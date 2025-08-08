"""
WebSocket连接管理器
处理实时数据推送和连接管理
"""

import asyncio
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from shared.models.trading import WebSocketMessage, TickData
from utils.logger import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> connection_ids
        
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """接受WebSocket连接"""
        await websocket.accept()
        
        if not client_id:
            client_id = str(uuid.uuid4())
        
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            'connect_time': datetime.now(),
            'last_ping': datetime.now(),
            'subscriptions': set()
        }
        
        logger.info(f"WebSocket客户端连接: {client_id}")
        return client_id
    
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            # 清理订阅
            if client_id in self.connection_info:
                for topic in self.connection_info[client_id]['subscriptions']:
                    if topic in self.subscriptions:
                        self.subscriptions[topic].discard(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]
            
            # 清理连接
            del self.active_connections[client_id]
            del self.connection_info[client_id]
            
            logger.info(f"WebSocket客户端断开: {client_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message, default=str, ensure_ascii=False))
            except Exception as e:
                logger.error(f"发送个人消息失败 {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: Dict[str, Any], topic: str = None):
        """广播消息"""
        if topic and topic in self.subscriptions:
            # 向订阅特定主题的客户端发送
            client_ids = list(self.subscriptions[topic])
        else:
            # 向所有客户端发送
            client_ids = list(self.active_connections.keys())
        
        if not client_ids:
            return
        
        message_text = json.dumps(message, default=str, ensure_ascii=False)
        disconnected_clients = []
        
        for client_id in client_ids:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"广播消息失败 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe(self, client_id: str, topic: str):
        """订阅主题"""
        if client_id not in self.active_connections:
            return False
        
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        
        self.subscriptions[topic].add(client_id)
        self.connection_info[client_id]['subscriptions'].add(topic)
        
        logger.debug(f"客户端 {client_id} 订阅主题: {topic}")
        return True
    
    def unsubscribe(self, client_id: str, topic: str):
        """取消订阅主题"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        if client_id in self.connection_info:
            self.connection_info[client_id]['subscriptions'].discard(topic)
        
        logger.debug(f"客户端 {client_id} 取消订阅主题: {topic}")
    
    def get_connection_count(self) -> int:
        """获取连接数量"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'total_connections': len(self.active_connections),
            'connections': {
                client_id: {
                    'connect_time': info['connect_time'].isoformat(),
                    'last_ping': info['last_ping'].isoformat(),
                    'subscriptions': list(info['subscriptions'])
                }
                for client_id, info in self.connection_info.items()
            },
            'subscriptions': {
                topic: len(clients)
                for topic, clients in self.subscriptions.items()
            }
        }

class MarketDataBroadcaster:
    """行情数据广播器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        """初始化广播器"""
        self.connection_manager = connection_manager
        self.last_prices: Dict[str, float] = {}
        self.broadcast_count = 0
        
    async def broadcast_tick_data(self, symbol: str, tick_data: TickData):
        """广播Tick数据"""
        try:
            # 检查价格是否有变化
            last_price = self.last_prices.get(symbol)
            if last_price == tick_data.last_price:
                return  # 价格没有变化，不广播
            
            self.last_prices[symbol] = tick_data.last_price
            
            # 构建WebSocket消息
            message = {
                'type': 'market_data',
                'symbol': symbol,
                'data': tick_data.dict(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 广播到订阅行情的客户端
            await self.connection_manager.broadcast(message, f"market_data:{symbol}")
            
            self.broadcast_count += 1
            
            if self.broadcast_count % 100 == 0:
                logger.debug(f"已广播 {self.broadcast_count} 条行情数据")
                
        except Exception as e:
            logger.error(f"广播Tick数据失败: {e}")
    
    async def broadcast_position_update(self, position_data: Dict[str, Any]):
        """广播持仓更新"""
        try:
            message = {
                'type': 'position_update',
                'data': position_data,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.connection_manager.broadcast(message, "position_update")
            
        except Exception as e:
            logger.error(f"广播持仓更新失败: {e}")
    
    async def broadcast_account_update(self, account_data: Dict[str, Any]):
        """广播账户更新"""
        try:
            message = {
                'type': 'account_update',
                'data': account_data,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.connection_manager.broadcast(message, "account_update")
            
        except Exception as e:
            logger.error(f"广播账户更新失败: {e}")
    
    async def broadcast_strategy_trigger(self, trigger_data: Dict[str, Any]):
        """广播策略触发"""
        try:
            message = {
                'type': 'strategy_trigger',
                'data': trigger_data,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.connection_manager.broadcast(message, "strategy_trigger")
            
        except Exception as e:
            logger.error(f"广播策略触发失败: {e}")

class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        """初始化处理器"""
        self.connection_manager = connection_manager
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """处理客户端消息"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'ping':
                # 处理心跳
                await self._handle_ping(client_id)
            elif msg_type == 'subscribe':
                # 处理订阅
                await self._handle_subscribe(client_id, message)
            elif msg_type == 'unsubscribe':
                # 处理取消订阅
                await self._handle_unsubscribe(client_id, message)
            else:
                logger.warning(f"未知消息类型: {msg_type}")
                
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")
    
    async def _handle_ping(self, client_id: str):
        """处理心跳消息"""
        if client_id in self.connection_manager.connection_info:
            self.connection_manager.connection_info[client_id]['last_ping'] = datetime.now()
        
        # 发送pong响应
        await self.connection_manager.send_personal_message({
            'type': 'pong',
            'timestamp': datetime.now().isoformat()
        }, client_id)
    
    async def _handle_subscribe(self, client_id: str, message: Dict[str, Any]):
        """处理订阅消息"""
        topic = message.get('topic')
        if topic:
            success = self.connection_manager.subscribe(client_id, topic)
            await self.connection_manager.send_personal_message({
                'type': 'subscribe_response',
                'topic': topic,
                'success': success,
                'timestamp': datetime.now().isoformat()
            }, client_id)
    
    async def _handle_unsubscribe(self, client_id: str, message: Dict[str, Any]):
        """处理取消订阅消息"""
        topic = message.get('topic')
        if topic:
            self.connection_manager.unsubscribe(client_id, topic)
            await self.connection_manager.send_personal_message({
                'type': 'unsubscribe_response',
                'topic': topic,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }, client_id)

# 全局实例
connection_manager = ConnectionManager()
market_data_broadcaster = MarketDataBroadcaster(connection_manager)
websocket_handler = WebSocketHandler(connection_manager)

def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    return connection_manager

def get_market_data_broadcaster() -> MarketDataBroadcaster:
    """获取行情广播器实例"""
    return market_data_broadcaster

def get_websocket_handler() -> WebSocketHandler:
    """获取WebSocket处理器实例"""
    return websocket_handler
