"""
交易日志API接口
基于文件日志提供交易日志查询和统计功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from utils.trading_logger import get_trading_logger
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/logs")
async def get_trading_logs(
    strategy_name: Optional[str] = Query(None, description="策略名称"),
    log_type: Optional[str] = Query(None, description="日志类型: ORDER, TRADE, SIGNAL, ERROR, INFO"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, description="返回条数", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """获取交易日志"""
    try:
        trading_logger = get_trading_logger()

        start_time = None
        end_time = None

        if start_date:
            try:
                start_time = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="开始日期格式错误，应为 YYYY-MM-DD")

        if end_date:
            try:
                end_time = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            except ValueError:
                raise HTTPException(status_code=400, detail="结束日期格式错误，应为 YYYY-MM-DD")

        logs = trading_logger.get_logs(
            strategy_name=strategy_name,
            log_type=log_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": {
                "logs": logs,
                "total": len(logs),
                "filters": {
                    "strategy_name": strategy_name,
                    "log_type": log_type,
                    "start_date": start_date,
                    "end_date": end_date
                }
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取交易日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易日志失败: {str(e)}")


@router.get("/logs/summary")
async def get_logs_summary(
    strategy_name: Optional[str] = Query(None, description="策略名称"),
    days: int = Query(7, description="统计天数", ge=1, le=365)
):
    """获取交易日志统计摘要"""
    try:
        trading_logger = get_trading_logger()

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        log_types = ["ORDER", "TRADE", "SIGNAL", "ERROR", "INFO"]
        summary = {}

        for lt in log_types:
            logs = trading_logger.get_logs(
                strategy_name=strategy_name,
                log_type=lt,
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            summary[lt.lower()] = len(logs)

        all_logs = trading_logger.get_logs(
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )

        success_count = len([log for log in all_logs if log.get("is_success", True)])
        failed_count = len(all_logs) - success_count

        return {
            "success": True,
            "data": {
                "summary": summary,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_count": len(all_logs),
                "time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "days": days
                }
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取日志统计失败: {str(e)}")


@router.get("/performance/{strategy_name}")
async def get_strategy_performance(
    strategy_name: str,
    days: int = Query(30, description="统计天数", ge=1, le=365)
):
    """获取策略性能统计"""
    try:
        trading_logger = get_trading_logger()

        performance = trading_logger.get_strategy_performance(
            strategy_name=strategy_name,
            days=days
        )

        if not performance or performance.get("total_orders", 0) == 0:
            return {
                "success": True,
                "data": {
                    "strategy_name": strategy_name,
                    "message": "暂无交易数据",
                    "days": days
                },
                "timestamp": datetime.now().isoformat()
            }

        return {
            "success": True,
            "data": {
                "performance": performance,
                "days": days
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取策略性能统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略性能统计失败: {str(e)}")


@router.get("/recent")
async def get_recent_logs(
    limit: int = Query(50, description="返回条数", ge=1, le=200)
):
    """获取最近的交易日志"""
    try:
        trading_logger = get_trading_logger()

        logs = trading_logger.get_logs(limit=limit, offset=0)

        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最近日志失败: {str(e)}")
