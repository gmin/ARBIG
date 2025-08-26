"""
ARBIG策略执行服务
负责策略的执行、生命周期管理、参数配置等功能
基于vnpy架构设计，支持微服务架构
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

# 导入策略引擎和相关组件
import sys
import os

# 添加当前目录到Python路径以支持相对导入
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from core.strategy_engine import StrategyEngine

# 配置日志 - 先配置日志再使用
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入回测API
try:
    from api.backtest_api import router as backtest_router
    BACKTEST_AVAILABLE = True
    logger.info("专业回测模块加载成功")
except ImportError as e:
    BACKTEST_AVAILABLE = False
    logger.warning(f"专业回测模块加载失败: {e}")
    backtest_router = None

# 导入策略轻量回测API
try:
    from api.strategy_backtest_api import router as strategy_backtest_router
    STRATEGY_BACKTEST_AVAILABLE = True
    logger.info("策略轻量回测模块加载成功")
except ImportError as e:
    STRATEGY_BACKTEST_AVAILABLE = False
    logger.warning(f"策略轻量回测模块加载失败: {e}")
    strategy_backtest_router = None

# 全局策略引擎实例
strategy_engine: Optional[StrategyEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global strategy_engine
    
    # 启动时初始化
    logger.info("ARBIG策略执行服务启动中...")
    
    # 创建策略引擎
    strategy_engine = StrategyEngine(trading_service_url="http://localhost:8001")
    
    # 启动策略引擎
    if strategy_engine.start_engine():
        logger.info("策略执行引擎启动成功")
        
        # 显示已加载的策略类型
        available_strategies = strategy_engine.get_available_strategies()
        logger.info(f"已加载 {len(available_strategies)} 个策略类型:")
        for strategy_type, info in available_strategies.items():
            logger.info(f"  - {strategy_type}: {info['description']}")
    else:
        logger.error("策略执行引擎启动失败")
    
    yield
    
    # 关闭时清理
    logger.info("ARBIG策略执行服务关闭中...")
    if strategy_engine:
        strategy_engine.stop_engine()
    logger.info("策略执行服务关闭完成")

app = FastAPI(
    title="ARBIG策略执行服务",
    description="基于vnpy架构的量化交易策略执行服务",
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册回测API路由
if BACKTEST_AVAILABLE and backtest_router:
    app.include_router(backtest_router)
    logger.info("专业回测API路由注册成功")

# 注册策略轻量回测API路由
if STRATEGY_BACKTEST_AVAILABLE and strategy_backtest_router:
    app.include_router(strategy_backtest_router)
    logger.info("策略轻量回测API路由注册成功")

# 注册交易统计API
try:
    from api.trading_statistics import router as statistics_router
    app.include_router(statistics_router)
    logger.info("交易统计API路由注册成功")
except Exception as e:
    logger.error(f"交易统计API路由注册失败: {e}")

# ==================== API 端点 ====================

@app.get("/")
async def root():
    """根路径"""
    engine_status = strategy_engine.get_engine_status() if strategy_engine else {"running": False}
    return {
        "service": "ARBIG策略执行服务",
        "version": "2.0.0",
        "status": "running",
        "engine_status": engine_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/engine/status")
async def get_engine_status():
    """获取策略引擎状态"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    return {
        "success": True,
        "data": strategy_engine.get_engine_status(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/strategies/types")
async def get_strategy_types():
    """获取所有可用的策略类型"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    available_strategies = strategy_engine.get_available_strategies()
    return {
        "success": True, 
        "data": available_strategies,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/strategies")
async def get_strategies():
    """获取所有策略实例"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    strategies_status = strategy_engine.get_all_strategies_status()
    
    return {
        "success": True,
        "data": strategies_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/strategies/{strategy_name}")
async def get_strategy(strategy_name: str):
    """获取单个策略状态"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    strategy_status = strategy_engine.get_strategy_status(strategy_name)
    if not strategy_status:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    return {
        "success": True,
        "data": strategy_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/{strategy_name}/start")
async def start_strategy(strategy_name: str):
    """启动策略"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    success = strategy_engine.start_strategy(strategy_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"策略 {strategy_name} 启动失败")
    
    return {
        "success": True,
        "message": f"策略 {strategy_name} 启动成功",
        "data": strategy_engine.get_strategy_status(strategy_name),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/{strategy_name}/stop")
async def stop_strategy(strategy_name: str):
    """停止策略"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    success = strategy_engine.stop_strategy(strategy_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"策略 {strategy_name} 停止失败")
    
    return {
        "success": True,
        "message": f"策略 {strategy_name} 停止成功",
        "data": strategy_engine.get_strategy_status(strategy_name),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/{strategy_name}/params")
async def update_strategy_params(strategy_name: str, params: dict):
    """更新策略参数"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    success = strategy_engine.update_strategy_setting(strategy_name, params)
    if not success:
        raise HTTPException(status_code=400, detail=f"策略 {strategy_name} 参数更新失败")
    
    return {
        "success": True,
        "message": f"策略 {strategy_name} 参数更新成功",
        "data": strategy_engine.get_strategy_status(strategy_name),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/register")
async def register_strategy(request: Request):
    """注册新策略"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    try:
        # 从请求体中提取JSON数据
        request_data = await request.json()
        
        strategy_name = request_data.get("strategy_name")
        symbol = request_data.get("symbol") 
        strategy_type = request_data.get("strategy_type", "DoubleMaStrategy")
        params = request_data.get("params", {})
        
        if not strategy_name or not symbol:
            raise HTTPException(status_code=400, detail="缺少必要参数: strategy_name, symbol")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=f"请求数据解析失败: {str(e)}")
    
    # 使用新的策略注册方式
    success = strategy_engine.register_strategy_by_type(
        strategy_type=strategy_type,
        strategy_name=strategy_name,
        symbol=symbol,
        setting=params
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=f"策略 {strategy_name} 注册失败")
    
    return {
        "success": True,
        "message": f"策略 {strategy_name} 注册成功",
        "data": strategy_engine.get_strategy_status(strategy_name),
        "timestamp": datetime.now().isoformat()
    }

@app.delete("/strategies/{strategy_name}")
async def remove_strategy(strategy_name: str):
    """移除策略"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    success = strategy_engine.remove_strategy(strategy_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"策略 {strategy_name} 移除失败")
    
    return {
        "success": True,
        "message": f"策略 {strategy_name} 移除成功",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/trading/status")
async def get_trading_status():
    """获取交易服务状态"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    status = strategy_engine.signal_sender.get_trading_status()
    return {
        "success": True,
        "data": status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/trading/positions")
async def get_positions():
    """获取持仓信息"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    positions = strategy_engine.signal_sender.get_positions()
    return {
        "success": True,
        "data": positions,
        "timestamp": datetime.now().isoformat()
    }

# 性能统计API已移至回测服务

@app.post("/strategies/{strategy_name}/trade")
async def update_strategy_trade(strategy_name: str, trade_data: dict):
    """更新策略交易记录"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    strategy_engine.update_strategy_trade(strategy_name, trade_data)
    return {
        "success": True,
        "message": f"策略 {strategy_name} 交易记录已更新",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/strategies/{strategy_name}/position")
async def update_strategy_position(strategy_name: str, position_data: dict):
    """更新策略持仓"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="策略引擎未初始化")
    
    position = position_data.get("position", 0)
    strategy_engine.update_strategy_position(strategy_name, position)
    return {
        "success": True,
        "message": f"策略 {strategy_name} 持仓已更新",
        "timestamp": datetime.now().isoformat()
    }

# 兼容旧版本API
@app.get("/status")
async def legacy_status():
    """兼容旧版本的状态接口"""
    return await root()

if __name__ == "__main__":
    logger.info("🚀 准备启动uvicorn服务器...")
    logger.info("📍 API端点定义完成，开始启动HTTP服务器")

    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8002,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ uvicorn启动失败: {e}")
        raise
