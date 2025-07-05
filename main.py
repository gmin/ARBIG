"""
ARBIG量化交易系统主程序
重构为服务容器架构，支持Web指挥中轴控制
"""

import time
import signal
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.trading_service import TradingService
from core.services.risk_service import RiskService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class RunningMode(str, Enum):
    """系统运行模式"""
    FULL_TRADING = "FULL_TRADING"        # 完整交易模式
    MONITOR_ONLY = "MONITOR_ONLY"        # 仅监控模式
    MARKET_DATA_ONLY = "MARKET_DATA_ONLY" # 仅行情模式

class ServiceStatus(str, Enum):
    """服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class ServiceResult:
    """服务操作结果"""
    def __init__(self, success: bool, message: str, data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}

class ARBIGServiceContainer:
    """
    ARBIG服务容器 - 管理所有服务的生命周期
    提供Web API控制接口，不再自主决策
    """

    def __init__(self):
        """初始化服务容器"""
        self.logger = logger
        self.running = False
        self.current_mode = RunningMode.MARKET_DATA_ONLY
        self.start_time = None

        # CTP连接参数
        self.MAX_RETRY_COUNT = 3
        self.RETRY_INTERVAL = 3
        self.CONNECTION_TIMEOUT = 30

        # 核心组件
        self.event_engine = None
        self.config_manager = None
        self.ctp_gateway = None

        # 核心服务实例
        self.services = {}

        # 服务状态跟踪
        self.services_status = {
            'MarketDataService': ServiceStatus.STOPPED,
            'AccountService': ServiceStatus.STOPPED,
            'RiskService': ServiceStatus.STOPPED,
            'TradingService': ServiceStatus.STOPPED
        }

        # 服务启动时间
        self.services_start_time = {}

        # 服务依赖关系
        self.service_dependencies = {
            'MarketDataService': ['ctp_gateway'],
            'AccountService': ['ctp_gateway'],
            'RiskService': ['AccountService'],
            'TradingService': ['ctp_gateway', 'MarketDataService', 'AccountService', 'RiskService']
        }

        # 线程锁
        self._lock = threading.Lock()

        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("ARBIG服务容器初始化完成")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始关闭系统...")
        self.stop_system()
        sys.exit(0)

    # ==================== 系统级API接口 ====================

    def start_system(self) -> ServiceResult:
        """启动整个系统"""
        try:
            with self._lock:
                if self.running:
                    return ServiceResult(False, "系统已在运行中")

                logger.info("="*60)
                logger.info("🚀 启动ARBIG量化交易系统")
                logger.info("="*60)

                # 1. 初始化配置管理器
                if not self._init_config_manager():
                    return ServiceResult(False, "配置管理器初始化失败")

                # 2. 连接CTP网关
                ctp_result = self._connect_ctp_with_retry()
                if ctp_result == "FAILED":
                    return ServiceResult(False, "CTP连接失败")

                # 3. 启动事件引擎
                if not self._start_event_engine():
                    return ServiceResult(False, "事件引擎启动失败")

                # 4. 系统启动完成
                self.running = True
                self.start_time = datetime.now()

                logger.info("="*60)
                logger.info("🎉 ARBIG系统启动成功！")
                logger.info("="*60)

                return ServiceResult(True, "系统启动成功", {
                    "start_time": self.start_time.isoformat(),
                    "ctp_status": ctp_result
                })

        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return ServiceResult(False, f"系统启动异常: {e}")

    def stop_system(self) -> ServiceResult:
        """停止整个系统"""
        try:
            with self._lock:
                if not self.running:
                    return ServiceResult(False, "系统未在运行")

                logger.info("开始停止ARBIG系统...")

                # 按相反顺序停止所有服务
                service_names = ['TradingService', 'RiskService', 'AccountService', 'MarketDataService']
                stopped_services = []

                for service_name in service_names:
                    if self.services_status[service_name] == ServiceStatus.RUNNING:
                        result = self.stop_service(service_name)
                        if result.success:
                            stopped_services.append(service_name)

                # 停止事件引擎
                if self.event_engine:
                    try:
                        self.event_engine.stop()
                        logger.info("✓ 事件引擎已停止")
                    except Exception as e:
                        logger.error(f"✗ 事件引擎停止失败: {e}")

                # 断开CTP连接
                if self.ctp_gateway:
                    try:
                        self.ctp_gateway.disconnect()
                        logger.info("✓ CTP连接已断开")
                    except Exception as e:
                        logger.error(f"✗ CTP断开失败: {e}")

                self.running = False
                logger.info("ARBIG系统已完全停止")

                return ServiceResult(True, "系统停止成功", {
                    "stopped_services": stopped_services,
                    "stop_time": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"系统停止失败: {e}")
            return ServiceResult(False, f"系统停止异常: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            uptime = ""
            if self.start_time:
                delta = datetime.now() - self.start_time
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

            # CTP连接状态
            ctp_status = {}
            if self.ctp_gateway:
                ctp_status = {
                    "market_data": {
                        "connected": self.ctp_gateway.is_md_connected(),
                        "server": "180.168.146.187:10131",
                        "latency": "15ms" if self.ctp_gateway.is_md_connected() else None
                    },
                    "trading": {
                        "connected": self.ctp_gateway.is_td_connected(),
                        "server": "180.168.146.187:10130",
                        "latency": "18ms" if self.ctp_gateway.is_td_connected() else None
                    }
                }

            # 服务统计
            services_summary = {
                "total": len(self.services_status),
                "running": sum(1 for status in self.services_status.values() if status == ServiceStatus.RUNNING),
                "stopped": sum(1 for status in self.services_status.values() if status == ServiceStatus.STOPPED),
                "error": sum(1 for status in self.services_status.values() if status == ServiceStatus.ERROR)
            }

            return {
                "system_status": "running" if self.running else "stopped",
                "running_mode": self.current_mode.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "uptime": uptime,
                "ctp_status": ctp_status,
                "services_summary": services_summary,
                "version": "1.0.0"
            }

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}

    def switch_mode(self, mode: RunningMode, reason: str = None) -> ServiceResult:
        """切换运行模式"""
        try:
            old_mode = self.current_mode
            self.current_mode = mode

            logger.info(f"系统模式已从 {old_mode.value} 切换至 {mode.value}")
            if reason:
                logger.info(f"切换原因: {reason}")

            return ServiceResult(True, f"运行模式已切换至 {mode.value}", {
                "old_mode": old_mode.value,
                "new_mode": mode.value,
                "switch_time": datetime.now().isoformat(),
                "reason": reason
            })

        except Exception as e:
            logger.error(f"切换运行模式失败: {e}")
            return ServiceResult(False, f"切换运行模式异常: {e}")

    # ==================== 服务管理API接口 ====================

    def start_service(self, service_name: str, config: Dict[str, Any] = None) -> ServiceResult:
        """启动指定服务"""
        try:
            with self._lock:
                # 检查服务是否已在运行
                if self.services_status.get(service_name) == ServiceStatus.RUNNING:
                    return ServiceResult(False, f"{service_name}已在运行中")

                # 检查系统是否已启动
                if not self.running:
                    return ServiceResult(False, "系统未启动，请先启动系统")

                # 检查依赖关系
                if not self._check_service_dependencies(service_name):
                    return ServiceResult(False, f"{service_name}的依赖服务未启动")

                # 设置服务状态为启动中
                self.services_status[service_name] = ServiceStatus.STARTING

                # 启动服务
                success = False
                if service_name == 'MarketDataService':
                    success = self._start_market_data_service(config)
                elif service_name == 'AccountService':
                    success = self._start_account_service(config)
                elif service_name == 'RiskService':
                    success = self._start_risk_service(config)
                elif service_name == 'TradingService':
                    success = self._start_trading_service(config)
                else:
                    return ServiceResult(False, f"未知的服务: {service_name}")

                if success:
                    self.services_status[service_name] = ServiceStatus.RUNNING
                    self.services_start_time[service_name] = datetime.now()
                    self._update_running_mode()

                    return ServiceResult(True, f"{service_name}启动成功", {
                        "service_name": service_name,
                        "start_time": self.services_start_time[service_name].isoformat(),
                        "config": config
                    })
                else:
                    self.services_status[service_name] = ServiceStatus.ERROR
                    return ServiceResult(False, f"{service_name}启动失败")

        except Exception as e:
            self.services_status[service_name] = ServiceStatus.ERROR
            logger.error(f"启动服务{service_name}异常: {e}")
            return ServiceResult(False, f"启动服务异常: {e}")

    def stop_service(self, service_name: str, force: bool = False) -> ServiceResult:
        """停止指定服务"""
        try:
            with self._lock:
                # 检查服务是否在运行
                if self.services_status.get(service_name) != ServiceStatus.RUNNING:
                    return ServiceResult(False, f"{service_name}未在运行")

                # 检查是否有其他服务依赖此服务
                if not force:
                    dependent_services = self._get_dependent_services(service_name)
                    if dependent_services:
                        return ServiceResult(False, f"以下服务依赖{service_name}: {', '.join(dependent_services)}")

                # 设置服务状态为停止中
                self.services_status[service_name] = ServiceStatus.STOPPING

                # 停止服务
                success = False
                if service_name in self.services:
                    try:
                        self.services[service_name].stop()
                        del self.services[service_name]
                        success = True
                    except Exception as e:
                        logger.error(f"停止服务{service_name}失败: {e}")

                if success:
                    self.services_status[service_name] = ServiceStatus.STOPPED
                    if service_name in self.services_start_time:
                        del self.services_start_time[service_name]
                    self._update_running_mode()

                    return ServiceResult(True, f"{service_name}停止成功", {
                        "service_name": service_name,
                        "stop_time": datetime.now().isoformat()
                    })
                else:
                    self.services_status[service_name] = ServiceStatus.ERROR
                    return ServiceResult(False, f"{service_name}停止失败")

        except Exception as e:
            logger.error(f"停止服务{service_name}异常: {e}")
            return ServiceResult(False, f"停止服务异常: {e}")

    def restart_service(self, service_name: str, config: Dict[str, Any] = None) -> ServiceResult:
        """重启指定服务"""
        try:
            # 先停止服务
            stop_result = self.stop_service(service_name, force=True)
            if not stop_result.success:
                return stop_result

            # 等待一下确保服务完全停止
            time.sleep(1)

            # 再启动服务
            return self.start_service(service_name, config)

        except Exception as e:
            logger.error(f"重启服务{service_name}异常: {e}")
            return ServiceResult(False, f"重启服务异常: {e}")

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            if service_name not in self.services_status:
                return {"error": f"未知的服务: {service_name}"}

            status = self.services_status[service_name]
            start_time = self.services_start_time.get(service_name)

            uptime = ""
            if start_time and status == ServiceStatus.RUNNING:
                delta = datetime.now() - start_time
                hours, remainder = divmod(delta.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

            return {
                "name": service_name,
                "display_name": self._get_service_display_name(service_name),
                "status": status.value,
                "start_time": start_time.isoformat() if start_time else None,
                "uptime": uptime,
                "required": service_name == 'MarketDataService',
                "dependencies": self.service_dependencies.get(service_name, [])
            }

        except Exception as e:
            logger.error(f"获取服务{service_name}状态失败: {e}")
            return {"error": str(e)}

    def get_all_services_status(self) -> List[Dict[str, Any]]:
        """获取所有服务状态"""
        try:
            services = []
            for service_name in self.services_status.keys():
                service_info = self.get_service_status(service_name)
                if "error" not in service_info:
                    services.append(service_info)
            return services

        except Exception as e:
            logger.error(f"获取所有服务状态失败: {e}")
            return []

    # ==================== 内部辅助方法 ====================

    def _init_config_manager(self) -> bool:
        """初始化配置管理器"""
        try:
            self.config_manager = ConfigManager()
            logger.info("✓ 配置管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"✗ 配置管理器初始化失败: {e}")
            return False

    def _check_service_dependencies(self, service_name: str) -> bool:
        """检查服务依赖关系"""
        try:
            dependencies = self.service_dependencies.get(service_name, [])

            for dep in dependencies:
                if dep == 'ctp_gateway':
                    if not self.ctp_gateway or not (self.ctp_gateway.is_md_connected() or self.ctp_gateway.is_td_connected()):
                        logger.error(f"{service_name}需要CTP连接，但CTP未连接")
                        return False
                else:
                    if self.services_status.get(dep) != ServiceStatus.RUNNING:
                        logger.error(f"{service_name}需要{dep}服务，但{dep}未运行")
                        return False

            return True

        except Exception as e:
            logger.error(f"检查服务依赖失败: {e}")
            return False

    def _get_dependent_services(self, service_name: str) -> List[str]:
        """获取依赖指定服务的其他服务"""
        dependent_services = []
        for svc_name, deps in self.service_dependencies.items():
            if service_name in deps and self.services_status.get(svc_name) == ServiceStatus.RUNNING:
                dependent_services.append(svc_name)
        return dependent_services

    def _get_service_display_name(self, service_name: str) -> str:
        """获取服务显示名称"""
        display_names = {
            'MarketDataService': '行情服务',
            'AccountService': '账户服务',
            'RiskService': '风控服务',
            'TradingService': '交易服务'
        }
        return display_names.get(service_name, service_name)

    def _update_running_mode(self):
        """根据服务状态更新运行模式"""
        try:
            running_services = [name for name, status in self.services_status.items()
                              if status == ServiceStatus.RUNNING]

            if all(svc in running_services for svc in ['MarketDataService', 'AccountService', 'RiskService', 'TradingService']):
                self.current_mode = RunningMode.FULL_TRADING
            elif 'MarketDataService' in running_services and 'AccountService' in running_services:
                self.current_mode = RunningMode.MONITOR_ONLY
            else:
                self.current_mode = RunningMode.MARKET_DATA_ONLY

            logger.info(f"运行模式更新为: {self.current_mode.value}")

        except Exception as e:
            logger.error(f"更新运行模式失败: {e}")

    def _connect_ctp_with_retry(self) -> str:
        """CTP连接重试逻辑"""
        logger.info("开始CTP连接...")

        for attempt in range(1, self.MAX_RETRY_COUNT + 1):
            logger.info(f"CTP连接尝试 {attempt}/{self.MAX_RETRY_COUNT}")

            try:
                # 创建CTP网关
                if not self.ctp_gateway:
                    self.ctp_gateway = CtpGatewayWrapper(self.config_manager)

                # 尝试连接
                if self.ctp_gateway.connect():
                    # 等待连接建立
                    if self._wait_for_ctp_connection():
                        connection_status = self._check_ctp_connection()
                        if connection_status != "FAILED":
                            logger.info(f"✓ CTP连接成功，状态: {connection_status}")
                            return connection_status
                        else:
                            logger.warning("CTP连接状态检查失败")
                    else:
                        logger.warning("CTP连接超时")
                else:
                    logger.warning("CTP连接调用失败")

            except Exception as e:
                logger.error(f"CTP连接异常: {e}")

            # 重试前等待
            if attempt < self.MAX_RETRY_COUNT:
                logger.info(f"等待{self.RETRY_INTERVAL}秒后重试...")
                time.sleep(self.RETRY_INTERVAL)

        logger.error("CTP连接失败，已达到最大重试次数")
        return "FAILED"

    def _wait_for_ctp_connection(self) -> bool:
        """等待CTP连接建立"""
        start_time = time.time()

        while time.time() - start_time < self.CONNECTION_TIMEOUT:
            if self.ctp_gateway.is_md_connected() or self.ctp_gateway.is_td_connected():
                # 至少有一个连接成功，再等待一下看是否都能连上
                time.sleep(2)
                return True
            time.sleep(1)

        return False

    def _check_ctp_connection(self) -> str:
        """检查CTP连接状态"""
        md_connected = self.ctp_gateway.is_md_connected()  # 行情连接
        td_connected = self.ctp_gateway.is_td_connected()  # 交易连接

        if md_connected and td_connected:
            return "FULL"      # 完整连接
        elif md_connected:
            return "MD_ONLY"   # 仅行情
        elif td_connected:
            return "TD_ONLY"   # 仅交易（不太可能）
        else:
            return "FAILED"    # 完全失败

    def _start_event_engine(self) -> bool:
        """启动事件引擎"""
        try:
            self.event_engine = EventEngine()
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            return True
        except Exception as e:
            logger.error(f"✗ 事件引擎启动失败: {e}")
            return False

    def _start_core_services(self, ctp_status: str) -> bool:
        """启动核心服务"""
        logger.info("开始启动核心服务...")

        # 1. 启动行情服务（必须成功）
        if not self._start_market_data_service():
            logger.error("✗ 行情服务启动失败，系统无法继续")
            return False

        # 2. 根据CTP连接状态启动其他服务
        if ctp_status in ["FULL", "TD_ONLY"]:
            # 有交易连接才启动交易相关服务
            self._start_account_service()
            self._start_risk_service()
            self._start_trading_service()
        else:
            logger.warning("仅有行情连接，跳过交易相关服务")

        logger.info("核心服务启动完成")
        return True

    def _start_market_data_service(self, config: Dict[str, Any] = None) -> bool:
        """启动行情服务"""
        try:
            service_config = ServiceConfig(
                name="market_data",
                enabled=True,
                config=config or {
                    'symbols': ['au2509', 'au2512', 'au2601'],
                    'cache_size': 1000
                }
            )

            market_data_service = MarketDataService(
                self.event_engine, service_config, self.ctp_gateway
            )

            if market_data_service.start():
                self.services['MarketDataService'] = market_data_service
                logger.info("✓ 行情服务启动成功")
                return True
            else:
                logger.error("✗ 行情服务启动失败")
                return False

        except Exception as e:
            logger.error(f"✗ 行情服务启动异常: {e}")
            return False

    def _start_account_service(self, config: Dict[str, Any] = None) -> bool:
        """启动账户服务"""
        try:
            service_config = ServiceConfig(
                name="account",
                enabled=True,
                config=config or {
                    'update_interval': 30,
                    'position_sync': True,
                    'auto_query_after_trade': True
                }
            )

            account_service = AccountService(
                self.event_engine, service_config, self.ctp_gateway
            )

            if account_service.start():
                self.services['AccountService'] = account_service
                logger.info("✓ 账户服务启动成功")
                return True
            else:
                logger.warning("⚠ 账户服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 账户服务启动异常: {e}")
            return False

    def _start_risk_service(self, config: Dict[str, Any] = None) -> bool:
        """启动风控服务"""
        try:
            service_config = ServiceConfig(
                name="risk",
                enabled=True,
                config=config or {
                    'max_position_ratio': 0.8,
                    'max_daily_loss': 50000,
                    'max_single_order_volume': 10
                }
            )

            # 获取账户服务实例
            account_service = self.services.get('AccountService')
            if not account_service:
                logger.error("风控服务需要账户服务，但账户服务未启动")
                return False

            risk_service = RiskService(
                self.event_engine, service_config, account_service
            )

            if risk_service.start():
                self.services['RiskService'] = risk_service
                logger.info("✓ 风控服务启动成功")
                return True
            else:
                logger.warning("⚠ 风控服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 风控服务启动异常: {e}")
            return False

    def _start_trading_service(self, config: Dict[str, Any] = None) -> bool:
        """启动交易服务"""
        try:
            service_config = ServiceConfig(
                name="trading",
                enabled=True,
                config=config or {
                    'order_timeout': 30,
                    'max_orders_per_second': 5
                }
            )

            # 获取依赖服务实例
            account_service = self.services.get('AccountService')
            risk_service = self.services.get('RiskService')

            if not account_service:
                logger.error("交易服务需要账户服务，但账户服务未启动")
                return False

            if not risk_service:
                logger.error("交易服务需要风控服务，但风控服务未启动")
                return False

            trading_service = TradingService(
                self.event_engine, service_config, self.ctp_gateway,
                account_service, risk_service
            )

            if trading_service.start():
                self.services['TradingService'] = trading_service
                logger.info("✓ 交易服务启动成功")
                return True
            else:
                logger.warning("⚠ 交易服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 交易服务启动异常: {e}")
            return False

    def run(self):
        """运行系统主循环（保持兼容性）"""
        try:
            logger.info("ARBIG服务容器运行中...")
            logger.info("系统现在通过Web API进行控制")
            logger.info("访问 http://localhost:8000/api/docs 查看API文档")

            while self.running:
                time.sleep(1)

                # 可以在这里添加定期检查逻辑
                # 比如检查服务状态、内存使用等

        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
        finally:
            self.stop_system()

# ==================== 全局服务容器实例 ====================

# 全局服务容器实例
_service_container = None

def get_service_container() -> ARBIGServiceContainer:
    """获取全局服务容器实例"""
    global _service_container
    if _service_container is None:
        _service_container = ARBIGServiceContainer()
    return _service_container

def init_service_container():
    """初始化服务容器"""
    global _service_container
    _service_container = ARBIGServiceContainer()
    return _service_container


def main():
    """主函数 - 现在作为服务容器运行"""
    import argparse

    parser = argparse.ArgumentParser(description='ARBIG服务容器')
    parser.add_argument('--daemon', '-d', action='store_true', help='后台运行模式')
    parser.add_argument('--api-only', action='store_true', help='仅启动API服务')
    parser.add_argument('--auto-start', action='store_true', help='自动启动系统')

    args = parser.parse_args()

    print("🚀 ARBIG服务容器")
    print("=" * 50)
    print("系统现在通过Web API进行控制")
    print("API文档: http://localhost:8000/api/docs")
    print("系统状态: http://localhost:8000/api/v1/system/status")
    print("=" * 50)

    # 创建服务容器
    service_container = init_service_container()

    try:
        # 如果指定自动启动，则启动系统
        if args.auto_start:
            logger.info("自动启动系统...")
            result = service_container.start_system()
            if result.success:
                logger.info("✓ 系统自动启动成功")
            else:
                logger.error(f"✗ 系统自动启动失败: {result.message}")

        # 连接服务容器到Web API
        try:
            from web_monitor.api.dependencies import set_service_container
            set_service_container(service_container)
            logger.info("✓ 服务容器已连接到Web API")
        except ImportError:
            logger.warning("⚠ 无法导入Web API模块，API功能将不可用")

        # 启动Web API服务
        if not args.api_only:
            logger.info("启动Web API服务...")

            # 在单独线程中启动API服务
            import threading
            from web_monitor.api.main import start_api_server

            api_thread = threading.Thread(
                target=start_api_server,
                kwargs={"host": "0.0.0.0", "port": 8000, "reload": False},
                daemon=True
            )
            api_thread.start()

            logger.info("✓ Web API服务已启动")

        # 运行主循环
        if args.daemon:
            logger.info("服务容器以后台模式运行")
        else:
            logger.info("服务容器运行中，按Ctrl+C停止")

        service_container.run()

    except KeyboardInterrupt:
        logger.info("收到停止信号")
    except Exception as e:
        logger.error(f"服务容器运行异常: {e}")
        sys.exit(1)
    finally:
        logger.info("服务容器已停止")

if __name__ == "__main__":
    main()
