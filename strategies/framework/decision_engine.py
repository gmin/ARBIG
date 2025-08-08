"""
决策引擎 - 基于信号做出交易决策
职责：信号过滤、时机选择、仓位计算
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, time as dt_time

from .signal_generator import Signal

@dataclass
class Decision:
    """交易决策数据类"""
    action: str  # BUY, SELL, CLOSE_LONG, CLOSE_SHORT, HOLD
    quantity: int  # 交易数量
    price: float  # 期望价格
    reason: str  # 决策原因
    confidence: float  # 决策置信度 0-1
    timestamp: float  # 决策时间

@dataclass
class MarketContext:
    """市场上下文"""
    current_price: float
    volatility: float
    volume: int
    timestamp: float
    trading_session: str  # 'morning', 'afternoon', 'night', 'closed'

@dataclass
class PortfolioContext:
    """组合上下文"""
    current_position: int  # 当前持仓
    available_margin: float  # 可用保证金
    unrealized_pnl: float  # 未实现盈亏
    daily_pnl: float  # 当日盈亏
    max_position: int  # 最大持仓限制

class SignalFilter:
    """信号过滤器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def should_filter(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> bool:
        """判断是否应该过滤掉这个信号"""
        return False

class TimeFilter(SignalFilter):
    """时间过滤器 - 只在指定时间段内交易"""
    
    def should_filter(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> bool:
        start_time = self.config.get('start_time', '09:00')
        end_time = self.config.get('end_time', '15:00')
        
        current_time = datetime.fromtimestamp(signal.timestamp).time()
        start = dt_time.fromisoformat(start_time)
        end = dt_time.fromisoformat(end_time)
        
        return not (start <= current_time <= end)

class VolatilityFilter(SignalFilter):
    """波动率过滤器 - 过滤极端波动情况"""
    
    def should_filter(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> bool:
        min_vol = self.config.get('min_volatility', 0.001)
        max_vol = self.config.get('max_volatility', 0.1)
        
        return not (min_vol <= market_ctx.volatility <= max_vol)

class PositionFilter(SignalFilter):
    """持仓过滤器 - 避免过度交易"""
    
    def should_filter(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> bool:
        # 如果已经满仓，过滤同方向信号
        if signal.action == 'BUY' and portfolio_ctx.current_position >= portfolio_ctx.max_position:
            return True
        if signal.action == 'SELL' and portfolio_ctx.current_position <= -portfolio_ctx.max_position:
            return True
        
        return False

class PnLFilter(SignalFilter):
    """盈亏过滤器 - 当日亏损过多时停止交易"""
    
    def should_filter(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> bool:
        max_daily_loss = self.config.get('max_daily_loss', 0.05)  # 5%
        
        # 如果当日亏损超过限制，停止交易
        if portfolio_ctx.daily_pnl < -max_daily_loss * portfolio_ctx.available_margin:
            return True
        
        return False

class PositionSizer:
    """仓位计算器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.method = config.get('method', 'fixed')
    
    def calculate_position(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> int:
        """计算交易仓位"""
        if self.method == 'fixed':
            return self._fixed_position(signal, portfolio_ctx)
        elif self.method == 'fixed_fraction':
            return self._fixed_fraction_position(signal, market_ctx, portfolio_ctx)
        elif self.method == 'volatility_adjusted':
            return self._volatility_adjusted_position(signal, market_ctx, portfolio_ctx)
        elif self.method == 'kelly':
            return self._kelly_position(signal, market_ctx, portfolio_ctx)
        
        return 0
    
    def _fixed_position(self, signal: Signal, portfolio_ctx: PortfolioContext) -> int:
        """固定仓位"""
        base_size = self.config.get('base_size', 1)
        
        # 根据信号强度调整
        adjusted_size = int(base_size * signal.strength)
        
        # 检查可用仓位
        if signal.action == 'BUY':
            available = portfolio_ctx.max_position - portfolio_ctx.current_position
            return min(adjusted_size, available)
        elif signal.action == 'SELL':
            available = portfolio_ctx.max_position + portfolio_ctx.current_position
            return min(adjusted_size, available)
        
        return 0
    
    def _fixed_fraction_position(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> int:
        """固定比例仓位"""
        fraction = self.config.get('fraction', 0.02)  # 2%
        
        # 基于可用资金计算仓位
        position_value = portfolio_ctx.available_margin * fraction
        position_size = int(position_value / market_ctx.current_price)
        
        # 根据信号强度调整
        adjusted_size = int(position_size * signal.strength)
        
        # 检查限制
        max_size = self.config.get('max_size', 100)
        return min(adjusted_size, max_size)
    
    def _volatility_adjusted_position(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> int:
        """波动率调整仓位"""
        base_fraction = self.config.get('base_fraction', 0.02)
        target_volatility = self.config.get('target_volatility', 0.02)
        
        # 根据波动率调整仓位
        vol_adjustment = target_volatility / max(market_ctx.volatility, 0.001)
        adjusted_fraction = base_fraction * vol_adjustment
        
        position_value = portfolio_ctx.available_margin * adjusted_fraction
        position_size = int(position_value / market_ctx.current_price)
        
        return int(position_size * signal.strength)
    
    def _kelly_position(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> int:
        """凯利公式仓位"""
        # 简化的凯利公式实现
        win_rate = self.config.get('win_rate', 0.55)
        avg_win = self.config.get('avg_win', 0.02)
        avg_loss = self.config.get('avg_loss', 0.01)
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制在0-25%
        
        position_value = portfolio_ctx.available_margin * kelly_fraction
        position_size = int(position_value / market_ctx.current_price)
        
        return int(position_size * signal.strength)

class DecisionEngine:
    """决策引擎 - 组合信号过滤和仓位计算"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.filters = self._init_filters()
        self.position_sizer = PositionSizer(config.get('position_sizing', {}))
        
        # 决策历史
        self.decision_history: List[Decision] = []
        self.last_decision_time = 0
        
    def _init_filters(self) -> List[SignalFilter]:
        """初始化信号过滤器"""
        filters = []
        
        filter_configs = self.config.get('filters', [])
        for filter_config in filter_configs:
            filter_type = filter_config.get('type')
            
            if filter_type == 'time':
                filters.append(TimeFilter(filter_config))
            elif filter_type == 'volatility':
                filters.append(VolatilityFilter(filter_config))
            elif filter_type == 'position':
                filters.append(PositionFilter(filter_config))
            elif filter_type == 'pnl':
                filters.append(PnLFilter(filter_config))
        
        return filters
    
    def make_decision(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> Optional[Decision]:
        """基于信号和上下文做出交易决策"""
        if not signal:
            return None
        
        # 检查决策频率限制
        min_interval = self.config.get('min_decision_interval', 1)  # 最小决策间隔（秒）
        if signal.timestamp - self.last_decision_time < min_interval:
            return None
        
        # 应用所有过滤器
        for filter_obj in self.filters:
            if filter_obj.should_filter(signal, market_ctx, portfolio_ctx):
                return None
        
        # 计算仓位
        quantity = self.position_sizer.calculate_position(signal, market_ctx, portfolio_ctx)
        
        if quantity == 0:
            return None
        
        # 调整交易动作
        action = self._adjust_action(signal.action, portfolio_ctx.current_position)
        
        # 计算决策置信度
        confidence = self._calculate_confidence(signal, market_ctx, portfolio_ctx)
        
        # 生成决策
        decision = Decision(
            action=action,
            quantity=quantity,
            price=signal.price,
            reason=f"信号: {signal.reason}, 仓位: {quantity}",
            confidence=confidence,
            timestamp=signal.timestamp
        )
        
        # 记录决策
        self.decision_history.append(decision)
        self.last_decision_time = signal.timestamp
        
        # 保持历史记录长度
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
        
        return decision
    
    def _adjust_action(self, signal_action: str, current_position: int) -> str:
        """根据当前持仓调整交易动作"""
        if signal_action == 'BUY':
            if current_position < 0:
                return 'CLOSE_SHORT'  # 先平空
            else:
                return 'BUY'  # 开多
        elif signal_action == 'SELL':
            if current_position > 0:
                return 'CLOSE_LONG'  # 先平多
            else:
                return 'SELL'  # 开空
        
        return signal_action
    
    def _calculate_confidence(self, signal: Signal, market_ctx: MarketContext, portfolio_ctx: PortfolioContext) -> float:
        """计算决策置信度"""
        confidence = signal.strength
        
        # 根据市场条件调整置信度
        if market_ctx.volatility > 0.05:  # 高波动
            confidence *= 0.8
        elif market_ctx.volatility < 0.01:  # 低波动
            confidence *= 0.9
        
        # 根据持仓情况调整置信度
        position_ratio = abs(portfolio_ctx.current_position) / portfolio_ctx.max_position
        if position_ratio > 0.8:  # 接近满仓
            confidence *= 0.7
        
        # 根据当日盈亏调整置信度
        if portfolio_ctx.daily_pnl < 0:  # 当日亏损
            confidence *= 0.9
        
        return min(confidence, 1.0)
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        if not self.decision_history:
            return {}
        
        recent_decisions = self.decision_history[-100:]  # 最近100个决策
        
        return {
            'total_decisions': len(self.decision_history),
            'recent_decisions': len(recent_decisions),
            'avg_confidence': sum(d.confidence for d in recent_decisions) / len(recent_decisions),
            'action_distribution': self._get_action_distribution(recent_decisions),
            'last_decision_time': self.last_decision_time
        }
    
    def _get_action_distribution(self, decisions: List[Decision]) -> Dict[str, int]:
        """获取动作分布统计"""
        distribution = {}
        for decision in decisions:
            distribution[decision.action] = distribution.get(decision.action, 0) + 1
        return distribution
