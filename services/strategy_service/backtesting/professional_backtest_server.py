#!/usr/bin/env python3
"""
专业回测服务器
独立运行的专业回测服务，提供完整的回测、优化、分析功能
"""

from fastapi import FastAPI
import uvicorn
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

try:
    # 修复导入路径
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from api.backtest_api import router as backtest_router
    BACKTEST_AVAILABLE = True
    print("✅ 回测模块导入成功")
except ImportError as e:
    print(f"⚠️ 回测模块导入失败: {e}")
    BACKTEST_AVAILABLE = False
    backtest_router = None

from utils.logger import get_logger

logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG专业回测服务",
    description="独立的专业回测服务，提供策略回测、参数优化、性能分析等功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 注册回测API路由
if BACKTEST_AVAILABLE and backtest_router:
    app.include_router(backtest_router)
    logger.info("专业回测API路由注册成功")

# 添加策略同步接口
@app.post("/strategies/sync")
async def sync_strategy(sync_data: dict):
    """接收策略同步数据"""
    try:
        strategy_id = sync_data.get("strategy_id")
        strategy_info = sync_data.get("strategy_info")
        
        logger.info(f"接收到策略同步: {strategy_id}")
        
        # 这里可以将策略信息存储到本地数据库
        # 暂时只记录日志
        
        return {
            "success": True,
            "message": f"策略 {strategy_id} 同步成功",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"策略同步失败: {e}")
        return {
            "success": False,
            "message": f"策略同步失败: {str(e)}"
        }

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "ARBIG专业回测服务",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "策略回测",
            "参数优化", 
            "性能分析",
            "批量回测",
            "历史数据管理"
        ],
        "endpoints": {
            "health": "/backtest/health",
            "strategies": "/backtest/strategies",
            "quick_backtest": "/backtest/quick",
            "comprehensive_backtest": "/backtest/run",
            "batch_backtest": "/backtest/batch",
            "optimization": "/backtest/optimize",
            "results": "/backtest/results"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "professional_backtest",
        "timestamp": datetime.now().isoformat(),
        "backtest_engine": "available" if BACKTEST_AVAILABLE else "unavailable"
    }

if __name__ == "__main__":
    print("🚀 启动ARBIG专业回测服务...")
    print("=" * 50)
    print("📍 服务地址: http://localhost:8003")
    print("📍 API文档: http://localhost:8003/docs")
    print("📍 健康检查: http://localhost:8003/health")
    print("📍 回测健康: http://localhost:8003/backtest/health")
    print("=" * 50)
    
    if not BACKTEST_AVAILABLE:
        print("⚠️ 回测模块不可用，服务功能受限")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info",
            reload=False
        )
    except Exception as e:
        print(f"❌ 专业回测服务启动失败: {e}")
        logger.error(f"专业回测服务启动失败: {e}")
