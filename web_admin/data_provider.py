"""
数据提供器
负责从核心交易系统获取数据并转换为Web API格式
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import json

from .models import (
    SystemStatus, PositionInfo, OrderInfo, TradeInfo,
    MarketDataInfo, RiskMetrics, TradingStatistics,
    OrderRequest, OrderModification
)
from utils.logger import get_logger

logger = get_logger(__name__)

class DataProvider:
    """数据提供器"""
    
    def __init__(self, trading_system):
        """
        初始化数据提供器
        
        Args:
            trading_system: 核心交易系统实例
        """
        self.trading_system = trading_system
        logger.info("数据提供器初始化完成")
    
    async def get_system_status(self) -> SystemStatus:
        """获取系统状态"""
        try:
            return SystemStatus(
                timestamp=datetime.now(),
                services={
                    "market_data": self.trading_system.market_data_service.get_status().value,
                    "account": self.trading_system.account_service.get_status().value,
                    "trading": self.trading_system.trading_service.get_status().value,
                    "risk": self.trading_system.risk_service.get_status().value
                },
                risk_level=self.trading_system.risk_service.risk_level,
                trading_halted=self.trading_system.risk_service.is_trading_halted,
                connections={
                    "ctp_md": self.trading_system.ctp_gateway.is_md_connected(),
                    "ctp_td": self.trading_system.ctp_gateway.is_td_connected()
                }
            )
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            raise
    
    async def get_positions(self) -> List[PositionInfo]:
        """获取持仓信息"""
        try:
            positions = self.trading_system.account_service.get_positions()
            return [
                PositionInfo(
                    symbol=pos.symbol,
                    direction=pos.direction.value,
                    volume=pos.volume,
                    price=pos.price,
                    pnl=pos.pnl,
                    frozen=pos.frozen,
                    yd_volume=getattr(pos, 'yd_volume', None)
                )
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            return []
    
    async def get_orders(self, active_only: bool = False) -> List[OrderInfo]:
        """获取订单信息"""
        try:
            if active_only:
                orders = self.trading_system.trading_service.get_active_orders()
            else:
                orders = self.trading_system.trading_service.get_orders()
            
            return [
                OrderInfo(
                    orderid=order.orderid,
                    symbol=order.symbol,
                    direction=order.direction.value,
                    volume=order.volume,
                    price=order.price,
                    status=order.status.value,
                    traded=order.traded,
                    datetime=order.datetime,
                    strategy=self._extract_strategy_from_reference(order.reference)
                )
                for order in orders
            ]
        except Exception as e:
            logger.error(f"获取订单信息失败: {e}")
            return []
    
    async def get_trades(self, limit: int = 100) -> List[TradeInfo]:
        """获取成交信息"""
        try:
            trades = self.trading_system.trading_service.get_trades()

            # 按时间倒序排列，取最近的记录
            trades.sort(key=lambda x: x.datetime, reverse=True)
            if limit > 0:
                trades = trades[:limit]

            return [
                TradeInfo(
                    tradeid=trade.tradeid,
                    orderid=trade.orderid,
                    symbol=trade.symbol,
                    direction=trade.direction.value,
                    volume=trade.volume,
                    price=trade.price,
                    datetime=trade.datetime
                )
                for trade in trades
            ]
        except Exception as e:
            logger.error(f"获取成交信息失败: {e}")
            return []

    async def get_history_orders(self) -> List[Dict[str, Any]]:
        """获取CTP历史订单"""
        try:
            if not hasattr(self.trading_system, 'ctp_gateway') or not self.trading_system.ctp_gateway:
                logger.warning("CTP网关未连接，无法查询历史订单")
                return []

            ctp_gateway = self.trading_system.ctp_gateway
            if not hasattr(ctp_gateway, 'td_api') or not ctp_gateway.td_api:
                logger.warning("CTP交易API未连接，无法查询历史订单")
                return []

            td_api = ctp_gateway.td_api
            received_orders = []

            def order_callback(data, error, reqid, last):
                if error and error.ErrorID != 0:
                    logger.error(f"历史订单查询错误: {error.ErrorID} - {error.ErrorMsg}")
                elif data:
                    received_orders.append(data)

            # 设置回调
            original_callback = getattr(td_api, 'onRspQryOrder', None)
            td_api.onRspQryOrder = order_callback

            # 发送查询请求
            result = td_api.reqQryOrder({}, int(time.time() * 1000) % 1000000)
            if result != 0:
                logger.error(f"历史订单查询请求失败: {result}")
                return []

            # 等待响应
            for i in range(10):
                time.sleep(0.5)
                if len(received_orders) > 0:
                    break

            # 恢复原始回调
            if original_callback:
                td_api.onRspQryOrder = original_callback

            logger.info(f"获取到 {len(received_orders)} 条历史订单")
            return received_orders

        except Exception as e:
            logger.error(f"获取历史订单失败: {e}")
            return []

    async def get_history_trades(self) -> List[Dict[str, Any]]:
        """获取CTP历史成交"""
        try:
            if not hasattr(self.trading_system, 'ctp_gateway') or not self.trading_system.ctp_gateway:
                logger.warning("CTP网关未连接，无法查询历史成交")
                return []

            ctp_gateway = self.trading_system.ctp_gateway
            if not hasattr(ctp_gateway, 'td_api') or not ctp_gateway.td_api:
                logger.warning("CTP交易API未连接，无法查询历史成交")
                return []

            td_api = ctp_gateway.td_api
            received_trades = []

            def trade_callback(data, error, reqid, last):
                if error and error.ErrorID != 0:
                    logger.error(f"历史成交查询错误: {error.ErrorID} - {error.ErrorMsg}")
                elif data:
                    received_trades.append(data)

            # 设置回调
            original_callback = getattr(td_api, 'onRspQryTrade', None)
            td_api.onRspQryTrade = trade_callback

            # 发送查询请求
            result = td_api.reqQryTrade({}, int(time.time() * 1000) % 1000000)
            if result != 0:
                logger.error(f"历史成交查询请求失败: {result}")
                return []

            # 等待响应
            for i in range(10):
                time.sleep(0.5)
                if len(received_trades) > 0:
                    break

            # 恢复原始回调
            if original_callback:
                td_api.onRspQryTrade = original_callback

            logger.info(f"获取到 {len(received_trades)} 条历史成交")
            return received_trades

        except Exception as e:
            logger.error(f"获取历史成交失败: {e}")
            return []

    async def get_trading_summary(self) -> Dict[str, Any]:
        """获取交易汇总统计"""
        try:
            # 获取历史数据
            history_orders = await self.get_history_orders()
            history_trades = await self.get_history_trades()

            # 统计订单状态
            total_orders = len(history_orders)
            successful_orders = len([o for o in history_orders if o.get('OrderStatus') == '0'])  # 全部成交
            rejected_orders = len([o for o in history_orders if o.get('OrderStatus') == '5'])   # 已撤单

            # 统计成交金额
            total_trade_amount = sum(
                float(t.get('Price', 0)) * int(t.get('Volume', 0)) * 1000  # 黄金每手1000克
                for t in history_trades
            )

            # 计算今日数据
            today = datetime.now().strftime('%Y%m%d')
            today_orders = [o for o in history_orders if o.get('InsertDate') == today]
            today_trades = [t for t in history_trades if t.get('TradeDate') == today]

            today_trade_amount = sum(
                float(t.get('Price', 0)) * int(t.get('Volume', 0)) * 1000
                for t in today_trades
            )

            return {
                'total_orders': total_orders,
                'successful_orders': successful_orders,
                'rejected_orders': rejected_orders,
                'success_rate': (successful_orders / total_orders * 100) if total_orders > 0 else 0,
                'total_trades': len(history_trades),
                'total_trade_amount': total_trade_amount,
                'today_orders': len(today_orders),
                'today_trades': len(today_trades),
                'today_trade_amount': today_trade_amount,
                'last_update': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取交易汇总失败: {e}")
            return {
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
    
    async def get_market_data(self) -> List[MarketDataInfo]:
        """获取行情数据"""
        try:
            ticks = self.trading_system.market_data_service.get_all_ticks()
            
            return [
                MarketDataInfo(
                    symbol=tick.symbol,
                    last_price=tick.last_price,
                    bid_price_1=tick.bid_price_1,
                    ask_price_1=tick.ask_price_1,
                    bid_volume_1=tick.bid_volume_1,
                    ask_volume_1=tick.ask_volume_1,
                    volume=tick.volume,
                    datetime=tick.datetime
                )
                for tick in ticks.values()
            ]
        except Exception as e:
            logger.error(f"获取行情数据失败: {e}")
            return []
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        try:
            metrics = self.trading_system.risk_service.get_risk_metrics()
            
            return {
                "timestamp": metrics.timestamp.isoformat(),
                "daily_pnl": metrics.daily_pnl,
                "total_pnl": metrics.total_pnl,
                "max_drawdown": metrics.max_drawdown,
                "current_drawdown": getattr(metrics, 'current_drawdown', 0.0),
                "position_ratio": metrics.position_ratio,
                "margin_ratio": metrics.margin_ratio,
                "risk_level": metrics.risk_level
            }
        except Exception as e:
            logger.error(f"获取风险指标失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "daily_pnl": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "current_drawdown": 0.0,
                "position_ratio": 0.0,
                "margin_ratio": 0.0,
                "risk_level": "UNKNOWN"
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 交易统计
            trading_stats = self.trading_system.trading_service.get_statistics()
            
            # 账户统计
            account_stats = self.trading_system.account_service.get_statistics()
            
            # 行情统计
            market_stats = self.trading_system.market_data_service.get_statistics()
            
            # 风控统计
            risk_stats = self.trading_system.risk_service.get_statistics()
            
            return {
                "trading": {
                    "total_orders": trading_stats.get('total_orders', 0),
                    "active_orders": trading_stats.get('active_orders', 0),
                    "total_trades": trading_stats.get('total_trades', 0),
                    "total_volume": trading_stats.get('total_volume', 0.0),
                    "total_turnover": trading_stats.get('total_turnover', 0.0),
                    "avg_price": trading_stats.get('avg_price', 0.0),
                    "strategies_count": trading_stats.get('strategies_count', 0),
                    "strategy_names": trading_stats.get('strategy_names', [])
                },
                "account": {
                    "available_funds": account_stats.get('account_available', 0.0),
                    "positions_count": account_stats.get('positions_count', 0),
                    "query_interval": account_stats.get('query_interval', 0)
                },
                "market_data": {
                    "subscribed_symbols": market_stats.get('subscribed_symbols', 0),
                    "cached_ticks": market_stats.get('cached_ticks', 0),
                    "tick_rate": market_stats.get('tick_rate', 0.0)
                },
                "risk": {
                    "risk_level": risk_stats.get('risk_level', 'UNKNOWN'),
                    "trading_halted": risk_stats.get('is_trading_halted', False),
                    "daily_pnl": risk_stats.get('daily_pnl', 0.0),
                    "max_drawdown": risk_stats.get('max_drawdown', 0.0)
                }
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "trading": {},
                "account": {},
                "market_data": {},
                "risk": {}
            }
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        try:
            account = self.trading_system.account_service.get_account_info()
            if account:
                return {
                    "accountid": account.accountid,
                    "balance": account.balance,
                    "available": account.available,
                    "frozen": account.frozen,
                    "datetime": account.datetime.isoformat()
                }
            return None
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return None
    
    async def get_strategy_statistics(self, strategy_name: str) -> Dict[str, Any]:
        """获取策略统计"""
        try:
            return self.trading_system.trading_service.get_strategy_statistics(strategy_name)
        except Exception as e:
            logger.error(f"获取策略统计失败: {e}")
            return {}
    
    async def get_latest_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新Tick数据"""
        try:
            tick = self.trading_system.market_data_service.get_latest_tick(symbol)
            if tick:
                return {
                    "symbol": tick.symbol,
                    "last_price": tick.last_price,
                    "bid_price_1": tick.bid_price_1,
                    "ask_price_1": tick.ask_price_1,
                    "bid_volume_1": tick.bid_volume_1,
                    "ask_volume_1": tick.ask_volume_1,
                    "volume": tick.volume,
                    "datetime": tick.datetime.isoformat()
                }
            return None
        except Exception as e:
            logger.error(f"获取最新Tick失败: {e}")
            return None
    
    def _extract_strategy_from_reference(self, reference: str) -> Optional[str]:
        """从订单引用中提取策略名称"""
        try:
            if reference and '_' in reference:
                return reference.split('_')[0]
            return reference
        except:
            return None

    # ========== 交易操作方法 ==========

    async def submit_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """提交订单"""
        try:
            # 构建订单数据
            order_data = {
                "symbol": order_request.symbol,
                "exchange": order_request.exchange,
                "direction": order_request.direction,
                "offset": order_request.offset,
                "order_type": order_request.order_type,
                "volume": order_request.volume,
                "price": order_request.price,
                "strategy_name": order_request.strategy_name,
                "signal_id": order_request.signal_id,
                "operator": order_request.operator,
                "timestamp": datetime.now()
            }

            # 调用交易服务下单
            if hasattr(self.trading_system, 'trading_service'):
                result = await self.trading_system.trading_service.submit_order(order_data)
                logger.info(f"手动下单成功: {order_request.symbol} {order_request.direction} {order_request.volume}")
                return result
            else:
                # 模拟下单结果
                order_id = f"WEB_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"模拟下单: {order_request.symbol} {order_request.direction} {order_request.volume}")
                return {
                    "order_id": order_id,
                    "status": "submitted",
                    "message": "订单已提交"
                }

        except Exception as e:
            logger.error(f"下单失败: {e}")
            raise

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """撤销订单"""
        try:
            if hasattr(self.trading_system, 'trading_service'):
                result = await self.trading_system.trading_service.cancel_order(order_id)
                logger.info(f"撤单成功: {order_id}")
                return result
            else:
                # 模拟撤单结果
                logger.info(f"模拟撤单: {order_id}")
                return {
                    "order_id": order_id,
                    "status": "cancelled",
                    "message": "订单已撤销"
                }

        except Exception as e:
            logger.error(f"撤单失败: {e}")
            raise

    async def modify_order(self, order_id: str, modification: OrderModification) -> Dict[str, Any]:
        """修改订单"""
        try:
            if hasattr(self.trading_system, 'trading_service'):
                result = await self.trading_system.trading_service.modify_order(order_id, modification.dict())
                logger.info(f"订单修改成功: {order_id}")
                return result
            else:
                # 模拟修改结果
                logger.info(f"模拟订单修改: {order_id}")
                return {
                    "order_id": order_id,
                    "status": "modified",
                    "message": "订单已修改"
                }

        except Exception as e:
            logger.error(f"订单修改失败: {e}")
            raise

    async def get_strategies(self):
        """获取策略列表"""
        try:
            strategy_service = self.trading_system.services.get('StrategyService')
            if strategy_service:
                return strategy_service.get_strategy_list()
            else:
                logger.warning("策略服务未启动")
                return []
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            return []

    async def start_strategy(self, strategy_name: str):
        """启动策略"""
        try:
            strategy_service = self.trading_system.services.get('StrategyService')
            if strategy_service:
                success = strategy_service.start_strategy(strategy_name)
                if success:
                    return {"strategy_name": strategy_name, "status": "started"}
                else:
                    raise Exception(f"策略 {strategy_name} 启动失败")
            else:
                raise Exception("策略服务未启动")
        except Exception as e:
            logger.error(f"启动策略失败: {e}")
            raise

    async def stop_strategy(self, strategy_name: str):
        """停止策略"""
        try:
            strategy_service = self.trading_system.services.get('StrategyService')
            if strategy_service:
                success = strategy_service.stop_strategy(strategy_name)
                if success:
                    return {"strategy_name": strategy_name, "status": "stopped"}
                else:
                    raise Exception(f"策略 {strategy_name} 停止失败")
            else:
                raise Exception("策略服务未启动")
        except Exception as e:
            logger.error(f"停止策略失败: {e}")
            raise

    async def halt_strategy(self, strategy_name: str, reason: str):
        """暂停策略"""
        try:
            strategy_service = self.trading_system.services.get('StrategyService')
            if strategy_service:
                success = strategy_service.stop_strategy(strategy_name)
                if success:
                    logger.info(f"策略 {strategy_name} 已暂停，原因: {reason}")
                    return {"strategy_name": strategy_name, "status": "halted", "reason": reason}
                else:
                    raise Exception(f"策略 {strategy_name} 暂停失败")
            else:
                raise Exception("策略服务未启动")
        except Exception as e:
            logger.error(f"暂停策略失败: {e}")
            raise
