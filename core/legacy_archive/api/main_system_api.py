"""
主系统内部API服务
提供主系统状态查询和控制接口
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import uuid
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# 全局服务容器引用
_service_container = None

def set_service_container(container):
    """设置服务容器引用"""
    global _service_container
    _service_container = container

def get_service_container():
    """获取服务容器引用"""
    return _service_container

# 创建FastAPI应用
app = FastAPI(
    title="ARBIG主系统API",
    description="ARBIG主系统内部API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        container = get_service_container()
        if not container:
            return {
                "success": True,
                "message": "系统状态获取成功",
                "data": {
                    "system_status": "stopped",
                    "running_mode": "UNKNOWN",
                    "start_time": datetime.now().isoformat(),
                    "uptime": "0h 0m",
                    "ctp_status": {
                        "market_data": {
                            "connected": False,
                            "server": "182.254.243.31:30011",
                            "latency": "N/A",
                            "last_connect_time": datetime.now().isoformat(),
                            "error_message": None
                        },
                        "trading": {
                            "connected": False,
                            "server": "182.254.243.31:30001",
                            "latency": "N/A",
                            "last_connect_time": datetime.now().isoformat(),
                            "error_message": None
                        }
                    },
                    "services_summary": {
                        "total": 5,
                        "running": 0,
                        "stopped": 5,
                        "error": 0
                    },
                    "version": "1.0.0"
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        
        # 获取真实的系统状态
        status_data = container.get_system_status()
        
        return {
            "success": True,
            "message": "系统状态获取成功",
            "data": status_data,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统状态失败: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "message": "主系统API运行正常",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        "request_id": str(uuid.uuid4())
    }

@app.post("/api/v1/system/start")
async def start_system():
    """启动系统"""
    try:
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        result = container.start_system()
        
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data or {},
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        logger.error(f"启动系统失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"启动系统失败: {str(e)}"
        )

@app.post("/api/v1/system/stop")
async def stop_system():
    """停止系统"""
    try:
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        result = container.stop_system()
        
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data or {},
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        logger.error(f"停止系统失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"停止系统失败: {str(e)}"
        )

@app.get("/api/v1/data/market/ticks")
async def get_market_ticks(symbols: str = Query(..., description="合约代码，多个用逗号分隔")):
    """获取实时行情数据"""
    try:
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")

        # 获取行情服务
        market_service = container.services.get('MarketDataService')
        if not market_service:
            raise HTTPException(status_code=500, detail="行情服务未启动")

        symbol_list = symbols.split(",")
        ticks_data = []

        for symbol in symbol_list:
            symbol = symbol.strip()
            tick = market_service.get_latest_tick(symbol)
            if tick:
                tick_data = {
                    "symbol": tick.symbol,
                    "last_price": tick.last_price,
                    "volume": tick.volume,
                    "turnover": getattr(tick, 'turnover', 0),
                    "open_interest": getattr(tick, 'open_interest', 0),
                    "time": tick.time.isoformat() if tick.time else datetime.now().isoformat(),
                    "bid_price_1": getattr(tick, 'bid_price_1', 0),
                    "ask_price_1": getattr(tick, 'ask_price_1', 0),
                    "bid_volume_1": getattr(tick, 'bid_volume_1', 0),
                    "ask_volume_1": getattr(tick, 'ask_volume_1', 0)
                }
                ticks_data.append(tick_data)
            else:
                # 如果没有数据，返回空的tick数据
                ticks_data.append({
                    "symbol": symbol,
                    "last_price": 0,
                    "volume": 0,
                    "turnover": 0,
                    "open_interest": 0,
                    "time": datetime.now().isoformat(),
                    "bid_price_1": 0,
                    "ask_price_1": 0,
                    "bid_volume_1": 0,
                    "ask_volume_1": 0,
                    "error": "无数据"
                })

        return {
            "success": True,
            "message": "行情数据获取成功",
            "data": {"ticks": ticks_data},
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取行情数据失败: {str(e)}"
        )

@app.get("/api/v1/data/market/price/{symbol}")
async def get_market_price(symbol: str):
    """获取合约最新价格"""
    try:
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")

        # 获取行情服务
        market_service = container.services.get('MarketDataService')
        if not market_service:
            raise HTTPException(status_code=500, detail="行情服务未启动")

        price = market_service.get_latest_price(symbol)

        return {
            "success": True,
            "message": "价格获取成功",
            "data": {
                "symbol": symbol,
                "price": price,
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取价格失败: {str(e)}"
        )

@app.post("/api/v1/data/market/subscribe")
async def subscribe_market_data(request: dict):
    """订阅行情数据"""
    try:
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")

        # 获取行情服务
        market_service = container.services.get('MarketDataService')
        if not market_service:
            raise HTTPException(status_code=500, detail="行情服务未启动")

        symbol = request.get('symbol')
        subscriber_id = request.get('subscriber_id', 'api_client')

        if not symbol:
            raise HTTPException(status_code=400, detail="缺少symbol参数")

        # 订阅合约
        success = market_service.subscribe_symbol(symbol, subscriber_id)

        return {
            "success": success,
            "message": f"订阅合约 {symbol} {'成功' if success else '失败'}",
            "data": {"symbol": symbol, "subscriber_id": subscriber_id},
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }

    except Exception as e:
        logger.error(f"订阅行情失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"订阅行情失败: {str(e)}"
        )

def start_main_system_api(host: str = "127.0.0.1", port: int = 8000, container=None):
    """启动主系统API服务"""
    if container:
        set_service_container(container)
    
    logger.info(f"启动主系统API服务: {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    start_main_system_api()
