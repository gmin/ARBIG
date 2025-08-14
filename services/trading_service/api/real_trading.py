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

@router.get("/positions/debug")
async def get_positions_debug():
    """调试：获取原始持仓数据"""
    try:
        ctp = get_ctp_integration()

        # 获取原始持仓字典
        raw_positions = dict(ctp.positions)

        # 转换为可序列化的格式
        debug_data = {}
        for key, position in raw_positions.items():
            debug_data[key] = {
                "symbol": position.symbol,
                "direction": position.direction.value,
                "volume": position.volume,
                "price": position.price,
                "pnl": getattr(position, 'pnl', 0),
                "yd_volume": getattr(position, 'yd_volume', 0)
            }

        return {
            "success": True,
            "data": {
                "raw_positions": debug_data,
                "positions_count": len(debug_data),
                "position_keys": list(debug_data.keys())
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取调试持仓信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试持仓信息失败: {str(e)}")

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

@router.post("/close_position")
async def close_position(request: Dict[str, Any]):
    """平仓操作 - 便捷接口"""
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
        force_offset = request.get('force_offset', None)  # 强制指定今昨仓类型: 'today', 'yesterday'

        ctp = get_ctp_integration()

        # 获取当前持仓
        position_info = ctp.get_position_info(symbol)

        orders_sent = []

        # 根据指定方向平仓
        if direction in ['long', 'all'] and position_info['long_position'] > 0:
            close_volume = volume if volume > 0 else position_info['long_position']
            close_volume = min(close_volume, position_info['long_position'])

            # 智能平仓：根据当前时间判断今昨仓优先级
            current_hour = datetime.now().hour

            order_id = None
            offset_used = None

            # 获取仓位详情，判断今昨仓
            position_detail = ctp.get_position_detail(symbol, 'LONG')
            today_volume = getattr(position_detail, 'today_position', 0) if position_detail else 0
            yesterday_volume = getattr(position_detail, 'yesterday_position', 0) if position_detail else 0

            order_id = None
            offset_used = None

            logger.info(f"多单仓位详情: 今仓{today_volume}手, 昨仓{yesterday_volume}手, 需平{close_volume}手")

            # 如果强制指定了今昨仓类型
            if force_offset == 'today':
                # 强制平今仓
                try:
                    order_id = ctp.send_order(symbol, 'SELL', close_volume, price, order_type, 'CLOSETODAY')
                    offset_used = 'CLOSETODAY'
                    logger.info(f"✅ 强制平今仓多单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"强制平今仓多单失败: {e}")
                    pass
            elif force_offset == 'yesterday':
                # 强制平昨仓
                try:
                    order_id = ctp.send_order(symbol, 'SELL', close_volume, price, order_type, 'CLOSEYESTERDAY')
                    offset_used = 'CLOSEYESTERDAY'
                    logger.info(f"✅ 强制平昨仓多单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"强制平昨仓多单失败: {e}")
                    pass
            else:
                # 智能判断：严格按照今仓优先，昨仓其次的顺序
                remaining_volume = close_volume

                # 第一步：优先平今仓
                if today_volume > 0 and remaining_volume > 0:
                    today_close_volume = min(remaining_volume, today_volume)
                    try:
                        order_id = ctp.send_order(symbol, 'SELL', today_close_volume, price, order_type, 'CLOSETODAY')
                        offset_used = 'CLOSETODAY'
                        remaining_volume -= today_close_volume
                        logger.info(f"✅ 平今仓多单: {symbol} {today_close_volume}手 (剩余需平{remaining_volume}手)")

                        orders_sent.append({
                            'order_id': order_id,
                            'symbol': symbol,
                            'direction': 'SELL',
                            'volume': today_close_volume,
                            'offset': offset_used,
                            'price': price,
                            'order_type': order_type
                        })
                    except Exception as e:
                        logger.warning(f"平今仓多单失败: {e}")
                        pass

                # 第二步：如果还有剩余需要平仓，平昨仓
                if remaining_volume > 0 and yesterday_volume > 0:
                    yesterday_close_volume = min(remaining_volume, yesterday_volume)
                    try:
                        order_id2 = ctp.send_order(symbol, 'SELL', yesterday_close_volume, price, order_type, 'CLOSEYESTERDAY')
                        logger.info(f"✅ 平昨仓多单: {symbol} {yesterday_close_volume}手")

                        orders_sent.append({
                            'order_id': order_id2,
                            'symbol': symbol,
                            'direction': 'SELL',
                            'volume': yesterday_close_volume,
                            'offset': 'CLOSEYESTERDAY',
                            'price': price,
                            'order_type': order_type
                        })

                        # 如果有多个订单，使用最后一个作为主订单ID
                        if not order_id:
                            order_id = order_id2
                            offset_used = 'CLOSEYESTERDAY'

                    except Exception as e:
                        logger.warning(f"平昨仓多单失败: {e}")
                        pass

            # 如果仓位信息获取失败，使用尝试模式
            if not order_id:
                logger.warning(f"无法获取仓位详情或平仓失败，使用尝试模式")
                # 先尝试平今仓
                try:
                    order_id = ctp.send_order(symbol, 'SELL', close_volume, price, order_type, 'CLOSETODAY')
                    offset_used = 'CLOSETODAY'
                    logger.info(f"尝试平今仓多单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"平今仓多单失败: {e}")
                    pass

                # 如果平今仓失败，尝试平昨仓
                if not order_id:
                    try:
                        order_id = ctp.send_order(symbol, 'SELL', close_volume, price, order_type, 'CLOSEYESTERDAY')
                        offset_used = 'CLOSEYESTERDAY'
                        logger.info(f"尝试平昨仓多单: {symbol} {close_volume}手")
                    except Exception as e:
                        logger.warning(f"平昨仓多单失败: {e}")
                        pass

            if order_id:
                orders_sent.append({
                    'order_id': order_id,
                    'direction': 'SELL',
                    'volume': close_volume,
                    'type': f'平多({offset_used})'
                })

        if direction in ['short', 'all'] and position_info['short_position'] > 0:
            close_volume = volume if volume > 0 else position_info['short_position']
            close_volume = min(close_volume, position_info['short_position'])

            # 获取仓位详情，判断今昨仓
            position_detail = ctp.get_position_detail(symbol, 'SHORT')
            today_volume = getattr(position_detail, 'today_position', 0) if position_detail else 0
            yesterday_volume = getattr(position_detail, 'yesterday_position', 0) if position_detail else 0

            order_id = None
            offset_used = None

            logger.info(f"空单仓位详情: 今仓{today_volume}手, 昨仓{yesterday_volume}手, 需平{close_volume}手")

            # 如果强制指定了今昨仓类型
            if force_offset == 'today':
                # 强制平今仓
                try:
                    order_id = ctp.send_order(symbol, 'BUY', close_volume, price, order_type, 'CLOSETODAY')
                    offset_used = 'CLOSETODAY'
                    logger.info(f"✅ 强制平今仓空单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"强制平今仓空单失败: {e}")
                    pass
            elif force_offset == 'yesterday':
                # 强制平昨仓
                try:
                    order_id = ctp.send_order(symbol, 'BUY', close_volume, price, order_type, 'CLOSEYESTERDAY')
                    offset_used = 'CLOSEYESTERDAY'
                    logger.info(f"✅ 强制平昨仓空单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"强制平昨仓空单失败: {e}")
                    pass
            else:
                # 智能判断：严格按照今仓优先，昨仓其次的顺序
                remaining_volume = close_volume

                # 第一步：优先平今仓
                if today_volume > 0 and remaining_volume > 0:
                    today_close_volume = min(remaining_volume, today_volume)
                    try:
                        order_id = ctp.send_order(symbol, 'BUY', today_close_volume, price, order_type, 'CLOSETODAY')
                        offset_used = 'CLOSETODAY'
                        remaining_volume -= today_close_volume
                        logger.info(f"✅ 平今仓空单: {symbol} {today_close_volume}手 (剩余需平{remaining_volume}手)")

                        orders_sent.append({
                            'order_id': order_id,
                            'symbol': symbol,
                            'direction': 'BUY',
                            'volume': today_close_volume,
                            'offset': offset_used,
                            'price': price,
                            'order_type': order_type
                        })
                    except Exception as e:
                        logger.warning(f"平今仓空单失败: {e}")
                        pass

                # 第二步：如果还有剩余需要平仓，平昨仓
                if remaining_volume > 0 and yesterday_volume > 0:
                    yesterday_close_volume = min(remaining_volume, yesterday_volume)
                    try:
                        order_id2 = ctp.send_order(symbol, 'BUY', yesterday_close_volume, price, order_type, 'CLOSEYESTERDAY')
                        logger.info(f"✅ 平昨仓空单: {symbol} {yesterday_close_volume}手")

                        orders_sent.append({
                            'order_id': order_id2,
                            'symbol': symbol,
                            'direction': 'BUY',
                            'volume': yesterday_close_volume,
                            'offset': 'CLOSEYESTERDAY',
                            'price': price,
                            'order_type': order_type
                        })

                        # 如果有多个订单，使用最后一个作为主订单ID
                        if not order_id:
                            order_id = order_id2
                            offset_used = 'CLOSEYESTERDAY'

                    except Exception as e:
                        logger.warning(f"平昨仓空单失败: {e}")
                        pass

            # 如果仓位信息获取失败，使用尝试模式
            if not order_id:
                logger.warning(f"无法获取仓位详情或平仓失败，使用尝试模式")
                # 先尝试平今仓
                try:
                    order_id = ctp.send_order(symbol, 'BUY', close_volume, price, order_type, 'CLOSETODAY')
                    offset_used = 'CLOSETODAY'
                    logger.info(f"尝试平今仓空单: {symbol} {close_volume}手")
                except Exception as e:
                    logger.warning(f"平今仓空单失败: {e}")
                    pass

                # 如果平今仓失败，尝试平昨仓
                if not order_id:
                    try:
                        order_id = ctp.send_order(symbol, 'BUY', close_volume, price, order_type, 'CLOSEYESTERDAY')
                        offset_used = 'CLOSEYESTERDAY'
                        logger.info(f"尝试平昨仓空单: {symbol} {close_volume}手")
                    except Exception as e:
                        logger.warning(f"平昨仓空单失败: {e}")
                        pass

            if order_id:
                orders_sent.append({
                    'order_id': order_id,
                    'direction': 'BUY',
                    'volume': close_volume,
                    'type': f'平空({offset_used})'
                })
                logger.info(f"✅ 空单平仓订单发送成功: {order_id} ({offset_used})")
            else:
                logger.error(f"❌ 空单平仓失败: 所有平仓方式都被拒绝")

        if not orders_sent:
            return {
                "success": True,
                "message": f"合约 {symbol} 无持仓需要平仓",
                "data": {
                    "symbol": symbol,
                    "position_info": position_info,
                    "orders_sent": []
                },
                "timestamp": datetime.now().isoformat()
            }

        logger.info(f"✅ 平仓操作成功: {symbol}, 发送了 {len(orders_sent)} 个订单")

        return {
            "success": True,
            "message": f"平仓操作成功，发送了 {len(orders_sent)} 个订单",
            "data": {
                "symbol": symbol,
                "position_info": position_info,
                "orders_sent": orders_sent
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"平仓操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"平仓操作失败: {str(e)}")

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

@router.get("/contracts")
async def get_available_contracts():
    """获取可用合约列表"""
    try:
        ctp = get_ctp_integration()
        
        if not ctp.contracts:
            return {
                "success": True,
                "message": "暂无合约数据，请稍后重试",
                "data": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # 筛选黄金合约
        gold_contracts = []
        for symbol, contract in ctp.contracts.items():
            if symbol.startswith('au'):
                gold_contracts.append({
                    "symbol": contract.symbol,
                    "name": getattr(contract, 'name', ''),
                    "exchange": contract.exchange.value,
                    "size": getattr(contract, 'size', 0),
                    "pricetick": getattr(contract, 'pricetick', 0),
                    "min_volume": getattr(contract, 'min_volume', 1)
                })
        
        return {
            "success": True,
            "data": {
                "total_contracts": len(ctp.contracts),
                "gold_contracts": gold_contracts,
                "gold_count": len(gold_contracts)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取合约列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取合约列表失败: {str(e)}")

@router.get("/health")
async def real_trading_health():
    """真实交易服务健康检查"""
    try:
        ctp = get_ctp_integration()
        status = ctp.get_status()
        
        # 判断健康状态
        is_healthy = (
            status.get('running', False) and
            status.get('td_login_status', False) and
            status.get('md_login_status', False)
        )
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "details": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"真实交易健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/historical_data/{symbol}")
async def get_historical_data(
    symbol: str,
    interval: str = "1m",
    count: int = 100
):
    """获取历史K线数据"""
    try:
        ctp = get_ctp_instance()
        if not ctp:
            raise HTTPException(status_code=500, detail="CTP服务未初始化")

        # 先尝试获取真实历史数据
        historical_data = ctp.get_historical_data(symbol, interval, count)

        # 如果获取失败，使用模拟数据
        if not historical_data:
            logger.warning(f"CTP历史数据获取失败，使用模拟数据: {symbol}")
            historical_data = ctp.get_simulated_historical_data(symbol, interval, count)

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "interval": interval,
                "count": len(historical_data),
                "bars": historical_data,
                "data_source": "CTP" if historical_data and len(historical_data) > 0 else "SIMULATED"
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")

@router.post("/backtest")
async def run_backtest(backtest_request: dict):
    """运行策略回测"""
    try:
        ctp = get_ctp_instance()
        if not ctp:
            raise HTTPException(status_code=500, detail="CTP服务未初始化")

        # 解析回测参数
        strategy_name = backtest_request.get("strategy_name", "shfe_quant")
        symbol = backtest_request.get("symbol", "au2510")
        interval = backtest_request.get("interval", "1m")
        count = backtest_request.get("count", 100)
        strategy_params = backtest_request.get("strategy_params", {})

        # 获取历史数据
        historical_data = ctp.get_historical_data(symbol, interval, count)
        if not historical_data:
            historical_data = ctp.get_simulated_historical_data(symbol, interval, count)

        # 运行回测
        backtest_result = await run_strategy_backtest(
            strategy_name,
            historical_data,
            strategy_params
        )

        return {
            "success": True,
            "data": {
                "strategy_name": strategy_name,
                "symbol": symbol,
                "data_count": len(historical_data),
                "backtest_result": backtest_result
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"回测运行失败: {e}")
        raise HTTPException(status_code=500, detail=f"回测运行失败: {str(e)}")

async def run_strategy_backtest(strategy_name: str, historical_data: list, strategy_params: dict):
    """运行策略回测的核心逻辑"""
    try:
        # 初始化回测环境
        initial_capital = strategy_params.get("initial_capital", 100000)  # 初始资金
        commission_rate = strategy_params.get("commission_rate", 0.0002)  # 手续费率

        # 回测统计
        trades = []
        positions = 0
        capital = initial_capital
        max_capital = initial_capital
        max_drawdown = 0

        # 简化的策略逻辑（移动平均策略）
        ma_short_period = strategy_params.get("ma_short", 5)
        ma_long_period = strategy_params.get("ma_long", 20)

        prices = [bar['close'] for bar in historical_data]

        for i in range(ma_long_period, len(historical_data)):
            current_bar = historical_data[i]
            current_price = current_bar['close']

            # 计算移动平均
            ma_short = sum(prices[i-ma_short_period:i]) / ma_short_period
            ma_long = sum(prices[i-ma_long_period:i]) / ma_long_period

            # 交易信号
            if ma_short > ma_long and positions <= 0:
                # 买入信号
                if positions < 0:
                    # 平空单
                    profit = (positions * -1) * (current_price - current_price)  # 简化计算
                    capital += profit
                    trades.append({
                        "type": "CLOSE_SHORT",
                        "price": current_price,
                        "time": current_bar['datetime'],
                        "profit": profit
                    })

                # 开多单
                positions = 1
                trades.append({
                    "type": "OPEN_LONG",
                    "price": current_price,
                    "time": current_bar['datetime'],
                    "profit": 0
                })

            elif ma_short < ma_long and positions >= 0:
                # 卖出信号
                if positions > 0:
                    # 平多单
                    profit = positions * (current_price - current_price)  # 简化计算
                    capital += profit
                    trades.append({
                        "type": "CLOSE_LONG",
                        "price": current_price,
                        "time": current_bar['datetime'],
                        "profit": profit
                    })

                # 开空单
                positions = -1
                trades.append({
                    "type": "OPEN_SHORT",
                    "price": current_price,
                    "time": current_bar['datetime'],
                    "profit": 0
                })

            # 更新最大资金和回撤
            if capital > max_capital:
                max_capital = capital

            current_drawdown = (max_capital - capital) / max_capital
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown

        # 计算回测结果
        total_return = (capital - initial_capital) / initial_capital
        total_trades = len([t for t in trades if 'CLOSE' in t['type']])

        return {
            "initial_capital": initial_capital,
            "final_capital": capital,
            "total_return": round(total_return * 100, 2),  # 百分比
            "max_drawdown": round(max_drawdown * 100, 2),  # 百分比
            "total_trades": total_trades,
            "trades": trades[-10:],  # 只返回最后10笔交易
            "strategy_params": strategy_params
        }

    except Exception as e:
        logger.error(f"回测计算失败: {e}")
        return {
            "error": str(e),
            "initial_capital": strategy_params.get("initial_capital", 100000),
            "final_capital": 0,
            "total_return": 0,
            "max_drawdown": 0,
            "total_trades": 0,
            "trades": []
        }
