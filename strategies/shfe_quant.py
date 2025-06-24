"""
上海市场量化交易策略
实现上期所黄金期货的量化交易策略
"""

import time
import numpy as np
from typing import Dict, Any, List
from core.strategy_base import StrategyBase
from core.event_engine import Event
from core.constants import *

class SHFEQuantStrategy(StrategyBase):
    """
    上海市场量化交易策略
    包含多种量化策略：趋势跟踪、均值回归、突破等
    """
    
    def __init__(self, name: str, event_engine, config: Dict[str, Any]):
        super().__init__(name, event_engine, config)
        
        # 策略参数
        self.strategy_type = config.get('strategy_type', 'trend')  # trend, mean_reversion, breakout
        self.symbol = config.get('symbol', 'AU9999')
        self.max_position = config.get('max_position', 1000)
        
        # 技术指标参数
        self.ma_short = config.get('ma_short', 5)      # 短期均线
        self.ma_long = config.get('ma_long', 20)       # 长期均线
        self.rsi_period = config.get('rsi_period', 14) # RSI周期
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        
        # 数据缓存
        self.price_history: List[float] = []
        self.position = 0
        self.last_signal = None
        
        # 方向判断相关
        self.current_direction = 'NEUTRAL'  # LONG, SHORT, NEUTRAL
        self.direction_confidence = 0.0
        self.last_direction_signal = None
        
    def on_start(self):
        """策略启动"""
        print(f"[{self.name}] 上海市场量化策略启动 - {self.strategy_type}")
        
    def on_stop(self):
        """策略停止"""
        print(f"[{self.name}] 上海市场量化策略停止")
        
    def on_tick(self, event: Event):
        """处理Tick事件"""
        if not self.active:
            return
            
        tick_data = event.data
        
        # 只处理指定合约的Tick
        if tick_data.get('symbol') != self.symbol:
            return
            
        price = tick_data.get('last_price')
        if price:
            self.price_history.append(price)
            
            # 保持历史数据长度
            max_length = max(self.ma_long * 2, 100)
            if len(self.price_history) > max_length:
                self.price_history = self.price_history[-max_length:]
                
            # 处理方向判断信号
            if tick_data.get('signal_type') == 'DIRECTION_SIGNAL':
                self._handle_direction_signal(tick_data.get('direction_data', {}))
                
            # 生成交易信号
            self._generate_signal()
        
    def on_bar(self, event: Event):
        """处理K线事件"""
        # K线数据可用于更复杂的策略
        pass
        
    def on_order(self, event: Event):
        """处理订单事件"""
        order_data = event.data
        print(f"[{self.name}] 订单状态更新: {order_data}")
        
    def on_trade(self, event: Event):
        """处理成交事件"""
        trade_data = event.data
        print(f"[{self.name}] 成交更新: {trade_data}")
        
        # 更新持仓
        if trade_data.get('direction') == 'BUY':
            self.position += trade_data.get('volume', 0)
        else:
            self.position -= trade_data.get('volume', 0)
            
    def on_account(self, event: Event):
        """处理账户事件"""
        account_data = event.data
        print(f"[{self.name}] 账户更新: {account_data}")
        
    def _handle_direction_signal(self, direction_data: Dict[str, Any]):
        """处理方向判断信号"""
        self.current_direction = direction_data.get('direction', 'NEUTRAL')
        self.direction_confidence = direction_data.get('confidence', 0.0)
        
        print(f"[{self.name}] 收到方向信号: {self.current_direction}, 置信度: {self.direction_confidence:.2f}")
        
    def _generate_signal(self):
        """生成交易信号"""
        if len(self.price_history) < self.ma_long:
            return
            
        signal = None
        
        if self.strategy_type == 'trend':
            signal = self._trend_strategy()
        elif self.strategy_type == 'mean_reversion':
            signal = self._mean_reversion_strategy()
        elif self.strategy_type == 'breakout':
            signal = self._breakout_strategy()
            
        if signal and signal != self.last_signal:
            # 根据方向判断调整信号
            adjusted_signal = self._adjust_signal_by_direction(signal)
            
            if adjusted_signal:
                # 计算仓位
                position = self._calculate_position(adjusted_signal)
                
                if position != 0:
                    # 发送交易信号
                    signal_data = {
                        'signal': adjusted_signal,
                        'price': self.price_history[-1],
                        'position': position,
                        'strategy_type': self.strategy_type,
                        'direction': self.current_direction,
                        'direction_confidence': self.direction_confidence,
                        'timestamp': time.time()
                    }
                    
                    self.send_signal(signal_data)
                    self.last_signal = adjusted_signal
                    
                    print(f"[{self.name}] 生成信号: {adjusted_signal}, 价格: {self.price_history[-1]:.2f}, 仓位: {position}, 方向: {self.current_direction}")
                    
    def _adjust_signal_by_direction(self, original_signal: str) -> str:
        """根据方向判断调整交易信号"""
        # 如果方向判断置信度不够，使用原始信号
        if self.direction_confidence < 0.3:
            return original_signal
            
        # 根据方向判断调整信号
        if self.current_direction == 'LONG':
            # 做多方向，只做多不做空
            if original_signal == 'BUY':
                return 'BUY'
            elif original_signal == 'SELL':
                return 'CLOSE_LONG'  # 平多而不是做空
                
        elif self.current_direction == 'SHORT':
            # 做空方向，只做空不做多
            if original_signal == 'BUY':
                return 'CLOSE_SHORT'  # 平空而不是做多
            elif original_signal == 'SELL':
                return 'SELL'
                
        else:  # NEUTRAL
            # 中性方向，使用原始信号但减少仓位
            return original_signal
            
        return None
        
    def _trend_strategy(self) -> str:
        """趋势跟踪策略"""
        if len(self.price_history) < self.ma_long:
            return None
            
        # 计算移动平均线
        ma_short = np.mean(self.price_history[-self.ma_short:])
        ma_long = np.mean(self.price_history[-self.ma_long:])
        
        # 趋势信号
        if ma_short > ma_long and self.position <= 0:
            return 'BUY'
        elif ma_short < ma_long and self.position >= 0:
            return 'SELL'
            
        return None
        
    def _mean_reversion_strategy(self) -> str:
        """均值回归策略"""
        if len(self.price_history) < self.rsi_period:
            return None
            
        # 计算RSI
        rsi = self._calculate_rsi()
        
        if rsi < self.rsi_oversold and self.position <= 0:
            return 'BUY'
        elif rsi > self.rsi_overbought and self.position >= 0:
            return 'SELL'
            
        return None
        
    def _breakout_strategy(self) -> str:
        """突破策略 - 专门用于判断市场方向（做多/做空）"""
        if len(self.price_history) < 20:
            return None
            
        # 计算布林带
        upper, lower = self._calculate_bollinger_bands()
        current_price = self.price_history[-1]
        
        # 计算突破强度
        breakout_strength = self._calculate_breakout_strength(current_price, upper, lower)
        
        # 方向判断逻辑
        if current_price > upper and breakout_strength > 0.5:  # 向上突破且强度足够
            # 向上突破，判断为做多方向
            self._record_direction_signal('LONG', current_price, upper, lower, breakout_strength)
            return 'LONG'  # 返回做多方向信号
            
        elif current_price < lower and breakout_strength > 0.5:  # 向下突破且强度足够
            # 向下突破，判断为做空方向
            self._record_direction_signal('SHORT', current_price, upper, lower, breakout_strength)
            return 'SHORT'  # 返回做空方向信号
            
        return None  # 无明显方向
        
    def _record_direction_signal(self, direction: str, price: float, upper: float, lower: float, strength: float):
        """记录方向判断信号"""
        direction_info = {
            'direction': direction,
            'price': price,
            'upper': upper,
            'lower': lower,
            'strength': strength,
            'timestamp': time.time(),
            'confidence': self._calculate_direction_confidence(direction, strength)
        }
        
        # 发送方向判断信号
        self.send_signal({
            'signal_type': 'DIRECTION_SIGNAL',
            'direction_data': direction_info
        })
        
        print(f"[{self.name}] 方向判断: {direction}, 价格: {price:.2f}, 强度: {strength:.2f}, 置信度: {direction_info['confidence']:.2f}")
        
    def _calculate_direction_confidence(self, direction: str, strength: float) -> float:
        """计算方向判断的置信度"""
        # 基础置信度基于突破强度
        base_confidence = min(strength / 2.0, 1.0)  # 最大1.0
        
        # 根据历史数据调整置信度
        if len(self.price_history) >= 50:
            # 计算最近的价格趋势
            recent_trend = self._calculate_recent_trend()
            
            # 如果方向与趋势一致，提高置信度
            if (direction == 'LONG' and recent_trend > 0) or (direction == 'SHORT' and recent_trend < 0):
                base_confidence *= 1.2
            else:
                base_confidence *= 0.8
                
        return min(base_confidence, 1.0)
        
    def _calculate_recent_trend(self) -> float:
        """计算最近的价格趋势"""
        if len(self.price_history) < 20:
            return 0.0
            
        # 计算最近20个价格点的线性回归斜率
        x = np.arange(20)
        y = np.array(self.price_history[-20:])
        
        # 简单的线性回归
        slope = np.polyfit(x, y, 1)[0]
        return slope
        
    def get_market_direction(self) -> dict:
        """获取当前市场方向判断"""
        if len(self.price_history) < 20:
            return {'direction': 'UNKNOWN', 'confidence': 0.0}
            
        # 计算布林带
        upper, lower = self._calculate_bollinger_bands()
        current_price = self.price_history[-1]
        
        # 判断方向
        if current_price > upper:
            direction = 'LONG'
            strength = self._calculate_breakout_strength(current_price, upper, lower)
        elif current_price < lower:
            direction = 'SHORT'
            strength = self._calculate_breakout_strength(current_price, upper, lower)
        else:
            direction = 'NEUTRAL'
            strength = 0.0
            
        return {
            'direction': direction,
            'strength': strength,
            'confidence': self._calculate_direction_confidence(direction, strength),
            'price': current_price,
            'upper': upper,
            'lower': lower
        }
        
    def _calculate_breakout_strength(self, price: float, upper: float, lower: float) -> float:
        """计算突破强度"""
        if price > upper:
            return (price - upper) / upper * 100
        elif price < lower:
            return (lower - price) / lower * 100
        return 0.0
        
    def get_market_condition(self) -> dict:
        """获取市场状态信息，供主策略参考"""
        if len(self.price_history) < 20:
            return {'condition': 'INSUFFICIENT_DATA'}
            
        # 计算布林带
        upper, lower = self._calculate_bollinger_bands()
        current_price = self.price_history[-1]
        
        # 判断市场状态
        if current_price > upper:
            condition = 'UPPER_BREAKOUT'
        elif current_price < lower:
            condition = 'LOWER_BREAKOUT'
        elif current_price > (upper + lower) / 2:
            condition = 'UPPER_RANGE'
        else:
            condition = 'LOWER_RANGE'
            
        return {
            'condition': condition,
            'price': current_price,
            'upper': upper,
            'lower': lower,
            'volatility': self._calculate_volatility()
        }
        
    def _calculate_volatility(self) -> float:
        """计算波动率"""
        if len(self.price_history) < 20:
            return 0.0
        returns = [self.price_history[i] / self.price_history[i-1] - 1 
                  for i in range(1, len(self.price_history))]
        return np.std(returns) * np.sqrt(252)  # 年化波动率
        
    def _calculate_rsi(self) -> float:
        """计算RSI指标"""
        if len(self.price_history) < self.rsi_period + 1:
            return 50
            
        deltas = np.diff(self.price_history)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def _calculate_bollinger_bands(self) -> tuple:
        """计算布林带"""
        period = 20
        std_multiplier = 2
        
        if len(self.price_history) < period:
            return (float('inf'), float('-inf'))
            
        prices = np.array(self.price_history[-period:])
        sma = np.mean(prices)
        std = np.std(prices)
        
        upper = sma + (std_multiplier * std)
        lower = sma - (std_multiplier * std)
        
        return (upper, lower)
        
    def _calculate_position(self, signal: str) -> int:
        """计算交易仓位"""
        base_position = 100  # 基础仓位
        
        # 根据方向置信度调整仓位
        if self.direction_confidence > 0.7:
            position_multiplier = 1.0  # 高置信度，正常仓位
        elif self.direction_confidence > 0.5:
            position_multiplier = 0.8  # 中等置信度，减少仓位
        else:
            position_multiplier = 0.5  # 低置信度，大幅减少仓位
            
        if signal == 'BUY':
            available = self.max_position - self.position
            return min(int(available * position_multiplier), base_position)
        elif signal == 'SELL':
            available = self.max_position + self.position
            return -min(int(available * position_multiplier), base_position)
        elif signal in ['CLOSE_LONG', 'CLOSE_SHORT']:
            # 平仓信号
            if signal == 'CLOSE_LONG' and self.position > 0:
                return -self.position
            elif signal == 'CLOSE_SHORT' and self.position < 0:
                return -self.position
                
        return 0 