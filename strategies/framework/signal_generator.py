"""
信号生成器 - 纯粹的技术分析组件
职责：基于市场数据生成交易信号，不涉及仓位管理和风控
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Signal:
    """交易信号数据类"""
    action: str  # BUY, SELL, HOLD
    strength: float  # 信号强度 0-1
    price: float  # 触发价格
    timestamp: float  # 时间戳
    indicators: Dict[str, float]  # 相关指标值
    reason: str  # 信号原因

class IndicatorBase(ABC):
    """技术指标基类"""
    
    @abstractmethod
    def calculate(self, prices: List[float]) -> float:
        """计算指标值"""
        pass
    
    @abstractmethod
    def is_ready(self, prices: List[float]) -> bool:
        """检查数据是否足够计算指标"""
        pass

class MovingAverage(IndicatorBase):
    """移动平均线指标"""
    
    def __init__(self, period: int):
        self.period = period
    
    def calculate(self, prices: List[float]) -> float:
        if not self.is_ready(prices):
            return 0.0
        return np.mean(prices[-self.period:])
    
    def is_ready(self, prices: List[float]) -> bool:
        return len(prices) >= self.period

class RSI(IndicatorBase):
    """RSI指标"""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def calculate(self, prices: List[float]) -> float:
        if not self.is_ready(prices):
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-self.period:])
        avg_loss = np.mean(losses[-self.period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def is_ready(self, prices: List[float]) -> bool:
        return len(prices) >= self.period + 1

class BollingerBands(IndicatorBase):
    """布林带指标"""
    
    def __init__(self, period: int = 20, std_multiplier: float = 2.0):
        self.period = period
        self.std_multiplier = std_multiplier
    
    def calculate(self, prices: List[float]) -> Dict[str, float]:
        if not self.is_ready(prices):
            return {'upper': float('inf'), 'middle': 0.0, 'lower': float('-inf')}
        
        recent_prices = np.array(prices[-self.period:])
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (self.std_multiplier * std)
        lower = middle - (self.std_multiplier * std)
        
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def is_ready(self, prices: List[float]) -> bool:
        return len(prices) >= self.period

class SignalGenerator:
    """信号生成器 - 组合多个技术指标生成交易信号"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.indicators = self._init_indicators()
        self.price_history: List[float] = []
        
    def _init_indicators(self) -> Dict[str, IndicatorBase]:
        """初始化技术指标"""
        indicators = {}
        
        # 移动平均线
        if 'ma_short' in self.config:
            indicators['ma_short'] = MovingAverage(self.config['ma_short'])
        if 'ma_long' in self.config:
            indicators['ma_long'] = MovingAverage(self.config['ma_long'])
        
        # RSI
        if 'rsi_period' in self.config:
            indicators['rsi'] = RSI(self.config['rsi_period'])
        
        # 布林带
        if 'bollinger_period' in self.config:
            indicators['bollinger'] = BollingerBands(
                self.config['bollinger_period'],
                self.config.get('bollinger_std', 2.0)
            )
        
        return indicators
    
    def update_price(self, price: float, timestamp: float = None):
        """更新价格数据"""
        self.price_history.append(price)
        
        # 保持历史数据长度
        max_length = max(
            self.config.get('ma_long', 20),
            self.config.get('rsi_period', 14),
            self.config.get('bollinger_period', 20)
        ) * 2
        
        if len(self.price_history) > max_length:
            self.price_history = self.price_history[-max_length:]
    
    def generate_signal(self, current_price: float, timestamp: float = None) -> Optional[Signal]:
        """生成交易信号"""
        if not self.price_history:
            return None
        
        # 更新价格
        self.update_price(current_price, timestamp)
        
        # 检查是否有足够数据
        if not self._has_sufficient_data():
            return None
        
        # 计算所有指标
        indicator_values = self._calculate_all_indicators()
        
        # 生成信号
        signal_result = self._analyze_signals(indicator_values, current_price, timestamp)
        
        if signal_result:
            return Signal(
                action=signal_result['action'],
                strength=signal_result['strength'],
                price=current_price,
                timestamp=timestamp or 0,
                indicators=indicator_values,
                reason=signal_result['reason']
            )
        
        return None
    
    def _has_sufficient_data(self) -> bool:
        """检查是否有足够的数据计算指标"""
        for indicator in self.indicators.values():
            if not indicator.is_ready(self.price_history):
                return False
        return True
    
    def _calculate_all_indicators(self) -> Dict[str, float]:
        """计算所有技术指标"""
        values = {}
        
        for name, indicator in self.indicators.items():
            if isinstance(indicator, BollingerBands):
                bb_values = indicator.calculate(self.price_history)
                values.update({f'{name}_{k}': v for k, v in bb_values.items()})
            else:
                values[name] = indicator.calculate(self.price_history)
        
        return values
    
    def _analyze_signals(self, indicators: Dict[str, float], price: float, timestamp: float) -> Optional[Dict[str, Any]]:
        """分析指标生成信号"""
        strategy_type = self.config.get('strategy_type', 'trend')
        
        if strategy_type == 'trend':
            return self._trend_signal(indicators, price)
        elif strategy_type == 'mean_reversion':
            return self._mean_reversion_signal(indicators, price)
        elif strategy_type == 'breakout':
            return self._breakout_signal(indicators, price)
        
        return None
    
    def _trend_signal(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """趋势跟踪信号"""
        if 'ma_short' not in indicators or 'ma_long' not in indicators:
            return None
        
        ma_short = indicators['ma_short']
        ma_long = indicators['ma_long']
        
        # 计算信号强度
        ma_diff = abs(ma_short - ma_long) / ma_long
        strength = min(ma_diff * 10, 1.0)  # 归一化到0-1
        
        if ma_short > ma_long and strength > 0.1:
            return {
                'action': 'BUY',
                'strength': strength,
                'reason': f'MA短线({ma_short:.2f}) > MA长线({ma_long:.2f}), 强度: {strength:.2f}'
            }
        elif ma_short < ma_long and strength > 0.1:
            return {
                'action': 'SELL',
                'strength': strength,
                'reason': f'MA短线({ma_short:.2f}) < MA长线({ma_long:.2f}), 强度: {strength:.2f}'
            }
        
        return None
    
    def _mean_reversion_signal(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """均值回归信号"""
        if 'rsi' not in indicators:
            return None
        
        rsi = indicators['rsi']
        rsi_overbought = self.config.get('rsi_overbought', 70)
        rsi_oversold = self.config.get('rsi_oversold', 30)
        
        if rsi < rsi_oversold:
            strength = (rsi_oversold - rsi) / rsi_oversold
            return {
                'action': 'BUY',
                'strength': strength,
                'reason': f'RSI超卖({rsi:.1f} < {rsi_oversold}), 强度: {strength:.2f}'
            }
        elif rsi > rsi_overbought:
            strength = (rsi - rsi_overbought) / (100 - rsi_overbought)
            return {
                'action': 'SELL',
                'strength': strength,
                'reason': f'RSI超买({rsi:.1f} > {rsi_overbought}), 强度: {strength:.2f}'
            }
        
        return None
    
    def _breakout_signal(self, indicators: Dict[str, float], price: float) -> Optional[Dict[str, Any]]:
        """突破信号"""
        if 'bollinger_upper' not in indicators or 'bollinger_lower' not in indicators:
            return None
        
        upper = indicators['bollinger_upper']
        lower = indicators['bollinger_lower']
        
        if price > upper:
            strength = (price - upper) / upper
            return {
                'action': 'BUY',
                'strength': min(strength * 100, 1.0),
                'reason': f'价格突破上轨({price:.2f} > {upper:.2f}), 强度: {strength:.2f}'
            }
        elif price < lower:
            strength = (lower - price) / lower
            return {
                'action': 'SELL',
                'strength': min(strength * 100, 1.0),
                'reason': f'价格突破下轨({price:.2f} < {lower:.2f}), 强度: {strength:.2f}'
            }
        
        return None
    
    def get_current_indicators(self) -> Dict[str, float]:
        """获取当前指标值"""
        if not self._has_sufficient_data():
            return {}
        return self._calculate_all_indicators()
    
    def reset(self):
        """重置信号生成器"""
        self.price_history.clear()
