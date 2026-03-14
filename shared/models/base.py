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

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    uptime: str = Field("", description="运行时长")
    version: str = Field("", description="服务版本")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="依赖服务状态")
