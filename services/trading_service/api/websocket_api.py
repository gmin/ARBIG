"""
交易服务 WebSocket API
提供实时数据推送：tick、order、trade
"""

import asyncio
import json
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TradingWebSocketManager:
    """交易服务 WebSocket 管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> client_ids
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """接受连接"""
        try:
            await websocket.accept()
            async with self._lock:
                self.active_connections[client_id] = websocket
            logger.info(f"🔌 WebSocket 客户端连接: {client_id}")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket 连接失败: {e}")
            return False
    
    async def disconnect(self, client_id: str):
        """断开连接"""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                # 清理订阅
                for topic in list(self.subscriptions.keys()):
                    self.subscriptions[topic].discard(client_id)
                    if not self.subscriptions[topic]:
                        del self.subscriptions[topic]
        logger.info(f"🔌 WebSocket 客户端断开: {client_id}")
    
    def subscribe(self, client_id: str, topic: str):
        """订阅主题"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)
        logger.debug(f"📡 {client_id} 订阅 {topic}")
    
    async def broadcast(self, message: Dict[str, Any], topic: str = None):
        """广播消息"""
        if topic:
            client_ids = list(self.subscriptions.get(topic, set()))
        else:
            client_ids = list(self.active_connections.keys())
        
        if not client_ids:
            return
        
        message_text = json.dumps(message, default=str, ensure_ascii=False)
        disconnected = []
        
        for client_id in client_ids:
            try:
                ws = self.active_connections.get(client_id)
                if ws:
                    await ws.send_text(message_text)
            except Exception as e:
                logger.warning(f"⚠️ 发送消息失败 {client_id}: {e}")
                disconnected.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected:
            await self.disconnect(client_id)
    
    async def push_tick(self, tick_data: Dict[str, Any]):
        """推送 Tick 数据"""
        message = {
            "type": "tick",
            "data": tick_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message, "tick")
    
    async def push_order(self, order_data: Dict[str, Any]):
        """推送订单数据"""
        message = {
            "type": "order",
            "data": order_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message, "order")
    
    async def push_trade(self, trade_data: Dict[str, Any]):
        """推送成交数据"""
        message = {
            "type": "trade",
            "data": trade_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message, "trade")
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "connections": len(self.active_connections),
            "clients": list(self.active_connections.keys()),
            "subscriptions": {k: len(v) for k, v in self.subscriptions.items()}
        }


# 全局实例
_ws_manager: TradingWebSocketManager = None


def get_trading_ws_manager() -> TradingWebSocketManager:
    """获取 WebSocket 管理器实例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = TradingWebSocketManager()
    return _ws_manager


@router.websocket("/ws/trading")
async def trading_websocket(websocket: WebSocket):
    """交易数据 WebSocket 端点"""
    ws_manager = get_trading_ws_manager()
    client_id = f"strategy_{datetime.now().strftime('%H%M%S%f')}"
    
    if not await ws_manager.connect(websocket, client_id):
        return
    
    try:
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "message": "交易 WebSocket 连接成功"
        }))
        
        # 自动订阅所有数据
        ws_manager.subscribe(client_id, "tick")
        ws_manager.subscribe(client_id, "order")
        ws_manager.subscribe(client_id, "trade")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理心跳
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 客户端主动断开: {client_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket 异常: {e}")
    finally:
        await ws_manager.disconnect(client_id)


@router.get("/ws/trading/status")
async def get_ws_status():
    """获取 WebSocket 状态"""
    ws_manager = get_trading_ws_manager()
    return ws_manager.get_status()

