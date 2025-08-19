"""
交易执行服务
负责处理策略信号、订单管理和交易执行
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime

from ..event_engine import EventEngine, Event
from ..types import (
    OrderRequest, OrderData, TradeData, SignalData,
    ServiceStatus, ServiceConfig, Direction, OrderType, Status
)
from ..constants import SIGNAL_EVENT, ORDER_EVENT, TRADE_EVENT
from utils.logger import get_logger

logger = get_logger(__name__)

class TradingServiceBase(ABC):
    """交易服务基类"""
    
    def __init__(self, event_engine: EventEngine, config: ServiceConfig):
        """
        初始化交易服务
        
        Args:
            event_engine: 事件引擎
            config: 服务配置
        """
        self.event_engine = event_engine
        self.config = config
        self.status = ServiceStatus.STOPPED
        
        # 订单管理
        self.orders: Dict[str, OrderData] = {}  # order_id -> order
        self.trades: Dict[str, TradeData] = {}  # trade_id -> trade
        self.order_ref_map: Dict[str, str] = {}  # order_ref -> order_id
        self.strategy_orders: Dict[str, List[str]] = {}  # strategy_name -> order_ids

        # 订单统计
        self.order_count = 0
        self.trade_count = 0
        self.total_volume = 0.0
        self.total_turnover = 0.0
        
        # 配置参数
        self.order_timeout = config.config.get('order_timeout', 30)
        self.max_orders_per_second = config.config.get('max_orders_per_second', 10)
        
        # 回调函数
        self.order_callbacks: List[Callable[[OrderData], None]] = []
        self.trade_callbacks: List[Callable[[TradeData], None]] = []
        
        # 注册事件处理
        self.event_engine.register(SIGNAL_EVENT, self.process_signal)
        
        logger.info(f"交易服务初始化完成: {self.config.name}")
    
    @abstractmethod
    def start(self) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止服务"""
        pass
    
    @abstractmethod
    def _send_order_impl(self, order_req: OrderRequest) -> Optional[str]:
        """实际的发送订单实现"""
        pass
    
    @abstractmethod
    def _cancel_order_impl(self, order_id: str) -> bool:
        """实际的撤销订单实现"""
        pass
    
    def send_order(self, order_req: OrderRequest) -> Optional[str]:
        """
        发送订单
        
        Args:
            order_req: 订单请求
            
        Returns:
            Optional[str]: 订单ID，失败返回None
        """
        try:
            # 检查服务状态
            if self.status != ServiceStatus.RUNNING:
                logger.error("交易服务未运行，无法发送订单")
                return None
            
            # 生成订单ID
            order_id = str(uuid.uuid4())
            
            # 调用实际发送实现
            order_ref = self._send_order_impl(order_req)
            if not order_ref:
                logger.error(f"发送订单失败: {order_req.symbol}")
                return None
            
            # 建立映射关系
            self.order_ref_map[order_ref] = order_id
            
            # 创建订单对象
            order = OrderData(
                orderid=order_id,
                symbol=order_req.symbol,
                exchange=order_req.exchange,
                direction=order_req.direction,
                type=order_req.type,
                volume=order_req.volume,
                traded=0.0,
                price=order_req.price,
                status=Status.SUBMITTING,
                datetime=datetime.now(),
                reference=order_req.reference,
                gateway_name="CTP"
            )
            
            # 缓存订单
            self.orders[order_id] = order

            # 跟踪策略订单
            strategy_name = order_req.reference.split('_')[0] if order_req.reference else 'unknown'
            if strategy_name not in self.strategy_orders:
                self.strategy_orders[strategy_name] = []
            self.strategy_orders[strategy_name].append(order_id)

            # 更新统计
            self.order_count += 1

            logger.info(f"订单发送成功: {order_req.symbol} {order_req.direction.value} {order_req.volume}@{order_req.price} (策略: {strategy_name})")
            return order_id
            
        except Exception as e:
            logger.error(f"发送订单异常: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 撤销是否成功
        """
        try:
            # 检查订单是否存在
            if order_id not in self.orders:
                logger.error(f"订单不存在: {order_id}")
                return False
            
            order = self.orders[order_id]
            
            # 检查订单状态
            if order.status.value in ['ALLTRADED', 'CANCELLED', 'REJECTED']:
                logger.warning(f"订单已完成，无法撤销: {order_id} {order.status.value}")
                return False
            
            # 调用实际撤销实现
            success = self._cancel_order_impl(order_id)
            if success:
                logger.info(f"订单撤销请求发送成功: {order_id}")
            else:
                logger.error(f"订单撤销请求发送失败: {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"撤销订单异常: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[OrderData]:
        """
        获取订单信息
        
        Args:
            order_id: 订单ID
            
        Returns:
            Optional[OrderData]: 订单信息
        """
        return self.orders.get(order_id)
    
    def get_active_orders(self, symbol: str = None) -> List[OrderData]:
        """
        获取活跃订单
        
        Args:
            symbol: 合约代码过滤
            
        Returns:
            List[OrderData]: 活跃订单列表
        """
        active_statuses = ['SUBMITTING', 'NOTTRADED', 'PARTTRADED']
        orders = [order for order in self.orders.values() 
                 if order.status.value in active_statuses]
        
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
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

    def get_orders_by_strategy(self, strategy_name: str) -> List[OrderData]:
        """
        获取策略的所有订单

        Args:
            strategy_name: 策略名称

        Returns:
            List[OrderData]: 订单列表
        """
        order_ids = self.strategy_orders.get(strategy_name, [])
        return [self.orders[order_id] for order_id in order_ids if order_id in self.orders]

    def cancel_strategy_orders(self, strategy_name: str, symbol: str = None) -> int:
        """
        撤销策略的所有活跃订单

        Args:
            strategy_name: 策略名称
            symbol: 合约代码过滤（可选）

        Returns:
            int: 撤销的订单数量
        """
        try:
            strategy_orders = self.get_orders_by_strategy(strategy_name)
            active_orders = [order for order in strategy_orders
                           if order.status.value in ['SUBMITTING', 'NOTTRADED', 'PARTTRADED']]

            if symbol:
                active_orders = [order for order in active_orders if order.symbol == symbol]

            cancelled_count = 0
            for order in active_orders:
                if self.cancel_order(order.orderid):
                    cancelled_count += 1

            logger.info(f"策略 {strategy_name} 撤销了 {cancelled_count} 个订单")
            return cancelled_count

        except Exception as e:
            logger.error(f"撤销策略订单失败: {e}")
            return 0

    def get_strategy_statistics(self, strategy_name: str) -> Dict[str, any]:
        """
        获取策略交易统计

        Args:
            strategy_name: 策略名称

        Returns:
            Dict[str, any]: 统计信息
        """
        try:
            strategy_orders = self.get_orders_by_strategy(strategy_name)
            strategy_trades = [trade for trade in self.trades.values()
                             if any(trade.orderid == order.orderid for order in strategy_orders)]

            total_volume = sum(trade.volume for trade in strategy_trades)
            total_turnover = sum(trade.volume * trade.price for trade in strategy_trades)

            active_orders = [order for order in strategy_orders
                           if order.status.value in ['SUBMITTING', 'NOTTRADED', 'PARTTRADED']]

            return {
                'strategy_name': strategy_name,
                'total_orders': len(strategy_orders),
                'active_orders': len(active_orders),
                'total_trades': len(strategy_trades),
                'total_volume': total_volume,
                'total_turnover': total_turnover,
                'avg_price': total_turnover / total_volume if total_volume > 0 else 0
            }

        except Exception as e:
            logger.error(f"获取策略统计失败: {e}")
            return {}
    
    def process_signal(self, event: Event) -> None:
        """
        处理策略信号
        
        Args:
            event: 信号事件
        """
        try:
            signal_data = event.data
            if not isinstance(signal_data, SignalData):
                logger.error(f"无效的信号数据类型: {type(signal_data)}")
                return
            
            logger.info(f"收到策略信号: {signal_data.strategy_name} {signal_data.symbol} "
                       f"{signal_data.direction.value} {signal_data.action} {signal_data.volume}")
            
            # 根据信号类型处理
            if signal_data.signal_type == "TRADE":
                self._process_trade_signal(signal_data)
            elif signal_data.signal_type == "RISK":
                self._process_risk_signal(signal_data)
            else:
                logger.warning(f"未知信号类型: {signal_data.signal_type}")
                
        except Exception as e:
            logger.error(f"处理策略信号异常: {e}")
    
    def _process_trade_signal(self, signal: SignalData) -> None:
        """处理交易信号"""
        try:
            # 创建订单请求
            order_req = OrderRequest(
                symbol=signal.symbol,
                exchange="SHFE",  # 默认上期所
                direction=signal.direction,
                type=OrderType.LIMIT if signal.price else OrderType.MARKET,
                volume=signal.volume,
                price=signal.price or 0.0,
                reference=f"{signal.strategy_name}_{signal.action}"
            )
            
            # 发送订单
            order_id = self.send_order(order_req)
            if order_id:
                logger.info(f"策略信号转换为订单成功: {order_id}")
            else:
                logger.error(f"策略信号转换为订单失败")
                
        except Exception as e:
            logger.error(f"处理交易信号异常: {e}")
    
    def _process_risk_signal(self, signal: SignalData) -> None:
        """处理风险信号"""
        try:
            if signal.action == "CANCEL_ALL":
                # 撤销所有活跃订单
                active_orders = self.get_active_orders(signal.symbol)
                for order in active_orders:
                    self.cancel_order(order.orderid)
                logger.info(f"风险信号：撤销所有订单 {signal.symbol}")
            
        except Exception as e:
            logger.error(f"处理风险信号异常: {e}")
    
    def add_order_callback(self, callback: Callable[[OrderData], None]) -> None:
        """添加订单状态回调"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable[[TradeData], None]) -> None:
        """添加成交信息回调"""
        if callback not in self.trade_callbacks:
            self.trade_callbacks.append(callback)
    
    def on_order(self, order: OrderData) -> None:
        """处理订单状态回调"""
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
        """处理成交信息回调"""
        try:
            # 更新成交缓存
            self.trades[trade.tradeid] = trade
            
            # 更新对应订单的成交数量
            if trade.orderid in self.orders:
                order = self.orders[trade.orderid]
                order.traded += trade.volume

            # 更新统计
            self.trade_count += 1
            self.total_volume += trade.volume
            self.total_turnover += trade.volume * trade.price
            
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
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def get_statistics(self) -> Dict[str, any]:
        """获取服务统计信息"""
        active_orders = self.get_active_orders()

        return {
            'status': self.status.value,
            'total_orders': self.order_count,
            'active_orders': len(active_orders),
            'total_trades': self.trade_count,
            'total_volume': self.total_volume,
            'total_turnover': self.total_turnover,
            'avg_price': self.total_turnover / self.total_volume if self.total_volume > 0 else 0,
            'order_timeout': self.order_timeout,
            'max_orders_per_second': self.max_orders_per_second,
            'strategies_count': len(self.strategy_orders),
            'strategy_names': list(self.strategy_orders.keys())
        }

class TradingService(TradingServiceBase):
    """交易执行服务实现"""

    def __init__(self, event_engine: EventEngine, config: ServiceConfig,
                 gateway=None, account_service=None, risk_service=None):
        """
        初始化交易服务

        Args:
            event_engine: 事件引擎
            config: 服务配置
            gateway: CTP网关实例
            account_service: 账户服务实例
            risk_service: 风控服务实例
        """
        super().__init__(event_engine, config)
        self.gateway = gateway
        self.account_service = account_service
        self.risk_service = risk_service

    def start(self) -> bool:
        """启动服务"""
        try:
            if self.status == ServiceStatus.RUNNING:
                logger.warning("交易服务已在运行")
                return True

            self.status = ServiceStatus.STARTING

            # 检查网关连接
            if not self.gateway:
                logger.error("CTP网关未设置")
                self.status = ServiceStatus.ERROR
                return False

            self.status = ServiceStatus.RUNNING
            logger.info("交易服务启动成功")
            return True

        except Exception as e:
            logger.error(f"交易服务启动失败: {e}")
            self.status = ServiceStatus.ERROR
            return False

    def stop(self) -> None:
        """停止服务"""
        try:
            if self.status == ServiceStatus.STOPPED:
                return

            self.status = ServiceStatus.STOPPING

            # 撤销所有活跃订单
            active_orders = self.get_active_orders()
            for order in active_orders:
                self.cancel_order(order.orderid)

            # 清理数据
            self.orders.clear()
            self.trades.clear()
            self.order_ref_map.clear()
            self.strategy_orders.clear()

            # 重置统计
            self.order_count = 0
            self.trade_count = 0
            self.total_volume = 0.0
            self.total_turnover = 0.0

            # 清理回调
            self.order_callbacks.clear()
            self.trade_callbacks.clear()

            self.status = ServiceStatus.STOPPED
            logger.info("交易服务已停止")

        except Exception as e:
            logger.error(f"停止交易服务失败: {e}")
            self.status = ServiceStatus.ERROR

    def send_order(self, order_req: OrderRequest) -> Optional[str]:
        """发送订单（重写以添加风控检查）"""
        try:
            # 风控检查
            if self.risk_service:
                risk_result = self.risk_service.check_pre_trade_risk(order_req)
                if not risk_result.passed:
                    logger.warning(f"风控检查未通过: {risk_result.reason}")
                    return None

                # 如果建议调整数量
                if risk_result.suggested_volume > 0 and risk_result.suggested_volume != order_req.volume:
                    logger.info(f"风控建议调整数量: {order_req.volume} -> {risk_result.suggested_volume}")
                    order_req.volume = risk_result.suggested_volume

            # 调用父类方法
            return super().send_order(order_req)

        except Exception as e:
            logger.error(f"发送订单异常: {e}")
            return None

    def _send_order_impl(self, order_req: OrderRequest) -> Optional[str]:
        """实际的发送订单实现"""
        try:
            if self.gateway:
                # 调用CTP网关的发送订单方法
                return self.gateway.send_order(order_req)
            return None
        except Exception as e:
            logger.error(f"发送订单到CTP失败: {e}")
            return None

    def _cancel_order_impl(self, order_id: str) -> bool:
        """实际的撤销订单实现"""
        try:
            if self.gateway:
                # 调用CTP网关的撤销订单方法
                return self.gateway.cancel_order(order_id)
            return False
        except Exception as e:
            logger.error(f"撤销订单失败: {e}")
            return False
