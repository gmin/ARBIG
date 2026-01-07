"""
MA-RSI组合策略 - 黄金期货专业交易策略

使用EMA5/EMA20双均线 + RSI14指标组合，适用于上期所黄金期货。
详细设计文档见：MaRsiComboStrategy_design.md
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
    
    核心逻辑：EMA5/EMA20金叉死叉 + RSI确认 + 两阶段时间确认机制
    详细设计：见 MaRsiComboStrategy_design.md
    """
    
    # ==================== 策略参数配置 ====================
    
    # 技术指标参数
    ma_short = 5          # 短期均线周期：5周期EMA，捕捉短期趋势变化
    ma_long = 20          # 长期均线周期：20周期EMA，确认主要趋势方向
    rsi_period = 14       # RSI计算周期：标准14周期，平衡敏感性和稳定性
    rsi_overbought = 70   # RSI超买阈值：>70视为超买，谨慎做多
    rsi_oversold = 30     # RSI超卖阈值：<30视为超卖，谨慎做空
    
    # 交叉检测参数 (2025-12-30 改进：时间确认机制)
    cross_confirm_bars = 2        # 交叉确认所需K线数：检测到交叉后等待2根K线确认
    min_cross_distance = 0.0001   # 最小交叉幅度：0.01%（极低阈值，主要靠时间确认过滤假突破）
    
    # 风险控制参数
    stop_loss_pct = 0.006  # 止损百分比：0.6%固定止损，控制单笔损失
    take_profit_pct = 0.008 # 止盈百分比：0.8%目标止盈，锁定利润
    
    # 加仓控制参数（2025-01-03 改进：ATR动态阈值）
    atr_period = 14                 # ATR 计算周期
    add_loss_atr_multiplier = 1.5   # 加仓阈值 = ATR * 此倍数（亏损超过1.5倍ATR才允许加仓）

    # 交易执行参数
    trade_volume = 1      # 基础交易手数：每次交易的标准手数
    max_position = 2      # 最大持仓限制：单一方向不超过2手，控制整体风险
    
    # 策略变量
    last_signal_time = 0  # 上次信号时间

    # 🎯 性能优化：缓存当前K线的指标计算结果
    current_ma5 = 0.0     # 当前MA5值
    current_ma20 = 0.0    # 当前MA20值
    current_rsi = 0.0     # 当前RSI值
    current_atr = 0.0     # 当前ATR值（用于动态加仓阈值）

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
        self.trade_volume = setting.get('trade_volume', 1)
        self.max_position = setting.get('max_position', 2)
        
        # 加仓控制参数（2025-01-03 改进：ATR动态阈值）
        self.atr_period = setting.get('atr_period', 14)
        self.add_loss_atr_multiplier = setting.get('add_loss_atr_multiplier', 1.5)
        
        # 交叉检测参数 (2025-12-29 新增)
        self.min_cross_distance = setting.get('min_cross_distance', 0.0001)
        
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
        
        # 🔧 交叉确认机制 (2025-12-30 新增)
        self.cross_confirm_bars = setting.get('cross_confirm_bars', 2)  # 确认所需K线数
        self.pending_cross_type = None     # 待确认的交叉类型："GOLDEN" / "DEATH" / None
        self.pending_cross_bar_count = 0   # 等待确认的K线计数
        self.pending_cross_diff = 0.0      # 交叉时的MA5-MA20差值（用于判断是否扩大）
        self.pending_cross_price = 0.0     # 交叉时的收盘价（用于极值确认）
        self.pending_cross_extreme = 0.0   # 确认期间的极值（金叉记录最高价，死叉记录最低价）
        self.current_cross_signal = "NONE" # 当前K线的交叉信号缓存（避免重复调用）

        # 🎯 真实开仓均价管理 (2026-01-06 新增)
        # CTP返回的持仓价格是结算价，不是真实开仓均价，需要自己记录
        self.real_positions = {}  # {direction: {"volume": int, "avg_price": float, "total_cost": float}}
        self._real_positions_file = f"data/real_positions_{self.strategy_name}_{self.symbol}.json"
        self._load_real_positions()  # 启动时从文件加载

        logger.info(f"✅ {self.strategy_name} 初始化完成 | 品种:{self.symbol} | EMA{self.ma_short}/{self.ma_long} | RSI{self.rsi_period}")
        logger.info(f"   风控:止损{self.stop_loss_pct*100:.1f}%/止盈{self.take_profit_pct*100:.1f}% | 加仓:ATR×{self.add_loss_atr_multiplier} | 最大持仓:{self.max_position}手")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("MA-RSI组合策略初始化")

    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 MA-RSI组合策略已启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ MA-RSI组合策略已停止")
        self._save_real_positions()  # 停止时保存真实持仓
    
    # ==================== 真实开仓均价管理 ====================
    
    def _load_real_positions(self):
        """从文件加载真实开仓均价"""
        import json
        import os
        
        try:
            # 确保data目录存在
            os.makedirs("data", exist_ok=True)
            
            if os.path.exists(self._real_positions_file):
                with open(self._real_positions_file, 'r', encoding='utf-8') as f:
                    self.real_positions = json.load(f)
                logger.debug(f"[均价] 加载: {self.real_positions}")
            else:
                self.real_positions = {}
                logger.debug(f"[均价] 初始化为空")
        except Exception as e:
            logger.error(f"❌ [真实均价] 加载失败: {e}")
            self.real_positions = {}
    
    def _save_real_positions(self):
        """保存真实开仓均价到文件"""
        import json
        import os
        
        try:
            os.makedirs("data", exist_ok=True)
            with open(self._real_positions_file, 'w', encoding='utf-8') as f:
                json.dump(self.real_positions, f, indent=2, ensure_ascii=False)
            logger.debug(f"[均价] 已保存: {self.real_positions}")
        except Exception as e:
            logger.error(f"❌ [真实均价] 保存失败: {e}")
    
    def _update_real_position(self, direction: str, offset: str, price: float, volume: int):
        """更新真实开仓均价
        
        Args:
            direction: 方向 "long" 或 "short"
            offset: 开平 "open" 或 "close"
            price: 成交价格
            volume: 成交数量
        """
        key = direction.lower()
        
        if offset.lower() in ["open", "开"]:
            # 开仓：计算新均价
            if key not in self.real_positions:
                self.real_positions[key] = {"volume": 0, "avg_price": 0.0, "total_cost": 0.0}
            
            old_volume = self.real_positions[key]["volume"]
            old_cost = self.real_positions[key]["total_cost"]
            
            new_volume = old_volume + volume
            new_cost = old_cost + price * volume
            new_avg_price = new_cost / new_volume if new_volume > 0 else 0
            
            self.real_positions[key] = {
                "volume": new_volume,
                "avg_price": round(new_avg_price, 4),
                "total_cost": round(new_cost, 4),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"📈 [均价] {key}开仓: {old_volume}→{new_volume}手@{new_avg_price:.2f}")
            
        else:
            # 平仓：减少持仓量，均价不变
            if key in self.real_positions:
                old_volume = self.real_positions[key]["volume"]
                old_avg_price = self.real_positions[key]["avg_price"]
                
                new_volume = max(0, old_volume - volume)
                
                if new_volume == 0:
                    # 全平，清除记录
                    del self.real_positions[key]
                    logger.info(f"📉 [均价] {key}全平: 清除记录")
                else:
                    self.real_positions[key]["volume"] = new_volume
                    self.real_positions[key]["total_cost"] = new_volume * old_avg_price
                    self.real_positions[key]["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logger.debug(f"[均价] {key}平仓: {old_volume}→{new_volume}手")
        
        # 每次更新后立即保存
        self._save_real_positions()
    
    def get_real_avg_price(self, direction: str) -> float:
        """获取真实开仓均价
        
        Args:
            direction: 方向 "long" 或 "short"
        Returns:
            真实开仓均价，无持仓返回0
        """
        key = direction.lower()
        if key in self.real_positions:
            return self.real_positions[key].get("avg_price", 0.0)
        return 0.0
    
    def get_real_volume(self, direction: str) -> int:
        """获取真实持仓量
        
        Args:
            direction: 方向 "long" 或 "short"
        Returns:
            真实持仓量，无持仓返回0
        """
        key = direction.lower()
        if key in self.real_positions:
            return self.real_positions[key].get("volume", 0)
        return 0
        
    # 🎯 MaRsiComboStrategy采用双层架构：
    # K线级别：技术分析和信号生成 (on_bar_impl)
    # Tick级别：实时风控和止盈止损 (on_tick_impl)
        
    def on_bar_impl(self, bar: BarData):
        """🎯 K线数据处理 - 技术分析策略的核心入口

        在基类ARBIGCtaTemplate的on_bar调用链中执行
        """
        logger.debug(f"[K线] {bar.symbol} {bar.datetime} 价格:{bar.close_price:.2f}")

        if not self.trading:
            logger.warning(f"⚠️ 策略未启用交易")
            return

        # 🎯 标准架构：策略引擎已在源头控制交易时间 → 策略更新ArrayManager → 计算指标 → 生成信号
        self.am.update_bar(bar)

        # 确保有足够的数据
        if not self.am.inited:
            logger.debug(f"🔧 ArrayManager 初始化中 ({self.am.count}/20)")
            return

        # 🎯 性能优化：每个K线只计算一次指标，后续复用
        self.current_ma5 = self.am.ema(self.ma_short)   # 改为EMA5
        self.current_ma20 = self.am.ema(self.ma_long)   # 改为EMA20
        self.current_rsi = self.am.rsi(self.rsi_period)
        self.current_atr = self.am.atr(self.atr_period) # ATR（用于动态加仓阈值）

        # 🔧 2025-12-30 修复：MA历史必须在调用 _detect_ma_cross 之前更新
        self.ma5_history.append(self.current_ma5)
        self.ma20_history.append(self.current_ma20)
        if len(self.ma5_history) > self.max_history_length:
            self.ma5_history.pop(0)
        if len(self.ma20_history) > self.max_history_length:
            self.ma20_history.pop(0)

        # 📝 每个K线只调用一次 _detect_ma_cross，结果缓存供CSV和交易信号使用
        self.current_cross_signal = self._detect_ma_cross(bar.close_price, bar.high_price, bar.low_price)
        
        csv_analysis = {
            "ma_short": self.current_ma5,
            "ma_long": self.current_ma20,
            "rsi": self.current_rsi,
            "cross_signal": self.current_cross_signal,
            "current_price": bar.close_price
        }

        self._log_indicators_to_csv(bar, csv_analysis)

        # 🛡️ 实时风控检查在on_tick_impl中处理，K线级别专注信号生成

        # 检查信号间隔（避免频繁交易）
        current_time = time.time()
        time_since_last_signal = current_time - self.last_signal_time
        # 2025-12-29 修复：使用 <= 避免边界条件问题（参考 EnhancedMaRsiComboStrategy）
        if time_since_last_signal <= self.min_signal_interval:
            logger.debug(f"[策略服务-GoldMaRsi] ⏱️ 信号间隔限制: {time_since_last_signal:.2f}s < {self.min_signal_interval}s，跳过处理")
            return

        logger.debug(f"✅ 准备生成交易信号")
        # 🎯 应用优化的信号生成机制
        self._generate_trading_signal(bar)

    def _generate_trading_signal(self, bar: BarData):
        """🎯 生成交易信号 - 分离信号生成和执行"""
        logger.debug(f"🔍 开始生成信号: {bar.symbol} {bar.datetime} @{bar.close_price:.2f}")

        # 🚨 信号生成前置检查
        if self.signal_lock:
            logger.debug(f"🔒 信号生成锁定中")
            return

        # 🎯 核心逻辑：分析市场条件（为交易决策单独分析）
        signal_analysis = self._analyze_market_conditions(bar)

        # 🎯 生成交易决策
        signal_decision = self._analyze_trading_opportunity(signal_analysis, bar.close_price)

        # 🎯 发送信号给处理模块
        if signal_decision['action'] in ['BUY', 'SELL']:
            # 📊 记录交易信号时的完整指标数据（用于复盘分析）
            self._log_trading_signal_indicators(signal_analysis, signal_decision, bar.close_price)
            logger.info(f"🎯 [信号] {signal_decision['action']} - {signal_decision['reason']}")
            self._process_trading_signal(signal_decision, bar.close_price)
        else:
            logger.debug(f"[无信号] {signal_decision['reason']}")

    def _analyze_market_conditions(self, bar: BarData) -> dict:
        """🎯 分析市场条件 - 基于技术指标
        
        2025-12-30 修复：MA历史更新和交叉检测已移到 on_bar_impl，
        这里只使用缓存的结果，避免重复调用导致计数错误。
        """
        # 🔧 确保有足够的数据进行计算
        if not self.am.inited:
            return {
                "ma_short": 0,
                "ma_long": 0,
                "rsi": 50,
                "trend_signal": "NEUTRAL",
                "rsi_signal": "NEUTRAL",
                "cross_signal": "NONE",
                "current_price": bar.close_price
            }

        # 🎯 使用缓存的技术指标和交叉信号（性能优化 + 避免重复调用）
        ma_short = self.current_ma5
        ma_long = self.current_ma20
        rsi = self.current_rsi
        cross_signal = self.current_cross_signal  # 使用 on_bar_impl 中已检测的结果

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
            "cross_signal": cross_signal,
            "current_price": bar.close_price
        }

    def _detect_ma_cross(self, current_price: float, high_price: float, low_price: float) -> str:
        """🎯 检测MA5和MA20的金叉死叉 - 两阶段时间确认机制
        
        2025-12-30 重大改进：
        - 第一阶段：检测到交叉发生，进入"待确认"状态
        - 第二阶段：等待N根K线，确认MA5仍在正确一侧且差值稳定/扩大
        - 价格确认：使用极值确认（金叉期间最高价>交叉价，死叉期间最低价<交叉价）
        - 假突破：MA5回撤到MA20另一侧，取消待确认状态
        
        这种机制可以有效过滤小幅度假突破，同时不会错过真正的趋势转折。
        """
        if len(self.ma5_history) < 2 or len(self.ma20_history) < 2:
            return "NONE"  # 数据不足，需要至少2个点进行确认

        # 获取最近2个时刻的MA值
        ma5_values = self.ma5_history[-2:]  # [前1, 当前]
        ma20_values = self.ma20_history[-2:]
        current_diff = ma5_values[1] - ma20_values[1]  # 当前MA5-MA20差值

        # 🔍 调试日志
        logger.debug(f"🔍 [交叉检测] MA5={ma5_values[1]:.2f}, MA20={ma20_values[1]:.2f}, 差值={current_diff:.2f}")
        if self.pending_cross_type:
            logger.debug(f"🔍 [待确认] 类型={self.pending_cross_type}, 已等待={self.pending_cross_bar_count}根K线, 初始差值={self.pending_cross_diff:.2f}")

        # ==================== 第二阶段：检查待确认的交叉 ====================
        if self.pending_cross_type:
            self.pending_cross_bar_count += 1
            
            # 更新极值：金叉记录最高价，死叉记录最低价
            if self.pending_cross_type == "GOLDEN":
                self.pending_cross_extreme = max(self.pending_cross_extreme, high_price)
            else:  # DEATH
                self.pending_cross_extreme = min(self.pending_cross_extreme, low_price)
            
            # 检查是否假突破（MA5回撤到错误一侧）
            if self.pending_cross_type == "GOLDEN" and current_diff <= 0:
                logger.info(f"❌ [假突破] 金叉失败：MA5已回撤到MA20下方，差值={current_diff:.2f}")
                self._clear_pending_cross()
                return "NONE"
            elif self.pending_cross_type == "DEATH" and current_diff >= 0:
                logger.info(f"❌ [假突破] 死叉失败：MA5已回撤到MA20上方，差值={current_diff:.2f}")
                self._clear_pending_cross()
                return "NONE"
            
            # 检查是否达到确认K线数
            if self.pending_cross_bar_count >= self.cross_confirm_bars:
                # 确认条件1：差值稳定或扩大（没有回缩）
                diff_maintained = abs(current_diff) >= abs(self.pending_cross_diff) * 0.5  # 差值保持50%以上
                
                # 确认条件2：极值确认（金叉期间最高价 > 交叉价，死叉期间最低价 < 交叉价）
                if self.pending_cross_type == "GOLDEN":
                    price_confirmation = self.pending_cross_extreme > self.pending_cross_price
                else:  # DEATH
                    price_confirmation = self.pending_cross_extreme < self.pending_cross_price
                
                if diff_maintained and price_confirmation:
                    cross_type = self.pending_cross_type
                    extreme_label = "最高" if cross_type == "GOLDEN" else "最低"
                    logger.info(f"✅ [{cross_type}确认] {self.pending_cross_bar_count}K确认 | 差值:{self.pending_cross_diff:.2f}→{current_diff:.2f} | 交叉价:{self.pending_cross_price:.2f} | {extreme_label}:{self.pending_cross_extreme:.2f}")
                    self._clear_pending_cross()
                    return f"{cross_type}_CROSS"
                else:
                    # 未通过确认
                    reason = []
                    if not diff_maintained:
                        reason.append(f"差值回缩过多({abs(current_diff):.2f}<{abs(self.pending_cross_diff)*0.5:.2f})")
                    if not price_confirmation:
                        if self.pending_cross_type == "GOLDEN":
                            reason.append(f"极值未确认(最高{self.pending_cross_extreme:.2f}≤交叉价{self.pending_cross_price:.2f})")
                        else:
                            reason.append(f"极值未确认(最低{self.pending_cross_extreme:.2f}≥交叉价{self.pending_cross_price:.2f})")
                    logger.info(f"❌ [交叉未确认] {self.pending_cross_type}未通过确认：{', '.join(reason)}")
                    self._clear_pending_cross()
                    return "NONE"
            else:
                # 还在等待中，差值在扩大是好迹象
                if abs(current_diff) > abs(self.pending_cross_diff):
                    logger.debug(f"📈 [等待确认] {self.pending_cross_type}差值扩大：{self.pending_cross_diff:.2f} → {current_diff:.2f}")
                return "NONE"  # 继续等待

        # ==================== 第一阶段：检测新的交叉 ====================
        
        # 金叉检测：MA5从下方穿越MA20
        if (ma5_values[0] <= ma20_values[0] and  # 前1时刻：MA5 <= MA20
            ma5_values[1] > ma20_values[1]):     # 当前时刻：MA5 > MA20
            
            # 计算交叉幅度
            diff_before = ma5_values[0] - ma20_values[0]
            diff_after = ma5_values[1] - ma20_values[1]
            cross_distance = abs(diff_after - diff_before) / ma20_values[1] if ma20_values[1] > 0 else 0
            
            if cross_distance >= self.min_cross_distance:
                # 进入待确认状态
                self.pending_cross_type = "GOLDEN"
                self.pending_cross_bar_count = 0
                self.pending_cross_diff = diff_after
                self.pending_cross_price = current_price    # 记录交叉时收盘价
                self.pending_cross_extreme = high_price     # 金叉初始极值=当前最高价
                logger.info(f"🔔 [金叉检测] MA5({ma5_values[1]:.2f})>MA20({ma20_values[1]:.2f}) 幅度:{cross_distance*100:.3f}% 差值:{diff_after:.2f} | 进入{self.cross_confirm_bars}K确认")
            else:
                logger.debug(f"🔍 [金叉检测] 穿越幅度不足：{cross_distance*100:.3f}% < {self.min_cross_distance*100:.3f}%")

        # 死叉检测：MA5从上方穿越MA20
        elif (ma5_values[0] >= ma20_values[0] and  # 前1时刻：MA5 >= MA20
              ma5_values[1] < ma20_values[1]):     # 当前时刻：MA5 < MA20
            
            # 计算交叉幅度
            diff_before = ma5_values[0] - ma20_values[0]
            diff_after = ma5_values[1] - ma20_values[1]
            cross_distance = abs(diff_after - diff_before) / ma20_values[1] if ma20_values[1] > 0 else 0
            
            if cross_distance >= self.min_cross_distance:
                # 进入待确认状态
                self.pending_cross_type = "DEATH"
                self.pending_cross_bar_count = 0
                self.pending_cross_diff = diff_after
                self.pending_cross_price = current_price    # 记录交叉时收盘价
                self.pending_cross_extreme = low_price      # 死叉初始极值=当前最低价
                logger.info(f"🔔 [死叉检测] MA5({ma5_values[1]:.2f})<MA20({ma20_values[1]:.2f}) 幅度:{cross_distance*100:.3f}% 差值:{diff_after:.2f} | 进入{self.cross_confirm_bars}K确认")
            else:
                logger.debug(f"🔍 [死叉检测] 穿越幅度不足：{cross_distance*100:.3f}% < {self.min_cross_distance*100:.3f}%")

        return "NONE"
    
    def _clear_pending_cross(self):
        """清除待确认交叉状态"""
        self.pending_cross_type = None
        self.pending_cross_bar_count = 0
        self.pending_cross_diff = 0.0
        self.pending_cross_price = 0.0
        self.pending_cross_extreme = 0.0

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

        # 📊 交易信号记录（精简版）
        logger.info(f"🎯 [交易信号] {decision['action']} | {decision['reason']} | 价格:{current_price:.2f} | 持仓:{self.pos}")
        logger.info(f"🎯 [指标] MA5:{ma5:.2f} MA20:{ma20:.2f} 差值:{ma5-ma20:+.2f}({(ma5-ma20)/ma20*100:+.2f}%) | RSI:{rsi:.1f} | {cross_signal}")

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

        # 🎯 获取真实开仓均价（2026-01-06 改进：使用自己记录的真实均价，而非CTP结算价）
        try:
            real_position = self._query_real_position()
            if real_position is None:
                logger.warning("⚠️ [风控] 无法获取持仓信息，跳过风控检查")
                return

            # 获取持仓成本价（根据净持仓方向选择对应价格）
            net_position = real_position.get("net_position", 0)
            if net_position > 0:
                # 净多头持仓，使用真实开仓均价
                entry_price = self.get_real_avg_price("long")
                ctp_price = real_position.get("long_price", 0)
                if entry_price <= 0:
                    entry_price = ctp_price  # 兜底：如果没有记录，使用CTP价格
                    logger.warning(f"⚠️ [风控] 无真实均价记录，使用CTP价格: {ctp_price:.2f}")
            elif net_position < 0:
                # 净空头持仓，使用真实开仓均价
                entry_price = self.get_real_avg_price("short")
                ctp_price = real_position.get("short_price", 0)
                if entry_price <= 0:
                    entry_price = ctp_price  # 兜底：如果没有记录，使用CTP价格
                    logger.warning(f"⚠️ [风控] 无真实均价记录，使用CTP价格: {ctp_price:.2f}")
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

            # 计算盈亏比例 - 🔧 统一使用 net_position 判断方向，避免不同步问题
            if net_position > 0:  # 多头持仓
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # 空头持仓
                pnl_pct = (entry_price - current_price) / entry_price

            logger.debug(f"[风控] 持仓:{net_position}手 入场:{entry_price:.2f} 现价:{current_price:.2f} | 盈亏:{pnl_pct*100:.2f}%")

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

        # 📊 风控触发记录
        logger.info(f"🛑 [风控触发] {reason} | {self.pos}手 | 入场:{entry_price:.2f} → 平仓:{price:.2f} | 盈亏:{pnl_amount:+.2f}元({pnl_pct*100:+.2f}%)")

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

                    logger.debug(f"[持仓] 多:{long_position}手(今{long_today}昨{long_yesterday}) 空:{short_position}手(今{short_today}昨{short_yesterday})")

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

            logger.info(f"📋 [平仓] 拆分: 昨仓{yesterday_volume}手 + 今仓{today_volume}手")
            # 先平昨仓（更稳定）
            if yesterday_volume > 0:
                if direction == 'LONG':
                    self.sell(price, yesterday_volume, stop=False)
                else:
                    self.cover(price, yesterday_volume, stop=False)
                time.sleep(0.1)  # 短暂延迟，避免订单冲突
            # 再平今仓
            if today_volume > 0:
                if direction == 'LONG':
                    self.sell(price, today_volume, stop=False)
                else:
                    self.cover(price, today_volume, stop=False)
        else:
            # 不需要拆分
            if direction == 'LONG':
                self.sell(price, volume, stop=False)
            else:
                self.cover(price, volume, stop=False)

    def _process_trading_signal(self, signal_decision: dict, current_price: float):
        """🔧 信号处理模块 - 新策略：盈利平仓+信号开仓
        
        2025-12-29 优化：增加重复开仓检查，避免在已有同方向持仓时重复开仓
        """
        action = signal_decision['action']

        logger.info(f"🔧 [持仓管理] {action}信号 | 价格:{current_price:.2f}")

        # 🔧 查询真实持仓信息（包含开仓均价）
        position_info = self._query_real_position()
        if position_info is None:
            logger.warning(f"⚠️ [持仓管理] 无法查询持仓信息，停止交易")
            return

        long_position = position_info.get("long_position", 0)
        short_position = position_info.get("short_position", 0)
        
        # 🎯 2026-01-06 改进：使用真实开仓均价，而非CTP结算价
        ctp_long_price = position_info.get("long_price", 0)
        ctp_short_price = position_info.get("short_price", 0)
        long_price = self.get_real_avg_price("long")
        short_price = self.get_real_avg_price("short")
        
        # 兜底：如果没有真实均价记录，使用CTP价格
        if long_price <= 0 and long_position > 0:
            long_price = ctp_long_price
            logger.warning(f"⚠️ [持仓管理] 无多头真实均价记录，使用CTP价格: {ctp_long_price:.2f}")
        if short_price <= 0 and short_position > 0:
            short_price = ctp_short_price
            logger.warning(f"⚠️ [持仓管理] 无空头真实均价记录，使用CTP价格: {ctp_short_price:.2f}")

        logger.info(f"🔍 [持仓] 多:{long_position}手@{long_price:.2f} 空:{short_position}手@{short_price:.2f} | 决策:{signal_decision['action']}")

        # 计算交易数量
        trade_volume = self._calculate_position_size(signal_decision.get('strength', 1.0))

        # 标记是否需要延迟（如果有平仓操作）
        need_delay = False

        # 🎯 新策略逻辑：金叉信号
        if action == 'BUY':

            # 1. 检查空头持仓 - 盈利则平仓
            if short_position > 0:
                short_pnl = (short_price - current_price) * short_position  # 空头盈亏
                if short_pnl > 0:  # 空头盈利
                    logger.info(f"✅ [平仓] 空头盈利{short_pnl:.2f}元 → 平仓{short_position}手")
                    self._smart_close_position('SHORT', short_position, current_price)
                    need_delay = True
                else:
                    logger.info(f"🔒 [保留] 空头亏损{abs(short_pnl):.2f}元，等待ATR加仓")

            # 2. 检查多头持仓限制
            if long_position >= self.max_position:
                logger.warning(f"⚠️ [持仓管理] 多头持仓已达上限{long_position}/{self.max_position}手，不开新仓")
            else:
                # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
                should_open = False

                if long_position == 0:
                    # 没有多头持仓，直接开仓
                    should_open = True
                    logger.info(f"✅ [加仓控制] 无多头持仓，允许开仓")
                else:
                    # 已有多头持仓，检查是否亏损达到 ATR 动态阈值
                    # 2025-01-03 改进：使用 ATR 动态阈值，而非固定百分比
                    price_loss = long_price - current_price  # 多头亏损金额（正数表示亏损）
                    atr_threshold = self.current_atr * self.add_loss_atr_multiplier
                    
                    if price_loss >= atr_threshold:
                        # 亏损达到 ATR 阈值，允许加仓
                        should_open = True
                        logger.info(f"✅ [加仓控制-ATR] 多头亏损{price_loss:.2f}元 >= {self.add_loss_atr_multiplier}倍ATR({atr_threshold:.2f}元)，允许加仓")
                    else:
                        # 亏损未达到阈值，不加仓
                        logger.warning(f"⚠️ [加仓控制] 多头亏损{price_loss:.2f}元 < ATR阈值({atr_threshold:.2f}元)，不加仓")

                if should_open:
                    # 开新多仓
                    if need_delay:
                        time.sleep(0.1)
                    logger.info(f"🚀 [开仓] 金叉开多{trade_volume}手")
                    self.buy(current_price, trade_volume, stop=False)

        # 🎯 新策略逻辑：死叉信号
        elif action == 'SELL':

            # 1. 检查多头持仓 - 盈利则平仓
            if long_position > 0:
                long_pnl = (current_price - long_price) * long_position  # 多头盈亏
                logger.info(f"🔍 [持仓管理] 多头持仓检查: 持仓={long_position}手, 均价={long_price:.2f}, 当前价={current_price:.2f}, 盈亏={long_pnl:.2f}元")
                if long_pnl > 0:  # 多头盈利
                    logger.info(f"✅ [平仓] 多头盈利{long_pnl:.2f}元 → 平仓{long_position}手")
                    self._smart_close_position('LONG', long_position, current_price)
                    need_delay = True
                else:
                    logger.info(f"🔒 [保留] 多头亏损{abs(long_pnl):.2f}元，等待ATR加仓")
            else:
                logger.info(f"🔍 [持仓管理] 无多头持仓，跳过平多检查")

            # 2. 检查空头持仓限制
            if short_position >= self.max_position:
                logger.warning(f"⚠️ [持仓管理] 空头持仓已达上限{short_position}/{self.max_position}手，不开新仓")
            else:
                # 🎯 加仓控制：只在没有持仓或亏损达到阈值时开仓
                should_open = False

                if short_position == 0:
                    # 没有空头持仓，直接开仓
                    should_open = True
                    logger.info(f"✅ [加仓控制] 无空头持仓，允许开仓")
                else:
                    # 已有空头持仓，检查是否亏损达到 ATR 动态阈值
                    # 2025-01-03 改进：使用 ATR 动态阈值，而非固定百分比
                    price_loss = current_price - short_price  # 空头亏损金额（正数表示亏损）
                    atr_threshold = self.current_atr * self.add_loss_atr_multiplier
                    
                    if price_loss >= atr_threshold:
                        # 亏损达到 ATR 阈值，允许加仓
                        should_open = True
                        logger.info(f"✅ [加仓控制-ATR] 空头亏损{price_loss:.2f}元 >= {self.add_loss_atr_multiplier}倍ATR({atr_threshold:.2f}元)，允许加仓")
                    else:
                        # 亏损未达到阈值，不加仓
                        logger.warning(f"⚠️ [加仓控制] 空头亏损{price_loss:.2f}元 < ATR阈值({atr_threshold:.2f}元)，不加仓")

                if should_open:
                    # 开新空仓
                    if need_delay:
                        time.sleep(0.1)
                    logger.info(f"🚀 [开仓] 死叉开空{trade_volume}手")
                    self.short(current_price, trade_volume, stop=False)

        # 更新信号时间
        self.last_signal_time = time.time()
        logger.info(f"✅ [持仓管理] {action}信号处理完成")

    def on_tick_impl(self, tick: TickData):
        """具体的tick处理实现 - 必需的抽象方法"""
        # 🛡️ 基于Tick的实时风控检查
        if self.pos != 0:
            self._check_risk_control(tick.last_price)

        # 其他基于tick的快速处理逻辑可以在这里添加
        # 主要的技术分析逻辑仍在on_bar_impl中处理

    def on_trade_impl(self, trade):
        """具体的成交处理实现"""
        logger.info(f"🔥 [成交] {trade.direction} {trade.volume}手@{trade.price:.2f}")

        # 🎯 记录成交信息
        self._log_trade_info(trade)
        
        # 🎯 更新真实开仓均价 (2026-01-06 新增)
        try:
            # 解析方向和开平
            direction_val = str(trade.direction.value).lower() if hasattr(trade.direction, 'value') else str(trade.direction).lower()
            offset_val = str(trade.offset.value).lower() if hasattr(trade.offset, 'value') else str(trade.offset).lower()
            
            # 判断持仓方向：买开=long，卖开=short，买平=减short，卖平=减long
            if "long" in direction_val or "买" in direction_val or direction_val == "多":
                if "open" in offset_val or "开" in offset_val:
                    pos_direction = "long"
                    pos_offset = "open"
                else:
                    pos_direction = "short"  # 买平 = 减空仓
                    pos_offset = "close"
            else:  # short/卖
                if "open" in offset_val or "开" in offset_val:
                    pos_direction = "short"
                    pos_offset = "open"
                else:
                    pos_direction = "long"  # 卖平 = 减多仓
                    pos_offset = "close"
            
            self._update_real_position(pos_direction, pos_offset, trade.price, trade.volume)
            logger.debug(f"[均价更新] {pos_direction} {pos_offset} {trade.volume}手@{trade.price:.2f}")
            
        except Exception as e:
            logger.error(f"❌ [真实均价] 更新失败: {e}")

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
                    logger.debug(f"[缓存更新] {old_cache} → {real_position}")

            # 在后台线程中更新缓存
            threading.Thread(target=update_cache, daemon=True).start()

        except Exception as e:
            logger.error(f"⚠️ [SHFE策略] 持仓缓存更新失败: {e}")

    def _log_trade_info(self, trade):
        """📊 记录成交信息"""
        logger.info(f"💰 [成交] {trade.direction.value} {trade.offset} {trade.volume}手 @ {trade.price:.2f} | 持仓→{self.pos}手")

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
                        'EMA5', 'EMA20', 'RSI', 'EMA5_EMA20_Diff', 'ATR', 'Cross_Signal'
                    ])

                # 计算EMA差值
                ema_diff = self.current_ma5 - self.current_ma20

                # 获取交叉信号 - 使用已有的检测结果，避免重复调用
                cross_signal = analysis.get("cross_signal", "NONE")

                # 写入数据（2025-01-03 新增 ATR 列）
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
                    f"{self.current_atr:.2f}",
                    cross_signal
                ])

            # 每10个K线输出一次指标对比
            if hasattr(self, '_csv_log_count'):
                self._csv_log_count += 1
            else:
                self._csv_log_count = 1

            if self._csv_log_count % 10 == 0:
                logger.debug(f"[指标] EMA5:{self.current_ma5:.2f} EMA20:{self.current_ma20:.2f} RSI:{self.current_rsi:.2f}")

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
        'max_position': 2,
        # 2025-12-29 新增参数
        'min_cross_distance': 0.0001   # 最小交叉幅度（0.01%，主要靠时间确认过滤假突破）
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
        "atr_period": {
            "type": "int",
            "default": 14,
            "description": "ATR计算周期"
        },
        "add_loss_atr_multiplier": {
            "type": "float",
            "default": 1.5,
            "description": "加仓阈值=ATR×此倍数（亏损超过才允许加仓）"
        },
        "trade_volume": {
            "type": "int",
            "default": 1,
            "description": "每次交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 2,
            "description": "最大持仓手数"
        },
        "min_cross_distance": {
            "type": "float",
            "default": 0.0001,
            "description": "最小交叉幅度（0.01%），主要靠时间确认过滤假突破"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("简化SHFE策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
