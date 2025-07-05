"""
账户信息服务
负责账户资金、持仓信息的管理（混合模式：查询+推送）
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

from ..event_engine import EventEngine, Event
from ..types import (
    AccountData, PositionData, OrderData, TradeData,
    ServiceStatus, ServiceConfig, AccountSnapshot
)
from ..constants import ACCOUNT_EVENT, POSITION_EVENT, ORDER_EVENT, TRADE_EVENT
from ...utils.logger import get_logger

logger = get_logger(__name__)

class AccountServiceBase(ABC):
    """账户服务基类"""
    
    def __init__(self, event_engine: EventEngine, config: ServiceConfig):
        """
        初始化账户服务
        
        Args:
            event_engine: 事件引擎
            config: 服务配置
        """
        self.event_engine = event_engine
        self.config = config
        self.status = ServiceStatus.STOPPED
        
        # 数据缓存
        self.account_data: Optional[AccountData] = None
        self.positions: Dict[str, PositionData] = {}  # symbol -> position
        self.orders: Dict[str, OrderData] = {}        # order_id -> order
        self.trades: Dict[str, TradeData] = {}        # trade_id -> trade
        
        # 查询控制
        self.query_interval = config.config.get('update_interval', 30)  # 秒
        self.last_account_query = None
        self.last_position_query = None
        self.query_thread: Optional[threading.Thread] = None
        self.query_running = False
        
        # 回调函数
        self.account_callbacks: List[Callable[[AccountData], None]] = []
        self.position_callbacks: List[Callable[[PositionData], None]] = []
        self.order_callbacks: List[Callable[[OrderData], None]] = []
        self.trade_callbacks: List[Callable[[TradeData], None]] = []
        
        logger.info(f"账户服务初始化完成: {self.config.name}")
    
    @abstractmethod
    def start(self) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止服务"""
        pass
    
    @abstractmethod
    def _query_account_impl(self) -> bool:
        """实际的账户查询实现"""
        pass
    
    @abstractmethod
    def _query_positions_impl(self) -> bool:
        """实际的持仓查询实现"""
        pass
    
    def get_account_info(self) -> Optional[AccountData]:
        """获取账户信息（从缓存）"""
        return self.account_data
    
    def get_positions(self, symbol: str = None) -> List[PositionData]:
        """
        获取持仓信息（从缓存）
        
        Args:
            symbol: 合约代码，如果为None则返回所有持仓
            
        Returns:
            List[PositionData]: 持仓信息列表
        """
        if symbol:
            position = self.positions.get(symbol)
            return [position] if position else []
        else:
            return list(self.positions.values())
    
    def get_position_by_symbol(self, symbol: str) -> Optional[PositionData]:
        """
        根据合约代码获取持仓
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[PositionData]: 持仓信息
        """
        return self.positions.get(symbol)
    
    def get_available_funds(self) -> float:
        """获取可用资金"""
        if self.account_data:
            return self.account_data.available
        return 0.0
    
    def get_orders(self, symbol: str = None, active_only: bool = False) -> List[OrderData]:
        """
        获取订单信息
        
        Args:
            symbol: 合约代码过滤
            active_only: 是否只返回活跃订单
            
        Returns:
            List[OrderData]: 订单列表
        """
        orders = list(self.orders.values())
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        if active_only:
            active_statuses = ['SUBMITTING', 'NOTTRADED', 'PARTTRADED']
            orders = [order for order in orders if order.status.value in active_statuses]
        
        return orders
    
    def get_trades(self, symbol: str = None) -> List[TradeData]:
        """
        获取成交记录
        
        Args:
            symbol: 合约代码过滤
            
        Returns:
            List[TradeData]: 成交记录列表
        """
        trades = list(self.trades.values())
        
        if symbol:
            trades = [trade for trade in trades if trade.symbol == symbol]
        
        return trades
    
    def query_account_info(self) -> bool:
        """主动查询账户信息"""
        try:
            success = self._query_account_impl()
            if success:
                self.last_account_query = datetime.now()
            return success
        except Exception as e:
            logger.error(f"查询账户信息失败: {e}")
            return False
    
    def query_positions(self) -> bool:
        """主动查询持仓信息"""
        try:
            success = self._query_positions_impl()
            if success:
                self.last_position_query = datetime.now()
            return success
        except Exception as e:
            logger.error(f"查询持仓信息失败: {e}")
            return False
    
    def _query_loop(self) -> None:
        """定时查询循环"""
        while self.query_running:
            try:
                current_time = datetime.now()
                
                # 检查是否需要查询账户信息
                if (not self.last_account_query or 
                    current_time - self.last_account_query >= timedelta(seconds=self.query_interval)):
                    self.query_account_info()
                
                # 检查是否需要查询持仓信息
                if (not self.last_position_query or 
                    current_time - self.last_position_query >= timedelta(seconds=self.query_interval)):
                    self.query_positions()
                
                # 等待一段时间再检查
                time.sleep(min(5, self.query_interval // 6))  # 最多等待5秒
                
            except Exception as e:
                logger.error(f"定时查询循环出错: {e}")
                time.sleep(5)
    
    def add_account_callback(self, callback: Callable[[AccountData], None]) -> None:
        """添加账户信息回调"""
        if callback not in self.account_callbacks:
            self.account_callbacks.append(callback)
    
    def add_position_callback(self, callback: Callable[[PositionData], None]) -> None:
        """添加持仓信息回调"""
        if callback not in self.position_callbacks:
            self.position_callbacks.append(callback)
    
    def add_order_callback(self, callback: Callable[[OrderData], None]) -> None:
        """添加订单状态回调"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable[[TradeData], None]) -> None:
        """添加成交信息回调"""
        if callback not in self.trade_callbacks:
            self.trade_callbacks.append(callback)
    
    def on_account(self, account: AccountData) -> None:
        """处理账户信息回调（查询响应）"""
        try:
            self.account_data = account
            
            # 调用回调函数
            for callback in self.account_callbacks:
                try:
                    callback(account)
                except Exception as e:
                    logger.error(f"账户信息回调执行失败: {e}")
            
            # 发送事件
            event = Event(ACCOUNT_EVENT, account)
            self.event_engine.put(event)
            
            logger.debug(f"更新账户信息: 可用资金 {account.available}")
            
        except Exception as e:
            logger.error(f"处理账户信息失败: {e}")
    
    def on_position(self, position: PositionData) -> None:
        """处理持仓信息回调（查询响应）"""
        try:
            # 更新持仓缓存
            key = f"{position.symbol}_{position.direction.value}"
            self.positions[key] = position
            
            # 调用回调函数
            for callback in self.position_callbacks:
                try:
                    callback(position)
                except Exception as e:
                    logger.error(f"持仓信息回调执行失败: {e}")
            
            # 发送事件
            event = Event(POSITION_EVENT, position)
            self.event_engine.put(event)
            
            logger.debug(f"更新持仓信息: {position.symbol} {position.direction.value} {position.volume}")
            
        except Exception as e:
            logger.error(f"处理持仓信息失败: {e}")
    
    def on_order(self, order: OrderData) -> None:
        """处理订单状态回调（实时推送）"""
        try:
            # 更新订单缓存
            self.orders[order.orderid] = order
            
            # 调用回调函数
            for callback in self.order_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"订单状态回调执行失败: {e}")
            
            # 发送事件
            event = Event(ORDER_EVENT, order)
            self.event_engine.put(event)
            
            logger.debug(f"订单状态更新: {order.orderid} {order.status.value}")
            
        except Exception as e:
            logger.error(f"处理订单状态失败: {e}")
    
    def on_trade(self, trade: TradeData) -> None:
        """处理成交信息回调（实时推送）"""
        try:
            # 更新成交缓存
            self.trades[trade.tradeid] = trade
            
            # 成交后触发账户和持仓查询
            if self.config.config.get('auto_query_after_trade', True):
                self.query_account_info()
                self.query_positions()
            
            # 调用回调函数
            for callback in self.trade_callbacks:
                try:
                    callback(trade)
                except Exception as e:
                    logger.error(f"成交信息回调执行失败: {e}")
            
            # 发送事件
            event = Event(TRADE_EVENT, trade)
            self.event_engine.put(event)
            
            logger.info(f"成交通知: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")
            
        except Exception as e:
            logger.error(f"处理成交信息失败: {e}")
    
    def get_account_snapshot(self) -> AccountSnapshot:
        """获取账户快照"""
        return AccountSnapshot(
            timestamp=datetime.now(),
            account=self.account_data,
            positions=self.positions.copy(),
            orders=self.orders.copy(),
            trades=self.trades.copy()
        )
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def get_statistics(self) -> Dict[str, any]:
        """获取服务统计信息"""
        return {
            'status': self.status.value,
            'account_available': self.account_data.available if self.account_data else 0,
            'positions_count': len(self.positions),
            'active_orders_count': len(self.get_orders(active_only=True)),
            'total_trades_count': len(self.trades),
            'last_account_query': self.last_account_query.isoformat() if self.last_account_query else None,
            'last_position_query': self.last_position_query.isoformat() if self.last_position_query else None,
            'query_interval': self.query_interval
        }

class AccountService(AccountServiceBase):
    """账户信息服务实现"""

    def __init__(self, event_engine: EventEngine, config: ServiceConfig, gateway=None):
        """
        初始化账户服务

        Args:
            event_engine: 事件引擎
            config: 服务配置
            gateway: CTP网关实例
        """
        super().__init__(event_engine, config)
        self.gateway = gateway

        # 如果有网关，注册回调
        if self.gateway:
            self.gateway.add_account_callback(self.on_account)
            self.gateway.add_position_callback(self.on_position)
            self.gateway.add_order_callback(self.on_order)
            self.gateway.add_trade_callback(self.on_trade)

    def start(self) -> bool:
        """启动服务"""
        try:
            if self.status == ServiceStatus.RUNNING:
                logger.warning("账户服务已在运行")
                return True

            self.status = ServiceStatus.STARTING

            # 检查网关连接
            if not self.gateway:
                logger.error("CTP网关未设置")
                self.status = ServiceStatus.ERROR
                return False

            if not self.gateway.is_td_connected():
                logger.error("CTP交易服务器未连接")
                self.status = ServiceStatus.ERROR
                return False

            # 启动定时查询线程
            self.query_running = True
            self.query_thread = threading.Thread(target=self._query_loop, daemon=True)
            self.query_thread.start()

            # 立即查询一次账户和持仓信息
            self.query_account_info()
            self.query_positions()

            self.status = ServiceStatus.RUNNING
            logger.info("账户服务启动成功")
            return True

        except Exception as e:
            logger.error(f"账户服务启动失败: {e}")
            self.status = ServiceStatus.ERROR
            return False

    def stop(self) -> None:
        """停止服务"""
        try:
            if self.status == ServiceStatus.STOPPED:
                return

            self.status = ServiceStatus.STOPPING

            # 停止查询线程
            self.query_running = False
            if self.query_thread and self.query_thread.is_alive():
                self.query_thread.join(timeout=5)

            # 清理数据
            self.account_data = None
            self.positions.clear()
            self.orders.clear()
            self.trades.clear()

            # 清理回调
            self.account_callbacks.clear()
            self.position_callbacks.clear()
            self.order_callbacks.clear()
            self.trade_callbacks.clear()

            self.status = ServiceStatus.STOPPED
            logger.info("账户服务已停止")

        except Exception as e:
            logger.error(f"停止账户服务失败: {e}")
            self.status = ServiceStatus.ERROR

    def _query_account_impl(self) -> bool:
        """实际的账户查询实现"""
        try:
            if self.gateway and self.gateway.is_td_connected():
                # 调用CTP网关的账户查询方法
                success = self.gateway.query_account()
                if success:
                    logger.debug("账户查询请求发送成功")
                else:
                    logger.error("账户查询请求发送失败")
                return success
            else:
                logger.error("CTP交易服务器未连接，无法查询账户")
                return False
        except Exception as e:
            logger.error(f"查询账户信息失败: {e}")
            return False

    def _query_positions_impl(self) -> bool:
        """实际的持仓查询实现"""
        try:
            if self.gateway and self.gateway.is_td_connected():
                # 调用CTP网关的持仓查询方法
                success = self.gateway.query_position()
                if success:
                    logger.debug("持仓查询请求发送成功")
                else:
                    logger.error("持仓查询请求发送失败")
                return success
            else:
                logger.error("CTP交易服务器未连接，无法查询持仓")
                return False
        except Exception as e:
            logger.error(f"查询持仓信息失败: {e}")
            return False
