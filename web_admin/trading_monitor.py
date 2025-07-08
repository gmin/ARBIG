"""
交易情况监控模块
监控实时持仓、订单状态、行情数据、风险指标等
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal

from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PositionInfo:
    """持仓信息"""
    symbol: str
    exchange: str
    direction: str  # "long", "short"
    volume: int
    frozen: int
    price: float
    pnl: float
    pnl_percent: float
    market_value: float
    last_update: datetime

@dataclass
class TradingSignal:
    """交易信号"""
    signal_id: str
    signal_type: str  # "technical", "fundamental", "arbitrage", "risk_control"
    strategy_name: str
    symbol: str
    direction: str  # "buy", "sell"
    strength: float  # 信号强度 0-1
    trigger_reason: str  # 触发原因详细描述
    trigger_conditions: Dict[str, Any]  # 触发条件数据
    market_context: Dict[str, Any]  # 市场环境数据
    signal_time: datetime
    executed: bool = False
    execution_time: Optional[datetime] = None
    execution_price: Optional[float] = None

@dataclass
class OrderInfo:
    """订单信息"""
    order_id: str
    symbol: str
    exchange: str
    direction: str
    offset: str  # "open", "close"
    order_type: str  # "limit", "market", "stop"
    volume: int
    traded: int
    price: float
    status: str
    create_time: datetime
    update_time: datetime
    # 新增：关联的交易信号
    signal_id: Optional[str] = None
    strategy_name: Optional[str] = None
    trigger_reason: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class TradeInfo:
    """成交信息"""
    trade_id: str
    order_id: str
    symbol: str
    exchange: str
    direction: str
    offset: str
    volume: int
    price: float
    trade_time: datetime
    commission: float = 0.0

@dataclass
class MarketData:
    """行情数据"""
    symbol: str
    exchange: str
    last_price: float
    bid_price: float
    ask_price: float
    bid_volume: int
    ask_volume: int
    volume: int
    turnover: float
    open_price: float
    high_price: float
    low_price: float
    pre_close: float
    change: float
    change_percent: float
    timestamp: datetime

@dataclass
class RiskMetrics:
    """风险指标"""
    total_balance: float  # 总资金
    available: float  # 可用资金
    margin: float  # 占用保证金
    pnl: float  # 浮动盈亏
    risk_ratio: float  # 风险度
    max_drawdown: float  # 最大回撤
    position_ratio: float  # 持仓比例
    leverage: float  # 杠杆倍数
    var_1day: float  # 1日VaR
    last_update: datetime

class TradingMonitor:
    """交易监控器"""
    
    def __init__(self):
        # 交易数据
        self.positions: Dict[str, PositionInfo] = {}
        self.active_orders: Dict[str, OrderInfo] = {}
        self.recent_trades: List[TradeInfo] = []
        self.market_data: Dict[str, MarketData] = {}

        # 交易信号数据
        self.trading_signals: List[TradingSignal] = []
        self.signal_performance: Dict[str, Dict[str, Any]] = {}  # 按策略统计信号表现
        
        # 风险指标
        self.risk_metrics = RiskMetrics(
            total_balance=0.0,
            available=0.0,
            margin=0.0,
            pnl=0.0,
            risk_ratio=0.0,
            max_drawdown=0.0,
            position_ratio=0.0,
            leverage=1.0,
            var_1day=0.0,
            last_update=datetime.now()
        )
        
        # 统计数据
        self.daily_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "total_commission": 0.0,
            "max_single_profit": 0.0,
            "max_single_loss": 0.0,
            "win_rate": 0.0
        }
        
        # 配置
        self.max_trade_history = 1000
        
    async def start_monitoring(self):
        """启动交易监控"""
        logger.info("启动交易监控...")
        
        # 启动监控任务
        asyncio.create_task(self._monitor_loop())
        
    async def _monitor_loop(self):
        """监控主循环"""
        while True:
            try:
                # 更新风险指标
                await self._update_risk_metrics()
                
                # 更新统计数据
                await self._update_statistics()
                
                # 清理历史数据
                self._cleanup_history()
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"交易监控循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _update_risk_metrics(self):
        """更新风险指标"""
        try:
            # 计算总持仓市值
            total_position_value = sum(pos.market_value for pos in self.positions.values())
            
            # 计算总浮动盈亏
            total_pnl = sum(pos.pnl for pos in self.positions.values())
            
            # 更新风险指标（这里使用模拟数据，实际应该从账户服务获取）
            self.risk_metrics.total_balance = 20500000.0  # 从账户查询获取
            self.risk_metrics.available = self.risk_metrics.total_balance - self.risk_metrics.margin
            self.risk_metrics.pnl = total_pnl
            self.risk_metrics.position_ratio = total_position_value / self.risk_metrics.total_balance if self.risk_metrics.total_balance > 0 else 0
            self.risk_metrics.risk_ratio = self.risk_metrics.margin / self.risk_metrics.total_balance if self.risk_metrics.total_balance > 0 else 0
            self.risk_metrics.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"更新风险指标失败: {e}")
    
    async def _update_statistics(self):
        """更新统计数据"""
        try:
            # 计算今日统计
            today = datetime.now().date()
            today_trades = [t for t in self.recent_trades if t.trade_time.date() == today]
            
            self.daily_stats["total_trades"] = len(today_trades)
            
            if today_trades:
                # 计算盈亏统计（简化版本）
                profits = []
                commissions = []
                
                for trade in today_trades:
                    commissions.append(trade.commission)
                    # 这里需要更复杂的盈亏计算逻辑
                
                self.daily_stats["total_commission"] = sum(commissions)
            
        except Exception as e:
            logger.error(f"更新统计数据失败: {e}")
    
    def _cleanup_history(self):
        """清理历史数据"""
        if len(self.recent_trades) > self.max_trade_history:
            self.recent_trades = self.recent_trades[-self.max_trade_history:]
    
    # ========== 交易信号接口 ==========

    def record_trading_signal(self, signal_data: Dict[str, Any]):
        """记录交易信号"""
        try:
            signal = TradingSignal(
                signal_id=signal_data['signal_id'],
                signal_type=signal_data['signal_type'],
                strategy_name=signal_data['strategy_name'],
                symbol=signal_data['symbol'],
                direction=signal_data['direction'],
                strength=signal_data.get('strength', 0.5),
                trigger_reason=signal_data['trigger_reason'],
                trigger_conditions=signal_data.get('trigger_conditions', {}),
                market_context=signal_data.get('market_context', {}),
                signal_time=signal_data.get('signal_time', datetime.now())
            )

            self.trading_signals.append(signal)

            # 更新信号统计
            self._update_signal_stats(signal)

            logger.info(f"记录交易信号: {signal.strategy_name} - {signal.trigger_reason}")

        except Exception as e:
            logger.error(f"记录交易信号失败: {e}")

    def link_order_to_signal(self, order_id: str, signal_id: str):
        """关联订单到信号"""
        try:
            if order_id in self.active_orders:
                # 找到对应的信号
                signal = next((s for s in self.trading_signals if s.signal_id == signal_id), None)
                if signal:
                    self.active_orders[order_id].signal_id = signal_id
                    self.active_orders[order_id].strategy_name = signal.strategy_name
                    self.active_orders[order_id].trigger_reason = signal.trigger_reason

                    # 标记信号已执行
                    signal.executed = True
                    signal.execution_time = datetime.now()

        except Exception as e:
            logger.error(f"关联订单到信号失败: {e}")

    def _update_signal_stats(self, signal: TradingSignal):
        """更新信号统计"""
        strategy_name = signal.strategy_name

        if strategy_name not in self.signal_performance:
            self.signal_performance[strategy_name] = {
                "total_signals": 0,
                "executed_signals": 0,
                "successful_signals": 0,
                "failed_signals": 0,
                "avg_strength": 0.0,
                "signal_types": {},
                "execution_rate": 0.0,
                "success_rate": 0.0
            }

        stats = self.signal_performance[strategy_name]
        stats["total_signals"] += 1

        # 更新信号类型统计
        if signal.signal_type not in stats["signal_types"]:
            stats["signal_types"][signal.signal_type] = 0
        stats["signal_types"][signal.signal_type] += 1

        # 重新计算平均强度
        total_signals = stats["total_signals"]
        stats["avg_strength"] = (stats["avg_strength"] * (total_signals - 1) + signal.strength) / total_signals

    def get_signal_analysis(self, strategy_name: str = None, hours: int = 24) -> Dict[str, Any]:
        """获取信号分析"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 筛选信号
        if strategy_name:
            signals = [s for s in self.trading_signals
                      if s.strategy_name == strategy_name and s.signal_time >= cutoff_time]
        else:
            signals = [s for s in self.trading_signals if s.signal_time >= cutoff_time]

        if not signals:
            return {"message": "没有找到符合条件的信号"}

        # 分析信号
        total_signals = len(signals)
        executed_signals = len([s for s in signals if s.executed])

        # 按类型分组
        signal_by_type = {}
        for signal in signals:
            if signal.signal_type not in signal_by_type:
                signal_by_type[signal.signal_type] = []
            signal_by_type[signal.signal_type].append(signal)

        # 按策略分组
        signal_by_strategy = {}
        for signal in signals:
            if signal.strategy_name not in signal_by_strategy:
                signal_by_strategy[signal.strategy_name] = []
            signal_by_strategy[signal.strategy_name].append(signal)

        return {
            "total_signals": total_signals,
            "executed_signals": executed_signals,
            "execution_rate": executed_signals / total_signals if total_signals > 0 else 0,
            "avg_strength": sum(s.strength for s in signals) / total_signals,
            "signal_by_type": {k: len(v) for k, v in signal_by_type.items()},
            "signal_by_strategy": {k: len(v) for k, v in signal_by_strategy.items()},
            "recent_signals": [
                {
                    "signal_id": s.signal_id,
                    "strategy_name": s.strategy_name,
                    "signal_type": s.signal_type,
                    "symbol": s.symbol,
                    "direction": s.direction,
                    "strength": s.strength,
                    "trigger_reason": s.trigger_reason,
                    "signal_time": s.signal_time.isoformat(),
                    "executed": s.executed,
                    "execution_time": s.execution_time.isoformat() if s.execution_time else None
                }
                for s in sorted(signals, key=lambda x: x.signal_time, reverse=True)[:20]
            ]
        }

    # ========== 数据更新接口 ==========
    
    def update_position(self, position_data: Dict[str, Any]):
        """更新持仓数据"""
        try:
            key = f"{position_data['symbol']}.{position_data['exchange']}"
            
            self.positions[key] = PositionInfo(
                symbol=position_data['symbol'],
                exchange=position_data['exchange'],
                direction=position_data['direction'],
                volume=position_data['volume'],
                frozen=position_data.get('frozen', 0),
                price=position_data['price'],
                pnl=position_data.get('pnl', 0.0),
                pnl_percent=position_data.get('pnl_percent', 0.0),
                market_value=position_data.get('market_value', 0.0),
                last_update=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"更新持仓数据失败: {e}")
    
    def update_order(self, order_data: Dict[str, Any]):
        """更新订单数据"""
        try:
            order_info = OrderInfo(
                order_id=order_data['order_id'],
                symbol=order_data['symbol'],
                exchange=order_data['exchange'],
                direction=order_data['direction'],
                offset=order_data['offset'],
                order_type=order_data['order_type'],
                volume=order_data['volume'],
                traded=order_data.get('traded', 0),
                price=order_data['price'],
                status=order_data['status'],
                create_time=order_data.get('create_time', datetime.now()),
                update_time=datetime.now(),
                # 信号相关信息
                signal_id=order_data.get('signal_id'),
                strategy_name=order_data.get('strategy_name'),
                trigger_reason=order_data.get('trigger_reason'),
                error_message=order_data.get('error_message')
            )
            
            if order_info.status in ['submitted', 'partial_filled']:
                self.active_orders[order_info.order_id] = order_info
            else:
                # 移除非活跃订单
                self.active_orders.pop(order_info.order_id, None)
                
        except Exception as e:
            logger.error(f"更新订单数据失败: {e}")
    
    def update_trade(self, trade_data: Dict[str, Any]):
        """更新成交数据"""
        try:
            trade_info = TradeInfo(
                trade_id=trade_data['trade_id'],
                order_id=trade_data['order_id'],
                symbol=trade_data['symbol'],
                exchange=trade_data['exchange'],
                direction=trade_data['direction'],
                offset=trade_data['offset'],
                volume=trade_data['volume'],
                price=trade_data['price'],
                trade_time=trade_data.get('trade_time', datetime.now()),
                commission=trade_data.get('commission', 0.0)
            )
            
            self.recent_trades.append(trade_info)
            
        except Exception as e:
            logger.error(f"更新成交数据失败: {e}")
    
    def update_market_data(self, market_data: Dict[str, Any]):
        """更新行情数据"""
        try:
            key = f"{market_data['symbol']}.{market_data['exchange']}"
            
            # 计算涨跌幅
            change = market_data['last_price'] - market_data['pre_close']
            change_percent = (change / market_data['pre_close'] * 100) if market_data['pre_close'] > 0 else 0
            
            self.market_data[key] = MarketData(
                symbol=market_data['symbol'],
                exchange=market_data['exchange'],
                last_price=market_data['last_price'],
                bid_price=market_data.get('bid_price', 0.0),
                ask_price=market_data.get('ask_price', 0.0),
                bid_volume=market_data.get('bid_volume', 0),
                ask_volume=market_data.get('ask_volume', 0),
                volume=market_data.get('volume', 0),
                turnover=market_data.get('turnover', 0.0),
                open_price=market_data.get('open_price', 0.0),
                high_price=market_data.get('high_price', 0.0),
                low_price=market_data.get('low_price', 0.0),
                pre_close=market_data['pre_close'],
                change=change,
                change_percent=change_percent,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"更新行情数据失败: {e}")
    
    # ========== 对外接口 ==========
    
    def get_trading_overview(self) -> Dict[str, Any]:
        """获取交易概览"""
        return {
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "active_orders": {k: asdict(v) for k, v in self.active_orders.items()},
            "risk_metrics": asdict(self.risk_metrics),
            "daily_stats": self.daily_stats,
            "market_data": {k: asdict(v) for k, v in self.market_data.items()},
            "last_update": datetime.now().isoformat()
        }
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近成交"""
        recent = sorted(self.recent_trades, key=lambda x: x.trade_time, reverse=True)[:limit]
        return [asdict(trade) for trade in recent]
    
    def get_position_summary(self) -> Dict[str, Any]:
        """获取持仓汇总"""
        total_positions = len(self.positions)
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        
        return {
            "total_positions": total_positions,
            "total_pnl": total_pnl,
            "total_market_value": total_market_value,
            "positions": [asdict(pos) for pos in self.positions.values()]
        }

# 全局交易监控实例
trading_monitor = TradingMonitor()
