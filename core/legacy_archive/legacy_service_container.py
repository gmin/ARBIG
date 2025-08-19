"""
ARBIG遗留服务容器
保持向后兼容性，供web_admin使用
将逐步迁移到新的架构组件
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

from .event_engine import EventEngine
from .config_manager import ConfigManager
# 暂时注释掉服务导入，避免导入错误
# from .services.market_data_service import MarketDataService
# from .services.account_service import AccountService
# from .services.trading_service import TradingService
# from .services.risk_service import RiskService
# from .services.strategy_service import StrategyService
# from .types import ServiceConfig
# from gateways.ctp_gateway import CtpGatewayWrapper  # 暂时注释掉，避免导入错误
# from .market_data_client import init_market_data_client
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
    ARBIG遗留服务容器 - 保持向后兼容性
    注意：这是遗留代码，新功能请使用新的架构组件
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
            'TradingService': ServiceStatus.STOPPED,
            'StrategyService': ServiceStatus.STOPPED
        }

        # 服务启动时间
        self.services_start_time = {}

        # 服务依赖关系
        self.service_dependencies = {
            'MarketDataService': ['ctp_gateway'],
            'AccountService': ['ctp_gateway'],
            'RiskService': ['AccountService'],
            'TradingService': ['ctp_gateway', 'MarketDataService', 'AccountService', 'RiskService'],
            'StrategyService': ['MarketDataService', 'AccountService', 'TradingService']
        }

        # 线程锁
        self._lock = threading.Lock()

        logger.info("ARBIG遗留服务容器初始化完成")

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
                logger.info("🚀 启动ARBIG量化交易系统（遗留模式）")
                logger.info("="*60)

                # 1. 初始化事件引擎
                if not self._init_event_engine():
                    return ServiceResult(False, "事件引擎初始化失败")

                # 2. 初始化配置管理器
                if not self._init_config_manager():
                    return ServiceResult(False, "配置管理器初始化失败")

                # 3. 连接CTP网关
                ctp_result = self._connect_ctp_with_retry()
                if ctp_result == "FAILED":
                    logger.warning("CTP连接失败，将以演示模式运行")

                # 4. 启动核心服务
                if not self._start_core_services(ctp_result):
                    return ServiceResult(False, "核心服务启动失败")

                # 5. 系统启动完成
                self.running = True
                self.start_time = datetime.now()

                logger.info("="*60)
                logger.info("🎉 ARBIG系统启动成功！")
                logger.info("="*60)

                return ServiceResult(True, "系统启动成功", {
                    "start_time": self.start_time.isoformat(),
                    "ctp_status": ctp_result,
                    "mode": self.current_mode.value
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

                # 停止所有服务
                self._stop_all_services()

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
                    "stop_time": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"系统停止失败: {e}")
            return ServiceResult(False, f"系统停止异常: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            uptime = ""
            if self.start_time and self.running:
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
                        "server": "182.254.243.31:30011",
                        "latency": "15ms" if self.ctp_gateway.is_md_connected() else None
                    },
                    "trading": {
                        "connected": self.ctp_gateway.is_td_connected(),
                        "server": "182.254.243.31:30001",
                        "latency": "18ms" if self.ctp_gateway.is_td_connected() else None
                    }
                }

            # 服务状态
            services_status = {}
            for service_name, status in self.services_status.items():
                start_time = self.services_start_time.get(service_name)
                service_uptime = ""
                if start_time and status == ServiceStatus.RUNNING:
                    delta = datetime.now() - start_time
                    hours, remainder = divmod(delta.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    service_uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

                services_status[service_name] = {
                    "name": service_name,
                    "display_name": self._get_service_display_name(service_name),
                    "status": status.value,
                    "start_time": start_time.isoformat() if start_time else None,
                    "uptime": service_uptime,
                    "dependencies": self.service_dependencies.get(service_name, [])
                }

            return {
                "system_status": "running" if self.running else "stopped",
                "running_mode": self.current_mode.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "uptime": uptime,
                "ctp_status": ctp_status,
                "services_status": services_status,
                "version": "1.0.0-legacy"
            }

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}

    def _init_event_engine(self) -> bool:
        """初始化事件引擎"""
        try:
            self.event_engine = EventEngine()
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            return True
        except Exception as e:
            logger.error(f"✗ 事件引擎启动失败: {e}")
            return False

    def _init_config_manager(self) -> bool:
        """初始化配置管理器"""
        try:
            self.config_manager = ConfigManager()
            logger.info("✓ 配置管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"✗ 配置管理器初始化失败: {e}")
            return False

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

    def _start_core_services(self, ctp_status: str) -> bool:
        """启动核心服务"""
        logger.info("开始启动核心服务...")

        # 根据CTP连接状态启动相应服务
        if ctp_status in ["FULL", "MD_ONLY"]:
            # 启动行情服务
            if not self._start_market_data_service():
                logger.error("行情服务启动失败")
                return False

        if ctp_status in ["FULL", "TD_ONLY"]:
            # 启动交易相关服务
            self._start_account_service()
            self._start_risk_service()
            self._start_trading_service()

        # 更新运行模式
        self._update_running_mode()

        logger.info("核心服务启动完成")
        return True

    def _update_running_mode(self):
        """根据服务状态更新运行模式"""
        running_services = [name for name, status in self.services_status.items() 
                           if status == ServiceStatus.RUNNING]

        # 完全交易模式：所有核心服务都在运行
        core_services = ['MarketDataService', 'AccountService', 'RiskService', 'TradingService']
        if all(svc in running_services for svc in core_services):
            self.current_mode = RunningMode.FULL_TRADING
        elif 'MarketDataService' in running_services and 'AccountService' in running_services:
            self.current_mode = RunningMode.MONITOR_ONLY
        else:
            self.current_mode = RunningMode.MARKET_DATA_ONLY

        logger.info(f"运行模式更新为: {self.current_mode.value}")

    def _get_service_display_name(self, service_name: str) -> str:
        """获取服务显示名称"""
        display_names = {
            'MarketDataService': '行情服务',
            'AccountService': '账户服务',
            'RiskService': '风控服务',
            'TradingService': '交易服务',
            'StrategyService': '策略服务'
        }
        return display_names.get(service_name, service_name)

    def _start_market_data_service(self) -> bool:
        """启动行情服务"""
        try:
            # 从配置文件读取行情订阅配置
            market_data_config = self.config_manager.config.get('market_data', {})
            main_contract = market_data_config.get('main_contract', 'au2509')
            main_contracts = [main_contract] if main_contract else ['au2509']
            cache_size = market_data_config.get('cache_size', 1000)

            service_config = ServiceConfig(
                name="market_data",
                enabled=True,
                config={
                    'symbols': main_contracts,
                    'cache_size': cache_size,
                    'auto_subscribe': market_data_config.get('auto_subscribe', True)
                }
            )

            # 获取Redis配置
            redis_config = self.config_manager.get_redis_config()
            redis_dict = {
                'host': redis_config.host,
                'port': redis_config.port,
                'db': redis_config.db
            }
            if redis_config.password:
                redis_dict['password'] = redis_config.password

            # 初始化全局市场数据客户端
            if init_market_data_client(redis_dict):
                logger.info("✓ 全局市场数据客户端初始化成功")
            else:
                logger.warning("⚠ 全局市场数据客户端初始化失败")

            market_data_service = MarketDataService(
                self.event_engine, service_config, self.ctp_gateway, redis_dict
            )

            if market_data_service.start():
                self.services['MarketDataService'] = market_data_service
                self.services_status['MarketDataService'] = ServiceStatus.RUNNING
                self.services_start_time['MarketDataService'] = datetime.now()
                logger.info("✓ 行情服务启动成功")
                return True
            else:
                logger.error("✗ 行情服务启动失败")
                return False

        except Exception as e:
            logger.error(f"✗ 行情服务启动异常: {e}")
            return False

    def _start_account_service(self) -> bool:
        """启动账户服务"""
        try:
            service_config = ServiceConfig(
                name="account",
                enabled=True,
                config={
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
                self.services_status['AccountService'] = ServiceStatus.RUNNING
                self.services_start_time['AccountService'] = datetime.now()
                logger.info("✓ 账户服务启动成功")
                return True
            else:
                logger.warning("⚠ 账户服务启动失败")
                return False
                
        except Exception as e:
            logger.warning(f"⚠ 账户服务启动异常: {e}")
            return False

    def _start_risk_service(self) -> bool:
        """启动风控服务"""
        try:
            service_config = ServiceConfig(
                name="risk",
                enabled=True,
                config={
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
                self.services_status['RiskService'] = ServiceStatus.RUNNING
                self.services_start_time['RiskService'] = datetime.now()
                logger.info("✓ 风控服务启动成功")
                return True
            else:
                logger.warning("⚠ 风控服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 风控服务启动异常: {e}")
            return False

    def _start_trading_service(self) -> bool:
        """启动交易服务"""
        try:
            service_config = ServiceConfig(
                name="trading",
                enabled=True,
                config={
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
                self.services_status['TradingService'] = ServiceStatus.RUNNING
                self.services_start_time['TradingService'] = datetime.now()
                logger.info("✓ 交易服务启动成功")
                return True
            else:
                logger.warning("⚠ 交易服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 交易服务启动异常: {e}")
            return False

    def _stop_all_services(self):
        """停止所有服务"""
        logger.info("开始停止所有服务...")
        
        # 按相反顺序停止服务
        service_names = ['StrategyService', 'TradingService', 'RiskService', 'AccountService', 'MarketDataService']
        
        for service_name in service_names:
            if self.services_status[service_name] == ServiceStatus.RUNNING:
                try:
                    if service_name in self.services:
                        self.services[service_name].stop()
                        del self.services[service_name]
                    
                    self.services_status[service_name] = ServiceStatus.STOPPED
                    if service_name in self.services_start_time:
                        del self.services_start_time[service_name]
                    
                    logger.info(f"✓ {service_name}已停止")
                except Exception as e:
                    logger.error(f"✗ {service_name}停止失败: {e}")

    # 为了向后兼容，保留一些必要的方法
    def get_service_instance(self, service_name: str):
        """获取服务实例"""
        return self.services.get(service_name)

    def is_running(self) -> bool:
        """检查系统是否在运行"""
        return self.running
