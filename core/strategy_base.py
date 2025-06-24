"""
策略基类
定义策略与事件引擎对接的标准接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .event_engine import Event, EventEngine
from .constants import *

class StrategyBase(ABC):
    """
    策略基类
    所有策略都应该继承此类并实现相应方法
    """
    
    def __init__(self, name: str, event_engine: EventEngine, config: Dict[str, Any]):
        """
        初始化策略
        
        Args:
            name: 策略名称
            event_engine: 事件引擎实例
            config: 策略配置
        """
        self.name = name
        self.event_engine = event_engine
        self.config = config
        self.active = False
        
        # 注意：不再自动注册事件处理函数
        # 事件分发由主控制器统一管理，避免多个策略同时处理相同事件
        
    def start(self):
        """启动策略"""
        self.active = True
        self.on_start()
        
    def stop(self):
        """停止策略"""
        self.active = False
        self.on_stop()
        
    def send_signal(self, signal_data: Dict[str, Any]):
        """发送策略信号"""
        event = Event(SIGNAL_EVENT, {
            'strategy_name': self.name,
            'data': signal_data
        })
        self.event_engine.put(event)
        
    # 抽象方法，子类必须实现
    @abstractmethod
    def on_start(self):
        """策略启动时调用"""
        pass
        
    @abstractmethod
    def on_stop(self):
        """策略停止时调用"""
        pass
        
    @abstractmethod
    def on_tick(self, event: Event):
        """Tick事件处理"""
        pass
        
    @abstractmethod
    def on_bar(self, event: Event):
        """K线事件处理"""
        pass
        
    @abstractmethod
    def on_order(self, event: Event):
        """订单事件处理"""
        pass
        
    @abstractmethod
    def on_trade(self, event: Event):
        """成交事件处理"""
        pass
        
    @abstractmethod
    def on_account(self, event: Event):
        """账户事件处理"""
        pass 