"""
策略性能统计模块
负责策略的性能指标计算和统计
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import numpy as np
from collections import defaultdict
import json

@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: datetime
    symbol: str
    direction: str  # 'buy', 'sell', 'short', 'cover'
    volume: int
    price: float
    pnl: float = 0.0
    commission: float = 0.0
    order_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "direction": self.direction,
            "volume": self.volume,
            "price": self.price,
            "pnl": self.pnl,
            "commission": self.commission,
            "order_id": self.order_id
        }

@dataclass
class DailyPerformance:
    """日度性能统计"""
    date: date
    pnl: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    commission: float = 0.0
    max_position: int = 0
    trades: List[TradeRecord] = field(default_factory=list)
    
    @property
    def win_rate(self) -> float:
        """胜率"""
        return self.win_count / self.trade_count if self.trade_count > 0 else 0.0
    
    @property
    def net_pnl(self) -> float:
        """净盈亏"""
        return self.pnl - self.commission
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "pnl": self.pnl,
            "net_pnl": self.net_pnl,
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "win_rate": self.win_rate,
            "commission": self.commission,
            "max_position": self.max_position
        }

class StrategyPerformance:
    """
    策略性能统计器
    
    负责：
    1. 交易记录管理
    2. 性能指标计算
    3. 风险指标统计
    4. 历史数据维护
    """
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.start_time = datetime.now()
        
        # 基础统计
        self.total_pnl = 0.0
        self.total_commission = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        # 交易记录
        self.trades: List[TradeRecord] = []
        self.daily_performance: Dict[date, DailyPerformance] = defaultdict(
            lambda: DailyPerformance(date=date.today())
        )
        
        # 净值曲线
        self.equity_curve: List[float] = [0.0]
        self.equity_timestamps: List[datetime] = [self.start_time]
        
        # 风险统计
        self.max_drawdown = 0.0
        self.max_equity = 0.0
        self.current_drawdown = 0.0
        
        # 持仓统计
        self.current_position = 0
        self.max_position = 0
        self.position_history: List[tuple] = []  # (timestamp, position)
    
    def add_trade(self, trade: TradeRecord):
        """添加交易记录"""
        self.trades.append(trade)
        self.total_trades += 1
        self.total_pnl += trade.pnl
        self.total_commission += trade.commission
        
        if trade.pnl > 0:
            self.winning_trades += 1
        
        # 更新日度统计
        today = trade.timestamp.date()
        daily = self.daily_performance[today]
        daily.date = today
        daily.pnl += trade.pnl
        daily.commission += trade.commission
        daily.trade_count += 1
        if trade.pnl > 0:
            daily.win_count += 1
        daily.trades.append(trade)
        
        # 更新净值曲线
        current_equity = self.net_pnl
        self.equity_curve.append(current_equity)
        self.equity_timestamps.append(trade.timestamp)
        
        # 更新风险统计
        self._update_drawdown(current_equity)
    
    def update_position(self, position: int, timestamp: Optional[datetime] = None):
        """更新持仓"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.current_position = position
        self.max_position = max(self.max_position, abs(position))
        self.position_history.append((timestamp, position))
        
        # 更新日度最大持仓
        today = timestamp.date()
        daily = self.daily_performance[today]
        daily.max_position = max(daily.max_position, abs(position))
    
    def _update_drawdown(self, current_equity: float):
        """更新回撤统计"""
        if current_equity > self.max_equity:
            self.max_equity = current_equity
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.max_equity - current_equity) / self.max_equity if self.max_equity > 0 else 0.0
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    @property
    def net_pnl(self) -> float:
        """净盈亏"""
        return self.total_pnl - self.total_commission
    
    @property
    def win_rate(self) -> float:
        """总胜率"""
        return self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
    
    @property
    def avg_win(self) -> float:
        """平均盈利"""
        winning_pnl = sum(trade.pnl for trade in self.trades if trade.pnl > 0)
        return winning_pnl / self.winning_trades if self.winning_trades > 0 else 0.0
    
    @property
    def avg_loss(self) -> float:
        """平均亏损"""
        losing_trades = self.total_trades - self.winning_trades
        losing_pnl = sum(trade.pnl for trade in self.trades if trade.pnl <= 0)
        return losing_pnl / losing_trades if losing_trades > 0 else 0.0
    
    @property
    def profit_factor(self) -> float:
        """盈亏比"""
        total_profit = sum(trade.pnl for trade in self.trades if trade.pnl > 0)
        total_loss = abs(sum(trade.pnl for trade in self.trades if trade.pnl <= 0))
        return total_profit / total_loss if total_loss > 0 else float('inf')
    
    @property
    def sharpe_ratio(self) -> float:
        """夏普比率 (简化计算)"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        returns = np.diff(self.equity_curve)
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        
        return np.mean(returns) / np.std(returns) * np.sqrt(252)  # 年化
    
    @property
    def calmar_ratio(self) -> float:
        """卡尔玛比率"""
        if self.max_drawdown == 0:
            return float('inf')
        
        annual_return = self.net_pnl  # 简化：假设为年化收益
        return annual_return / self.max_drawdown
    
    def get_today_performance(self) -> DailyPerformance:
        """获取今日表现"""
        today = date.today()
        return self.daily_performance[today]
    
    def get_recent_performance(self, days: int = 7) -> List[DailyPerformance]:
        """获取最近N天表现"""
        from datetime import timedelta
        
        recent_dates = []
        current_date = date.today()
        for i in range(days):
            recent_dates.append(current_date - timedelta(days=i))
        
        return [self.daily_performance[d] for d in reversed(recent_dates)]
    
    def get_equity_curve_data(self, limit: int = 100) -> Dict[str, List]:
        """获取净值曲线数据"""
        if limit and len(self.equity_curve) > limit:
            step = len(self.equity_curve) // limit
            timestamps = self.equity_timestamps[::step]
            equity = self.equity_curve[::step]
        else:
            timestamps = self.equity_timestamps
            equity = self.equity_curve
        
        return {
            "timestamps": [ts.isoformat() for ts in timestamps],
            "equity": equity
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        return {
            "strategy_name": self.strategy_name,
            "start_time": self.start_time.isoformat(),
            "runtime_hours": runtime_hours,
            
            # 基础统计
            "total_pnl": self.total_pnl,
            "net_pnl": self.net_pnl,
            "total_commission": self.total_commission,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": self.win_rate,
            
            # 风险指标
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "profit_factor": self.profit_factor,
            
            # 交易统计
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "current_position": self.current_position,
            "max_position": self.max_position,
            
            # 今日表现
            "today": self.get_today_performance().to_dict()
        }
    
    def reset(self):
        """重置统计数据"""
        self.__init__(self.strategy_name)
    
    def save_to_dict(self) -> Dict[str, Any]:
        """保存为字典格式"""
        return {
            "strategy_name": self.strategy_name,
            "start_time": self.start_time.isoformat(),
            "trades": [trade.to_dict() for trade in self.trades],
            "daily_performance": {
                d.isoformat(): perf.to_dict() 
                for d, perf in self.daily_performance.items()
            },
            "equity_curve": self.equity_curve,
            "equity_timestamps": [ts.isoformat() for ts in self.equity_timestamps],
            "position_history": [
                (ts.isoformat(), pos) for ts, pos in self.position_history
            ]
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """从字典格式加载"""
        self.strategy_name = data["strategy_name"]
        self.start_time = datetime.fromisoformat(data["start_time"])
        
        # 重建交易记录
        self.trades = []
        for trade_data in data.get("trades", []):
            trade = TradeRecord(
                timestamp=datetime.fromisoformat(trade_data["timestamp"]),
                symbol=trade_data["symbol"],
                direction=trade_data["direction"],
                volume=trade_data["volume"],
                price=trade_data["price"],
                pnl=trade_data["pnl"],
                commission=trade_data["commission"],
                order_id=trade_data["order_id"]
            )
            self.add_trade(trade)
        
        # 重建净值曲线
        self.equity_curve = data.get("equity_curve", [0.0])
        self.equity_timestamps = [
            datetime.fromisoformat(ts) 
            for ts in data.get("equity_timestamps", [self.start_time.isoformat()])
        ]
        
        # 重建持仓历史
        self.position_history = [
            (datetime.fromisoformat(ts), pos)
            for ts, pos in data.get("position_history", [])
        ]
