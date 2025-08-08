"""
行情数据API接口
提供行情数据查询和管理功能
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.trading_service.core.market_data_manager import get_market_data_manager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/market", tags=["market_data"])

@router.get("/current/{symbol}")
async def get_current_market_data(symbol: str):
    """获取指定合约的当前行情数据"""
    try:
        market_manager = get_market_data_manager()
        tick_data = market_manager.get_latest_tick(symbol)

        if not tick_data:
            raise HTTPException(status_code=404, detail=f"合约 {symbol} 行情数据不存在，请检查CTP连接状态")

        return {
            "symbol": symbol,
            "tick_data": tick_data,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行情数据失败: {str(e)}")

@router.get("/price/{symbol}")
async def get_current_price(symbol: str):
    """获取指定合约的当前价格"""
    try:
        market_manager = get_market_data_manager()
        price = market_manager.get_latest_price(symbol)

        if price is None:
            raise HTTPException(status_code=404, detail=f"合约 {symbol} 价格数据不存在，请检查CTP连接状态")

        return {
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取价格数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取价格数据失败: {str(e)}")

@router.get("/symbols")
async def get_subscribed_symbols():
    """获取已订阅的合约列表"""
    try:
        market_manager = get_market_data_manager()
        symbols = market_manager.get_subscribed_symbols()
        
        return {
            "symbols": symbols,
            "count": len(symbols),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取订阅合约列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订阅合约列表失败: {str(e)}")

@router.post("/subscribe/{symbol}")
async def subscribe_symbol(symbol: str):
    """订阅合约行情"""
    try:
        market_manager = get_market_data_manager()
        
        # 简单的订阅回调函数
        def on_tick(symbol: str, tick_data: Dict[str, Any]):
            logger.debug(f"收到行情更新: {symbol} @ {tick_data.get('last_price')}")
        
        market_manager.subscribe(symbol, on_tick)
        
        return {
            "success": True,
            "message": f"成功订阅合约 {symbol}",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"订阅合约失败: {e}")
        raise HTTPException(status_code=500, detail=f"订阅合约失败: {str(e)}")

@router.delete("/unsubscribe/{symbol}")
async def unsubscribe_symbol(symbol: str):
    """取消订阅合约行情"""
    try:
        market_manager = get_market_data_manager()
        
        # 这里需要找到对应的回调函数来取消订阅
        # 简化处理：清空该合约的所有订阅
        if symbol in market_manager.subscribers:
            market_manager.subscribers[symbol].clear()
            if symbol in market_manager.tick_cache:
                del market_manager.tick_cache[symbol]
        
        return {
            "success": True,
            "message": f"成功取消订阅合约 {symbol}",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"取消订阅合约失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消订阅合约失败: {str(e)}")

@router.post("/mock/{symbol}")
async def generate_mock_data(symbol: str):
    """为指定合约生成模拟行情数据"""
    try:
        market_manager = get_market_data_manager()
        tick_data = await market_manager.generate_mock_data(symbol)
        
        if not tick_data:
            raise HTTPException(status_code=500, detail="生成模拟数据失败")
        
        return {
            "success": True,
            "message": f"成功生成合约 {symbol} 的模拟数据",
            "tick_data": tick_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成模拟数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成模拟数据失败: {str(e)}")

@router.get("/statistics")
async def get_market_statistics():
    """获取行情服务统计信息"""
    try:
        market_manager = get_market_data_manager()
        stats = market_manager.get_statistics()
        
        return {
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.post("/start_mock_feed")
async def start_mock_feed():
    """启动模拟行情推送"""
    try:
        import asyncio
        
        market_manager = get_market_data_manager()
        
        # 为主要合约启动模拟数据生成
        symbols = ["au2509", "au2512", "au2601"]
        
        # 模拟行情推送已禁用，使用真实CTP数据
        logger.info("模拟行情推送请求被忽略，系统使用真实CTP数据")
        
        return {
            "success": True,
            "message": "模拟行情推送已禁用，系统使用真实CTP数据",
            "status": "disabled",
            "recommendation": "请确保CTP连接正常以获取真实行情数据",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动模拟行情推送失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动模拟行情推送失败: {str(e)}")

@router.get("/health")
async def market_health_check():
    """行情服务健康检查"""
    try:
        market_manager = get_market_data_manager()
        stats = market_manager.get_statistics()
        
        return {
            "status": "healthy" if stats["running"] else "stopped",
            "running": stats["running"],
            "subscribed_symbols": stats["subscribed_symbols"],
            "cached_ticks": stats["cached_ticks"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"行情服务健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
