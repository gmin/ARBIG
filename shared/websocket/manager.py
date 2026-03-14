"""
WebSocket连接管理器
处理实时数据推送和连接管理
"""

import json
from typing import Dict, Set, Any
from datetime import datetime
import uuid
from fastapi import WebSocket

from utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
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
            if client_id in self.connection_info:
                for topic in self.connection_info[client_id]['subscriptions']:
                    if topic in self.subscriptions:
                        self.subscriptions[topic].discard(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]

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
            client_ids = list(self.subscriptions[topic])
        else:
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


class WebSocketHandler:
    """WebSocket处理器"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def handle_message(self, client_id: str, message: Dict[str, Any]):
        """处理客户端消息"""
        try:
            msg_type = message.get('type')

            if msg_type == 'ping':
                await self._handle_ping(client_id)
            elif msg_type == 'subscribe':
                await self._handle_subscribe(client_id, message)
            elif msg_type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, message)
            else:
                logger.warning(f"未知消息类型: {msg_type}")

        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")

    async def _handle_ping(self, client_id: str):
        """处理心跳消息"""
        if client_id in self.connection_manager.connection_info:
            self.connection_manager.connection_info[client_id]['last_ping'] = datetime.now()

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
websocket_handler = WebSocketHandler(connection_manager)


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例"""
    return connection_manager


def get_websocket_handler() -> WebSocketHandler:
    """获取WebSocket处理器实例"""
    return websocket_handler
