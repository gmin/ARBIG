"""
行情订阅服务
负责统一管理行情订阅、数据分发和缓存
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict

from ..event_engine import EventEngine, Event
from ..types import (
    TickData, ServiceStatus, ServiceConfig, MarketSnapshot,
    TickEventData
)
from ..constants import TICK_EVENT, SERVICE_EVENT
from ...utils.logger import get_logger

logger = get_logger(__name__)

class MarketDataServiceBase(ABC):
    """行情服务基类"""
    
    def __init__(self, event_engine: EventEngine, config: ServiceConfig):
        """
        初始化行情服务
        
        Args:
            event_engine: 事件引擎
            config: 服务配置
        """
        self.event_engine = event_engine
        self.config = config
        self.status = ServiceStatus.STOPPED
        
        # 订阅管理
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # symbol -> subscriber_ids
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)    # subscriber_id -> symbols
        
        # 数据缓存
        self.tick_cache: Dict[str, TickData] = {}
        self.last_update_time: Optional[datetime] = None
        
        # 回调函数
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        
        logger.info(f"行情服务初始化完成: {self.config.name}")
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动服务
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止服务"""
        pass
    
    @abstractmethod
    def _subscribe_symbol_impl(self, symbol: str) -> bool:
        """
        实际的订阅实现（由子类实现）
        
        Args:
            symbol: 合约代码
            
        Returns:
            bool: 订阅是否成功
        """
        pass
    
    @abstractmethod
    def _unsubscribe_symbol_impl(self, symbol: str) -> bool:
        """
        实际的取消订阅实现（由子类实现）
        
        Args:
            symbol: 合约代码
            
        Returns:
            bool: 取消订阅是否成功
        """
        pass
    
    def subscribe_symbol(self, symbol: str, subscriber_id: str) -> bool:
        """
        订阅合约行情
        
        Args:
            symbol: 合约代码
            subscriber_id: 订阅者ID
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            # 检查服务状态
            if self.status != ServiceStatus.RUNNING:
                logger.error(f"服务未运行，无法订阅: {symbol}")
                return False
            
            # 添加订阅关系
            was_subscribed = len(self.subscriptions[symbol]) > 0
            self.subscriptions[symbol].add(subscriber_id)
            self.subscribers[subscriber_id].add(symbol)
            
            # 如果是新的合约订阅，调用实际订阅
            if not was_subscribed:
                success = self._subscribe_symbol_impl(symbol)
                if not success:
                    # 订阅失败，回滚
                    self.subscriptions[symbol].discard(subscriber_id)
                    self.subscribers[subscriber_id].discard(symbol)
                    return False
            
            logger.info(f"订阅成功: {symbol} by {subscriber_id}")
            return True
            
        except Exception as e:
            logger.error(f"订阅失败: {symbol} by {subscriber_id}, 错误: {e}")
            return False
    
    def unsubscribe_symbol(self, symbol: str, subscriber_id: str) -> bool:
        """
        取消订阅合约行情
        
        Args:
            symbol: 合约代码
            subscriber_id: 订阅者ID
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            # 移除订阅关系
            self.subscriptions[symbol].discard(subscriber_id)
            self.subscribers[subscriber_id].discard(symbol)
            
            # 如果没有其他订阅者，取消实际订阅
            if len(self.subscriptions[symbol]) == 0:
                success = self._unsubscribe_symbol_impl(symbol)
                if success:
                    # 清理空的订阅记录
                    del self.subscriptions[symbol]
                    # 清理缓存
                    self.tick_cache.pop(symbol, None)
            
            logger.info(f"取消订阅成功: {symbol} by {subscriber_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消订阅失败: {symbol} by {subscriber_id}, 错误: {e}")
            return False
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取最新Tick数据
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[TickData]: 最新Tick数据
        """
        return self.tick_cache.get(symbol)
    
    def get_market_snapshot(self) -> MarketSnapshot:
        """
        获取市场快照
        
        Returns:
            MarketSnapshot: 市场快照
        """
        return MarketSnapshot(
            timestamp=datetime.now(),
            symbols=self.tick_cache.copy()
        )
    
    def get_subscription_status(self) -> Dict[str, List[str]]:
        """
        获取订阅状态
        
        Returns:
            Dict[str, List[str]]: 合约代码 -> 订阅者列表
        """
        return {symbol: list(subscribers) 
                for symbol, subscribers in self.subscriptions.items()}
    
    def get_subscribed_symbols(self) -> List[str]:
        """
        获取已订阅的合约列表
        
        Returns:
            List[str]: 合约代码列表
        """
        return list(self.subscriptions.keys())
    
    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """
        添加Tick数据回调函数
        
        Args:
            callback: 回调函数
        """
        if callback not in self.tick_callbacks:
            self.tick_callbacks.append(callback)
    
    def remove_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """
        移除Tick数据回调函数
        
        Args:
            callback: 回调函数
        """
        if callback in self.tick_callbacks:
            self.tick_callbacks.remove(callback)
    
    def on_tick(self, tick: TickData) -> None:
        """
        处理Tick数据
        
        Args:
            tick: Tick数据
        """
        try:
            # 更新缓存
            self.tick_cache[tick.symbol] = tick
            self.last_update_time = datetime.now()
            
            # 调用回调函数
            for callback in self.tick_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Tick回调函数执行失败: {e}")
            
            # 发送事件
            event_data = TickEventData(tick=tick, source="market_data")
            event = Event(TICK_EVENT, event_data)
            self.event_engine.put(event)
            
            logger.debug(f"处理Tick数据: {tick.symbol} @ {tick.last_price}")
            
        except Exception as e:
            logger.error(f"处理Tick数据失败: {e}")
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取服务统计信息
        
        Returns:
            Dict[str, any]: 统计信息
        """
        return {
            'status': self.status.value,
            'subscribed_symbols': len(self.subscriptions),
            'total_subscribers': sum(len(subs) for subs in self.subscriptions.values()),
            'cached_ticks': len(self.tick_cache),
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'symbols': list(self.subscriptions.keys())
        }

class MarketDataService(MarketDataServiceBase):
    """行情订阅服务实现"""

    def __init__(self, event_engine: EventEngine, config: ServiceConfig, gateway=None):
        """
        初始化行情服务

        Args:
            event_engine: 事件引擎
            config: 服务配置
            gateway: CTP网关实例
        """
        super().__init__(event_engine, config)
        self.gateway = gateway

        # 如果有网关，注册Tick回调
        if self.gateway:
            self.gateway.add_tick_callback(self.on_tick)
    
    def start(self) -> bool:
        """启动服务"""
        try:
            if self.status == ServiceStatus.RUNNING:
                logger.warning("行情服务已在运行")
                return True
            
            self.status = ServiceStatus.STARTING
            
            # 检查网关连接
            if not self.gateway:
                logger.error("CTP网关未设置")
                self.status = ServiceStatus.ERROR
                return False
            
            # 自动订阅配置中的合约
            symbols = self.config.config.get('symbols', [])
            for symbol in symbols:
                self.subscribe_symbol(symbol, 'system')
            
            self.status = ServiceStatus.RUNNING
            logger.info("行情服务启动成功")
            return True
            
        except Exception as e:
            logger.error(f"行情服务启动失败: {e}")
            self.status = ServiceStatus.ERROR
            return False
    
    def stop(self) -> None:
        """停止服务"""
        try:
            if self.status == ServiceStatus.STOPPED:
                return
            
            self.status = ServiceStatus.STOPPING
            
            # 取消所有订阅
            symbols_to_unsubscribe = list(self.subscriptions.keys())
            for symbol in symbols_to_unsubscribe:
                self._unsubscribe_symbol_impl(symbol)
            
            # 清理数据
            self.subscriptions.clear()
            self.subscribers.clear()
            self.tick_cache.clear()
            self.tick_callbacks.clear()
            
            self.status = ServiceStatus.STOPPED
            logger.info("行情服务已停止")
            
        except Exception as e:
            logger.error(f"停止行情服务失败: {e}")
            self.status = ServiceStatus.ERROR
    
    def _subscribe_symbol_impl(self, symbol: str) -> bool:
        """实际的订阅实现"""
        try:
            if self.gateway and self.gateway.is_md_connected():
                # 调用CTP网关的订阅方法
                success = self.gateway.subscribe(symbol, "SHFE")
                if success:
                    logger.info(f"CTP订阅成功: {symbol}")
                else:
                    logger.error(f"CTP订阅失败: {symbol}")
                return success
            else:
                logger.error(f"CTP网关未连接，无法订阅: {symbol}")
                return False
        except Exception as e:
            logger.error(f"订阅合约失败: {symbol}, 错误: {e}")
            return False

    def _unsubscribe_symbol_impl(self, symbol: str) -> bool:
        """实际的取消订阅实现"""
        try:
            if self.gateway:
                # 调用CTP网关的取消订阅方法
                success = self.gateway.unsubscribe(symbol, "SHFE")
                if success:
                    logger.info(f"CTP取消订阅成功: {symbol}")
                else:
                    logger.error(f"CTP取消订阅失败: {symbol}")
                return success
            return False
        except Exception as e:
            logger.error(f"取消订阅合约失败: {symbol}, 错误: {e}")
            return False
