"""
实盘交易统计API
提供详细的交易统计和分析功能
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, date
import json

from utils.logger import get_logger
from services.strategy_service.core.strategy_engine import get_strategy_engine

logger = get_logger(__name__)
router = APIRouter(prefix="/statistics", tags=["交易统计"])

@router.get("/overview")
async def get_trading_overview():
    """获取交易总览统计"""
    try:
        engine = get_strategy_engine()
        
        # 获取所有策略的统计
        all_stats = {}
        total_trades = 0
        total_pnl = 0.0
        total_commission = 0.0
        winning_strategies = 0
        
        for strategy_name in engine.strategies.keys():
            if strategy_name in engine.performance_stats:
                perf = engine.performance_stats[strategy_name]
                stats = perf.get_summary()
                all_stats[strategy_name] = stats
                
                total_trades += stats['total_trades']
                total_pnl += stats['total_pnl']
                total_commission += stats['total_commission']
                
                if stats['total_pnl'] > 0:
                    winning_strategies += 1
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_strategies": len(engine.strategies),
                    "active_strategies": len(engine.active_strategies),
                    "winning_strategies": winning_strategies,
                    "total_trades": total_trades,
                    "total_pnl": total_pnl,
                    "total_commission": total_commission,
                    "net_pnl": total_pnl - total_commission,
                    "overall_win_rate": winning_strategies / len(engine.strategies) if engine.strategies else 0
                },
                "strategies": all_stats
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取交易总览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易总览失败: {str(e)}")

@router.get("/strategy/{strategy_name}")
async def get_strategy_statistics(strategy_name: str):
    """获取指定策略的详细统计"""
    try:
        engine = get_strategy_engine()
        
        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_name} 不存在")
        
        if strategy_name not in engine.performance_stats:
            return {
                "success": True,
                "data": {
                    "strategy_name": strategy_name,
                    "status": "no_data",
                    "message": "暂无交易数据"
                },
                "timestamp": datetime.now().isoformat()
            }
        
        perf = engine.performance_stats[strategy_name]
        
        return {
            "success": True,
            "data": {
                "strategy_name": strategy_name,
                "summary": perf.get_summary(),
                "daily_performance": perf.get_daily_performance(),
                "recent_trades": [trade.to_dict() for trade in perf.trades[-10:]],  # 最近10笔交易
                "equity_curve": {
                    "values": perf.equity_curve[-100:],  # 最近100个点
                    "timestamps": [ts.isoformat() for ts in perf.equity_timestamps[-100:]]
                },
                "risk_metrics": perf.get_risk_metrics()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略统计失败: {str(e)}")

@router.get("/daily")
async def get_daily_statistics(
    strategy_name: Optional[str] = Query(None, description="策略名称，不指定则返回所有策略"),
    days: int = Query(30, description="统计天数", ge=1, le=365)
):
    """获取日度统计数据"""
    try:
        engine = get_strategy_engine()
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        daily_stats = {}
        
        # 确定要统计的策略
        strategies_to_check = [strategy_name] if strategy_name else list(engine.strategies.keys())
        
        for strat_name in strategies_to_check:
            if strat_name in engine.performance_stats:
                perf = engine.performance_stats[strat_name]
                daily_data = []
                
                # 生成每日数据
                current_date = start_date
                while current_date <= end_date:
                    if current_date in perf.daily_performance:
                        daily_perf = perf.daily_performance[current_date]
                        daily_data.append(daily_perf.to_dict())
                    else:
                        # 没有交易的日期
                        daily_data.append({
                            "date": current_date.isoformat(),
                            "pnl": 0.0,
                            "net_pnl": 0.0,
                            "trade_count": 0,
                            "win_count": 0,
                            "win_rate": 0.0,
                            "commission": 0.0,
                            "max_position": 0
                        })
                    current_date += timedelta(days=1)
                
                daily_stats[strat_name] = daily_data
        
        return {
            "success": True,
            "data": {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "strategies": daily_stats
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取日度统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取日度统计失败: {str(e)}")

@router.get("/performance/ranking")
async def get_performance_ranking():
    """获取策略性能排名"""
    try:
        engine = get_strategy_engine()
        
        rankings = []
        
        for strategy_name, perf in engine.performance_stats.items():
            summary = perf.get_summary()
            risk_metrics = perf.get_risk_metrics()
            
            rankings.append({
                "strategy_name": strategy_name,
                "total_pnl": summary['total_pnl'],
                "net_pnl": summary['net_pnl'],
                "win_rate": summary['win_rate'],
                "total_trades": summary['total_trades'],
                "sharpe_ratio": risk_metrics.get('sharpe_ratio', 0),
                "max_drawdown": risk_metrics.get('max_drawdown', 0),
                "profit_factor": risk_metrics.get('profit_factor', 0)
            })
        
        # 按净盈亏排序
        rankings.sort(key=lambda x: x['net_pnl'], reverse=True)
        
        return {
            "success": True,
            "data": {
                "rankings": rankings,
                "total_strategies": len(rankings)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取性能排名失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能排名失败: {str(e)}")

@router.get("/realtime")
async def get_realtime_statistics():
    """获取实时统计数据"""
    try:
        engine = get_strategy_engine()
        
        realtime_data = {
            "engine_status": {
                "running": engine.running,
                "active_strategies": len(engine.active_strategies),
                "total_strategies": len(engine.strategies),
                "data_processing": engine.running
            },
            "current_positions": {},
            "recent_signals": engine.total_signals,
            "market_status": "trading" if engine.running else "closed"
        }
        
        # 获取当前持仓
        for strategy_name, strategy in engine.strategies.items():
            if hasattr(strategy, 'pos'):
                realtime_data["current_positions"][strategy_name] = {
                    "position": strategy.pos,
                    "symbol": strategy.symbol,
                    "status": strategy.status.value if hasattr(strategy.status, 'value') else str(strategy.status)
                }
        
        return {
            "success": True,
            "data": realtime_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取实时统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时统计失败: {str(e)}")

@router.get("/signals/{strategy_name}")
async def get_strategy_signals(strategy_name: str, limit: int = Query(20, description="返回信号数量", ge=1, le=100)):
    """获取策略的信号触发历史"""
    try:
        engine = get_strategy_engine()

        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_name} 不存在")

        strategy = engine.strategies[strategy_name]

        # 检查策略是否有信号触发记录功能
        if hasattr(strategy, 'get_signal_triggers'):
            triggers = strategy.get_signal_triggers()

            # 按时间倒序，返回最新的信号
            triggers.sort(key=lambda x: x['timestamp'], reverse=True)
            limited_triggers = triggers[:limit]

            return {
                "success": True,
                "data": {
                    "strategy_name": strategy_name,
                    "total_signals": len(triggers),
                    "signals": limited_triggers
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": True,
                "data": {
                    "strategy_name": strategy_name,
                    "message": "该策略不支持信号分析功能",
                    "signals": []
                },
                "timestamp": datetime.now().isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略信号失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略信号失败: {str(e)}")

@router.get("/signals/{strategy_name}/analysis")
async def get_signal_analysis(strategy_name: str):
    """获取策略信号分析报告"""
    try:
        engine = get_strategy_engine()

        if strategy_name not in engine.strategies:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_name} 不存在")

        strategy = engine.strategies[strategy_name]

        if not hasattr(strategy, 'get_signal_triggers'):
            raise HTTPException(status_code=400, detail="该策略不支持信号分析功能")

        triggers = strategy.get_signal_triggers()

        if not triggers:
            return {
                "success": True,
                "data": {
                    "strategy_name": strategy_name,
                    "message": "暂无信号数据",
                    "analysis": {}
                },
                "timestamp": datetime.now().isoformat()
            }

        # 分析信号统计
        analysis = {
            "total_signals": len(triggers),
            "signal_frequency": {},
            "action_distribution": {},
            "trigger_reasons": {},
            "market_conditions": {},
            "performance_by_signal": {}
        }

        # 统计信号频率（按小时）
        from collections import defaultdict
        hourly_signals = defaultdict(int)
        action_counts = defaultdict(int)
        reason_counts = defaultdict(int)

        for trigger in triggers:
            # 按小时统计
            hour = datetime.fromtimestamp(trigger['timestamp']).hour
            hourly_signals[hour] += 1

            # 统计动作分布
            action_counts[trigger.get('action', 'UNKNOWN')] += 1

            # 统计触发原因
            reason_counts[trigger.get('reason', 'UNKNOWN')] += 1

        analysis["signal_frequency"] = dict(hourly_signals)
        analysis["action_distribution"] = dict(action_counts)
        analysis["trigger_reasons"] = dict(reason_counts)

        # 最新市场分析
        if hasattr(strategy, 'get_latest_market_analysis'):
            analysis["current_market_conditions"] = strategy.get_latest_market_analysis()

        return {
            "success": True,
            "data": {
                "strategy_name": strategy_name,
                "analysis": analysis,
                "recent_signals": triggers[-5:] if len(triggers) >= 5 else triggers  # 最近5个信号
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取信号分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取信号分析失败: {str(e)}")
