"""
通信管理器 - 负责与主系统的通信
"""

import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MainSystemClient:
    """主系统客户端"""
    
    def __init__(self, base_urls: List[str] = None):
        self.base_urls = base_urls or [
            "http://localhost:8000",
            "http://localhost:8001", 
            "http://localhost:8002"
        ]
        self.timeout = 10.0
        self.stats = {
            "requests": 0,
            "success": 0,
            "errors": 0,
            "last_success": None,
            "last_error": None
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """发送请求到主系统"""
        self.stats["requests"] += 1
        
        for base_url in self.base_urls:
            try:
                url = f"{base_url}{endpoint}"
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data)
                    else:
                        raise ValueError(f"不支持的HTTP方法: {method}")
                    
                    if response.status_code == 200:
                        self.stats["success"] += 1
                        self.stats["last_success"] = datetime.now().isoformat()
                        return response.json()
                    else:
                        logger.warning(f"主系统返回错误状态码: {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"连接主系统失败 {base_url}: {e}")
                continue
        
        # 所有连接都失败
        self.stats["errors"] += 1
        self.stats["last_error"] = datetime.now().isoformat()
        return {"success": False, "message": "主系统不可用"}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return await self._make_request("GET", "/api/v1/system/status")
    
    async def send_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送订单"""
        return await self._make_request("POST", "/api/v1/data/orders/send", order_data)
    
    async def get_orders(self, active_only: bool = False) -> Dict[str, Any]:
        """获取订单列表"""
        params = f"?active_only={active_only}" if active_only else ""
        return await self._make_request("GET", f"/api/v1/data/orders{params}")
    
    async def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return await self._make_request("GET", "/api/v1/data/account/info")
    
    async def get_positions(self) -> Dict[str, Any]:
        """获取持仓信息"""
        return await self._make_request("GET", "/api/v1/data/account/positions")
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        return await self._make_request("GET", "/api/v1/data/risk/metrics")
    
    async def get_strategies(self) -> Dict[str, Any]:
        """获取策略列表"""
        return await self._make_request("GET", "/api/v1/strategies/list")
    
    async def get_market_ticks(self, symbols: str = "au2508") -> Dict[str, Any]:
        """获取市场行情"""
        return await self._make_request("GET", f"/api/v1/data/market/ticks?symbols={symbols}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计信息"""
        return self.stats.copy()

class CommunicationManager:
    """通信管理器"""

    def __init__(self):
        self.client = MainSystemClient()
        self._service_container = None

    def set_service_container(self, container):
        """设置服务容器引用"""
        self._service_container = container

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        # 优先使用直接的服务容器连接
        if self._service_container:
            try:
                logger.info("使用直接服务容器连接获取系统状态")
                status = self._service_container.get_system_status()
                return {
                    "success": True,
                    "message": "系统状态获取成功（直接连接）",
                    "data": status,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"从服务容器获取状态失败: {e}")
        else:
            logger.warning("服务容器未设置，回退到HTTP请求")

        # 回退到HTTP请求
        return await self.client.get_system_status()
    
    async def send_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送订单"""
        return await self.client.send_order(order_data)
    
    async def get_orders(self, active_only: bool = False) -> Dict[str, Any]:
        """获取订单列表"""
        return await self.client.get_orders(active_only)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return await self.client.get_account_info()
    
    async def get_positions(self) -> Dict[str, Any]:
        """获取持仓信息"""
        return await self.client.get_positions()
    
    async def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        return await self.client.get_risk_metrics()
    
    async def get_strategies(self) -> Dict[str, Any]:
        """获取策略列表"""
        return await self.client.get_strategies()
    
    async def get_market_ticks(self, symbols: str = "au2508") -> Dict[str, Any]:
        """获取市场行情"""
        return await self.client.get_market_ticks(symbols)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计信息"""
        return self.client.get_stats()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息（兼容性方法）"""
        stats = self.client.get_stats()
        return {
            "connection_status": "connected" if stats["success"] > 0 else "disconnected",
            "total_requests": stats["requests"],
            "successful_requests": stats["success"],
            "failed_requests": stats["errors"],
            "current_endpoint": self.client.base_urls[0] if self.client.base_urls else None,
            "total_endpoints": len(self.client.base_urls),
            "last_success": stats["last_success"],
            "last_error": stats["last_error"]
        }

# 全局通信管理器实例
_communication_manager = None

def get_communication_manager() -> CommunicationManager:
    """获取通信管理器实例"""
    global _communication_manager
    if _communication_manager is None:
        _communication_manager = CommunicationManager()
    return _communication_manager

def set_service_container_for_communication(container):
    """为通信管理器设置服务容器"""
    comm_manager = get_communication_manager()
    comm_manager.set_service_container(container)