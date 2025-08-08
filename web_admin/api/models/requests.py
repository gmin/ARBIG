"""
API请求数据模型
定义所有API请求的数据结构
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class ServiceAction(str, Enum):
    """服务操作类型"""
    START = "start"
    STOP = "stop"
    RESTART = "restart"

class SystemMode(str, Enum):
    """系统运行模式"""
    FULL_TRADING = "FULL_TRADING"
    MONITOR_ONLY = "MONITOR_ONLY"
    MARKET_DATA_ONLY = "MARKET_DATA_ONLY"

class ServiceControlRequest(BaseModel):
    """服务控制请求"""
    service_name: str = Field(..., description="服务名称")
    action: ServiceAction = Field(..., description="操作类型")
    force: bool = Field(False, description="是否强制执行")
    config: Optional[Dict[str, Any]] = Field(None, description="服务配置")

class ServiceConfigRequest(BaseModel):
    """服务配置请求"""
    config: Dict[str, Any] = Field(..., description="服务配置参数")

class StrategyControlRequest(BaseModel):
    """策略控制请求"""
    strategy_name: str = Field(..., description="策略名称")
    action: str = Field(..., description="操作类型: switch/pause/resume/stop")
    config: Optional[Dict[str, Any]] = Field(None, description="策略配置")
    
class StrategySwitchRequest(BaseModel):
    """策略切换请求"""
    from_strategy: Optional[str] = Field(None, description="当前策略")
    to_strategy: str = Field(..., description="目标策略")
    config: Optional[Dict[str, Any]] = Field(None, description="新策略配置")
    switch_mode: str = Field("safe", description="切换模式: safe/force")
    reason: Optional[str] = Field(None, description="切换原因")

class SystemModeRequest(BaseModel):
    """系统模式切换请求"""
    mode: SystemMode = Field(..., description="目标运行模式")
    reason: Optional[str] = Field(None, description="切换原因")
    operator: Optional[str] = Field(None, description="操作员")

class EmergencyRequest(BaseModel):
    """紧急操作请求"""
    action: str = Field(..., description="紧急操作类型: stop/close")
    reason: str = Field(..., description="操作原因")
    operator: str = Field(..., description="操作员")
    confirmation_code: Optional[str] = Field(None, description="确认码")

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    service_name: str = Field(..., description="服务名称")
    config: Dict[str, Any] = Field(..., description="配置参数")
    restart_service: bool = Field(False, description="是否重启服务")

class MarketDataRequest(BaseModel):
    """行情数据请求"""
    symbols: List[str] = Field(..., description="合约代码列表")
    data_type: str = Field("tick", description="数据类型: tick/kline")
    interval: Optional[str] = Field(None, description="K线周期")
    limit: int = Field(100, description="数据条数限制")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")

class RiskControlRequest(BaseModel):
    """风控操作请求"""
    action: str = Field(..., description="风控操作: update_limits/emergency_stop")
    params: Dict[str, Any] = Field(..., description="操作参数")
    operator: str = Field(..., description="操作员")
    reason: Optional[str] = Field(None, description="操作原因")

class WebSocketSubscribeRequest(BaseModel):
    """WebSocket订阅请求"""
    channel: str = Field(..., description="订阅频道")
    action: str = Field("subscribe", description="操作类型: subscribe/unsubscribe")
    params: Optional[Dict[str, Any]] = Field(None, description="订阅参数")

class OrderRequest(BaseModel):
    """订单请求"""
    symbol: str = Field(..., description="合约代码")
    direction: str = Field(..., description="方向: long/short")
    order_type: str = Field(..., description="订单类型: market/limit")
    volume: float = Field(..., description="数量")
    price: Optional[float] = Field(None, description="价格")
    strategy: Optional[str] = Field(None, description="策略名称")
    reference: Optional[str] = Field(None, description="订单引用")

class PositionRequest(BaseModel):
    """持仓操作请求"""
    symbol: str = Field(..., description="合约代码")
    action: str = Field(..., description="操作类型: close/adjust")
    volume: Optional[float] = Field(None, description="操作数量")
    price: Optional[float] = Field(None, description="操作价格")

class AnalysisRequest(BaseModel):
    """数据分析请求"""
    analysis_type: str = Field(..., description="分析类型: performance/risk/backtest")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    symbols: Optional[List[str]] = Field(None, description="合约列表")
    strategy: Optional[str] = Field(None, description="策略名称")
    params: Optional[Dict[str, Any]] = Field(None, description="分析参数")


