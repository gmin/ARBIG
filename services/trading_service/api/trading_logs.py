"""
交易日志API接口
提供交易日志查询和统计功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from shared.utils.trading_logger import get_trading_logger
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
        
        # 解析时间参数
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
        
        # 获取日志
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
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 获取各类型日志数量
        log_types = ['ORDER', 'TRADE', 'SIGNAL', 'ERROR', 'INFO']
        summary = {}
        
        for log_type in log_types:
            logs = trading_logger.get_logs(
                strategy_name=strategy_name,
                log_type=log_type,
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            summary[log_type.lower()] = len(logs)
        
        # 获取成功/失败统计
        all_logs = trading_logger.get_logs(
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        success_count = len([log for log in all_logs if log.get('is_success', True)])
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
        
        if not performance:
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
        
        # 获取最近的日志
        logs = trading_logger.get_logs(
            limit=limit,
            offset=0
        )
        
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


@router.delete("/logs")
async def clear_old_logs(
    days: int = Query(30, description="保留天数", ge=1, le=365),
    strategy_name: Optional[str] = Query(None, description="策略名称，不指定则清理所有策略")
):
    """清理旧的交易日志"""
    try:
        # 这里可以实现清理逻辑
        # 为了安全，暂时只返回提示信息
        return {
            "success": True,
            "data": {
                "message": f"日志清理功能暂未实现，计划清理{days}天前的日志",
                "strategy_name": strategy_name,
                "days": days
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"清理日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理日志失败: {str(e)}")


@router.get("/export")
async def export_logs(
    strategy_name: Optional[str] = Query(None, description="策略名称"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    format: str = Query("json", description="导出格式: json, csv")
):
    """导出交易日志"""
    try:
        # 这里可以实现导出逻辑
        return {
            "success": True,
            "data": {
                "message": "日志导出功能暂未实现",
                "parameters": {
                    "strategy_name": strategy_name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "format": format
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"导出日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出日志失败: {str(e)}")
