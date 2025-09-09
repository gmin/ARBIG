"""
MA-RSI组合策略 - 黄金期货专业交易策略

## 策略概述
这是一个专门针对上期所黄金期货设计的技术分析策略，结合双均线趋势识别和RSI超买超卖指标，
提供稳健的交易信号。策略集成了完善的风控机制和实时持仓管理功能。

## 技术指标组合
- 📈 **双均线系统**：MA5/MA20 用于趋势识别
- 📊 **RSI指标**：14周期RSI用于超买超卖确认
- 🛡️ **风控系统**：止损2% + 止盈3% + 持仓限制
- 🔄 **持仓管理**：实时查询 + 智能缓存机制

## 交易逻辑
1. **趋势识别**：短期均线上穿长期均线 → 看涨趋势
2. **入场确认**：RSI在合理区间（非极端超买超卖）
3. **风控执行**：严格的止损止盈和持仓限制
4. **信号过滤**：避免频繁交易，设置最小信号间隔

## 适用市场
- ✅ 上期所黄金期货（au主力合约）
- ✅ 日内交易和短线交易
- ✅ 趋势性行情和震荡行情
- ⚠️ 需要足够的流动性和波动性

## 风险特征
- 📊 **风险等级**：中等
- 💰 **资金要求**：适中（每手约5-10万保证金）
- ⏱️ **持仓周期**：分钟级到小时级
- 📈 **预期收益**：稳健型，追求风险调整后收益
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from services.strategy_service.core.data_tools import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class MaRsiComboStrategy(ARBIGCtaTemplate):
    """
    MA-RSI组合策略 - 黄金期货专业交易策略
    
    ## 核心交易逻辑
    1. **趋势判断**：双均线(MA5/MA20)识别市场趋势方向
    2. **入场时机**：RSI(14)确认超买超卖状态，避免极端点位入场
    3. **风控机制**：动态止损止盈 + 实时持仓限制
    4. **信号过滤**：时间间隔控制，避免过度交易
    5. **持仓管理**：实时查询真实持仓，智能缓存减少服务压力
    
    ## 技术指标详解
    - **MA5/MA20**：短期/长期均线，判断趋势强度和方向
    - **RSI14**：相对强弱指标，识别超买(>70)超卖(<30)状态  
    - **止损机制**：2%固定止损，保护资金安全
    - **止盈机制**：3%目标止盈，锁定利润
    
    ## 信号生成条件
    - 🟢 **买入信号**：MA5 > MA20 (上升趋势) + RSI < 70 (非超买)
    - 🔴 **卖出信号**：MA5 < MA20 (下降趋势) + RSI > 30 (非超卖)
    - ⏸️ **观望信号**：趋势不明确或RSI处于极端区域
    """
    
    # ==================== 策略参数配置 ====================
    
    # 技术指标参数
    ma_short = 5          # 短期均线周期：5周期EMA，捕捉短期趋势变化
    ma_long = 20          # 长期均线周期：20周期EMA，确认主要趋势方向
    rsi_period = 14       # RSI计算周期：标准14周期，平衡敏感性和稳定性
    rsi_overbought = 70   # RSI超买阈值：>70视为超买，谨慎做多
    rsi_oversold = 30     # RSI超卖阈值：<30视为超卖，谨慎做空
    
    # 风险控制参数
    stop_loss_pct = 0.006  # 止损百分比：0.6%固定止损，控制单笔损失
    take_profit_pct = 0.008 # 止盈百分比：0.8%目标止盈，锁定利润
    
    # 交易执行参数
    trade_volume = 1      # 基础交易手数：每次交易的标准手数
    max_position = 5      # 最大持仓限制：总持仓不超过5手，控制整体风险
    
    # 策略变量
    entry_price = 0.0     # 入场价格
    last_signal_time = 0  # 上次信号时间
    signal_count = 0      # 信号计数

    # 🔧 重复下单防护机制
    last_bar_time = None  # 上次处理的K线时间
    last_order_id = None  # 上次发送的订单ID
    min_signal_interval = 30  # 最小信号间隔（秒）
    pending_orders = set()  # 待成交订单集合
    
    def __init__(self, strategy_name: str, symbol: str, setting: dict, signal_sender=None, **kwargs):
        """初始化策略 - 兼容策略引擎参数"""
        super().__init__(strategy_name, symbol, setting, signal_sender=signal_sender, **kwargs)
        
        # 策略参数配置
        self.ma_short = setting.get('ma_short', 5)
        self.ma_long = setting.get('ma_long', 20)
        self.rsi_period = setting.get('rsi_period', 14)
        self.rsi_overbought = setting.get('rsi_overbought', 70)
        self.rsi_oversold = setting.get('rsi_oversold', 30)
        self.stop_loss_pct = setting.get('stop_loss_pct', 0.006)
        self.take_profit_pct = setting.get('take_profit_pct', 0.008)
        self.trade_volume = setting.get('trade_volume', 1)
        self.max_position = setting.get('max_position', 5)
        
        # 初始化ArrayManager
        self.am = ArrayManager()

        # 🔧 持仓缓存机制 - 应用优化架构
        self.cached_position = 0  # 净持仓缓存
        self.cached_long_position = 0  # 多单持仓缓存
        self.cached_short_position = 0  # 空单持仓缓存
        self.last_position_update = 0  # 上次持仓更新时间

        # 🔧 信号控制优化
        self.signal_lock = False  # 信号生成锁定标志

        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   双均线: {self.ma_short}/{self.ma_long}")
        logger.info(f"   RSI参数: {self.rsi_period}({self.rsi_oversold}-{self.rsi_overbought})")
        logger.info(f"   风控: 止损{self.stop_loss_pct*100}% 止盈{self.take_profit_pct*100}%")
        logger.info(f"   🔧 已集成优化的持仓管理和风控机制")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("MA-RSI组合策略初始化")

    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 MA-RSI组合策略已启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ MA-RSI组合策略已停止")
        
    # 🎯 MaRsiComboStrategy是纯技术分析策略，不需要on_tick方法
    # 只基于K线数据进行分析，符合标准量化交易架构：
    # 策略服务合成K线 → 策略计算指标 → 策略生成信号
        
    def on_bar_impl(self, bar: BarData):
        """🎯 K线数据处理 - 技术分析策略的核心入口

        在基类ARBIGCtaTemplate的on_bar调用链中执行
        """
        logger.info(f"[策略服务-GoldMaRsi] 📊 收到K线数据: {bar.symbol} 时间={bar.datetime} 收盘价={bar.close_price}")

        if not self.trading:
            logger.info(f"[策略服务-GoldMaRsi] 🔧 策略未启用交易，跳过处理")
            return

        # 🎯 检查是否在交易时间，避免停市后生成重复K线
        if not self._is_trading_time():
            logger.debug(f"[策略服务-GoldMaRsi] ⏰ 非交易时间，跳过K线处理")
            return

        # 🎯 标准架构：策略服务合成K线 → 策略更新ArrayManager → 计算指标 → 生成信号
        self.am.update_bar(bar)

        # 确保有足够的数据
        if not self.am.inited:
            return

        # 🛡️ 优先检查止盈止损（基于当前价格）
        if self.pos != 0:
            self._check_risk_control(bar.close_price)

        # 检查信号间隔（避免频繁交易）
        current_time = time.time()
        if current_time - self.last_signal_time < 60:  # 1分钟间隔
            return

        # 🎯 应用优化的信号生成机制
        self._generate_sophisticated_signal(bar)

    def _process_tick_signal(self, tick: TickData):
        """🎯 基于tick的快速信号判断"""
        # 基于缓存持仓进行快速风控预检
        if abs(self.cached_position) >= self.max_position:
            return  # 已达上限，不生成信号

        # 其他快速判断逻辑...
        # 这里可以添加基于tick的快速信号判断
        pass

    def _generate_sophisticated_signal(self, bar: BarData):
        """🎯 优化的信号生成 - 分离信号生成和执行"""
        # 🚨 信号生成前置检查
        if self.signal_lock:
            logger.info(f"🔒 [SHFE策略] 信号生成被锁定，等待交易完成")
            return

        # 🎯 核心逻辑：分析市场条件
        signal_analysis = self._analyze_market_conditions(bar)

        # 🎯 生成交易决策
        signal_decision = self._make_sophisticated_decision(signal_analysis, bar.close_price)

        # 🎯 发送信号给处理模块
        if signal_decision['action'] in ['BUY', 'SELL']:
            logger.info(f"🎯 [SHFE策略] 生成交易信号: {signal_decision['action']} - {signal_decision['reason']}")
            self._process_trading_signal(signal_decision, bar.close_price)
        else:
            logger.info(f"🎯 [SHFE策略] 无交易信号: {signal_decision['reason']}")

    def _analyze_market_conditions(self, bar: BarData) -> dict:
        """🎯 分析市场条件 - 基于技术指标"""
        # 🔧 确保有足够的数据进行计算
        if not self.am.inited:
            return {
                "ma_short": 0,
                "ma_long": 0,
                "rsi": 50,
                "trend_signal": "NEUTRAL",
                "rsi_signal": "NEUTRAL",
                "current_price": bar.close_price
            }

        # 计算技术指标
        ma_short = self.am.sma(self.ma_short)
        ma_long = self.am.sma(self.ma_long)
        rsi = self.am.rsi(self.rsi_period)

        # 趋势分析
        trend_signal = "NEUTRAL"
        if ma_short > ma_long:
            trend_signal = "BULLISH"
        elif ma_short < ma_long:
            trend_signal = "BEARISH"

        # RSI分析
        rsi_signal = "NEUTRAL"
        if rsi < self.rsi_oversold:
            rsi_signal = "OVERSOLD"
        elif rsi > self.rsi_overbought:
            rsi_signal = "OVERBOUGHT"

        return {
            "ma_short": ma_short,
            "ma_long": ma_long,
            "rsi": rsi,
            "trend_signal": trend_signal,
            "rsi_signal": rsi_signal,
            "current_price": bar.close_price
        }

    def _make_sophisticated_decision(self, analysis: dict, current_price: float) -> dict:
        """🎯 基于分析结果做出交易决策"""
        trend_signal = analysis["trend_signal"]
        rsi_signal = analysis["rsi_signal"]
        rsi = analysis["rsi"]

        # 决策逻辑：趋势跟踪 + RSI确认
        if trend_signal == "BULLISH" and rsi_signal == "OVERSOLD":
            return {
                "action": "BUY",
                "reason": f"多头趋势+RSI超卖({rsi:.1f})",
                "strength": 1.0
            }
        elif trend_signal == "BEARISH" and rsi_signal == "OVERBOUGHT":
            return {
                "action": "SELL",
                "reason": f"空头趋势+RSI超买({rsi:.1f})",
                "strength": 1.0
            }
        elif trend_signal == "BULLISH" and rsi < 50:
            return {
                "action": "BUY",
                "reason": f"多头趋势+RSI中性偏低({rsi:.1f})",
                "strength": 0.7
            }
        elif trend_signal == "BEARISH" and rsi > 50:
            return {
                "action": "SELL",
                "reason": f"空头趋势+RSI中性偏高({rsi:.1f})",
                "strength": 0.7
            }
        else:
            return {
                "action": "HOLD",
                "reason": f"趋势{trend_signal}+RSI{rsi_signal}({rsi:.1f})，条件不满足",
                "strength": 0.0
            }
    def _execute_signal(self, signal: str, price: float, reason: str):
        """执行交易信号"""
        # 检查持仓限制
        if abs(self.pos) >= self.max_position:
            self.write_log(f"已达最大持仓 {self.max_position}，忽略信号: {signal}")
            return
            
        self.signal_count += 1
        
        if signal == "BUY":
            self.buy(price, self.trade_volume, stop=False)
            self.entry_price = price
            
        elif signal == "SELL":
            self.sell(price, self.trade_volume, stop=False)
            self.entry_price = price
            
        self.last_signal_time = time.time()
        
        self.write_log(f"📊 信号 #{self.signal_count}: {signal}")
        self.write_log(f"   原因: {reason}")
        self.write_log(f"   价格: {price:.2f}, 持仓: {self.pos}")
        
    def _check_risk_control(self, current_price: float):
        """检查风险控制"""
        if self.pos == 0 or self.entry_price == 0:
            return
            
        # 计算盈亏比例
        if self.pos > 0:  # 多头持仓
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:  # 空头持仓
            pnl_pct = (self.entry_price - current_price) / self.entry_price
            
        # 止损（使用小的容差处理浮点数精度问题）
        if pnl_pct <= -self.stop_loss_pct + 1e-6:
            self._close_all_positions(current_price, "止损")

        # 止盈（使用小的容差处理浮点数精度问题）
        elif pnl_pct >= self.take_profit_pct - 1e-6:
            self._close_all_positions(current_price, "止盈")
            
    def _close_all_positions(self, price: float, reason: str):
        """平掉所有持仓"""
        if self.pos == 0:
            return
            
        if self.pos > 0:
            self.sell(price, abs(self.pos), stop=False)
        else:
            self.buy(price, abs(self.pos), stop=False)
            
        self.write_log(f"🛑 {reason}: 平仓 {self.pos}手 @ {price:.2f}")
        self.entry_price = 0.0
        
    def on_order(self, order):
        """处理订单回调"""
        self.write_log(f"订单状态: {order.orderid} - {order.status}")
        
        # 如果订单被拒绝，重置入场价格
        if order.status.value == "拒单":
            self.entry_price = 0.0
            
    def on_trade(self, trade):
        """处理成交回调"""
        self.write_log(f"✅ 成交: {trade.direction} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"   当前持仓: {self.pos}")
        
        # 如果是开仓成交，记录入场价格
        if trade.offset.value == "开仓":
            self.entry_price = trade.price
            
        # 如果是平仓成交，重置入场价格
        elif abs(self.pos) == 0:
            self.entry_price = 0.0
            
        # 重要成交发送邮件通知
        if abs(trade.volume) >= 3:
            self.send_email(f"大额成交: {trade.direction} {trade.volume}手")
            
    def on_stop_order(self, stop_order):
        """处理停止单回调"""
        self.write_log(f"停止单触发: {stop_order.orderid}")
        
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        if not self.am.inited:
            return {"status": "数据不足"}
            
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "position": self.pos,
            "entry_price": self.entry_price,
            "signal_count": self.signal_count,
            "indicators": {
                "ma_short": self.am.sma(self.ma_short),
                "ma_long": self.am.sma(self.ma_long),
                "rsi": self.am.rsi(self.rsi_period)
            },
            "last_price": self.am.close_array[-1] if len(self.am.close_array) > 0 else 0
        }

    def _query_real_position(self) -> Optional[int]:
        """🔧 实时查询真实持仓 - 集成优化架构"""
        try:
            import requests

            # 查询交易服务的持仓API
            url = f"http://localhost:8001/real_trading/positions?symbol={self.symbol}"
            response = requests.get(url, timeout=2.0)

            if response.status_code == 200:
                position_data = response.json()
                if position_data.get("success") and position_data.get("data"):
                    position_info = position_data["data"]

                    # 获取持仓信息
                    long_position = position_info.get("long_position", 0)
                    short_position = position_info.get("short_position", 0)
                    net_position = position_info.get("net_position", 0)

                    logger.info(f"🔍 [SHFE策略] 查询到真实持仓: 多单={long_position}, 空单={short_position}, 净持仓={net_position}")

                    # 更新缓存
                    self.cached_long_position = long_position
                    self.cached_short_position = short_position
                    self.cached_position = net_position

                    return net_position
                else:
                    logger.warning(f"⚠️ [SHFE策略] 持仓查询返回空数据")
                    return None
            else:
                logger.warning(f"⚠️ [SHFE策略] 持仓查询失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"⚠️ [SHFE策略] 持仓查询异常: {e}")
            return None

    def _process_trading_signal(self, signal_decision: dict, current_price: float):
        """🔧 信号处理模块 - 主动查询持仓并执行交易"""
        action = signal_decision['action']

        logger.info(f"🔧 [SHFE策略] 信号处理模块：接收到{action}信号，开始处理")

        # 🔧 主动查询持仓进行智能风控检查
        if not self._pre_trade_safety_check(action):
            logger.info(f"🔧 [SHFE策略] 信号处理模块：风控检查未通过，信号被拒绝")
            return

        # 🎯 风控通过，执行交易订单
        logger.info(f"🔧 [SHFE策略] 信号处理模块：风控通过，执行{action}订单")

        # 计算交易数量
        trade_volume = self._calculate_position_size(signal_decision.get('strength', 1.0))

        # 🎯 智能单向持仓管理
        if action == 'BUY':
            if self.pos < 0:  # 有空头持仓，优先平空仓
                close_volume = min(trade_volume, abs(self.pos))
                logger.info(f"� [持仓管理] 有空头持仓{self.pos}手，BUY信号优先平空仓{close_volume}手")
                self.buy(current_price, close_volume, stop=False)

                # 如果还有剩余信号强度，考虑开多仓
                remaining_volume = trade_volume - close_volume
                if remaining_volume > 0:
                    logger.info(f"🔧 [持仓管理] 平空后剩余信号，开多仓{remaining_volume}手")
                    self.buy(current_price, remaining_volume, stop=False)
            else:  # 无持仓或有多头持仓，开多仓或加多仓
                if self.pos == 0:
                    logger.info(f"�🚀 [SHFE策略] 无持仓，执行开多仓！价格: {current_price}, 数量: {trade_volume}")
                else:
                    logger.info(f"🚀 [SHFE策略] 有多头持仓{self.pos}手，执行加多仓！价格: {current_price}, 数量: {trade_volume}")
                self.buy(current_price, trade_volume, stop=False)

        elif action == 'SELL':
            if self.pos > 0:  # 有多头持仓，优先平多仓
                close_volume = min(trade_volume, abs(self.pos))
                logger.info(f"🔧 [持仓管理] 有多头持仓{self.pos}手，SELL信号优先平多仓{close_volume}手")
                self.sell(current_price, close_volume, stop=False)

                # 如果还有剩余信号强度，考虑开空仓
                remaining_volume = trade_volume - close_volume
                if remaining_volume > 0:
                    logger.info(f"🔧 [持仓管理] 平多后剩余信号，开空仓{remaining_volume}手")
                    self.sell(current_price, remaining_volume, stop=False)
            else:  # 无持仓或有空头持仓，开空仓或加空仓
                if self.pos == 0:
                    logger.info(f"🚀 [SHFE策略] 无持仓，执行开空仓！价格: {current_price}, 数量: {trade_volume}")
                else:
                    logger.info(f"🚀 [SHFE策略] 有空头持仓{self.pos}手，执行加空仓！价格: {current_price}, 数量: {trade_volume}")
                self.sell(current_price, trade_volume, stop=False)

        # 更新信号时间
        self.last_signal_time = time.time()

    def _pre_trade_safety_check(self, action: str) -> bool:
        """🔧 交易前安全检查 - 智能持仓风控模块"""
        real_position = self._query_real_position()
        if real_position is None:
            logger.warning(f"⚠️ [SHFE策略] 无法查询持仓，停止交易")
            return False

        # 更新策略持仓
        if real_position != self.pos:
            logger.info(f"🔄 [SHFE策略] 持仓同步: {self.pos} → {real_position}")
            self.pos = real_position

        # 🎯 智能风控：区分平仓和开仓
        if action == 'BUY':
            if real_position < 0:
                # 有空头持仓，BUY信号是平空仓，允许执行
                logger.info(f"✅ [SHFE策略] BUY信号-平空仓: 当前空头={real_position}手，允许平仓")
                return True
            else:
                # 无空头持仓，BUY信号是开多仓，检查风控
                predicted_position = abs(real_position + 1)
                if predicted_position > self.max_position:
                    logger.warning(f"⚠️ [SHFE策略] 风控阻止开多: 当前={real_position}, 预测={predicted_position}, 限制={self.max_position}")
                    return False
                logger.info(f"✅ [SHFE策略] BUY信号-开多仓: 当前={real_position}手，预测={predicted_position}手，风控通过")
                return True

        elif action == 'SELL':
            if real_position > 0:
                # 有多头持仓，SELL信号是平多仓，允许执行
                logger.info(f"✅ [SHFE策略] SELL信号-平多仓: 当前多头={real_position}手，允许平仓")
                return True
            else:
                # 无多头持仓，SELL信号是开空仓，检查风控
                predicted_position = abs(real_position - 1)
                if predicted_position > self.max_position:
                    logger.warning(f"⚠️ [SHFE策略] 风控阻止开空: 当前={real_position}, 预测={predicted_position}, 限制={self.max_position}")
                    return False
                logger.info(f"✅ [SHFE策略] SELL信号-开空仓: 当前={real_position}手，预测={predicted_position}手，风控通过")
                return True

        return True

    def _is_trading_time(self) -> bool:
        """检查是否在交易时间"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        # 日盘: 9:00-11:30, 13:30-15:00
        # 夜盘: 21:00-02:30
        if (9 <= hour < 11) or (hour == 11 and minute <= 30):
            return True
        elif (13 <= hour < 15) or (hour == 13 and minute >= 30):
            return True
        elif hour >= 21 or hour <= 2:
            return True
        elif hour == 2 and minute <= 30:
            return True

        return False

    def on_tick_impl(self, tick: TickData):
        """具体的tick处理实现 - 必需的抽象方法"""
        # 这里可以添加基于tick的快速处理逻辑
        # 目前主要逻辑在on_bar中处理
        pass

    def on_tick_impl(self, tick: TickData):
        """具体的tick处理实现 - 必需的抽象方法"""
        # 这里可以添加基于tick的快速处理逻辑
        # 目前主要逻辑在on_bar_impl中处理
        pass

    def on_trade_impl(self, trade):
        """具体的成交处理实现"""
        logger.info(f"🔥 [SHFE策略] 成交确认: {trade.direction} {trade.volume}手 @ {trade.price}")

        # 成交后异步更新持仓缓存
        try:
            import threading

            def update_cache():
                real_position = self._query_real_position()
                if real_position is not None:
                    old_cache = self.cached_position
                    self.cached_position = real_position
                    self.last_position_update = time.time()
                    logger.info(f"🔧 [SHFE策略] 成交后缓存更新: {old_cache} → {real_position}")

            # 在后台线程中更新缓存
            threading.Thread(target=update_cache, daemon=True).start()

        except Exception as e:
            logger.error(f"⚠️ [SHFE策略] 持仓缓存更新失败: {e}")

    def _calculate_position_size(self, signal_strength: float = 1.0) -> int:
        """
        计算交易数量

        Args:
            signal_strength: 信号强度 (0.0-1.0)

        Returns:
            交易数量
        """
        # 基础交易数量
        base_volume = self.trade_volume

        # 根据信号强度调整数量（可选）
        adjusted_volume = int(base_volume * signal_strength)

        # 确保至少为1手
        return max(1, adjusted_volume)


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> MaRsiComboStrategy:
    """创建MA-RSI组合策略实例"""
    
    # 默认设置
    default_setting = {
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss_pct': 0.006,
        'take_profit_pct': 0.008,
        'trade_volume': 1,
        'max_position': 5
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return MaRsiComboStrategy(strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "MaRsiComboStrategy",
    "file_name": "MaRsiComboStrategy.py",
    "description": "MA-RSI组合策略，专门针对黄金期货的双均线+RSI组合交易策略",
    "parameters": {
        "ma_short": {
            "type": "int",
            "default": 5,
            "description": "短期均线周期"
        },
        "ma_long": {
            "type": "int",
            "default": 20,
            "description": "长期均线周期"
        },
        "rsi_period": {
            "type": "int",
            "default": 14,
            "description": "RSI计算周期"
        },
        "rsi_overbought": {
            "type": "int",
            "default": 70,
            "description": "RSI超买阈值"
        },
        "rsi_oversold": {
            "type": "int", 
            "default": 30,
            "description": "RSI超卖阈值"
        },
        "stop_loss_pct": {
            "type": "float",
            "default": 0.006,
            "description": "止损百分比"
        },
        "take_profit_pct": {
            "type": "float",
            "default": 0.008,
            "description": "止盈百分比"
        },
        "trade_volume": {
            "type": "int",
            "default": 1,
            "description": "每次交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 5,
            "description": "最大持仓手数"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("简化SHFE策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
