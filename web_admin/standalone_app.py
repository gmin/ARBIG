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
import uuid
import re
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from utils.logger import get_logger

logger = get_logger(__name__)

class LogEntry(BaseModel):
    """日志条目"""
    timestamp: str
    level: str
    module: str
    message: str
    line_number: int

class LogManager:
    """日志管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.log_dirs = [
            self.project_root / "logs",
            self.project_root / "web_admin" / "logs"
        ]

        # 日志级别映射
        self.log_levels = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }

    def get_log_files(self) -> Dict[str, List[str]]:
        """获取所有日志文件"""
        log_files = {}

        for log_dir in self.log_dirs:
            if log_dir.exists():
                dir_name = log_dir.name if log_dir.name != "logs" else "main"
                log_files[dir_name] = []

                # 查找所有.log文件
                for log_file in log_dir.glob("*.log"):
                    log_files[dir_name].append(log_file.name)

                # 按日期排序（最新的在前）
                log_files[dir_name].sort(reverse=True)

        return log_files

    def parse_log_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        """解析日志行"""
        # 日志格式: 2025-08-03 17:08:56,968 - module_name - LEVEL - message
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)$'
        match = re.match(pattern, line.strip())

        if match:
            timestamp, module, level, message = match.groups()
            return LogEntry(
                timestamp=timestamp,
                level=level.strip(),
                module=module.strip(),
                message=message.strip(),
                line_number=line_number
            )
        return None

    def get_logs(self, service: str = "main", filename: str = None,
                 lines: int = 100, level: str = None,
                 search: str = None, start_time: str = None,
                 end_time: str = None) -> Dict[str, Any]:
        """获取日志内容"""
        try:
            # 确定日志目录
            if service == "main":
                log_dir = self.project_root / "logs"
            else:
                log_dir = self.project_root / "web_admin" / "logs"

            if not log_dir.exists():
                return {"success": False, "message": f"日志目录不存在: {log_dir}"}

            # 确定日志文件
            if filename:
                log_file = log_dir / filename
            else:
                # 获取最新的日志文件
                log_files = list(log_dir.glob("*.log"))
                if not log_files:
                    return {"success": False, "message": "没有找到日志文件"}
                log_file = max(log_files, key=lambda f: f.stat().st_mtime)

            if not log_file.exists():
                return {"success": False, "message": f"日志文件不存在: {log_file}"}

            # 读取日志文件
            log_entries = []
            total_lines = 0

            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                total_lines = len(all_lines)

                # 从后往前读取指定行数
                start_idx = max(0, total_lines - lines)
                selected_lines = all_lines[start_idx:]

                for i, line in enumerate(selected_lines, start=start_idx + 1):
                    entry = self.parse_log_line(line, i)
                    if entry:
                        # 应用过滤条件
                        if level and entry.level != level:
                            continue

                        if search and search.lower() not in entry.message.lower():
                            continue

                        # 时间过滤（简化版本）
                        if start_time or end_time:
                            # 这里可以添加更复杂的时间过滤逻辑
                            pass

                        log_entries.append(entry.dict())

            return {
                "success": True,
                "data": {
                    "logs": log_entries,
                    "total_lines": total_lines,
                    "file_path": str(log_file),
                    "file_size": log_file.stat().st_size,
                    "last_modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
            }

        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            return {"success": False, "message": f"获取日志失败: {str(e)}"}

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
        self.log_manager = LogManager()
        
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
        try:
            if service_id:
                if service_id not in self.services:
                    return {"success": False, "message": f"未知服务: {service_id}"}

                # 手动构造状态字典，避免调用.dict()方法
                service_status = self.services[service_id]
                return {
                    "success": True,
                    "data": {
                        "name": service_status.name,
                        "status": service_status.status,
                        "pid": service_status.pid,
                        "start_time": service_status.start_time,
                        "error_message": service_status.error_message
                    }
                }
            else:
                # 手动构造所有服务状态字典
                services_data = {}
                for service_id, status in self.services.items():
                    services_data[service_id] = {
                        "name": status.name,
                        "status": status.status,
                        "pid": status.pid,
                        "start_time": status.start_time,
                        "error_message": status.error_message
                    }

                return {
                    "success": True,
                    "data": services_data
                }
        except Exception as e:
            logger.error(f"获取服务状态时发生错误: {e}")
            return {
                "success": False,
                "message": f"获取服务状态失败: {str(e)}"
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
            description="ARBIG量化交易系统服务管理界面",
            docs_url="/api/docs",
            redoc_url="/api/redoc"
        )
        
        # 设置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 注册简化的API路由
        self.setup_api_routes()

        self.service_manager = ServiceManager()
        self.setup_routes()
        self.setup_static_files()
        
        # 注册清理函数（仅在主线程中有效）
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError as e:
            # 在非主线程中运行时会出现此错误，可以忽略
            logger.warning(f"无法注册信号处理器（可能不在主线程中）: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("收到退出信号，正在清理...")
        self.service_manager.cleanup()
        sys.exit(0)
    
    def setup_api_routes(self):
        """设置API路由 - 本地API + 代理到主系统API"""
        import requests
        from fastapi import Request, HTTPException
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
        import yaml

        # 本地API - 保存主力合约
        class SubscribeRequest(BaseModel):
            symbol: str
            subscriber_id: str = "web_admin"
            save_to_config: bool = False

        @self.app.get("/api/v1/system/config", summary="获取系统配置")
        async def get_system_config():
            """获取系统配置信息"""
            try:
                # 配置文件路径
                config_path = Path("config.yaml")

                if not config_path.exists():
                    return {"success": False, "message": "配置文件不存在", "data": None}

                # 读取配置文件
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                # 提取关键配置信息
                result = {
                    "main_contract": config.get('market_data', {}).get('main_contract'),
                    "trading_mode": config.get('trading', {}).get('mode'),
                    "risk_settings": config.get('risk', {}),
                    "ctp_settings": config.get('ctp', {})
                }

                return {
                    "success": True,
                    "message": "获取系统配置成功",
                    "data": result
                }

            except Exception as e:
                logger.error(f"获取系统配置失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"获取配置失败: {str(e)}",
                    "data": None
                }

        @self.app.get("/api/v1/system/config/market_data", summary="获取行情数据配置")
        async def get_market_data_config():
            """获取行情数据配置信息"""
            try:
                # 配置文件路径
                config_path = Path("config.yaml")

                if not config_path.exists():
                    return {"success": False, "message": "配置文件不存在", "data": None}

                # 读取配置文件
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                # 提取行情数据配置
                market_data_config = config.get('market_data', {})
                result = {
                    "main_contract": market_data_config.get('main_contract'),
                    "auto_subscribe": market_data_config.get('auto_subscribe', True),
                    "cache_size": market_data_config.get('cache_size', 1000),
                    "redis": market_data_config.get('redis', {})
                }

                return {
                    "success": True,
                    "message": "获取行情数据配置成功",
                    "data": result
                }

            except Exception as e:
                logger.error(f"获取行情数据配置失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"获取配置失败: {str(e)}",
                    "data": None
                }

        class SaveMainContractRequest(BaseModel):
            main_contract: str

        @self.app.post("/api/v1/system/config/market_data/save_main_contract", summary="保存主力合约")
        async def save_main_contract_market_data(request: SaveMainContractRequest):
            """保存主力合约配置"""
            try:
                # 配置文件路径
                config_path = Path("config.yaml")

                if not config_path.exists():
                    return {"success": False, "message": "配置文件不存在", "data": None}

                # 读取配置文件
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                # 确保market_data配置存在
                if 'market_data' not in config:
                    config['market_data'] = {}

                # 设置主力合约
                config['market_data']['main_contract'] = request.main_contract

                # 保存配置文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

                logger.info(f"主力合约已设置为: {request.main_contract}")

                return {
                    "success": True,
                    "message": f"主力合约已设置为: {request.main_contract}",
                    "data": {"main_contract": request.main_contract}
                }

            except Exception as e:
                logger.error(f"保存主力合约配置失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"保存配置失败: {str(e)}",
                    "data": None
                }

        @self.app.post("/api/v1/data/market/subscribe", summary="保存主力合约")
        async def save_main_contract(request: SubscribeRequest):
            """保存主力合约到配置文件"""
            try:
                # 如果需要保存到配置文件，使用本地处理
                if request.save_to_config:
                    # 配置文件路径
                    config_path = Path("config.yaml")

                    if not config_path.exists():
                        return {"success": False, "message": "配置文件不存在", "data": None}

                    # 读取配置文件
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)

                    # 确保market_data配置存在
                    if 'market_data' not in config:
                        config['market_data'] = {}

                    # 设置主力合约
                    config['market_data']['main_contract'] = request.symbol

                    # 保存配置文件
                    with open(config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

                    logger.info(f"主力合约已设置为: {request.symbol}")

                    return {
                        "success": True,
                        "message": f"主力合约已设置为: {request.symbol}",
                        "data": {"symbol": request.symbol, "main_contract": True}
                    }
                else:
                    # 如果不需要保存配置，转发到主系统
                    try:
                        response = requests.post(
                            f"http://localhost:8000/api/v1/data/market/subscribe",
                            json=request.dict(),
                            timeout=10
                        )
                        return JSONResponse(
                            content=response.json() if response.content else {},
                            status_code=response.status_code
                        )
                    except requests.exceptions.ConnectionError:
                        return {"success": False, "message": "主系统未运行或无法连接", "data": None}

            except Exception as e:
                logger.error(f"保存主力合约配置失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"保存配置失败: {str(e)}",
                    "data": None
                }

        # API代理路由 - 将其他API请求转发到主系统
        @self.app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def api_proxy(path: str, request: Request):
            """API代理 - 转发请求到主系统"""
            try:
                # 主系统API地址
                main_system_url = f"http://localhost:8000/api/v1/{path}"

                # 获取请求数据
                method = request.method
                headers = dict(request.headers)
                # 移除可能导致问题的headers
                headers.pop('host', None)
                headers.pop('content-length', None)

                # 获取查询参数
                query_params = dict(request.query_params)

                # 获取请求体（如果有）
                body = None
                if method in ['POST', 'PUT', 'PATCH']:
                    try:
                        body = await request.body()
                        if body:
                            body = body.decode('utf-8')
                    except:
                        body = None

                # 发送请求到主系统
                response = requests.request(
                    method=method,
                    url=main_system_url,
                    headers={'Content-Type': 'application/json'},
                    params=query_params,
                    data=body,
                    timeout=10
                )

                # 返回响应
                return JSONResponse(
                    content=response.json() if response.content else {},
                    status_code=response.status_code
                )

            except requests.exceptions.ConnectionError:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "主系统未运行或无法连接",
                        "data": None
                    },
                    status_code=503
                )
            except Exception as e:
                logger.error(f"API代理错误: {str(e)}")
                return JSONResponse(
                    content={
                        "success": False,
                        "message": f"API代理错误: {str(e)}",
                        "data": None
                    },
                    status_code=500
                )

    def setup_static_files(self):
        """设置静态文件"""
        static_dir = Path(__file__).parent / "static"
        logger.info(f"静态文件目录: {static_dir}")
        logger.info(f"静态文件目录是否存在: {static_dir.exists()}")

        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
            logger.info("已挂载 /static 路由")
        else:
            logger.error(f"静态文件目录不存在: {static_dir}")
    
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
            # 优先从主系统获取真实状态
            try:
                import httpx
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get("http://localhost:8000/api/v1/system/status")
                    if response.status_code == 200:
                        main_system_data = response.json()
                        if main_system_data.get("success", False):
                            # 转换主系统状态为服务管理器格式
                            system_data = main_system_data.get("data", {})
                            ctp_status = system_data.get("ctp_status", {})

                            # 构造服务状态
                            services_status = {
                                "main_system": {
                                    "name": "主系统",
                                    "status": "running" if system_data.get("system_status") == "running" else "error",
                                    "pid": None,
                                    "start_time": system_data.get("start_time"),
                                    "error_message": None if system_data.get("system_status") == "running" else "主系统未运行"
                                },
                                "ctp_gateway": {
                                    "name": "CTP网关",
                                    "status": "running" if (ctp_status.get("market_data", {}).get("connected") and ctp_status.get("trading", {}).get("connected")) else "error",
                                    "pid": None,
                                    "start_time": system_data.get("start_time"),
                                    "error_message": None if (ctp_status.get("market_data", {}).get("connected") and ctp_status.get("trading", {}).get("connected")) else "CTP连接失败"
                                },
                                "market_data": {
                                    "name": "行情服务",
                                    "status": "running" if ctp_status.get("market_data", {}).get("connected") else "stopped",
                                    "pid": None,
                                    "start_time": system_data.get("start_time"),
                                    "error_message": None
                                },
                                "trading": {
                                    "name": "交易服务",
                                    "status": "running" if ctp_status.get("trading", {}).get("connected") else "stopped",
                                    "pid": None,
                                    "start_time": system_data.get("start_time"),
                                    "error_message": None
                                },
                                "risk": {
                                    "name": "风控服务",
                                    "status": "running" if system_data.get("system_status") == "running" else "stopped",
                                    "pid": None,
                                    "start_time": system_data.get("start_time"),
                                    "error_message": None
                                }
                            }

                            return {
                                "success": True,
                                "data": services_status
                            }
            except Exception as e:
                logger.warning(f"无法从主系统获取状态: {e}")

            # 回退到独立服务管理器状态
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
        async def get_market_ticks(symbols: str = "au2507", use_real_data: bool = False):
            """获取市场行情数据"""
            try:
                import random
                import time
                from datetime import datetime, time as dt_time
                
                # 检查交易时间
                now = datetime.now()
                current_time = now.time()
                
                # 期货交易时间（简化版）
                morning_start = dt_time(9, 0)   # 9:00
                morning_end = dt_time(11, 30)   # 11:30
                afternoon_start = dt_time(13, 30)  # 13:30
                afternoon_end = dt_time(15, 0)     # 15:00
                night_start = dt_time(21, 0)       # 21:00
                night_end = dt_time(2, 30)         # 次日2:30
                
                # 判断是否在交易时间内
                is_trading_time = (
                    (morning_start <= current_time <= morning_end) or
                    (afternoon_start <= current_time <= afternoon_end) or
                    (night_start <= current_time) or
                    (current_time <= night_end)
                )
                
                # 如果要求真实数据但不在交易时间，返回停盘提示
                if use_real_data and not is_trading_time:
                    return {
                        "success": False, 
                        "message": f"当前时间 {current_time.strftime('%H:%M:%S')} 不在交易时间内，无法获取实时数据",
                        "data": {
                            "trading_status": "closed",
                            "next_trading_time": "09:00",
                            "current_time": current_time.strftime('%H:%M:%S')
                        }
                    }
                
                # 合约基础价格配置
                contract_prices = {
                    "au2507": 485.50,  # 黄金2507合约
                    "au2508": 486.20,  # 黄金2508合约
                    "au2509": 487.10,  # 黄金2509合约
                    "ag2507": 5800.0,  # 白银2507合约
                    "ag2508": 5810.0,  # 白银2508合约
                    "cu2507": 72000.0, # 铜2507合约
                    "al2507": 19500.0, # 铝2507合约
                    "zn2507": 22000.0, # 锌2507合约
                    "pb2507": 16500.0, # 铅2507合约
                    "ni2507": 140000.0, # 镍2507合约
                    "sn2507": 280000.0, # 锡2507合约
                }
                
                ticks = []
                for symbol in symbols.split(','):
                    symbol = symbol.strip().lower()
                    
                    # 获取合约基础价格，如果没有配置则使用默认价格
                    base_price = contract_prices.get(symbol, 485.50)
                    
                    if use_real_data:
                        # 真实数据模式：尝试从外部数据源获取
                        try:
                            # 这里可以集成真实的数据源，比如：
                            # - CTP行情接口
                            # - 第三方数据API
                            # - 数据库中的历史数据
                            
                            # 模拟真实数据获取失败的情况
                            if random.random() < 0.1:  # 10%概率模拟数据获取失败
                                raise Exception("数据源连接超时")
                            
                            # 模拟真实数据的波动
                            price_change = random.uniform(-5.0, 5.0)
                            current_price = base_price + price_change
                            
                        except Exception as e:
                            logger.warning(f"获取真实数据失败，使用模拟数据: {e}")
                            # 回退到模拟数据
                            price_change = random.uniform(-2.0, 2.0)
                            current_price = base_price + price_change
                    else:
                        # 模拟数据模式
                        price_change = random.uniform(-2.0, 2.0)
                        current_price = base_price + price_change
                    
                    # 计算涨跌幅
                    change_percent = (price_change / base_price) * 100
                    
                    # 生成买卖盘数据
                    bid_price = current_price - random.uniform(0.1, 0.5)
                    ask_price = current_price + random.uniform(0.1, 0.5)
                    
                    tick = {
                        "symbol": symbol.upper(),
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
                        "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "data_source": "real" if use_real_data else "simulated",
                        "trading_status": "open" if is_trading_time else "closed"
                    }
                    ticks.append(tick)
                
                return {"success": True, "data": {"ticks": ticks}}
            except Exception as e:
                logger.error(f"获取市场行情失败: {e}")
                return {"success": False, "message": str(e)}

        # 已废弃：合约列表API，现在使用配置文件中的主力合约
        # @self.app.get("/api/v1/data/market/contracts")
        # async def get_available_contracts():
        #     """获取可用的合约列表"""
        #     try:
        #         contracts = [
        #             {"symbol": "AU2507", "name": "黄金2507", "exchange": "SHFE", "category": "贵金属"},
        #             {"symbol": "AU2508", "name": "黄金2508", "exchange": "SHFE", "category": "贵金属"},
        #             {"symbol": "AU2509", "name": "黄金2509", "exchange": "SHFE", "category": "贵金属"},
        #             {"symbol": "AG2507", "name": "白银2507", "exchange": "SHFE", "category": "贵金属"},
        #             {"symbol": "AG2508", "name": "白银2508", "exchange": "SHFE", "category": "贵金属"},
        #             {"symbol": "CU2507", "name": "铜2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "AL2507", "name": "铝2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "ZN2507", "name": "锌2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "PB2507", "name": "铅2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "NI2507", "name": "镍2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "SN2507", "name": "锡2507", "exchange": "SHFE", "category": "有色金属"},
        #             {"symbol": "RB2507", "name": "螺纹钢2507", "exchange": "SHFE", "category": "黑色金属"},
        #             {"symbol": "HC2507", "name": "热轧卷板2507", "exchange": "SHFE", "category": "黑色金属"},
        #             {"symbol": "I2507", "name": "铁矿石2507", "exchange": "DCE", "category": "黑色金属"},
        #             {"symbol": "J2507", "name": "焦炭2507", "exchange": "DCE", "category": "黑色金属"},
        #             {"symbol": "JM2507", "name": "焦煤2507", "exchange": "DCE", "category": "黑色金属"},
        #             {"symbol": "MA2507", "name": "甲醇2507", "exchange": "DCE", "category": "化工"},
        #             {"symbol": "PP2507", "name": "聚丙烯2507", "exchange": "DCE", "category": "化工"},
        #             {"symbol": "V2507", "name": "PVC2507", "exchange": "DCE", "category": "化工"},
        #             {"symbol": "TA2507", "name": "PTA2507", "exchange": "DCE", "category": "化工"},
        #             {"symbol": "EG2507", "name": "乙二醇2507", "exchange": "DCE", "category": "化工"},
        #             {"symbol": "SR2507", "name": "白糖2507", "exchange": "CZCE", "category": "农产品"},
        #             {"symbol": "CF2507", "name": "棉花2507", "exchange": "CZCE", "category": "农产品"},
        #             {"symbol": "MA2507", "name": "甲醇2507", "exchange": "CZCE", "category": "化工"},
        #             {"symbol": "TA2507", "name": "PTA2507", "exchange": "CZCE", "category": "化工"},
        #             {"symbol": "IF2507", "name": "沪深300指数2507", "exchange": "CFFEX", "category": "股指期货"},
        #             {"symbol": "IH2507", "name": "上证50指数2507", "exchange": "CFFEX", "category": "股指期货"},
        #             {"symbol": "IC2507", "name": "中证500指数2507", "exchange": "CFFEX", "category": "股指期货"},
        #         ]
        #
        #         return {"success": True, "data": {"contracts": contracts}}
        #     except Exception as e:
        #         logger.error(f"获取合约列表失败: {e}")
        #         return {"success": False, "message": str(e)}

        @self.app.get("/api/v1/data/market/trading_status")
        async def get_trading_status():
            """获取交易时间状态"""
            try:
                from datetime import datetime, time as dt_time
                
                now = datetime.now()
                current_time = now.time()
                
                # 期货交易时间
                morning_start = dt_time(9, 0)
                morning_end = dt_time(11, 30)
                afternoon_start = dt_time(13, 30)
                afternoon_end = dt_time(15, 0)
                night_start = dt_time(21, 0)
                night_end = dt_time(2, 30)
                
                is_trading_time = (
                    (morning_start <= current_time <= morning_end) or
                    (afternoon_start <= current_time <= afternoon_end) or
                    (night_start <= current_time) or
                    (current_time <= night_end)
                )
                
                # 计算下一个交易时间
                if current_time < morning_start:
                    next_trading = "09:00"
                elif current_time < afternoon_start:
                    next_trading = "13:30"
                elif current_time < night_start:
                    next_trading = "21:00"
                else:
                    next_trading = "09:00 (明日)"
                
                return {
                    "success": True,
                    "data": {
                        "is_trading_time": is_trading_time,
                        "current_time": current_time.strftime('%H:%M:%S'),
                        "next_trading_time": next_trading,
                        "trading_sessions": [
                            {"name": "早盘", "start": "09:00", "end": "11:30"},
                            {"name": "午盘", "start": "13:30", "end": "15:00"},
                            {"name": "夜盘", "start": "21:00", "end": "02:30"}
                        ]
                    }
                }
            except Exception as e:
                logger.error(f"获取交易状态失败: {e}")
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

        @self.app.post("/api/v1/system/start")
        async def start_system():
            """启动ARBIG主系统"""
            try:
                # 尝试启动主系统
                import subprocess
                import sys
                
                # 启动主系统进程（后台运行）
                process = subprocess.Popen([
                    "/root/anaconda3/envs/vnpy/bin/python", "main.py", "--auto-start"
                ], cwd=str(Path(__file__).parent.parent),
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   start_new_session=True)
                
                return {
                    "success": True,
                    "message": "ARBIG主系统启动命令已发送",
                    "data": {"pid": process.pid},
                    "request_id": str(uuid.uuid4())
                }
            except Exception as e:
                logger.error(f"启动主系统失败: {e}")
                return {
                    "success": False,
                    "message": f"启动主系统失败: {str(e)}",
                    "data": None,
                    "request_id": str(uuid.uuid4())
                }

        @self.app.post("/api/v1/system/stop")
        async def stop_system():
            """停止ARBIG主系统"""
            try:
                # 查找并停止主系统进程
                import subprocess
                
                # 查找main.py进程
                result = subprocess.run([
                    "pkill", "-f", "python.*main.py"
                ], capture_output=True, text=True)
                
                return {
                    "success": True,
                    "message": "ARBIG主系统停止命令已发送",
                    "data": {"stopped": True}
                }
            except Exception as e:
                logger.error(f"停止主系统失败: {e}")
                return {
                    "success": False,
                    "message": f"停止主系统失败: {str(e)}"
                }

        @self.app.post("/api/v1/system/mode")
        async def switch_mode(request: dict):
            """切换系统运行模式"""
            try:
                mode = request.get("mode", "")
                reason = request.get("reason", "")
                
                return {
                    "success": True,
                    "message": f"系统模式切换为: {mode}",
                    "data": {"mode": mode, "reason": reason}
                }
            except Exception as e:
                logger.error(f"切换系统模式失败: {e}")
                return {
                    "success": False,
                    "message": f"切换系统模式失败: {str(e)}"
                }

        @self.app.post("/api/v1/system/emergency/stop")
        async def emergency_stop(request: dict):
            """紧急停止系统"""
            try:
                reason = request.get("reason", "")
                
                # 执行紧急停止
                import subprocess
                subprocess.run(["pkill", "-f", "python.*main.py"])
                
                return {
                    "success": True,
                    "message": "紧急停止已执行",
                    "data": {"reason": reason}
                }
            except Exception as e:
                logger.error(f"紧急停止失败: {e}")
                return {
                    "success": False,
                    "message": f"紧急停止失败: {str(e)}"
                }

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

        @self.app.get("/api/test/simple")
        async def test_simple():
            """测试简单API"""
            return {"test": "ok"}

        @self.app.get("/api/v1/test/simple")
        def test_v1_simple():
            """测试v1路径的简单API"""
            return {"test": "v1_ok"}

        @self.app.get("/api/test/services")
        async def test_services():
            """测试服务API - 不使用v1路径"""
            services_list = [
                {
                    "id": "main_system",
                    "name": "main_system",
                    "display_name": "主系统",
                    "status": "stopped",
                    "description": "ARBIG主系统（包含所有服务）",
                    "uptime": "0h 0m 0s",
                    "required": True,
                    "dependencies": [],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": "主系统未运行"
                }
            ]

            return {
                "success": True,
                "message": "服务列表获取成功",
                "data": {
                    "services": services_list
                }
            }

        @self.app.get("/api/v1/services/list")
        def get_services_list_sync():
            """获取服务列表 - 同步版本，避免异步相关的信号错误"""
            services_list = [
                {
                    "id": "main_system",
                    "name": "main_system",
                    "display_name": "主系统",
                    "status": "stopped",
                    "description": "ARBIG主系统（包含所有服务）",
                    "uptime": "0h 0m 0s",
                    "required": True,
                    "dependencies": [],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": "主系统未运行"
                },
                {
                    "id": "ctp_gateway",
                    "name": "ctp_gateway",
                    "display_name": "CTP网关",
                    "status": "stopped",
                    "description": "CTP交易网关连接",
                    "uptime": "0h 0m 0s",
                    "required": True,
                    "dependencies": [],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": None
                },
                {
                    "id": "market_data",
                    "name": "market_data",
                    "display_name": "行情服务",
                    "status": "stopped",
                    "description": "市场行情数据服务",
                    "uptime": "0h 0m 0s",
                    "required": True,
                    "dependencies": ["ctp_gateway"],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": None
                },
                {
                    "id": "trading",
                    "name": "trading",
                    "display_name": "交易服务",
                    "status": "stopped",
                    "description": "交易执行服务",
                    "uptime": "0h 0m 0s",
                    "required": False,
                    "dependencies": ["ctp_gateway", "market_data"],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": None
                },
                {
                    "id": "risk",
                    "name": "risk",
                    "display_name": "风控服务",
                    "status": "stopped",
                    "description": "风险控制服务",
                    "uptime": "0h 0m 0s",
                    "required": False,
                    "dependencies": ["trading"],
                    "cpu_usage": None,
                    "memory_usage": None,
                    "last_heartbeat": None,
                    "pid": None,
                    "start_time": None,
                    "error_message": None
                }
            ]

            return {
                "success": True,
                "message": "服务列表获取成功",
                "data": {
                    "services": services_list
                }
            }

        # 注释掉有问题的API，使用工作正常的版本
        # @self.app.get("/api/v1/services/list")
        # async def get_services_list():
        #     """获取服务列表 - 兼容前端API调用"""
        #     # 这个API有信号处理相关的错误，暂时禁用
        #     pass

        @self.app.post("/api/v1/services/start")
        async def start_service_v1(request: dict):
            """启动服务 - v1 API兼容"""
            try:
                service_name = request.get("service_name")
                if not service_name:
                    return {
                        "success": False,
                        "message": "缺少service_name参数"
                    }

                result = self.service_manager.start_service(service_name)
                return result
            except Exception as e:
                logger.error(f"启动服务失败: {e}")
                return {
                    "success": False,
                    "message": f"启动服务失败: {str(e)}"
                }

        @self.app.post("/api/v1/services/stop")
        async def stop_service_v1(request: dict):
            """停止服务 - v1 API兼容"""
            try:
                service_name = request.get("service_name")
                force = request.get("force", False)
                if not service_name:
                    return {
                        "success": False,
                        "message": "缺少service_name参数"
                    }

                result = self.service_manager.stop_service(service_name)
                return result
            except Exception as e:
                logger.error(f"停止服务失败: {e}")
                return {
                    "success": False,
                    "message": f"停止服务失败: {str(e)}"
                }

        @self.app.post("/api/v1/services/restart")
        async def restart_service_v1(request: dict):
            """重启服务 - v1 API兼容"""
            try:
                service_name = request.get("service_name")
                if not service_name:
                    return {
                        "success": False,
                        "message": "缺少service_name参数"
                    }

                result = self.service_manager.restart_service(service_name)
                return result
            except Exception as e:
                logger.error(f"重启服务失败: {e}")
                return {
                    "success": False,
                    "message": f"重启服务失败: {str(e)}"
                }

        # 日志管理API
        @self.app.get("/api/v1/logs/files")
        async def get_log_files():
            """获取所有日志文件列表"""
            try:
                log_files = self.service_manager.log_manager.get_log_files()
                return {
                    "success": True,
                    "message": "日志文件列表获取成功",
                    "data": {
                        "log_files": log_files
                    }
                }
            except Exception as e:
                logger.error(f"获取日志文件列表失败: {e}")
                return {
                    "success": False,
                    "message": f"获取日志文件列表失败: {str(e)}"
                }

        @self.app.get("/api/v1/logs/content")
        async def get_log_content(
            service: str = "main",
            filename: str = None,
            lines: int = 100,
            level: str = None,
            search: str = None,
            start_time: str = None,
            end_time: str = None
        ):
            """获取日志内容"""
            try:
                result = self.service_manager.log_manager.get_logs(
                    service=service,
                    filename=filename,
                    lines=lines,
                    level=level,
                    search=search,
                    start_time=start_time,
                    end_time=end_time
                )

                if result["success"]:
                    return {
                        "success": True,
                        "message": "日志内容获取成功",
                        "data": result["data"]
                    }
                else:
                    return result

            except Exception as e:
                logger.error(f"获取日志内容失败: {e}")
                return {
                    "success": False,
                    "message": f"获取日志内容失败: {str(e)}"
                }

        @self.app.get("/api/v1/logs/download/{service}/{filename}")
        async def download_log_file(service: str, filename: str):
            """下载日志文件"""
            try:
                # 确定日志目录
                if service == "main":
                    log_dir = Path(__file__).parent.parent / "logs"
                else:
                    log_dir = Path(__file__).parent.parent / "web_admin" / "logs"

                log_file = log_dir / filename

                if not log_file.exists():
                    raise HTTPException(status_code=404, detail="日志文件不存在")

                from fastapi.responses import FileResponse
                return FileResponse(
                    path=str(log_file),
                    filename=filename,
                    media_type='text/plain'
                )

            except Exception as e:
                logger.error(f"下载日志文件失败: {e}")
                raise HTTPException(status_code=500, detail=f"下载日志文件失败: {str(e)}")

        @self.app.get("/assets/{file_path:path}")
        async def serve_assets(file_path: str):
            """专门处理assets文件的静态文件服务"""
            try:
                static_dir = Path(__file__).parent / "static"
                assets_dir = static_dir / "assets"
                file_path_obj = assets_dir / file_path
                
                if file_path_obj.exists() and file_path_obj.is_file():
                    with open(file_path_obj, "rb") as f:
                        content = f.read()
                    
                    # 根据文件扩展名设置正确的Content-Type
                    if file_path.endswith('.js'):
                        return Response(content, media_type="application/javascript")
                    elif file_path.endswith('.css'):
                        return Response(content, media_type="text/css")
                    else:
                        return Response(content)
                else:
                    raise HTTPException(status_code=404, detail=f"Asset file not found: {file_path}")
            except Exception as e:
                logger.error(f"提供assets文件失败: {e}")
                raise HTTPException(status_code=404, detail="Asset file not found")

        @self.app.get("/{full_path:path}")
        async def catch_all(full_path: str):
            """捕获所有其他路由，返回前端页面（用于支持Vue Router的history模式）"""
            # 如果是API路由，返回404
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API endpoint not found")
            
            # 如果是静态资源，返回404（让静态文件中间件处理）
            if full_path.startswith("static/"):
                raise HTTPException(status_code=404, detail="Static file not found")
            
            # 其他所有路由都返回前端页面
            try:
                static_dir = Path(__file__).parent / "static"
                index_file = static_dir / "index.html"
                
                if index_file.exists():
                    with open(index_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        return HTMLResponse(content)
                else:
                    return HTMLResponse("<h1>ARBIG系统</h1><p>前端页面文件不存在</p>")
            except Exception as e:
                logger.error(f"返回前端页面失败: {e}")
                return HTMLResponse(f"<h1>ARBIG系统</h1><p>加载页面失败: {e}</p>")


def run_standalone_web_service(host: str = "0.0.0.0", port: int = 80):
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
