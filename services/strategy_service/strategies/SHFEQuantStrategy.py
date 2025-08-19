"""
上海期货量化策略 - vnpy风格版本
基于ARBIGCtaTemplate实现的综合量化交易策略
包含趋势跟踪、均值回归、突破等多种策略类型
"""

import time
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from vnpy.trader.utility import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyType(Enum):
    """策略类型枚举"""
    TREND = "trend"              # 趋势跟踪
    MEAN_REVERSION = "mean_reversion"  # 均值回归
    BREAKOUT = "breakout"        # 突破策略


class MarketDirection(Enum):
    """市场方向枚举"""
    LONG = "LONG"
    SHORT = "SHORT"  
    NEUTRAL = "NEUTRAL"


class SHFEQuantStrategy(ARBIGCtaTemplate):
    """
    上海期货量化策略 - vnpy风格实现
    
    策略特点：
    1. 多策略类型：趋势、均值回归、突破
    2. 动态方向判断
    3. 智能仓位管理
    4. 风险控制
    """
    
    # 策略参数
    strategy_type = "trend"       # 策略类型
    ma_short = 5                  # 短期均线
    ma_long = 20                  # 长期均线
    rsi_period = 14              # RSI周期
    rsi_overbought = 70          # RSI超买线
    rsi_oversold = 30            # RSI超卖线
    
    bollinger_period = 20        # 布林带周期
    bollinger_std = 2.0          # 布林带标准差
    
    stop_loss_pct = 0.05         # 止损比例
    take_profit_pct = 0.08       # 止盈比例
    
    trade_volume = 1             # 基础交易手数
    max_position = 10            # 最大持仓
    
    min_signal_interval = 300    # 最小信号间隔(秒)
    
    # 策略变量
    current_direction = MarketDirection.NEUTRAL
    direction_confidence = 0.0
    entry_price = 0.0
    last_signal_time = 0
    signal_count = 0
    
    def __init__(self, strategy_engine, strategy_name: str, symbol: str, setting: dict):
        """初始化策略"""
        super().__init__(strategy_engine, strategy_name, symbol, setting)
        
        # 从设置中获取参数
        self.strategy_type = setting.get('strategy_type', self.strategy_type)
        self.ma_short = setting.get('ma_short', self.ma_short)
        self.ma_long = setting.get('ma_long', self.ma_long)
        self.rsi_period = setting.get('rsi_period', self.rsi_period)
        self.rsi_overbought = setting.get('rsi_overbought', self.rsi_overbought)
        self.rsi_oversold = setting.get('rsi_oversold', self.rsi_oversold)
        
        self.bollinger_period = setting.get('bollinger_period', self.bollinger_period)
        self.bollinger_std = setting.get('bollinger_std', self.bollinger_std)
        
        self.stop_loss_pct = setting.get('stop_loss_pct', self.stop_loss_pct)
        self.take_profit_pct = setting.get('take_profit_pct', self.take_profit_pct)
        
        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)
        self.min_signal_interval = setting.get('min_signal_interval', self.min_signal_interval)
        
        # 初始化ArrayManager
        self.am = ArrayManager(size=max(self.ma_long * 2, 100))
        
        # 解析策略类型
        if isinstance(self.strategy_type, str):
            try:
                self.strategy_type = StrategyType(self.strategy_type)
            except ValueError:
                self.strategy_type = StrategyType.TREND
                
        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   策略类型: {self.strategy_type.value}")
        logger.info(f"   技术指标: MA({self.ma_short}/{self.ma_long}) RSI({self.rsi_period})")
        logger.info(f"   风险控制: 止损{self.stop_loss_pct*100}% 止盈{self.take_profit_pct*100}%")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log(f"上海期货量化策略初始化 - {self.strategy_type.value}")
        
    def on_start(self):
        """策略启动回调"""
        self.write_log(f"🚀 上海期货量化策略已启动 - {self.strategy_type.value}")
        
    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 上海期货量化策略已停止")
        
    def on_tick(self, tick: TickData):
        """处理tick数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager
        self.am.update_tick(tick)
        
        # 检查风险控制
        self._check_risk_control(tick.last_price)
        
    def on_bar(self, bar: BarData):
        """处理bar数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager
        self.am.update_bar(bar)
        
        # 确保有足够的数据
        if not self.am.inited:
            return
            
        # 检查信号间隔
        current_time = time.time()
        if current_time - self.last_signal_time < self.min_signal_interval:
            return
            
        # 更新市场方向判断
        self._update_market_direction(bar)
        
        # 生成交易信号
        self._generate_trading_signal(bar)
        
    def _update_market_direction(self, bar: BarData):
        """更新市场方向判断"""
        if not self.am.inited:
            return
            
        # 使用布林带判断市场方向
        upper, middle, lower = self._calculate_bollinger_bands()
        current_price = bar.close_price
        
        # 计算突破强度
        if current_price > upper:
            breakout_strength = (current_price - upper) / upper * 100
            if breakout_strength > 0.5:
                self.current_direction = MarketDirection.LONG
                self.direction_confidence = min(breakout_strength / 2.0, 1.0)
        elif current_price < lower:
            breakout_strength = (lower - current_price) / lower * 100
            if breakout_strength > 0.5:
                self.current_direction = MarketDirection.SHORT
                self.direction_confidence = min(breakout_strength / 2.0, 1.0)
        else:
            self.current_direction = MarketDirection.NEUTRAL
            self.direction_confidence = 0.0
            
        # 结合趋势确认方向
        ma_short = self.am.sma(self.ma_short)
        ma_long = self.am.sma(self.ma_long)
        
        if ma_short > ma_long and self.current_direction == MarketDirection.LONG:
            self.direction_confidence *= 1.2
        elif ma_short < ma_long and self.current_direction == MarketDirection.SHORT:
            self.direction_confidence *= 1.2
        else:
            self.direction_confidence *= 0.8
            
        self.direction_confidence = min(self.direction_confidence, 1.0)
        
    def _generate_trading_signal(self, bar: BarData):
        """生成交易信号"""
        signal = None
        reason = ""
        
        if self.strategy_type == StrategyType.TREND:
            signal, reason = self._trend_strategy()
        elif self.strategy_type == StrategyType.MEAN_REVERSION:
            signal, reason = self._mean_reversion_strategy()
        elif self.strategy_type == StrategyType.BREAKOUT:
            signal, reason = self._breakout_strategy()
            
        if signal:
            # 根据方向判断调整信号
            adjusted_signal = self._adjust_signal_by_direction(signal)
            if adjusted_signal:
                self._execute_signal(adjusted_signal, bar.close_price, reason)
                
    def _trend_strategy(self) -> tuple:
        """趋势跟踪策略"""
        ma_short = self.am.sma(self.ma_short)
        ma_long = self.am.sma(self.ma_long)
        
        if ma_short > ma_long and self.pos <= 0:
            return "BUY", f"均线金叉 MA{self.ma_short}({ma_short:.2f}) > MA{self.ma_long}({ma_long:.2f})"
        elif ma_short < ma_long and self.pos >= 0:
            return "SELL", f"均线死叉 MA{self.ma_short}({ma_short:.2f}) < MA{self.ma_long}({ma_long:.2f})"
            
        return None, ""
        
    def _mean_reversion_strategy(self) -> tuple:
        """均值回归策略"""
        rsi = self.am.rsi(self.rsi_period)
        
        if rsi < self.rsi_oversold and self.pos <= 0:
            return "BUY", f"RSI超卖 ({rsi:.1f})"
        elif rsi > self.rsi_overbought and self.pos >= 0:
            return "SELL", f"RSI超买 ({rsi:.1f})"
            
        return None, ""
        
    def _breakout_strategy(self) -> tuple:
        """突破策略"""
        upper, middle, lower = self._calculate_bollinger_bands()
        current_price = self.am.close_array[-1]
        
        if current_price > upper and self.pos <= 0:
            strength = (current_price - upper) / upper * 100
            if strength > 0.5:
                return "BUY", f"上轨突破 强度{strength:.2f}%"
        elif current_price < lower and self.pos >= 0:
            strength = (lower - current_price) / lower * 100
            if strength > 0.5:
                return "SELL", f"下轨突破 强度{strength:.2f}%"
                
        return None, ""
        
    def _adjust_signal_by_direction(self, original_signal: str) -> Optional[str]:
        """根据方向判断调整交易信号"""
        # 如果方向判断置信度不够，使用原始信号
        if self.direction_confidence < 0.3:
            return original_signal
            
        # 根据方向判断调整信号
        if self.current_direction == MarketDirection.LONG:
            if original_signal == "BUY":
                return "BUY"
            elif original_signal == "SELL" and self.pos > 0:
                return "SELL"  # 只平多，不开空
        elif self.current_direction == MarketDirection.SHORT:
            if original_signal == "SELL":
                return "SELL"
            elif original_signal == "BUY" and self.pos < 0:
                return "BUY"  # 只平空，不开多
        else:  # NEUTRAL
            return original_signal
            
        return None
        
    def _execute_signal(self, signal: str, price: float, reason: str):
        """执行交易信号"""
        # 检查持仓限制
        if abs(self.pos) >= self.max_position:
            self.write_log(f"已达最大持仓 {self.max_position}，忽略信号: {signal}")
            return
            
        # 计算交易手数（根据置信度调整）
        volume = self._calculate_position_size()
        if volume <= 0:
            return
            
        self.signal_count += 1
        
        if signal == "BUY":
            self.buy(price, volume, stop=False)
            if self.pos <= 0:  # 开多仓
                self.entry_price = price
                
        elif signal == "SELL":
            self.sell(price, volume, stop=False)
            if self.pos >= 0:  # 开空仓
                self.entry_price = price
                
        self.last_signal_time = time.time()
        
        self.write_log(f"📊 信号 #{self.signal_count}: {signal} {volume}手")
        self.write_log(f"   原因: {reason}")
        self.write_log(f"   方向: {self.current_direction.value} 置信度: {self.direction_confidence:.2f}")
        self.write_log(f"   价格: {price:.2f}, 持仓: {self.pos}")
        
    def _calculate_position_size(self) -> int:
        """计算交易仓位"""
        # 基础仓位
        base_volume = self.trade_volume
        
        # 根据方向置信度调整
        if self.direction_confidence > 0.7:
            multiplier = 1.0
        elif self.direction_confidence > 0.5:
            multiplier = 0.8
        else:
            multiplier = 0.5
            
        volume = int(base_volume * multiplier)
        
        # 确保不超过最大持仓
        available = self.max_position - abs(self.pos)
        volume = min(volume, available)
        
        return max(volume, 0)
        
    def _calculate_bollinger_bands(self) -> tuple:
        """计算布林带"""
        if len(self.am.close_array) < self.bollinger_period:
            return (float('inf'), 0, float('-inf'))
            
        prices = self.am.close_array[-self.bollinger_period:]
        middle = np.mean(prices)
        std = np.std(prices)
        
        upper = middle + (self.bollinger_std * std)
        lower = middle - (self.bollinger_std * std)
        
        return (upper, middle, lower)
        
    def _check_risk_control(self, current_price: float):
        """检查风险控制"""
        if self.pos == 0 or self.entry_price == 0:
            return
            
        # 计算盈亏比例
        if self.pos > 0:  # 多头持仓
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:  # 空头持仓
            pnl_pct = (self.entry_price - current_price) / self.entry_price
            
        # 止损
        if pnl_pct <= -self.stop_loss_pct:
            self._close_all_positions(current_price, "止损")
            
        # 止盈
        elif pnl_pct >= self.take_profit_pct:
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
        
        # 更新入场价格
        if trade.offset.value == "开仓":
            self.entry_price = trade.price
        elif abs(self.pos) == 0:
            self.entry_price = 0.0
            
        # 大额成交通知
        if abs(trade.volume) >= 5:
            self.send_email(f"大额成交: {trade.direction} {trade.volume}手")
            
    def on_stop_order(self, stop_order):
        """处理停止单回调"""
        self.write_log(f"停止单触发: {stop_order.orderid}")
        
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        if not self.am.inited:
            return {"status": "数据不足"}
            
        upper, middle, lower = self._calculate_bollinger_bands()
        
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "strategy_type": self.strategy_type.value,
            "position": self.pos,
            "entry_price": self.entry_price,
            "signal_count": self.signal_count,
            "direction": self.current_direction.value,
            "direction_confidence": self.direction_confidence,
            "indicators": {
                "ma_short": self.am.sma(self.ma_short),
                "ma_long": self.am.sma(self.ma_long),
                "rsi": self.am.rsi(self.rsi_period),
                "bollinger_upper": upper,
                "bollinger_middle": middle,
                "bollinger_lower": lower
            },
            "last_price": self.am.close_array[-1] if len(self.am.close_array) > 0 else 0
        }


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> SHFEQuantStrategy:
    """创建上海期货量化策略实例"""
    
    # 默认设置
    default_setting = {
        'strategy_type': 'trend',
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'bollinger_period': 20,
        'bollinger_std': 2.0,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.08,
        'trade_volume': 1,
        'max_position': 10,
        'min_signal_interval': 300
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return SHFEQuantStrategy(strategy_engine, strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "SHFEQuantStrategy",
    "file_name": "shfe_quant_strategy.py",
    "description": "上海期货综合量化策略，支持趋势、均值回归、突破等多种策略类型",
    "parameters": {
        "strategy_type": {
            "type": "str",
            "default": "trend",
            "options": ["trend", "mean_reversion", "breakout"],
            "description": "策略类型"
        },
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
        "bollinger_period": {
            "type": "int",
            "default": 20,
            "description": "布林带周期"
        },
        "bollinger_std": {
            "type": "float",
            "default": 2.0,
            "description": "布林带标准差倍数"
        },
        "stop_loss_pct": {
            "type": "float",
            "default": 0.05,
            "description": "止损百分比"
        },
        "take_profit_pct": {
            "type": "float",
            "default": 0.08,
            "description": "止盈百分比"
        },
        "trade_volume": {
            "type": "int",
            "default": 1,
            "description": "基础交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 10,
            "description": "最大持仓手数"
        },
        "min_signal_interval": {
            "type": "int",
            "default": 300,
            "description": "最小信号间隔(秒)"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("上海期货量化策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
