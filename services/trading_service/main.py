#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG核心交易服务
微服务架构 - 核心交易业务逻辑
"""

import sys
import os
import argparse
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid

from shared.models.base import (
    APIResponse, HealthCheckResponse, SystemInfo, SystemStatus, 
    RunningMode, ServiceInfo, ServiceStatus
)
from core.system_controller import SystemController
from core.service_manager import ServiceManager
from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)

class TradingService:
    """核心交易服务"""
    
    def __init__(self):
        """初始化交易服务"""
        self.service_name = "trading_service"
        self.version = "2.0.0"
        self.start_time = datetime.now()
        
        # 核心组件
        self.system_controller = SystemController()
        self.running = False
        
        logger.info("核心交易服务初始化完成")
    
    def start(self) -> bool:
        """启动交易服务"""
        try:
            logger.info("启动核心交易服务...")
            self.running = True
            logger.info("✅ 核心交易服务启动成功")
            return True
        except Exception as e:
            logger.error(f"启动核心交易服务失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止交易服务"""
        try:
            logger.info("停止核心交易服务...")
            if self.system_controller.status.value == "running":
                self.system_controller.stop_system()
            self.running = False
            logger.info("✅ 核心交易服务已停止")
            return True
        except Exception as e:
            logger.error(f"停止核心交易服务失败: {e}")
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
            "system_status": self.system_controller.status.value,
            "system_mode": self.system_controller.mode.value
        }

# 创建交易服务实例
trading_service = TradingService()

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG核心交易服务",
    description="ARBIG量化交易系统的核心交易服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册交易操作API路由
try:
    from api.trading_operations import router as trading_operations_router
    app.include_router(trading_operations_router)
    logger.info("✅ 交易操作API路由注册成功")
except ImportError as e:
    logger.warning(f"⚠️ 交易操作API路由导入失败: {e}")

# 导入并注册行情数据API路由
try:
    from services.trading_service.api.market_data import router as market_data_router
    app.include_router(market_data_router)
    logger.info("✅ 行情数据API路由注册成功")
except ImportError as e:
    logger.warning(f"⚠️ 行情数据API路由导入失败: {e}")

# 导入并注册真实交易API路由
try:
    from services.trading_service.api.real_trading import router as real_trading_router
    app.include_router(real_trading_router)
    logger.info("✅ 真实交易API路由注册成功")
except ImportError as e:
    logger.warning(f"⚠️ 真实交易API路由导入失败: {e}")

# 导入并注册交易日志API路由
try:
    from services.trading_service.api.trading_logs import router as trading_logs_router
    app.include_router(trading_logs_router, prefix="/trading_logs")
    logger.info("✅ 交易日志API路由注册成功")
except ImportError as e:
    logger.warning(f"⚠️ 交易日志API路由导入失败: {e}")

@app.on_event("startup")
async def startup_event():
    """服务启动事件"""
    logger.info("🚀 启动核心交易服务...")

    # 初始化MySQL数据库连接（Redis已完全移除）
    try:
        from shared.database.connection import db_manager
        import json

        # 加载数据库配置
        config_file = project_root / "config" / "database.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                db_config = json.load(f)

            mysql_config = db_config['mysql']
            # Redis已完全移除，不再需要

            # 只初始化MySQL
            success = await db_manager.init_mysql(mysql_config)
            if success:
                logger.info("✅ MySQL数据库连接初始化成功（Redis已移除）")
            else:
                logger.error("❌ MySQL数据库连接初始化失败")
        else:
            logger.warning("⚠️ 数据库配置文件不存在，跳过数据库初始化")

    except Exception as e:
        logger.error(f"❌ 数据库初始化异常: {e}")

    # 初始化行情数据管理器（轻量级API转换层）
    try:
        from services.trading_service.core.market_data_manager import get_market_data_manager
        from services.trading_service.core.ctp_integration import get_ctp_integration

        market_manager = get_market_data_manager()
        ctp_integration = get_ctp_integration()
        market_manager.set_ctp_integration(ctp_integration)
        logger.info("✅ 行情数据管理器初始化成功（轻量级API转换层）")
    except Exception as e:
        logger.error(f"❌ 行情数据管理器初始化失败: {e}")

    # 启动CTP集成
    try:
        from services.trading_service.core.ctp_integration import get_ctp_integration
        ctp_integration = get_ctp_integration()

        # 初始化CTP
        if await ctp_integration.initialize():
            logger.info("✅ CTP集成初始化成功")

            # 连接CTP服务器
            if await ctp_integration.connect():
                logger.info("✅ CTP服务器连接成功")
            else:
                logger.warning("⚠️ CTP服务器连接失败，将使用模拟数据")
        else:
            logger.warning("⚠️ CTP集成初始化失败，将使用模拟数据")
    except Exception as e:
        logger.error(f"❌ CTP集成启动失败: {e}")

    # 启动统一策略管理器
    try:
        from services.trading_service.core.unified_strategy_manager import get_unified_strategy_manager
        strategy_manager = get_unified_strategy_manager()
        await strategy_manager.initialize()
        logger.info("✅ 统一策略管理器启动成功")
    except Exception as e:
        logger.error(f"❌ 统一策略管理器启动失败: {e}")

    trading_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭事件"""
    logger.info("⏹️ 关闭核心交易服务...")

    # 停止统一策略管理器
    try:
        from services.trading_service.core.unified_strategy_manager import get_unified_strategy_manager
        strategy_manager = get_unified_strategy_manager()
        await strategy_manager.shutdown()
        logger.info("✅ 统一策略管理器已停止")
    except Exception as e:
        logger.error(f"❌ 停止统一策略管理器失败: {e}")

    # 停止CTP集成
    try:
        from services.trading_service.core.ctp_integration import get_ctp_integration
        ctp_integration = get_ctp_integration()
        await ctp_integration.disconnect()
        logger.info("✅ CTP集成已停止")
    except Exception as e:
        logger.error(f"❌ 停止CTP集成失败: {e}")

    # 行情数据管理器无需停止（轻量级API转换层）
    logger.info("✅ 行情数据管理器已清理（轻量级API转换层）")

    trading_service.stop()

@app.get("/health", response_model=HealthCheckResponse, summary="健康检查")
async def health_check():
    """健康检查端点"""
    status = trading_service.get_status()
    
    return HealthCheckResponse(
        status="healthy" if trading_service.running else "unhealthy",
        timestamp=datetime.now(),
        uptime=status["uptime"],
        version=status["version"],
        dependencies={
            "system_controller": status["system_status"],
            "config_manager": "healthy",
            "event_engine": "healthy"
        }
    )

@app.get("/status", response_model=APIResponse, summary="获取服务状态")
async def get_service_status():
    """获取服务详细状态"""
    try:
        status = trading_service.get_status()
        return APIResponse(
            success=True,
            message="服务状态获取成功",
            data=status,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取服务状态失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.post("/system/start", response_model=APIResponse, summary="启动交易系统")
async def start_trading_system():
    """启动交易系统"""
    try:
        result = trading_service.system_controller.start_system()
        return APIResponse(
            success=result.success,
            message=result.message,
            data=result.data,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"启动交易系统失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.post("/system/stop", response_model=APIResponse, summary="停止交易系统")
async def stop_trading_system():
    """停止交易系统"""
    try:
        result = trading_service.system_controller.stop_system()
        return APIResponse(
            success=result.success,
            message=result.message,
            data=result.data,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"停止交易系统失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.get("/system/status", response_model=APIResponse, summary="获取交易系统状态")
async def get_trading_system_status():
    """获取交易系统状态"""
    try:
        status = trading_service.system_controller.get_system_status()
        return APIResponse(
            success=True,
            message="交易系统状态获取成功",
            data=status,
            request_id=str(uuid.uuid4())
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取交易系统状态失败: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@app.get("/", summary="服务信息")
async def root():
    """服务根端点"""
    return {
        "service": "ARBIG核心交易服务",
        "version": "2.0.0",
        "status": "running" if trading_service.running else "stopped",
        "docs": "/docs",
        "health": "/health"
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG核心交易服务')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8001,
                       help='服务器端口')
    parser.add_argument('--reload', action='store_true',
                       help='开发模式：自动重载')
    parser.add_argument('--log-level', type=str, default='info',
                       choices=['debug', 'info', 'warning', 'error'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("🏛️  ARBIG核心交易服务 v2.0")
    logger.info("🔄 微服务架构 - 核心交易业务")
    logger.info("="*60)
    
    try:
        logger.info(f"🚀 启动服务器: http://{args.host}:{args.port}")
        
        uvicorn.run(
            "services.trading_service.main:app",
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
