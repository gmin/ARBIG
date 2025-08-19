"""
简化SHFE策略 - vnpy风格版本
基于ARBIGCtaTemplate实现的上期所黄金期货交易策略
包含趋势跟踪和均值回归逻辑
"""

import time
from typing import Dict, Any
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from vnpy.trader.utility import ArrayManager
from utils.logger import get_logger

logger = get_logger(__name__)


class SimpleSHFEStrategy(ARBIGCtaTemplate):
    """
    简化SHFE策略 - vnpy风格实现
    
    策略逻辑：
    1. 基于双均线的趋势跟踪
    2. RSI超买超卖的均值回归
    3. 简单的风险控制
    4. 固定止损止盈
    """
    
    # 策略参数
    ma_short = 5          # 短期均线周期
    ma_long = 20          # 长期均线周期
    rsi_period = 14       # RSI计算周期
    rsi_overbought = 70   # RSI超买线
    rsi_oversold = 30     # RSI超卖线
    
    stop_loss_pct = 0.02  # 止损百分比 (2%)
    take_profit_pct = 0.03 # 止盈百分比 (3%)
    
    trade_volume = 1      # 每次交易手数
    max_position = 5      # 最大持仓
    
    # 策略变量
    entry_price = 0.0     # 入场价格
    last_signal_time = 0  # 上次信号时间
    signal_count = 0      # 信号计数
    
    def __init__(self, strategy_engine, strategy_name: str, symbol: str, setting: dict):
        """初始化策略"""
        super().__init__(strategy_engine, strategy_name, symbol, setting)
        
        # 从设置中获取参数
        self.ma_short = setting.get('ma_short', self.ma_short)
        self.ma_long = setting.get('ma_long', self.ma_long)
        self.rsi_period = setting.get('rsi_period', self.rsi_period)
        self.rsi_overbought = setting.get('rsi_overbought', self.rsi_overbought)
        self.rsi_oversold = setting.get('rsi_oversold', self.rsi_oversold)
        
        self.stop_loss_pct = setting.get('stop_loss_pct', self.stop_loss_pct)
        self.take_profit_pct = setting.get('take_profit_pct', self.take_profit_pct)
        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)
        
        # 初始化ArrayManager
        self.am = ArrayManager()
        
        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   双均线: {self.ma_short}/{self.ma_long}")
        logger.info(f"   RSI参数: {self.rsi_period}({self.rsi_oversold}-{self.rsi_overbought})")
        logger.info(f"   风控: 止损{self.stop_loss_pct*100}% 止盈{self.take_profit_pct*100}%")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("简化SHFE策略初始化")
        
    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 简化SHFE策略已启动")
        
    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 简化SHFE策略已停止")
        
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
            
        # 检查信号间隔（避免频繁交易）
        current_time = time.time()
        if current_time - self.last_signal_time < 60:  # 1分钟间隔
            return
            
        # 生成交易信号
        self._generate_trading_signal(bar)
        
    def _generate_trading_signal(self, bar: BarData):
        """生成交易信号"""
        # 计算技术指标
        ma_short = self.am.sma(self.ma_short)
        ma_long = self.am.sma(self.ma_long)
        rsi = self.am.rsi(self.rsi_period)
        
        current_price = bar.close_price
        signal = None
        reason = ""
        
        # 趋势信号：双均线交叉
        if ma_short > ma_long and self.pos <= 0:
            # 短均线上穿长均线，且当前无多头持仓
            if rsi < self.rsi_overbought:  # 避免在超买区域买入
                signal = "BUY"
                reason = f"双均线金叉 + RSI({rsi:.1f})"
                
        elif ma_short < ma_long and self.pos >= 0:
            # 短均线下穿长均线，且当前无空头持仓
            if rsi > self.rsi_oversold:  # 避免在超卖区域卖出
                signal = "SELL" 
                reason = f"双均线死叉 + RSI({rsi:.1f})"
        
        # 均值回归信号：RSI极值
        elif rsi < self.rsi_oversold and self.pos <= 0:
            # RSI超卖，买入
            signal = "BUY"
            reason = f"RSI超卖({rsi:.1f})"
            
        elif rsi > self.rsi_overbought and self.pos >= 0:
            # RSI超买，卖出
            signal = "SELL"
            reason = f"RSI超买({rsi:.1f})"
        
        # 执行交易信号
        if signal:
            self._execute_signal(signal, current_price, reason)
            
    def _execute_signal(self, signal: str, price: float, reason: str):
        """执行交易信号"""
        # 检查持仓限制
        if abs(self.pos) >= self.max_position:
            self.write_log(f"已达最大持仓 {self.max_position}，忽略信号: {signal}")
            return
            
        self.signal_count += 1
        
        if signal == "BUY":
            self.buy(price, self.trade_volume, stop=False)
            self.entry_price = price
            
        elif signal == "SELL":
            self.sell(price, self.trade_volume, stop=False)
            self.entry_price = price
            
        self.last_signal_time = time.time()
        
        self.write_log(f"📊 信号 #{self.signal_count}: {signal}")
        self.write_log(f"   原因: {reason}")
        self.write_log(f"   价格: {price:.2f}, 持仓: {self.pos}")
        
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
        
        # 如果是开仓成交，记录入场价格
        if trade.offset.value == "开仓":
            self.entry_price = trade.price
            
        # 如果是平仓成交，重置入场价格
        elif abs(self.pos) == 0:
            self.entry_price = 0.0
            
        # 重要成交发送邮件通知
        if abs(trade.volume) >= 3:
            self.send_email(f"大额成交: {trade.direction} {trade.volume}手")
            
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
            "entry_price": self.entry_price,
            "signal_count": self.signal_count,
            "indicators": {
                "ma_short": self.am.sma(self.ma_short),
                "ma_long": self.am.sma(self.ma_long),
                "rsi": self.am.rsi(self.rsi_period)
            },
            "last_price": self.am.close_array[-1] if len(self.am.close_array) > 0 else 0
        }


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> SimpleSHFEStrategy:
    """创建简化SHFE策略实例"""
    
    # 默认设置
    default_setting = {
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.03,
        'trade_volume': 1,
        'max_position': 5
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return SimpleSHFEStrategy(strategy_engine, strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "SimpleSHFEStrategy",
    "file_name": "simple_shfe_strategy.py", 
    "description": "简化的上期所黄金期货交易策略，基于双均线和RSI",
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
            "default": 0.02,
            "description": "止损百分比"
        },
        "take_profit_pct": {
            "type": "float",
            "default": 0.03,
            "description": "止盈百分比"
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
