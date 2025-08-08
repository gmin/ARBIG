"""
简化的SHFE策略 - 基于新架构设计
职责明确：只负责组合各个组件，实现策略逻辑
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .framework.signal_generator import SignalGenerator, Signal
from .framework.decision_engine import DecisionEngine, Decision, MarketContext, PortfolioContext

@dataclass
class Order:
    """订单数据类"""
    symbol: str
    action: str  # BUY, SELL, CLOSE_LONG, CLOSE_SHORT
    quantity: int
    price: float
    order_type: str  # MARKET, LIMIT
    strategy_name: str
    timestamp: float
    reason: str

class SimpleSHFEStrategy:
    """简化的SHFE策略 - 清晰的职责分离"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.symbol = config.get('symbol', 'au2509')
        
        # 初始化各个组件
        self.signal_generator = SignalGenerator(config.get('signals', {}))
        self.decision_engine = DecisionEngine(config.get('decisions', {}))
        
        # 策略状态
        self.current_position = 0
        self.available_margin = config.get('initial_margin', 100000.0)
        self.max_position = config.get('max_position', 10)
        self.daily_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # 性能统计
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # 运行状态
        self.is_active = False
        self.last_price = 0.0
        self.last_update_time = 0.0
        
    def start(self):
        """启动策略"""
        self.is_active = True
        print(f"[{self.name}] 简化SHFE策略启动 - 合约: {self.symbol}")
    
    def stop(self):
        """停止策略"""
        self.is_active = False
        print(f"[{self.name}] 简化SHFE策略停止")
    
    def process_market_data(self, market_data: Dict[str, Any]) -> List[Order]:
        """处理市场数据 - 策略的核心方法"""
        if not self.is_active:
            return []
        
        # 只处理指定合约
        if market_data.get('symbol') != self.symbol:
            return []
        
        current_price = market_data.get('last_price', 0)
        if current_price <= 0:
            return []
        
        self.last_price = current_price
        self.last_update_time = market_data.get('timestamp', time.time())
        
        try:
            # 1. 生成信号
            signal = self.signal_generator.generate_signal(current_price, self.last_update_time)
            if not signal:
                return []
            
            # 2. 构建上下文
            market_ctx = self._build_market_context(market_data)
            portfolio_ctx = self._build_portfolio_context()
            
            # 3. 做出决策
            decision = self.decision_engine.make_decision(signal, market_ctx, portfolio_ctx)
            if not decision:
                return []
            
            # 4. 生成订单
            orders = self._create_orders(decision)
            
            # 5. 记录决策
            self._log_decision(signal, decision)
            
            return orders
            
        except Exception as e:
            print(f"[{self.name}] 处理市场数据异常: {e}")
            return []
    
    def _build_market_context(self, market_data: Dict[str, Any]) -> MarketContext:
        """构建市场上下文"""
        return MarketContext(
            current_price=market_data.get('last_price', 0),
            volatility=self._calculate_volatility(market_data),
            volume=market_data.get('volume', 0),
            timestamp=market_data.get('timestamp', time.time()),
            trading_session=self._get_trading_session()
        )
    
    def _build_portfolio_context(self) -> PortfolioContext:
        """构建组合上下文"""
        return PortfolioContext(
            current_position=self.current_position,
            available_margin=self.available_margin,
            unrealized_pnl=self.unrealized_pnl,
            daily_pnl=self.daily_pnl,
            max_position=self.max_position
        )
    
    def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """计算简单波动率"""
        # 简化实现：基于价格变化
        if hasattr(self, '_prev_price') and self._prev_price > 0:
            price_change = abs(market_data.get('last_price', 0) - self._prev_price) / self._prev_price
            self._prev_price = market_data.get('last_price', 0)
            return price_change
        else:
            self._prev_price = market_data.get('last_price', 0)
            return 0.01  # 默认波动率
    
    def _get_trading_session(self) -> str:
        """获取交易时段"""
        from datetime import datetime
        current_hour = datetime.now().hour
        
        if 9 <= current_hour < 12:
            return 'morning'
        elif 13 <= current_hour < 15:
            return 'afternoon'
        elif 21 <= current_hour < 24 or 0 <= current_hour < 3:
            return 'night'
        else:
            return 'closed'
    
    def _create_orders(self, decision: Decision) -> List[Order]:
        """基于决策创建订单"""
        if decision.quantity == 0:
            return []
        
        order = Order(
            symbol=self.symbol,
            action=decision.action,
            quantity=abs(decision.quantity),
            price=decision.price,
            order_type='MARKET',  # 简化为市价单
            strategy_name=self.name,
            timestamp=decision.timestamp,
            reason=decision.reason
        )
        
        return [order]
    
    def _log_decision(self, signal: Signal, decision: Decision):
        """记录决策信息"""
        print(f"[{self.name}] 策略决策:")
        print(f"  信号: {signal.action} (强度: {signal.strength:.2f}) - {signal.reason}")
        print(f"  决策: {decision.action} {decision.quantity}手 @ {decision.price:.2f}")
        print(f"  置信度: {decision.confidence:.2f}")
        print(f"  当前持仓: {self.current_position}")
    
    def on_order_update(self, order_data: Dict[str, Any]):
        """处理订单状态更新"""
        print(f"[{self.name}] 订单更新: {order_data}")
    
    def on_trade_update(self, trade_data: Dict[str, Any]):
        """处理成交更新"""
        print(f"[{self.name}] 成交更新: {trade_data}")
        
        # 更新持仓
        direction = trade_data.get('direction')
        volume = trade_data.get('volume', 0)
        
        if direction == 'BUY':
            self.current_position += volume
        elif direction == 'SELL':
            self.current_position -= volume
        
        # 更新统计
        self.total_trades += 1
        
        # 如果是平仓交易，更新盈亏
        if trade_data.get('offset') == 'CLOSE':
            pnl = trade_data.get('pnl', 0)
            self.total_pnl += pnl
            self.daily_pnl += pnl
            
            if pnl > 0:
                self.winning_trades += 1
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        signal_stats = {}
        decision_stats = {}
        
        # 获取组件统计
        try:
            current_indicators = self.signal_generator.get_current_indicators()
            decision_stats = self.decision_engine.get_decision_statistics()
        except:
            pass
        
        return {
            'name': self.name,
            'symbol': self.symbol,
            'is_active': self.is_active,
            'current_position': self.current_position,
            'last_price': self.last_price,
            'last_update_time': self.last_update_time,
            
            # 性能统计
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': self.winning_trades / max(self.total_trades, 1),
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            
            # 组件统计
            'current_indicators': current_indicators,
            'decision_stats': decision_stats
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取策略配置"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'max_position': self.max_position,
            'signals': self.config.get('signals', {}),
            'decisions': self.config.get('decisions', {})
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """更新策略配置"""
        self.config.update(new_config)
        
        # 重新初始化组件
        if 'signals' in new_config:
            self.signal_generator = SignalGenerator(new_config['signals'])
        
        if 'decisions' in new_config:
            self.decision_engine = DecisionEngine(new_config['decisions'])
        
        print(f"[{self.name}] 配置已更新")
    
    def reset(self):
        """重置策略状态"""
        self.current_position = 0
        self.daily_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # 重置组件
        self.signal_generator.reset()
        
        print(f"[{self.name}] 策略状态已重置")

# 策略工厂函数
def create_simple_shfe_strategy(name: str, config: Dict[str, Any]) -> SimpleSHFEStrategy:
    """创建简化SHFE策略实例"""
    
    # 默认配置
    default_config = {
        'symbol': 'au2509',
        'max_position': 10,
        'initial_margin': 100000.0,
        
        'signals': {
            'strategy_type': 'trend',
            'ma_short': 5,
            'ma_long': 20,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        },
        
        'decisions': {
            'min_decision_interval': 5,  # 5秒最小决策间隔
            'filters': [
                {
                    'type': 'time',
                    'start_time': '09:00',
                    'end_time': '15:00'
                },
                {
                    'type': 'volatility',
                    'min_volatility': 0.001,
                    'max_volatility': 0.1
                }
            ],
            'position_sizing': {
                'method': 'fixed',
                'base_size': 1,
                'max_size': 5
            }
        }
    }
    
    # 合并配置
    merged_config = {**default_config, **config}
    
    return SimpleSHFEStrategy(name, merged_config)
