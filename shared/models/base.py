"""
共享数据模型
定义微服务间通信的标准数据结构
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ServiceStatus(str, Enum):
    """服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class SystemStatus(str, Enum):
    """系统状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class RunningMode(str, Enum):
    """运行模式"""
    FULL_TRADING = "FULL_TRADING"
    MONITOR_ONLY = "MONITOR_ONLY"
    MARKET_DATA_ONLY = "MARKET_DATA_ONLY"

class ServiceInfo(BaseModel):
    """服务信息"""
    name: str = Field(..., description="服务名称")
    display_name: str = Field(..., description="显示名称")
    status: ServiceStatus = Field(..., description="服务状态")
    host: str = Field(..., description="服务主机")
    port: int = Field(..., description="服务端口")
    start_time: Optional[datetime] = Field(None, description="启动时间")
    uptime: str = Field("", description="运行时长")
    version: str = Field("1.0.0", description="服务版本")
    health_check_url: str = Field("", description="健康检查URL")

class SystemInfo(BaseModel):
    """系统信息"""
    system_status: SystemStatus = Field(..., description="系统状态")
    running_mode: RunningMode = Field(..., description="运行模式")
    start_time: Optional[datetime] = Field(None, description="启动时间")
    uptime: str = Field("", description="运行时长")
    version: str = Field("2.0.0", description="系统版本")
    services: List[ServiceInfo] = Field(default_factory=list, description="服务列表")

class APIResponse(BaseModel):
    """标准API响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Dict[str, Any] = Field(default_factory=dict, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: str = Field("", description="请求ID")

class ServiceRequest(BaseModel):
    """服务请求"""
    action: str = Field(..., description="操作类型")
    params: Dict[str, Any] = Field(default_factory=dict, description="请求参数")
    request_id: str = Field("", description="请求ID")

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    uptime: str = Field("", description="运行时长")
    version: str = Field("", description="服务版本")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="依赖服务状态")

# 交易相关模型
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

class OrderInfo(BaseModel):
    """订单信息"""
    order_id: str = Field(..., description="订单ID")
    symbol: str = Field(..., description="合约代码")
    side: OrderSide = Field(..., description="订单方向")
    order_type: OrderType = Field(..., description="订单类型")
    quantity: float = Field(..., description="订单数量")
    price: Optional[float] = Field(None, description="订单价格")
    status: OrderStatus = Field(..., description="订单状态")
    filled_quantity: float = Field(0.0, description="已成交数量")
    avg_price: Optional[float] = Field(None, description="平均成交价格")
    create_time: datetime = Field(default_factory=datetime.now, description="创建时间")
    update_time: datetime = Field(default_factory=datetime.now, description="更新时间")

class PositionInfo(BaseModel):
    """持仓信息"""
    symbol: str = Field(..., description="合约代码")
    side: OrderSide = Field(..., description="持仓方向")
    quantity: float = Field(..., description="持仓数量")
    avg_price: float = Field(..., description="平均成本价")
    current_price: float = Field(..., description="当前价格")
    unrealized_pnl: float = Field(..., description="未实现盈亏")
    realized_pnl: float = Field(..., description="已实现盈亏")

class AccountInfo(BaseModel):
    """账户信息"""
    account_id: str = Field(..., description="账户ID")
    balance: float = Field(..., description="账户余额")
    available: float = Field(..., description="可用资金")
    margin: float = Field(..., description="保证金占用")
    unrealized_pnl: float = Field(..., description="未实现盈亏")
    realized_pnl: float = Field(..., description="已实现盈亏")
    positions: List[PositionInfo] = Field(default_factory=list, description="持仓列表")

class TickData(BaseModel):
    """Tick数据"""
    symbol: str = Field(..., description="合约代码")
    timestamp: datetime = Field(..., description="时间戳")
    last_price: float = Field(..., description="最新价")
    volume: int = Field(..., description="成交量")
    bid_price: float = Field(..., description="买一价")
    ask_price: float = Field(..., description="卖一价")
    bid_volume: int = Field(..., description="买一量")
    ask_volume: int = Field(..., description="卖一量")

class BarData(BaseModel):
    """K线数据"""
    symbol: str = Field(..., description="合约代码")
    timestamp: datetime = Field(..., description="时间戳")
    interval: str = Field(..., description="时间间隔")
    open_price: float = Field(..., description="开盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    close_price: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")

# 服务发现相关
class ServiceRegistry(BaseModel):
    """服务注册信息"""
    services: Dict[str, ServiceInfo] = Field(default_factory=dict, description="服务列表")
    last_update: datetime = Field(default_factory=datetime.now, description="最后更新时间")

    def register_service(self, service_info: ServiceInfo):
        """注册服务"""
        self.services[service_info.name] = service_info
        self.last_update = datetime.now()

    def unregister_service(self, service_name: str):
        """注销服务"""
        if service_name in self.services:
            del self.services[service_name]
            self.last_update = datetime.now()

    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        return self.services.get(service_name)

    def get_service_url(self, service_name: str) -> Optional[str]:
        """获取服务URL"""
        service = self.get_service(service_name)
        if service:
            return f"http://{service.host}:{service.port}"
        return None
