"""
ARBIG Web API 主应用
FastAPI应用的入口点，集成所有API路由
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
import uuid
import os
import json
import asyncio
from pathlib import Path
from typing import List

from .routers import system_router, services_router, strategies_router, data_router
from .models.responses import APIResponse, ErrorResponse

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

# 创建连接管理器实例
manager = ConnectionManager()

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG Web指挥中轴 API",
    description="ARBIG量化交易系统的Web指挥中轴API接口",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 注册路由
app.include_router(system_router)
app.include_router(services_router)
app.include_router(strategies_router)
app.include_router(data_router)

# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await manager.connect(websocket)
    try:
        # 发送连接成功消息
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "WebSocket连接成功",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )

        # 定期发送心跳和状态更新
        while True:
            # 发送心跳
            await manager.send_personal_message(
                json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )

            # 等待30秒
            await asyncio.sleep(30)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error={
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": None
            },
            request_id=str(uuid.uuid4())
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error={
                "code": "INTERNAL_ERROR",
                "message": "内部服务器错误",
                "details": str(exc)
            },
            request_id=str(uuid.uuid4())
        ).dict()
    )

# Web界面路由
@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Web监控界面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        index_file = static_dir / "index.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("""
            <html>
            <head><title>ARBIG监控系统</title></head>
            <body>
                <h1>ARBIG Web指挥中轴</h1>
                <p>状态: 运行中</p>
                <p>版本: 1.0.0</p>
                <p><a href="/api/docs">API文档</a></p>
                <p>静态文件未找到，请检查 static/index.html</p>
            </body>
            </html>
            """)
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/strategy_monitor.html", response_class=HTMLResponse)
async def strategy_monitor():
    """策略监控页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        monitor_file = static_dir / "strategy_monitor.html"
        if monitor_file.exists():
            with open(monitor_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>策略监控页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

# API信息路径
@app.get("/api/info", response_model=APIResponse)
async def api_info():
    """API信息"""
    return APIResponse(
        success=True,
        message="ARBIG Web指挥中轴 API",
        data={
            "version": "1.0.0",
            "description": "ARBIG量化交易系统的Web指挥中轴API接口",
            "docs_url": "/api/docs",
            "status": "running"
        },
        request_id=str(uuid.uuid4())
    )

# 健康检查
@app.get("/health", response_model=APIResponse)
async def health_check():
    """健康检查接口"""
    return APIResponse(
        success=True,
        message="API服务运行正常",
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        request_id=str(uuid.uuid4())
    )

# API信息
@app.get("/api/info", response_model=APIResponse)
async def api_info():
    """API信息接口"""
    return APIResponse(
        success=True,
        message="API信息获取成功",
        data={
            "title": "ARBIG Web指挥中轴 API",
            "version": "1.0.0",
            "description": "ARBIG量化交易系统的Web指挥中轴API接口",
            "endpoints": {
                "system": "/api/v1/system",
                "services": "/api/v1/services",
                "strategies": "/api/v1/strategies",
                "data": "/api/v1/data"
            },
            "documentation": {
                "swagger": "/api/docs",
                "redoc": "/api/redoc"
            }
        },
        request_id=str(uuid.uuid4())
    )

# 启动函数
def start_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """启动API服务器"""
    uvicorn.run(
        "web_admin.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    start_api_server(reload=True)
