"""
高级SHFE策略 - 使用组件化框架
基于ARBIGCtaTemplate和框架组件实现的高级策略
展示如何使用DecisionEngine和SignalGenerator
"""

import time
from typing import Dict, Any
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import TickData, BarData
from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from vnpy.trader.utility import ArrayManager
from services.strategy_service.core.framework.decision_engine import DecisionEngine, Decision, MarketContext, PortfolioContext
from services.strategy_service.core.framework.signal_generator import SignalGenerator
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedSHFEStrategy(ARBIGCtaTemplate):
    """
    高级SHFE策略 - 组件化实现
    
    特点：
    1. 使用SignalGenerator生成技术信号
    2. 使用DecisionEngine做交易决策
    3. 多时间周期分析
    4. 智能风险控制
    """
    
    # 策略参数
    signal_config = {
        "strategy_type": "trend",
        "ma_short": 5,
        "ma_long": 20,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    }
    
    decision_config = {
        "min_decision_interval": 60,  # 最小决策间隔(秒)
        "filters": [
            {
                "type": "time",
                "start_time": "09:00",
                "end_time": "15:00"
            },
            {
                "type": "volatility", 
                "min_volatility": 0.001,
                "max_volatility": 0.1
            }
        ],
        "position_sizing": {
            "method": "fixed",
            "base_size": 1,
            "max_size": 5
        }
    }
    
    trade_volume = 1      # 基础交易手数
    max_position = 10     # 最大持仓
    
    # 策略变量
    last_decision_time = 0
    decision_count = 0
    
    def __init__(self, strategy_engine, strategy_name: str, symbol: str, setting: dict):
        """初始化策略"""
        super().__init__(strategy_engine, strategy_name, symbol, setting)
        
        # 从设置中获取参数
        self.signal_config.update(setting.get('signal_config', {}))
        self.decision_config.update(setting.get('decision_config', {}))
        self.trade_volume = setting.get('trade_volume', self.trade_volume)
        self.max_position = setting.get('max_position', self.max_position)
        
        # 初始化组件
        self.signal_generator = SignalGenerator(self.signal_config)
        self.decision_engine = DecisionEngine(self.decision_config)
        
        # 初始化ArrayManager
        self.am = ArrayManager()
        
        # 价格历史（用于信号生成器）
        self.price_history = []
        
        logger.info(f"✅ {self.strategy_name} 初始化完成")
        logger.info(f"   交易品种: {self.symbol}")
        logger.info(f"   信号配置: {self.signal_config}")
        logger.info(f"   决策配置: {self.decision_config}")
    
    def on_init(self):
        """策略初始化回调"""
        self.write_log("高级SHFE策略初始化")
        
    def on_start(self):
        """策略启动回调"""
        self.write_log("🚀 高级SHFE策略已启动")
        
    def on_stop(self):
        """策略停止回调"""
        self.write_log("⏹️ 高级SHFE策略已停止")
        
    def on_tick(self, tick: TickData):
        """处理tick数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager
        self.am.update_tick(tick)
        
        # 更新价格历史
        self.price_history.append(tick.last_price)
        if len(self.price_history) > 200:
            self.price_history = self.price_history[-200:]
        
    def on_bar(self, bar: BarData):
        """处理bar数据"""
        if not self.trading:
            return
            
        # 更新ArrayManager
        self.am.update_bar(bar)
        
        # 确保有足够的数据
        if not self.am.inited or len(self.price_history) < 50:
            return
            
        # 检查决策间隔
        current_time = time.time()
        if current_time - self.last_decision_time < self.decision_config["min_decision_interval"]:
            return
            
        # 生成交易决策
        self._make_trading_decision(bar)
        
    def _make_trading_decision(self, bar: BarData):
        """生成交易决策"""
        try:
            # 1. 生成信号
            signal = self.signal_generator.generate_signal(
                price=bar.close_price, 
                timestamp=time.time()
            )
            
            if not signal:
                return
                
            # 2. 构建上下文
            market_context = self._build_market_context(bar)
            portfolio_context = self._build_portfolio_context()
            
            # 3. 做出决策
            decision = self.decision_engine.make_decision(
                signal=signal,
                market_context=market_context,
                portfolio_context=portfolio_context
            )
            
            if not decision or decision.quantity == 0:
                return
                
            # 4. 执行决策
            self._execute_decision(decision)
            
            self.last_decision_time = time.time()
            self.decision_count += 1
            
        except Exception as e:
            self.write_log(f"决策生成异常: {e}")
            
    def _build_market_context(self, bar: BarData) -> MarketContext:
        """构建市场上下文"""
        # 计算波动率
        volatility = 0.0
        if len(self.am.close_array) >= 20:
            returns = []
            for i in range(1, min(20, len(self.am.close_array))):
                ret = (self.am.close_array[-i] - self.am.close_array[-i-1]) / self.am.close_array[-i-1]
                returns.append(ret)
            if returns:
                volatility = float(np.std(returns))
        
        return MarketContext(
            current_price=bar.close_price,
            volatility=volatility,
            volume=bar.volume,
            timestamp=time.time(),
            trading_session=self._get_trading_session()
        )
    
    def _build_portfolio_context(self) -> PortfolioContext:
        """构建投资组合上下文"""
        return PortfolioContext(
            current_position=self.pos,
            available_margin=100000.0,  # 假设可用保证金
            unrealized_pnl=0.0,  # 这里可以从策略引擎获取
            daily_pnl=0.0,
            max_position=self.max_position
        )
    
    def _get_trading_session(self) -> str:
        """获取交易时段"""
        current_hour = datetime.now().hour
        
        if 9 <= current_hour < 12:
            return 'morning'
        elif 13 <= current_hour < 15:
            return 'afternoon'
        elif 21 <= current_hour < 24 or 0 <= current_hour < 3:
            return 'night'
        else:
            return 'closed'
    
    def _execute_decision(self, decision: Decision):
        """执行交易决策"""
        # 检查持仓限制
        if abs(self.pos) >= self.max_position:
            self.write_log(f"已达最大持仓 {self.max_position}，忽略决策")
            return
            
        quantity = min(decision.quantity, self.max_position - abs(self.pos))
        
        if decision.action == "BUY":
            self.buy(decision.price, quantity, stop=False)
        elif decision.action == "SELL":
            self.sell(decision.price, quantity, stop=False)
        elif decision.action == "CLOSE_LONG" and self.pos > 0:
            self.sell(decision.price, min(quantity, self.pos), stop=False)
        elif decision.action == "CLOSE_SHORT" and self.pos < 0:
            self.buy(decision.price, min(quantity, abs(self.pos)), stop=False)
        else:
            return
            
        self.write_log(f"📊 决策 #{self.decision_count}: {decision.action} {quantity}手")
        self.write_log(f"   原因: {decision.reason}")
        self.write_log(f"   置信度: {decision.confidence:.2f}")
        self.write_log(f"   价格: {decision.price:.2f}, 持仓: {self.pos}")
        
    def on_order(self, order):
        """处理订单回调"""
        self.write_log(f"订单状态: {order.orderid} - {order.status}")
        
    def on_trade(self, trade):
        """处理成交回调"""
        self.write_log(f"✅ 成交: {trade.direction} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"   当前持仓: {self.pos}")
        
        # 大额成交通知
        if abs(trade.volume) >= 3:
            self.send_email(f"大额成交: {trade.direction} {trade.volume}手")
            
    def on_stop_order(self, stop_order):
        """处理停止单回调"""
        self.write_log(f"停止单触发: {stop_order.orderid}")
        
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        if not self.am.inited:
            return {"status": "数据不足"}
            
        # 获取组件状态
        signal_stats = {}
        decision_stats = {}
        
        try:
            signal_stats = self.signal_generator.get_current_indicators()
            decision_stats = self.decision_engine.get_decision_statistics()
        except:
            pass
            
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "position": self.pos,
            "decision_count": self.decision_count,
            "signal_stats": signal_stats,
            "decision_stats": decision_stats,
            "last_price": self.am.close_array[-1] if len(self.am.close_array) > 0 else 0
        }


# 策略工厂函数
def create_strategy(strategy_engine, strategy_name: str, symbol: str, setting: dict) -> AdvancedSHFEStrategy:
    """创建高级SHFE策略实例"""
    
    # 默认设置
    default_setting = {
        'signal_config': {
            "strategy_type": "trend",
            "ma_short": 5,
            "ma_long": 20,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30
        },
        'decision_config': {
            "min_decision_interval": 60,
            "filters": [
                {
                    "type": "time",
                    "start_time": "09:00", 
                    "end_time": "15:00"
                }
            ],
            "position_sizing": {
                "method": "fixed",
                "base_size": 1,
                "max_size": 5
            }
        },
        'trade_volume': 1,
        'max_position': 10
    }
    
    # 合并设置
    merged_setting = {**default_setting, **setting}
    
    return AdvancedSHFEStrategy(strategy_engine, strategy_name, symbol, merged_setting)


# 策略配置模板
STRATEGY_TEMPLATE = {
    "class_name": "AdvancedSHFEStrategy",
    "file_name": "advanced_shfe_strategy.py",
    "description": "高级SHFE策略，使用组件化框架，支持复杂决策逻辑",
    "parameters": {
        "signal_config": {
            "type": "dict",
            "default": {
                "strategy_type": "trend",
                "ma_short": 5,
                "ma_long": 20
            },
            "description": "信号生成配置"
        },
        "decision_config": {
            "type": "dict", 
            "default": {
                "min_decision_interval": 60
            },
            "description": "决策引擎配置"
        },
        "trade_volume": {
            "type": "int",
            "default": 1,
            "description": "基础交易手数"
        },
        "max_position": {
            "type": "int",
            "default": 10,
            "description": "最大持仓手数"
        }
    }
}


if __name__ == "__main__":
    # 本地测试代码
    print("高级SHFE策略模块加载成功")
    print(f"策略模板: {STRATEGY_TEMPLATE}")
