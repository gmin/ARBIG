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

try:
    from .routers import system_router, services_router, strategies_router, data_router
except ImportError:
    # 如果相对导入失败，使用绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from web_admin.api.routers import system_router, services_router, strategies_router, data_router
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
    error_response = ErrorResponse(
        error={
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": None
        },
        request_id=str(uuid.uuid4())
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    error_response = ErrorResponse(
        error={
            "code": "INTERNAL_ERROR",
            "message": "内部服务器错误",
            "details": str(exc)
        },
        request_id=str(uuid.uuid4())
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
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

@app.get("/test_simple.html", response_class=HTMLResponse)
async def test_simple():
    """简单测试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        test_file = static_dir / "test_simple.html"
        if test_file.exists():
            with open(test_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("""
            <html>
            <head><title>测试页面</title></head>
            <body>
            <h1>如果您能看到这个页面，说明Web服务器工作正常</h1>
            <p>当前时间: <span id="time"></span></p>
            <script>
            document.getElementById('time').textContent = new Date().toLocaleString();
            </script>
            </body>
            </html>
            """)
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/debug.html", response_class=HTMLResponse)
async def debug_page():
    """调试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        debug_file = static_dir / "debug.html"
        if debug_file.exists():
            with open(debug_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>调试页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/static_test.html", response_class=HTMLResponse)
async def static_test_page():
    """静态测试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        test_file = static_dir / "static_test.html"
        if test_file.exists():
            with open(test_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>静态测试页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/simple_test.html", response_class=HTMLResponse)
async def simple_test_page():
    """简单测试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        test_file = static_dir / "simple_test.html"
        if test_file.exists():
            with open(test_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>简单测试页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/minimal_index.html", response_class=HTMLResponse)
async def minimal_index_page():
    """简化主页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        index_file = static_dir / "minimal_index.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>简化主页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/debug_positions.html", response_class=HTMLResponse)
async def debug_positions_page():
    """持仓调试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        debug_file = static_dir / "debug_positions.html"
        if debug_file.exists():
            with open(debug_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>持仓调试页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/minimal_test.html", response_class=HTMLResponse)
async def minimal_test_page():
    """最小测试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        test_file = static_dir / "minimal_test.html"
        if test_file.exists():
            with open(test_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>最小测试页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/emergency_debug.html", response_class=HTMLResponse)
async def emergency_debug_page():
    """紧急调试页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        debug_file = static_dir / "emergency_debug.html"
        if debug_file.exists():
            with open(debug_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("""
            <html>
            <head><title>紧急调试</title></head>
            <body style="font-family: Arial; margin: 20px;">
                <h1 style="color: red;">🚨 紧急调试页面</h1>
                <p><strong>如果您能看到这个页面，说明Web服务器正常工作</strong></p>
                <p>当前时间: <span id="time"></span></p>
                <script>
                    document.getElementById('time').textContent = new Date().toLocaleString();
                    setInterval(function() {
                        document.getElementById('time').textContent = new Date().toLocaleString();
                    }, 1000);
                </script>
            </body>
            </html>
            """)
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/super_simple", response_class=HTMLResponse)
async def super_simple():
    """超级简单的测试页面"""
    return HTMLResponse("""
    <html>
    <body style="background: yellow; font-size: 48px; text-align: center; padding: 50px;">
        <h1 style="color: red;">🚨 超级简单测试</h1>
        <p style="color: blue;">如果您能看到这个黄色页面，说明网络连接正常！</p>
        <p style="color: green;">时间: <span id="t"></span></p>
        <script>document.getElementById('t').innerHTML=new Date();</script>
    </body>
    </html>
    """)

@app.get("/index_no_ws.html", response_class=HTMLResponse)
async def index_no_websocket():
    """无WebSocket版本的主页面"""
    try:
        static_dir = Path(__file__).parent.parent / "static"
        index_file = static_dir / "index_no_ws.html"
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse("<html><body><h1>无WebSocket版本页面未找到</h1></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body><h1>错误</h1><p>{str(e)}</p></body></html>")

@app.get("/docs", response_class=HTMLResponse)
async def api_docs():
    """API文档页面"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ARBIG API 文档</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 1000px; margin: 0 auto; }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .method { display: inline-block; padding: 4px 8px; border-radius: 3px; color: white; font-weight: bold; margin-right: 10px; }
            .get { background: #28a745; }
            .post { background: #007bff; }
            .put { background: #ffc107; color: #212529; }
            .delete { background: #dc3545; }
            code { background: #e9ecef; padding: 2px 4px; border-radius: 3px; }
            .description { margin-top: 10px; color: #6c757d; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 ARBIG API 文档</h1>
            <p>ARBIG 量化交易系统 RESTful API 接口文档</p>

            <h2>📊 系统管理</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/system/status</code>
                <div class="description">获取系统运行状态、CTP连接状态、服务状态等信息</div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/v1/system/start</code>
                <div class="description">启动ARBIG系统核心服务</div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/v1/system/stop</code>
                <div class="description">停止ARBIG系统核心服务</div>
            </div>

            <h2>💰 账户数据</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/data/account/info</code>
                <div class="description">获取账户基本信息：总资产、可用资金、保证金等</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/data/account/positions</code>
                <div class="description">获取当前持仓信息</div>
            </div>

            <h2>⚠️ 风险管理</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/data/risk/metrics</code>
                <div class="description">获取风险指标：风险度、最大回撤、夏普比率等</div>
            </div>

            <h2>📈 策略管理</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/strategies/list</code>
                <div class="description">获取所有可用策略列表</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/strategies/{strategy_id}/details</code>
                <div class="description">获取指定策略的详细信息</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/strategies/{strategy_id}/params</code>
                <div class="description">获取策略参数配置</div>
            </div>

            <h2>📋 订单管理</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/v1/data/orders</code>
                <div class="description">获取订单列表，支持 active_only=true 参数只获取活跃订单</div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/v1/trading/order</code>
                <div class="description">提交交易订单</div>
            </div>

            <h2>🔌 实时数据</h2>
            <div class="endpoint">
                <span class="method get">WebSocket</span>
                <code>/ws</code>
                <div class="description">WebSocket连接，用于实时推送市场数据、订单状态、账户变化等</div>
            </div>

            <h2>🌐 Web页面</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/</code>
                <div class="description">主管理界面</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/minimal_index.html</code>
                <div class="description">简化版管理界面</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/static_test.html</code>
                <div class="description">静态测试页面</div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/simple_test.html</code>
                <div class="description">JavaScript功能测试页面</div>
            </div>

            <h2>📝 使用示例</h2>
            <div class="endpoint">
                <h3>获取系统状态</h3>
                <code>curl http://localhost:8000/api/v1/system/status</code>
            </div>
            <div class="endpoint">
                <h3>获取账户信息</h3>
                <code>curl http://localhost:8000/api/v1/data/account/info</code>
            </div>
            <div class="endpoint">
                <h3>启动系统</h3>
                <code>curl -X POST http://localhost:8000/api/v1/system/start</code>
            </div>

            <h2>📞 技术支持</h2>
            <p>如需技术支持，请查看系统日志文件：<code>logs/gold_arbitrage_*.log</code></p>
            <p>系统版本：ARBIG v1.0</p>
            <p>最后更新：2025-07-22</p>
        </div>
    </body>
    </html>
    """)

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
