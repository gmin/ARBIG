"""
测试策略 - vnpy风格版本
基于ARBIGCtaTemplate实现的简单测试策略
用于系统集成测试和功能验证
"""

import time
import random
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


class TestStrategy(ARBIGCtaTemplate):
    """
    测试策略 - vnpy风格实现
    
    策略逻辑：
    1. 每隔N秒生成一个随机信号
    2. 买入/卖出概率各50%
    3. 固定手数交易
    4. 无复杂指标计算
    """
    
    # 策略参数
    signal_interval = 30  # 信号间隔(秒)
    trade_volume = 1      # 交易手数
    max_position = 3      # 最大持仓
    
    # 策略变量
    last_signal_time = 0
    signal_count = 0
    
    def __init__(self, strategy_engine, strategy_name: str, symbol: str, setting: dict):
        """初始化策略"""
        super().__init__(strategy_engine, strategy_name, symbol, setting)
        
        # 从设置中获取参数
        self.signal_interval = setting.get('signal_interval', self.signal_interval)
        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)
        
        # 初始化ArrayManager用于数据管理（虽然这个策略不需要复杂计算）
        self.am = ArrayManager()
        
        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   信号间隔: {self.signal_interval}秒")
        logger.info(f"   交易手数: {self.trade_volume}")
        logger.info(f"   最大持仓: {self.max_position}")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("测试策略初始化")
        
    def on_start(self):
        """策略启动回调"""
        self.last_signal_time = time.time()
        self.write_log("🚀 测试策略已启动")
        
    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 测试策略已停止")
        
    def on_tick(self, tick: TickData):
        """处理tick数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager（虽然不使用，但保持vnpy风格）
        self.am.update_tick(tick)
        
        current_time = time.time()
        
        # 检查是否到了生成信号的时间
        if current_time - self.last_signal_time < self.signal_interval:
            return
            
        # 生成随机信号
        self._generate_test_signal(tick)
        self.last_signal_time = current_time
        
    def on_bar(self, bar: BarData):
        """处理bar数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager
        self.am.update_bar(bar)
        
        # 确保有足够的数据
        if not self.am.inited:
            return
            
        # 这个测试策略主要基于tick，bar处理可以为空
        pass
        
    def _generate_test_signal(self, tick: TickData):
        """生成测试信号"""
        current_price = tick.last_price
        
        # 30%概率不生成信号
        if random.random() < 0.3:
            return
            
        self.signal_count += 1
        
        # 检查持仓限制
        if abs(self.pos) >= self.max_position:
            # 如果已达最大持仓，只能平仓
            if self.pos > 0:
                self.sell(current_price, self.trade_volume, stop=False)
                reason = "多头持仓已满，平仓"
            elif self.pos < 0:
                self.buy(current_price, self.trade_volume, stop=False)
                reason = "空头持仓已满，平仓"
            else:
                return
        else:
            # 随机选择买入或卖出
            action = random.choice(['BUY', 'SELL'])
            
            if action == 'BUY':
                self.buy(current_price, self.trade_volume, stop=False)
                reason = f"随机信号 - 买入"
            else:
                self.sell(current_price, self.trade_volume, stop=False)
                reason = f"随机信号 - 卖出"
        
        self.write_log(f"📊 生成信号 #{self.signal_count}: {reason}")
        self.write_log(f"   价格: {current_price:.2f}, 持仓: {self.pos}")
        
    def on_order(self, order):
        """处理订单回调"""
        self.write_log(f"订单状态: {order.orderid} - {order.status}")
        
    def on_trade(self, trade):
        """处理成交回调"""
        self.write_log(f"✅ 成交: {trade.direction} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"   当前持仓: {self.pos}")
        
        # 发送邮件通知（如果配置了）
        if abs(self.pos) >= self.max_position:
            self.send_email(f"测试策略达到最大持仓: {self.pos}")
            
    def on_stop_order(self, stop_order):
        """处理停止单回调"""
        self.write_log(f"停止单触发: {stop_order.orderid}")


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> TestStrategy:
    """创建测试策略实例"""
    
    # 默认设置
    default_setting = {
        'signal_interval': 30,  # 30秒生成一次信号
        'trade_volume': 1,      # 每次交易1手
        'max_position': 3       # 最大持仓3手
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return TestStrategy(strategy_engine, strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "TestStrategy",
    "file_name": "test_strategy.py",
    "description": "简单测试策略，用于系统功能验证",
    "parameters": {
        "signal_interval": {
            "type": "int",
            "default": 30,
            "description": "信号生成间隔(秒)"
        },
        "trade_volume": {
            "type": "int", 
            "default": 1,
            "description": "每次交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 3,
            "description": "最大持仓手数"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("测试策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
