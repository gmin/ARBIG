"""
数据提供器
负责从核心交易系统获取数据并转换为Web API格式
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import (
    SystemStatus, PositionInfo, OrderInfo, TradeInfo, 
    MarketDataInfo, RiskMetrics, TradingStatistics
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
