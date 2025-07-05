"""
策略管理API路由
提供策略切换、配置和监控接口
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid
from datetime import datetime

from ..models.requests import StrategyControlRequest, StrategySwitchRequest
from ..models.responses import (
    APIResponse, StrategyStatusResponse, StrategyListResponse,
    StrategyInfo, CurrentStrategyInfo, StrategyStatistics
)
from ..dependencies import get_strategy_manager

router = APIRouter(prefix="/api/v1/strategies", tags=["策略管理"])

@router.get("/list", response_model=StrategyListResponse, summary="获取策略列表")
async def get_strategies_list(strategy_manager=Depends(get_strategy_manager)):
    """获取所有可用策略的列表"""
    try:
        strategies = [
            StrategyInfo(
                name="spread_arbitrage",
                display_name="套利策略",
                description="黄金期货跨期套利策略",
                version="1.0.0",
                risk_level="medium",
                status="available",
                author="ARBIG Team"
            ),
            StrategyInfo(
                name="trend_following",
                display_name="趋势跟踪策略",
                description="基于技术指标的趋势跟踪",
                version="1.2.0",
                risk_level="high",
                status="available",
                author="ARBIG Team"
            ),
            StrategyInfo(
                name="high_frequency",
                display_name="高频策略",
                description="高频交易策略",
                version="0.9.0",
                risk_level="very_high",
                status="available",
                author="ARBIG Team"
            )
        ]
        
        return StrategyListResponse(
            success=True,
            message="策略列表获取成功",
            data={"strategies": strategies},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取策略列表失败: {str(e)}"
        )

@router.get("/current", response_model=StrategyStatusResponse, summary="获取当前策略")
async def get_current_strategy(strategy_manager=Depends(get_strategy_manager)):
    """获取当前运行的策略信息"""
    try:
        # 模拟当前策略数据
        current_strategy = CurrentStrategyInfo(
            strategy_name="spread_arbitrage",
            display_name="套利策略",
            status="running",
            start_time=datetime.now(),
            runtime="2h 30m 15s",
            statistics=StrategyStatistics(
                signals_generated=45,
                orders_executed=28,
                successful_trades=18,
                failed_trades=2,
                current_profit=12500.00,
                today_profit=8500.00,
                win_rate=0.685,
                sharpe_ratio=1.85,
                max_drawdown=-0.12
            )
        )
        
        return StrategyStatusResponse(
            success=True,
            message="当前策略信息获取成功",
            data=current_strategy,
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取当前策略失败: {str(e)}"
        )

@router.post("/switch", response_model=APIResponse, summary="切换策略")
async def switch_strategy(
    request: StrategySwitchRequest,
    strategy_manager=Depends(get_strategy_manager)
):
    """切换到新的策略"""
    try:
        # 这里暂时返回成功响应，后续会实现实际的策略切换逻辑
        return APIResponse(
            success=True,
            message=f"策略已切换至 {request.to_strategy}",
            data={
                "switch_id": f"switch_{uuid.uuid4().hex[:8]}",
                "from_strategy": request.from_strategy,
                "to_strategy": request.to_strategy,
                "switch_time": datetime.now().isoformat(),
                "switch_mode": request.switch_mode,
                "reason": request.reason,
                "status": "completed"
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"策略切换失败: {str(e)}"
        )

@router.post("/pause", response_model=APIResponse, summary="暂停策略")
async def pause_strategy(strategy_manager=Depends(get_strategy_manager)):
    """暂停当前运行的策略"""
    try:
        return APIResponse(
            success=True,
            message="策略已暂停",
            data={
                "action": "pause",
                "timestamp": datetime.now().isoformat()
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"暂停策略失败: {str(e)}"
        )

@router.post("/resume", response_model=APIResponse, summary="恢复策略")
async def resume_strategy(strategy_manager=Depends(get_strategy_manager)):
    """恢复暂停的策略"""
    try:
        return APIResponse(
            success=True,
            message="策略已恢复",
            data={
                "action": "resume",
                "timestamp": datetime.now().isoformat()
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"恢复策略失败: {str(e)}"
        )
