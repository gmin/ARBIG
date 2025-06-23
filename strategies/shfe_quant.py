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
            # 计算仓位
            position = self._calculate_position(signal)
            
            if position != 0:
                # 发送交易信号
                signal_data = {
                    'signal': signal,
                    'price': self.price_history[-1],
                    'position': position,
                    'strategy_type': self.strategy_type,
                    'timestamp': time.time()
                }
                
                self.send_signal(signal_data)
                self.last_signal = signal
                
                print(f"[{self.name}] 生成信号: {signal}, 价格: {self.price_history[-1]:.2f}, 仓位: {position}")
                
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
        """突破策略"""
        if len(self.price_history) < 20:
            return None
            
        # 计算布林带
        upper, lower = self._calculate_bollinger_bands()
        current_price = self.price_history[-1]
        
        if current_price > upper and self.position <= 0:
            return 'BUY'
        elif current_price < lower and self.position >= 0:
            return 'SELL'
            
        return None
        
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
        if signal == 'BUY':
            available = self.max_position - self.position
            return min(available, 100)  # 每次最多100克
        elif signal == 'SELL':
            available = self.max_position + self.position
            return -min(available, 100)
            
        return 0 