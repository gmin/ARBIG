"""
大单跟踪策略 (Large Order Following Strategy)
基于tick数据跟踪大资金流向的交易策略
核心信号: 大单识别、价格跳跃、买卖压力、成交密集区
适用场景: 趋势市场，中频交易，追求高盈亏比
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


class LargeOrderFollowingStrategy(ARBIGCtaTemplate):
    """
    大单跟踪策略 (Large Order Following Strategy)

    核心逻辑：
    1. 大单识别和跟踪 - 发现主力资金动向
    2. 价格跳跃检测和确认 - 捕捉突破信号
    3. 买卖压力分析 - 判断多空力量对比
    4. 成交密集区支撑阻力 - 识别关键价位
    5. 中频交易，持仓5-30分钟 - 追求高盈亏比
    """
    
    # ==================== 策略参数 ====================
    
    # 账户设置
    account_name = "account_A"
    initial_capital = 1000000
    max_position = 15
    
    # 大单识别参数
    large_order_threshold = 3.0      # 大单阈值(倍数)
    large_order_window = 100         # 大单检测窗口(tick数)
    
    # 价格跳跃参数
    jump_threshold = 0.0008          # 跳跃阈值(0.08%)
    jump_confirmation_ticks = 5      # 跳跃确认tick数
    
    # 买卖压力参数
    pressure_window = 50             # 压力计算窗口
    pressure_threshold = 0.6         # 压力不平衡阈值
    
    # 成交密集区参数
    cluster_window = 200             # 密集区计算窗口
    cluster_threshold = 0.0005       # 密集区价格范围(0.05%)
    
    # 风险管理参数
    max_risk_per_trade = 0.008       # 单笔最大风险0.8%
    stop_loss_ticks = 20             # 止损tick数
    take_profit_ratio = 2.5          # 止盈比例(相对止损)
    max_holding_minutes = 30         # 最大持仓时间(分钟)
    
    # 时间过滤参数
    min_signal_interval = 60         # 最小信号间隔(秒)
    
    # ==================== 策略变量 ====================
    
    # tick数据缓存
    tick_buffer: Deque[TickData] = deque(maxlen=500)
    
    # 技术指标
    average_volume = 0.0
    current_vwap = 0.0
    tick_atr = 0.0
    trend_strength = 0.0
    
    # 信号状态
    last_signal_time = 0
    current_signal_strength = 0.0
    signal_count = 0
    
    # 持仓管理
    entry_time = 0
    entry_price = 0.0
    stop_loss_price = 0.0
    take_profit_price = 0.0
    
    # 统计数据
    large_orders_detected = 0
    price_jumps_detected = 0
    successful_trades = 0
    
    def __init__(self, strategy_name: str, symbol: str, setting: Dict[str, Any], signal_sender):
        """初始化微观结构策略"""
        super().__init__(strategy_name, symbol, setting, signal_sender)
        
        # 初始化数据结构
        self.tick_buffer = deque(maxlen=500)
        
        # 创建数组管理器用于K线数据
        self.am = ArrayManager(size=100)
        
        logger.info(f"微观结构策略初始化完成: {strategy_name} - 账户A")
    
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("微观结构策略初始化完成 - 专注大单跟踪和价格跳跃")
    
    def on_start(self) -> None:
        """策略启动"""
        self.write_log("微观结构策略启动 - 开始监控tick数据")
    
    def on_stop(self) -> None:
        """策略停止"""
        self.write_log(f"微观结构策略停止 - 统计: 大单{self.large_orders_detected}次, "
                      f"跳跃{self.price_jumps_detected}次, 成功交易{self.successful_trades}次")
    
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理 - 核心逻辑"""
        # 添加到缓存
        self.tick_buffer.append(tick)
        
        # 需要足够的历史数据
        if len(self.tick_buffer) < self.large_order_window:
            return
        
        # 更新基础指标
        self._update_indicators()
        
        # 检查是否在交易时间
        if not self._is_trading_time():
            return
        
        # 生成交易信号
        signal = self._generate_microstructure_signal(tick)
        
        # 执行交易决策
        if signal and signal["strength"] > 0.6:
            self._execute_signal(signal, tick)
        
        # 管理现有持仓
        if self.pos != 0:
            self._manage_position(tick)
    
    def on_bar_impl(self, bar: BarData) -> None:
        """K线数据处理 - 辅助分析"""
        self.am.update_bar(bar)
        
        # 更新长期指标用于过滤
        if self.am.inited:
            # 计算趋势强度用于信号过滤
            ma_5 = self.am.sma(5)
            ma_20 = self.am.sma(20)
            self.trend_strength = abs(ma_5 - ma_20) / ma_20 if ma_20 > 0 else 0
    
    def _update_indicators(self) -> None:
        """更新技术指标"""
        if len(self.tick_buffer) < 50:
            return
        
        recent_ticks = list(self.tick_buffer)[-50:]
        
        # 计算平均成交量
        volumes = [tick.volume for tick in recent_ticks]
        self.average_volume = np.mean(volumes)
        
        # 计算VWAP
        total_value = sum(tick.last_price * tick.volume for tick in recent_ticks)
        total_volume = sum(tick.volume for tick in recent_ticks)
        self.current_vwap = total_value / total_volume if total_volume > 0 else 0
        
        # 计算tick级ATR
        price_changes = []
        for i in range(1, len(recent_ticks)):
            price_changes.append(abs(recent_ticks[i].last_price - recent_ticks[i-1].last_price))
        self.tick_atr = np.mean(price_changes) if price_changes else 0
    
    def _generate_microstructure_signal(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """生成微观结构信号"""
        # 检查信号间隔
        current_time = time.time()
        if current_time - self.last_signal_time < self.min_signal_interval:
            return None
        
        signals = []
        
        # 1. 大单信号
        large_order_signal = self._detect_large_order(tick)
        if large_order_signal:
            signals.append(large_order_signal)
        
        # 2. 价格跳跃信号  
        jump_signal = self._detect_price_jump(tick)
        if jump_signal:
            signals.append(jump_signal)
        
        # 3. 买卖压力信号
        pressure_signal = self._analyze_bid_ask_pressure(tick)
        if pressure_signal:
            signals.append(pressure_signal)
        
        # 4. 支撑阻力信号
        sr_signal = self._identify_support_resistance(tick)
        if sr_signal:
            signals.append(sr_signal)
        
        # 综合信号
        if signals:
            return self._combine_signals(signals)
        
        return None
    
    def _detect_large_order(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """大单识别"""
        if tick.volume > self.average_volume * self.large_order_threshold:
            # 判断大单方向
            direction = "NEUTRAL"
            if hasattr(tick, 'bid_volume_1') and hasattr(tick, 'ask_volume_1'):
                if tick.bid_volume_1 > tick.ask_volume_1 * 1.5:
                    direction = "BUY"
                elif tick.ask_volume_1 > tick.bid_volume_1 * 1.5:
                    direction = "SELL"
            else:
                # 通过价格变动判断方向
                if len(self.tick_buffer) >= 2:
                    prev_tick = self.tick_buffer[-2]
                    if tick.last_price > prev_tick.last_price:
                        direction = "BUY"
                    elif tick.last_price < prev_tick.last_price:
                        direction = "SELL"

            if direction != "NEUTRAL":
                self.large_orders_detected += 1
                return {
                    "type": "large_order",
                    "direction": direction,
                    "strength": min(tick.volume / self.average_volume / 3.0, 1.0),
                    "volume": tick.volume
                }
        return None

    def _detect_price_jump(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """价格跳跃检测"""
        if len(self.tick_buffer) < 2:
            return None

        prev_tick = self.tick_buffer[-2]
        price_change = abs(tick.last_price - prev_tick.last_price) / prev_tick.last_price

        if price_change > self.jump_threshold:
            direction = "BUY" if tick.last_price > prev_tick.last_price else "SELL"
            volume_confirmation = tick.volume > self.average_volume * 1.5

            self.price_jumps_detected += 1
            return {
                "type": "price_jump",
                "direction": direction,
                "strength": min(price_change / self.jump_threshold, 1.0),
                "volume_confirmed": volume_confirmation
            }
        return None

    def _analyze_bid_ask_pressure(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """买卖压力分析"""
        if not hasattr(tick, 'bid_volume_1') or not hasattr(tick, 'ask_volume_1'):
            return None

        total_volume = tick.bid_volume_1 + tick.ask_volume_1
        if total_volume > 0:
            buy_pressure = tick.bid_volume_1 / total_volume

            if buy_pressure > self.pressure_threshold:
                return {
                    "type": "pressure",
                    "direction": "BUY",
                    "strength": (buy_pressure - 0.5) * 2,
                    "pressure_ratio": buy_pressure
                }
            elif buy_pressure < (1 - self.pressure_threshold):
                return {
                    "type": "pressure",
                    "direction": "SELL",
                    "strength": (0.5 - buy_pressure) * 2,
                    "pressure_ratio": buy_pressure
                }
        return None

    def _identify_support_resistance(self, tick: TickData) -> Optional[Dict[str, Any]]:
        """识别支撑阻力位"""
        if len(self.tick_buffer) < self.cluster_window:
            return None

        recent_ticks = list(self.tick_buffer)[-self.cluster_window:]
        prices = [t.last_price for t in recent_ticks]

        # 寻找价格密集区
        current_price = tick.last_price
        price_clusters = []

        for price in set(prices):
            nearby_count = sum(1 for p in prices if abs(p - price) / price < self.cluster_threshold)
            if nearby_count > len(prices) * 0.1:  # 超过10%的tick在附近
                price_clusters.append((price, nearby_count))

        if price_clusters:
            # 找到最强的支撑/阻力位
            strongest_cluster = max(price_clusters, key=lambda x: x[1])
            cluster_price = strongest_cluster[0]

            if abs(current_price - cluster_price) / cluster_price < self.cluster_threshold * 2:
                if current_price > cluster_price:
                    return {
                        "type": "resistance",
                        "direction": "SELL",
                        "strength": 0.6,
                        "level": cluster_price
                    }
                else:
                    return {
                        "type": "support",
                        "direction": "BUY",
                        "strength": 0.6,
                        "level": cluster_price
                    }
        return None

    def _combine_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """综合多个信号"""
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

        # 确定最终方向
        if buy_strength > sell_strength and buy_strength > 0.6:
            final_direction = "BUY"
            final_strength = min(buy_strength, 1.0)
        elif sell_strength > buy_strength and sell_strength > 0.6:
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
        """执行交易信号"""
        if self.pos != 0:  # 已有持仓，不开新仓
            return

        # 计算仓位大小
        position_size = self._calculate_position_size(signal["strength"])
        if position_size <= 0:
            return

        # 计算止损止盈
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

        self.write_log(f"🎯 微观结构信号执行: {signal['direction']} {position_size}手 "
                      f"@ {entry_price:.2f}, 强度: {signal['strength']:.2f}")
        self.write_log(f"   信号组合: {', '.join(signal['signals'])}")

    def _manage_position(self, tick: TickData) -> None:
        """管理现有持仓"""
        if self.pos == 0:
            return

        current_price = tick.last_price
        holding_time = time.time() - self.entry_time

        # 止损止盈检查
        if self.pos > 0:  # 多头持仓
            if current_price <= self.stop_loss_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"微观结构止损: {current_price:.2f}")
                self._reset_position()
            elif current_price >= self.take_profit_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"微观结构止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()
        else:  # 空头持仓
            if current_price >= self.stop_loss_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"微观结构止损: {current_price:.2f}")
                self._reset_position()
            elif current_price <= self.take_profit_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"微观结构止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()

        # 时间止损
        if holding_time > self.max_holding_minutes * 60:
            self._close_position(current_price, "时间止损")

    def _calculate_position_size(self, signal_strength: float) -> int:
        """计算仓位大小"""
        # 基础仓位
        base_position = 3

        # 根据信号强度调整
        strength_multiplier = 0.5 + signal_strength * 1.5

        # 根据波动率调整
        volatility_multiplier = max(0.5, 2.0 - self.tick_atr * 1000)

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

    def _combine_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """综合多个信号"""
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

        # 确定最终方向
        if buy_strength > sell_strength and buy_strength > 0.6:
            final_direction = "BUY"
            final_strength = min(buy_strength, 1.0)
        elif sell_strength > buy_strength and sell_strength > 0.6:
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
        """执行交易信号"""
        if self.pos != 0:  # 已有持仓，不开新仓
            return

        # 计算仓位大小
        position_size = self._calculate_position_size(signal["strength"])
        if position_size <= 0:
            return

        # 计算止损止盈
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

        self.write_log(f"🎯 微观结构信号执行: {signal['direction']} {position_size}手 "
                      f"@ {entry_price:.2f}, 强度: {signal['strength']:.2f}")
        self.write_log(f"   信号组合: {', '.join(signal['signals'])}")

    def _manage_position(self, tick: TickData) -> None:
        """管理现有持仓"""
        if self.pos == 0:
            return

        current_price = tick.last_price
        holding_time = time.time() - self.entry_time

        # 止损止盈检查
        if self.pos > 0:  # 多头持仓
            if current_price <= self.stop_loss_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"微观结构止损: {current_price:.2f}")
                self._reset_position()
            elif current_price >= self.take_profit_price:
                self.sell(current_price, abs(self.pos))
                self.write_log(f"微观结构止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()
        else:  # 空头持仓
            if current_price >= self.stop_loss_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"微观结构止损: {current_price:.2f}")
                self._reset_position()
            elif current_price <= self.take_profit_price:
                self.cover(current_price, abs(self.pos))
                self.write_log(f"微观结构止盈: {current_price:.2f}")
                self.successful_trades += 1
                self._reset_position()

        # 时间止损
        if holding_time > self.max_holding_minutes * 60:
            self._close_position(current_price, "时间止损")

    def _calculate_position_size(self, signal_strength: float) -> int:
        """计算仓位大小"""
        # 基础仓位
        base_position = 3

        # 根据信号强度调整
        strength_multiplier = 0.5 + signal_strength * 1.5

        # 根据波动率调整
        volatility_multiplier = max(0.5, 2.0 - self.tick_atr * 1000)

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
