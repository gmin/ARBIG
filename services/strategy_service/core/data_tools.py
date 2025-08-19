"""
ARBIG数据处理工具
基于vnpy的BarGenerator和ArrayManager设计
"""

import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import deque
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData, Direction
from utils.logger import get_logger

logger = get_logger(__name__)

class BarGenerator:
    """
    K线生成器
    基于Tick数据生成不同周期的K线数据
    """
    
    def __init__(self, on_bar_callback, window: int = 0, on_window_bar_callback=None):
        """
        初始化K线生成器
        
        Args:
            on_bar_callback: 1分钟K线回调函数
            window: 时间窗口（分钟），0表示只生成1分钟K线
            on_window_bar_callback: 时间窗口K线回调函数
        """
        self.on_bar = on_bar_callback
        self.window = window
        self.on_window_bar = on_window_bar_callback
        
        self.bar: Optional[BarData] = None
        self.window_bar: Optional[BarData] = None
        
        self.last_tick: Optional[TickData] = None
        self.hour_bar: Optional[BarData] = None
        
        logger.info(f"K线生成器初始化完成，窗口: {window}分钟")
    
    def update_tick(self, tick: TickData) -> None:
        """
        更新Tick数据
        
        Args:
            tick: Tick数据
        """
        new_minute = False
        
        # 检查是否为新的分钟
        if not self.bar:
            new_minute = True
        elif self.bar.datetime.minute != tick.datetime.minute:
            new_minute = True
        elif self.bar.datetime.hour != tick.datetime.hour:
            new_minute = True
        
        if new_minute:
            if self.bar:
                self.on_bar(self.bar)
                self.update_window_bar(self.bar)
            
            # 创建新的分钟K线
            self.bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=tick.datetime.replace(second=0, microsecond=0),
                interval="1m",
                volume=tick.volume,
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                open_interest=getattr(tick, 'open_interest', 0)
            )
        else:
            # 更新当前K线
            if tick.last_price > self.bar.high_price:
                self.bar.high_price = tick.last_price
            
            if tick.last_price < self.bar.low_price:
                self.bar.low_price = tick.last_price
            
            self.bar.close_price = tick.last_price
            self.bar.volume = tick.volume
            self.bar.open_interest = getattr(tick, 'open_interest', 0)
        
        self.last_tick = tick
    
    def update_window_bar(self, bar: BarData) -> None:
        """
        更新时间窗口K线
        
        Args:
            bar: 1分钟K线数据
        """
        if not self.window or not self.on_window_bar:
            return
        
        # 检查是否为新的时间窗口
        if not self.window_bar:
            dt = bar.datetime.replace(second=0, microsecond=0)
            dt = dt.replace(minute=(dt.minute // self.window) * self.window)
            
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                interval=f"{self.window}m",
                volume=bar.volume,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                open_interest=bar.open_interest
            )
        else:
            # 检查是否需要生成新的窗口K线
            dt = bar.datetime.replace(second=0, microsecond=0)
            dt = dt.replace(minute=(dt.minute // self.window) * self.window)
            
            if dt != self.window_bar.datetime:
                # 输出完成的窗口K线
                self.on_window_bar(self.window_bar)
                
                # 创建新的窗口K线
                self.window_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=dt,
                    interval=f"{self.window}m",
                    volume=bar.volume,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    open_interest=bar.open_interest
                )
            else:
                # 更新当前窗口K线
                if bar.high_price > self.window_bar.high_price:
                    self.window_bar.high_price = bar.high_price
                
                if bar.low_price < self.window_bar.low_price:
                    self.window_bar.low_price = bar.low_price
                
                self.window_bar.close_price = bar.close_price
                self.window_bar.volume = bar.volume
                self.window_bar.open_interest = bar.open_interest
    
    def generate(self, tick: TickData) -> None:
        """
        生成K线（兼容性方法）
        
        Args:
            tick: Tick数据
        """
        self.update_tick(tick)

class ArrayManager:
    """
    数组管理器
    用于存储和计算技术指标数据
    """
    
    def __init__(self, size: int = 100):
        """
        初始化数组管理器
        
        Args:
            size: 数组大小
        """
        self.size = size
        self.count = 0
        self.inited = False
        
        # 价格数据数组
        self.open_array = np.zeros(size)
        self.high_array = np.zeros(size)
        self.low_array = np.zeros(size)
        self.close_array = np.zeros(size)
        self.volume_array = np.zeros(size)
        self.open_interest_array = np.zeros(size)
        
        logger.info(f"数组管理器初始化完成，大小: {size}")
    
    def update_bar(self, bar: BarData) -> None:
        """
        更新K线数据
        
        Args:
            bar: K线数据
        """
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True
        
        # 移动数组
        self.open_array[:-1] = self.open_array[1:]
        self.high_array[:-1] = self.high_array[1:]
        self.low_array[:-1] = self.low_array[1:]
        self.close_array[:-1] = self.close_array[1:]
        self.volume_array[:-1] = self.volume_array[1:]
        self.open_interest_array[:-1] = self.open_interest_array[1:]
        
        # 添加新数据
        self.open_array[-1] = bar.open_price
        self.high_array[-1] = bar.high_price
        self.low_array[-1] = bar.low_price
        self.close_array[-1] = bar.close_price
        self.volume_array[-1] = bar.volume
        self.open_interest_array[-1] = bar.open_interest
    
    @property
    def open(self) -> float:
        """获取最新开盘价"""
        return self.open_array[-1]
    
    @property
    def high(self) -> float:
        """获取最新最高价"""
        return self.high_array[-1]
    
    @property
    def low(self) -> float:
        """获取最新最低价"""
        return self.low_array[-1]
    
    @property
    def close(self) -> float:
        """获取最新收盘价"""
        return self.close_array[-1]
    
    @property
    def volume(self) -> float:
        """获取最新成交量"""
        return self.volume_array[-1]
    
    @property
    def open_interest(self) -> float:
        """获取最新持仓量"""
        return self.open_interest_array[-1]
    
    def sma(self, n: int, array: bool = False):
        """
        简单移动平均线
        
        Args:
            n: 周期
            array: 是否返回数组
            
        Returns:
            移动平均值或数组
        """
        if not self.inited:
            return 0
        
        result = np.mean(self.close_array[-n:])
        if array:
            return np.convolve(self.close_array, np.ones(n)/n, mode='valid')
        return result
    
    def ema(self, n: int, array: bool = False):
        """
        指数移动平均线
        
        Args:
            n: 周期
            array: 是否返回数组
            
        Returns:
            指数移动平均值或数组
        """
        if not self.inited:
            return 0
        
        # 计算EMA
        alpha = 2 / (n + 1)
        ema_values = np.zeros_like(self.close_array)
        ema_values[0] = self.close_array[0]
        
        for i in range(1, len(self.close_array)):
            ema_values[i] = alpha * self.close_array[i] + (1 - alpha) * ema_values[i-1]
        
        if array:
            return ema_values
        return ema_values[-1]
    
    def std(self, n: int, array: bool = False):
        """
        标准差
        
        Args:
            n: 周期
            array: 是否返回数组
            
        Returns:
            标准差值或数组
        """
        if not self.inited:
            return 0
        
        result = np.std(self.close_array[-n:])
        if array:
            return np.array([np.std(self.close_array[i-n+1:i+1]) 
                           for i in range(n-1, len(self.close_array))])
        return result
    
    def rsi(self, n: int = 14, array: bool = False):
        """
        相对强弱指标
        
        Args:
            n: 周期
            array: 是否返回数组
            
        Returns:
            RSI值或数组
        """
        if not self.inited:
            return 50
        
        # 计算价格变化
        diff = np.diff(self.close_array)
        gains = np.where(diff > 0, diff, 0)
        losses = np.where(diff < 0, -diff, 0)
        
        # 计算平均收益和损失
        avg_gains = np.convolve(gains, np.ones(n)/n, mode='valid')
        avg_losses = np.convolve(losses, np.ones(n)/n, mode='valid')
        
        # 避免除零
        avg_losses = np.where(avg_losses == 0, 1e-10, avg_losses)
        
        # 计算RSI
        rs = avg_gains / avg_losses
        rsi_values = 100 - (100 / (1 + rs))
        
        if array:
            return rsi_values
        return rsi_values[-1] if len(rsi_values) > 0 else 50
    
    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """
        MACD指标
        
        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            (macd, signal, histogram)
        """
        if not self.inited:
            return 0, 0, 0
        
        # 计算EMA
        ema_fast = self.ema(fast, array=True)
        ema_slow = self.ema(slow, array=True)
        
        # 对齐数组长度
        min_len = min(len(ema_fast), len(ema_slow))
        if min_len == 0:
            return 0, 0, 0
        
        ema_fast = ema_fast[-min_len:]
        ema_slow = ema_slow[-min_len:]
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线（MACD的EMA）
        if len(macd_line) < signal:
            return 0, 0, 0
        
        signal_line = np.zeros_like(macd_line)
        alpha = 2 / (signal + 1)
        signal_line[0] = macd_line[0]
        
        for i in range(1, len(macd_line)):
            signal_line[i] = alpha * macd_line[i] + (1 - alpha) * signal_line[i-1]
        
        # 计算柱状图
        histogram = macd_line - signal_line
        
        return macd_line[-1], signal_line[-1], histogram[-1]
    
    def boll(self, n: int = 20, dev: float = 2) -> tuple:
        """
        布林带指标
        
        Args:
            n: 周期
            dev: 标准差倍数
            
        Returns:
            (upper, middle, lower)
        """
        if not self.inited:
            return 0, 0, 0
        
        middle = self.sma(n)
        std_value = self.std(n)
        
        upper = middle + dev * std_value
        lower = middle - dev * std_value
        
        return upper, middle, lower
    
    def atr(self, n: int = 14) -> float:
        """
        平均真实波幅
        
        Args:
            n: 周期
            
        Returns:
            ATR值
        """
        if not self.inited:
            return 0
        
        # 计算真实波幅
        tr_list = []
        for i in range(1, len(self.close_array)):
            hl = self.high_array[i] - self.low_array[i]
            hc = abs(self.high_array[i] - self.close_array[i-1])
            lc = abs(self.low_array[i] - self.close_array[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if len(tr_list) < n:
            return 0
        
        return np.mean(tr_list[-n:])
    
    def cci(self, n: int = 20) -> float:
        """
        商品通道指标
        
        Args:
            n: 周期
            
        Returns:
            CCI值
        """
        if not self.inited:
            return 0
        
        # 计算典型价格
        tp = (self.high_array + self.low_array + self.close_array) / 3
        
        # 计算移动平均
        ma = np.mean(tp[-n:])
        
        # 计算平均绝对偏差
        mad = np.mean(np.abs(tp[-n:] - ma))
        
        if mad == 0:
            return 0
        
        # 计算CCI
        cci = (tp[-1] - ma) / (0.015 * mad)
        return cci

class TechnicalIndicators:
    """
    技术指标计算工具类
    提供常用技术指标的静态计算方法
    """
    
    @staticmethod
    def sma(data: List[float], period: int) -> float:
        """简单移动平均"""
        if len(data) < period:
            return 0
        return sum(data[-period:]) / period
    
    @staticmethod
    def ema(data: List[float], period: int) -> float:
        """指数移动平均"""
        if len(data) < period:
            return 0
        
        alpha = 2 / (period + 1)
        ema = data[0]
        
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> float:
        """RSI指标"""
        if len(data) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        
        if len(gains) < period:
            return 50
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std_dev: float = 2) -> tuple:
        """布林带"""
        if len(data) < period:
            return 0, 0, 0
        
        sma = TechnicalIndicators.sma(data, period)
        
        # 计算标准差
        variance = sum([(x - sma) ** 2 for x in data[-period:]]) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, sma, lower
