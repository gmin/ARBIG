"""
API响应数据模型
定义所有API响应的数据结构
"""

from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ServiceStatus(str, Enum):
    """服务状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"

class APIResponse(BaseModel):
    """通用API响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field("", description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="操作失败")
    error: Dict[str, Any] = Field(..., description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

class ServiceInfo(BaseModel):
    """服务信息"""
    name: str = Field(..., description="服务名称")
    display_name: str = Field(..., description="显示名称")
    status: ServiceStatus = Field(..., description="服务状态")
    start_time: Optional[datetime] = Field(None, description="启动时间")
    uptime: Optional[str] = Field(None, description="运行时长")
    cpu_usage: Optional[str] = Field(None, description="CPU使用率")
    memory_usage: Optional[str] = Field(None, description="内存使用")
    last_heartbeat: Optional[datetime] = Field(None, description="最后心跳")
    required: bool = Field(False, description="是否必需服务")
    dependencies: List[str] = Field(default_factory=list, description="依赖服务")
    error_message: Optional[str] = Field(None, description="错误信息")

class ServiceStatusResponse(APIResponse):
    """服务状态响应"""
    data: Optional[ServiceInfo] = Field(None, description="服务信息")

class ServiceListResponse(APIResponse):
    """服务列表响应"""
    data: Optional[Dict[str, List[ServiceInfo]]] = Field(None, description="服务列表")

class CTPConnectionInfo(BaseModel):
    """CTP连接信息"""
    connected: bool = Field(..., description="是否连接")
    server: Optional[str] = Field(None, description="服务器地址")
    latency: Optional[str] = Field(None, description="延迟")
    last_connect_time: Optional[datetime] = Field(None, description="最后连接时间")
    error_message: Optional[str] = Field(None, description="错误信息")

class SystemInfo(BaseModel):
    """系统信息"""
    system_status: str = Field(..., description="系统状态")
    running_mode: str = Field(..., description="运行模式")
    start_time: datetime = Field(..., description="启动时间")
    uptime: str = Field(..., description="运行时长")
    ctp_status: Dict[str, CTPConnectionInfo] = Field(..., description="CTP连接状态")
    services_summary: Dict[str, int] = Field(..., description="服务统计")
    version: str = Field("1.0.0", description="系统版本")

class SystemStatusResponse(APIResponse):
    """系统状态响应"""
    data: Optional[SystemInfo] = Field(None, description="系统信息")

class StrategyInfo(BaseModel):
    """策略信息"""
    name: str = Field(..., description="策略名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field("", description="策略描述")
    version: str = Field("1.0.0", description="策略版本")
    risk_level: str = Field("medium", description="风险级别")
    status: str = Field("available", description="策略状态")
    author: str = Field("", description="策略作者")

class StrategyStatistics(BaseModel):
    """策略统计信息"""
    signals_generated: int = Field(0, description="生成信号数")
    orders_executed: int = Field(0, description="执行订单数")
    successful_trades: int = Field(0, description="成功交易数")
    failed_trades: int = Field(0, description="失败交易数")
    current_profit: float = Field(0.0, description="当前盈亏")
    today_profit: float = Field(0.0, description="今日盈亏")
    win_rate: float = Field(0.0, description="胜率")
    sharpe_ratio: float = Field(0.0, description="夏普比率")
    max_drawdown: float = Field(0.0, description="最大回撤")

class CurrentStrategyInfo(BaseModel):
    """当前策略信息"""
    strategy_name: str = Field(..., description="策略名称")
    display_name: str = Field(..., description="显示名称")
    status: str = Field(..., description="运行状态")
    start_time: datetime = Field(..., description="启动时间")
    runtime: str = Field(..., description="运行时长")
    statistics: StrategyStatistics = Field(..., description="统计信息")

class StrategyStatusResponse(APIResponse):
    """策略状态响应"""
    data: Optional[CurrentStrategyInfo] = Field(None, description="策略信息")

class StrategyListResponse(APIResponse):
    """策略列表响应"""
    data: Optional[Dict[str, List[StrategyInfo]]] = Field(None, description="策略列表")

class TickData(BaseModel):
    """Tick数据"""
    symbol: str = Field(..., description="合约代码")
    timestamp: datetime = Field(..., description="时间")
    last_price: float = Field(..., description="最新价")
    bid_price: float = Field(..., description="买价")
    ask_price: float = Field(..., description="卖价")
    volume: int = Field(..., description="成交量")
    open_interest: int = Field(..., description="持仓量")
    change: float = Field(..., description="涨跌")
    change_percent: float = Field(..., description="涨跌幅")

class KlineData(BaseModel):
    """K线数据"""
    symbol: str = Field(..., description="合约代码")
    timestamp: datetime = Field(..., description="时间")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    open_interest: int = Field(..., description="持仓量")

class MarketDataResponse(APIResponse):
    """行情数据响应"""
    data: Optional[Dict[str, Union[List[TickData], List[KlineData]]]] = Field(None, description="行情数据")

class AccountInfo(BaseModel):
    """账户信息"""
    account_id: str = Field(..., description="账户ID")
    total_assets: float = Field(..., description="总资产")
    available: float = Field(..., description="可用资金")
    margin: float = Field(..., description="占用保证金")
    frozen: float = Field(..., description="冻结资金")
    profit: float = Field(..., description="浮动盈亏")
    today_profit: float = Field(..., description="今日盈亏")
    commission: float = Field(..., description="手续费")
    currency: str = Field("CNY", description="币种")
    update_time: datetime = Field(..., description="更新时间")

class PositionInfo(BaseModel):
    """持仓信息"""
    symbol: str = Field(..., description="合约代码")
    direction: str = Field(..., description="方向")
    volume: float = Field(..., description="持仓量")
    avg_price: float = Field(..., description="均价")
    current_price: float = Field(..., description="现价")
    profit: float = Field(..., description="盈亏")
    margin: float = Field(..., description="保证金")
    open_time: datetime = Field(..., description="开仓时间")

class AccountResponse(APIResponse):
    """账户响应"""
    data: Optional[AccountInfo] = Field(None, description="账户信息")

class PositionsResponse(APIResponse):
    """持仓响应"""
    data: Optional[Dict[str, List[PositionInfo]]] = Field(None, description="持仓列表")

class RiskMetrics(BaseModel):
    """风险指标"""
    risk_level: str = Field(..., description="风险级别")
    position_ratio: float = Field(..., description="持仓比例")
    daily_loss: float = Field(..., description="日内亏损")
    max_drawdown: float = Field(..., description="最大回撤")
    var_95: float = Field(..., description="95% VaR")
    leverage: float = Field(..., description="杠杆率")
    concentration: Dict[str, float] = Field(..., description="持仓集中度")

class RiskResponse(APIResponse):
    """风控响应"""
    data: Optional[RiskMetrics] = Field(None, description="风险指标")

class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    channel: str = Field(..., description="频道")
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
