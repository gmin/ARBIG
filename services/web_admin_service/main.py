#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG Web管理服务
微服务架构 - Web管理界面和API网关
"""

import sys
import os
import argparse
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import uuid

from shared.models.base import APIResponse, HealthCheckResponse, ServiceInfo, ServiceStatus
from shared.utils.service_client import ServiceClient, get_service_registry, call_service
from utils.logger import get_logger

logger = get_logger(__name__)

class WebAdminService:
    """Web管理服务"""
    
    def __init__(self):
        """初始化Web管理服务"""
        self.service_name = "web_admin_service"
        self.version = "2.0.0"
        self.start_time = datetime.now()
        self.running = False
        
        # 服务注册中心
        self.service_registry = get_service_registry()
        
        # 注册核心交易服务
        self._register_core_services()
        
        logger.info("Web管理服务初始化完成")
    
    def _register_core_services(self):
        """注册核心服务"""
        # 注册核心交易服务
        trading_service = ServiceInfo(
            name="trading_service",
            display_name="核心交易服务",
            status=ServiceStatus.STOPPED,
            host="localhost",
            port=8001,
            version="2.0.0",
            health_check_url="/health"
        )
        self.service_registry.register_service(trading_service)
    
    def start(self) -> bool:
        """启动Web管理服务"""
        try:
            logger.info("启动Web管理服务...")
            self.running = True
            logger.info("✅ Web管理服务启动成功")
            return True
        except Exception as e:
            logger.error(f"启动Web管理服务失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止Web管理服务"""
        try:
            logger.info("停止Web管理服务...")
            self.running = False
            logger.info("✅ Web管理服务已停止")
            return True
        except Exception as e:
            logger.error(f"停止Web管理服务失败: {e}")
            return False
    
    def get_status(self) -> dict:
        """获取服务状态"""
        uptime = ""
        if self.start_time:
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        return {
            "service_name": self.service_name,
            "status": "running" if self.running else "stopped",
            "version": self.version,
            "start_time": self.start_time.isoformat(),
            "uptime": uptime,
            "registered_services": len(self.service_registry.services)
        }

# 创建Web管理服务实例
web_admin_service = WebAdminService()

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG Web管理服务",
    description="ARBIG量化交易系统的Web管理界面和API网关",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册API路由
try:
    from api.trading import router as trading_router
    from api.websocket import router as websocket_router

    app.include_router(trading_router)
    app.include_router(websocket_router)
    logger.info("✅ 交易API路由注册成功")
except ImportError as e:
    logger.warning(f"⚠️ 交易API路由导入失败: {e}")

# 挂载静态文件（如果存在）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 模板引擎
from fastapi.templating import Jinja2Templates
templates_dir = Path(__file__).parent / "templates"
if templates_dir.exists():
    templates = Jinja2Templates(directory=templates_dir)
else:
    templates = None

@app.on_event("startup")
async def startup_event():
    """服务启动事件"""
    logger.info("🚀 启动Web管理服务...")

    # 初始化数据库连接
    try:
        from shared.database.connection import db_manager
        import json

        # 加载数据库配置
        config_file = project_root / "config" / "database.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                db_config = json.load(f)

            mysql_config = db_config['mysql']
            # Redis已完全移除，不再需要

            success = await db_manager.init_mysql(mysql_config)
            if success:
                logger.info("✅ MySQL数据库连接初始化成功（Redis已移除）")
            else:
                logger.error("❌ MySQL数据库连接初始化失败")
        else:
            logger.warning("⚠️ 数据库配置文件不存在，使用默认配置")

    except Exception as e:
        logger.error(f"❌ 数据库初始化异常: {e}")

    web_admin_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭事件"""
    logger.info("⏹️ 关闭Web管理服务...")
    web_admin_service.stop()

@app.get("/health", response_model=HealthCheckResponse, summary="健康检查")
async def health_check():
    """健康检查端点"""
    status = web_admin_service.get_status()
    
    # 检查核心服务健康状态
    dependencies = {}
    for service_name in web_admin_service.service_registry.services:
        try:
            client = web_admin_service.service_registry.get_client(service_name)
            if client:
                async with client:
                    health = await client.health_check()
                    dependencies[service_name] = health.status
            else:
                dependencies[service_name] = "unknown"
        except Exception:
            dependencies[service_name] = "unhealthy"
    
    return HealthCheckResponse(
        status="healthy" if web_admin_service.running else "unhealthy",
        timestamp=datetime.now(),
        uptime=status["uptime"],
        version=status["version"],
        dependencies=dependencies
    )

@app.get("/", response_class=HTMLResponse, summary="Web管理界面")
async def web_interface():
    """Web管理界面主页"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ARBIG量化交易系统 - Web管理界面</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
            .service-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
            .service-card { border: 1px solid #ddd; padding: 20px; border-radius: 6px; background: #fafafa; }
            .status-running { color: #28a745; font-weight: bold; }
            .status-stopped { color: #dc3545; font-weight: bold; }
            .btn { padding: 8px 16px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn-primary { background: #007acc; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .btn:hover { opacity: 0.8; }
            .api-links { margin: 20px 0; }
            .api-links a { margin-right: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏛️ ARBIG量化交易系统 v2.0</h1>
            <p><strong>微服务架构</strong> - Web管理界面</p>
            
            <div class="api-links">
                <a href="/trading" class="btn btn-success">📈 交易管理</a>
                <a href="/api/docs" class="btn btn-primary">📚 API文档</a>
                <a href="/health" class="btn btn-success">💚 健康检查</a>
                <a href="/api/v1/services" class="btn btn-primary">🔧 服务列表</a>
                <a href="/api/v1/system/status" class="btn btn-primary">📊 系统状态</a>
            </div>
            
            <h2>🔧 微服务管理</h2>
            <div class="service-grid">
                <div class="service-card">
                    <h3>核心交易服务</h3>
                    <p><strong>端口:</strong> 8001</p>
                    <p><strong>状态:</strong> <span id="trading-status" class="status-stopped">检查中...</span></p>
                    <a href="http://localhost:8001/docs" class="btn btn-primary" target="_blank">API文档</a>
                    <a href="http://localhost:8001/health" class="btn btn-success" target="_blank">健康检查</a>
                </div>
                
                <div class="service-card">
                    <h3>Web管理服务</h3>
                    <p><strong>端口:</strong> 80</p>
                    <p><strong>状态:</strong> <span class="status-running">运行中</span></p>
                    <a href="/api/docs" class="btn btn-primary">API文档</a>
                    <a href="/health" class="btn btn-success">健康检查</a>
                </div>
            </div>
            
            <h2>🎯 快速操作</h2>
            <div style="margin: 20px 0;">
                <button onclick="startSystem()" class="btn btn-success">启动交易系统</button>
                <button onclick="stopSystem()" class="btn btn-danger">停止交易系统</button>
                <button onclick="checkStatus()" class="btn btn-primary">检查系统状态</button>
            </div>
            
            <div id="result" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 4px; display: none;"></div>
        </div>
        
        <script>
            // 检查交易服务状态
            async function checkTradingServiceStatus() {
                try {
                    const response = await fetch('/api/v1/services/trading_service/status');
                    const data = await response.json();
                    const statusElement = document.getElementById('trading-status');
                    if (data.success && data.data.status === 'running') {
                        statusElement.textContent = '运行中';
                        statusElement.className = 'status-running';
                    } else {
                        statusElement.textContent = '已停止';
                        statusElement.className = 'status-stopped';
                    }
                } catch (error) {
                    const statusElement = document.getElementById('trading-status');
                    statusElement.textContent = '连接失败';
                    statusElement.className = 'status-stopped';
                }
            }
            
            async function startSystem() {
                showResult('正在启动交易系统...', 'info');
                try {
                    const response = await fetch('/api/v1/system/start', { method: 'POST' });
                    const data = await response.json();
                    showResult(data.message, data.success ? 'success' : 'error');
                    checkTradingServiceStatus();
                } catch (error) {
                    showResult('启动失败: ' + error.message, 'error');
                }
            }
            
            async function stopSystem() {
                showResult('正在停止交易系统...', 'info');
                try {
                    const response = await fetch('/api/v1/system/stop', { method: 'POST' });
                    const data = await response.json();
                    showResult(data.message, data.success ? 'success' : 'error');
                    checkTradingServiceStatus();
                } catch (error) {
                    showResult('停止失败: ' + error.message, 'error');
                }
            }
            
            async function checkStatus() {
                showResult('正在检查系统状态...', 'info');
                try {
                    const response = await fetch('/api/v1/system/status');
                    const data = await response.json();
                    if (data.success) {
                        const status = data.data;
                        showResult(`系统状态: ${status.system_status} | 运行模式: ${status.running_mode} | 运行时间: ${status.uptime}`, 'success');
                    } else {
                        showResult(data.message, 'error');
                    }
                    checkTradingServiceStatus();
                } catch (error) {
                    showResult('状态检查失败: ' + error.message, 'error');
                }
            }
            
            function showResult(message, type) {
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = message;
                resultDiv.style.background = type === 'success' ? '#d4edda' : 
                                           type === 'error' ? '#f8d7da' : '#d1ecf1';
                resultDiv.style.color = type === 'success' ? '#155724' : 
                                       type === 'error' ? '#721c24' : '#0c5460';
            }
            
            // 页面加载时检查服务状态
            window.onload = function() {
                checkTradingServiceStatus();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# API路由
@app.get("/api/v1/services", response_model=APIResponse, summary="获取所有服务")
async def get_all_services():
    """获取所有注册的服务"""
    try:
        services = web_admin_service.service_registry.list_services()
        services_data = [service.dict() for service in services]
        
        return APIResponse(
            success=True,
            message="服务列表获取成功",
            data={"services": services_data},
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取服务列表失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.get("/api/v1/services/{service_name}/status", response_model=APIResponse, summary="获取服务状态")
async def get_service_status(service_name: str):
    """获取指定服务的状态"""
    try:
        response = await call_service(service_name, "GET", "/status")
        return response
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取服务{service_name}状态失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.post("/api/v1/system/start", response_model=APIResponse, summary="启动交易系统")
async def start_trading_system():
    """启动交易系统"""
    try:
        response = await call_service("trading_service", "POST", "/system/start")
        return response
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"启动交易系统失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.post("/api/v1/system/stop", response_model=APIResponse, summary="停止交易系统")
async def stop_trading_system():
    """停止交易系统"""
    try:
        response = await call_service("trading_service", "POST", "/system/stop")
        return response
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"停止交易系统失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.get("/api/v1/system/status", response_model=APIResponse, summary="获取交易系统状态")
async def get_trading_system_status():
    """获取交易系统状态"""
    try:
        response = await call_service("trading_service", "GET", "/system/status")
        return response
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取交易系统状态失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.get("/trading", response_class=HTMLResponse, summary="交易管理页面")
async def trading_page(request: Request):
    """交易管理页面"""
    # 检查模板文件是否存在
    template_file = templates_dir / "trading.html" if templates_dir.exists() else None
    if templates and template_file and template_file.exists():
        return templates.TemplateResponse("trading.html", {"request": request})
    else:
        # 返回简单的交易管理页面
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ARBIG交易管理</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="Pragma" content="no-cache">
            <meta http-equiv="Expires" content="0">
            <link rel="stylesheet" href="/static/css/main.css?v=2.1">
        </head>
        <body>
            <nav class="navbar">
                <div class="container">
                    <h1>ARBIG交易管理</h1>
                    <ul class="nav-links">
                        <li><a href="/">首页</a></li>
                        <li><a href="/trading" class="active">交易管理</a></li>
                        <li><a href="/api/docs">API文档</a></li>
                    </ul>
                </div>
            </nav>

            <div class="container">
                <div class="grid grid-2">
                    <!-- 实时行情 -->
                    <div class="card">
                        <div class="card-header">实时行情 - au2508</div>
                        <div class="card-body">
                            <div class="connection-status">
                                <div class="connection-dot" id="market-connection"></div>
                                <span id="connection-text">连接中...</span>
                            </div>
                            <div class="market-data" id="market-data">
                                <div class="price-item">
                                    <div class="price-value" id="last-price">--</div>
                                    <div class="price-label">最新价</div>
                                </div>
                                <div class="price-item">
                                    <div class="price-value" id="bid-price">--</div>
                                    <div class="price-label">买一价</div>
                                </div>
                                <div class="price-item">
                                    <div class="price-value" id="ask-price">--</div>
                                    <div class="price-label">卖一价</div>
                                </div>
                                <div class="price-item">
                                    <div class="price-value" id="volume">--</div>
                                    <div class="price-label">成交量</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 账户信息 -->
                    <div class="card">
                        <div class="card-header">账户信息</div>
                        <div class="card-body">
                            <div class="grid grid-3">
                                <div class="metric neutral">
                                    <div class="metric-value" id="balance">--</div>
                                    <div class="metric-label">账户余额</div>
                                </div>
                                <div class="metric neutral">
                                    <div class="metric-value" id="available">--</div>
                                    <div class="metric-label">可用资金</div>
                                </div>
                                <div class="metric neutral">
                                    <div class="metric-value" id="unrealized-pnl">--</div>
                                    <div class="metric-label">未实现盈亏</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 手动交易 -->
                <div class="card">
                    <div class="card-header">手动交易 - au2508</div>
                    <div class="card-body">
                        <div class="grid grid-2">
                            <div class="trading-panel">
                                <h4>开仓交易</h4>
                                <div class="form-group">
                                    <label>交易方向:</label>
                                    <div class="btn-group">
                                        <button class="btn btn-success" id="buy-btn" onclick="setDirection('BUY')">买入开多</button>
                                        <button class="btn btn-danger" id="sell-btn" onclick="setDirection('SELL')">卖出开空</button>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label>交易数量:</label>
                                    <input type="number" id="volume-input" value="1" min="1" max="100" class="form-input">
                                </div>
                                <div class="form-group">
                                    <label>订单类型:</label>
                                    <select id="order-type-select" class="form-select">
                                        <option value="MARKET">市价单</option>
                                        <option value="LIMIT">限价单</option>
                                    </select>
                                </div>
                                <div class="form-group" id="price-group" style="display: none;">
                                    <label>限价价格:</label>
                                    <input type="number" id="price-input" step="0.01" class="form-input">
                                </div>
                                <button class="btn btn-primary" onclick="submitOrder()" id="submit-order-btn">
                                    提交订单
                                </button>
                            </div>

                            <div class="trading-panel">
                                <h4>快速平仓</h4>
                                <div class="form-group">
                                    <label>平仓合约:</label>
                                    <select id="close-symbol-select" class="form-select">
                                        <option value="au2508">au2508</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>平仓数量:</label>
                                    <input type="number" id="close-volume-input" value="0" min="0" class="form-input" placeholder="0=全部平仓">
                                </div>
                                <button class="btn btn-warning" onclick="closeAllPositions()">
                                    一键平仓
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 持仓信息 -->
                <div class="card">
                    <div class="card-header">持仓信息</div>
                    <div class="card-body">
                        <table class="data-table" id="positions-table">
                            <thead>
                                <tr>
                                    <th>合约</th>
                                    <th>方向</th>
                                    <th>数量</th>
                                    <th>成本价</th>
                                    <th>当前价</th>
                                    <th>盈亏</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="7" style="text-align: center; color: #666;">暂无持仓</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 策略管理 -->
                <div class="card">
                    <div class="card-header">
                        策略管理
                        <div style="float: right;">
                            <button class="btn btn-danger" onclick="emergencyStop()" style="margin-left: 10px;">
                                🚨 紧急停止
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <table class="data-table" id="strategy-table">
                            <thead>
                                <tr>
                                    <th>策略名称</th>
                                    <th>状态</th>
                                    <th>今日触发</th>
                                    <th>成功率</th>
                                    <th>最后触发</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" style="text-align: center; color: #666;">加载中...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 策略触发记录 -->
                <div class="card">
                    <div class="card-header">策略触发记录</div>
                    <div class="card-body">
                        <table class="data-table" id="triggers-table">
                            <thead>
                                <tr>
                                    <th>策略名称</th>
                                    <th>触发时间</th>
                                    <th>触发条件</th>
                                    <th>信号类型</th>
                                    <th>执行结果</th>
                                    <th>订单ID</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td colspan="6" style="text-align: center; color: #666;">加载中...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <script src="/static/js/utils.js"></script>
            <script>
                // 初始化API客户端
                const api = new APIClient();

                // 初始化WebSocket
                const wsUrl = `ws://${window.location.host}/ws`;
                const ws = new WebSocketManager(wsUrl);

                // 连接状态处理
                ws.on('connected', () => {
                    document.getElementById('market-connection').classList.add('connected');
                    document.getElementById('connection-text').textContent = '已连接';

                    // 订阅行情数据
                    ws.subscribe('market_data:au2508');
                });

                ws.on('disconnected', () => {
                    document.getElementById('market-connection').classList.remove('connected');
                    document.getElementById('connection-text').textContent = '连接断开';
                });

                // 行情数据处理
                ws.on('market_data', (data) => {
                    const tickData = data.data;
                    document.getElementById('last-price').textContent = Utils.formatNumber(tickData.last_price);
                    document.getElementById('bid-price').textContent = Utils.formatNumber(tickData.bid_price);
                    document.getElementById('ask-price').textContent = Utils.formatNumber(tickData.ask_price);
                    document.getElementById('volume').textContent = tickData.volume;
                });

                // 加载行情数据
                async function loadMarketData() {
                    try {
                        // 优先从CTP状态接口获取数据，确保数据来源一致
                        const response = await fetch('/api/v1/trading/ctp_status');
                        const statusData = await response.json();

                        if (statusData.success && statusData.data.tick_data && statusData.data.tick_data.au2508) {
                            const tickData = statusData.data.tick_data.au2508;
                            document.getElementById('last-price').textContent = Utils.formatNumber(tickData.last_price);
                            document.getElementById('bid-price').textContent = Utils.formatNumber(tickData.bid_price);
                            document.getElementById('ask-price').textContent = Utils.formatNumber(tickData.ask_price);
                            document.getElementById('volume').textContent = tickData.volume;

                            console.log('行情数据来源:', tickData.data_source || 'CTP_STATUS', '价格:', tickData.last_price);
                            return;
                        }

                        // 如果状态接口失败，尝试直接API（需要解析包装的响应）
                        const tickResponse = await fetch('/api/v1/trading/tick/au2508');
                        if (tickResponse.ok) {
                            const tickResult = await tickResponse.json();
                            if (tickResult.success && tickResult.data && tickResult.data.response) {
                                // 解析ServiceClient包装的响应
                                const innerData = JSON.parse(tickResult.data.response);
                                if (innerData.success && innerData.data) {
                                    const tickData = innerData.data;
                                    document.getElementById('last-price').textContent = Utils.formatNumber(tickData.last_price);
                                    document.getElementById('bid-price').textContent = Utils.formatNumber(tickData.bid_price);
                                    document.getElementById('ask-price').textContent = Utils.formatNumber(tickData.ask_price);
                                    document.getElementById('volume').textContent = tickData.volume;

                                    console.log('行情数据来源:', tickData.data_source || 'DIRECT_API', '价格:', tickData.last_price);
                                    return;
                                }
                            }
                        }

                        throw new Error('无法获取行情数据');
                    } catch (error) {
                        console.error('加载行情数据失败:', error);
                        // 显示默认值
                        document.getElementById('last-price').textContent = '--';
                        document.getElementById('bid-price').textContent = '--';
                        document.getElementById('ask-price').textContent = '--';
                        document.getElementById('volume').textContent = '--';
                    }
                }

                // 加载账户信息
                async function loadAccountInfo() {
                    try {
                        // 直接调用真实的账户API
                        const response = await fetch('/api/v1/trading/ctp_status');
                        const statusData = await response.json();

                        if (statusData.success && statusData.data.account_info) {
                            const account = statusData.data.account_info;
                            document.getElementById('balance').textContent = Utils.formatCurrency(account.balance);
                            document.getElementById('available').textContent = Utils.formatCurrency(account.available);
                            document.getElementById('unrealized-pnl').textContent = Utils.formatCurrency(account.close_profit || 0);

                            // 设置盈亏颜色
                            const pnlElement = document.getElementById('unrealized-pnl').parentElement;
                            pnlElement.className = `metric ${Utils.getPriceChangeClass(account.close_profit || 0)}`;
                        } else {
                            // 显示默认值
                            document.getElementById('balance').textContent = '--';
                            document.getElementById('available').textContent = '--';
                            document.getElementById('unrealized-pnl').textContent = '--';
                        }
                    } catch (error) {
                        console.error('加载账户信息失败:', error);
                        // 显示默认值
                        document.getElementById('balance').textContent = '--';
                        document.getElementById('available').textContent = '--';
                        document.getElementById('unrealized-pnl').textContent = '--';
                    }
                }

                // 加载持仓信息
                async function loadPositions() {
                    try {
                        const response = await api.get('/api/v1/trading/positions');
                        const tbody = document.querySelector('#positions-table tbody');

                        // 处理持仓数据格式 - API现在直接返回数组
                        let positionsArray = [];
                        if (Array.isArray(response)) {
                            // API直接返回数组格式
                            positionsArray = response.map(pos => ({
                                symbol: pos.symbol,
                                direction: pos.direction.toLowerCase(), // 转换为小写以匹配前端逻辑
                                volume: pos.volume,
                                avg_price: pos.avg_price,
                                current_price: pos.current_price || 0,
                                unrealized_pnl: pos.unrealized_pnl || 0
                            }));
                        } else if (response.success && response.data) {
                            // 兼容旧的对象格式
                            Object.keys(response.data).forEach(symbol => {
                                const pos = response.data[symbol];
                                if (pos.long_position > 0) {
                                    positionsArray.push({
                                        symbol: symbol,
                                        direction: 'long',
                                        volume: pos.long_position,
                                        avg_price: pos.long_price,
                                        current_price: pos.current_price || 0,
                                        unrealized_pnl: pos.long_pnl || 0
                                    });
                                }
                                if (pos.short_position > 0) {
                                    positionsArray.push({
                                        symbol: symbol,
                                        direction: 'short',
                                        volume: pos.short_position,
                                        avg_price: pos.short_price,
                                        current_price: pos.current_price || 0,
                                        unrealized_pnl: pos.short_pnl || 0
                                    });
                                }
                            });
                        }

                        if (positionsArray.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #666;">暂无持仓</td></tr>';
                            return;
                        }

                        tbody.innerHTML = positionsArray.map(pos => `
                            <tr>
                                <td>${pos.symbol}</td>
                                <td>${pos.direction === 'long' ? '多头' : '空头'}</td>
                                <td>${pos.volume}</td>
                                <td>${Utils.formatNumber(pos.avg_price)}</td>
                                <td>${Utils.formatNumber(pos.current_price)}</td>
                                <td style="color: ${pos.unrealized_pnl >= 0 ? '#28a745' : '#dc3545'}">${Utils.formatNumber(pos.unrealized_pnl)}</td>
                                <td>
                                    <button class="btn btn-danger" onclick="closePosition('${pos.symbol}', '${pos.direction}', ${pos.volume})">平仓</button>
                                </td>
                            </tr>
                        `).join('');
                    } catch (error) {
                        console.error('加载持仓信息失败:', error);
                        const tbody = document.querySelector('#positions-table tbody');
                        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #666;">加载失败</td></tr>';
                    }
                }

                // 平仓操作 - 修复为使用symbol而不是positionId
                async function closePosition(symbol, direction, volume) {
                    Utils.confirm(`确定要平仓 ${symbol} ${direction === 'long' ? '多头' : '空头'} ${volume}手 吗？`, async () => {
                        try {
                            // 使用一键平仓API，但指定具体的方向和数量
                            const closeData = {
                                symbol: symbol,
                                volume: volume,
                                direction: direction  // 指定平仓方向
                            };
                            const result = await api.post('/api/v1/trading/close_position', closeData);
                            Utils.showNotification(result.message || '平仓操作成功', 'success');
                            loadPositions(); // 重新加载持仓
                        } catch (error) {
                            console.error('平仓失败:', error);
                            const errorMsg = error.response?.data?.detail || error.message || '未知错误';
                            Utils.showNotification('平仓失败: ' + errorMsg, 'error');
                        }
                    });
                }

                // 加载策略状态
                async function loadStrategyStatus() {
                    try {
                        const strategies = await api.get('/api/v1/trading/strategy/status');
                        const tbody = document.querySelector('#strategy-table tbody');

                        if (strategies.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">暂无策略</td></tr>';
                            return;
                        }

                        tbody.innerHTML = strategies.map(strategy => `
                            <tr>
                                <td>${strategy.strategy_name}</td>
                                <td>
                                    <span class="status ${strategy.is_active ? 'online' : 'offline'}">
                                        ${strategy.is_active ? '运行中' : '已停止'}
                                    </span>
                                </td>
                                <td>${strategy.trigger_count_today}</td>
                                <td>${(strategy.success_rate * 100).toFixed(1)}%</td>
                                <td>${strategy.last_trigger_time ? Utils.formatRelativeTime(strategy.last_trigger_time) : '--'}</td>
                                <td>
                                    ${strategy.is_active ?
                                        `<button class="btn btn-danger" onclick="stopStrategy('${strategy.strategy_name}')">停止</button>` :
                                        `<button class="btn btn-success" onclick="startStrategy('${strategy.strategy_name}')">启动</button>`
                                    }
                                </td>
                            </tr>
                        `).join('');
                    } catch (error) {
                        console.error('加载策略状态失败:', error);
                        Utils.showNotification('加载策略状态失败', 'error');
                    }
                }

                // 启动策略
                async function startStrategy(strategyName) {
                    Utils.confirm(`确定要启动策略 ${strategyName} 吗？`, async () => {
                        try {
                            const result = await api.post(`/api/v1/trading/strategy/${strategyName}/start`);
                            Utils.showNotification(result.message, 'success');
                            loadStrategyStatus(); // 重新加载策略状态
                        } catch (error) {
                            Utils.showNotification('启动策略失败: ' + error.message, 'error');
                        }
                    });
                }

                // 停止策略
                async function stopStrategy(strategyName) {
                    Utils.confirm(`确定要停止策略 ${strategyName} 吗？`, async () => {
                        try {
                            const result = await api.post(`/api/v1/trading/strategy/${strategyName}/stop`);
                            Utils.showNotification(result.message, 'success');
                            loadStrategyStatus(); // 重新加载策略状态
                        } catch (error) {
                            Utils.showNotification('停止策略失败: ' + error.message, 'error');
                        }
                    });
                }

                // 紧急停止
                async function emergencyStop() {
                    Utils.confirm('⚠️ 确定要执行系统紧急停止吗？这将停止所有策略！', async () => {
                        try {
                            const result = await api.post('/api/v1/trading/emergency_stop');
                            Utils.showNotification(result.message, 'warning');
                            loadStrategyStatus(); // 重新加载策略状态
                        } catch (error) {
                            Utils.showNotification('紧急停止失败: ' + error.message, 'error');
                        }
                    });
                }

                // 手动交易相关函数
                let selectedDirection = 'BUY';

                // 设置交易方向
                function setDirection(direction) {
                    selectedDirection = direction;
                    document.getElementById('buy-btn').classList.toggle('active', direction === 'BUY');
                    document.getElementById('sell-btn').classList.toggle('active', direction === 'SELL');
                }

                // 订单类型变化处理
                document.getElementById('order-type-select').addEventListener('change', function() {
                    const priceGroup = document.getElementById('price-group');
                    if (this.value === 'LIMIT') {
                        priceGroup.style.display = 'block';
                        // 设置当前价格作为默认限价
                        const currentPrice = document.getElementById('last-price').textContent;
                        if (currentPrice !== '--') {
                            document.getElementById('price-input').value = currentPrice;
                        }
                    } else {
                        priceGroup.style.display = 'none';
                    }
                });

                // 提交订单
                async function submitOrder() {
                    try {
                        const volume = parseInt(document.getElementById('volume-input').value);
                        const orderType = document.getElementById('order-type-select').value;
                        const price = orderType === 'LIMIT' ? parseFloat(document.getElementById('price-input').value) : 0;

                        if (volume <= 0) {
                            Utils.showNotification('请输入有效的交易数量', 'error');
                            return;
                        }

                        if (orderType === 'LIMIT' && price <= 0) {
                            Utils.showNotification('请输入有效的限价价格', 'error');
                            return;
                        }

                        const orderData = {
                            symbol: 'au2508',
                            direction: selectedDirection,
                            volume: volume,
                            order_type: orderType,
                            offset: 'AUTO'
                        };

                        if (orderType === 'LIMIT') {
                            orderData.price = price;
                        }

                        Utils.confirm(`确定要${selectedDirection === 'BUY' ? '买入' : '卖出'} ${volume}手 au2508 吗？`, async () => {
                            try {
                                document.getElementById('submit-order-btn').disabled = true;
                                document.getElementById('submit-order-btn').textContent = '提交中...';

                                const result = await api.post('/api/v1/trading/manual_order', orderData);
                                Utils.showNotification(result.message || '订单提交成功', 'success');

                                // 重新加载持仓信息
                                loadPositions();

                                // 重置表单
                                document.getElementById('volume-input').value = '1';
                                document.getElementById('price-input').value = '';

                            } catch (error) {
                                Utils.showNotification('订单提交失败: ' + error.message, 'error');
                            } finally {
                                document.getElementById('submit-order-btn').disabled = false;
                                document.getElementById('submit-order-btn').textContent = '提交订单';
                            }
                        });

                    } catch (error) {
                        Utils.showNotification('订单提交失败: ' + error.message, 'error');
                    }
                }

                // 一键平仓
                async function closeAllPositions() {
                    try {
                        const symbol = document.getElementById('close-symbol-select').value;
                        const volume = parseInt(document.getElementById('close-volume-input').value) || 0;

                        Utils.confirm(`确定要平仓 ${symbol} ${volume > 0 ? volume + '手' : '全部持仓'} 吗？`, async () => {
                            try {
                                const closeData = { symbol: symbol };
                                if (volume > 0) {
                                    closeData.volume = volume;
                                }

                                const result = await api.post('/api/v1/trading/close_position', closeData);
                                Utils.showNotification(result.message || '平仓操作成功', 'success');

                                // 重新加载持仓信息
                                loadPositions();

                            } catch (error) {
                                Utils.showNotification('平仓操作失败: ' + error.message, 'error');
                            }
                        });

                    } catch (error) {
                        Utils.showNotification('平仓操作失败: ' + error.message, 'error');
                    }
                }

                // 加载策略触发记录
                async function loadStrategyTriggers() {
                    try {
                        const triggers = await api.get('/api/v1/trading/strategy/triggers?limit=20');
                        const tbody = document.querySelector('#triggers-table tbody');

                        if (triggers.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">暂无触发记录</td></tr>';
                            return;
                        }

                        tbody.innerHTML = triggers.map(trigger => `
                            <tr>
                                <td>${trigger.strategy_name}</td>
                                <td>${Utils.formatTime(trigger.trigger_time)}</td>
                                <td>${trigger.trigger_condition}</td>
                                <td>
                                    <span class="status ${trigger.signal_type === 'buy' || trigger.signal_type === 'sell' ? 'warning' : 'neutral'}">
                                        ${trigger.signal_type}
                                    </span>
                                </td>
                                <td>
                                    <span class="status ${trigger.execution_result === 'success' ? 'online' : trigger.execution_result === 'failed' ? 'offline' : 'warning'}">
                                        ${trigger.execution_result}
                                    </span>
                                </td>
                                <td>${trigger.order_id || '--'}</td>
                            </tr>
                        `).join('');
                    } catch (error) {
                        console.error('加载策略触发记录失败:', error);
                        Utils.showNotification('加载策略触发记录失败', 'error');
                    }
                }

                // 初始化
                ws.connect();
                loadMarketData();
                loadAccountInfo();
                loadPositions();
                loadStrategyStatus();
                loadStrategyTriggers();

                // 设置默认交易方向
                setDirection('BUY');

                // 定期刷新数据
                setInterval(loadMarketData, 3000);
                setInterval(loadAccountInfo, 5000);
                setInterval(loadPositions, 10000);
                setInterval(loadStrategyStatus, 15000);
                setInterval(loadStrategyTriggers, 30000);
            </script>
        </body>
        </html>
        """

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG Web管理服务')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=80,
                       help='服务器端口')
    parser.add_argument('--reload', action='store_true',
                       help='开发模式：自动重载')
    parser.add_argument('--log-level', type=str, default='info',
                       choices=['debug', 'info', 'warning', 'error'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("🌐 ARBIG Web管理服务 v2.0")
    logger.info("🔄 微服务架构 - Web管理界面")
    logger.info("="*60)
    
    try:
        logger.info(f"🚀 启动服务器: http://{args.host}:{args.port}")
        
        uvicorn.run(
            "services.web_admin_service.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
