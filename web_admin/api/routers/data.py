"""
数据查询API路由
提供行情数据、账户数据、风控数据等查询接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from ..models.requests import MarketDataRequest, AnalysisRequest, OrderRequest
from ..models.responses import (
    APIResponse, MarketDataResponse, AccountResponse, PositionsResponse,
    RiskResponse, TickData, AccountInfo, PositionInfo, RiskMetrics
)
from ..dependencies import get_data_manager
from core.market_data_client import get_market_data_client

router = APIRouter(prefix="/api/v1/data", tags=["数据查询"])

@router.get("/market/price/{symbol}", summary="从Redis获取最新价格")
async def get_latest_price_from_redis(symbol: str):
    """从Redis获取指定合约的最新价格"""
    try:
        market_client = get_market_data_client()
        if not market_client:
            return {"success": False, "message": "市场数据客户端不可用", "data": None}

        # 获取最新价格
        latest_price = market_client.get_latest_price(symbol)

        # 获取买卖价
        bid_price, ask_price = market_client.get_bid_ask_price(symbol)

        # 获取完整Tick数据
        tick = market_client.get_latest_tick(symbol)

        return {
            "success": True,
            "message": "获取成功",
            "data": {
                "symbol": symbol,
                "latest_price": latest_price,
                "bid_price": bid_price,
                "ask_price": ask_price,
                "tick_data": {
                    "last_price": tick.last_price if tick else None,
                    "volume": tick.volume if tick else None,
                    "time": tick.time.isoformat() if tick and tick.time else None
                } if tick else None
            }
        }
    except Exception as e:
        logger.error(f"获取Redis行情数据失败: {e}")
        return {"success": False, "message": f"获取失败: {str(e)}", "data": None}

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

                    # 判断持仓方向 - 支持多种可能的值
                    direction_value = position_data.direction.value
                    if direction_value in ["多", "LONG", "Long", "long"]:
                        direction = "long"
                    elif direction_value in ["空", "SHORT", "Short", "short"]:
                        direction = "short"
                    else:
                        logger.warning(f"未知的持仓方向值: {direction_value}")
                        direction = "unknown"

                    position = PositionInfo(
                        symbol=position_data.symbol,
                        direction=direction,
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
    print(f"DEBUG: ===== send_order函数开始执行 =====")
    print(f"DEBUG: request: {request}")
    print(f"DEBUG: request.order_type: {request.order_type}")
    try:
        # 检查服务容器是否可用
        print(f"DEBUG: hasattr(data_manager, 'services'): {hasattr(data_manager, 'services')}")
        if hasattr(data_manager, 'services'):
            print(f"DEBUG: data_manager.services: {data_manager.services}")
        else:
            raise HTTPException(status_code=503, detail="服务容器未连接 - 没有services属性")

        service_container = data_manager

        # 调试：打印所有服务
        print(f"DEBUG: Available services: {list(service_container.services.keys())}")
        print(f"DEBUG: Services dict: {service_container.services}")

        # 检查交易服务是否运行
        trading_service = service_container.services.get('TradingService')
        if not trading_service:
            raise HTTPException(status_code=503, detail=f"交易服务未启动，可用服务: {list(service_container.services.keys())}")

        print(f"DEBUG: trading_service found: {trading_service}")
        print(f"DEBUG: trading_service type: {type(trading_service)}")

        # 转换请求格式为vnpy OrderRequest
        from core.types import OrderRequest as VnpyOrderRequest, Direction, OrderType, Offset, Exchange

        # 转换方向
        direction = Direction.LONG if request.direction.lower() in ['long', 'buy'] else Direction.SHORT

        # 转换订单类型 - CTP不支持真正的市价单，使用限价单模拟
        # 市价单在CTP中需要使用限价单 + 对手价实现
        order_type = OrderType.LIMIT  # CTP只支持限价单

        # 转换开平仓
        offset = Offset.OPEN  # 默认开仓，后续可以根据需要扩展

        # 处理价格 - 市价单需要合理的价格
        order_price = 0.0
        print(f"DEBUG: ===== 开始处理订单价格 =====")
        print(f"DEBUG: request.price: {request.price}")
        print(f"DEBUG: request.order_type: {request.order_type}")
        print(f"DEBUG: order_type: {order_type}")
        print(f"DEBUG: OrderType.LIMIT: {OrderType.LIMIT}")
        print(f"DEBUG: order_type == OrderType.LIMIT: {order_type == OrderType.LIMIT}")

        if request.price:
            order_price = float(request.price)
            print(f"DEBUG: 使用用户指定价格: {order_price}")
        elif request.order_type.lower() == 'market':
            print(f"DEBUG: 进入市价单处理逻辑...")
            # 市价单：先确保订阅了行情，然后获取当前市场价格
            try:
                # 1. 先确保订阅了行情
                market_data_service = data_manager.services.get('MarketDataService')
                if market_data_service:
                    print(f"DEBUG: 尝试订阅合约行情: {request.symbol}")
                    subscribe_success = market_data_service.subscribe_symbol(request.symbol, 'web_order')
                    print(f"DEBUG: 订阅结果: {subscribe_success}")

                    # 等待一下让行情数据到达
                    import time
                    time.sleep(2)

                # 2. 获取市场价格
                market_client = get_market_data_client()
                print(f"DEBUG: market_client: {market_client}")
                if market_client:
                    # 使用专门的方法获取订单价格
                    market_price = market_client.get_market_price_for_order(
                        request.symbol,
                        'long' if direction == Direction.LONG else 'short'
                    )
                    print(f"DEBUG: market_price from Redis: {market_price}")

                    if market_price and market_price > 0:
                        # 市价单使用更激进的价格确保成交
                        if direction == Direction.LONG:
                            # 买入时使用稍高价格
                            order_price = market_price * 1.01  # 高1%
                        else:
                            # 卖出时使用稍低价格
                            order_price = market_price * 0.99  # 低1%
                        print(f"DEBUG: 市价单使用激进价格: {order_price} (基准价: {market_price})")
                    else:
                        # 如果还是没有行情，尝试从CTP网关直接获取
                        print(f"DEBUG: Redis无行情，尝试从CTP网关获取...")
                        ctp_gateway = getattr(data_manager, 'ctp_gateway', None)
                        if ctp_gateway:
                            tick_data = ctp_gateway.get_tick(request.symbol)
                            if tick_data and tick_data.last_price > 0:
                                market_price = tick_data.last_price
                                if direction == Direction.LONG:
                                    order_price = market_price * 1.01
                                else:
                                    order_price = market_price * 0.99
                                print(f"DEBUG: 从CTP获取价格: {market_price}, 使用价格: {order_price}")
                            else:
                                print(f"DEBUG: CTP也无行情数据，拒绝市价单")
                                return {"success": False, "message": f"无法获取 {request.symbol} 的行情数据，无法执行市价单"}
                        else:
                            print(f"DEBUG: CTP网关不可用，拒绝市价单")
                            return {"success": False, "message": "CTP网关不可用，无法执行市价单"}
                else:
                    print(f"DEBUG: 市场数据客户端不可用，拒绝市价单")
                    return {"success": False, "message": "市场数据客户端不可用，无法执行市价单"}
            except Exception as e:
                print(f"DEBUG: 获取市场价格失败: {e}")
                return {"success": False, "message": f"获取市场价格失败: {str(e)}"}
        else:
            print(f"DEBUG: 限价单但无价格，保持0.0: {order_price}")

        print(f"DEBUG: 最终订单价格: {order_price}")
        print(f"DEBUG: ===== 价格处理完成 =====")

        # 创建vnpy订单请求
        vnpy_order_req = VnpyOrderRequest(
            symbol=request.symbol,
            exchange=Exchange.SHFE,  # 默认上期所
            direction=direction,
            type=order_type,
            volume=float(request.volume),
            price=order_price,
            offset=offset,
            reference=f"web_api_{datetime.now().strftime('%H%M%S')}"
        )

        # 发送订单 - 直接调用本地服务，无需HTTP转发
        order_id = trading_service.send_order(vnpy_order_req)

        if order_id:
            return APIResponse(
                success=True,
                message="订单发送成功",
                data={
                    "order_id": order_id,
                    "symbol": request.symbol,
                    "direction": request.direction,
                    "volume": request.volume,
                    "price": request.price,
                    "type": request.order_type,
                    "status": "submitted",
                    "submit_time": datetime.now().isoformat()
                },
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(status_code=400, detail="订单发送失败")

    except HTTPException:
        raise
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
        # 检查服务容器是否可用
        if not hasattr(data_manager, 'service_container') or not data_manager.service_container:
            raise HTTPException(status_code=503, detail="交易服务未连接")

        service_container = data_manager.service_container

        # 获取交易服务
        trading_service = data_manager.services.get('TradingService')
        if not trading_service:
            raise HTTPException(status_code=503, detail="交易服务未启动")

        # 撤销订单
        success = trading_service.cancel_order(order_id)

        if success:
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
        else:
            raise HTTPException(status_code=400, detail="订单撤销失败")

    except HTTPException:
        raise
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
