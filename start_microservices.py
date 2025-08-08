#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG微服务启动脚本
用于启动和管理微服务架构的各个服务
"""

import sys
import os
import argparse
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class MicroserviceManager:
    """微服务管理器"""
    
    def __init__(self):
        """初始化微服务管理器"""
        self.services = {
            "trading_service": {
                "name": "核心交易服务",
                "script": "services/trading_service/main.py",
                "port": 8001,
                "process": None,
                "required": True
            },
            "web_admin_service": {
                "name": "Web管理服务",
                "script": "services/web_admin_service/main.py", 
                "port": 80,
                "process": None,
                "required": True
            }
        }
        self.running = False
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始关闭所有服务...")
        self.stop_all_services()
        sys.exit(0)
    
    def start_service(self, service_name: str, **kwargs) -> bool:
        """启动单个服务"""
        if service_name not in self.services:
            logger.error(f"未知服务: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if service["process"] and service["process"].poll() is None:
            logger.warning(f"服务 {service['name']} 已在运行")
            return True
        
        try:
            logger.info(f"启动服务: {service['name']} (端口 {service['port']})")
            
            # 构建启动命令 - 在vnpy环境中运行
            cmd = [
                "conda", "run", "-n", "vnpy",
                "python", service["script"],
                "--host", kwargs.get("host", "0.0.0.0"),
                "--port", str(service["port"]),
                "--log-level", kwargs.get("log_level", "info")
            ]
            
            if kwargs.get("reload", False):
                cmd.append("--reload")
            
            # 启动进程
            service["process"] = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 等待一下确保服务启动
            time.sleep(2)
            
            if service["process"].poll() is None:
                logger.info(f"✅ 服务 {service['name']} 启动成功 (PID: {service['process'].pid})")
                return True
            else:
                logger.error(f"❌ 服务 {service['name']} 启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动服务 {service['name']} 异常: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """停止单个服务"""
        if service_name not in self.services:
            logger.error(f"未知服务: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if not service["process"] or service["process"].poll() is not None:
            logger.warning(f"服务 {service['name']} 未在运行")
            return True
        
        try:
            logger.info(f"停止服务: {service['name']}")
            
            # 发送终止信号
            service["process"].terminate()
            
            # 等待进程结束
            try:
                service["process"].wait(timeout=10)
                logger.info(f"✅ 服务 {service['name']} 已停止")
                return True
            except subprocess.TimeoutExpired:
                # 强制杀死进程
                logger.warning(f"强制杀死服务: {service['name']}")
                service["process"].kill()
                service["process"].wait()
                logger.info(f"✅ 服务 {service['name']} 已强制停止")
                return True
                
        except Exception as e:
            logger.error(f"停止服务 {service['name']} 异常: {e}")
            return False
        finally:
            service["process"] = None
    
    def start_all_services(self, **kwargs) -> bool:
        """启动所有服务"""
        logger.info("="*60)
        logger.info("🚀 启动ARBIG微服务架构")
        logger.info("="*60)
        
        success_count = 0
        total_count = len(self.services)
        
        # 按顺序启动服务
        service_order = ["trading_service", "web_admin_service"]
        
        for service_name in service_order:
            if service_name in self.services:
                if self.start_service(service_name, **kwargs):
                    success_count += 1
                else:
                    service = self.services[service_name]
                    if service["required"]:
                        logger.error(f"必需服务 {service['name']} 启动失败，停止启动流程")
                        self.stop_all_services()
                        return False
        
        if success_count == total_count:
            logger.info("="*60)
            logger.info("🎉 所有微服务启动成功！")
            logger.info("💻 Web管理界面: http://localhost:80")
            logger.info("🔧 核心交易服务: http://localhost:8001")
            logger.info("📚 API文档: http://localhost:80/api/docs")
            logger.info("="*60)
            self.running = True
            return True
        else:
            logger.error(f"部分服务启动失败 ({success_count}/{total_count})")
            return False
    
    def stop_all_services(self) -> bool:
        """停止所有服务"""
        logger.info("停止所有微服务...")
        
        success_count = 0
        total_count = len([s for s in self.services.values() if s["process"]])
        
        # 按相反顺序停止服务
        service_order = ["web_admin_service", "trading_service"]
        
        for service_name in service_order:
            if service_name in self.services:
                if self.stop_service(service_name):
                    success_count += 1
        
        self.running = False
        
        if total_count == 0:
            logger.info("没有运行中的服务")
            return True
        elif success_count == total_count:
            logger.info("✅ 所有微服务已停止")
            return True
        else:
            logger.warning(f"部分服务停止失败 ({success_count}/{total_count})")
            return False
    
    def get_services_status(self) -> Dict[str, Dict]:
        """获取所有服务状态"""
        status = {}
        for service_name, service in self.services.items():
            is_running = service["process"] and service["process"].poll() is None
            status[service_name] = {
                "name": service["name"],
                "port": service["port"],
                "running": is_running,
                "pid": service["process"].pid if is_running else None,
                "required": service["required"]
            }
        return status
    
    def monitor_services(self):
        """监控服务状态"""
        try:
            logger.info("开始监控微服务状态...")
            logger.info("按 Ctrl+C 退出")
            
            while self.running:
                time.sleep(5)
                
                # 检查服务状态
                for service_name, service in self.services.items():
                    if service["process"]:
                        if service["process"].poll() is not None:
                            logger.error(f"服务 {service['name']} 意外退出")
                            service["process"] = None
                            
                            if service["required"]:
                                logger.error("必需服务退出，停止所有服务")
                                self.stop_all_services()
                                return
                
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"监控异常: {e}")
        finally:
            self.stop_all_services()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG微服务管理器')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'restart'],
                       help='操作类型')
    parser.add_argument('--service', type=str,
                       help='指定服务名称（可选）')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--reload', action='store_true',
                       help='开发模式：自动重载')
    parser.add_argument('--log-level', type=str, default='info',
                       choices=['debug', 'info', 'warning', 'error'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    manager = MicroserviceManager()
    
    try:
        if args.action == 'start':
            if args.service:
                success = manager.start_service(
                    args.service,
                    host=args.host,
                    reload=args.reload,
                    log_level=args.log_level
                )
                if success:
                    logger.info(f"服务 {args.service} 启动成功")
                else:
                    logger.error(f"服务 {args.service} 启动失败")
                    sys.exit(1)
            else:
                success = manager.start_all_services(
                    host=args.host,
                    reload=args.reload,
                    log_level=args.log_level
                )
                if success:
                    manager.monitor_services()
                else:
                    sys.exit(1)
        
        elif args.action == 'stop':
            if args.service:
                manager.stop_service(args.service)
            else:
                manager.stop_all_services()
        
        elif args.action == 'status':
            status = manager.get_services_status()
            logger.info("微服务状态:")
            for service_name, info in status.items():
                status_text = "运行中" if info["running"] else "已停止"
                pid_text = f" (PID: {info['pid']})" if info["pid"] else ""
                required_text = " [必需]" if info["required"] else ""
                logger.info(f"  {info['name']}: {status_text}{pid_text}{required_text}")
        
        elif args.action == 'restart':
            if args.service:
                manager.stop_service(args.service)
                time.sleep(2)
                manager.start_service(
                    args.service,
                    host=args.host,
                    reload=args.reload,
                    log_level=args.log_level
                )
            else:
                manager.stop_all_services()
                time.sleep(2)
                success = manager.start_all_services(
                    host=args.host,
                    reload=args.reload,
                    log_level=args.log_level
                )
                if success:
                    manager.monitor_services()
                else:
                    sys.exit(1)
    
    except Exception as e:
        logger.error(f"操作异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
