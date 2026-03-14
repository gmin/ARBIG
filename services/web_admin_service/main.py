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
from utils.service_client import ServiceClient, get_service_registry, call_service
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
        # 先清理可能存在的旧服务注册
        if "trading_service" in self.service_registry.services:
            logger.info("清理旧的trading_service注册")
            del self.service_registry.services["trading_service"]

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
        logger.info("注册trading_service: http://localhost:8001")

        # 注册策略服务
        if "strategy_service" in self.service_registry.services:
            del self.service_registry.services["strategy_service"]

        strategy_service = ServiceInfo(
            name="strategy_service",
            display_name="策略服务",
            status=ServiceStatus.STOPPED,
            host="localhost",
            port=8002,
            version="2.0.0",
            health_check_url="/health"
        )
        self.service_registry.register_service(strategy_service)
        logger.info("注册strategy_service: http://localhost:8002")
    
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
async def web_interface(request: Request):
    """Web管理界面主页 - Dashboard"""
    # 检查模板文件是否存在
    template_file = templates_dir / "dashboard.html" if templates_dir.exists() else None
    if templates and template_file and template_file.exists():
        return templates.TemplateResponse("dashboard.html", {"request": request})
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ARBIG量化交易系统</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>ARBIG量化交易系统</h1>
            <p>Dashboard模板文件不存在，请检查 templates/dashboard.html</p>
        </body>
        </html>
        """)

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

@app.get("/strategy", response_class=HTMLResponse, summary="策略管理页面")
async def strategy_page(request: Request):
    """统一的策略管理页面"""
    # 使用基础模板（现在包含增强版内容）
    template_file = templates_dir / "strategy.html" if templates_dir.exists() else None

    if templates and template_file and template_file.exists():
        logger.info("使用strategy.html模板")
        return templates.TemplateResponse("strategy.html", {"request": request})
    else:
        logger.warning("模板文件不存在，使用内置策略管理页面")
        # 返回完整的策略管理页面
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ARBIG策略管理</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/static/css/dashboard.css?v=2.1">
        </head>
        <body>
            <nav class="navbar">
                <div class="container">
                    <h1>ARBIG策略管理</h1>
                    <ul class="nav-links">
                        <li><a href="/">总控台</a></li>
                        <li><a href="/strategy" class="active">策略中心</a></li>
                        <li><a href="/trading_logs">交易日志</a></li>
                    </ul>
                </div>
            </nav>
            <div class="container">
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
            </div>

            <script>
                // 加载策略状态
                async function loadStrategyStatus() {
                    console.log('🔍 开始加载策略状态...');

                    try {
                        // 调用回测服务的策略API
                        console.log('📡 发送API请求到: http://localhost:8002/backtest/strategies');
                        const response = await fetch('http://localhost:8002/backtest/strategies');

                        console.log('📊 响应状态:', response.status, response.statusText);

                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }

                        const result = await response.json();
                        console.log('📊 API响应:', result);

                        let strategies = [];
                        if (result.success && result.data && result.data.strategies) {
                            strategies = result.data.strategies;
                            console.log('✅ 使用 result.data.strategies');
                        } else if (result.data && Array.isArray(result.data)) {
                            strategies = result.data;
                            console.log('✅ 使用 result.data (数组)');
                        } else if (Array.isArray(result)) {
                            strategies = result;
                            console.log('✅ 使用 result (数组)');
                        } else {
                            console.log('❌ 无法解析策略数据:', result);
                        }

                        console.log('📋 解析后的策略列表:', strategies);
                        console.log('📊 策略数量:', strategies.length);

                        const tbody = document.querySelector('#strategy-table tbody');
                        if (!tbody) {
                            console.error('❌ 找不到策略表格元素');
                            return;
                        }

                        if (strategies.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #666;">暂无策略</td></tr>';
                            return;
                        }

                        // 适配回测API的数据格式
                        tbody.innerHTML = strategies.map(strategyName => `
                            <tr>
                                <td>${strategyName}</td>
                                <td>
                                    <span class="status neutral">
                                        可用于回测
                                    </span>
                                </td>
                                <td>--</td>
                                <td>--</td>
                                <td>--</td>
                                <td>
                                    <button class="btn btn-primary" onclick="quickBacktest('${strategyName}')">快速回测</button>
                                    <button class="btn btn-info" onclick="advancedBacktest('${strategyName}')">高级回测</button>
                                </td>
                            </tr>
                        `).join('');
                    } catch (error) {
                        console.error('❌ 加载策略状态失败:', error);
                        console.error('❌ 错误详情:', error.message);

                        const tbody = document.querySelector('#strategy-table tbody');
                        if (tbody) {
                            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #f56565;">
                                加载策略失败: ${error.message}<br>
                                <small>请检查浏览器控制台获取详细信息</small>
                            </td></tr>`;
                        }

                        showNotification('策略加载失败: ' + error.message, 'error');
                    }
                }

                // 快速回测
                async function quickBacktest(strategyName) {
                    if (confirm(`确定要对策略 ${strategyName} 进行快速回测吗？`)) {
                        try {
                            showNotification('正在进行快速回测...', 'info');
                            const response = await fetch('http://localhost:8002/backtest/quick', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({strategy_name: strategyName, days: 7, strategy_setting: {max_position: 5}})
                            });
                            const result = await response.json();

                            if (result.success) {
                                const metrics = result.key_metrics;
                                showNotification(
                                    `回测完成！收益率: ${(metrics.total_return * 100).toFixed(2)}%, 胜率: ${(metrics.win_rate * 100).toFixed(1)}%`,
                                    'success'
                                );
                            } else {
                                showNotification('回测失败: ' + (result.message || '未知错误'), 'error');
                            }
                        } catch (error) {
                            showNotification('回测失败: ' + error.message, 'error');
                        }
                    }
                }

                // 高级回测
                async function advancedBacktest(strategyName) {
                    showNotification(`正在打开 ${strategyName} 的高级回测页面...`, 'info');
                    window.open(`http://localhost:8003/docs`, '_blank');
                }

                // 紧急停止
                async function emergencyStop() {
                    if (confirm('⚠️ 确定要执行系统紧急停止吗？这将停止所有策略！')) {
                        try {
                            const result = await fetch('/api/v1/trading/emergency_stop', {method: 'POST'});
                            showNotification('紧急停止执行完成', 'warning');
                            loadStrategyStatus(); // 重新加载策略状态
                        } catch (error) {
                            showNotification('紧急停止失败: ' + error.message, 'error');
                        }
                    }
                }

                // 显示通知
                function showNotification(message, type = 'info') {
                    console.log(`[${type.toUpperCase()}] ${message}`);
                    // 这里可以添加更复杂的通知UI
                }

                // 页面加载完成后执行
                document.addEventListener('DOMContentLoaded', function() {
                    console.log('🚀 策略管理页面加载完成');
                    loadStrategyStatus();
                });
            </script>
        </body>
        </html>
        """

@app.get("/trading_logs", response_class=HTMLResponse, summary="交易日志页面")
async def trading_logs_page(request: Request):
    """交易日志页面"""
    # 检查模板文件是否存在
    template_file = templates_dir / "trading_logs.html" if templates_dir.exists() else None
    if templates and template_file and template_file.exists():
        return templates.TemplateResponse("trading_logs.html", {"request": request})
    else:
        # 返回简单的交易日志页面
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ARBIG交易日志</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/static/css/dashboard.css?v=2.1">
        </head>
        <body>
            <nav class="navbar">
                <div class="container">
                    <h1>ARBIG交易日志</h1>
                    <ul class="nav-links">
                        <li><a href="/">总控台</a></li>
                        <li><a href="/strategy">策略中心</a></li>
                        <li><a href="/trading_logs" class="active">交易日志</a></li>
                    </ul>
                </div>
            </nav>
            <div class="container">
                <h2>交易日志功能开发中...</h2>
                <p>交易日志系统正在开发中，敬请期待！</p>
                <p>日志API: <a href="http://localhost:8001/trading_logs" target="_blank">http://localhost:8001/trading_logs</a></p>
            </div>
        </body>
        </html>
        """

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG Web管理服务')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8000,
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
