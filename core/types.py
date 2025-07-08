"""
数据类型定义
定义系统中使用的所有数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

# 导入vnpy的数据类型
from vnpy.trader.object import (
    TickData, OrderData, TradeData, PositionData, AccountData,
    OrderRequest, CancelRequest, SubscribeRequest
)
from vnpy.trader.constant import (
    Direction, OrderType, Status, Offset, Exchange
)

# 重新导出vnpy类型，方便使用
__all__ = [
    # vnpy数据类型
    'TickData', 'OrderData', 'TradeData', 'PositionData', 'AccountData',
    'OrderRequest', 'CancelRequest', 'SubscribeRequest',
    'Direction', 'OrderType', 'Status', 'Offset', 'Exchange',
    
    # 自定义数据类型
    'RiskCheckResult', 'SignalData', 'ServiceStatus'
]

# 自定义枚举类型
class ServiceStatus(Enum):
    """服务状态"""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

# 自定义数据类型
@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    reason: str = ""
    suggested_volume: float = 0.0
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class SignalData:
    """策略信号数据"""
    strategy_name: str
    symbol: str
    direction: Direction
    action: str  # OPEN, CLOSE, CANCEL
    volume: float
    price: Optional[float] = None
    signal_type: str = "TRADE"  # TRADE, RISK, INFO
    confidence: float = 1.0
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}

@dataclass
class MarketSnapshot:
    """市场快照"""
    timestamp: datetime
    symbols: Dict[str, TickData]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class AccountSnapshot:
    """账户快照"""
    timestamp: datetime
    account: Optional[AccountData]
    positions: Dict[str, PositionData]
    orders: Dict[str, OrderData]
    trades: Dict[str, TradeData]
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class RiskMetrics:
    """风险指标"""
    timestamp: datetime
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    position_ratio: float = 0.0
    margin_ratio: float = 0.0
    risk_level: str = "LOW"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

# 事件数据类型
@dataclass
class EventData:
    """事件数据基类"""
    event_type: str
    timestamp: datetime = None
    source: str = ""
    data: Any = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TickEventData(EventData):
    """Tick事件数据"""
    tick: TickData = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = "TICK"
        self.data = self.tick

@dataclass
class OrderEventData(EventData):
    """订单事件数据"""
    order: OrderData = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = "ORDER"
        self.data = self.order

@dataclass
class TradeEventData(EventData):
    """成交事件数据"""
    trade: TradeData = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = "TRADE"
        self.data = self.trade

@dataclass
class SignalEventData(EventData):
    """信号事件数据"""
    signal: SignalData = None

    def __post_init__(self):
        super().__post_init__()
        self.event_type = "SIGNAL"
        self.data = self.signal

@dataclass
class RiskEventData(EventData):
    """风险事件数据"""
    risk_type: str = ""
    risk_level: str = ""
    message: str = ""
    metrics: Optional[RiskMetrics] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.event_type = "RISK"
        self.data = {
            'risk_type': self.risk_type,
            'risk_level': self.risk_level,
            'message': self.message,
            'metrics': self.metrics
        }

# 配置相关类型
@dataclass
class CtpConfig:
    """CTP配置"""
    userid: str = ""
    password: str = ""
    brokerid: str = ""
    td_address: str = ""
    md_address: str = ""
    appid: str = ""
    auth_code: str = ""
    product_info: str = ""

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 27017
    database: str = "arbig"
    username: str = ""
    password: str = ""

@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
