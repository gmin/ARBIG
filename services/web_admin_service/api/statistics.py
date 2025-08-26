"""
交易统计API代理
代理到strategy_service的统计接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime

from shared.utils.service_client import ServiceClient
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/statistics", tags=["交易统计"])

# 依赖注入
async def get_strategy_service_client():
    """获取策略服务客户端"""
    return ServiceClient("strategy_service", "http://localhost:8002")

@router.get("/overview")
async def get_trading_overview(service_client: ServiceClient = Depends(get_strategy_service_client)):
    """获取交易总览统计"""
    try:
        response = await service_client.get("/statistics/overview")
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取交易总览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易总览失败: {str(e)}")

@router.get("/strategy/{strategy_name}")
async def get_strategy_statistics(strategy_name: str, service_client: ServiceClient = Depends(get_strategy_service_client)):
    """获取指定策略的详细统计"""
    try:
        response = await service_client.get(f"/statistics/strategy/{strategy_name}")
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略统计失败: {str(e)}")

@router.get("/daily")
async def get_daily_statistics(
    strategy_name: Optional[str] = Query(None, description="策略名称，不指定则返回所有策略"),
    days: int = Query(30, description="统计天数", ge=1, le=365),
    service_client: ServiceClient = Depends(get_strategy_service_client)
):
    """获取日度统计数据"""
    try:
        params = {"days": days}
        if strategy_name:
            params["strategy_name"] = strategy_name

        response = await service_client.get("/statistics/daily", params=params)
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日度统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取日度统计失败: {str(e)}")

@router.get("/performance/ranking")
async def get_performance_ranking(service_client: ServiceClient = Depends(get_strategy_service_client)):
    """获取策略性能排名"""
    try:
        response = await service_client.get("/statistics/performance/ranking")
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取性能排名失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能排名失败: {str(e)}")

@router.get("/realtime")
async def get_realtime_statistics(service_client: ServiceClient = Depends(get_strategy_service_client)):
    """获取实时统计数据"""
    try:
        response = await service_client.get("/statistics/realtime")
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时统计失败: {str(e)}")

@router.get("/signals/{strategy_name}")
async def get_strategy_signals(
    strategy_name: str,
    limit: int = Query(20, description="返回信号数量", ge=1, le=100),
    service_client: ServiceClient = Depends(get_strategy_service_client)
):
    """获取策略的信号触发历史"""
    try:
        params = {"limit": limit}
        response = await service_client.get(f"/statistics/signals/{strategy_name}", params=params)
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略信号失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略信号失败: {str(e)}")

@router.get("/signals/{strategy_name}/analysis")
async def get_signal_analysis(strategy_name: str, service_client: ServiceClient = Depends(get_strategy_service_client)):
    """获取策略信号分析报告"""
    try:
        response = await service_client.get(f"/statistics/signals/{strategy_name}/analysis")
        if response.success:
            return response.data
        else:
            raise HTTPException(status_code=500, detail=response.message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取信号分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取信号分析失败: {str(e)}")
