"""
回测API接口
提供HTTP API进行策略回测和结果查询
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from services.strategy_service.backtesting.backtest_manager import BacktestManager, quick_backtest
from utils.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/backtest", tags=["回测"])

# 全局回测管理器
backtest_manager = BacktestManager()


# 请求模型
class BacktestRequest(BaseModel):
    """回测请求模型"""
    strategy_name: str = Field(..., description="策略名称")
    strategy_setting: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    capital: Optional[int] = Field(1000000, description="初始资金")
    rate: Optional[float] = Field(0.0002, description="手续费率")
    slippage: Optional[float] = Field(0.2, description="滑点")


class BatchBacktestRequest(BaseModel):
    """批量回测请求模型"""
    strategies: List[Dict[str, Any]] = Field(..., description="策略配置列表")
    backtest_setting: Optional[Dict[str, Any]] = Field(default_factory=dict, description="回测设置")


class QuickBacktestRequest(BaseModel):
    """快速回测请求模型"""
    strategy_name: str = Field(..., description="策略名称")
    strategy_setting: Optional[Dict[str, Any]] = Field(default_factory=dict, description="策略参数")
    days: Optional[int] = Field(30, description="回测天数")


class OptimizationRequest(BaseModel):
    """参数优化请求模型"""
    strategy_name: str = Field(..., description="策略名称")
    optimization_setting: Dict[str, Any] = Field(..., description="优化参数设置")
    target_name: Optional[str] = Field("sharpe_ratio", description="优化目标")


# API接口
@router.get("/strategies")
async def get_available_strategies():
    """获取可用的策略列表"""
    try:
        strategies = backtest_manager.get_available_strategies()
        return {
            "success": True,
            "data": {
                "strategies": strategies,
                "count": len(strategies)
            },
            "message": "获取策略列表成功"
        }
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")


@router.post("/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """运行单个策略回测"""
    try:
        logger.info(f"收到回测请求: {request.strategy_name}")
        
        # 构建回测设置
        backtest_setting = {
            "capital": request.capital,
            "rate": request.rate,
            "slippage": request.slippage
        }
        
        # 处理日期
        if request.start_date:
            backtest_setting["start_date"] = datetime.strptime(request.start_date, "%Y-%m-%d")
        if request.end_date:
            backtest_setting["end_date"] = datetime.strptime(request.end_date, "%Y-%m-%d")
        
        # 运行回测
        result = await backtest_manager.run_single_backtest(
            strategy_name=request.strategy_name,
            strategy_setting=request.strategy_setting,
            backtest_setting=backtest_setting
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result,
            "message": "回测完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")


@router.post("/quick")
async def run_quick_backtest(request: QuickBacktestRequest):
    """快速回测 - 使用最近N天数据"""
    try:
        logger.info(f"收到快速回测请求: {request.strategy_name}, {request.days}天")
        
        result = await quick_backtest(
            strategy_name=request.strategy_name,
            strategy_setting=request.strategy_setting,
            days=request.days
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result,
            "message": f"快速回测完成 ({request.days}天)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"快速回测失败: {str(e)}")


@router.post("/batch")
async def run_batch_backtest(request: BatchBacktestRequest):
    """批量回测多个策略"""
    try:
        logger.info(f"收到批量回测请求: {len(request.strategies)}个策略")
        
        # 构建策略配置
        strategies_config = []
        for strategy_config in request.strategies:
            if "strategy_name" not in strategy_config:
                raise HTTPException(status_code=400, detail="策略配置缺少strategy_name")
            
            strategies_config.append({
                "strategy_name": strategy_config["strategy_name"],
                "strategy_setting": strategy_config.get("strategy_setting", {})
            })
        
        # 处理回测设置中的日期
        backtest_setting = request.backtest_setting.copy()
        if "start_date" in backtest_setting and isinstance(backtest_setting["start_date"], str):
            backtest_setting["start_date"] = datetime.strptime(backtest_setting["start_date"], "%Y-%m-%d")
        if "end_date" in backtest_setting and isinstance(backtest_setting["end_date"], str):
            backtest_setting["end_date"] = datetime.strptime(backtest_setting["end_date"], "%Y-%m-%d")
        
        # 运行批量回测
        result = await backtest_manager.run_batch_backtest(
            strategies_config=strategies_config,
            backtest_setting=backtest_setting
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result,
            "message": "批量回测完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量回测失败: {str(e)}")


@router.post("/optimize")
async def optimize_parameters(request: OptimizationRequest):
    """参数优化"""
    try:
        logger.info(f"收到参数优化请求: {request.strategy_name}")
        
        result = await backtest_manager.optimize_strategy_parameters(
            strategy_name=request.strategy_name,
            optimization_config={
                "optimization_setting": request.optimization_setting,
                "target_name": request.target_name
            }
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result,
            "message": "参数优化完成"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"参数优化失败: {e}")
        raise HTTPException(status_code=500, detail=f"参数优化失败: {str(e)}")


@router.get("/results")
async def get_backtest_results(strategy_name: Optional[str] = None):
    """获取回测结果"""
    try:
        results = backtest_manager.get_backtest_results(strategy_name)
        
        return {
            "success": True,
            "data": {
                "results": results,
                "count": len(results)
            },
            "message": "获取回测结果成功"
        }
        
    except Exception as e:
        logger.error(f"获取回测结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取回测结果失败: {str(e)}")


@router.get("/results/{result_key}/report")
async def get_backtest_report(result_key: str):
    """获取回测报告"""
    try:
        report = backtest_manager.generate_report(result_key)
        
        return {
            "success": True,
            "data": {
                "report": report,
                "result_key": result_key
            },
            "message": "获取回测报告成功"
        }
        
    except Exception as e:
        logger.error(f"获取回测报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取回测报告失败: {str(e)}")


@router.post("/results/save")
async def save_backtest_results(filename: Optional[str] = None):
    """保存回测结果到文件"""
    try:
        backtest_manager.save_results(filename)
        
        return {
            "success": True,
            "message": f"回测结果已保存: {filename or '默认文件名'}"
        }
        
    except Exception as e:
        logger.error(f"保存回测结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存回测结果失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        strategies_count = len(backtest_manager.get_available_strategies())
        results_count = len(backtest_manager.get_backtest_results())
        
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "strategies_count": strategies_count,
                "results_count": results_count,
                "timestamp": datetime.now().isoformat()
            },
            "message": "回测服务运行正常"
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


# 示例配置
@router.get("/examples")
async def get_examples():
    """获取回测配置示例"""
    examples = {
        "single_backtest": {
            "strategy_name": "LargeOrderFollowing",
            "strategy_setting": {
                "large_order_threshold": 3.0,
                "jump_threshold": 0.0008,
                "max_position": 10
            },
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "capital": 1000000
        },
        "batch_backtest": {
            "strategies": [
                {
                    "strategy_name": "LargeOrderFollowing",
                    "strategy_setting": {"max_position": 10}
                },
                {
                    "strategy_name": "VWAPDeviationReversion", 
                    "strategy_setting": {"max_position": 8}
                }
            ],
            "backtest_setting": {
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "capital": 1000000
            }
        },
        "optimization": {
            "strategy_name": "LargeOrderFollowing",
            "optimization_setting": {
                "large_order_threshold": [2.0, 3.0, 4.0],
                "jump_threshold": [0.0005, 0.0008, 0.001]
            },
            "target_name": "sharpe_ratio"
        }
    }
    
    return {
        "success": True,
        "data": examples,
        "message": "回测配置示例"
    }
