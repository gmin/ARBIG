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
            
        # 计算基差
        spread = self.shfe_price - self.mt5_price
        
        # 生成交易信号
        signal = self.arbitrage_strategy.generate_signal(spread)
        
        if signal and signal != self.last_signal:
            # 计算仓位
            position = self.arbitrage_strategy.calculate_position(signal, self.position)
            
            if position > 0:
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
                
                print(f"[{self.name}] 生成套利信号: {signal}, 基差: {spread:.2f}, 仓位: {position}")
                
        # 发送基差事件
        spread_event = Event(SPREAD_EVENT, {
            'spread': spread,
            'shfe_price': self.shfe_price,
            'mt5_price': self.mt5_price,
            'timestamp': time.time()
        })
        self.event_engine.put(spread_event) 