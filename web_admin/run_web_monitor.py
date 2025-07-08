#!/usr/bin/env python3
"""
ARBIG Web监控服务启动脚本
可以独立运行，也可以与核心交易系统集成运行
"""

import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_monitor.app import web_app, run_web_service
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

class TradingSystemManager:
    """交易系统管理器"""
    
    def __init__(self):
        """初始化交易系统"""
        self.event_engine = None
        self.config_manager = None
        self.ctp_gateway = None
        self.market_data_service = None
        self.account_service = None
        self.trading_service = None
        self.risk_service = None
        
        self.running = False
    
    def initialize(self) -> bool:
        """初始化所有组件"""
        try:
            logger.info("初始化ARBIG交易系统...")
            
            # 创建事件引擎
            self.event_engine = EventEngine()
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            
            # 创建配置管理器
            self.config_manager = ConfigManager()
            logger.info("✓ 配置管理器创建成功")
            
            # 创建CTP网关
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            logger.info("✓ CTP网关创建成功")
            
            # 连接CTP
            logger.info("正在连接CTP服务器...")
            if not self.ctp_gateway.connect():
                logger.error("✗ CTP连接失败")
                return False
            logger.info("✓ CTP连接成功")
            
            # 创建服务组件
            self._create_services()
            
            # 启动服务
            self._start_services()
            
            self.running = True
            logger.info("✓ ARBIG交易系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 交易系统初始化失败: {e}")
            return False
    
    def _create_services(self):
        """创建所有服务"""
        # 行情服务
        market_config = ServiceConfig(
            name="market_data",
            enabled=True,
            config={
                'symbols': ['au2509', 'au2512', 'au2601'],
                'cache_size': 1000
            }
        )
        self.market_data_service = MarketDataService(
            self.event_engine, market_config, self.ctp_gateway
        )
        
        # 账户服务
        account_config = ServiceConfig(
            name="account",
            enabled=True,
            config={
                'update_interval': 30,
                'position_sync': True,
                'auto_query_after_trade': True
            }
        )
        self.account_service = AccountService(
            self.event_engine, account_config, self.ctp_gateway
        )
        
        # 风控服务
        risk_config = ServiceConfig(
            name="risk",
            enabled=True,
            config={
                'max_position_ratio': 0.8,
                'max_daily_loss': 50000,
                'max_single_order_volume': 10
            }
        )
        self.risk_service = RiskService(
            self.event_engine, risk_config, self.account_service
        )
        
        # 交易服务
        trading_config = ServiceConfig(
            name="trading",
            enabled=True,
            config={
                'order_timeout': 30,
                'max_orders_per_second': 5
            }
        )
        self.trading_service = TradingService(
            self.event_engine, trading_config, self.ctp_gateway,
            self.account_service, self.risk_service
        )
        
        logger.info("✓ 所有服务组件创建完成")
    
    def _start_services(self):
        """启动所有服务"""
        services = [
            ("行情服务", self.market_data_service),
            ("账户服务", self.account_service),
            ("风控服务", self.risk_service),
            ("交易服务", self.trading_service)
        ]
        
        for name, service in services:
            if service.start():
                logger.info(f"✓ {name}启动成功")
            else:
                logger.error(f"✗ {name}启动失败")
                raise Exception(f"{name}启动失败")
    
    def stop(self):
        """停止所有服务"""
        try:
            logger.info("正在停止ARBIG交易系统...")
            
            services = [
                ("交易服务", self.trading_service),
                ("风控服务", self.risk_service),
                ("账户服务", self.account_service),
                ("行情服务", self.market_data_service)
            ]
            
            for name, service in services:
                if service:
                    service.stop()
                    logger.info(f"✓ {name}已停止")
            
            if self.ctp_gateway:
                self.ctp_gateway.disconnect()
                logger.info("✓ CTP连接已断开")
            
            if self.event_engine:
                self.event_engine.stop()
                logger.info("✓ 事件引擎已停止")
            
            self.running = False
            logger.info("✓ ARBIG交易系统已停止")
            
        except Exception as e:
            logger.error(f"停止交易系统失败: {e}")

def run_standalone_web_service():
    """运行独立的Web服务（不连接交易系统）"""
    logger.info("启动独立Web监控服务...")
    logger.warning("注意: 独立模式下无法连接到交易系统，仅提供界面预览")
    
    # 直接运行Web服务
    run_web_service(host="0.0.0.0", port=8000)

def run_integrated_service():
    """运行集成的Web服务（连接交易系统）"""
    logger.info("启动集成Web监控服务...")
    
    # 创建交易系统管理器
    trading_system = TradingSystemManager()
    
    try:
        # 初始化交易系统
        if not trading_system.initialize():
            logger.error("交易系统初始化失败，退出")
            return
        
        # 连接Web服务到交易系统
        if not web_app.connect_services(trading_system):
            logger.error("Web服务连接交易系统失败")
            return
        
        logger.info("✓ Web监控服务已连接到交易系统")
        
        # 在单独线程中运行Web服务
        web_thread = threading.Thread(
            target=run_web_service,
            kwargs={"host": "0.0.0.0", "port": 8000},
            daemon=True
        )
        web_thread.start()
        
        logger.info("🌐 Web监控服务已启动: http://localhost:8000")
        logger.info("按 Ctrl+C 退出")
        
        # 主线程保持运行
        try:
            while trading_system.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到退出信号...")
        
    except Exception as e:
        logger.error(f"运行过程中出错: {e}")
    
    finally:
        # 清理资源
        trading_system.stop()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ARBIG Web监控服务")
    parser.add_argument(
        "--mode",
        choices=["standalone", "integrated"],
        default="integrated",
        help="运行模式: standalone(独立) 或 integrated(集成)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Web服务监听地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web服务监听端口"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("ARBIG Web监控与风控系统")
    logger.info("="*60)
    logger.info(f"运行模式: {args.mode}")
    logger.info(f"监听地址: {args.host}:{args.port}")
    
    if args.mode == "standalone":
        run_standalone_web_service()
    else:
        run_integrated_service()

if __name__ == "__main__":
    main()
