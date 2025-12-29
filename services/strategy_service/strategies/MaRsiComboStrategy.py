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
    add_loss_pct = 0.001   # 加仓亏损阈值：0.1%，只有亏损达到此阈值才允许加仓

    # 交易执行参数
    trade_volume = 1      # 基础交易手数：每次交易的标准手数
    max_position = 5      # 最大持仓限制：总持仓不超过5手，控制整体风险
    
    # 策略变量
    last_signal_time = 0  # 上次信号时间

    # 🎯 性能优化：缓存当前K线的指标计算结果
    current_ma5 = 0.0     # 当前MA5值
    current_ma20 = 0.0    # 当前MA20值
    current_rsi = 0.0     # 当前RSI值

    # � 绘图数据记录
    plot_data = []        # 存储绘图数据 [时间, 价格, MA5, MA20, RSI]

    # �🔧 重复下单防护机制
    last_bar_time = None  # 上次处理的K线时间
    last_order_id = None  # 上次发送的订单ID
    min_signal_interval = 60  # 最小信号间隔（秒）- 可配置参数
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
        self.add_loss_pct = setting.get('add_loss_pct', 0.001)
        self.trade_volume = setting.get('trade_volume', 1)
        self.max_position = setting.get('max_position', 5)
        
        # 初始化ArrayManager
        self.am = ArrayManager()

        # 🔧 持仓缓存机制 - 应用优化架构
        self.cached_position = 0  # 净持仓缓存（减少API查询）
        self.last_position_update = 0  # 上次持仓更新时间

        # 🔧 信号控制优化
        self.signal_lock = False  # 信号生成锁定标志

        # 🎯 均线历史数据（用于金叉死叉检测）
        self.ma5_history = []  # MA5历史值
        self.ma20_history = []  # MA20历史值
        self.max_history_length = 10  # 保留最近10个值

        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   双均线: {self.ma_short}/{self.ma_long}")
        logger.info(f"   RSI参数: {self.rsi_period}({self.rsi_oversold}-{self.rsi_overbought})")
        logger.info(f"   风控: 止损{self.stop_loss_pct*100}% 止盈{self.take_profit_pct*100}%")
        logger.info(f"   加仓控制: 亏损阈值{self.add_loss_pct*100}%")
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
        
    # 🎯 MaRsiComboStrategy采用双层架构：
    # K线级别：技术分析和信号生成 (on_bar_impl)
    # Tick级别：实时风控和止盈止损 (on_tick_impl)
        
    def on_bar_impl(self, bar: BarData):
        """🎯 K线数据处理 - 技术分析策略的核心入口

        在基类ARBIGCtaTemplate的on_bar调用链中执行
        """
        logger.info(f"[策略服务-GoldMaRsi] 📊 收到K线数据: {bar.symbol} 时间={bar.datetime} 收盘价={bar.close_price}")

        if not self.trading:
            logger.warning(f"[策略服务-GoldMaRsi] ⚠️ 策略未启用交易(self.trading={self.trading})，跳过处理")
            return

        # 🎯 标准架构：策略引擎已在源头控制交易时间 → 策略更新ArrayManager → 计算指标 → 生成信号
        self.am.update_bar(bar)

        # 确保有足够的数据
        if not self.am.inited:
            logger.debug(f"[策略服务-GoldMaRsi] 🔧 ArrayManager未初始化(inited={self.am.inited})，跳过处理")
            return

        # 🎯 性能优化：每个K线只计算一次指标，后续复用
        self.current_ma5 = self.am.ema(self.ma_short)   # 改为EMA5
        self.current_ma20 = self.am.ema(self.ma_long)   # 改为EMA20
        self.current_rsi = self.am.rsi(self.rsi_period)

        # 📝 每个K线都记录指标数据到CSV文件（不受信号间隔限制）
        # 🎯 为CSV记录单独检测交叉信号（避免重复调用）
        csv_cross_signal = self._detect_ma_cross(bar.close_price)
        csv_analysis = {
            "ma_short": self.current_ma5,
            "ma_long": self.current_ma20,
            "rsi": self.current_rsi,
            "cross_signal": csv_cross_signal,
            "current_price": bar.close_price
        }

        self._log_indicators_to_csv(bar, csv_analysis)

        # 🛡️ 实时风控检查在on_tick_impl中处理，K线级别专注信号生成

        # 检查信号间隔（避免频繁交易）
        current_time = time.time()
        time_since_last_signal = current_time - self.last_signal_time
        if time_since_last_signal < self.min_signal_interval:
            logger.debug(f"[策略服务-GoldMaRsi] ⏱️ 信号间隔限制: {time_since_last_signal:.2f}s < {self.min_signal_interval}s，跳过处理")
            return

        logger.info(f"[策略服务-GoldMaRsi] ✅ 通过所有检查，准备生成交易信号")
        # 🎯 应用优化的信号生成机制
        self._generate_trading_signal(bar)

    def _generate_trading_signal(self, bar: BarData):
        """🎯 生成交易信号 - 分离信号生成和执行"""
        logger.info(f"🔍 [SHFE策略] 开始生成交易信号: {bar.symbol} 时间={bar.datetime} 价格={bar.close_price}")

        # 🚨 信号生成前置检查
        if self.signal_lock:
            logger.info(f"🔒 [SHFE策略] 信号生成被锁定，等待交易完成")
            return

        # 🎯 核心逻辑：分析市场条件（为交易决策单独分析）
        signal_analysis = self._analyze_market_conditions(bar)

        # 🎯 生成交易决策
        signal_decision = self._analyze_trading_opportunity(signal_analysis, bar.close_price)

        # 🎯 发送信号给处理模块
        if signal_decision['action'] in ['BUY', 'SELL']:
            # 📊 记录交易信号时的完整指标数据（用于复盘分析）
            self._log_trading_signal_indicators(signal_analysis, signal_decision, bar.close_price)
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

        # 🎯 使用缓存的技术指标（性能优化）
        ma_short = self.current_ma5
        ma_long = self.current_ma20
        rsi = self.current_rsi

        # 🎯 更新MA历史数据
        self.ma5_history.append(ma_short)
        self.ma20_history.append(ma_long)

        # 保持历史数据长度
        if len(self.ma5_history) > self.max_history_length:
            self.ma5_history.pop(0)
        if len(self.ma20_history) > self.max_history_length:
            self.ma20_history.pop(0)

        # 🎯 金叉死叉检测 - 传入当前价格进行确认
        cross_signal = self._detect_ma_cross(bar.close_price)

        # 趋势分析（保留原有逻辑作为辅助）
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
            "cross_signal": cross_signal,  # 新增：金叉死叉信号
            "current_price": bar.close_price
        }

    def _detect_ma_cross(self, current_price: float) -> str:
        """🎯 检测MA5和MA20的金叉死叉 - 改进的交叉幅度和价格确认"""
        if len(self.ma5_history) < 2 or len(self.ma20_history) < 2:
            return "NONE"  # 数据不足，需要至少2个点进行确认

        # 获取最近2个时刻的MA值（用于确认检测）
        ma5_values = self.ma5_history[-2:]  # [前1, 当前]
        ma20_values = self.ma20_history[-2:]

        # 🔍 详细调试日志
        logger.debug(f"🔍 [交叉调试] MA5历史: {self.ma5_history[-3:] if len(self.ma5_history) >= 3 else self.ma5_history}")
        logger.debug(f"🔍 [交叉调试] MA20历史: {self.ma20_history[-3:] if len(self.ma20_history) >= 3 else self.ma20_history}")
        logger.debug(f"🔍 [交叉调试] 比较点 - 前1时刻: MA5={ma5_values[0]:.2f}, MA20={ma20_values[0]:.2f}")
        logger.debug(f"🔍 [交叉调试] 比较点 - 当前时刻: MA5={ma5_values[1]:.2f}, MA20={ma20_values[1]:.2f}")
        logger.debug(f"🔍 [交叉调试] 当前价格: {current_price:.2f}")

        # 金叉检测：MA5从下方穿越MA20 + 价格确认
        if (ma5_values[0] <= ma20_values[0] and  # 前1时刻：MA5 <= MA20
            ma5_values[1] > ma20_values[1]):     # 当前时刻：MA5 > MA20 (交叉发生)

            # 计算交叉幅度 - 从交叉前到交叉后的总变化
            cross_strength = abs((ma5_values[1] - ma20_values[1]) - (ma5_values[0] - ma20_values[0]))

            # 价格确认 - 收盘价应该在MA5之上
            price_confirmation = current_price > ma5_values[1]

            if cross_strength >= 0.05 and price_confirmation:  # 交叉幅度降到0.05，提高灵敏度
                logger.info(f"🌟 [均线信号] 确认金叉: MA5({ma5_values[1]:.2f}) 上穿 MA20({ma20_values[1]:.2f})")
                logger.info(f"🌟 [交叉详情] 交叉幅度:{cross_strength:.2f} | 价格:{current_price:.2f} > MA5:{ma5_values[1]:.2f}")
                return "GOLDEN_CROSS"
            else:
                reason = []
                if cross_strength < 0.05:
                    reason.append(f"幅度不足({cross_strength:.2f}<0.05)")
                if not price_confirmation:
                    reason.append(f"价格未确认({current_price:.2f}≤{ma5_values[1]:.2f})")
                logger.debug(f"🔍 [均线信号] 金叉未确认: {', '.join(reason)}")

        # 死叉检测：MA5从上方穿越MA20 + 价格确认
        death_cross_condition1 = ma5_values[0] >= ma20_values[0]  # 前1时刻：MA5 >= MA20
        death_cross_condition2 = ma5_values[1] < ma20_values[1]   # 当前时刻：MA5 < MA20

        logger.debug(f"🔍 [死叉检测] 条件1(前1时刻MA5>=MA20): {ma5_values[0]:.2f} >= {ma20_values[0]:.2f} = {death_cross_condition1}")
        logger.debug(f"🔍 [死叉检测] 条件2(当前时刻MA5<MA20): {ma5_values[1]:.2f} < {ma20_values[1]:.2f} = {death_cross_condition2}")

        if death_cross_condition1 and death_cross_condition2:

            # 计算交叉幅度 - 从交叉前到交叉后的总变化
            cross_strength = abs((ma5_values[1] - ma20_values[1]) - (ma5_values[0] - ma20_values[0]))

            # 价格确认 - 收盘价应该在MA5之下
            price_confirmation = current_price < ma5_values[1]

            logger.debug(f"🔍 [死叉检测] 交叉幅度: {cross_strength:.2f} >= 0.05 = {cross_strength >= 0.05}")
            logger.debug(f"🔍 [死叉检测] 价格确认: {current_price:.2f} < {ma5_values[1]:.2f} = {price_confirmation}")

            if cross_strength >= 0.05 and price_confirmation:  # 交叉幅度降到0.05，提高灵敏度
                logger.info(f"💀 [均线信号] 确认死叉: MA5({ma5_values[1]:.2f}) 下穿 MA20({ma20_values[1]:.2f})")
                logger.info(f"💀 [交叉详情] 交叉幅度:{cross_strength:.2f} | 价格:{current_price:.2f} < MA5:{ma5_values[1]:.2f}")
                return "DEATH_CROSS"
            else:
                reason = []
                if cross_strength < 0.05:
                    reason.append(f"幅度不足({cross_strength:.2f}<0.05)")
                if not price_confirmation:
                    reason.append(f"价格未确认({current_price:.2f}≥{ma5_values[1]:.2f})")
                logger.debug(f"🔍 [均线信号] 死叉未确认: {', '.join(reason)}")
        else:
            logger.debug(f"🔍 [死叉检测] 不满足交叉条件，跳过检测")

        return "NONE"

    def _log_trading_signal_indicators(self, analysis: dict, decision: dict, current_price: float):
        """📊 记录交易信号时的完整指标数据到K线日志文件（用于复盘分析）"""
        # 直接使用现有logger记录交易信号指标

        ma5 = analysis["ma_short"]
        ma20 = analysis["ma_long"]
        rsi = analysis["rsi"]
        cross_signal = analysis["cross_signal"]

        # 计算交叉强度
        cross_strength = 0.0
        if len(self.ma5_history) >= 1 and len(self.ma20_history) >= 1:
            cross_strength = abs(ma5 - ma20) / ma20

        # 📊 详细的交易信号记录
        logger.info(f"🎯 [交易信号] ==========================================")
        logger.info(f"🎯 [交易信号] 信号类型: {decision['action']} - {decision['reason']}")
        logger.info(f"🎯 [交易信号] 当前价格: {current_price:.2f}")
        logger.info(f"🎯 [交易信号] MA5: {ma5:.2f}")
        logger.info(f"🎯 [交易信号] MA20: {ma20:.2f}")
        logger.info(f"🎯 [交易信号] MA差值: {ma5-ma20:.2f} ({((ma5-ma20)/ma20*100):+.2f}%)")
        logger.info(f"🎯 [交易信号] RSI: {rsi:.1f}")
        logger.info(f"🎯 [交易信号] 交叉信号: {cross_signal}")
        logger.info(f"🎯 [交易信号] 交叉强度: {cross_strength:.4f} ({cross_strength*100:.2f}%)")
        logger.info(f"🎯 [交易信号] 当前持仓: {self.pos}")

        # MA历史数据（最近3个值）用于手工验证
        if len(self.ma5_history) >= 3:
            logger.info(f"🎯 [交易信号] MA5历史: {[f'{x:.2f}' for x in self.ma5_history[-3:]]}")
        if len(self.ma20_history) >= 3:
            logger.info(f"🎯 [交易信号] MA20历史: {[f'{x:.2f}' for x in self.ma20_history[-3:]]}")

        logger.info(f"🎯 [交易信号] ==========================================")

    def _analyze_trading_opportunity(self, analysis: dict, current_price: float) -> dict:
        """🎯 分析交易机会 - 基于金叉死叉信号做出交易决策"""
        cross_signal = analysis["cross_signal"]
        rsi = analysis["rsi"]

        # 🎯 新逻辑：基于金叉死叉 + RSI确认
        if cross_signal == "GOLDEN_CROSS":
            # 金叉买入信号
            if 30 < rsi < 70:  # RSI在合理区间
                return {
                    "action": "BUY",
                    "reason": f"金叉信号+RSI确认({rsi:.1f})",
                    "strength": 1.0
                }
            else:
                return {
                    "action": "NONE",
                    "reason": f"金叉信号但RSI不合适({rsi:.1f})",
                    "strength": 0
                }
        elif cross_signal == "DEATH_CROSS":
            # 死叉卖出信号
            if 30 < rsi < 70:  # RSI在合理区间
                return {
                    "action": "SELL",
                    "reason": f"死叉信号+RSI确认({rsi:.1f})",
                    "strength": 1.0
                }
            else:
                return {
                    "action": "NONE",
                    "reason": f"死叉信号但RSI不合适({rsi:.1f})",
                    "strength": 0
                }
        else:
            # 无交叉信号
            return {
                "action": "NONE",
                "reason": f"无金叉死叉信号，RSI({rsi:.1f})",
                "strength": 0.0
            }

    def _check_risk_control(self, current_price: float):
        """检查风险控制 - 基于上期所真实持仓成本价"""
        if self.pos == 0:
            return

        # 🎯 从上期所查询真实的持仓成本价
        try:
            real_position = self._query_real_position()
            if real_position is None:
                logger.warning("⚠️ [风控] 无法获取持仓信息，跳过风控检查")
                return

            # 获取持仓成本价（根据净持仓方向选择对应价格）
            net_position = real_position.get("net_position", 0)
            if net_position > 0:
                # 净多头持仓，使用多单价格
                entry_price = real_position.get("long_price", 0)
            elif net_position < 0:
                # 净空头持仓，使用空单价格
                entry_price = real_position.get("short_price", 0)
            else:
                # 无净持仓
                logger.debug("⚠️ [风控] 无净持仓，跳过风控检查")
                return

            if entry_price <= 0:
                logger.warning(f"⚠️ [风控] 持仓成本价无效: net_position={net_position}, entry_price={entry_price}")
                return

            # 🔍 调试日志：验证 net_position 和 self.pos 是否一致
            if net_position != self.pos:
                logger.warning(f"⚠️ [风控] 持仓不同步! net_position={net_position}, self.pos={self.pos}, entry_price={entry_price:.2f}, current_price={current_price:.2f}")

            logger.info(f"🔍 [风控检查] net_position={net_position}, self.pos={self.pos}, entry_price={entry_price:.2f}, current_price={current_price:.2f}")

            # 计算盈亏比例 - 🔧 统一使用 net_position 判断方向，避免不同步问题
            if net_position > 0:  # 多头持仓
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # 空头持仓
                pnl_pct = (entry_price - current_price) / entry_price

            logger.info(f"🔍 [风控检查] 盈亏比例={pnl_pct*100:.3f}%, 止损线={-self.stop_loss_pct*100:.2f}%, 止盈线={self.take_profit_pct*100:.2f}%")

            # 止损（使用小的容差处理浮点数精度问题）
            if pnl_pct <= -self.stop_loss_pct + 1e-6:
                self._close_all_positions(current_price, entry_price, "止损")

            # 止盈（使用小的容差处理浮点数精度问题）
            elif pnl_pct >= self.take_profit_pct - 1e-6:
                self._close_all_positions(current_price, entry_price, "止盈")

        except Exception as e:
            logger.error(f"⚠️ [风控] 风控检查异常: {e}")
            
    def _close_all_positions(self, price: float, entry_price: float, reason: str):
        """平掉所有持仓"""
        if self.pos == 0:
            return

        # 📊 记录风控触发时的详细数据（用于复盘分析）
        pnl_amount = 0.0
        pnl_pct = 0.0
        if entry_price > 0:
            if self.pos > 0:  # 多头持仓
                pnl_amount = (price - entry_price) * abs(self.pos)
                pnl_pct = (price - entry_price) / entry_price
            else:  # 空头持仓
                pnl_amount = (entry_price - price) * abs(self.pos)
                pnl_pct = (entry_price - price) / entry_price

        # 📊 详细的风控记录
        logger.info(f"🛑 [风控触发] ==========================================")
        logger.info(f"🛑 [风控触发] 风控类型: {reason}")
        logger.info(f"🛑 [风控触发] 平仓价格: {price:.2f}")
        logger.info(f"🛑 [风控触发] 入场价格: {entry_price:.2f} (来自上期所)")
        logger.info(f"🛑 [风控触发] 持仓数量: {self.pos}手")
        logger.info(f"🛑 [风控触发] 盈亏金额: {pnl_amount:+.2f}元")
        logger.info(f"🛑 [风控触发] 盈亏比例: {pnl_pct*100:+.2f}%")
        logger.info(f"🛑 [风控触发] 价格变动: {price - entry_price:+.2f}元")
        logger.info(f"🛑 [风控触发] ==========================================")

        if self.pos > 0:
            self._smart_close_position('LONG', abs(self.pos), price)  # 智能平多仓
        else:
            self._smart_close_position('SHORT', abs(self.pos), price)  # 智能平空仓

        self.write_log(f"🛑 {reason}: 平仓 {self.pos}手 @ {price:.2f}, 盈亏{pnl_pct*100:+.2f}%")
        
    def on_order(self, order):
        """处理订单回调"""
        self.write_log(f"订单状态: {order.orderid} - {order.status}")
        
        # 订单被拒绝时的处理
        if order.status.value == "拒单":
            logger.warning(f"⚠️ 订单被拒绝: {order.orderid}")
            
    def on_trade(self, trade):
        """处理成交回调"""
        self.write_log(f"✅ 成交: {trade.direction} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"   当前持仓: {self.pos}")
            
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
            "indicators": {
                "ma_short": self.current_ma5,
                "ma_long": self.current_ma20,
                "rsi": self.current_rsi
            },
            "last_price": self.am.close_array[-1] if len(self.am.close_array) > 0 else 0
        }

    def _query_real_position(self) -> Optional[dict]:
        """🔧 实时查询真实持仓 - 返回完整持仓信息（包含今昨仓）"""
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
                    long_price = position_info.get("long_price", 0)
                    short_price = position_info.get("short_price", 0)
                    current_price = position_info.get("current_price", 0)

                    # 获取今昨仓信息
                    long_today = position_info.get("long_today", 0)
                    long_yesterday = position_info.get("long_yesterday", 0)
                    short_today = position_info.get("short_today", 0)
                    short_yesterday = position_info.get("short_yesterday", 0)

                    logger.info(f"🔍 [SHFE策略] 查询到真实持仓: 多单={long_position}@{long_price:.2f}(今{long_today}昨{long_yesterday}), 空单={short_position}@{short_price:.2f}(今{short_today}昨{short_yesterday}), 净持仓={net_position}")

                    # 更新缓存（只保留净持仓）
                    self.cached_position = net_position

                    # 返回完整持仓信息（包含多空价格和今昨仓）
                    return {
                        "net_position": net_position,
                        "long_position": long_position,
                        "short_position": short_position,
                        "long_price": long_price,
                        "short_price": short_price,
                        "current_price": current_price,
                        "long_today": long_today,
                        "long_yesterday": long_yesterday,
                        "short_today": short_today,
                        "short_yesterday": short_yesterday
                    }
                else:
                    logger.warning(f"⚠️ [SHFE策略] 持仓查询返回空数据")
                    return None
            else:
                logger.warning(f"⚠️ [SHFE策略] 持仓查询失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"⚠️ [SHFE策略] 持仓查询异常: {e}")
            return None

    def _smart_close_position(self, direction: str, volume: int, price: float):
        """🔧 智能平仓 - 自动拆分今昨仓订单

        Args:
            direction: 'LONG' 表示平多仓，'SHORT' 表示平空仓
            volume: 要平仓的总数量
            price: 平仓价格
        """
        if volume <= 0:
            logger.warning(f"⚠️ [智能平仓] 平仓数量无效: {volume}")
            return

        # 查询持仓今昨仓信息
        position_info = self._query_real_position()
        if not position_info:
            logger.warning(f"⚠️ [智能平仓] 无法获取持仓信息，使用普通平仓")
            if direction == 'LONG':
                self.sell(price, volume, stop=False)
            else:
                self.cover(price, volume, stop=False)
            return

        # 根据方向获取今昨仓数量
        if direction == 'LONG':
            # 平多仓
            today_pos = position_info.get("long_today", 0)
            yesterday_pos = position_info.get("long_yesterday", 0)
            action_name = "平多"
        else:
            # 平空仓
            today_pos = position_info.get("short_today", 0)
            yesterday_pos = position_info.get("short_yesterday", 0)
            action_name = "平空"

        total_pos = today_pos + yesterday_pos

        # 检查持仓是否足够
        if volume > total_pos:
            logger.warning(f"⚠️ [智能平仓] {action_name}数量{volume}超过持仓{total_pos}，调整为{total_pos}")
            volume = total_pos

        # 调整后再次检查数量
        if volume <= 0:
            logger.warning(f"⚠️ [智能平仓] 调整后数量为0，取消平仓")
            return

        logger.info(f"🔍 [智能平仓] {action_name}{volume}手: 今仓{today_pos}手, 昨仓{yesterday_pos}手")

        # 🔧 修改策略：优先平昨仓（更稳定），再平今仓
        # 判断是否需要拆分订单
        if today_pos > 0 and yesterday_pos > 0 and volume > yesterday_pos:
            # 需要拆分：今昨仓都有，且平仓数量超过昨仓
            yesterday_volume = min(volume, yesterday_pos)
            today_volume = volume - yesterday_volume

            logger.info(f"📋 [智能平仓] 拆分订单: 先平昨仓{yesterday_volume}手, 再平今仓{today_volume}手")

            # 先平昨仓（更稳定）
            if yesterday_volume > 0:
                if direction == 'LONG':
                    self.sell(price, yesterday_volume, stop=False)
                else:
                    self.cover(price, yesterday_volume, stop=False)
                logger.info(f"✅ [智能平仓] 已发送平昨仓订单: {yesterday_volume}手")
                time.sleep(0.1)  # 短暂延迟，避免订单冲突

            # 再平今仓
            if today_volume > 0:
                if direction == 'LONG':
                    self.sell(price, today_volume, stop=False)
                else:
                    self.cover(price, today_volume, stop=False)
                logger.info(f"✅ [智能平仓] 已发送平今仓订单: {today_volume}手")
        else:
            # 不需要拆分：只有昨仓或只有今仓，或平仓数量不超过昨仓
            logger.info(f"📋 [智能平仓] 无需拆分，直接{action_name}{volume}手")
            if direction == 'LONG':
                self.sell(price, volume, stop=False)
            else:
                self.cover(price, volume, stop=False)

    def _process_trading_signal(self, signal_decision: dict, current_price: float):
        """🔧 信号处理模块 - 新策略：盈利平仓+信号开仓"""
        action = signal_decision['action']

        logger.info(f"🔧 [持仓管理] 接收到{action}信号，当前价格={current_price:.2f}")

        # 🔧 查询真实持仓信息（包含开仓均价）
        position_info = self._query_real_position()
        if position_info is None:
            logger.warning(f"⚠️ [持仓管理] 无法查询持仓信息，停止交易")
            return

        long_position = position_info.get("long_position", 0)
        short_position = position_info.get("short_position", 0)
        long_price = position_info.get("long_price", 0)
        short_price = position_info.get("short_price", 0)

        logger.info(f"🔍 [持仓管理] 当前持仓: 多头={long_position}手@{long_price:.2f}, 空头={short_position}手@{short_price:.2f}")
        logger.info(f"🔍 [持仓管理] 信号决策: {signal_decision}")

        # 计算交易数量
        trade_volume = self._calculate_position_size(signal_decision.get('strength', 1.0))

        # 标记是否需要延迟（如果有平仓操作）
        need_delay = False

        # 🎯 新策略逻辑：金叉信号
        if action == 'BUY':
            logger.info(f"🌟 [持仓管理] 金叉信号处理开始")

            # 1. 检查空头持仓 - 盈利则平仓
            if short_position > 0:
                short_pnl = (short_price - current_price) * short_position  # 空头盈亏
                if short_pnl > 0:  # 空头盈利
                    logger.info(f"� [持仓管理] 空头盈利{short_pnl:.2f}元，平空{short_position}手")
                    self._smart_close_position('SHORT', short_position, current_price)
                    need_delay = True
                else:
                    logger.info(f"📉 [持仓管理] 空头亏损{abs(short_pnl):.2f}元，保留空头{short_position}手")

            # 2. 检查多头持仓限制（最多2手）
            if long_position >= 2:
                logger.warning(f"⚠️ [持仓管理] 多头持仓已达上限{long_position}手，不开新仓")
            else:
                # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
                should_open = False

                if long_position == 0:
                    # 没有多头持仓，直接开仓
                    should_open = True
                    logger.info(f"✅ [加仓控制] 无多头持仓，允许开仓")
                else:
                    # 已有多头持仓，检查是否亏损达到阈值
                    long_pnl_pct = (current_price - long_price) / long_price
                    if long_pnl_pct <= -self.add_loss_pct:
                        # 亏损达到阈值，允许加仓
                        should_open = True
                        logger.info(f"✅ [加仓控制] 多头亏损{long_pnl_pct*100:.2f}%（阈值{-self.add_loss_pct*100:.2f}%），允许加仓")
                    else:
                        # 亏损未达到阈值，不加仓
                        logger.warning(f"⚠️ [加仓控制] 多头盈亏{long_pnl_pct*100:.2f}%，未达到加仓阈值{-self.add_loss_pct*100:.2f}%，不加仓")
                        logger.info(f"📊 [加仓控制] 当前价格{current_price:.2f}，持仓均价{long_price:.2f}，价格差{current_price-long_price:.2f}")

                if should_open:
                    # 开新多仓
                    if need_delay:
                        time.sleep(0.1)
                    logger.info(f"🚀 [持仓管理] 金叉信号：开多仓{trade_volume}手")
                    self.buy(current_price, trade_volume, stop=False)

        # 🎯 新策略逻辑：死叉信号
        elif action == 'SELL':
            logger.info(f"💀 [持仓管理] 死叉信号处理开始")

            # 1. 检查多头持仓 - 盈利则平仓
            if long_position > 0:
                long_pnl = (current_price - long_price) * long_position  # 多头盈亏
                logger.info(f"🔍 [持仓管理] 多头持仓检查: 持仓={long_position}手, 均价={long_price:.2f}, 当前价={current_price:.2f}, 盈亏={long_pnl:.2f}元")
                if long_pnl > 0:  # 多头盈利
                    logger.info(f"✅ [持仓管理] 多头盈利{long_pnl:.2f}元，平多{long_position}手")
                    self._smart_close_position('LONG', long_position, current_price)
                    need_delay = True
                else:
                    logger.info(f"📉 [持仓管理] 多头亏损{abs(long_pnl):.2f}元，保留多头{long_position}手")
            else:
                logger.info(f"🔍 [持仓管理] 无多头持仓，跳过平多检查")

            # 2. 检查空头持仓限制（最多2手）
            if short_position >= 2:
                logger.warning(f"⚠️ [持仓管理] 空头持仓已达上限{short_position}手，不开新仓")
            else:
                # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
                should_open = False

                if short_position == 0:
                    # 没有空头持仓，直接开仓
                    should_open = True
                    logger.info(f"✅ [加仓控制] 无空头持仓，允许开仓")
                else:
                    # 已有空头持仓，检查是否亏损达到阈值
                    short_pnl_pct = (short_price - current_price) / short_price
                    if short_pnl_pct <= -self.add_loss_pct:
                        # 亏损达到阈值，允许加仓
                        should_open = True
                        logger.info(f"✅ [加仓控制] 空头亏损{short_pnl_pct*100:.2f}%（阈值{-self.add_loss_pct*100:.2f}%），允许加仓")
                    else:
                        # 亏损未达到阈值，不加仓
                        logger.warning(f"⚠️ [加仓控制] 空头盈亏{short_pnl_pct*100:.2f}%，未达到加仓阈值{-self.add_loss_pct*100:.2f}%，不加仓")
                        logger.info(f"📊 [加仓控制] 当前价格{current_price:.2f}，持仓均价{short_price:.2f}，价格差{current_price-short_price:.2f}")

                if should_open:
                    # 开新空仓
                    if need_delay:
                        time.sleep(0.1)
                    logger.info(f"🚀 [持仓管理] 死叉信号：开空仓{trade_volume}手")
                    self.short(current_price, trade_volume, stop=False)

        # 更新信号时间
        self.last_signal_time = time.time()
        logger.info(f"✅ [持仓管理] {action}信号处理完成")

    def _pre_trade_safety_check(self, action: str) -> bool:
        """🔧 交易前安全检查 - 智能持仓风控模块"""
        real_position_info = self._query_real_position()
        if real_position_info is None:
            logger.warning(f"⚠️ [SHFE策略] 无法查询持仓，停止交易")
            return False

        # 获取净持仓
        real_position = real_position_info.get("net_position", 0)

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

    def on_tick_impl(self, tick: TickData):
        """具体的tick处理实现 - 必需的抽象方法"""
        # 🛡️ 基于Tick的实时风控检查
        if self.pos != 0:
            self._check_risk_control(tick.last_price)

        # 其他基于tick的快速处理逻辑可以在这里添加
        # 主要的技术分析逻辑仍在on_bar_impl中处理

    def on_trade_impl(self, trade):
        """具体的成交处理实现"""
        logger.info(f"🔥 [SHFE策略] 成交确认: {trade.direction} {trade.volume}手 @ {trade.price}")

        # 🎯 记录成交信息
        self._log_trade_info(trade)

        # 成交后异步更新持仓缓存
        try:
            import threading

            def update_cache():
                real_position_info = self._query_real_position()
                if real_position_info is not None:
                    real_position = real_position_info.get("net_position", 0)
                    old_cache = self.cached_position
                    self.cached_position = real_position
                    self.last_position_update = time.time()
                    logger.info(f"🔧 [SHFE策略] 成交后缓存更新: {old_cache} → {real_position}")

            # 在后台线程中更新缓存
            threading.Thread(target=update_cache, daemon=True).start()

        except Exception as e:
            logger.error(f"⚠️ [SHFE策略] 持仓缓存更新失败: {e}")

    def _log_trade_info(self, trade):
        """📊 记录成交信息"""
        logger.info(f"💰 [成交记录] {trade.direction.value} {trade.offset} {trade.volume}手 @ {trade.price:.2f}")
        logger.info(f"💰 [持仓变化] 持仓更新为: {self.pos}手")

    def _log_indicators_to_csv(self, bar, analysis):
        """📊 记录指标数据到CSV文件"""
        import csv
        import os
        from datetime import datetime

        try:
            # 创建logs目录
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # CSV文件路径 - 按日期分文件
            today = datetime.now().strftime('%Y%m%d')
            csv_file = f"{log_dir}/indicators_{self.strategy_name}_{self.symbol}_{today}.csv"

            # 检查文件是否存在，如果不存在则创建并写入表头
            file_exists = os.path.exists(csv_file)

            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # 写入表头
                if not file_exists:
                    writer.writerow([
                        'DateTime', 'Open', 'High', 'Low', 'Close', 'Volume',
                        'EMA5', 'EMA20', 'RSI', 'EMA5_EMA20_Diff', 'Cross_Signal'
                    ])

                # 计算EMA差值
                ema_diff = self.current_ma5 - self.current_ma20

                # 获取交叉信号 - 使用已有的检测结果，避免重复调用
                cross_signal = analysis.get("cross_signal", "NONE")

                # 写入数据
                writer.writerow([
                    bar.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    f"{bar.open_price:.2f}",
                    f"{bar.high_price:.2f}",
                    f"{bar.low_price:.2f}",
                    f"{bar.close_price:.2f}",
                    bar.volume,
                    f"{self.current_ma5:.2f}",
                    f"{self.current_ma20:.2f}",
                    f"{self.current_rsi:.2f}",
                    f"{ema_diff:.2f}",
                    cross_signal
                ])

            # 每10个K线输出一次指标对比
            if hasattr(self, '_csv_log_count'):
                self._csv_log_count += 1
            else:
                self._csv_log_count = 1

            if self._csv_log_count % 10 == 0:
                logger.info(f"📊 [EMA指标] EMA5:{self.current_ma5:.2f} | "
                           f"EMA20:{self.current_ma20:.2f} | RSI:{self.current_rsi:.2f}")

        except Exception as e:
            logger.error(f"⚠️ [指标记录] CSV记录失败: {e}")

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
        "add_loss_pct": {
            "type": "float",
            "default": 0.001,
            "description": "加仓亏损阈值"
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
