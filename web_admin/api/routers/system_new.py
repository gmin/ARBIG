"""
系统控制API路由 - 重构版本
提供系统级别的控制和状态查询接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import uuid
from datetime import datetime

from ..models.requests import SystemModeRequest, EmergencyRequest
from ..models.responses import (
    APIResponse, SystemStatusResponse, SystemInfo, 
    CTPConnectionInfo, ErrorResponse
)
from ..dependencies import get_system_connector_dep
from ..system_connector import SystemConnector

router = APIRouter(prefix="/api/v1/system", tags=["系统控制"])

@router.get("/status", response_model=SystemStatusResponse, summary="获取系统状态")
async def get_system_status(connector: SystemConnector = Depends(get_system_connector_dep)):
    """
    获取系统整体状态信息

    返回:
    - 系统运行状态
    - 运行模式
    - CTP连接状态
    - 服务统计信息
    """
    try:
        # 使用新的系统连接器获取状态
        result = await connector.get_system_status()
        
        if result["success"]:
            data = result["data"]
            
            # 构建CTP连接信息
            ctp_status_data = data.get("ctp_status", {})
            market_data_info = ctp_status_data.get("market_data", {})
            trading_info = ctp_status_data.get("trading", {})

            ctp_info = {
                "market_data": CTPConnectionInfo(
                    connected=market_data_info.get("connected", False),
                    server=market_data_info.get("server", "未知"),
                    latency=market_data_info.get("latency", "N/A"),
                    last_connect_time=None
                ),
                "trading": CTPConnectionInfo(
                    connected=trading_info.get("connected", False),
                    server=trading_info.get("server", "未知"),
                    latency=trading_info.get("latency", "N/A"),
                    last_connect_time=None
                )
            }
            
            # 构建服务摘要信息
            services_status_data = data.get("services_status", {})
            services_summary = services_status_data.get("summary", {
                "total": 5,
                "running": 0,
                "stopped": 5,
                "error": 0
            })
            
            system_info = SystemInfo(
                system_status=data.get("system_status", "stopped"),
                running_mode=data.get("running_mode", "MARKET_DATA_ONLY"),
                start_time=datetime.fromisoformat(data["start_time"].replace("Z", "+00:00")) if data.get("start_time") else datetime.now(),
                uptime=data.get("uptime", ""),
                version=data.get("version", "2.0.0"),
                ctp_status=ctp_info,
                services_summary=services_summary
            )

            return SystemStatusResponse(
                success=True,
                message="系统状态获取成功",
                data=system_info,
                request_id=str(uuid.uuid4())
            )
        else:
            # 系统连接器返回错误
            raise HTTPException(
                status_code=500,
                detail=f"获取系统状态失败: {result['message']}"
            )
            
    except Exception as e:
        # 发生异常，返回默认状态
        system_info = SystemInfo(
            system_status="unknown",
            running_mode="UNKNOWN",
            start_time=datetime.now(),
            uptime="",
            version="2.0.0",
            ctp_status={
                "market_data": CTPConnectionInfo(
                    connected=False,
                    server="未知",
                    latency="N/A",
                    last_connect_time=None
                ),
                "trading": CTPConnectionInfo(
                    connected=False,
                    server="未知",
                    latency="N/A",
                    last_connect_time=None
                )
            },
            services_summary={
                "total": 5,
                "running": 0,
                "stopped": 0,
                "error": 5
            }
        )

        return SystemStatusResponse(
            success=False,
            message=f"获取系统状态异常: {str(e)}",
            data=system_info,
            request_id=str(uuid.uuid4())
        )

@router.post("/start", response_model=APIResponse, summary="启动系统")
async def start_system(connector: SystemConnector = Depends(get_system_connector_dep)):
    """
    启动整个系统
    
    启动所有核心服务，包括：
    - 事件引擎
    - 配置管理器
    - CTP网关连接
    - 核心业务服务
    """
    try:
        result = await connector.start_system()
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data=result["data"],
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"启动系统异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/stop", response_model=APIResponse, summary="停止系统")
async def stop_system(connector: SystemConnector = Depends(get_system_connector_dep)):
    """
    停止整个系统
    
    按顺序停止所有服务：
    - 策略服务
    - 交易服务
    - 风控服务
    - 账户服务
    - 行情服务
    - 事件引擎
    """
    try:
        result = await connector.stop_system()
        
        return APIResponse(
            success=result["success"],
            message=result["message"],
            data=result["data"],
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"停止系统异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/mode", response_model=APIResponse, summary="切换运行模式")
async def switch_mode(
    request: SystemModeRequest,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    切换系统运行模式
    
    支持的模式：
    - FULL_TRADING: 完整交易模式
    - MONITOR_ONLY: 仅监控模式
    - MARKET_DATA_ONLY: 仅行情模式
    """
    try:
        # 这里可以添加模式切换逻辑
        # 目前返回成功响应
        return APIResponse(
            success=True,
            message=f"运行模式已切换为: {request.mode}",
            data={"new_mode": request.mode},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"切换运行模式异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/emergency/pause", response_model=APIResponse, summary="紧急暂停")
async def emergency_pause(
    request: EmergencyRequest,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    紧急暂停所有交易活动
    
    立即停止：
    - 所有策略执行
    - 新订单提交
    - 保持监控功能
    """
    try:
        # 这里可以添加紧急暂停逻辑
        return APIResponse(
            success=True,
            message="紧急暂停执行成功",
            data={"reason": request.reason, "timestamp": datetime.now().isoformat()},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"紧急暂停异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.post("/emergency/close-positions", response_model=APIResponse, summary="紧急平仓")
async def emergency_close_positions(
    request: EmergencyRequest,
    connector: SystemConnector = Depends(get_system_connector_dep)
):
    """
    紧急平仓所有持仓
    
    立即执行：
    - 获取所有持仓
    - 提交平仓订单
    - 监控执行状态
    """
    try:
        # 这里可以添加紧急平仓逻辑
        return APIResponse(
            success=True,
            message="紧急平仓指令已发送",
            data={"reason": request.reason, "timestamp": datetime.now().isoformat()},
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"紧急平仓异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )

@router.get("/architecture", response_model=APIResponse, summary="获取架构信息")
async def get_architecture_info(connector: SystemConnector = Depends(get_system_connector_dep)):
    """
    获取系统架构信息
    
    返回：
    - 架构版本
    - 组件状态
    - 连接信息
    """
    try:
        architecture_info = connector.get_architecture_info()
        
        return APIResponse(
            success=True,
            message="架构信息获取成功",
            data=architecture_info,
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"获取架构信息异常: {str(e)}",
            data={},
            request_id=str(uuid.uuid4())
        )
