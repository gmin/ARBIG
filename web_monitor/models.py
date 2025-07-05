"""
Web监控系统的数据模型定义
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# ========== 请求模型 ==========

class RiskAction(BaseModel):
    """风控操作请求"""
    action: str = Field(..., description="操作类型")
    target: Optional[str] = Field(None, description="操作目标（如策略名、合约代码）")
    value: Optional[float] = Field(None, description="操作值（如价格、数量）")
    reason: str = Field(..., description="操作原因")
    operator: str = Field("web_user", description="操作员")
    confirmation_code: Optional[str] = Field(None, description="确认码（用于危险操作）")

class PositionLimitUpdate(BaseModel):
    """仓位限制更新"""
    symbol: str = Field(..., description="合约代码")
    new_limit: float = Field(..., description="新的仓位限制")
    reason: str = Field(..., description="调整原因")
    operator: str = Field("web_user", description="操作员")

class StopLossUpdate(BaseModel):
    """止损设置"""
    symbol: str = Field(..., description="合约代码")
    price: float = Field(..., description="止损价格")
    reason: str = Field(..., description="设置原因")
    operator: str = Field("web_user", description="操作员")

# ========== 响应模型 ==========

class SystemStatus(BaseModel):
    """系统状态"""
    timestamp: datetime
    services: Dict[str, str] = Field(..., description="各服务状态")
    risk_level: str = Field(..., description="当前风险级别")
    trading_halted: bool = Field(..., description="是否暂停交易")
    connections: Dict[str, bool] = Field(..., description="连接状态")

class PositionInfo(BaseModel):
    """持仓信息"""
    symbol: str
    direction: str
    volume: float
    price: float
    pnl: float
    frozen: float
    yd_volume: Optional[float] = None

class OrderInfo(BaseModel):
    """订单信息"""
    orderid: str
    symbol: str
    direction: str
    volume: float
    price: float
    status: str
    traded: float
    datetime: datetime
    strategy: Optional[str] = None

class TradeInfo(BaseModel):
    """成交信息"""
    tradeid: str
    orderid: str
    symbol: str
    direction: str
    volume: float
    price: float
    datetime: datetime

class MarketDataInfo(BaseModel):
    """行情信息"""
    symbol: str
    last_price: float
    bid_price_1: float
    ask_price_1: float
    bid_volume_1: int
    ask_volume_1: int
    volume: int
    datetime: datetime

class RiskMetrics(BaseModel):
    """风险指标"""
    timestamp: datetime
    daily_pnl: float
    total_pnl: float
    max_drawdown: float
    current_drawdown: float
    position_ratio: float
    margin_ratio: float
    risk_level: str

class TradingStatistics(BaseModel):
    """交易统计"""
    total_orders: int
    active_orders: int
    total_trades: int
    total_volume: float
    total_turnover: float
    avg_price: float
    strategies_count: int
    strategy_names: List[str]

class OperationLogEntry(BaseModel):
    """操作日志条目"""
    timestamp: datetime
    operator: str
    action: str
    details: str
    success: bool = True

class AlertInfo(BaseModel):
    """预警信息"""
    timestamp: datetime
    level: str  # INFO, WARNING, CRITICAL, EMERGENCY
    type: str   # 预警类型
    message: str
    details: Optional[Dict[str, Any]] = None

# ========== 复合响应模型 ==========

class DashboardData(BaseModel):
    """仪表板数据"""
    system_status: SystemStatus
    risk_metrics: RiskMetrics
    trading_stats: TradingStatistics
    positions: List[PositionInfo]
    active_orders: List[OrderInfo]
    recent_trades: List[TradeInfo]
    market_data: List[MarketDataInfo]
    recent_alerts: List[AlertInfo]

class ApiResponse(BaseModel):
    """通用API响应"""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# ========== WebSocket消息模型 ==========

class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str  # realtime_update, risk_alert, system_notification
    timestamp: datetime
    data: Dict[str, Any]

class RealTimeUpdate(BaseModel):
    """实时更新数据"""
    system_status: SystemStatus
    risk_metrics: RiskMetrics
    statistics: TradingStatistics
    active_orders_count: int
    positions_count: int
