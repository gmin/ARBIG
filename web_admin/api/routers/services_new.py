"""
服务管理API路由 - 重构版本
提供服务级别的控制和状态查询接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import uuid
from datetime import datetime

from ..models.requests import ServiceConfigRequest
from ..models.responses import APIResponse, ServiceStatusResponse, ServiceInfo
from ..dependencies import get_system_connector_dep
from ..system_connector import SystemConnector

router = APIRouter(prefix="/api/v1/services", tags=["服务管理"])

@router.get("/", response_model=Dict[str, Any], summary="获取所有服务状态")
async def get_all_services_status(connector: SystemConnector = Depends(get_system_connector_dep)):
    """
    获取所有服务的状态信息
    
    返回:
    - 服务列表
    - 服务统计
    - 依赖关系
    """
    try:
        result = await connector.get_all_services_status()
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": result["data"],
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取服务状态异常: {str(e)}",
            "data": {},
            "request_id": str(uuid.uuid4())
        }

@router.get("/{service_name}", response_model=Dict[str, Any], summary="获取指定服务状态")
async def get_service_status(
    service_name: str,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    获取指定服务的详细状态信息
    
    Args:
        service_name: 服务名称
        
    返回:
    - 服务状态
    - 启动时间
    - 运行时长
    - 依赖关系
    """
    try:
        result = await connector.get_service_status(service_name)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": result["data"],
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取服务{service_name}状态异常: {str(e)}",
            "data": {},
            "request_id": str(uuid.uuid4())
        }

@router.post("/{service_name}/start", response_model=APIResponse, summary="启动服务")
async def start_service(
    service_name: str,
    config: ServiceConfigRequest = None,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    启动指定的服务
    
    Args:
        service_name: 服务名称
        config: 服务配置（可选）
        
    支持的服务:
    - MarketDataService: 行情服务
    - AccountService: 账户服务
    - RiskService: 风控服务
    - TradingService: 交易服务
    - StrategyService: 策略服务
    """
    try:
        service_config = config.config if config else None
        result = await connector.start_service(service_name, service_config)
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data=result["data"],
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"启动服务{service_name}异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/{service_name}/stop", response_model=APIResponse, summary="停止服务")
async def stop_service(
    service_name: str,
    force: bool = False,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    停止指定的服务
    
    Args:
        service_name: 服务名称
        force: 是否强制停止（忽略依赖关系）
    """
    try:
        result = await connector.stop_service(service_name, force)
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data=result["data"],
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"停止服务{service_name}异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/{service_name}/restart", response_model=APIResponse, summary="重启服务")
async def restart_service(
    service_name: str,
    config: ServiceConfigRequest = None,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    重启指定的服务
    
    Args:
        service_name: 服务名称
        config: 新的服务配置（可选）
    """
    try:
        # 先停止服务
        stop_result = await connector.stop_service(service_name, force=True)
        if not stop_result["success"]:
            return APIResponse(
                success=False,
                message=f"重启失败：停止服务{service_name}失败 - {stop_result['message']}",
                data={},
                request_id=str(uuid.uuid4())
            )
        
        # 再启动服务
        service_config = config.config if config else None
        start_result = await connector.start_service(service_name, service_config)
        
        return APIResponse(
            success=start_result["success"],
            message=f"服务{service_name}重启{'成功' if start_result['success'] else '失败'}: {start_result['message']}",
            data=start_result["data"],
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"重启服务{service_name}异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.get("/dependencies/graph", response_model=Dict[str, Any], summary="获取服务依赖图")
async def get_service_dependencies():
    """
    获取服务依赖关系图
    
    返回:
    - 服务依赖关系
    - 启动顺序建议
    - 停止顺序建议
    """
    try:
        # 硬编码的服务依赖关系
        dependencies = {
            'MarketDataService': ['ctp_gateway'],
            'AccountService': ['ctp_gateway'],
            'RiskService': ['AccountService'],
            'TradingService': ['ctp_gateway', 'MarketDataService', 'AccountService', 'RiskService'],
            'StrategyService': ['MarketDataService', 'AccountService', 'TradingService']
        }
        
        # 建议的启动顺序
        start_order = [
            'MarketDataService',
            'AccountService', 
            'RiskService',
            'TradingService',
            'StrategyService'
        ]
        
        # 建议的停止顺序（相反）
        stop_order = list(reversed(start_order))
        
        return {
            "success": True,
            "message": "服务依赖图获取成功",
            "data": {
                "dependencies": dependencies,
                "start_order": start_order,
                "stop_order": stop_order
            },
            "request_id": str(uuid.uuid4())
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取服务依赖图异常: {str(e)}",
            "data": {},
            "request_id": str(uuid.uuid4())
        }

@router.post("/batch/start", response_model=APIResponse, summary="批量启动服务")
async def batch_start_services(
    service_names: List[str],
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    按依赖顺序批量启动服务
    
    Args:
        service_names: 要启动的服务名称列表
    """
    try:
        results = []
        
        # 按依赖顺序启动
        start_order = [
            'MarketDataService',
            'AccountService', 
            'RiskService',
            'TradingService',
            'StrategyService'
        ]
        
        for service_name in start_order:
            if service_name in service_names:
                result = await connector.start_service(service_name)
                results.append({
                    "service": service_name,
                    "success": result["success"],
                    "message": result["message"]
                })
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        return APIResponse(
            success=success_count == total_count,
            message=f"批量启动完成：{success_count}/{total_count} 个服务启动成功",
            data={"results": results},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"批量启动服务异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/batch/stop", response_model=APIResponse, summary="批量停止服务")
async def batch_stop_services(
    service_names: List[str],
    force: bool = False,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    按依赖顺序批量停止服务
    
    Args:
        service_names: 要停止的服务名称列表
        force: 是否强制停止
    """
    try:
        results = []
        
        # 按相反依赖顺序停止
        stop_order = [
            'StrategyService',
            'TradingService',
            'RiskService',
            'AccountService',
            'MarketDataService'
        ]
        
        for service_name in stop_order:
            if service_name in service_names:
                result = await connector.stop_service(service_name, force)
                results.append({
                    "service": service_name,
                    "success": result["success"],
                    "message": result["message"]
                })
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        return APIResponse(
            success=success_count == total_count,
            message=f"批量停止完成：{success_count}/{total_count} 个服务停止成功",
            data={"results": results},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"批量停止服务异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )
