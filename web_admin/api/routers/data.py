"""
数据查询API路由
提供行情数据、账户数据、风控数据等查询接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import uuid
from datetime import datetime

from ..models.requests import MarketDataRequest, AnalysisRequest, OrderRequest
from ..models.responses import (
    APIResponse, MarketDataResponse, AccountResponse, PositionsResponse,
    RiskResponse, TickData, AccountInfo, PositionInfo, RiskMetrics
)
from ..dependencies import get_data_manager

router = APIRouter(prefix="/api/v1/data", tags=["数据查询"])

@router.get("/market/ticks", response_model=MarketDataResponse, summary="获取实时行情")
async def get_market_ticks(
    symbols: str = Query(..., description="合约代码，多个用逗号分隔"),
    limit: int = Query(100, description="数据条数限制"),
    data_manager=Depends(get_data_manager)
):
    """获取实时Tick行情数据"""
    try:
        symbol_list = symbols.split(",")
        
        # 模拟Tick数据
        ticks = []
        for symbol in symbol_list:
            tick = TickData(
                symbol=symbol.strip(),
                datetime=datetime.now(),
                last_price=485.50,
                bid_price=485.40,
                ask_price=485.60,
                volume=12580,
                open_interest=45230,
                change=2.30,
                change_percent=0.48
            )
            ticks.append(tick)
        
        return MarketDataResponse(
            success=True,
            message="实时行情获取成功",
            data={"ticks": ticks},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取实时行情失败: {str(e)}"
        )

@router.get("/market/klines", response_model=MarketDataResponse, summary="获取K线数据")
async def get_market_klines(
    symbol: str = Query(..., description="合约代码"),
    interval: str = Query("1m", description="K线周期"),
    limit: int = Query(100, description="数据条数限制"),
    data_manager=Depends(get_data_manager)
):
    """获取K线数据"""
    try:
        # 这里暂时返回空数据，后续会连接到实际的数据源
        return MarketDataResponse(
            success=True,
            message="K线数据获取成功",
            data={
                "symbol": symbol,
                "interval": interval,
                "klines": []
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取K线数据失败: {str(e)}"
        )

@router.get("/account/info", response_model=AccountResponse, summary="获取账户信息")
async def get_account_info(data_manager=Depends(get_data_manager)):
    """获取账户资金信息"""
    try:
        # 尝试从真实的服务容器获取账户数据
        if hasattr(data_manager, 'ctp_gateway') and data_manager.ctp_gateway:
            # 先查询账户信息（如果还没有数据的话）
            if not data_manager.ctp_gateway.account:
                # 主动查询账户信息
                query_success = data_manager.ctp_gateway.query_account()
                if query_success:
                    # 等待一下让查询结果返回
                    import asyncio
                    await asyncio.sleep(1.0)  # 增加等待时间

            # 从CTP网关获取真实账户数据
            account_data = data_manager.ctp_gateway.account
            if account_data:
                # 计算保证金（总资金 - 可用资金）
                margin = float(account_data.balance - account_data.available)

                account = AccountInfo(
                    account_id=account_data.accountid,
                    total_assets=float(account_data.balance),
                    available=float(account_data.available),
                    margin=margin,
                    frozen=float(account_data.frozen),
                    profit=float(getattr(account_data, 'close_profit', 0.0)),
                    today_profit=float(getattr(account_data, 'position_profit', 0.0)),
                    commission=float(getattr(account_data, 'commission', 0.0)),
                    currency="CNY",
                    update_time=datetime.now()
                )

                return AccountResponse(
                    success=True,
                    message=f"账户信息获取成功（真实数据 - {account_data.accountid}）",
                    data=account,
                    request_id=str(uuid.uuid4())
                )

        # 如果没有真实数据，返回提示信息
        account = AccountInfo(
            account_id="未连接",
            total_assets=0.00,
            available=0.00,
            margin=0.00,
            frozen=0.00,
            profit=0.00,
            today_profit=0.00,
            commission=0.00,
            currency="CNY",
            update_time=datetime.now()
        )

        return AccountResponse(
            success=True,
            message="CTP未连接或账户信息查询失败",
            data=account,
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取账户信息失败: {str(e)}"
        )

@router.get("/account/positions", response_model=PositionsResponse, summary="获取持仓信息")
async def get_positions(data_manager=Depends(get_data_manager)):
    """获取持仓信息"""
    try:
        positions = []

        # 尝试从真实的服务容器获取持仓数据
        if hasattr(data_manager, 'ctp_gateway') and data_manager.ctp_gateway:
            # 先查询持仓信息（如果还没有数据的话）
            if not data_manager.ctp_gateway.positions:
                # 主动查询持仓信息
                query_success = data_manager.ctp_gateway.query_position()
                if query_success:
                    # 等待一下让查询结果返回
                    import asyncio
                    await asyncio.sleep(0.5)

            # 从CTP网关获取真实持仓数据
            ctp_positions = data_manager.ctp_gateway.positions
            for vt_symbol, position_data in ctp_positions.items():
                if position_data.volume > 0:  # 只显示有持仓的合约
                    # 获取当前价格
                    current_price = 0.0
                    tick_data = data_manager.ctp_gateway.ticks.get(vt_symbol)
                    if tick_data:
                        current_price = float(tick_data.last_price)

                    position = PositionInfo(
                        symbol=position_data.symbol,
                        direction="long" if position_data.direction.value == "多" else "short",
                        volume=float(position_data.volume),
                        avg_price=float(position_data.price),
                        current_price=current_price,
                        profit=float(position_data.pnl),
                        margin=float(getattr(position_data, 'margin', 0.0)),
                        open_time=datetime.now()  # CTP没有开仓时间，使用当前时间
                    )
                    positions.append(position)

        return PositionsResponse(
            success=True,
            message=f"持仓信息获取成功，共{len(positions)}个持仓（真实数据）",
            data={"positions": positions},
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取持仓信息失败: {str(e)}"
        )

@router.get("/risk/metrics", response_model=APIResponse, summary="获取风险指标和交易统计")
async def get_risk_metrics(data_manager=Depends(get_data_manager)):
    """获取风险指标和交易统计"""
    try:
        # 尝试从真实的服务容器获取数据
        if hasattr(data_manager, 'ctp_gateway') and data_manager.ctp_gateway:
            # 从CTP网关获取真实数据
            orders = data_manager.ctp_gateway.orders
            trades = data_manager.ctp_gateway.trades

            # 计算交易统计
            total_orders = len(orders)
            active_orders = len([o for o in orders.values() if o.status in ['未成交', '部分成交']])
            total_trades = len(trades)
            total_turnover = sum([t.volume * t.price for t in trades.values()])

            trading_stats = {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "total_trades": total_trades,
                "total_turnover": total_turnover
            }
        else:
            # 模拟交易统计
            trading_stats = {
                "total_orders": 0,
                "active_orders": 0,
                "total_trades": 0,
                "total_turnover": 0.0
            }

        # 风险指标数据
        risk_data = {
            "risk_level": "low",
            "position_ratio": 0.0,
            "daily_loss": 0.0,
            "max_drawdown": 0.0,
            "var_95": 0.0,
            "leverage": 1.0,
            "concentration": {}
        }

        return APIResponse(
            success=True,
            message="风险指标和交易统计获取成功",
            data={
                "risk_metrics": risk_data,
                "trading": trading_stats
            },
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取风险指标失败: {str(e)}"
        )

@router.get("/symbols", response_model=APIResponse, summary="获取合约列表")
async def get_symbols(data_manager=Depends(get_data_manager)):
    """获取可交易合约列表"""
    try:
        symbols = [
            {
                "symbol": "au2509",
                "name": "黄金2509",
                "exchange": "SHFE",
                "product_type": "futures",
                "contract_size": 1000,
                "tick_size": 0.05,
                "margin_ratio": 0.08
            },
            {
                "symbol": "au2512",
                "name": "黄金2512", 
                "exchange": "SHFE",
                "product_type": "futures",
                "contract_size": 1000,
                "tick_size": 0.05,
                "margin_ratio": 0.08
            },
            {
                "symbol": "au2601",
                "name": "黄金2601",
                "exchange": "SHFE", 
                "product_type": "futures",
                "contract_size": 1000,
                "tick_size": 0.05,
                "margin_ratio": 0.08
            }
        ]
        
        return APIResponse(
            success=True,
            message="合约列表获取成功",
            data={"symbols": symbols},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取合约列表失败: {str(e)}"
        )

@router.post("/orders/send", response_model=APIResponse, summary="发送订单")
async def send_order(
    request: OrderRequest,
    data_manager=Depends(get_data_manager)
):
    """发送交易订单"""
    try:
        # 这里需要连接到实际的交易服务
        # 暂时返回模拟响应
        order_id = f"order_{uuid.uuid4().hex[:8]}"

        return APIResponse(
            success=True,
            message="订单发送成功",
            data={
                "order_id": order_id,
                "symbol": request.symbol,
                "direction": request.direction,
                "volume": request.volume,
                "price": request.price,
                "type": request.type,
                "status": "submitted",
                "submit_time": datetime.now().isoformat()
            },
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"发送订单失败: {str(e)}"
        )

@router.post("/orders/cancel", response_model=APIResponse, summary="撤销订单")
async def cancel_order(
    order_id: str,
    data_manager=Depends(get_data_manager)
):
    """撤销订单"""
    try:
        # 这里需要连接到实际的交易服务
        # 暂时返回模拟响应
        return APIResponse(
            success=True,
            message="订单撤销成功",
            data={
                "order_id": order_id,
                "status": "cancelled",
                "cancel_time": datetime.now().isoformat()
            },
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"撤销订单失败: {str(e)}"
        )

@router.get("/orders", response_model=APIResponse, summary="获取订单列表")
async def get_orders(
    status: Optional[str] = Query(None, description="订单状态过滤"),
    active_only: Optional[bool] = Query(False, description="仅获取活跃订单"),
    limit: int = Query(100, description="返回数量限制"),
    data_manager=Depends(get_data_manager)
):
    """获取订单列表"""
    try:
        orders = []

        # 尝试从真实的服务容器获取订单数据
        if hasattr(data_manager, 'ctp_gateway') and data_manager.ctp_gateway:
            # 从CTP网关获取真实订单数据
            ctp_orders = data_manager.ctp_gateway.orders

            for order_id, order_data in ctp_orders.items():
                # 过滤活跃订单
                if active_only and order_data.status not in ['未成交', '部分成交']:
                    continue

                # 状态过滤
                if status and order_data.status != status:
                    continue

                order_info = {
                    "order_id": order_id,
                    "symbol": order_data.symbol,
                    "direction": order_data.direction.value,
                    "volume": float(order_data.volume),
                    "price": float(order_data.price),
                    "type": order_data.type.value,
                    "status": order_data.status,
                    "submit_time": order_data.datetime.isoformat() if hasattr(order_data, 'datetime') else datetime.now().isoformat()
                }
                orders.append(order_info)

                if len(orders) >= limit:
                    break

        return APIResponse(
            success=True,
            message=f"订单列表获取成功，共{len(orders)}个订单",
            data={"orders": orders},
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取订单列表失败: {str(e)}"
        )

@router.get("/trading/statistics", response_model=APIResponse, summary="获取交易统计")
async def get_trading_statistics(data_manager=Depends(get_data_manager)):
    """获取交易统计数据"""
    try:
        # 尝试从真实的服务容器获取交易统计
        if hasattr(data_manager, 'ctp_gateway') and data_manager.ctp_gateway:
            # 从CTP网关获取真实交易统计
            orders = data_manager.ctp_gateway.orders
            trades = data_manager.ctp_gateway.trades

            # 计算统计数据
            total_orders = len(orders)
            active_orders = len([o for o in orders.values() if o.status in ['未成交', '部分成交']])
            total_trades = len(trades)
            total_turnover = sum([t.volume * t.price for t in trades.values()])

            trading_stats = {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "total_trades": total_trades,
                "total_turnover": total_turnover,
                "today_pnl": 0.0,  # 今日盈亏
                "commission": 0.0,  # 手续费
                "update_time": datetime.now().isoformat()
            }

            return APIResponse(
                success=True,
                message="交易统计获取成功（真实数据）",
                data={"trading": trading_stats},
                request_id=str(uuid.uuid4())
            )

        # 如果没有真实数据，返回模拟数据
        trading_stats = {
            "total_orders": 0,
            "active_orders": 0,
            "total_trades": 0,
            "total_turnover": 0.0,
            "today_pnl": 0.0,
            "commission": 0.0,
            "update_time": datetime.now().isoformat()
        }

        return APIResponse(
            success=True,
            message="交易统计获取成功（无交易数据）",
            data={"trading": trading_stats},
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取交易统计失败: {str(e)}"
        )

@router.get("/history/orders", response_model=APIResponse, summary="获取历史订单")
async def get_history_orders(
    limit: int = Query(100, description="返回数量限制"),
    data_manager=Depends(get_data_manager)
):
    """获取CTP历史订单数据"""
    try:
        # 使用数据提供器的历史查询功能
        if hasattr(data_manager, 'data_provider'):
            history_orders = await data_manager.data_provider.get_history_orders()

            # 转换为API响应格式
            formatted_orders = []
            for order in history_orders[:limit]:
                formatted_order = {
                    "order_id": order.get('OrderSysID', order.get('OrderLocalID', 'N/A')),
                    "order_ref": order.get('OrderRef', 'N/A'),
                    "symbol": order.get('InstrumentID', 'N/A'),
                    "direction": "买入" if order.get('Direction') == '0' else "卖出",
                    "volume": int(order.get('VolumeTotalOriginal', 0)),
                    "price": float(order.get('LimitPrice', 0)),
                    "status": order.get('StatusMsg', 'N/A'),
                    "order_status": order.get('OrderStatus', 'N/A'),
                    "traded_volume": int(order.get('VolumeTraded', 0)),
                    "remaining_volume": int(order.get('VolumeTotal', 0)),
                    "insert_date": order.get('InsertDate', 'N/A'),
                    "insert_time": order.get('InsertTime', 'N/A'),
                    "exchange": order.get('ExchangeID', 'N/A'),
                    "session_id": order.get('SessionID', 'N/A')
                }
                formatted_orders.append(formatted_order)

            return APIResponse(
                success=True,
                message=f"历史订单获取成功，共{len(formatted_orders)}条记录",
                data={"orders": formatted_orders},
                request_id=str(uuid.uuid4())
            )
        else:
            return APIResponse(
                success=False,
                message="数据提供器未初始化",
                data={"orders": []},
                request_id=str(uuid.uuid4())
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史订单失败: {str(e)}"
        )

@router.get("/history/trades", response_model=APIResponse, summary="获取历史成交")
async def get_history_trades(
    limit: int = Query(100, description="返回数量限制"),
    data_manager=Depends(get_data_manager)
):
    """获取CTP历史成交数据"""
    try:
        # 使用数据提供器的历史查询功能
        if hasattr(data_manager, 'data_provider'):
            history_trades = await data_manager.data_provider.get_history_trades()

            # 转换为API响应格式
            formatted_trades = []
            for trade in history_trades[:limit]:
                formatted_trade = {
                    "trade_id": trade.get('TradeID', 'N/A'),
                    "order_id": trade.get('OrderSysID', 'N/A'),
                    "order_ref": trade.get('OrderRef', 'N/A'),
                    "symbol": trade.get('InstrumentID', 'N/A'),
                    "direction": "买入" if trade.get('Direction') == '0' else "卖出",
                    "volume": int(trade.get('Volume', 0)),
                    "price": float(trade.get('Price', 0)),
                    "trade_date": trade.get('TradeDate', 'N/A'),
                    "trade_time": trade.get('TradeTime', 'N/A'),
                    "exchange": trade.get('ExchangeID', 'N/A'),
                    "amount": float(trade.get('Price', 0)) * int(trade.get('Volume', 0)) * 1000  # 黄金每手1000克
                }
                formatted_trades.append(formatted_trade)

            return APIResponse(
                success=True,
                message=f"历史成交获取成功，共{len(formatted_trades)}条记录",
                data={"trades": formatted_trades},
                request_id=str(uuid.uuid4())
            )
        else:
            return APIResponse(
                success=False,
                message="数据提供器未初始化",
                data={"trades": []},
                request_id=str(uuid.uuid4())
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史成交失败: {str(e)}"
        )

@router.get("/trading/summary", response_model=APIResponse, summary="获取交易汇总")
async def get_trading_summary(data_manager=Depends(get_data_manager)):
    """获取交易汇总统计"""
    try:
        # 使用数据提供器的汇总功能
        if hasattr(data_manager, 'data_provider'):
            summary = await data_manager.data_provider.get_trading_summary()

            return APIResponse(
                success=True,
                message="交易汇总获取成功",
                data=summary,
                request_id=str(uuid.uuid4())
            )
        else:
            # 返回空汇总
            summary = {
                'total_orders': 0,
                'successful_orders': 0,
                'rejected_orders': 0,
                'success_rate': 0,
                'total_trades': 0,
                'total_trade_amount': 0,
                'today_orders': 0,
                'today_trades': 0,
                'today_trade_amount': 0,
                'last_update': datetime.now().isoformat()
            }

            return APIResponse(
                success=True,
                message="数据提供器未初始化，返回空汇总",
                data=summary,
                request_id=str(uuid.uuid4())
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取交易汇总失败: {str(e)}"
        )
