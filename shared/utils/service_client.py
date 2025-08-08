"""
微服务客户端工具
提供服务间通信的标准化接口
"""

import requests
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from shared.models.base import APIResponse, ServiceInfo, HealthCheckResponse
from utils.logger import get_logger

logger = get_logger(__name__)

class ServiceClient:
    """微服务客户端"""

    def __init__(self, service_name: str, base_url: str, timeout: float = 30.0):
        """
        初始化服务客户端

        Args:
            service_name: 服务名称
            base_url: 服务基础URL
            timeout: 请求超时时间
        """
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session = requests.Session()
        self._session.timeout = timeout

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._session:
            self._session.close()
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> APIResponse:
        """发送GET请求"""
        return await self._request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any] = None) -> APIResponse:
        """发送POST请求"""
        return await self._request("POST", endpoint, json=data)
    
    async def put(self, endpoint: str, data: Dict[str, Any] = None) -> APIResponse:
        """发送PUT请求"""
        return await self._request("PUT", endpoint, json=data)
    
    async def delete(self, endpoint: str) -> APIResponse:
        """发送DELETE请求"""
        return await self._request("DELETE", endpoint)
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        request_id = str(uuid.uuid4())
        
        try:
            logger.debug(f"发送{method}请求到{self.service_name}: {url}")

            # 在线程池中运行同步请求，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._session.request(method, url, **kwargs)
            )
            response.raise_for_status()
            
            # 尝试解析JSON响应
            try:
                data = response.json()
                if isinstance(data, dict) and "success" in data:
                    return APIResponse(**data)
                else:
                    # 如果不是标准APIResponse格式，包装一下
                    return APIResponse(
                        success=True,
                        message="请求成功",
                        data=data if isinstance(data, dict) else {"response": data},
                        request_id=request_id
                    )
            except Exception:
                # 如果不是JSON响应，返回文本内容
                return APIResponse(
                    success=True,
                    message="请求成功",
                    data={"response": response.text},
                    request_id=request_id
                )
                
        except requests.exceptions.Timeout:
            logger.error(f"请求{self.service_name}超时: {url}")
            return APIResponse(
                success=False,
                message=f"请求{self.service_name}服务超时",
                data={"error": "timeout", "url": url},
                request_id=request_id
            )
        except requests.exceptions.HTTPError as e:
            logger.error(f"请求{self.service_name}失败: {e.response.status_code} - {url}")
            return APIResponse(
                success=False,
                message=f"请求{self.service_name}服务失败: {e.response.status_code}",
                data={"error": "http_error", "status_code": e.response.status_code, "url": url},
                request_id=request_id
            )
        except Exception as e:
            logger.error(f"请求{self.service_name}异常: {e}")
            return APIResponse(
                success=False,
                message=f"请求{self.service_name}服务异常: {str(e)}",
                data={"error": "exception", "details": str(e)},
                request_id=request_id
            )
    
    async def health_check(self) -> HealthCheckResponse:
        """健康检查"""
        try:
            response = await self.get("/health")
            if response.success:
                return HealthCheckResponse(**response.data)
            else:
                return HealthCheckResponse(
                    status="unhealthy",
                    timestamp=datetime.now(),
                    version="unknown"
                )
        except Exception as e:
            logger.error(f"健康检查失败 {self.service_name}: {e}")
            return HealthCheckResponse(
                status="unhealthy",
                timestamp=datetime.now(),
                version="unknown"
            )

class ServiceRegistry:
    """服务注册中心"""
    
    def __init__(self):
        """初始化服务注册中心"""
        self.services: Dict[str, ServiceInfo] = {}
        self.clients: Dict[str, ServiceClient] = {}
        
    def register_service(self, service_info: ServiceInfo):
        """注册服务"""
        self.services[service_info.name] = service_info
        
        # 创建服务客户端
        base_url = f"http://{service_info.host}:{service_info.port}"
        self.clients[service_info.name] = ServiceClient(
            service_info.name, 
            base_url
        )
        
        logger.info(f"服务已注册: {service_info.name} -> {base_url}")
    
    def unregister_service(self, service_name: str):
        """注销服务"""
        if service_name in self.services:
            del self.services[service_name]
        if service_name in self.clients:
            del self.clients[service_name]
        logger.info(f"服务已注销: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        return self.services.get(service_name)
    
    def get_client(self, service_name: str) -> Optional[ServiceClient]:
        """获取服务客户端"""
        return self.clients.get(service_name)
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """获取服务URL"""
        service = self.get_service(service_name)
        if service:
            return f"http://{service.host}:{service.port}"
        return None
    
    def list_services(self) -> List[ServiceInfo]:
        """列出所有服务"""
        return list(self.services.values())
    
    async def health_check_all(self) -> Dict[str, HealthCheckResponse]:
        """检查所有服务健康状态"""
        results = {}
        
        for service_name, client in self.clients.items():
            try:
                async with client:
                    health = await client.health_check()
                    results[service_name] = health
            except Exception as e:
                logger.error(f"健康检查失败 {service_name}: {e}")
                results[service_name] = HealthCheckResponse(
                    status="error",
                    timestamp=datetime.now(),
                    version="unknown"
                )
        
        return results

# 全局服务注册中心实例
service_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册中心"""
    return service_registry

async def call_service(service_name: str, method: str, endpoint: str, 
                      data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> APIResponse:
    """
    调用微服务的便捷函数
    
    Args:
        service_name: 服务名称
        method: HTTP方法
        endpoint: API端点
        data: 请求数据
        params: 查询参数
        
    Returns:
        API响应
    """
    client = service_registry.get_client(service_name)
    if not client:
        return APIResponse(
            success=False,
            message=f"服务{service_name}未注册",
            data={"error": "service_not_found"}
        )
    
    try:
        async with client:
            if method.upper() == "GET":
                return await client.get(endpoint, params=params)
            elif method.upper() == "POST":
                return await client.post(endpoint, data=data)
            elif method.upper() == "PUT":
                return await client.put(endpoint, data=data)
            elif method.upper() == "DELETE":
                return await client.delete(endpoint)
            else:
                return APIResponse(
                    success=False,
                    message=f"不支持的HTTP方法: {method}",
                    data={"error": "unsupported_method"}
                )
    except Exception as e:
        logger.error(f"调用服务{service_name}异常: {e}")
        return APIResponse(
            success=False,
            message=f"调用服务异常: {str(e)}",
            data={"error": "call_exception", "details": str(e)}
        )
