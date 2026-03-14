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

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Direction
from utils.logger import get_logger
import logging

logger = get_logger(__name__)

# K线日志记录器全局变量
bar_logger = None
current_bar_log_date = None

def get_bar_logger():
    """获取K线专用日志记录器 - 支持按日期自动切换文件"""
    global bar_logger, current_bar_log_date

    # 获取当前日期
    today = datetime.now().strftime('%Y%m%d')

    # 如果日期变化或首次创建，重新创建logger
    if current_bar_log_date != today or bar_logger is None:
        # 清理旧的handlers
        if bar_logger:
            for handler in bar_logger.handlers[:]:
                handler.close()
                bar_logger.removeHandler(handler)

        # 创建新的logger
        bar_logger = logging.getLogger('bar_data')
        bar_logger.setLevel(logging.INFO)

        # 使用与其他日志相同的目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # 创建文件handler - 使用当前日期
        log_file = os.path.join(log_dir, f"bar_data_{today}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)

        bar_logger.addHandler(file_handler)

        # 更新当前日期
        current_bar_log_date = today

        print(f"📅 [K线日志] 切换到新日期文件: {log_file}")

    return bar_logger

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
        logger.debug(f"[K线生成器] 🔧 收到tick: {tick.symbol} 价格={tick.last_price} 时间={tick.datetime}")

        new_minute = False

        # 检查是否为新的分钟
        if not self.bar:
            new_minute = True
            logger.info(f"[K线生成器] 🔧 首次tick，创建新分钟K线")
        elif self.bar.datetime.minute != tick.datetime.minute:
            new_minute = True
            logger.info(f"[K线生成器] 🔧 分钟变化: {self.bar.datetime.minute} → {tick.datetime.minute}")
        elif self.bar.datetime.hour != tick.datetime.hour:
            new_minute = True
            logger.info(f"[K线生成器] 🔧 小时变化: {self.bar.datetime.hour} → {tick.datetime.hour}")
        else:
            logger.debug(f"[K线生成器] 🔧 同一分钟内tick: {tick.datetime.strftime('%H:%M:%S')}")
        
        if new_minute:
            if self.bar:
                logger.info(f"[K线生成器] 📊 生成1分钟K线: {self.bar.symbol} 时间={self.bar.datetime} 收盘价={self.bar.close_price}")

                # 📊 记录K线数据到专用日志文件 - 支持日期自动切换
                current_bar_logger = get_bar_logger()
                current_bar_logger.info(f"K线生成 | {self.bar.symbol} | {self.bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} | "
                              f"开:{self.bar.open_price:.2f} | 高:{self.bar.high_price:.2f} | "
                              f"低:{self.bar.low_price:.2f} | 收:{self.bar.close_price:.2f} | "
                              f"量:{self.bar.volume}")

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
                open_interest=getattr(tick, 'open_interest', 0),
                gateway_name=getattr(tick, 'gateway_name', 'CTP')
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
                open_interest=bar.open_interest,
                gateway_name=getattr(bar, 'gateway_name', 'CTP')
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
                    open_interest=bar.open_interest,
                    gateway_name=getattr(bar, 'gateway_name', 'CTP')
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
    
    def update_tick(self, tick: TickData) -> None:
        """
        更新Tick数据（简化版，主要用于测试）
        
        Args:
            tick: Tick数据
        """
        # 对于测试目的，我们可以简单地忽略tick数据
        # 或者将其转换为简单的bar数据进行处理
        pass
    
    def update_bar(self, bar: BarData) -> None:
        """
        更新K线数据
        
        Args:
            bar: K线数据
        """
        self.count += 1
        # 对于测试，降低初始化要求
        min_required = min(self.size, 20)  # 最少20个数据就可以初始化
        if not self.inited and self.count >= min_required:
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
    

    
    def ema(self, n: int, array: bool = False):
        """
        指数移动平均线 - 完全标准的EMA算法

        Args:
            n: 周期
            array: 是否返回数组

        Returns:
            指数移动平均值或数组
        """
        if not self.inited:
            return 0

        # 🎯 完全标准的EMA算法
        alpha = 2.0 / (n + 1)  # 平滑因子

        # 获取所有有效数据（不只是最近n个）
        all_data = self.close_array[self.close_array != 0]  # 过滤掉初始化的0值

        if len(all_data) < n:
            return 0

        # 标准EMA算法：
        # 1. 初始EMA = 前n个数据的SMA
        initial_sma = np.mean(all_data[:n])
        ema = initial_sma

        # 2. 从第n+1个数据开始，逐个计算EMA
        for i in range(n, len(all_data)):
            ema = alpha * all_data[i] + (1 - alpha) * ema

        if array:
            # 返回EMA序列
            ema_values = []
            current_ema = initial_sma
            ema_values.append(current_ema)

            for i in range(n, len(all_data)):
                current_ema = alpha * all_data[i] + (1 - alpha) * current_ema
                ema_values.append(current_ema)

            return np.array(ema_values)
        else:
            return ema
    
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
        相对强弱指标 - 使用EMA计算（标准算法）

        Args:
            n: 周期
            array: 是否返回数组

        Returns:
            RSI值或数组
        """
        if not self.inited or len(self.close_array) < n + 1:
            return 50

        # 获取有效数据（过滤掉初始化的0值）
        all_data = self.close_array[self.close_array != 0]

        if len(all_data) < n + 1:
            return 50

        # 计算价格变化
        diff = np.diff(all_data)
        gains = np.where(diff > 0, diff, 0)
        losses = np.where(diff < 0, -diff, 0)

        # 🎯 使用EMA计算平均收益和损失（标准RSI算法）
        alpha = 1.0 / n  # EMA平滑因子

        # 初始化：使用前n个值的SMA作为起始值
        if len(gains) >= n:
            avg_gain = np.mean(gains[:n])
            avg_loss = np.mean(losses[:n])

            # 从第n+1个值开始使用EMA
            for i in range(n, len(gains)):
                avg_gain = alpha * gains[i] + (1 - alpha) * avg_gain
                avg_loss = alpha * losses[i] + (1 - alpha) * avg_loss
        else:
            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 1e-10

        # 避免除零
        if avg_loss == 0:
            avg_loss = 1e-10

        # 计算RSI
        rs = avg_gain / avg_loss
        rsi_value = 100 - (100 / (1 + rs))

        if array:
            # 如果需要数组，计算所有历史RSI值
            rsi_array = []
            if len(gains) >= n:
                # 初始RSI
                init_avg_gain = np.mean(gains[:n])
                init_avg_loss = np.mean(losses[:n])
                if init_avg_loss == 0:
                    init_avg_loss = 1e-10
                init_rs = init_avg_gain / init_avg_loss
                rsi_array.append(100 - (100 / (1 + init_rs)))

                # 后续RSI
                avg_gain = init_avg_gain
                avg_loss = init_avg_loss
                for i in range(n, len(gains)):
                    avg_gain = alpha * gains[i] + (1 - alpha) * avg_gain
                    avg_loss = alpha * losses[i] + (1 - alpha) * avg_loss
                    rs = avg_gain / avg_loss
                    rsi_array.append(100 - (100 / (1 + rs)))

            return np.array(rsi_array) if rsi_array else np.array([50])

        return rsi_value
    
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
        
        middle = self.ema(n)
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


# TechnicalIndicators 已移除（与 ArrayManager 的指标方法重复）
