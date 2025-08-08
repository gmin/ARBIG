"""
ARBIG事件总线
提供标准化的事件发布和订阅机制
"""

import json
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .event_engine import EventEngine, Event
from utils.logger import get_logger

logger = get_logger(__name__)

class EventType(str, Enum):
    """事件类型枚举"""
    # 系统事件
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"
    
    # 服务事件
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_ERROR = "service.error"
    
    # 市场数据事件
    MARKET_DATA_TICK = "market_data.tick"
    MARKET_DATA_BAR = "market_data.bar"
    MARKET_DATA_CONNECTED = "market_data.connected"
    MARKET_DATA_DISCONNECTED = "market_data.disconnected"
    
    # 账户事件
    ACCOUNT_UPDATED = "account.updated"
    POSITION_UPDATED = "position.updated"
    
    # 交易事件
    ORDER_SUBMITTED = "order.submitted"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"
    TRADE_EXECUTED = "trade.executed"
    
    # 策略事件
    STRATEGY_STARTED = "strategy.started"
    STRATEGY_STOPPED = "strategy.stopped"
    STRATEGY_SIGNAL = "strategy.signal"
    
    # 风控事件
    RISK_WARNING = "risk.warning"
    RISK_LIMIT_EXCEEDED = "risk.limit_exceeded"
    
    # Web事件
    WEB_CLIENT_CONNECTED = "web.client_connected"
    WEB_CLIENT_DISCONNECTED = "web.client_disconnected"

@dataclass
class EventData:
    """标准事件数据结构"""
    event_type: str
    timestamp: str
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

class EventBus:
    """
    事件总线
    提供标准化的事件发布和订阅机制
    """

    def __init__(self, event_engine: EventEngine):
        """初始化事件总线"""
        self.event_engine = event_engine
        self.subscribers = {}  # 事件订阅者
        self.event_history = []  # 事件历史记录
        self.max_history_size = 1000  # 最大历史记录数量
        
        logger.info("事件总线初始化完成")

    def publish(self, event_type: str, data: Dict[str, Any], 
                source: str = "system", correlation_id: str = None):
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件源
            correlation_id: 关联ID
        """
        try:
            # 创建事件数据
            event_data = EventData(
                event_type=event_type,
                timestamp=datetime.now().isoformat(),
                source=source,
                data=data,
                correlation_id=correlation_id
            )

            # 记录事件历史
            self._add_to_history(event_data)

            # 创建VeighNa事件
            event = Event(event_type, event_data.to_dict())

            # 发布事件
            self.event_engine.put(event)

            logger.debug(f"事件已发布: {event_type} from {source}")

        except Exception as e:
            logger.error(f"发布事件失败: {e}")

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None], 
                  subscriber_name: str = "unknown"):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
            subscriber_name: 订阅者名称
        """
        try:
            # 包装处理函数
            def wrapped_handler(event: Event):
                try:
                    handler(event.data)
                except Exception as e:
                    logger.error(f"事件处理失败 [{subscriber_name}]: {e}")

            # 注册事件处理器
            self.event_engine.register(event_type, wrapped_handler)

            # 记录订阅者
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            
            self.subscribers[event_type].append({
                'name': subscriber_name,
                'handler': handler,
                'subscribed_at': datetime.now().isoformat()
            })

            logger.debug(f"事件订阅成功: {event_type} by {subscriber_name}")

        except Exception as e:
            logger.error(f"订阅事件失败: {e}")

    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        try:
            # 从VeighNa事件引擎取消注册
            self.event_engine.unregister(event_type, handler)

            # 从订阅者列表中移除
            if event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub for sub in self.subscribers[event_type] 
                    if sub['handler'] != handler
                ]

            logger.debug(f"取消事件订阅: {event_type}")

        except Exception as e:
            logger.error(f"取消订阅事件失败: {e}")

    def get_event_history(self, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取事件历史记录
        
        Args:
            event_type: 事件类型过滤器
            limit: 返回记录数量限制
            
        Returns:
            事件历史记录列表
        """
        try:
            history = self.event_history

            # 按事件类型过滤
            if event_type:
                history = [event for event in history if event.event_type == event_type]

            # 限制返回数量
            history = history[-limit:] if limit > 0 else history

            return [event.to_dict() for event in history]

        except Exception as e:
            logger.error(f"获取事件历史失败: {e}")
            return []

    def get_subscribers_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取订阅者信息"""
        try:
            return dict(self.subscribers)
        except Exception as e:
            logger.error(f"获取订阅者信息失败: {e}")
            return {}

    def get_event_statistics(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        try:
            # 统计各类型事件数量
            event_counts = {}
            for event in self.event_history:
                event_type = event.event_type
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # 统计订阅者数量
            subscriber_counts = {}
            for event_type, subscribers in self.subscribers.items():
                subscriber_counts[event_type] = len(subscribers)

            return {
                'total_events': len(self.event_history),
                'event_counts': event_counts,
                'total_subscribers': sum(subscriber_counts.values()),
                'subscriber_counts': subscriber_counts,
                'history_size': len(self.event_history),
                'max_history_size': self.max_history_size
            }

        except Exception as e:
            logger.error(f"获取事件统计失败: {e}")
            return {}

    def clear_history(self):
        """清空事件历史记录"""
        try:
            self.event_history.clear()
            logger.info("事件历史记录已清空")
        except Exception as e:
            logger.error(f"清空事件历史失败: {e}")

    def _add_to_history(self, event_data: EventData):
        """添加事件到历史记录"""
        try:
            self.event_history.append(event_data)

            # 限制历史记录大小
            if len(self.event_history) > self.max_history_size:
                # 删除最旧的记录
                self.event_history = self.event_history[-self.max_history_size:]

        except Exception as e:
            logger.error(f"添加事件历史失败: {e}")

    # 便捷方法：系统事件
    def publish_system_started(self, data: Dict[str, Any] = None):
        """发布系统启动事件"""
        self.publish(EventType.SYSTEM_STARTED, data or {}, "system")

    def publish_system_stopped(self, data: Dict[str, Any] = None):
        """发布系统停止事件"""
        self.publish(EventType.SYSTEM_STOPPED, data or {}, "system")

    def publish_system_error(self, error_message: str, error_details: Dict[str, Any] = None):
        """发布系统错误事件"""
        data = {
            'error_message': error_message,
            'error_details': error_details or {}
        }
        self.publish(EventType.SYSTEM_ERROR, data, "system")

    # 便捷方法：服务事件
    def publish_service_started(self, service_name: str, data: Dict[str, Any] = None):
        """发布服务启动事件"""
        event_data = {'service_name': service_name}
        if data:
            event_data.update(data)
        self.publish(EventType.SERVICE_STARTED, event_data, f"service.{service_name}")

    def publish_service_stopped(self, service_name: str, data: Dict[str, Any] = None):
        """发布服务停止事件"""
        event_data = {'service_name': service_name}
        if data:
            event_data.update(data)
        self.publish(EventType.SERVICE_STOPPED, event_data, f"service.{service_name}")

    # 便捷方法：市场数据事件
    def publish_market_data_tick(self, tick_data: Dict[str, Any]):
        """发布Tick数据事件"""
        self.publish(EventType.MARKET_DATA_TICK, tick_data, "market_data")

    def publish_market_data_bar(self, bar_data: Dict[str, Any]):
        """发布K线数据事件"""
        self.publish(EventType.MARKET_DATA_BAR, bar_data, "market_data")

    # 便捷方法：交易事件
    def publish_order_submitted(self, order_data: Dict[str, Any]):
        """发布订单提交事件"""
        self.publish(EventType.ORDER_SUBMITTED, order_data, "trading")

    def publish_order_filled(self, order_data: Dict[str, Any]):
        """发布订单成交事件"""
        self.publish(EventType.ORDER_FILLED, order_data, "trading")

    def publish_trade_executed(self, trade_data: Dict[str, Any]):
        """发布交易执行事件"""
        self.publish(EventType.TRADE_EXECUTED, trade_data, "trading")

    # 便捷方法：风控事件
    def publish_risk_warning(self, warning_message: str, risk_data: Dict[str, Any] = None):
        """发布风控警告事件"""
        data = {
            'warning_message': warning_message,
            'risk_data': risk_data or {}
        }
        self.publish(EventType.RISK_WARNING, data, "risk")

    def publish_risk_limit_exceeded(self, limit_type: str, current_value: float, 
                                   limit_value: float, risk_data: Dict[str, Any] = None):
        """发布风控限制超出事件"""
        data = {
            'limit_type': limit_type,
            'current_value': current_value,
            'limit_value': limit_value,
            'risk_data': risk_data or {}
        }
        self.publish(EventType.RISK_LIMIT_EXCEEDED, data, "risk")

    # 便捷方法：Web事件
    def publish_web_client_connected(self, client_info: Dict[str, Any]):
        """发布Web客户端连接事件"""
        self.publish(EventType.WEB_CLIENT_CONNECTED, client_info, "web")

    def publish_web_client_disconnected(self, client_info: Dict[str, Any]):
        """发布Web客户端断开事件"""
        self.publish(EventType.WEB_CLIENT_DISCONNECTED, client_info, "web")
