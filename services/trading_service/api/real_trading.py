"""
真实交易API接口
提供真实的CTP交易功能
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from services.trading_service.core.ctp_integration import get_ctp_integration
from shared.database.connection import get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/real_trading", tags=["real_trading"])

@router.get("/status")
async def get_ctp_status():
    """获取CTP连接状态"""
    try:
        ctp = get_ctp_integration()
        status = ctp.get_status()

        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取CTP状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取CTP状态失败: {str(e)}")

@router.post("/subscribe/{symbol}")
async def subscribe_symbol(symbol: str):
    """手动订阅合约行情"""
    try:
        ctp = get_ctp_integration()

        # 确保CTP已连接
        if not ctp.running or not ctp.md_connected:
            raise HTTPException(status_code=503, detail="CTP行情服务未连接")

        # 检查合约是否存在
        if symbol not in ctp.contracts:
            raise HTTPException(status_code=404, detail=f"合约 {symbol} 不存在")

        # 订阅行情
        from vnpy.trader.object import SubscribeRequest
        contract = ctp.contracts[symbol]
        req = SubscribeRequest(
            symbol=contract.symbol,
            exchange=contract.exchange
        )
        ctp.ctp_gateway.subscribe(req)

        logger.info(f"手动订阅合约: {symbol}")

        return {
            "success": True,
            "message": f"已订阅合约 {symbol} 行情",
            "symbol": symbol,
            "exchange": contract.exchange.value,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"订阅合约失败: {e}")
        raise HTTPException(status_code=500, detail=f"订阅合约失败: {str(e)}")

@router.get("/account")
async def get_account_info():
    """获取账户信息"""
    try:
        ctp = get_ctp_integration()
        account_info = ctp.get_account_info()

        if not account_info:
            raise HTTPException(status_code=404, detail="账户信息不可用，请检查CTP连接")

        return {
            "success": True,
            "data": account_info,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取账户信息失败: {str(e)}")

@router.get("/positions")
async def get_positions(symbol: Optional[str] = None):
    """获取持仓信息"""
    try:
        ctp = get_ctp_integration()
        position_info = ctp.get_position_info(symbol)

        return {
            "success": True,
            "data": position_info,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取持仓信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取持仓信息失败: {str(e)}")


@router.get("/ticks/debug")
async def debug_ticks():
    """调试：获取行情数据键名"""
    try:
        ctp = get_ctp_integration()

        # 获取行情数据键名
        tick_keys = list(ctp.ticks.keys())[:20]  # 显示前20个

        return {
            "success": True,
            "data": {
                "tick_keys": tick_keys,
                "tick_count": len(ctp.ticks)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取调试行情信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试行情信息失败: {str(e)}")

@router.get("/tick/{symbol}")
async def get_real_tick(symbol: str):
    """获取真实行情数据"""
    try:
        ctp = get_ctp_integration()

        # 确保CTP已连接
        if not ctp.running or not ctp.md_connected:
            raise HTTPException(status_code=503, detail=f"CTP行情服务未连接")

        tick_data = ctp.get_latest_tick(symbol)

        if not tick_data:
            raise HTTPException(status_code=404, detail=f"合约 {symbol} 行情数据不可用，请检查合约代码或等待行情推送")

        # 添加数据来源标识
        tick_data['data_source'] = 'CTP_REAL'
        tick_data['server_time'] = datetime.now().isoformat()

        return {
            "success": True,
            "data": tick_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取真实行情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取真实行情失败: {str(e)}")

@router.get("/trades/{strategy_name}")
async def get_strategy_trades(
    strategy_name: str,
    since: Optional[str] = Query(None, description="查询此时间之后的成交，格式：YYYY-MM-DD HH:MM:SS")
):
    """获取策略的成交数据（类似tick数据的轮询方式）"""
    try:
        ctp = get_ctp_integration()

        # 解析since参数
        since_time = None
        if since:
            try:
                since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="时间格式错误，应为：YYYY-MM-DD HH:MM:SS")

        # 从CTP集成中获取成交数据
        trades = ctp.get_trades_by_strategy(strategy_name, since_time)

        return {
            "success": True,
            "data": {
                "strategy_name": strategy_name,
                "trades": trades,
                "count": len(trades)
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略成交数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略成交数据失败: {str(e)}")

@router.get("/orders")
async def get_orders():
    """获取订单列表"""
    try:
        ctp = get_ctp_integration()

        # 获取所有订单
        orders_data = []
        for order_id, order in ctp.orders.items():
            orders_data.append({
                'order_id': order_id,
                'symbol': order.symbol,
                'direction': order.direction.value,
                'volume': order.volume,
                'traded': order.traded,
                'price': order.price,
                'status': order.status.value,
                'time': order.datetime.isoformat() if order.datetime else None
            })

        return {
            "success": True,
            "data": orders_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订单列表失败: {str(e)}")

@router.post("/order")
async def send_real_order(request: Dict[str, Any]):
    """发送真实订单"""
    try:
        # 验证必需参数
        required_fields = ['symbol', 'direction', 'volume']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"缺少必需参数: {field}")

        symbol = request['symbol']
        direction = request['direction'].upper()
        volume = int(request['volume'])
        price = float(request.get('price', 0))
        order_type = request.get('order_type', 'MARKET').upper()
        offset = request.get('offset', 'AUTO').upper()  # 支持手动指定开平仓
        
        # 验证参数
        if direction not in ['BUY', 'SELL']:
            raise HTTPException(status_code=400, detail="direction必须是BUY或SELL")
        
        if volume <= 0:
            raise HTTPException(status_code=400, detail="volume必须大于0")
        
        if order_type not in ['MARKET', 'LIMIT']:
            raise HTTPException(status_code=400, detail="order_type必须是MARKET或LIMIT")
        
        if order_type == 'LIMIT' and price <= 0:
            raise HTTPException(status_code=400, detail="限价单必须指定价格")

        # 智能判断开平仓
        ctp = get_ctp_integration()
        if offset == 'AUTO':
            offset = ctp.get_smart_offset(symbol, direction)

        # 发送订单
        order_id = ctp.send_order(symbol, direction, volume, price, order_type, offset)
        
        if not order_id:
            raise HTTPException(status_code=500, detail="订单发送失败")
        
        # 记录到数据库
        try:
            db_manager = get_db_manager()
            await db_manager.execute_insert("""
                INSERT INTO orders 
                (order_id, account_id, symbol, direction, volume, price, order_type, status, order_time, create_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                "CTP_ACCOUNT",  # 实际应该从CTP获取
                symbol,
                direction.lower(),
                volume,
                price,
                order_type.lower(),
                "pending",
                datetime.now(),
                datetime.now()
            ))
        except Exception as db_e:
            logger.warning(f"订单数据库记录失败: {db_e}")
        
        logger.info(f"✅ 真实订单发送成功: {symbol} {direction} {volume}@{price}")
        
        return {
            "success": True,
            "message": "订单发送成功",
            "data": {
                "order_id": order_id,
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "price": price,
                "order_type": order_type,
                "offset": offset
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送真实订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送真实订单失败: {str(e)}")

@router.delete("/order/{order_id}")
async def cancel_real_order(order_id: str):
    """撤销真实订单"""
    try:
        ctp = get_ctp_integration()
        success = ctp.cancel_order(order_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="订单撤销失败")
        
        # 更新数据库状态
        try:
            db_manager = get_db_manager()
            await db_manager.execute_update("""
                UPDATE orders 
                SET status = 'cancelled', update_time = %s
                WHERE order_id = %s
            """, (datetime.now(), order_id))
        except Exception as db_e:
            logger.warning(f"订单状态更新失败: {db_e}")
        
        logger.info(f"✅ 订单撤销成功: {order_id}")
        
        return {
            "success": True,
            "message": "订单撤销成功",
            "data": {"order_id": order_id},
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销真实订单失败: {e}")
        raise HTTPException(status_code=500, detail=f"撤销真实订单失败: {str(e)}")


# 平仓辅助函数已删除，现在前端控制平仓逻辑，后端只提供simple_close接口


# close_position接口已删除，现在使用simple_close接口

# close_position接口已删除，现在使用simple_close接口


@router.post("/simple_close")
async def simple_close_position(request: Dict[str, Any]):
    """简单平仓接口 - 前端控制逻辑"""
    try:
        # 验证必需参数
        required_fields = ['symbol', 'direction', 'volume', 'offset_type']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"缺少必需参数: {field}")

        symbol = request['symbol']
        direction = request['direction'].lower()  # 'long' 或 'short'
        volume = int(request['volume'])
        offset_type = request['offset_type'].upper()  # 'TODAY' 或 'YESTERDAY'
        price = float(request.get('price', 0))
        order_type = request.get('order_type', 'MARKET').upper()

        if volume <= 0:
            raise HTTPException(status_code=400, detail="平仓数量必须大于0")

        if offset_type not in ['TODAY', 'YESTERDAY']:
            raise HTTPException(status_code=400, detail="offset_type必须是TODAY或YESTERDAY")

        ctp = get_ctp_integration()

        # 根据方向和今昨仓类型发送订单
        if direction == 'long':
            # 平多单，发送卖出订单
            trade_direction = 'SELL'
            offset_flag = 'CLOSETODAY' if offset_type == 'TODAY' else 'CLOSEYESTERDAY'
        elif direction == 'short':
            # 平空单，发送买入订单
            trade_direction = 'BUY'
            offset_flag = 'CLOSETODAY' if offset_type == 'TODAY' else 'CLOSEYESTERDAY'
        else:
            raise HTTPException(status_code=400, detail="direction必须是long或short")

        # 发送订单
        order_id = ctp.send_order(symbol, trade_direction, volume, price, order_type, offset_flag)

        if not order_id:
            raise HTTPException(status_code=400, detail="订单发送失败")

        logger.info(f"✅ 简单平仓成功: {symbol} {direction} {volume}手 ({offset_type})")

        return {
            "success": True,
            "message": f"平仓订单发送成功",
            "data": {
                "order_id": order_id,
                "symbol": symbol,
                "direction": trade_direction,
                "volume": volume,
                "offset": offset_flag,
                "price": price,
                "order_type": order_type
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简单平仓失败: {e}")
        raise HTTPException(status_code=500, detail=f"简单平仓失败: {str(e)}")

@router.post("/strategy_signal")
async def handle_strategy_signal(request: Dict[str, Any]):
    """处理策略信号"""
    try:
        # 验证必需参数
        required_fields = ['strategy_name', 'symbol', 'direction', 'action', 'volume']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"缺少必需参数: {field}")

        strategy_name = request['strategy_name']
        symbol = request['symbol']
        direction = request['direction'].upper()
        action = request['action'].upper()
        volume = int(request['volume'])
        price = float(request.get('price', 0))
        order_type = 'MARKET' if price == 0 else 'LIMIT'
        order_id = request.get('order_id', f"STRATEGY_{uuid.uuid4().hex[:8].upper()}")



        logger.info(f"📨 收到策略信号: {strategy_name} {action} {direction} {volume}@{price}")

        # 验证参数
        if direction not in ['LONG', 'SHORT']:
            raise HTTPException(status_code=400, detail="direction必须是LONG或SHORT")

        if action not in ['BUY', 'SELL', 'OPEN', 'CLOSE']:
            raise HTTPException(status_code=400, detail="action必须是BUY、SELL、OPEN或CLOSE")

        if volume <= 0:
            raise HTTPException(status_code=400, detail="volume必须大于0")

        # 转换策略信号为CTP订单
        ctp = get_ctp_integration()

        # 根据策略信号确定交易方向和开平仓
        if action in ['BUY', 'OPEN']:
            if direction == 'LONG':
                trade_direction = 'BUY'
                offset = 'OPEN'
            else:  # SHORT
                trade_direction = 'SELL'
                offset = 'OPEN'
        else:  # SELL, CLOSE
            if direction == 'LONG':
                trade_direction = 'SELL'
                offset = 'AUTO'  # 智能平仓
            else:  # SHORT
                trade_direction = 'BUY'
                offset = 'AUTO'  # 智能平仓

        # 发送订单到CTP
        ctp_order_id = ctp.send_order(symbol, trade_direction, volume, price, order_type, offset)

        if not ctp_order_id:
            raise HTTPException(status_code=500, detail="CTP订单发送失败")

        logger.info(f"✅ 策略信号转换为CTP订单成功: {strategy_name} -> {ctp_order_id}")

        return {
            "success": True,
            "message": "策略信号处理成功",
            "data": {
                "order_id": ctp_order_id,
                "strategy_name": strategy_name,
                "symbol": symbol,
                "direction": direction,
                "action": action,
                "volume": volume,
                "price": price,
                "order_type": order_type
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理策略信号失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理策略信号失败: {str(e)}")

@router.get("/status")
async def get_trading_status():
    """获取交易服务状态"""
    try:
        ctp = get_ctp_integration()

        # 检查CTP连接状态
        ctp_status = "connected" if ctp and hasattr(ctp, 'is_connected') and ctp.is_connected() else "disconnected"

        return {
            "success": True,
            "message": "交易服务运行正常",
            "data": {
                "service": "交易服务",
                "status": "running",
                "ctp_status": ctp_status,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取交易状态失败: {e}")
        return {
            "success": False,
            "message": f"获取交易状态失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.post("/test_connection")
async def test_ctp_connection():
    """测试CTP连接"""
    try:
        ctp = get_ctp_integration()

        # 重新连接
        if not ctp.running:
            if await ctp.initialize():
                await ctp.connect()

        status = ctp.get_status()

        return {
            "success": True,
            "message": "CTP连接测试完成",
            "data": {
                "connection_status": status,
                "recommendations": [
                    "如果连接失败，请检查网络连接",
                    "确认CTP账户信息正确",
                    "检查config/ctp_sim.json配置文件",
                    "确认在交易时间内进行测试"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"CTP连接测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"CTP连接测试失败: {str(e)}")
