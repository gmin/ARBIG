"""
WebSocket API接口
提供实时数据推送服务
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Dict, Any

from shared.websocket.manager import get_connection_manager, get_websocket_handler
# Redis已完全移除，不再需要get_market_data_redis
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    connection_manager = get_connection_manager()
    websocket_handler = get_websocket_handler()
    client_id = None
    
    try:
        # 接受连接
        client_id = await connection_manager.connect(websocket)
        logger.info(f"WebSocket客户端连接成功: {client_id}")
        
        # 发送连接成功消息
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "message": "WebSocket连接建立成功",
            "timestamp": asyncio.get_event_loop().time()
        }, client_id)
        
        # 启动行情推送任务
        market_task = asyncio.create_task(
            market_data_pusher(client_id, connection_manager)
        )
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                await websocket_handler.handle_message(client_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket客户端主动断开: {client_id}")
        finally:
            # 取消行情推送任务
            market_task.cancel()
            try:
                await market_task
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
    finally:
        # 清理连接
        if client_id:
            connection_manager.disconnect(client_id)

async def market_data_pusher(client_id: str, connection_manager):
    """行情数据推送任务（Redis已移除，使用HTTP API获取数据）"""
    try:
        # Redis已完全移除，WebSocket行情推送已禁用
        logger.info(f"WebSocket行情推送已禁用（Redis已移除），客户端请使用HTTP API获取实时数据: {client_id}")

        while True:
            try:
                # 检查客户端是否还连接
                if client_id not in connection_manager.active_connections:
                    break

                # 发送心跳消息
                await connection_manager.send_personal_message({
                    "type": "heartbeat",
                    "message": "WebSocket连接正常，请使用HTTP API获取行情数据",
                    "timestamp": asyncio.get_event_loop().time()
                }, client_id)

                # 等待30秒再发送下一次心跳
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"WebSocket心跳异常: {e}")
                await asyncio.sleep(5)  # 出错时等待5秒再重试

    except asyncio.CancelledError:
        logger.info(f"WebSocket推送任务被取消: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket推送任务异常: {e}")

@router.get("/ws/status")
async def get_websocket_status():
    """获取WebSocket连接状态"""
    try:
        connection_manager = get_connection_manager()
        return connection_manager.get_connection_info()
    except Exception as e:
        logger.error(f"获取WebSocket状态失败: {e}")
        return {"error": str(e)}

# 用于测试的行情数据广播函数（已禁用）
async def broadcast_test_market_data():
    """广播测试行情数据（已禁用，使用真实CTP数据）"""
    logger.info("测试行情数据广播已禁用，请使用真实CTP数据")
    return

# 后台任务：定期广播测试数据（已禁用）
async def start_market_data_simulation():
    """启动行情数据模拟（已禁用）"""
    logger.info("行情数据模拟已禁用，请使用真实CTP数据")
    return
