"""
真实交易API接口
提供真实的CTP交易功能
"""

from fastapi import APIRouter, HTTPException
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


def close_today_position(ctp, symbol: str, direction: str, volume: int, price: float, order_type: str):
    """
    平今仓函数

    Args:
        ctp: CTP集成对象
        symbol: 交易品种
        direction: 平仓方向 ('long' 或 'short')
        volume: 平仓手数
        price: 价格
        order_type: 订单类型

    Returns:
        dict: 订单信息，失败时返回None
    """
    try:
        if direction == 'long':
            # 平多单，发送卖出订单
            order_id = ctp.send_order(symbol, 'SELL', volume, price, order_type, 'CLOSETODAY')
            trade_direction = 'SELL'
        else:
            # 平空单，发送买入订单
            order_id = ctp.send_order(symbol, 'BUY', volume, price, order_type, 'CLOSETODAY')
            trade_direction = 'BUY'

        if order_id:
            logger.info(f"✅ 平今仓{direction}单成功: {symbol} {volume}手@{price} (订单ID: {order_id})")
            return {
                'order_id': order_id,
                'symbol': symbol,
                'direction': trade_direction,
                'volume': volume,
                'offset': 'CLOSETODAY',
                'price': price,
                'order_type': order_type
            }
        else:
            logger.warning(f"❌ 平今仓{direction}单失败: {symbol} {volume}手")
            return None

    except Exception as e:
        logger.error(f"平今仓{direction}单异常: {e}")
        return None


def close_yesterday_position(ctp, symbol: str, direction: str, volume: int, price: float, order_type: str):
    """
    平昨仓函数

    Args:
        ctp: CTP集成对象
        symbol: 交易品种
        direction: 平仓方向 ('long' 或 'short')
        volume: 平仓手数
        price: 价格
        order_type: 订单类型

    Returns:
        dict: 订单信息，失败时返回None
    """
    try:
        if direction == 'long':
            # 平多单，发送卖出订单
            order_id = ctp.send_order(symbol, 'SELL', volume, price, order_type, 'CLOSEYESTERDAY')
            trade_direction = 'SELL'
        else:
            # 平空单，发送买入订单
            order_id = ctp.send_order(symbol, 'BUY', volume, price, order_type, 'CLOSEYESTERDAY')
            trade_direction = 'BUY'

        if order_id:
            logger.info(f"✅ 平昨仓{direction}单成功: {symbol} {volume}手@{price} (订单ID: {order_id})")
            return {
                'order_id': order_id,
                'symbol': symbol,
                'direction': trade_direction,
                'volume': volume,
                'offset': 'CLOSEYESTERDAY',
                'price': price,
                'order_type': order_type
            }
        else:
            logger.warning(f"❌ 平昨仓{direction}单失败: {symbol} {volume}手")
            return None

    except Exception as e:
        logger.error(f"平昨仓{direction}单异常: {e}")
        return None


def smart_close_position(ctp, symbol: str, direction: str, volume: int, price: float, order_type: str,
                        today_volume: int = 0, yesterday_volume: int = 0):
    """
    智能平仓函数 - 优先平今仓，再平昨仓

    Args:
        ctp: CTP集成对象
        symbol: 交易品种
        direction: 平仓方向 ('long' 或 'short')
        volume: 需要平仓的手数
        price: 价格
        order_type: 订单类型
        today_volume: 今仓数量
        yesterday_volume: 昨仓数量

    Returns:
        list: 成功发送的订单列表
    """
    orders_sent = []
    remaining_volume = volume

    logger.info(f"🎯 智能平仓: {symbol} {direction} 需平{volume}手, 今仓{today_volume}手, 昨仓{yesterday_volume}手")

    # 第一步：优先平今仓
    if today_volume > 0 and remaining_volume > 0:
        today_close_volume = min(remaining_volume, today_volume)
        order_info = close_today_position(ctp, symbol, direction, today_close_volume, price, order_type)

        if order_info:
            orders_sent.append(order_info)
            remaining_volume -= today_close_volume
            logger.info(f"✅ 今仓平仓成功: {today_close_volume}手, 剩余需平: {remaining_volume}手")
        else:
            # 平今仓失败，尝试平昨仓
            logger.info(f"🔄 平今仓失败，尝试平昨仓: {today_close_volume}手")
            order_info = close_yesterday_position(ctp, symbol, direction, today_close_volume, price, order_type)
            if order_info:
                orders_sent.append(order_info)
                remaining_volume -= today_close_volume
                logger.info(f"✅ 重试昨仓平仓成功: {today_close_volume}手")

    # 第二步：平昨仓
    if yesterday_volume > 0 and remaining_volume > 0:
        yesterday_close_volume = min(remaining_volume, yesterday_volume)
        order_info = close_yesterday_position(ctp, symbol, direction, yesterday_close_volume, price, order_type)

        if order_info:
            orders_sent.append(order_info)
            remaining_volume -= yesterday_close_volume
            logger.info(f"✅ 昨仓平仓成功: {yesterday_close_volume}手, 剩余需平: {remaining_volume}手")
        else:
            # 平昨仓失败，尝试平今仓
            logger.info(f"🔄 平昨仓失败，尝试平今仓: {yesterday_close_volume}手")
            order_info = close_today_position(ctp, symbol, direction, yesterday_close_volume, price, order_type)
            if order_info:
                orders_sent.append(order_info)
                remaining_volume -= yesterday_close_volume
                logger.info(f"✅ 重试今仓平仓成功: {yesterday_close_volume}手")

    # 第三步：如果仍有剩余，尝试按顺序平仓（容错机制）
    if remaining_volume > 0:
        logger.warning(f"⚠️ 仍有{remaining_volume}手未平仓，启用容错机制")

        # 先尝试平今仓
        order_info = close_today_position(ctp, symbol, direction, remaining_volume, price, order_type)
        if order_info:
            orders_sent.append(order_info)
            logger.info(f"✅ 容错机制-今仓平仓成功: {remaining_volume}手")
        else:
            # 再尝试平昨仓
            order_info = close_yesterday_position(ctp, symbol, direction, remaining_volume, price, order_type)
            if order_info:
                orders_sent.append(order_info)
                logger.info(f"✅ 容错机制-昨仓平仓成功: {remaining_volume}手")

    return orders_sent


@router.post("/close_position")
async def close_position(request: Dict[str, Any]):
    """平仓操作 - 重构后的简化版本"""
    try:
        # 验证必需参数
        required_fields = ['symbol']
        for field in required_fields:
            if field not in request:
                raise HTTPException(status_code=400, detail=f"缺少必需参数: {field}")

        symbol = request['symbol']
        volume = request.get('volume', 0)  # 0表示全部平仓
        direction = request.get('direction', 'all').lower()  # 支持指定平仓方向
        price = float(request.get('price', 0))
        order_type = request.get('order_type', 'MARKET').upper()

        ctp = get_ctp_integration()

        # 获取当前持仓
        position_info = ctp.get_position_info(symbol)
        if not position_info:
            raise HTTPException(status_code=404, detail="未找到持仓信息")

        all_orders_sent = []

        logger.info(f"📊 平仓请求: {symbol} {direction} {volume}手 ({order_type})")
        logger.info(f"📊 当前持仓: 多单{position_info['long_position']}手, 空单{position_info['short_position']}手")

        # 处理多单平仓
        if direction in ['long', 'all'] and position_info['long_position'] > 0:
            close_volume = volume if volume > 0 else position_info['long_position']
            close_volume = min(close_volume, position_info['long_position'])

            # 获取多单的今昨仓详情
            long_detail = ctp.get_position_detail(symbol, 'long')
            today_volume = getattr(long_detail, 'today_position', 0)
            yesterday_volume = getattr(long_detail, 'yesterday_position', 0)

            # 使用智能平仓函数
            orders = smart_close_position(ctp, symbol, 'long', close_volume, price, order_type,
                                        today_volume, yesterday_volume)
            all_orders_sent.extend(orders)

        # 处理空单平仓
        if direction in ['short', 'all'] and position_info['short_position'] > 0:
            close_volume = volume if volume > 0 else position_info['short_position']
            close_volume = min(close_volume, position_info['short_position'])

            # 获取空单的今昨仓详情
            short_detail = ctp.get_position_detail(symbol, 'short')
            today_volume = getattr(short_detail, 'today_position', 0)
            yesterday_volume = getattr(short_detail, 'yesterday_position', 0)

            # 使用智能平仓函数
            orders = smart_close_position(ctp, symbol, 'short', close_volume, price, order_type,
                                        today_volume, yesterday_volume)
            all_orders_sent.extend(orders)

        # 检查是否有订单发送成功
        if not all_orders_sent:
            raise HTTPException(status_code=400, detail="没有找到可平仓的持仓或平仓失败")

        # 返回结果
        main_order = all_orders_sent[0] if all_orders_sent else None

        return {
            "success": True,
            "message": f"平仓操作成功，发送了 {len(all_orders_sent)} 个订单",
            "data": {
                "symbol": symbol,
                "position_info": position_info,
                "orders_sent": all_orders_sent,
                "main_order": main_order
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"平仓操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"平仓操作失败: {str(e)}")


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
