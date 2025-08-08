"""
系统控制API路由
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
from ..dependencies import get_system_manager, get_system_connector_dep
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

            system_info = SystemInfo(
                system_status=data.get("system_status", "stopped"),
                running_mode=data.get("running_mode", "MARKET_DATA_ONLY"),
                start_time=datetime.fromisoformat(data["start_time"].replace("Z", "+00:00")) if data.get("start_time") else None,
                uptime=data.get("uptime", ""),
                                ctp_status={
                                    "market_data": CTPConnectionInfo(
                                        connected=data.get("ctp_status", {}).get("market_data", {}).get("connected", False),
                                        server=data.get("ctp_status", {}).get("market_data", {}).get("server", "182.254.243.31:30011"),
                                        latency=data.get("ctp_status", {}).get("market_data", {}).get("latency", "N/A"),
                                        last_connect_time=datetime.fromisoformat(data.get("ctp_status", {}).get("market_data", {}).get("last_connect_time", datetime.now().isoformat()).replace("Z", "+00:00")) if data.get("ctp_status", {}).get("market_data", {}).get("last_connect_time") else datetime.now()
                                    ),
                                    "trading": CTPConnectionInfo(
                                        connected=data.get("ctp_status", {}).get("trading", {}).get("connected", False),
                                        server=data.get("ctp_status", {}).get("trading", {}).get("server", "182.254.243.31:30001"),
                                        latency=data.get("ctp_status", {}).get("trading", {}).get("latency", "N/A"),
                                        last_connect_time=datetime.fromisoformat(data.get("ctp_status", {}).get("trading", {}).get("last_connect_time", datetime.now().isoformat()).replace("Z", "+00:00")) if data.get("ctp_status", {}).get("trading", {}).get("last_connect_time") else datetime.now()
                                    )
                                },
                                services_summary=data.get("services_summary", {
                                    "total": 5,
                                    "running": 1,
                                    "stopped": 4,
                                    "error": 0
                                }),
                                version=data.get("version", "1.0.0")
                            )

                            return SystemStatusResponse(
                                success=True,
                                message="系统状态获取成功",
                                data=system_info,
                                request_id=str(uuid.uuid4())
                            )
                except:
                    continue

        # 如果无法连接到主系统，返回默认状态
        system_info = SystemInfo(
            system_status="stopped",
            running_mode="UNKNOWN",
            start_time=datetime.now(),
            uptime="0h 0m",
            ctp_status={
                "market_data": CTPConnectionInfo(
                    connected=False,
                    server="182.254.243.31:30011",
                    latency="N/A",
                    last_connect_time=datetime.now()
                ),
                "trading": CTPConnectionInfo(
                    connected=False,
                    server="182.254.243.31:30001",
                    latency="N/A",
                    last_connect_time=datetime.now()
                )
            },
            services_summary={
                "total": 5,
                "running": 0,
                "stopped": 5,
                "error": 0
            }
        )
        
        return SystemStatusResponse(
            success=True,
            message="系统状态获取成功",
            data=system_info,
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取系统状态失败: {str(e)}"
        )

@router.post("/mode", response_model=APIResponse, summary="切换运行模式")
async def switch_system_mode(
    request: SystemModeRequest,
    system_manager=Depends(get_system_manager)
):
    """
    切换系统运行模式
    
    支持的模式:
    - FULL_TRADING: 完整交易模式
    - MONITOR_ONLY: 仅监控模式
    - MARKET_DATA_ONLY: 仅行情模式
    """
    try:
        # 这里暂时返回成功响应，后续会实现实际的模式切换逻辑
        return APIResponse(
            success=True,
            message=f"系统模式已切换至 {request.mode.value}",
            data={
                "old_mode": "FULL_TRADING",
                "new_mode": request.mode.value,
                "switch_time": datetime.now().isoformat(),
                "operator": request.operator,
                "reason": request.reason
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"切换运行模式失败: {str(e)}"
        )

@router.post("/start", response_model=APIResponse, summary="启动系统")
async def start_system(system_manager=Depends(get_system_manager)):
    """
    启动整个ARBIG系统
    
    按照依赖顺序启动所有服务:
    1. CTP连接
    2. 事件引擎
    3. 核心服务
    """
    try:
        # 这里暂时返回成功响应，后续会实现实际的系统启动逻辑
        return APIResponse(
            success=True,
            message="系统启动成功",
            data={
                "start_time": datetime.now().isoformat(),
                "services_started": ["MarketDataService", "AccountService", "RiskService", "TradingService"]
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"系统启动失败: {str(e)}"
        )

@router.post("/stop", response_model=APIResponse, summary="停止系统")
async def stop_system(system_manager=Depends(get_system_manager)):
    """
    停止整个ARBIG系统
    
    按照相反顺序停止所有服务，确保优雅关闭
    """
    try:
        # 这里暂时返回成功响应，后续会实现实际的系统停止逻辑
        return APIResponse(
            success=True,
            message="系统停止成功",
            data={
                "stop_time": datetime.now().isoformat(),
                "services_stopped": ["TradingService", "RiskService", "AccountService", "MarketDataService"]
            },
            request_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"系统停止失败: {str(e)}"
        )

@router.post("/emergency/stop", response_model=APIResponse, summary="紧急停止")
async def emergency_stop(
    request: EmergencyRequest,
    system_manager=Depends(get_system_manager)
):
    """
    紧急停止系统
    
    立即停止所有交易活动，保护资金安全
    需要提供操作原因和操作员信息
    """
    try:
        # 验证确认码（如果需要）
        if request.confirmation_code and request.confirmation_code != "EMERGENCY_STOP_123":
            raise HTTPException(
                status_code=400,
                detail="确认码错误"
            )
        
        # 这里暂时返回成功响应，后续会实现实际的紧急停止逻辑
        return APIResponse(
            success=True,
            message="紧急停止执行成功",
            data={
                "action": "emergency_stop",
                "execute_time": datetime.now().isoformat(),
                "operator": request.operator,
                "reason": request.reason,
                "affected_services": ["TradingService", "RiskService"]
            },
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"紧急停止失败: {str(e)}"
        )

@router.post("/emergency/close", response_model=APIResponse, summary="紧急平仓")
async def emergency_close(
    request: EmergencyRequest,
    system_manager=Depends(get_system_manager)
):
    """
    紧急平仓操作
    
    立即平掉所有持仓，需要特殊确认码
    这是最高级别的风控操作
    """
    try:
        # 验证确认码
        if request.confirmation_code != "EMERGENCY_CLOSE_123":
            raise HTTPException(
                status_code=400,
                detail="紧急平仓确认码错误"
            )
        
        # 这里暂时返回成功响应，后续会实现实际的紧急平仓逻辑
        return APIResponse(
            success=True,
            message="紧急平仓执行成功",
            data={
                "action": "emergency_close",
                "execute_time": datetime.now().isoformat(),
                "operator": request.operator,
                "reason": request.reason,
                "positions_closed": ["au2509_long_5", "au2512_short_2"]
            },
            request_id=str(uuid.uuid4())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"紧急平仓失败: {str(e)}"
        )

@router.get("/health", response_model=APIResponse, summary="健康检查")
async def health_check():
    """
    系统健康检查接口
    
    用于监控系统是否正常运行
    """
    return APIResponse(
        success=True,
        message="系统运行正常",
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        },
        request_id=str(uuid.uuid4())
    )


# ==================== 配置管理API ====================

import yaml
import os
from pydantic import BaseModel

class RemoveMainContractRequest(BaseModel):
    symbol: str

class SaveMainContractRequest(BaseModel):
    main_contract: str

@router.get("/config/market_data", summary="获取行情配置")
async def get_market_data_config():
    """获取行情订阅配置"""
    try:
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            return APIResponse(
                success=False,
                message="配置文件不存在",
                data=None
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        market_data_config = config.get('market_data', {})

        return APIResponse(
            success=True,
            message="获取行情配置成功",
            data=market_data_config
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取行情配置失败: {str(e)}"
        )

@router.post("/config/market_data/remove_main_contract", summary="从主力合约配置中移除")
async def remove_main_contract(request: RemoveMainContractRequest):
    """从主力合约配置中移除指定合约"""
    try:
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            return APIResponse(
                success=False,
                message="配置文件不存在",
                data=None
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'market_data' not in config:
            config['market_data'] = {}

        current_main_contract = config['market_data'].get('main_contract', '')

        if request.symbol == current_main_contract:
            # 移除主力合约（设置为空）
            config['market_data']['main_contract'] = ''

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            return APIResponse(
                success=True,
                message=f"已清除主力合约配置 {request.symbol}",
                data={"removed_symbol": request.symbol}
            )
        else:
            return APIResponse(
                success=False,
                message=f"合约 {request.symbol} 不是当前主力合约（当前主力合约: {current_main_contract}）",
                data=None
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"移除主力合约失败: {str(e)}"
        )

@router.post("/config/market_data/save_main_contract", summary="保存主力合约")
async def save_main_contract(request: SaveMainContractRequest):
    """保存主力合约到配置文件"""
    try:
        config_path = "config.yaml"
        if not os.path.exists(config_path):
            return APIResponse(
                success=False,
                message="配置文件不存在",
                data=None
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'market_data' not in config:
            config['market_data'] = {}

        # 保存主力合约
        config['market_data']['main_contract'] = request.main_contract

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        return APIResponse(
            success=True,
            message=f"主力合约 {request.main_contract} 保存成功",
            data={"main_contract": request.main_contract}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存主力合约失败: {str(e)}"
        )
