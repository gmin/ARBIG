"""
基差套利策略
实现香港离岸人民币黄金与上海黄金交易所黄金的基差套利
"""

import time
from typing import Dict, Any, Optional
from core.strategy_base import StrategyBase
from core.event_engine import Event
from core.constants import *
from core.strategy import ArbitrageStrategy

class SpreadArbitrageStrategy(StrategyBase):
    """
    基差套利策略
    监控香港和上海黄金价格，在基差达到阈值时进行套利交易
    """
    
    def __init__(self, name: str, event_engine, config: Dict[str, Any]):
        super().__init__(name, event_engine, config)
        
        # 初始化套利策略
        self.arbitrage_strategy = ArbitrageStrategy(config)
        
        # 价格缓存
        self.shfe_price = None
        self.mt5_price = None
        
        # 交易状态
        self.position = 0
        self.last_signal = None
        
    def on_start(self):
        """策略启动"""
        print(f"[{self.name}] 基差套利策略启动")
        
    def on_stop(self):
        """策略停止"""
        print(f"[{self.name}] 基差套利策略停止")
        
    def on_tick(self, event: Event):
        """处理Tick事件"""
        if not self.active:
            return
            
        tick_data = event.data
        
        # 更新价格缓存
        if tick_data.get('source') == 'shfe':
            self.shfe_price = tick_data.get('last_price')
        elif tick_data.get('source') == 'mt5':
            self.mt5_price = tick_data.get('last_price')
            
        # 计算基差并生成信号
        self._process_spread()
        
    def on_bar(self, event: Event):
        """处理K线事件"""
        # 基差套利主要基于Tick数据，K线可用于辅助分析
        pass
        
    def on_order(self, event: Event):
        """处理订单事件"""
        order_data = event.data
        print(f"[{self.name}] 订单状态更新: {order_data}")
        
    def on_trade(self, event: Event):
        """处理成交事件"""
        trade_data = event.data
        print(f"[{self.name}] 成交更新: {trade_data}")
        
        # 更新持仓
        if trade_data.get('direction') == 'BUY':
            self.position += trade_data.get('volume', 0)
        else:
            self.position -= trade_data.get('volume', 0)
            
    def on_account(self, event: Event):
        """处理账户事件"""
        account_data = event.data
        print(f"[{self.name}] 账户更新: {account_data}")
        
    def _process_spread(self):
        """处理基差计算和信号生成"""
        if self.shfe_price is None or self.mt5_price is None:
            return
            
        # 计算基差：spread = SHFE价格 - MT5价格
        spread = self.shfe_price - self.mt5_price
        
        # 基差套利逻辑说明：
        # 当spread > 0时：SHFE价格 > MT5价格，应该在低价MT5买入，高价SHFE卖出
        # 当spread < 0时：SHFE价格 < MT5价格，应该在低价SHFE买入，高价MT5卖出
        # 这样确保在低价市场买入，高价市场卖出，实现套利盈利
        
        # 生成套利信号
        signal = self._adjust_arbitrage_for_market_condition(spread)
        
        if signal and signal != self.last_signal:
            # 计算仓位
            position = self._calculate_position(signal)
            
            if position != 0:
                # 发送交易信号
                signal_data = {
                    'signal': signal,
                    'spread': spread,
                    'shfe_price': self.shfe_price,
                    'mt5_price': self.mt5_price,
                    'position': position,
                    'timestamp': time.time()
                }
                
                self.send_signal(signal_data)
                self.last_signal = signal
                
                # 详细的信号说明
                if signal == 'BUY_MT5_SELL_SHFE':
                    print(f"[{self.name}] 开仓信号: {signal}, 基差: {spread:.2f}, SHFE({self.shfe_price:.2f}) > MT5({self.mt5_price:.2f}), 买入MT5(低价), 卖出SHFE(高价), 仓位: {position}")
                elif signal == 'BUY_SHFE_SELL_MT5':
                    print(f"[{self.name}] 开仓信号: {signal}, 基差: {spread:.2f}, SHFE({self.shfe_price:.2f}) < MT5({self.mt5_price:.2f}), 买入SHFE(低价), 卖出MT5(高价), 仓位: {position}")
                elif signal in ['CLOSE_LONG', 'CLOSE_SHORT']:
                    print(f"[{self.name}] 平仓信号: {signal}, 基差: {spread:.2f}, 当前持仓: {self.position}")
                
        # 发送基差事件
        spread_event = Event(SPREAD_EVENT, {
            'spread': spread,
            'shfe_price': self.shfe_price,
            'mt5_price': self.mt5_price,
            'position': self.position,
            'timestamp': time.time()
        })
        self.event_engine.put(spread_event)
        
    def _adjust_arbitrage_for_market_condition(self, spread: float) -> str:
        """根据基差生成套利信号"""
        # 使用配置中的阈值，去掉复杂的市场状态判断
        entry_threshold = self.arbitrage_strategy.config.get('entry_threshold', 0.8)
        exit_threshold = self.arbitrage_strategy.config.get('exit_threshold', 0.2)
        
        # 如果有持仓，检查是否需要平仓
        if self.position != 0:
            if abs(spread) <= exit_threshold:
                # 基差回归到平仓阈值，平仓
                if self.position > 0:  # 持有多头
                    return 'CLOSE_LONG'
                else:  # 持有空头
                    return 'CLOSE_SHORT'
        
        # 如果没有持仓，检查是否需要开仓
        if abs(spread) > entry_threshold:
            if spread > 0:
                # SHFE价格 > MT5价格，买入MT5(低价)，卖出SHFE(高价)
                return 'BUY_MT5_SELL_SHFE'
            else:
                # SHFE价格 < MT5价格，买入SHFE(低价)，卖出MT5(高价)
                return 'BUY_SHFE_SELL_MT5'
                
        return None
        
    def _calculate_position(self, signal: str) -> int:
        """计算交易仓位"""
        if signal in ['CLOSE_LONG', 'CLOSE_SHORT']:
            # 平仓：全部平仓
            return -self.position
        
        # 开仓：使用固定仓位
        base_position = self.arbitrage_strategy.calculate_position(signal, self.position)
        return base_position 