"""
服务管理API路由
提供各个服务的启停控制和状态查询接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import uuid
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from ..models.requests import ServiceControlRequest, ConfigUpdateRequest
from ..models.responses import (
    APIResponse, ServiceStatusResponse, ServiceListResponse,
    ServiceInfo, ServiceStatus, ErrorResponse
)
from ..dependencies import get_service_manager

# 导入主系统服务容器
from main import get_service_container

router = APIRouter(prefix="/api/v1/services", tags=["服务管理"])

@router.get("/list", response_model=ServiceListResponse, summary="获取服务列表")
async def get_services_list(service_manager=Depends(get_service_manager)):
    """
    获取所有可用服务的列表和状态
    
    返回:
    - 服务基本信息
    - 运行状态
    - 依赖关系
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 获取所有服务状态
        services_status = container.get_all_services_status()
        
        # 转换为API响应格式
        services = []
        for service_info in services_status:
            service = ServiceInfo(
                name=service_info['name'],
                display_name=service_info.get('display_name', service_info['name']),
                status=ServiceStatus(service_info['status']),
                start_time=service_info.get('start_time'),
                uptime=service_info.get('uptime', '0s'),
                cpu_usage=service_info.get('cpu_usage', '0%'),
                memory_usage=service_info.get('memory_usage', '0MB'),
                last_heartbeat=service_info.get('last_heartbeat'),
                required=service_info.get('required', False),
                dependencies=service_info.get('dependencies', [])
            )
            services.append(service)
        
        return ServiceListResponse(
            success=True,
            message="服务列表获取成功",
            data={"services": services},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取服务列表失败: {str(e)}"
        )

@router.get("/status", response_model=ServiceStatusResponse, summary="获取服务状态")
async def get_service_status(
    service_name: str,
    service_manager=Depends(get_service_manager)
):
    """
    获取指定服务的详细状态
    
    Args:
        service_name: 服务名称
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 获取服务状态
        service_status = container.get_service_status(service_name)
        if not service_status:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
        
        return ServiceStatusResponse(
            success=True,
            message="服务状态获取成功",
            data=service_status,
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取服务状态失败: {str(e)}"
        )

@router.post("/start", response_model=APIResponse, summary="启动服务")
async def start_service(
    request: ServiceControlRequest,
    service_manager=Depends(get_service_manager)
):
    """
    启动指定服务
    
    Args:
        request: 服务控制请求
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 启动服务
        result = container.start_service(request.service_name, request.config)
        
        if result.success:
            return APIResponse(
                success=True,
                message=f"服务 {request.service_name} 启动成功",
                data={"service_name": request.service_name, "status": "starting"},
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"启动服务失败: {result.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"启动服务失败: {str(e)}"
        )

@router.post("/stop", response_model=APIResponse, summary="停止服务")
async def stop_service(
    request: ServiceControlRequest,
    service_manager=Depends(get_service_manager)
):
    """
    停止指定服务
    
    Args:
        request: 服务控制请求
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 停止服务
        result = container.stop_service(request.service_name, request.force)
        
        if result.success:
            return APIResponse(
                success=True,
                message=f"服务 {request.service_name} 停止成功",
                data={"service_name": request.service_name, "status": "stopping"},
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"停止服务失败: {result.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"停止服务失败: {str(e)}"
        )

@router.post("/restart", response_model=APIResponse, summary="重启服务")
async def restart_service(
    request: ServiceControlRequest,
    service_manager=Depends(get_service_manager)
):
    """
    重启指定服务
    
    Args:
        request: 服务控制请求
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 重启服务
        result = container.restart_service(request.service_name, request.config)
        
        if result.success:
            return APIResponse(
                success=True,
                message=f"服务 {request.service_name} 重启成功",
                data={"service_name": request.service_name, "status": "restarting"},
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"重启服务失败: {result.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重启服务失败: {str(e)}"
        )

@router.get("/{service_name}/config", response_model=APIResponse, summary="获取服务配置")
async def get_service_config(
    service_name: str,
    service_manager=Depends(get_service_manager)
):
    """
    获取指定服务的配置
    
    Args:
        service_name: 服务名称
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 获取服务状态（包含配置信息）
        service_status = container.get_service_status(service_name)
        if not service_status:
            raise HTTPException(status_code=404, detail=f"服务 {service_name} 不存在")
        
        config = service_status.get('config', {})
        
        return APIResponse(
            success=True,
            message="服务配置获取成功",
            data={"service_name": service_name, "config": config},
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取服务配置失败: {str(e)}"
        )

@router.post("/{service_name}/config", response_model=APIResponse, summary="更新服务配置")
async def update_service_config(
    service_name: str,
    request: ConfigUpdateRequest,
    service_manager=Depends(get_service_manager)
):
    """
    更新指定服务的配置
    
    Args:
        service_name: 服务名称
        request: 配置更新请求
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 这里需要实现配置更新逻辑
        # 暂时返回成功响应
        return APIResponse(
            success=True,
            message=f"服务 {service_name} 配置更新成功",
            data={"service_name": service_name, "config": request.config},
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新服务配置失败: {str(e)}"
        )

@router.get("/{service_name}/logs", response_model=APIResponse, summary="获取服务日志")
async def get_service_logs(
    service_name: str,
    lines: int = 100,
    level: str = "INFO",
    service_manager=Depends(get_service_manager)
):
    """
    获取指定服务的日志
    
    Args:
        service_name: 服务名称
        lines: 日志行数
        level: 日志级别
    """
    try:
        # 这里需要实现日志获取逻辑
        # 暂时返回模拟数据
        logs = [
            f"[{datetime.now().isoformat()}] INFO - 服务 {service_name} 运行正常",
            f"[{datetime.now().isoformat()}] DEBUG - 处理请求: {service_name}",
        ]
        
        return APIResponse(
            success=True,
            message="服务日志获取成功",
            data={
                "service_name": service_name,
                "logs": logs,
                "lines": lines,
                "level": level
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取服务日志失败: {str(e)}"
        )

@router.get("/system/status", response_model=APIResponse, summary="获取系统整体状态")
async def get_system_status(service_manager=Depends(get_service_manager)):
    """
    获取系统整体状态
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 获取系统状态
        system_status = container.get_system_status()
        
        return APIResponse(
            success=True,
            message="系统状态获取成功",
            data=system_status,
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取系统状态失败: {str(e)}"
        )

@router.post("/system/start", response_model=APIResponse, summary="启动整个系统")
async def start_system(service_manager=Depends(get_service_manager)):
    """
    启动整个系统
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 启动系统
        result = container.start_system()
        
        if result.success:
            return APIResponse(
                success=True,
                message="系统启动成功",
                data={"status": "starting"},
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"系统启动失败: {result.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"系统启动失败: {str(e)}"
        )

@router.post("/system/stop", response_model=APIResponse, summary="停止整个系统")
async def stop_system(service_manager=Depends(get_service_manager)):
    """
    停止整个系统
    """
    try:
        # 获取主系统服务容器
        container = get_service_container()
        if not container:
            raise HTTPException(status_code=500, detail="服务容器未初始化")
        
        # 停止系统
        result = container.stop_system()
        
        if result.success:
            return APIResponse(
                success=True,
                message="系统停止成功",
                data={"status": "stopping"},
                request_id=str(uuid.uuid4())
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"系统停止失败: {result.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"系统停止失败: {str(e)}"
        )
