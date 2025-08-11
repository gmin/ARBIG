"""
交易相关API接口
提供行情、账户、持仓等数据的API服务
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import json
from datetime import datetime

from shared.database.connection import get_db_manager
from shared.models.trading import (
    TickData, AccountInfo, PositionInfo, MarketDataResponse,
    AccountSummary, PositionSummary
)
from shared.utils.service_client import ServiceClient
from utils.logger import get_logger
from config.config import get_supported_contracts, get_main_contract_symbol

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["trading"])

# 依赖注入
async def get_service_client():
    """获取服务客户端"""
    return ServiceClient("trading_service", "http://localhost:8001")

@router.get("/market/current", response_model=MarketDataResponse)
async def get_current_market_data(symbol: str = "au2508"):
    """获取当前行情数据（Redis已移除，使用CTP数据）"""
    try:
        # 直接从核心交易服务获取CTP数据
        service_client = await get_service_client()
        response = await service_client.get(f"/real_trading/tick/{symbol}")

        if response.success and "response" in response.data:
            import json
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

@router.get("/accounts", response_model=List[AccountInfo])
async def get_accounts():
    """获取账户列表"""
    try:
        db_manager = get_db_manager()
        result = await db_manager.execute_query("""
            SELECT account_id, balance, available, margin, 
                   unrealized_pnl, realized_pnl, currency, risk_ratio, update_time
            FROM accounts
            ORDER BY update_time DESC
        """)
        
        accounts = []
        for row in result:
            accounts.append(AccountInfo(
                account_id=row['account_id'],
                balance=float(row['balance']),
                available=float(row['available']),
                margin=float(row['margin']),
                unrealized_pnl=float(row['unrealized_pnl']),
                realized_pnl=float(row['realized_pnl']),
                currency=row['currency'],
                risk_ratio=float(row['risk_ratio']),
                update_time=row['update_time']
            ))
        
        return accounts
        
    except Exception as e:
        logger.error(f"获取账户列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户列表失败: {str(e)}")

@router.get("/accounts/{account_id}", response_model=AccountSummary)
async def get_account_summary(account_id: str):
    """获取账户汇总信息"""
    try:
        db_manager = get_db_manager()
        
        # 获取账户基本信息
        account_result = await db_manager.execute_query("""
            SELECT account_id, balance, available, margin, 
                   unrealized_pnl, realized_pnl, currency, risk_ratio, update_time
            FROM accounts
            WHERE account_id = %s
        """, (account_id,))
        
        if not account_result:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        account_data = account_result[0]
        account_info = AccountInfo(
            account_id=account_data['account_id'],
            balance=float(account_data['balance']),
            available=float(account_data['available']),
            margin=float(account_data['margin']),
            unrealized_pnl=float(account_data['unrealized_pnl']),
            realized_pnl=float(account_data['realized_pnl']),
            currency=account_data['currency'],
            risk_ratio=float(account_data['risk_ratio']),
            update_time=account_data['update_time']
        )
        
        # 获取持仓信息
        position_result = await db_manager.execute_query("""
            SELECT account_id, symbol, direction, volume, avg_price, 
                   current_price, unrealized_pnl, margin, open_time, update_time
            FROM positions
            WHERE account_id = %s AND volume > 0
            ORDER BY open_time DESC
        """, (account_id,))
        
        positions = []
        total_margin = 0
        total_unrealized_pnl = 0
        
        for row in position_result:
            position = PositionInfo(
                account_id=row['account_id'],
                symbol=row['symbol'],
                direction=row['direction'],
                volume=row['volume'],
                avg_price=float(row['avg_price']),
                current_price=float(row['current_price']),
                unrealized_pnl=float(row['unrealized_pnl']),
                margin=float(row['margin']),
                open_time=row['open_time'],
                update_time=row['update_time']
            )
            positions.append(position)
            total_margin += position.margin
            total_unrealized_pnl += position.unrealized_pnl
        
        position_summary = PositionSummary(
            total_positions=len(positions),
            total_volume=sum(p.volume for p in positions),
            total_margin=total_margin,
            total_unrealized_pnl=total_unrealized_pnl,
            positions=positions
        )
        
        # 计算总资产
        total_assets = account_info.balance + account_info.unrealized_pnl
        
        return AccountSummary(
            account_info=account_info,
            position_summary=position_summary,
            daily_pnl=account_info.unrealized_pnl,  # 简化处理，实际应该是当日盈亏
            total_assets=total_assets
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户汇总失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户汇总失败: {str(e)}")

# 数据库持仓查询已移除，使用实时CTP数据

@router.post("/positions/{position_id}/close")
async def close_position(position_id: int, service_client: ServiceClient = Depends(get_service_client)):
    """平仓操作"""
    try:
        # 获取持仓信息
        db_manager = get_db_manager()
        result = await db_manager.execute_query("""
            SELECT id, account_id, symbol, direction, volume, avg_price
            FROM positions
            WHERE id = %s AND volume > 0
        """, (position_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="持仓不存在或已平仓")
        
        position = result[0]
        
        # 调用核心交易服务执行平仓
        response = await service_client.post("/trading/close_position", {
            "position_id": position_id,
            "account_id": position['account_id'],
            "symbol": position['symbol'],
            "direction": "sell" if position['direction'] == "long" else "buy",
            "volume": position['volume']
        })

        # 处理APIResponse对象
        response_data = response.data if hasattr(response, 'data') else response

        if response_data.get("success"):
            return {"success": True, "message": "平仓指令已发送", "order_id": response_data.get("order_id")}
        else:
            raise HTTPException(status_code=400, detail=response_data.get("message", "平仓失败"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"平仓操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"平仓操作失败: {str(e)}")

@router.get("/config/main_contract")
async def get_main_contract():
    """获取主力合约配置"""
    try:
        from core.config_manager import ConfigManager
        config_mgr = ConfigManager()
        
        return {
            "main_contract": config_mgr.get_main_contract(),
            "contract_multiplier": config_mgr.get_contract_multiplier(),
            "market_data_config": config_mgr.get_market_data_config()
        }
        
    except Exception as e:
        logger.error(f"获取主力合约配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.post("/config/main_contract")
async def update_main_contract(contract: str):
    """更新主力合约配置"""
    try:
        from core.config_manager import ConfigManager
        config_mgr = ConfigManager()

        success = config_mgr.set_main_contract(contract)
        if success:
            return {"success": True, "message": f"主力合约已更新为: {contract}"}
        else:
            raise HTTPException(status_code=400, detail="更新主力合约失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主力合约配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.get("/strategy/status")
async def get_strategy_status(service_client: ServiceClient = Depends(get_service_client)):
    """获取策略运行状态"""
    try:
        response = await service_client.get("/trading/strategy/status")
        return response

    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")

@router.post("/strategy/{strategy_name}/start")
async def start_strategy(strategy_name: str, service_client: ServiceClient = Depends(get_service_client)):
    """启动策略"""
    try:
        response = await service_client.post(f"/trading/strategy/{strategy_name}/start", {})
        return response

    except Exception as e:
        logger.error(f"启动策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动策略失败: {str(e)}")

@router.post("/strategy/{strategy_name}/stop")
async def stop_strategy(strategy_name: str, service_client: ServiceClient = Depends(get_service_client)):
    """停止策略"""
    try:
        response = await service_client.post(f"/trading/strategy/{strategy_name}/stop", {})
        return response

    except Exception as e:
        logger.error(f"停止策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止策略失败: {str(e)}")

@router.post("/emergency_stop")
async def emergency_stop(service_client: ServiceClient = Depends(get_service_client)):
    """系统紧急停止"""
    try:
        response = await service_client.post("/trading/emergency_stop", {})
        return response

    except Exception as e:
        logger.error(f"系统紧急停止失败: {e}")
        raise HTTPException(status_code=500, detail=f"系统紧急停止失败: {str(e)}")

@router.get("/strategy/triggers")
async def get_strategy_triggers(
    limit: int = 50,
    strategy_name: Optional[str] = None,
    service_client: ServiceClient = Depends(get_service_client)
):
    """获取策略触发记录"""
    try:
        params = {"limit": limit}
        if strategy_name:
            params["strategy_name"] = strategy_name

        response = await service_client.get("/trading/strategy/triggers", params=params)
        return response

    except Exception as e:
        logger.error(f"获取策略触发记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略触发记录失败: {str(e)}")

@router.post("/manual_order")
async def submit_manual_order(
    order_data: dict,
    service_client: ServiceClient = Depends(get_service_client)
):
    """提交手动交易订单"""
    try:
        # 转发到核心交易服务的真实交易接口
        response = await service_client.post("/real_trading/order", data=order_data)

        logger.info(f"手动交易订单提交: {order_data}")
        return response

    except Exception as e:
        logger.error(f"手动交易订单提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动交易订单提交失败: {str(e)}")

@router.post("/close_position")
async def close_position(
    close_data: dict,
    service_client: ServiceClient = Depends(get_service_client)
):
    """平仓操作"""
    try:
        # 转发到核心交易服务的平仓接口
        response = await service_client.post("/real_trading/close_position", data=close_data)

        logger.info(f"平仓操作: {close_data}")
        return response

    except Exception as e:
        logger.error(f"平仓操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"平仓操作失败: {str(e)}")

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
            import json
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
                            "margin": pos_data["long_position"] * pos_data.get("current_price", 0) * 1000 * 0.08  # 8%保证金率
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
                            "margin": pos_data["short_position"] * pos_data.get("current_price", 0) * 1000 * 0.08  # 8%保证金率
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
            import json
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
        except:
            pass

        try:
            tick_response = await service_client.get("/real_trading/tick/au2508")
            if tick_response.success and "response" in tick_response.data:
                tick_data = json.loads(tick_response.data["response"])
                if tick_data.get("success"):
                    result_data["tick_data"] = {"au2508": tick_data["data"]}
        except:
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
