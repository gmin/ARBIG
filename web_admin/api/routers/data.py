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
        # 模拟账户数据
        account = AccountInfo(
            account_id="123456789",
            total_assets=1000000.00,
            available=850000.00,
            margin=150000.00,
            frozen=0.00,
            profit=25000.00,
            today_profit=5000.00,
            commission=120.50,
            currency="CNY",
            update_time=datetime.now()
        )
        
        return AccountResponse(
            success=True,
            message="账户信息获取成功",
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
        # 模拟持仓数据
        positions = [
            PositionInfo(
                symbol="au2509",
                direction="long",
                volume=5.0,
                avg_price=483.20,
                current_price=485.50,
                profit=11500.00,
                margin=120000.00,
                open_time=datetime.now()
            ),
            PositionInfo(
                symbol="au2512",
                direction="short",
                volume=2.0,
                avg_price=486.80,
                current_price=485.20,
                profit=3200.00,
                margin=48000.00,
                open_time=datetime.now()
            )
        ]
        
        return PositionsResponse(
            success=True,
            message="持仓信息获取成功",
            data={"positions": positions},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取持仓信息失败: {str(e)}"
        )

@router.get("/risk/metrics", response_model=RiskResponse, summary="获取风险指标")
async def get_risk_metrics(data_manager=Depends(get_data_manager)):
    """获取风险指标"""
    try:
        # 模拟风险数据
        risk_metrics = RiskMetrics(
            risk_level="medium",
            position_ratio=0.65,
            daily_loss=-2500.00,
            max_drawdown=-8500.00,
            var_95=-15000.00,
            leverage=3.2,
            concentration={
                "au2509": 0.8,
                "au2512": 0.2
            }
        )
        
        return RiskResponse(
            success=True,
            message="风险指标获取成功",
            data=risk_metrics,
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
    limit: int = Query(100, description="返回数量限制"),
    data_manager=Depends(get_data_manager)
):
    """获取订单列表"""
    try:
        # 模拟订单数据
        orders = [
            {
                "order_id": "order_12345678",
                "symbol": "au2509",
                "direction": "LONG",
                "volume": 1.0,
                "price": 485.50,
                "type": "LIMIT",
                "status": "submitted",
                "submit_time": datetime.now().isoformat()
            }
        ]

        return APIResponse(
            success=True,
            message="订单列表获取成功",
            data={"orders": orders},
            request_id=str(uuid.uuid4())
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取订单列表失败: {str(e)}"
        )
