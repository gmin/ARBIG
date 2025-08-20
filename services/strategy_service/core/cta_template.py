"""
ARBIG CTA策略模板
基于vnpy CtaTemplate设计，适配ARBIG微服务架构
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from core.types import (
    TickData, BarData, OrderData, TradeData, SignalData,
    Direction, OrderType, Status
)
from core.event_engine import EventEngine, Event
from core.constants import SIGNAL_EVENT
from utils.logger import get_logger

logger = get_logger(__name__)

class StrategyStatus(Enum):
    """策略状态"""
    INIT = "init"           # 初始化
    RUNNING = "running"     # 运行中
    STOPPED = "stopped"     # 已停止
    ERROR = "error"         # 错误状态

class ARBIGCtaTemplate(ABC):
    """
    ARBIG CTA策略模板
    
    基于vnpy CtaTemplate设计理念，提供标准化的策略开发接口
    同时适配ARBIG的微服务架构，通过事件机制与交易服务通信
    """
    
    # 策略参数（子类可重写）
    parameters = []
    variables = []
    
    def __init__(
        self,
        strategy_name: str,
        symbol: str,
        setting: Dict[str, Any],
        signal_sender  # 信号发送器，用于向交易服务发送信号
    ):
        """
        初始化策略
        
        Args:
            strategy_name: 策略名称
            symbol: 交易合约
            setting: 策略参数设置
            signal_sender: 信号发送器
        """
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.setting = setting.copy()
        self.signal_sender = signal_sender
        
        # 策略状态
        self.status = StrategyStatus.INIT
        self.active = False
        self.trading = False
        
        # 持仓信息
        self.pos = 0            # 净持仓
        self.target_pos = 0     # 目标持仓
        
        # 订单管理
        self.orders: Dict[str, OrderData] = {}
        self.trades: Dict[str, TradeData] = {}
        
        # 数据存储
        self.tick: Optional[TickData] = None
        self.bar: Optional[BarData] = None
        self.bars: List[BarData] = []
        
        # 统计信息
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        
        # 初始化策略参数
        self.update_setting(setting)
        
        logger.info(f"策略初始化完成: {self.strategy_name} - {self.symbol}")
    
    def update_setting(self, setting: Dict[str, Any]) -> None:
        """
        更新策略参数
        
        Args:
            setting: 新的参数设置
        """
        for name in self.parameters:
            if name in setting:
                setattr(self, name, setting[name])
        
        self.setting.update(setting)
        logger.info(f"策略参数更新: {self.strategy_name}")
    
    def get_variables(self) -> Dict[str, Any]:
        """获取策略变量"""
        variables = {}
        for name in self.variables:
            variables[name] = getattr(self, name, None)
        return variables
    
    def get_parameters(self) -> Dict[str, Any]:
        """获取策略参数"""
        parameters = {}
        for name in self.parameters:
            parameters[name] = getattr(self, name, None)
        return parameters
    
    # ==================== 策略生命周期管理 ====================
    
    def start(self) -> None:
        """启动策略"""
        if self.status != StrategyStatus.INIT:
            logger.warning(f"策略 {self.strategy_name} 状态异常，无法启动")
            return
        
        try:
            self.active = True
            self.trading = True  # 策略微服务中默认允许交易
            self.status = StrategyStatus.RUNNING
            self.on_init()
            self.on_start()
            logger.info(f"策略启动成功: {self.strategy_name}")
        except Exception as e:
            self.status = StrategyStatus.ERROR
            logger.error(f"策略启动失败 {self.strategy_name}: {e}")
    
    def stop(self) -> None:
        """停止策略"""
        if self.status != StrategyStatus.RUNNING:
            logger.warning(f"策略 {self.strategy_name} 未在运行")
            return
        
        try:
            self.active = False
            self.trading = False
            self.status = StrategyStatus.STOPPED
            self.on_stop()
            logger.info(f"策略停止成功: {self.strategy_name}")
        except Exception as e:
            self.status = StrategyStatus.ERROR
            logger.error(f"策略停止失败 {self.strategy_name}: {e}")
    
    # ==================== 标准交易方法 (vnpy风格) ====================
    
    def buy(self, price: float, volume: int, stop: bool = False) -> str:
        """
        买入开仓
        
        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            
        Returns:
            订单ID
        """
        return self._send_order(Direction.LONG, "BUY", volume, price, stop)
    
    def sell(self, price: float, volume: int, stop: bool = False) -> str:
        """
        卖出平仓
        
        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            
        Returns:
            订单ID
        """
        return self._send_order(Direction.SHORT, "SELL", volume, price, stop)
    
    def short(self, price: float, volume: int, stop: bool = False) -> str:
        """
        卖出开仓
        
        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            
        Returns:
            订单ID
        """
        return self._send_order(Direction.SHORT, "SHORT", volume, price, stop)
    
    def cover(self, price: float, volume: int, stop: bool = False) -> str:
        """
        买入平仓
        
        Args:
            price: 委托价格，0表示市价单
            volume: 委托数量
            stop: 是否为停止单
            
        Returns:
            订单ID
        """
        return self._send_order(Direction.LONG, "COVER", volume, price, stop)
    
    def set_target_pos(self, target_pos: int) -> None:
        """
        设置目标持仓
        
        Args:
            target_pos: 目标持仓数量（正数为多头，负数为空头）
        """
        self.target_pos = target_pos
        
        # 计算需要调整的持仓
        pos_diff = target_pos - self.pos
        
        if pos_diff > 0:
            # 需要增加多头持仓
            if self.pos < 0:
                # 当前为空头，先平仓再开多
                cover_volume = min(abs(self.pos), pos_diff)
                self.cover(0, cover_volume)  # 市价平空
                pos_diff -= cover_volume
            
            if pos_diff > 0:
                # 开多头仓位
                self.buy(0, pos_diff)  # 市价买入
        
        elif pos_diff < 0:
            # 需要减少持仓或增加空头
            pos_diff = abs(pos_diff)
            
            if self.pos > 0:
                # 当前为多头，先平仓再开空
                sell_volume = min(self.pos, pos_diff)
                self.sell(0, sell_volume)  # 市价平多
                pos_diff -= sell_volume
            
            if pos_diff > 0:
                # 开空头仓位
                self.short(0, pos_diff)  # 市价卖空
        
        logger.info(f"设置目标持仓: {self.strategy_name} {self.pos} -> {target_pos}")
    
    def _send_order(
        self, 
        direction: Direction, 
        action: str, 
        volume: int, 
        price: float, 
        stop: bool = False
    ) -> str:
        """
        发送订单信号到交易服务
        
        Args:
            direction: 交易方向
            action: 交易动作
            volume: 数量
            price: 价格
            stop: 是否为停止单
            
        Returns:
            订单ID
        """
        if not self.active or not self.trading:
            logger.warning(f"策略 {self.strategy_name} 未激活或禁止交易")
            return ""
        
        # 创建信号数据
        signal = SignalData(
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            direction=direction,
            action=action,
            volume=volume,
            price=price if price > 0 else None,  # 0价格表示市价单
            signal_type="TRADE",
            timestamp=datetime.now(),
            metadata={"stop_order": stop}  # 将stop_order放入metadata中
        )
        
        # 通过信号发送器发送到交易服务
        order_id = self.signal_sender.send_signal(signal)
        
        logger.info(f"发送交易信号: {self.strategy_name} {action} {volume}@{price}")
        return order_id
    
    # ==================== 数据处理方法 ====================
    
    def on_tick(self, tick: TickData) -> None:
        """
        Tick数据回调
        
        Args:
            tick: Tick数据
        """
        if not self.active:
            return
        
        self.tick = tick
        
        # 调用策略实现
        try:
            self.on_tick_impl(tick)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} Tick处理异常: {e}")
    
    def on_bar(self, bar: BarData) -> None:
        """
        Bar数据回调
        
        Args:
            bar: Bar数据
        """
        if not self.active:
            return
        
        self.bar = bar
        self.bars.append(bar)
        
        # 限制历史数据长度
        if len(self.bars) > 1000:
            self.bars = self.bars[-1000:]
        
        # 调用策略实现
        try:
            self.on_bar_impl(bar)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} Bar处理异常: {e}")
    
    def on_order(self, order: OrderData) -> None:
        """
        订单状态回调
        
        Args:
            order: 订单数据
        """
        self.orders[order.order_id] = order
        
        try:
            self.on_order_impl(order)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} 订单处理异常: {e}")
    
    def on_trade(self, trade: TradeData) -> None:
        """
        成交回调
        
        Args:
            trade: 成交数据
        """
        self.trades[trade.trade_id] = trade
        
        # 更新持仓
        if trade.direction == Direction.LONG:
            if trade.offset == "OPEN":
                self.pos += trade.volume
            else:  # CLOSE
                self.pos -= trade.volume
        else:  # SHORT
            if trade.offset == "OPEN":
                self.pos -= trade.volume
            else:  # CLOSE
                self.pos += trade.volume
        
        # 更新统计
        self.total_trades += 1
        self.total_pnl += trade.pnl if hasattr(trade, 'pnl') else 0
        
        logger.info(f"策略成交: {self.strategy_name} {trade.direction.value} "
                   f"{trade.volume}@{trade.price} 持仓:{self.pos}")
        
        try:
            self.on_trade_impl(trade)
        except Exception as e:
            logger.error(f"策略 {self.strategy_name} 成交处理异常: {e}")
    
    # ==================== 抽象方法 (子类必须实现) ====================
    
    @abstractmethod
    def on_init(self) -> None:
        """策略初始化"""
        pass
    
    @abstractmethod
    def on_start(self) -> None:
        """策略启动"""
        pass
    
    @abstractmethod
    def on_stop(self) -> None:
        """策略停止"""
        pass
    
    @abstractmethod
    def on_tick_impl(self, tick: TickData) -> None:
        """Tick数据处理实现"""
        pass
    
    @abstractmethod
    def on_bar_impl(self, bar: BarData) -> None:
        """Bar数据处理实现"""
        pass
    
    def on_order_impl(self, order: OrderData) -> None:
        """订单状态处理实现（可选重写）"""
        pass
    
    def on_trade_impl(self, trade: TradeData) -> None:
        """成交处理实现（可选重写）"""
        pass
    
    # ==================== 工具方法 ====================
    
    def write_log(self, msg: str, level: str = "INFO") -> None:
        """写入日志"""
        log_msg = f"[{self.strategy_name}] {msg}"
        if level == "INFO":
            logger.info(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        elif level == "ERROR":
            logger.error(log_msg)
        elif level == "DEBUG":
            logger.debug(log_msg)
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取策略状态信息"""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "status": self.status.value,
            "active": self.active,
            "trading": self.trading,
            "pos": self.pos,
            "target_pos": self.target_pos,
            "total_trades": self.total_trades,
            "total_pnl": self.total_pnl,
            "parameters": self.get_parameters(),
            "variables": self.get_variables()
        }
