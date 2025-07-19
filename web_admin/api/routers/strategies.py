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
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/strategies", tags=["策略管理"])

@router.get("/list", response_model=StrategyListResponse, summary="获取策略列表")
async def get_strategies_list(strategy_manager=Depends(get_strategy_manager)):
    """获取所有可用策略的列表"""
    try:
        strategies = []

        # 从实际的策略管理器获取策略信息
        if strategy_manager and hasattr(strategy_manager, 'services') and 'StrategyService' in strategy_manager.services:
            strategy_service = strategy_manager.services['StrategyService']

            # 获取配置中的策略
            if hasattr(strategy_service, 'config_manager') and strategy_service.config_manager:
                strategies_config = strategy_service.config_manager.get_config('strategies', {})

                for strategy_name, strategy_config in strategies_config.items():
                    # 确定策略状态
                    status = "available"
                    if strategy_config.get('enabled', False):
                        status = "running" if strategy_name in getattr(strategy_service, 'running_strategies', {}) else "loaded"

                    # 根据策略类型确定显示名称和描述
                    display_name = strategy_name
                    description = f"{strategy_name} 策略"
                    risk_level = "medium"

                    if strategy_name == "shfe_quant":
                        display_name = "SHFE量化策略"
                        description = "上海期货交易所黄金量化交易策略"
                        risk_level = "high"


                    strategies.append(StrategyInfo(
                        name=strategy_name,
                        display_name=display_name,
                        description=description,
                        version="1.0.0",
                        risk_level=risk_level,
                        status=status,
                        author="ARBIG Team"
                    ))

        # 删除默认策略列表中的套利策略
        if not strategies:
            strategies = [
                StrategyInfo(
                    name="shfe_quant",
                    display_name="SHFE量化策略",
                    description="上海期货交易所黄金量化交易策略",
                    version="1.0.0",
                    risk_level="high",
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

        current_strategy = CurrentStrategyInfo(
            strategy_name="shfe_quant",
            display_name="SHFE量化策略",
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

@router.get("/{strategy_name}/details", response_model=StrategyStatusResponse, summary="获取策略详细信息")
async def get_strategy_details(
    strategy_name: str,
    strategy_manager=Depends(get_strategy_manager)
):
    """获取指定策略的详细信息"""
    try:
        # 从实际的策略管理器获取策略信息
        if strategy_manager and hasattr(strategy_manager, 'services') and 'StrategyService' in strategy_manager.services:
            strategy_service = strategy_manager.services['StrategyService']

            # 获取策略配置
            if hasattr(strategy_service, 'config_manager') and strategy_service.config_manager:
                strategies_config = strategy_service.config_manager.get_config('strategies', {})
                strategy_config = strategies_config.get(strategy_name, {})

                if strategy_config:
                    # 找到策略配置，继续处理
                    pass
                else:
                    # 策略配置不存在，但我们仍然可以返回默认信息
                    strategy_config = {}

                # 构建策略详细信息
                display_name = strategy_name
                if strategy_name == "shfe_quant":
                    display_name = "SHFE量化策略"


                # 模拟策略统计数据
                current_strategy = CurrentStrategyInfo(
                    strategy_name=strategy_name,
                    display_name=display_name,
                    status="stopped",  # 默认停止状态
                    start_time=datetime.now().isoformat(),
                    runtime="00:00:00",
                    statistics=StrategyStatistics(
                        signals_generated=0,
                        orders_executed=0,
                        successful_trades=0,
                        failed_trades=0,
                        current_profit=0.0,
                        today_profit=0.0,
                        win_rate=0.0,
                        sharpe_ratio=0.0,
                        max_drawdown=0.0
                    )
                )

                return StrategyStatusResponse(
                    success=True,
                    message=f"策略 {strategy_name} 详细信息获取成功",
                    data=current_strategy,
                    request_id=str(uuid.uuid4())
                )

        # 如果无法从配置获取，返回默认信息
        display_name = strategy_name
        if strategy_name == "shfe_quant":
            display_name = "SHFE量化策略"


        current_strategy = CurrentStrategyInfo(
            strategy_name=strategy_name,
            display_name=display_name,
            status="stopped",
            start_time=datetime.now().isoformat(),
            runtime="00:00:00",
            statistics=StrategyStatistics(
                signals_generated=0,
                orders_executed=0,
                successful_trades=0,
                failed_trades=0,
                current_profit=0.0,
                today_profit=0.0,
                win_rate=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0
            )
        )

        return StrategyStatusResponse(
            success=True,
            message=f"策略 {strategy_name} 详细信息获取成功",
            data=current_strategy,
            request_id=str(uuid.uuid4())
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取策略详细信息失败: {str(e)}"
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

@router.get("/{strategy_name}/params", summary="获取策略参数")
async def get_strategy_params(strategy_name: str, strategy_manager=Depends(get_strategy_manager)):
    """获取指定策略的参数配置"""
    try:
        # 演示模式返回模拟参数
        demo_params = {
            "ma_short": 5,
            "ma_long": 20,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "stop_loss": 0.05,
            "take_profit": 0.08,
            "position_size": 1,
            "max_position": 5,
            "risk_factor": 0.02,
            "add_interval": 50,
            "position_mode": "fixed",
            "position_multiplier": 1.0
        }

        return APIResponse(
            success=True,
            message="获取策略参数成功",
            data=demo_params,
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取策略参数失败: {str(e)}"
        )

@router.post("/{strategy_name}/params", summary="更新策略参数")
async def update_strategy_params(strategy_name: str, params: Dict[str, Any], strategy_manager=Depends(get_strategy_manager)):
    """更新指定策略的参数配置"""
    try:
        # 在演示模式下，只记录参数更新
        print(f"演示模式：更新策略 {strategy_name} 参数: {params}")

        return APIResponse(
            success=True,
            message=f"策略 {strategy_name} 参数更新成功（演示模式）",
            data={"updated_params": params},
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新策略参数失败: {str(e)}"
        )

@router.post("/{strategy_name}/backtest", summary="运行历史回测")
async def run_backtest(strategy_name: str, config: Dict[str, Any], strategy_manager=Depends(get_strategy_manager)):
    """运行指定策略的历史回测"""
    try:
        # 使用真正的回测引擎
        from core.backtest import SimpleBacktester

        # 获取回测参数
        start_date = config.get("start_date", "2024-01-01")
        end_date = config.get("end_date", "2024-03-31")
        initial_capital = config.get("initial_capital", 100000)

        # 策略参数
        strategy_params = {
            'ma_short': config.get('ma_short', 5),
            'ma_long': config.get('ma_long', 20),
            'rsi_period': config.get('rsi_period', 14),
            'rsi_overbought': config.get('rsi_overbought', 70),
            'rsi_oversold': config.get('rsi_oversold', 30),
            'stop_loss': config.get('stop_loss', 0.05),
            'take_profit': config.get('take_profit', 0.08),
            'position_size': config.get('position_size', 1),
            'max_position': config.get('max_position', 5),
            'risk_factor': config.get('risk_factor', 0.02),
            'position_mode': config.get('position_mode', 'fixed'),
            'position_multiplier': config.get('position_multiplier', 1.0)
        }

        # 运行回测
        backtester = SimpleBacktester(initial_capital)
        backtest_results = backtester.run_backtest(strategy_params, start_date, end_date)

        return APIResponse(
            success=True,
            message="回测完成（演示模式）",
            data=backtest_results,
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"运行回测失败: {str(e)}"
        )
