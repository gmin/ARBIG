"""
ARBIG Web管理系统 - 独立启动版本
可以独立启动，然后通过Web界面管理各个服务的启动和停止
"""

import asyncio
import json
import sys
import os
import subprocess
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from utils.logger import get_logger

logger = get_logger(__name__)

class ServiceStatus(BaseModel):
    name: str
    status: str  # "stopped", "starting", "running", "error"
    pid: Optional[int] = None
    start_time: Optional[str] = None
    error_message: Optional[str] = None

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.services = {}
        self.processes = {}
        self.project_root = Path(__file__).parent.parent
        
        # 定义可管理的服务
        self.service_configs = {
            "ctp_gateway": {
                "name": "CTP网关",
                "command": [sys.executable, "test_ctp_connection.py"],
                "cwd": str(self.project_root),
                "description": "CTP交易网关连接测试"
            },
            "market_data": {
                "name": "行情服务",
                "command": [sys.executable, "-c", "from core.services.market_data_service import MarketDataService; print('行情服务模拟启动')"],
                "cwd": str(self.project_root),
                "description": "市场行情数据服务"
            },
            "trading": {
                "name": "交易服务",
                "command": [sys.executable, "-c", "from core.services.trading_service import TradingService; print('交易服务模拟启动')"],
                "cwd": str(self.project_root),
                "description": "交易执行服务"
            },
            "risk": {
                "name": "风控服务",
                "command": [sys.executable, "-c", "from core.services.risk_service import RiskService; print('风控服务模拟启动')"],
                "cwd": str(self.project_root),
                "description": "风险控制服务"
            },
            "main_system": {
                "name": "主系统",
                "command": [sys.executable, "main.py", "--auto-start"],
                "cwd": str(self.project_root),
                "description": "ARBIG主系统（包含所有服务）"
            }
        }
        
        # 初始化服务状态
        for service_id, config in self.service_configs.items():
            self.services[service_id] = ServiceStatus(
                name=config["name"],
                status="stopped"
            )
    
    def start_service(self, service_id: str) -> Dict[str, Any]:
        """启动服务"""
        if service_id not in self.service_configs:
            return {"success": False, "message": f"未知服务: {service_id}"}
        
        if self.services[service_id].status == "running":
            return {"success": False, "message": f"服务 {service_id} 已在运行"}
        
        try:
            config = self.service_configs[service_id]
            self.services[service_id].status = "starting"
            
            # 启动进程
            process = subprocess.Popen(
                config["command"],
                cwd=config["cwd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[service_id] = process
            self.services[service_id].pid = process.pid
            self.services[service_id].start_time = datetime.now().isoformat()
            self.services[service_id].status = "running"
            self.services[service_id].error_message = None
            
            logger.info(f"服务 {service_id} 启动成功，PID: {process.pid}")
            
            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_process,
                args=(service_id, process),
                daemon=True
            )
            monitor_thread.start()
            
            return {
                "success": True,
                "message": f"服务 {config['name']} 启动成功",
                "pid": process.pid
            }
            
        except Exception as e:
            self.services[service_id].status = "error"
            self.services[service_id].error_message = str(e)
            logger.error(f"启动服务 {service_id} 失败: {e}")
            return {"success": False, "message": f"启动失败: {str(e)}"}
    
    def stop_service(self, service_id: str) -> Dict[str, Any]:
        """停止服务"""
        if service_id not in self.service_configs:
            return {"success": False, "message": f"未知服务: {service_id}"}
        
        if self.services[service_id].status != "running":
            return {"success": False, "message": f"服务 {service_id} 未在运行"}
        
        try:
            process = self.processes.get(service_id)
            if process:
                # 尝试优雅关闭
                process.terminate()
                
                # 等待进程结束
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    process.kill()
                    process.wait()
                
                del self.processes[service_id]
            
            self.services[service_id].status = "stopped"
            self.services[service_id].pid = None
            self.services[service_id].start_time = None
            self.services[service_id].error_message = None
            
            config = self.service_configs[service_id]
            logger.info(f"服务 {service_id} 停止成功")
            
            return {
                "success": True,
                "message": f"服务 {config['name']} 停止成功"
            }
            
        except Exception as e:
            logger.error(f"停止服务 {service_id} 失败: {e}")
            return {"success": False, "message": f"停止失败: {str(e)}"}
    
    def restart_service(self, service_id: str) -> Dict[str, Any]:
        """重启服务"""
        stop_result = self.stop_service(service_id)
        if not stop_result["success"]:
            return stop_result
        
        # 等待一秒确保进程完全停止
        time.sleep(1)
        
        return self.start_service(service_id)
    
    def get_service_status(self, service_id: str = None) -> Dict[str, Any]:
        """获取服务状态"""
        if service_id:
            if service_id not in self.services:
                return {"success": False, "message": f"未知服务: {service_id}"}
            return {
                "success": True,
                "data": self.services[service_id].dict()
            }
        else:
            return {
                "success": True,
                "data": {
                    service_id: status.dict()
                    for service_id, status in self.services.items()
                }
            }
    
    def get_service_logs(self, service_id: str, lines: int = 50) -> Dict[str, Any]:
        """获取服务日志"""
        if service_id not in self.processes:
            return {"success": False, "message": f"服务 {service_id} 未在运行"}
        
        try:
            process = self.processes[service_id]
            # 这里简化处理，实际应该读取日志文件
            return {
                "success": True,
                "data": {
                    "service_id": service_id,
                    "logs": f"服务 {service_id} 运行中...\nPID: {process.pid}",
                    "lines": lines
                }
            }
        except Exception as e:
            return {"success": False, "message": f"获取日志失败: {str(e)}"}
    
    def _monitor_process(self, service_id: str, process: subprocess.Popen):
        """监控进程状态"""
        try:
            return_code = process.wait()
            
            # 进程结束了
            if service_id in self.processes:
                del self.processes[service_id]
            
            if return_code == 0:
                self.services[service_id].status = "stopped"
                logger.info(f"服务 {service_id} 正常结束")
            else:
                self.services[service_id].status = "error"
                self.services[service_id].error_message = f"进程异常退出，返回码: {return_code}"
                logger.error(f"服务 {service_id} 异常结束，返回码: {return_code}")
                
        except Exception as e:
            self.services[service_id].status = "error"
            self.services[service_id].error_message = str(e)
            logger.error(f"监控服务 {service_id} 时发生错误: {e}")
    
    def cleanup(self):
        """清理所有进程"""
        for service_id in list(self.processes.keys()):
            self.stop_service(service_id)


class StandaloneWebApp:
    """独立的Web管理应用"""
    
    def __init__(self):
        self.app = FastAPI(
            title="ARBIG服务管理系统",
            version="1.0.0",
            description="ARBIG量化交易系统服务管理界面"
        )
        
        # 设置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.service_manager = ServiceManager()
        self.setup_routes()
        self.setup_static_files()
        
        # 注册清理函数
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("收到退出信号，正在清理...")
        self.service_manager.cleanup()
        sys.exit(0)
    
    def setup_static_files(self):
        """设置静态文件"""
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
            # 新增：挂载/assets路由，解决前端资源404
            assets_dir = static_dir / "assets"
            if assets_dir.exists():
                self.app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """主页面 - 保留原来的首页"""
            try:
                static_dir = Path(__file__).parent / "static"
                index_file = static_dir / "index.html"
                logger.info(f"尝试读取首页文件: {index_file}")
                logger.info(f"文件是否存在: {index_file.exists()}")

                if index_file.exists():
                    with open(index_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        logger.info(f"成功读取首页文件，长度: {len(content)}")
                        return HTMLResponse(content)
                else:
                    logger.warning(f"首页文件不存在: {index_file}")
                    # 如果没有原来的index.html，返回导航页面
                    return HTMLResponse("""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>ARBIG量化交易系统</title>
                        <meta charset="utf-8">
                        <style>
                            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                            h1 { color: #333; text-align: center; margin-bottom: 30px; }
                            .nav-card { border: 1px solid #ddd; margin: 15px 0; padding: 20px; border-radius: 8px; background: #fafafa; }
                            .nav-card h3 { margin-top: 0; color: #2196F3; }
                            .nav-card p { color: #666; margin: 10px 0; }
                            .nav-link { display: inline-block; padding: 10px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin-top: 10px; }
                            .nav-link:hover { background: #1976D2; }
                            .status { text-align: center; margin: 20px 0; padding: 15px; background: #e8f5e8; border-radius: 5px; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>🚀 ARBIG量化交易系统</h1>

                            <div class="status">
                                <strong>系统状态:</strong> Web管理界面运行中
                            </div>

                            <div class="nav-card">
                                <h3>📊 交易监控</h3>
                                <p>实时监控交易状态、持仓信息、订单执行情况</p>
                                <a href="/static/index.html" class="nav-link">进入交易监控</a>
                            </div>

                            <div class="nav-card">
                                <h3>⚙️ 服务管理</h3>
                                <p>管理系统各个服务的启动、停止、重启操作</p>
                                <a href="/services" class="nav-link">进入服务管理</a>
                            </div>

                            <div class="nav-card">
                                <h3>📈 策略管理</h3>
                                <p>管理量化交易策略，查看策略运行状态和收益</p>
                                <a href="/static/strategy_monitor.html" class="nav-link">进入策略管理</a>
                            </div>

                            <div class="nav-card">
                                <h3>🛡️ 风控管理</h3>
                                <p>风险控制设置，紧急停止交易，仓位管理</p>
                                <a href="/static/emergency_debug.html" class="nav-link">进入风控管理</a>
                            </div>

                            <div class="nav-card">
                                <h3>📋 API文档</h3>
                                <p>查看系统API接口文档和测试接口</p>
                                <a href="/docs" class="nav-link">查看API文档</a>
                            </div>
                        </div>
                    </body>
                    </html>
                    """)
            except Exception as e:
                logger.error(f"读取首页文件失败: {e}")
                return HTMLResponse(f"<h1>ARBIG系统</h1><p>读取首页文件失败: {e}</p><p>请检查 web_admin/static/index.html 文件</p>")

        @self.app.get("/services", response_class=HTMLResponse)
        async def services_management():
            """服务管理页面"""
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>ARBIG服务管理系统</title>
                <meta charset="utf-8">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .header h1 { margin: 0; color: #333; }
                    .header .nav { margin-top: 10px; }
                    .header .nav a { color: #2196F3; text-decoration: none; margin-right: 20px; }
                    .header .nav a:hover { text-decoration: underline; }

                    .controls { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    .controls button { margin: 5px; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
                    .refresh-btn { background-color: #2196F3; color: white; }
                    .refresh-btn:hover { background-color: #1976D2; }

                    .service {
                        background: white;
                        border: 1px solid #ddd;
                        margin: 15px 0;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        transition: all 0.3s ease;
                    }
                    .service:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.15); }

                    .running { border-left: 4px solid #4CAF50; }
                    .stopped { border-left: 4px solid #f44336; }
                    .starting { border-left: 4px solid #ff9800; }
                    .error { border-left: 4px solid #f44336; background-color: #ffebee; }

                    .service-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                    .service-title { margin: 0; color: #333; }
                    .service-status {
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: bold;
                        text-transform: uppercase;
                    }
                    .status-running { background: #e8f5e8; color: #2e7d32; }
                    .status-stopped { background: #ffebee; color: #c62828; }
                    .status-starting { background: #fff3e0; color: #ef6c00; }
                    .status-error { background: #ffebee; color: #c62828; }

                    .service-info { margin-bottom: 15px; }
                    .service-info p { margin: 5px 0; color: #666; font-size: 14px; }

                    .service-actions button {
                        margin: 5px 5px 5px 0;
                        padding: 8px 16px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 14px;
                        transition: background-color 0.3s ease;
                    }
                    .start-btn { background-color: #4CAF50; color: white; }
                    .start-btn:hover { background-color: #45a049; }
                    .start-btn:disabled { background-color: #cccccc; cursor: not-allowed; }

                    .stop-btn { background-color: #f44336; color: white; }
                    .stop-btn:hover { background-color: #da190b; }
                    .stop-btn:disabled { background-color: #cccccc; cursor: not-allowed; }

                    .restart-btn { background-color: #ff9800; color: white; }
                    .restart-btn:hover { background-color: #e68900; }

                    .loading { text-align: center; padding: 40px; color: #666; }
                    .error-message { color: #f44336; font-size: 14px; margin-top: 5px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔧 ARBIG服务管理系统</h1>
                        <div class="nav">
                            <a href="/">← 返回首页</a>
                            <a href="/static/index.html">交易监控</a>
                            <a href="/docs">API文档</a>
                        </div>
                    </div>

                    <div class="controls">
                        <button class="refresh-btn" onclick="refreshStatus()">🔄 刷新状态</button>
                        <span id="last-update" style="margin-left: 20px; color: #666; font-size: 14px;"></span>
                    </div>

                    <div id="services" class="loading">正在加载服务状态...</div>
                </div>

                <script>
                    let lastUpdateTime = null;

                    async function refreshStatus() {
                        try {
                            const response = await fetch('/api/services/status');
                            const result = await response.json();
                            if (result.success) {
                                displayServices(result.data);
                                lastUpdateTime = new Date();
                                updateLastUpdateTime();
                            } else {
                                document.getElementById('services').innerHTML = '<div class="error-message">获取服务状态失败</div>';
                            }
                        } catch (error) {
                            console.error('获取服务状态失败:', error);
                            document.getElementById('services').innerHTML = '<div class="error-message">网络错误，无法获取服务状态</div>';
                        }
                    }

                    function updateLastUpdateTime() {
                        if (lastUpdateTime) {
                            const timeStr = lastUpdateTime.toLocaleTimeString();
                            document.getElementById('last-update').textContent = `最后更新: ${timeStr}`;
                        }
                    }

                    function displayServices(services) {
                        const container = document.getElementById('services');
                        container.innerHTML = '';

                        for (const [serviceId, status] of Object.entries(services)) {
                            const div = document.createElement('div');
                            div.className = `service ${status.status}`;

                            const statusClass = `status-${status.status}`;
                            const statusText = {
                                'running': '运行中',
                                'stopped': '已停止',
                                'starting': '启动中',
                                'error': '错误'
                            }[status.status] || status.status;

                            div.innerHTML = `
                                <div class="service-header">
                                    <h3 class="service-title">${status.name} (${serviceId})</h3>
                                    <span class="service-status ${statusClass}">${statusText}</span>
                                </div>
                                <div class="service-info">
                                    ${status.pid ? `<p><strong>进程ID:</strong> ${status.pid}</p>` : ''}
                                    ${status.start_time ? `<p><strong>启动时间:</strong> ${new Date(status.start_time).toLocaleString()}</p>` : ''}
                                    ${status.error_message ? `<p class="error-message"><strong>错误信息:</strong> ${status.error_message}</p>` : ''}
                                </div>
                                <div class="service-actions">
                                    <button class="start-btn" onclick="startService('${serviceId}')" ${status.status === 'running' || status.status === 'starting' ? 'disabled' : ''}>
                                        ▶️ 启动
                                    </button>
                                    <button class="stop-btn" onclick="stopService('${serviceId}')" ${status.status !== 'running' ? 'disabled' : ''}>
                                        ⏹️ 停止
                                    </button>
                                    <button class="restart-btn" onclick="restartService('${serviceId}')">
                                        🔄 重启
                                    </button>
                                </div>
                            `;
                            container.appendChild(div);
                        }
                    }

                    async function startService(serviceId) {
                        try {
                            const response = await fetch(`/api/services/${serviceId}/start`, { method: 'POST' });
                            const result = await response.json();
                            if (result.success) {
                                showMessage(result.message, 'success');
                            } else {
                                showMessage(result.message, 'error');
                            }
                            refreshStatus();
                        } catch (error) {
                            showMessage('启动服务失败: ' + error.message, 'error');
                        }
                    }

                    async function stopService(serviceId) {
                        if (!confirm('确定要停止这个服务吗？')) return;

                        try {
                            const response = await fetch(`/api/services/${serviceId}/stop`, { method: 'POST' });
                            const result = await response.json();
                            if (result.success) {
                                showMessage(result.message, 'success');
                            } else {
                                showMessage(result.message, 'error');
                            }
                            refreshStatus();
                        } catch (error) {
                            showMessage('停止服务失败: ' + error.message, 'error');
                        }
                    }

                    async function restartService(serviceId) {
                        if (!confirm('确定要重启这个服务吗？')) return;

                        try {
                            const response = await fetch(`/api/services/${serviceId}/restart`, { method: 'POST' });
                            const result = await response.json();
                            if (result.success) {
                                showMessage(result.message, 'success');
                            } else {
                                showMessage(result.message, 'error');
                            }
                            refreshStatus();
                        } catch (error) {
                            showMessage('重启服务失败: ' + error.message, 'error');
                        }
                    }

                    function showMessage(message, type) {
                        // 简单的消息提示
                        const alertType = type === 'success' ? '✅' : '❌';
                        alert(`${alertType} ${message}`);
                    }

                    // 页面加载时刷新状态
                    refreshStatus();

                    // 每10秒自动刷新状态
                    setInterval(refreshStatus, 10000);

                    // 每秒更新最后更新时间显示
                    setInterval(updateLastUpdateTime, 1000);
                </script>
            </body>
            </html>
            """)
        
        @self.app.get("/api/services/status")
        async def get_services_status():
            """获取所有服务状态"""
            return self.service_manager.get_service_status()
        
        @self.app.get("/api/services/{service_id}/status")
        async def get_service_status(service_id: str):
            """获取单个服务状态"""
            return self.service_manager.get_service_status(service_id)
        
        @self.app.post("/api/services/{service_id}/start")
        async def start_service(service_id: str):
            """启动服务"""
            return self.service_manager.start_service(service_id)
        
        @self.app.post("/api/services/{service_id}/stop")
        async def stop_service(service_id: str):
            """停止服务"""
            return self.service_manager.stop_service(service_id)
        
        @self.app.post("/api/services/{service_id}/restart")
        async def restart_service(service_id: str):
            """重启服务"""
            return self.service_manager.restart_service(service_id)
        
        @self.app.get("/api/services/{service_id}/logs")
        async def get_service_logs(service_id: str, lines: int = 50):
            """获取服务日志"""
            return self.service_manager.get_service_logs(service_id, lines)

        # 数据查询API路由
        @self.app.get("/api/v1/data/orders")
        async def get_orders(active_only: bool = False):
            """获取订单列表"""
            try:
                # 模拟订单数据
                orders = [
                    {
                        "order_id": "ORD001",
                        "symbol": "au2507",
                        "direction": "LONG",
                        "order_type": "limit",
                        "volume": 1,
                        "price": 485.50,
                        "status": "active",
                        "create_time": "2024-01-15 10:30:00"
                    }
                ]
                
                if active_only:
                    orders = [o for o in orders if o["status"] == "active"]
                
                return {"success": True, "data": {"orders": orders}}
            except Exception as e:
                logger.error(f"获取订单列表失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/data/account/info")
        async def get_account_info():
            """获取账户信息"""
            try:
                # 模拟账户数据
                account_info = {
                    "account_id": "123456",
                    "balance": 1000000.00,
                    "available": 950000.00,
                    "frozen": 50000.00,
                    "margin": 25000.00,
                    "risk_ratio": 0.25
                }
                return {"success": True, "data": account_info}
            except Exception as e:
                logger.error(f"获取账户信息失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/data/account/positions")
        async def get_positions():
            """获取持仓信息"""
            try:
                # 模拟持仓数据
                positions = [
                    {
                        "symbol": "au2507",
                        "direction": "LONG",
                        "volume": 1,
                        "open_price": 485.50,
                        "current_price": 486.20,
                        "pnl": 700,
                        "margin": 25000
                    }
                ]
                return {"success": True, "data": {"positions": positions}}
            except Exception as e:
                logger.error(f"获取持仓信息失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/data/risk/metrics")
        async def get_risk_metrics():
            """获取风险指标"""
            try:
                # 模拟风险数据
                risk_metrics = {
                    "total_pnl": 1800,
                    "today_pnl": 500,
                    "max_drawdown": -2000,
                    "sharpe_ratio": 1.2,
                    "position_count": 2,
                    "risk_level": "LOW"
                }
                return {"success": True, "data": risk_metrics}
            except Exception as e:
                logger.error(f"获取风险指标失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/strategies/list")
        async def get_strategies():
            """获取策略列表"""
            try:
                # 模拟策略数据
                strategies = [
                    {
                        "id": "1",
                        "name": "黄金套利策略",
                        "type": "arbitrage",
                        "status": "running",
                        "symbols": ["au2507", "au2508"],
                        "total_return": 15.6,
                        "create_time": "2024-01-15 10:30:00"
                    }
                ]
                return {"success": True, "data": {"strategies": strategies}}
            except Exception as e:
                logger.error(f"获取策略列表失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/trading/summary")
        async def get_trading_summary():
            """获取交易汇总"""
            try:
                # 模拟交易汇总数据
                summary = {
                    "today_trades": 5,
                    "today_volume": 10,
                    "today_turnover": 4855000,
                    "total_trades": 150,
                    "total_volume": 300,
                    "total_turnover": 145650000
                }
                return {"success": True, "data": summary}
            except Exception as e:
                logger.error(f"获取交易汇总失败: {e}")
                return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/data/market/ticks")
        async def get_market_ticks(symbols: str = "au2507"):
            """获取市场行情数据"""
            try:
                import random
                import time
                
                # 模拟黄金主力合约行情数据
                base_price = 485.50
                # 添加一些随机波动，模拟真实行情
                price_change = random.uniform(-2.0, 2.0)
                current_price = base_price + price_change
                
                # 计算涨跌幅
                change_percent = (price_change / base_price) * 100
                
                # 模拟买卖盘数据
                bid_price = current_price - random.uniform(0.1, 0.5)
                ask_price = current_price + random.uniform(0.1, 0.5)
                
                ticks = []
                for symbol in symbols.split(','):
                    tick = {
                        "symbol": symbol.strip(),
                        "last_price": round(current_price, 2),
                        "bid_price": round(bid_price, 2),
                        "ask_price": round(ask_price, 2),
                        "bid_volume": random.randint(1, 10),
                        "ask_volume": random.randint(1, 10),
                        "volume": random.randint(100, 1000),
                        "open_interest": random.randint(5000, 15000),
                        "change": round(price_change, 2),
                        "change_percent": round(change_percent, 2),
                        "high": round(current_price + random.uniform(1, 3), 2),
                        "low": round(current_price - random.uniform(1, 3), 2),
                        "open": round(base_price, 2),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "update_time": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    ticks.append(tick)
                
                return {"success": True, "data": {"ticks": ticks}}
            except Exception as e:
                logger.error(f"获取市场行情失败: {e}")
                return {"success": False, "message": str(e)}

        # 导入通信管理器
        try:
            from web_admin.core.communication_manager import get_communication_manager
        except ImportError:
            # 如果导入失败，使用简单的代理方式
            logger.warning("通信管理器导入失败，使用简单代理模式")
            get_communication_manager = None
        
        # 代理到主系统API的路由
        @self.app.get("/api/v1/system/status")
        async def proxy_system_status():
            """代理系统状态API"""
            try:
                if get_communication_manager:
                    comm_manager = get_communication_manager()
                    result = await comm_manager.get_system_status()
                    return result
                else:
                    # 回退到原来的方式
                    import httpx
                    async with httpx.AsyncClient() as client:
                        for port in [8001, 8002, 8003]:
                            try:
                                response = await client.get(f"http://localhost:{port}/api/v1/system/status", timeout=5.0)
                                if response.status_code == 200:
                                    return response.json()
                            except:
                                continue
                        return {"success": False, "message": "主系统API不可用"}
            except Exception as e:
                logger.error(f"代理系统状态API失败: {e}")
                return {"success": False, "message": f"连接主系统失败: {str(e)}"}

        @self.app.post("/api/v1/data/orders/send")
        async def proxy_send_order(request: dict):
            """代理发送订单API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.send_order(request)
                return result
            except Exception as e:
                logger.error(f"代理发送订单API失败: {e}")
                return {"success": False, "message": f"发送订单失败: {str(e)}"}

        # 更多代理API
        @self.app.get("/api/v1/data/orders")
        async def proxy_get_orders(active_only: bool = False):
            """代理获取订单列表API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_orders(active_only)
                return result
            except Exception as e:
                logger.error(f"代理获取订单列表API失败: {e}")
                return {"success": False, "message": f"获取订单列表失败: {str(e)}", "data": {"orders": []}}

        @self.app.get("/api/v1/data/account/info")
        async def proxy_get_account_info():
            """代理获取账户信息API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_account_info()
                return result
            except Exception as e:
                logger.error(f"代理获取账户信息API失败: {e}")
                return {"success": False, "message": f"获取账户信息失败: {str(e)}", "data": {}}

        @self.app.get("/api/v1/data/account/positions")
        async def proxy_get_positions():
            """代理获取持仓信息API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_positions()
                return result
            except Exception as e:
                logger.error(f"代理获取持仓信息API失败: {e}")
                return {"success": False, "message": f"获取持仓信息失败: {str(e)}", "data": {"positions": []}}

        @self.app.get("/api/v1/data/risk/metrics")
        async def proxy_get_risk_metrics():
            """代理获取风险指标API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_risk_metrics()
                return result
            except Exception as e:
                logger.error(f"代理获取风险指标API失败: {e}")
                return {"success": False, "message": f"获取风险指标失败: {str(e)}", "data": {}}

        @self.app.get("/api/v1/strategies/list")
        async def proxy_get_strategies():
            """代理获取策略列表API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_strategies_list()
                return result
            except Exception as e:
                logger.error(f"代理获取策略列表API失败: {e}")
                return {"success": False, "message": f"获取策略列表失败: {str(e)}", "data": {"strategies": []}}

        @self.app.get("/api/v1/data/market/ticks")
        async def proxy_get_market_ticks(symbols: str = "au2507"):
            """代理获取市场行情API"""
            try:
                comm_manager = get_communication_manager()
                result = await comm_manager.get_market_ticks(symbols)
                return result
            except Exception as e:
                logger.error(f"代理获取市场行情API失败: {e}")
                # 如果主系统不可用，返回模拟数据
                return await get_market_ticks(symbols)

        @self.app.get("/api/communication/stats")
        async def get_communication_stats():
            """获取通信统计信息"""
            try:
                if get_communication_manager:
                    comm_manager = get_communication_manager()
                    stats = comm_manager.get_connection_stats()
                    return {"success": True, "data": stats}
                else:
                    # 返回默认统计信息
                    return {
                        "success": True, 
                        "data": {
                            "connection_status": "disconnected",
                            "total_requests": 0,
                            "successful_requests": 0,
                            "failed_requests": 0,
                            "current_endpoint": None,
                            "total_endpoints": 0
                        }
                    }
            except Exception as e:
                logger.error(f"获取通信统计信息失败: {e}")
                return {"success": False, "message": f"获取通信统计信息失败: {str(e)}"}


def run_standalone_web_service(host: str = "0.0.0.0", port: int = 8000):
    """运行独立的Web服务管理系统"""
    logger.info(f"启动ARBIG服务管理系统: http://{host}:{port}")
    
    app_instance = StandaloneWebApp()
    
    try:
        uvicorn.run(app_instance.app, host=host, port=port)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        app_instance.service_manager.cleanup()


if __name__ == "__main__":
    run_standalone_web_service()
