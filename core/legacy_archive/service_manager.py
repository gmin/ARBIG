"""
ARBIG服务管理器
负责所有服务的生命周期管理
"""

import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from .event_engine import EventEngine
from .config_manager import ConfigManager
from .types import ServiceConfig
# 暂时注释掉服务导入，避免导入错误
# from .services.market_data_service import MarketDataService
# from .services.account_service import AccountService
# from .services.trading_service import TradingService
# from .services.risk_service import RiskService
# from .services.strategy_service import StrategyService
# from .market_data_client import init_market_data_client
from utils.logger import get_logger

logger = get_logger(__name__)

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

class ServiceManager:
    """
    服务管理器
    负责管理所有业务服务的生命周期
    """

    def __init__(self, event_engine: EventEngine, config_manager: ConfigManager, 
                 ctp_gateway, event_bus):
        """初始化服务管理器"""
        self.event_engine = event_engine
        self.config_manager = config_manager
        self.ctp_gateway = ctp_gateway
        self.event_bus = event_bus

        # 服务实例
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

        logger.info("服务管理器初始化完成")

    def start_service(self, service_name: str, config: Dict[str, Any] = None) -> ServiceResult:
        """启动指定服务"""
        try:
            with self._lock:
                # 检查服务是否已在运行
                if self.services_status.get(service_name) == ServiceStatus.RUNNING:
                    return ServiceResult(False, f"{service_name}已在运行中")

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
                elif service_name == 'StrategyService':
                    success = self._start_strategy_service(config)
                else:
                    return ServiceResult(False, f"未知的服务: {service_name}")

                if success:
                    self.services_status[service_name] = ServiceStatus.RUNNING
                    self.services_start_time[service_name] = datetime.now()

                    # 发布服务启动事件
                    if self.event_bus:
                        self.event_bus.publish('service.started', {
                            'service_name': service_name,
                            'start_time': self.services_start_time[service_name].isoformat()
                        })

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

                    # 发布服务停止事件
                    if self.event_bus:
                        self.event_bus.publish('service.stopped', {
                            'service_name': service_name,
                            'stop_time': datetime.now().isoformat()
                        })

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

    def stop_all_services(self):
        """停止所有服务"""
        logger.info("开始停止所有服务...")
        
        # 按相反顺序停止服务
        service_names = ['StrategyService', 'TradingService', 'RiskService', 'AccountService', 'MarketDataService']
        
        for service_name in service_names:
            if self.services_status[service_name] == ServiceStatus.RUNNING:
                result = self.stop_service(service_name, force=True)
                if result.success:
                    logger.info(f"✓ {service_name}已停止")
                else:
                    logger.error(f"✗ {service_name}停止失败: {result.message}")

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
                "dependencies": self.service_dependencies.get(service_name, [])
            }

        except Exception as e:
            logger.error(f"获取服务{service_name}状态失败: {e}")
            return {"error": str(e)}

    def get_all_services_status(self) -> Dict[str, Any]:
        """获取所有服务状态"""
        try:
            services = {}
            for service_name in self.services_status.keys():
                service_info = self.get_service_status(service_name)
                if "error" not in service_info:
                    services[service_name] = service_info

            # 服务统计
            summary = {
                "total": len(self.services_status),
                "running": sum(1 for status in self.services_status.values() if status == ServiceStatus.RUNNING),
                "stopped": sum(1 for status in self.services_status.values() if status == ServiceStatus.STOPPED),
                "error": sum(1 for status in self.services_status.values() if status == ServiceStatus.ERROR)
            }

            return {
                "services": services,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"获取所有服务状态失败: {e}")
            return {"error": str(e)}

    def get_running_services(self) -> List[str]:
        """获取正在运行的服务列表"""
        return [name for name, status in self.services_status.items() 
                if status == ServiceStatus.RUNNING]

    def get_service_instance(self, service_name: str):
        """获取服务实例"""
        return self.services.get(service_name)

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
            'TradingService': '交易服务',
            'StrategyService': '策略服务'
        }
        return display_names.get(service_name, service_name)

    def _start_market_data_service(self, config: Dict[str, Any] = None) -> bool:
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
                config=config or {
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

    def _start_strategy_service(self, config: Dict[str, Any] = None) -> bool:
        """启动策略服务"""
        try:
            # 检查依赖服务
            market_data_service = self.services.get('MarketDataService')
            account_service = self.services.get('AccountService')
            trading_service = self.services.get('TradingService')

            if not market_data_service:
                logger.error("策略服务需要行情服务，但行情服务未启动")
                return False

            if not account_service:
                logger.error("策略服务需要账户服务，但账户服务未启动")
                return False

            if not trading_service:
                logger.error("策略服务需要交易服务，但交易服务未启动")
                return False

            strategy_service = StrategyService(self.event_engine, self.config_manager)

            if strategy_service.start():
                self.services['StrategyService'] = strategy_service
                logger.info("✓ 策略服务启动成功")
                return True
            else:
                logger.warning("⚠ 策略服务启动失败")
                return False

        except Exception as e:
            logger.warning(f"⚠ 策略服务启动异常: {e}")
            return False
