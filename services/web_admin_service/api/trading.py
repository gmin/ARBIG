"""
交易相关API接口
提供行情、账户、持仓等数据的API服务
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
import json
import httpx
from datetime import datetime

from shared.models.trading import (
    TickData, MarketDataResponse,
)
from utils.service_client import ServiceClient
from utils.logger import get_logger
from config.config import CONFIG, get_supported_contracts, get_main_contract_symbol

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])

# 依赖注入
async def get_service_client():
    """获取服务客户端"""
    return ServiceClient("trading_service", "http://localhost:8001")

@router.get("/config/main_contract")
async def get_main_contract():
    """获取主力合约配置"""
    try:
        main_symbol = get_main_contract_symbol()
        supported_contracts = get_supported_contracts()

        return {
            "success": True,
            "data": {
                "main_contract": main_symbol,
                "supported_contracts": supported_contracts
            }
        }
    except Exception as e:
        logger.error(f"获取主力合约配置失败: {e}")
        return {
            "success": False,
            "message": f"获取主力合约配置失败: {str(e)}"
        }

@router.get("/market/current", response_model=MarketDataResponse)
async def get_current_market_data(symbol: str = None):
    """获取当前行情数据（Redis已移除，使用CTP数据）"""
    try:
        # 如果没有指定合约，使用主力合约
        if symbol is None:
            symbol = get_main_contract_symbol()

        # 直接从核心交易服务获取CTP数据
        service_client = await get_service_client()
        response = await service_client.get(f"/real_trading/tick/{symbol}")

        if response.success and "response" in response.data:
            tick_response = json.loads(response.data["response"])
            if tick_response.get("success") and tick_response.get("data"):
                tick_data = tick_response["data"]
                return MarketDataResponse(
                    symbol=symbol,
                    tick_data=TickData(**tick_data),
                    is_connected=True,
                    last_update=datetime.now()
                )

        # 如果CTP数据不可用，返回错误
        raise HTTPException(status_code=503, detail="CTP行情数据不可用")

    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行情数据失败: {str(e)}")


@router.post("/config/main_contract")
async def update_main_contract(contract: str):
    """更新主力合约配置。

    这里先更新当前进程内配置，避免继续依赖缺失的旧模块。
    """
    try:
        supported_contracts = get_supported_contracts()
        target_contract = next((item for item in supported_contracts if item["symbol"] == contract), None)

        if not target_contract:
            raise HTTPException(status_code=400, detail="更新主力合约失败")

        for item in CONFIG["supported_contracts"]:
            item["is_main"] = item["symbol"] == contract

        CONFIG["main_contract"] = {
            "symbol": target_contract["symbol"],
            "name": target_contract["name"],
            "exchange": target_contract["exchange"],
            "description": f"{target_contract['name']}主力合约"
        }

        return {"success": True, "message": f"主力合约已更新为: {contract}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主力合约配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.get("/strategy/status")
async def get_strategy_status():
    """获取策略运行状态。策略管理边界已归属 Strategy Service。"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/strategies")
            return response.json()
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")


@router.post("/emergency_stop")
async def emergency_stop():
    """系统紧急停止。统一转发到 Strategy Service。"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8002/emergency_stop")
            return response.json()
    except Exception as e:
        logger.error(f"系统紧急停止失败: {e}")
        raise HTTPException(status_code=500, detail=f"系统紧急停止失败: {str(e)}")


@router.get("/strategy/triggers")
async def get_strategy_triggers(limit: int = 50, strategy_name: Optional[str] = None):
    """获取策略触发记录。统一转发到 Strategy Service。"""
    try:
        params = {"limit": limit}
        if strategy_name:
            params["strategy_name"] = strategy_name

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/strategies/triggers", params=params)
            return response.json()
    except Exception as e:
        logger.error(f"获取策略触发记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略触发记录失败: {str(e)}")

# 策略管理API代理
@router.get("/strategies")
async def get_strategies():
    """获取策略列表"""
    try:
        # 直接调用策略管理服务
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/strategies")
            return response.json()
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略列表失败: {str(e)}")

@router.get("/strategies/types")
async def get_strategy_types():
    """获取可用策略类型"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/strategies/types")
            return response.json()
    except Exception as e:
        logger.error(f"获取策略类型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略类型失败: {str(e)}")

@router.post("/strategies/{strategy_name}/start")
async def start_strategy(strategy_name: str):
    """启动策略"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8002/strategies/{strategy_name}/start")
            return response.json()
    except Exception as e:
        logger.error(f"启动策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动策略失败: {str(e)}")

@router.post("/strategies/{strategy_name}/stop")
async def stop_strategy(strategy_name: str):
    """停止策略"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8002/strategies/{strategy_name}/stop")
            return response.json()
    except Exception as e:
        logger.error(f"停止策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止策略失败: {str(e)}")

@router.post("/strategies/{strategy_name}/params")
async def update_strategy_params(strategy_name: str, params: dict):
    """更新策略参数"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8002/strategies/{strategy_name}/params",
                json=params
            )
            return response.json()
    except Exception as e:
        logger.error(f"更新策略参数失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略参数失败: {str(e)}")

@router.post("/strategies/register")
async def register_strategy(request: Request):
    """注册新策略实例"""
    try:
        # 从请求体中提取JSON数据
        request_data = await request.json()
        
        # 从请求体中提取数据
        strategy_type = request_data.get('strategy_type')
        instance_name = request_data.get('instance_name')
        symbol = request_data.get('symbol')
        description = request_data.get('description', '')
        params = request_data.get('params', {})
        
        if not strategy_type or not instance_name or not symbol:
            raise HTTPException(status_code=400, detail="缺少必要参数: strategy_type, instance_name, symbol")
        
        # 构建发送给策略服务的数据
        strategy_data = {
            "strategy_name": instance_name,
            "symbol": symbol,
            "strategy_type": strategy_type,
            "description": description,
            "params": params
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8002/strategies/register", json=strategy_data)
            return response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"注册策略失败: {str(e)}")

# 性能统计API已移至回测服务，不再代理策略服务的性能接口

@router.post("/strategies/{strategy_name}/trade")
async def update_strategy_trade(strategy_name: str, trade_data: dict):
    """更新策略交易记录"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8002/strategies/{strategy_name}/trade",
                json=trade_data
            )
            return response.json()
    except Exception as e:
        logger.error(f"更新策略交易记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略交易记录失败: {str(e)}")

@router.post("/strategies/{strategy_name}/position")
async def update_strategy_position(strategy_name: str, position_data: dict):
    """更新策略持仓"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8002/strategies/{strategy_name}/position",
                json=position_data
            )
            return response.json()
    except Exception as e:
        logger.error(f"更新策略持仓失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略持仓失败: {str(e)}")

@router.post("/backtest")
async def run_backtest(backtest_request: dict):
    """运行策略回测（转发到 Strategy Service）"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8002/backtest/quick",
                json=backtest_request,
            )
            return response.json()
    except Exception as e:
        logger.error(f"运行回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"运行回测失败: {str(e)}")

@router.get("/positions")
async def get_positions(
    symbol: Optional[str] = None,
    service_client: ServiceClient = Depends(get_service_client)
):
    """获取持仓信息"""
    try:
        params = {}
        if symbol:
            params["symbol"] = symbol

        response = await service_client.get("/real_trading/positions", params=params)

        # 解析ServiceClient的响应格式
        if response.success and "response" in response.data:
            positions_data = json.loads(response.data["response"])
            if positions_data.get("success") and positions_data.get("data"):
                # 转换持仓数据格式为前端期望的数组格式
                positions_dict = positions_data["data"]
                positions_list = []

                for symbol, pos_data in positions_dict.items():
                    # 如果有多单持仓
                    if pos_data.get("long_position", 0) > 0:
                        positions_list.append({
                            "symbol": symbol,
                            "direction": "LONG",
                            "volume": pos_data["long_position"],
                            "avg_price": pos_data.get("long_price", 0),
                            "current_price": pos_data.get("current_price", 0),
                            "unrealized_pnl": pos_data.get("long_pnl", 0),
                            "margin": pos_data["long_position"] * pos_data.get("current_price", 0) * 1000 * 0.08,  # 8%保证金率
                            # 添加今昨仓信息
                            "today_volume": pos_data.get("long_today", 0),
                            "yd_volume": pos_data.get("long_yesterday", 0),
                            "position_detail": {
                                "total": pos_data["long_position"],
                                "today": pos_data.get("long_today", 0),
                                "yesterday": pos_data.get("long_yesterday", 0)
                            }
                        })

                    # 如果有空单持仓
                    if pos_data.get("short_position", 0) > 0:
                        positions_list.append({
                            "symbol": symbol,
                            "direction": "SHORT",
                            "volume": pos_data["short_position"],
                            "avg_price": pos_data.get("short_price", 0),
                            "current_price": pos_data.get("current_price", 0),
                            "unrealized_pnl": pos_data.get("short_pnl", 0),
                            "margin": pos_data["short_position"] * pos_data.get("current_price", 0) * 1000 * 0.08,  # 8%保证金率
                            # 添加今昨仓信息
                            "today_volume": pos_data.get("short_today", 0),
                            "yd_volume": pos_data.get("short_yesterday", 0),
                            "position_detail": {
                                "total": pos_data["short_position"],
                                "today": pos_data.get("short_today", 0),
                                "yesterday": pos_data.get("short_yesterday", 0)
                            }
                        })

                return positions_list

        # 如果没有持仓数据，返回空数组
        return []

    except Exception as e:
        logger.error(f"获取持仓信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持仓信息失败: {str(e)}")

@router.get("/ctp_status")
async def get_ctp_status(
    service_client: ServiceClient = Depends(get_service_client)
):
    """获取CTP连接状态"""
    try:
        response = await service_client.get("/real_trading/status")

        # 解析ServiceClient的响应格式
        if response.success and "response" in response.data:
            status_data = json.loads(response.data["response"])
        else:
            status_data = response.data if response.success else {}

        # 同时获取账户信息和行情数据
        result_data = status_data.get("data", {}) if status_data.get("success") else {}

        try:
            account_response = await service_client.get("/real_trading/account")
            if account_response.success and "response" in account_response.data:
                account_data = json.loads(account_response.data["response"])
                if account_data.get("success"):
                    result_data["account_info"] = account_data["data"]
        except Exception:
            pass

        try:
            main_symbol = get_main_contract_symbol()
            tick_response = await service_client.get(f"/real_trading/tick/{main_symbol}")
            if tick_response.success and "response" in tick_response.data:
                tick_data = json.loads(tick_response.data["response"])
                if tick_data.get("success"):
                    result_data["tick_data"] = {main_symbol: tick_data["data"]}
        except Exception:
            pass

        return {
            "success": True,
            "data": result_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取CTP状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取CTP状态失败: {str(e)}")

@router.get("/account")
async def get_account(
    service_client: ServiceClient = Depends(get_service_client)
):
    """获取账户信息"""
    try:
        response = await service_client.get("/real_trading/account")
        return response

    except Exception as e:
        logger.error(f"获取账户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户信息失败: {str(e)}")

@router.get("/tick/{symbol}")
async def get_tick(
    symbol: str,
    service_client: ServiceClient = Depends(get_service_client)
):
    """获取行情数据"""
    try:
        response = await service_client.get(f"/real_trading/tick/{symbol}")
        return response

    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行情数据失败: {str(e)}")

@router.get("/contracts/config")
async def get_contracts_config():
    """获取合约配置信息"""
    try:
        supported_contracts = get_supported_contracts()
        main_contract_symbol = get_main_contract_symbol()

        return {
            "success": True,
            "data": {
                "main_contract": main_contract_symbol,
                "supported_contracts": supported_contracts,
                "default_symbol": main_contract_symbol
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取合约配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取合约配置失败: {str(e)}")


# ==================== 交易日志代理路由 ====================

@router.get("/trading_logs/logs")
async def proxy_trading_logs(request: Request):
    """代理交易日志查询到 Trading Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/trading_logs/logs",
                params=dict(request.query_params),
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取交易日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易日志失败: {str(e)}")


@router.get("/trading_logs/logs/summary")
async def proxy_trading_logs_summary(request: Request):
    """代理交易日志统计到 Trading Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/trading_logs/logs/summary",
                params=dict(request.query_params),
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取交易日志统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易日志统计失败: {str(e)}")


@router.get("/trading_logs/performance/{strategy_name}")
async def proxy_trading_performance(strategy_name: str, request: Request):
    """代理策略绩效查询到 Trading Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8001/trading_logs/performance/{strategy_name}",
                params=dict(request.query_params),
            )
            return response.json()
    except Exception as e:
        logger.error(f"获取策略绩效失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略绩效失败: {str(e)}")
