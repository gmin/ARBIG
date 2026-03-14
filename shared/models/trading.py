"""
交易相关数据模型
定义交易系统中使用的数据结构
"""

from pydantic import BaseModel, Field
from datetime import datetime


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


class MarketDataResponse(BaseModel):
    """行情数据响应模型"""
    symbol: str = Field(..., description="合约代码")
    tick_data: TickData = Field(..., description="Tick数据")
    is_connected: bool = Field(..., description="连接状态")
    last_update: datetime = Field(..., description="最后更新时间")
