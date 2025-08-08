"""
系统连接器
负责Web界面与ARBIG核心系统的通信
"""

import asyncio
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from core.system_controller import SystemController
from core.legacy_service_container import ARBIGServiceContainer
from utils.logger import get_logger

logger = get_logger(__name__)

class SystemConnector:
    """
    系统连接器
    提供Web界面与核心系统的统一接口
    """

    def __init__(self):
        """初始化系统连接器"""
        self.system_controller = None
        self.legacy_container = None
        self.use_new_architecture = True
        self._lock = threading.Lock()

        logger.info("系统连接器初始化完成")

    def initialize(self, use_new_architecture: bool = True, system_controller=None):
        """
        初始化系统连接

        Args:
            use_new_architecture: 是否使用新架构
            system_controller: 外部传入的系统控制器实例（单体架构）
        """
        try:
            with self._lock:
                self.use_new_architecture = use_new_architecture

                if use_new_architecture:
                    if system_controller:
                        # 单体架构：使用外部传入的系统控制器
                        self.system_controller = system_controller
                        logger.info("✓ 使用外部系统控制器（单体架构）")
                    else:
                        # 独立架构：创建新的系统控制器
                        self.system_controller = SystemController()
                        logger.info("✓ 新架构系统控制器已初始化")
                else:
                    # 使用遗留架构
                    self.legacy_container = ARBIGServiceContainer()
                    logger.info("✓ 遗留架构服务容器已初始化")

        except Exception as e:
            logger.error(f"系统连接器初始化失败: {e}")
            raise

    def set_system_controller(self, system_controller):
        """设置系统控制器实例（用于单体架构）"""
        with self._lock:
            self.system_controller = system_controller
            self.use_new_architecture = True
            logger.info("✓ 系统控制器已设置")

    async def start_system(self) -> Dict[str, Any]:
        """启动系统"""
        try:
            if self.use_new_architecture and self.system_controller:
                result = self.system_controller.start_system()
                return {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data
                }
            elif not self.use_new_architecture and self.legacy_container:
                result = self.legacy_container.start_system()
                return {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            return {
                "success": False,
                "message": f"启动系统异常: {e}",
                "data": {}
            }

    async def stop_system(self) -> Dict[str, Any]:
        """停止系统"""
        try:
            if self.use_new_architecture and self.system_controller:
                result = self.system_controller.stop_system()
                return {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data
                }
            elif not self.use_new_architecture and self.legacy_container:
                result = self.legacy_container.stop_system()
                return {
                    "success": result.success,
                    "message": result.message,
                    "data": result.data
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"停止系统失败: {e}")
            return {
                "success": False,
                "message": f"停止系统异常: {e}",
                "data": {}
            }

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            if self.use_new_architecture and self.system_controller:
                status = self.system_controller.get_system_status()

                # 确保ctp_status有正确的结构
                if not status.get("ctp_status"):
                    status["ctp_status"] = {
                        "market_data": {
                            "connected": False,
                            "server": "未连接",
                            "latency": "N/A"
                        },
                        "trading": {
                            "connected": False,
                            "server": "未连接",
                            "latency": "N/A"
                        }
                    }

                # 确保services_status有正确的结构
                if not status.get("services_status"):
                    status["services_status"] = {
                        "services": {},
                        "summary": {
                            "total": 5,
                            "running": 0,
                            "stopped": 5,
                            "error": 0
                        }
                    }

                return {
                    "success": True,
                    "message": "获取系统状态成功",
                    "data": status
                }
            elif not self.use_new_architecture and self.legacy_container:
                status = self.legacy_container.get_system_status()
                return {
                    "success": True,
                    "message": "获取系统状态成功",
                    "data": status
                }
            else:
                # 系统未初始化，返回默认状态
                return {
                    "success": True,
                    "message": "系统未初始化",
                    "data": {
                        "system_status": "stopped",
                        "running_mode": "MARKET_DATA_ONLY",
                        "start_time": None,
                        "uptime": "",
                        "ctp_status": {},
                        "services_status": {},
                        "version": "2.0.0"
                    }
                }
                
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "success": False,
                "message": f"获取系统状态异常: {e}",
                "data": {}
            }

    async def start_service(self, service_name: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """启动服务"""
        try:
            if self.use_new_architecture and self.system_controller:
                if self.system_controller.service_manager:
                    result = self.system_controller.service_manager.start_service(service_name, config)
                    return {
                        "success": result.success,
                        "message": result.message,
                        "data": result.data
                    }
                else:
                    return {
                        "success": False,
                        "message": "服务管理器未初始化",
                        "data": {}
                    }
            elif not self.use_new_architecture and self.legacy_container:
                # 遗留架构暂不支持单独启动服务
                return {
                    "success": False,
                    "message": "遗留架构不支持单独启动服务",
                    "data": {}
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"启动服务{service_name}失败: {e}")
            return {
                "success": False,
                "message": f"启动服务异常: {e}",
                "data": {}
            }

    async def stop_service(self, service_name: str, force: bool = False) -> Dict[str, Any]:
        """停止服务"""
        try:
            if self.use_new_architecture and self.system_controller:
                if self.system_controller.service_manager:
                    result = self.system_controller.service_manager.stop_service(service_name, force)
                    return {
                        "success": result.success,
                        "message": result.message,
                        "data": result.data
                    }
                else:
                    return {
                        "success": False,
                        "message": "服务管理器未初始化",
                        "data": {}
                    }
            elif not self.use_new_architecture and self.legacy_container:
                # 遗留架构暂不支持单独停止服务
                return {
                    "success": False,
                    "message": "遗留架构不支持单独停止服务",
                    "data": {}
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"停止服务{service_name}失败: {e}")
            return {
                "success": False,
                "message": f"停止服务异常: {e}",
                "data": {}
            }

    async def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            if self.use_new_architecture and self.system_controller:
                if self.system_controller.service_manager:
                    status = self.system_controller.service_manager.get_service_status(service_name)
                    return {
                        "success": True,
                        "message": "获取服务状态成功",
                        "data": status
                    }
                else:
                    return {
                        "success": False,
                        "message": "服务管理器未初始化",
                        "data": {}
                    }
            elif not self.use_new_architecture and self.legacy_container:
                # 从遗留容器获取服务状态
                system_status = self.legacy_container.get_system_status()
                services_status = system_status.get("services_status", {})
                service_status = services_status.get(service_name, {})
                
                return {
                    "success": True,
                    "message": "获取服务状态成功",
                    "data": service_status
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"获取服务{service_name}状态失败: {e}")
            return {
                "success": False,
                "message": f"获取服务状态异常: {e}",
                "data": {}
            }

    async def get_all_services_status(self) -> Dict[str, Any]:
        """获取所有服务状态"""
        try:
            if self.use_new_architecture and self.system_controller:
                if self.system_controller.service_manager:
                    status = self.system_controller.service_manager.get_all_services_status()
                    return {
                        "success": True,
                        "message": "获取所有服务状态成功",
                        "data": status
                    }
                else:
                    return {
                        "success": False,
                        "message": "服务管理器未初始化",
                        "data": {}
                    }
            elif not self.use_new_architecture and self.legacy_container:
                # 从遗留容器获取服务状态
                system_status = self.legacy_container.get_system_status()
                services_status = system_status.get("services_status", {})
                
                return {
                    "success": True,
                    "message": "获取所有服务状态成功",
                    "data": {
                        "services": services_status,
                        "summary": {
                            "total": len(services_status),
                            "running": sum(1 for s in services_status.values() if s.get("status") == "running"),
                            "stopped": sum(1 for s in services_status.values() if s.get("status") == "stopped"),
                            "error": sum(1 for s in services_status.values() if s.get("status") == "error")
                        }
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "系统未初始化",
                    "data": {}
                }
                
        except Exception as e:
            logger.error(f"获取所有服务状态失败: {e}")
            return {
                "success": False,
                "message": f"获取所有服务状态异常: {e}",
                "data": {}
            }

    def is_system_running(self) -> bool:
        """检查系统是否在运行"""
        try:
            if self.use_new_architecture and self.system_controller:
                return self.system_controller.status.value == "running"
            elif not self.use_new_architecture and self.legacy_container:
                return self.legacy_container.is_running()
            else:
                return False
        except Exception as e:
            logger.error(f"检查系统运行状态失败: {e}")
            return False

    def get_architecture_info(self) -> Dict[str, Any]:
        """获取架构信息"""
        return {
            "use_new_architecture": self.use_new_architecture,
            "architecture_version": "2.0.0" if self.use_new_architecture else "1.0.0-legacy",
            "system_controller_initialized": self.system_controller is not None,
            "legacy_container_initialized": self.legacy_container is not None
        }

# 全局系统连接器实例
system_connector = SystemConnector()

def get_system_connector() -> SystemConnector:
    """获取系统连接器实例"""
    return system_connector
