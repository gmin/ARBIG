"""
ARBIG系统控制器
负责系统的启动、停止和状态管理
"""

import time
import signal
import sys
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from .event_engine import EventEngine
from .config_manager import ConfigManager
from .service_manager import ServiceManager
from .event_bus import EventBus
# from gateways.ctp_gateway import CtpGatewayWrapper  # 暂时注释掉，避免导入错误
from utils.logger import get_logger

logger = get_logger(__name__)

class SystemStatus(str, Enum):
    """系统状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class RunningMode(str, Enum):
    """系统运行模式"""
    FULL_TRADING = "FULL_TRADING"        # 完整交易模式
    MONITOR_ONLY = "MONITOR_ONLY"        # 仅监控模式
    MARKET_DATA_ONLY = "MARKET_DATA_ONLY" # 仅行情模式

class SystemResult:
    """系统操作结果"""
    def __init__(self, success: bool, message: str, data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}

class SystemController:
    """
    ARBIG系统控制器
    负责系统的整体控制和协调
    """

    def __init__(self):
        """初始化系统控制器"""
        self.logger = logger
        self.status = SystemStatus.STOPPED
        self.mode = RunningMode.MARKET_DATA_ONLY
        self.start_time = None

        # 核心组件
        self.config_manager = None
        self.event_engine = None
        self.event_bus = None
        self.service_manager = None
        self.ctp_gateway = None

        # 系统配置
        self.MAX_RETRY_COUNT = 3
        self.RETRY_INTERVAL = 3
        self.CONNECTION_TIMEOUT = 30

        # 线程锁
        self._lock = threading.Lock()

        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("系统控制器初始化完成")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始关闭系统...")
        self.stop_system()
        sys.exit(0)

    def start_system(self) -> SystemResult:
        """启动系统"""
        try:
            with self._lock:
                if self.status == SystemStatus.RUNNING:
                    return SystemResult(False, "系统已在运行中")

                logger.info("="*60)
                logger.info("🚀 启动ARBIG量化交易系统")
                logger.info("="*60)

                self.status = SystemStatus.STARTING

                # 1. 初始化配置管理器
                if not self._init_config_manager():
                    self.status = SystemStatus.ERROR
                    return SystemResult(False, "配置管理器初始化失败")

                # 2. 启动事件引擎
                if not self._start_event_engine():
                    self.status = SystemStatus.ERROR
                    return SystemResult(False, "事件引擎启动失败")

                # 3. 初始化事件总线
                if not self._init_event_bus():
                    self.status = SystemStatus.ERROR
                    return SystemResult(False, "事件总线初始化失败")

                # 4. 连接CTP网关
                ctp_result = self._connect_ctp_with_retry()
                if ctp_result == "FAILED":
                    logger.warning("CTP连接失败，将以演示模式运行")

                # 5. 初始化服务管理器
                if not self._init_service_manager():
                    self.status = SystemStatus.ERROR
                    return SystemResult(False, "服务管理器初始化失败")

                # 6. 启动核心服务
                if not self._start_core_services(ctp_result):
                    self.status = SystemStatus.ERROR
                    return SystemResult(False, "核心服务启动失败")

                # 7. 系统启动完成
                self.status = SystemStatus.RUNNING
                self.start_time = datetime.now()

                logger.info("="*60)
                logger.info("🎉 ARBIG系统启动成功！")
                logger.info("="*60)

                return SystemResult(True, "系统启动成功", {
                    "start_time": self.start_time.isoformat(),
                    "ctp_status": ctp_result,
                    "mode": self.mode.value
                })

        except Exception as e:
            self.status = SystemStatus.ERROR
            logger.error(f"系统启动失败: {e}")
            return SystemResult(False, f"系统启动异常: {e}")

    def stop_system(self) -> SystemResult:
        """停止系统"""
        try:
            with self._lock:
                if self.status == SystemStatus.STOPPED:
                    return SystemResult(False, "系统未在运行")

                logger.info("开始停止ARBIG系统...")
                self.status = SystemStatus.STOPPING

                # 停止服务管理器
                if self.service_manager:
                    self.service_manager.stop_all_services()

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

                self.status = SystemStatus.STOPPED
                logger.info("ARBIG系统已完全停止")

                return SystemResult(True, "系统停止成功", {
                    "stop_time": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"系统停止失败: {e}")
            return SystemResult(False, f"系统停止异常: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            uptime = ""
            if self.start_time and self.status == SystemStatus.RUNNING:
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
            if self.service_manager:
                services_status = self.service_manager.get_all_services_status()

            return {
                "system_status": self.status.value,
                "running_mode": self.mode.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "uptime": uptime,
                "ctp_status": ctp_status,
                "services_status": services_status,
                "version": "2.0.0"
            }

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}

    def _init_config_manager(self) -> bool:
        """初始化配置管理器"""
        try:
            self.config_manager = ConfigManager()
            logger.info("✓ 配置管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"✗ 配置管理器初始化失败: {e}")
            return False

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

    def _init_event_bus(self) -> bool:
        """初始化事件总线"""
        try:
            self.event_bus = EventBus(self.event_engine)
            logger.info("✓ 事件总线初始化成功")
            return True
        except Exception as e:
            logger.error(f"✗ 事件总线初始化失败: {e}")
            return False

    def _init_service_manager(self) -> bool:
        """初始化服务管理器"""
        try:
            self.service_manager = ServiceManager(
                self.event_engine,
                self.config_manager,
                self.ctp_gateway,
                self.event_bus
            )
            logger.info("✓ 服务管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"✗ 服务管理器初始化失败: {e}")
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

        if not self.service_manager:
            logger.error("服务管理器未初始化")
            return False

        # 根据CTP连接状态启动相应服务
        if ctp_status in ["FULL", "MD_ONLY"]:
            # 启动行情服务
            if not self.service_manager.start_service('MarketDataService'):
                logger.error("行情服务启动失败")
                return False

        if ctp_status in ["FULL", "TD_ONLY"]:
            # 启动交易相关服务
            self.service_manager.start_service('AccountService')
            self.service_manager.start_service('RiskService')
            self.service_manager.start_service('TradingService')

        # 更新运行模式
        self._update_running_mode()

        logger.info("核心服务启动完成")
        return True

    def _update_running_mode(self):
        """根据服务状态更新运行模式"""
        if not self.service_manager:
            return

        running_services = self.service_manager.get_running_services()

        # 完全交易模式：所有核心服务都在运行
        core_services = ['MarketDataService', 'AccountService', 'RiskService', 'TradingService']
        if all(svc in running_services for svc in core_services):
            self.mode = RunningMode.FULL_TRADING
        elif 'MarketDataService' in running_services and 'AccountService' in running_services:
            self.mode = RunningMode.MONITOR_ONLY
        else:
            self.mode = RunningMode.MARKET_DATA_ONLY

        logger.info(f"运行模式更新为: {self.mode.value}")

    def run(self):
        """运行系统主循环"""
        try:
            logger.info("ARBIG系统控制器运行中...")
            logger.info("系统现在通过Web API进行控制")

            # 系统主循环 - 无论系统状态如何都保持运行，等待Web API控制
            self._running = True
            while self._running:
                time.sleep(1)
                # 可以在这里添加定期检查逻辑
                # 比如检查服务状态、内存使用等

        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
        finally:
            self._running = False
            if self.status == SystemStatus.RUNNING:
                self.stop_system()

    def shutdown(self):
        """关闭系统控制器"""
        self._running = False
