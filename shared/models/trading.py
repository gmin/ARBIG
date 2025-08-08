"""
交易相关数据模型
定义交易系统中使用的数据结构
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from decimal import Decimal

class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class PositionDirection(str, Enum):
    """持仓方向"""
    LONG = "long"
    SHORT = "short"

class SignalType(str, Enum):
    """策略信号类型"""
    BUY = "buy"
    SELL = "sell"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"

class ExecutionResult(str, Enum):
    """执行结果"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    IGNORED = "ignored"

# 基础数据模型
class TickData(BaseModel):
    """Tick数据模型"""
    symbol: str = Field(..., description="合约代码")
    timestamp: float = Field(..., description="时间戳（毫秒）")
    last_price: float = Field(..., description="最新价")
    volume: int = Field(..., description="成交量")
    bid_price: float = Field(..., description="买一价")
    ask_price: float = Field(..., description="卖一价")
    bid_volume: int = Field(..., description="买一量")
    ask_volume: int = Field(..., description="卖一量")
    high_price: float = Field(0, description="最高价")
    low_price: float = Field(0, description="最低价")
    open_price: float = Field(0, description="开盘价")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AccountInfo(BaseModel):
    """账户信息模型"""
    account_id: str = Field(..., description="账户ID")
    balance: float = Field(..., description="账户余额")
    available: float = Field(..., description="可用资金")
    margin: float = Field(..., description="保证金占用")
    unrealized_pnl: float = Field(0, description="未实现盈亏")
    realized_pnl: float = Field(0, description="已实现盈亏")
    currency: str = Field("CNY", description="币种")
    risk_ratio: float = Field(0, description="风险度")
    update_time: Optional[datetime] = Field(None, description="更新时间")

class PositionInfo(BaseModel):
    """持仓信息模型"""
    id: Optional[int] = Field(None, description="主键ID")
    account_id: str = Field(..., description="账户ID")
    symbol: str = Field(..., description="合约代码")
    direction: PositionDirection = Field(..., description="持仓方向")
    volume: int = Field(..., description="持仓数量")
    avg_price: float = Field(..., description="平均成本价")
    current_price: float = Field(0, description="当前价格")
    unrealized_pnl: float = Field(0, description="未实现盈亏")
    margin: float = Field(0, description="保证金占用")
    open_time: Optional[datetime] = Field(None, description="开仓时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    
    def calculate_pnl(self, current_price: float, contract_multiplier: int = 1000) -> float:
        """计算未实现盈亏"""
        if self.direction == PositionDirection.LONG:
            return (current_price - self.avg_price) * self.volume * contract_multiplier
        else:
            return (self.avg_price - current_price) * self.volume * contract_multiplier

class OrderInfo(BaseModel):
    """订单信息模型"""
    id: Optional[int] = Field(None, description="主键ID")
    order_id: str = Field(..., description="订单ID")
    account_id: str = Field(..., description="账户ID")
    symbol: str = Field(..., description="合约代码")
    direction: OrderSide = Field(..., description="买卖方向")
    order_type: OrderType = Field(OrderType.LIMIT, description="订单类型")
    volume: int = Field(..., description="订单数量")
    price: Optional[float] = Field(None, description="订单价格")
    filled_volume: int = Field(0, description="已成交数量")
    avg_price: float = Field(0, description="平均成交价")
    status: OrderStatus = Field(OrderStatus.PENDING, description="订单状态")
    order_time: datetime = Field(..., description="下单时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

class TradeInfo(BaseModel):
    """交易记录模型"""
    id: Optional[int] = Field(None, description="主键ID")
    trade_id: str = Field(..., description="成交ID")
    order_id: str = Field(..., description="订单ID")
    account_id: str = Field(..., description="账户ID")
    symbol: str = Field(..., description="合约代码")
    direction: OrderSide = Field(..., description="买卖方向")
    volume: int = Field(..., description="成交数量")
    price: float = Field(..., description="成交价格")
    commission: float = Field(0, description="手续费")
    trade_time: datetime = Field(..., description="成交时间")
    create_time: Optional[datetime] = Field(None, description="创建时间")

class StrategyConfig(BaseModel):
    """策略配置模型"""
    id: Optional[int] = Field(None, description="主键ID")
    strategy_name: str = Field(..., description="策略名称")
    strategy_class: str = Field(..., description="策略类名")
    config_data: Dict[str, Any] = Field(..., description="策略配置数据")
    is_active: bool = Field(False, description="是否激活")
    description: Optional[str] = Field(None, description="策略描述")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

class StrategyTrigger(BaseModel):
    """策略触发记录模型"""
    id: Optional[int] = Field(None, description="主键ID")
    strategy_name: str = Field(..., description="策略名称")
    trigger_time: datetime = Field(..., description="触发时间")
    trigger_condition: str = Field(..., description="触发条件描述")
    trigger_price: Optional[float] = Field(None, description="触发时价格")
    signal_type: SignalType = Field(..., description="信号类型")
    action_type: SignalType = Field(..., description="执行动作")
    execution_result: ExecutionResult = Field(..., description="执行结果")
    order_id: Optional[str] = Field(None, description="关联订单ID")
    volume: Optional[int] = Field(None, description="操作数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[datetime] = Field(None, description="执行时间")
    create_time: Optional[datetime] = Field(None, description="创建时间")

# 响应模型
class MarketDataResponse(BaseModel):
    """行情数据响应模型"""
    symbol: str = Field(..., description="合约代码")
    tick_data: TickData = Field(..., description="Tick数据")
    is_connected: bool = Field(..., description="连接状态")
    last_update: datetime = Field(..., description="最后更新时间")

class PositionSummary(BaseModel):
    """持仓汇总模型"""
    total_positions: int = Field(..., description="持仓总数")
    total_volume: int = Field(..., description="总持仓量")
    total_margin: float = Field(..., description="总保证金")
    total_unrealized_pnl: float = Field(..., description="总未实现盈亏")
    positions: List[PositionInfo] = Field(..., description="持仓列表")

class AccountSummary(BaseModel):
    """账户汇总模型"""
    account_info: AccountInfo = Field(..., description="账户信息")
    position_summary: PositionSummary = Field(..., description="持仓汇总")
    daily_pnl: float = Field(0, description="当日盈亏")
    total_assets: float = Field(..., description="总资产")

class TradingSummary(BaseModel):
    """交易汇总模型"""
    trade_date: str = Field(..., description="交易日期")
    trade_count: int = Field(..., description="交易次数")
    buy_volume: int = Field(..., description="买入量")
    sell_volume: int = Field(..., description="卖出量")
    total_commission: float = Field(..., description="总手续费")
    net_pnl: float = Field(..., description="净盈亏")

class StrategyStatus(BaseModel):
    """策略状态模型"""
    strategy_name: str = Field(..., description="策略名称")
    is_active: bool = Field(..., description="是否激活")
    last_trigger_time: Optional[datetime] = Field(None, description="最后触发时间")
    trigger_count_today: int = Field(0, description="今日触发次数")
    success_rate: float = Field(0, description="成功率")
    current_position: Optional[PositionInfo] = Field(None, description="当前持仓")

# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

class MarketDataMessage(WebSocketMessage):
    """行情数据WebSocket消息"""
    type: str = Field("market_data", description="消息类型")
    data: TickData = Field(..., description="Tick数据")

class PositionUpdateMessage(WebSocketMessage):
    """持仓更新WebSocket消息"""
    type: str = Field("position_update", description="消息类型")
    data: PositionInfo = Field(..., description="持仓数据")

class AccountUpdateMessage(WebSocketMessage):
    """账户更新WebSocket消息"""
    type: str = Field("account_update", description="消息类型")
    data: AccountInfo = Field(..., description="账户数据")

class StrategyTriggerMessage(WebSocketMessage):
    """策略触发WebSocket消息"""
    type: str = Field("strategy_trigger", description="消息类型")
    data: StrategyTrigger = Field(..., description="策略触发数据")
