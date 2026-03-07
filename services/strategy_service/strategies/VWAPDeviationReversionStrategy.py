"""
VWAP偏离回归策略 (VWAP Deviation Reversion Strategy)
基于VWAP偏离的高频均值回归交易策略
核心信号: VWAP偏离、RSI极值、布林带边界、动量背离
适用场景: 震荡市场，高频交易，追求高胜率
"""

import time
import numpy as np
from typing import Dict, Any, Optional, List, Deque
from datetime import datetime
from collections import deque
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from vnpy.trader.utility import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class VWAPDeviationReversionStrategy(ARBIGCtaTemplate):
    """
    VWAP偏离回归策略 (VWAP Deviation Reversion Strategy)

    核心逻辑：
    1. VWAP偏离检测和回归 - 价格偏离成交量加权均价后回归
    2. RSI极值的均值回归 - 利用RSI超买超卖信号
    3. 布林带边界触碰反转 - 价格触及统计边界后反转
    4. 短期动量背离 - 短期与长期动量方向背离
    5. 高频交易，持仓1-10分钟 - 快进快出获取小幅利润
    """
    
    # ==================== 策略参数 ====================
    
    # 账户设置
    account_name = "account_B"
    initial_capital = 1000000
    max_position = 12
    
    # VWAP偏离参数
    vwap_window = 100                    # VWAP计算窗口
    vwap_deviation_threshold = 0.002     # 偏离阈值(0.2%)
    reversion_probability_threshold = 0.7 # 回归概率阈值
    
    # RSI参数
    rsi_period = 14                      # RSI计算周期
    rsi_oversold = 25                    # RSI超卖线
    rsi_overbought = 75                  # RSI超买线
    
    # 布林带参数
    bollinger_period = 20                # 布林带周期
    bollinger_std = 2.0                  # 标准差倍数
    
    # 动量参数
    momentum_short_period = 60           # 短期动量周期(1分钟)
    momentum_long_period = 300           # 长期动量周期(5分钟)
    
    # 风险管理参数
    max_risk_per_trade = 0.005           # 单笔最大风险0.5%
    stop_loss_ticks = 12                 # 止损tick数
    take_profit_ratio = 1.5              # 止盈比例
    max_holding_seconds = 300            # 最大持仓时间(5分钟)
    
    # 时间过滤参数
    min_signal_interval = 30             # 最小信号间隔(秒)
    
    # ==================== 策略变量（类型注解，实际初始化在__init__）====================

    # tick数据缓存
    tick_buffer: Deque[TickData]

    # 技术指标
    current_vwap: float
    current_rsi: float
    rsi_initialized: bool  # RSI是否已初始化
    bb_upper: float
    bb_middle: float
    bb_lower: float
    tick_atr: float

    # 动量指标
    short_momentum: float
    long_momentum: float

    # 信号状态
    last_signal_time: float
    signal_count: int

    # 持仓管理
    entry_time: float
    entry_price: float
    stop_loss_price: float
    take_profit_price: float

    # 统计数据
    vwap_signals: int
    rsi_signals: int
    bb_signals: int
    successful_trades: int
    
    def __init__(self, strategy_name: str, symbol: str, setting: Dict[str, Any], signal_sender):
        """初始化高频均值回归策略"""
        super().__init__(strategy_name, symbol, setting, signal_sender)

        # 初始化数据结构（实例变量，避免多实例共享）
        self.tick_buffer = deque(maxlen=500)

        # 初始化技术指标
        self.current_vwap = 0.0
        self.current_rsi = 50.0
        self.rsi_initialized = False  # RSI是否已初始化
        self.bb_upper = 0.0
        self.bb_middle = 0.0
        self.bb_lower = 0.0
        self.tick_atr = 0.0

        # 初始化动量指标
        self.short_momentum = 0.0
        self.long_momentum = 0.0

        # 初始化信号状态
        self.last_signal_time = 0.0
        self.signal_count = 0

        # 初始化持仓管理
        self.entry_time = 0.0
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

        # 初始化统计数据
        self.vwap_signals = 0
        self.rsi_signals = 0
        self.bb_signals = 0
        self.successful_trades = 0

        # 创建数组管理器用于K线数据
        self.am = ArrayManager(size=100)

        logger.info(f"高频均值回归策略初始化完成: {strategy_name} - 策略B")
    
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("高频均值回归策略初始化完成 - 专注价格回归特性")
    
    def on_start(self) -> None:
        """策略启动"""
        self.write_log("高频均值回归策略启动 - 开始高频监控")
    
    def on_stop(self) -> None:
        """策略停止"""
        self.write_log(f"高频均值回归策略停止 - 统计: VWAP信号{self.vwap_signals}次, "
                      f"RSI信号{self.rsi_signals}次, 布林带信号{self.bb_signals}次, "
                      f"成功交易{self.successful_trades}次")
    
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理 - 核心逻辑"""
        # 添加到缓存
        self.tick_buffer.append(tick)
        
        # 需要足够的历史数据
        if len(self.tick_buffer) < self.vwap_window:
            return
        
        # 更新技术指标
        self._update_indicators()
        
        # 检查是否在交易时间
        if not self._is_trading_time():
            return
        
        # 生成均值回归信号
        signal = self._generate_mean_reversion_signal(tick)
        
        # 执行交易决策
        if signal and signal["strength"] > 0.7:
            self._execute_signal(signal, tick)
        
        # 管理现有持仓
        if self.pos != 0:
            self._manage_position(tick)
    
    def on_bar_impl(self, bar: BarData) -> None:
        """K线数据处理 - 辅助分析"""
        self.am.update_bar(bar)
    
    def _update_indicators(self) -> None:
        """更新技术指标"""
        if len(self.tick_buffer) < max(self.vwap_window, self.bollinger_period):
            return
        
        recent_ticks = list(self.tick_buffer)
        
        # 计算VWAP
        vwap_ticks = recent_ticks[-self.vwap_window:]
        total_value = sum(tick.last_price * tick.volume for tick in vwap_ticks)
        total_volume = sum(tick.volume for tick in vwap_ticks)
        self.current_vwap = total_value / total_volume if total_volume > 0 else 0
        
        # 计算RSI
        self.current_rsi = self._calculate_tick_rsi()
        
        # 计算布林带
        self.bb_upper, self.bb_middle, self.bb_lower = self._calculate_tick_bollinger()
        
        # 计算tick级ATR
        price_changes = []
        for i in range(1, min(50, len(recent_ticks))):
            price_changes.append(abs(recent_ticks[i].last_price - recent_ticks[i-1].last_price))
        self.tick_atr = np.mean(price_changes) if price_changes else 0
        
        # 计算动量
        self._calculate_momentum()
    
    def _calculate_tick_rsi(self) -> float:
        """计算tick级RSI"""
        if len(self.tick_buffer) < self.rsi_period + 1:
            return 50.0
        
        recent_ticks = list(self.tick_buffer)[-(self.rsi_period + 1):]
        price_changes = []
        
        for i in range(1, len(recent_ticks)):
            change = recent_ticks[i].last_price - recent_ticks[i-1].last_price
            price_changes.append(change)
        
        if not price_changes:
            return 50.0
        
        gains = [change for change in price_changes if change > 0]
        losses = [-change for change in price_changes if change < 0]
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_tick_bollinger(self) -> tuple:
        """计算tick级布林带"""
        if len(self.tick_buffer) < self.bollinger_period:
            return 0.0, 0.0, 0.0
        
        recent_ticks = list(self.tick_buffer)[-self.bollinger_period:]
        prices = [tick.last_price for tick in recent_ticks]
        
        middle = np.mean(prices)
        std = np.std(prices)
        
        upper = middle + self.bollinger_std * std
        lower = middle - self.bollinger_std * std
        
        return upper, middle, lower
    
    def _calculate_momentum(self) -> None:
        """计算动量指标"""
        if len(self.tick_buffer) < self.momentum_long_period:
            return
        
        recent_ticks = list(self.tick_buffer)
        
        # 短期动量
        if len(recent_ticks) >= self.momentum_short_period:
            short_start = recent_ticks[-self.momentum_short_period].last_price
            short_end = recent_ticks[-1].last_price
            self.short_momentum = (short_end - short_start) / short_start
        
        # 长期动量
        long_start = recent_ticks[-self.momentum_long_period].last_price
        long_end = recent_ticks[-1].last_price
        self.long_momentum = (long_end - long_start) / long_start

    def _generate_mean_reversion_signal(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """生成均值回归信号"""
        # 检查信号间隔
        current_time = time.time()
        if current_time - self.last_signal_time < self.min_signal_interval:
            return None

        signals = []

        # 1. VWAP偏离信号
        vwap_signal = self._detect_vwap_deviation(tick)
        if vwap_signal:
            signals.append(vwap_signal)

        # 2. RSI极值信号
        rsi_signal = self._detect_rsi_extreme(tick)
        if rsi_signal:
            signals.append(rsi_signal)

        # 3. 布林带边界信号
        bb_signal = self._detect_bollinger_touch(tick)
        if bb_signal:
            signals.append(bb_signal)

        # 4. 动量背离信号
        momentum_signal = self._detect_momentum_divergence(tick)
        if momentum_signal:
            signals.append(momentum_signal)

        # 综合信号
        if signals:
            return self._combine_reversion_signals(signals)

        return None

    def _detect_vwap_deviation(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """VWAP偏离检测"""
        if self.current_vwap <= 0:
            return None

        deviation = (tick.last_price - self.current_vwap) / self.current_vwap

        if abs(deviation) > self.vwap_deviation_threshold:
            reversion_prob = self._calculate_reversion_probability(deviation)

            if reversion_prob > self.reversion_probability_threshold:
                direction = "SELL" if deviation > 0 else "BUY"  # 反向操作
                self.vwap_signals += 1
                return {
                    "type": "vwap_deviation",
                    "direction": direction,
                    "strength": min(abs(deviation) / self.vwap_deviation_threshold, 1.0),
                    "deviation": deviation,
                    "reversion_prob": reversion_prob
                }
        return None

    def _detect_rsi_extreme(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """RSI极值检测"""
        if self.current_rsi == 0:
            return None

        if self.current_rsi < self.rsi_oversold:
            self.rsi_signals += 1
            return {
                "type": "rsi_extreme",
                "direction": "BUY",
                "strength": (self.rsi_oversold - self.current_rsi) / self.rsi_oversold,
                "rsi_value": self.current_rsi
            }
        elif self.current_rsi > self.rsi_overbought:
            self.rsi_signals += 1
            return {
                "type": "rsi_extreme",
                "direction": "SELL",
                "strength": (self.current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought),
                "rsi_value": self.current_rsi
            }
        return None

    def _detect_bollinger_touch(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """布林带边界触碰"""
        if self.bb_upper == 0 or self.bb_lower == 0:
            return None

        current_price = tick.last_price

        if current_price >= self.bb_upper:
            self.bb_signals += 1
            return {
                "type": "bollinger_touch",
                "direction": "SELL",  # 触及上轨，看跌
                "strength": min((current_price - self.bb_upper) / (self.bb_upper - self.bb_middle), 1.0),
                "bb_position": "upper"
            }
        elif current_price <= self.bb_lower:
            self.bb_signals += 1
            return {
                "type": "bollinger_touch",
                "direction": "BUY",   # 触及下轨，看涨
                "strength": min((self.bb_lower - current_price) / (self.bb_middle - self.bb_lower), 1.0),
                "bb_position": "lower"
            }
        return None

    def _detect_momentum_divergence(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """动量背离检测"""
        if self.short_momentum == 0 or self.long_momentum == 0:
            return None

        # 检查短期和长期动量是否背离
        if self.short_momentum * self.long_momentum < 0:  # 方向相反
            if abs(self.short_momentum) > 0.001:  # 短期动量足够强
                direction = "SELL" if self.short_momentum > 0 else "BUY"  # 反向操作
                return {
                    "type": "momentum_divergence",
                    "direction": direction,
                    "strength": min(abs(self.short_momentum) * 100, 1.0),
                    "short_momentum": self.short_momentum,
                    "long_momentum": self.long_momentum
                }
        return None

    def _calculate_reversion_probability(self, deviation: float) -> float:
        """计算均值回归概率"""
        abs_deviation = abs(deviation)

        if abs_deviation > 0.005:  # 0.5%以上偏离
            return 0.9
        elif abs_deviation > 0.003:  # 0.3%以上偏离
            return 0.8
        elif abs_deviation > 0.002:  # 0.2%以上偏离
            return 0.7
        else:
            return 0.5

    def _combine_reversion_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """综合均值回归信号"""
        if not signals:
            return None

        buy_strength = 0
        sell_strength = 0
        signal_details = []

        for signal in signals:
            strength = signal["strength"]
            signal_details.append(f"{signal['type']}({strength:.2f})")

            if signal["direction"] == "BUY":
                buy_strength += strength
            elif signal["direction"] == "SELL":
                sell_strength += strength

        # 确定最终方向（均值回归需要更高的信号强度）
        if buy_strength > sell_strength and buy_strength > 0.7:
            final_direction = "BUY"
            final_strength = min(buy_strength, 1.0)
        elif sell_strength > buy_strength and sell_strength > 0.7:
            final_direction = "SELL"
            final_strength = min(sell_strength, 1.0)
        else:
            return None

        return {
            "direction": final_direction,
            "strength": final_strength,
            "signals": signal_details,
            "buy_strength": buy_strength,
            "sell_strength": sell_strength
        }

    def _execute_signal(self, signal: Dict[str, Any], tick: TickData) -> None:
        """执行均值回归信号"""
        # 如果已有持仓，先平仓（均值回归策略快进快出）
        if self.pos != 0:
            self._close_position(tick.last_price, "新信号平仓")

        # 计算仓位大小
        position_size = self._calculate_position_size(signal["strength"])
        if position_size <= 0:
            return

        # 计算止损止盈（均值回归策略止损更紧）
        entry_price = tick.last_price
        stop_distance = self.tick_atr * self.stop_loss_ticks

        if signal["direction"] == "BUY":
            self.buy(entry_price, position_size)
            self.stop_loss_price = entry_price - stop_distance
            self.take_profit_price = entry_price + stop_distance * self.take_profit_ratio
        else:
            self.short(entry_price, position_size)
            self.stop_loss_price = entry_price + stop_distance
            self.take_profit_price = entry_price - stop_distance * self.take_profit_ratio

        self.entry_price = entry_price
        self.entry_time = time.time()
        self.last_signal_time = time.time()
        self.signal_count += 1

        self.write_log(f"⚡ 均值回归信号: {signal['direction']} {position_size}手 "
                      f"@ {entry_price:.2f}, 强度: {signal['strength']:.2f}")
        self.write_log(f"   信号组合: {', '.join(signal['signals'])}")

    def _manage_position(self, tick: TickData) -> None:
        """管理均值回归持仓 - 快进快出"""
        if self.pos == 0:
            return

        current_price = tick.last_price
        holding_time = time.time() - self.entry_time

        # 快速止盈止损
        if self.pos > 0:  # 多头
            if current_price <= self.stop_loss_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"均值回归止损: {current_price:.2f}")
                self._reset_position()
            elif current_price >= self.take_profit_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"均值回归止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()
        else:  # 空头
            if current_price >= self.stop_loss_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"均值回归止损: {current_price:.2f}")
                self._reset_position()
            elif current_price <= self.take_profit_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"均值回归止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()

        # 时间止损（均值回归不宜持仓过久）
        if holding_time > self.max_holding_seconds:
            self._close_position(current_price, "时间止损")

    def _calculate_position_size(self, signal_strength: float) -> int:
        """计算仓位大小"""
        # 基础仓位（均值回归策略相对保守）
        base_position = 2

        # 根据信号强度调整
        strength_multiplier = 0.8 + signal_strength * 1.2

        # 根据波动率调整
        volatility_multiplier = max(0.6, 1.5 - self.tick_atr * 800)

        position = int(base_position * strength_multiplier * volatility_multiplier)
        return min(position, self.max_position)

    def _close_position(self, price: float, reason: str) -> None:
        """平仓"""
        if self.pos == 0:
            return

        if self.pos > 0:
            self.sell(price, abs(self.pos))
        else:
            self.cover(price, abs(self.pos))

        self.write_log(f"🛑 {reason}: 平仓 {self.pos}手 @ {price:.2f}")
        self._reset_position()

    def _reset_position(self) -> None:
        """重置持仓相关变量"""
        self.entry_price = 0.0
        self.entry_time = 0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

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
