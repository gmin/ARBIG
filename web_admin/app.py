"""
ARBIG Web管理系统主应用
提供交易管理、风控管理、系统监控等功能
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .models import *
from .risk_controller import WebRiskController
from .data_provider import DataProvider
from utils.logger import get_logger

logger = get_logger(__name__)

class ARBIGWebApp:
    """ARBIG Web管理系统"""

    def __init__(self):
        self.app = FastAPI(
            title="ARBIG Web管理系统",
            version="1.0.0",
            description="量化交易管理、风控管理、系统监控平台"
        )
        
        # 设置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 核心组件
        self.data_provider = None
        self.risk_controller = None
        self.websocket_connections = []
        
        # 设置路由
        self.setup_routes()
        
        # 挂载静态文件（前端页面）
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    def setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/")
        async def root():
            """根路径"""
            return {
                "message": "ARBIG监控与风控系统", 
                "status": "running",
                "version": "1.0.0"
            }
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services_connected": self._services_ready()
            }
        
        # ========== 数据查询API ==========
        
        @self.app.get("/api/status", response_model=SystemStatus)
        async def get_system_status():
            """获取系统状态"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_system_status()
        
        @self.app.get("/api/positions")
        async def get_positions():
            """获取持仓信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_positions()
        
        @self.app.get("/api/orders")
        async def get_orders(active_only: bool = False):
            """获取订单信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_orders(active_only)
        
        @self.app.get("/api/trades")
        async def get_trades(limit: int = 100):
            """获取成交信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_trades(limit)
        
        @self.app.get("/api/market_data")
        async def get_market_data():
            """获取行情数据"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_market_data()
        
        @self.app.get("/api/risk_metrics")
        async def get_risk_metrics():
            """获取风险指标"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_risk_metrics()
        
        @self.app.get("/api/statistics")
        async def get_statistics():
            """获取统计信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_statistics()
        
        # ========== 风控操作API ==========
        
        @self.app.post("/api/risk/emergency_halt")
        async def emergency_halt(action: RiskAction):
            """紧急暂停交易"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            success = await self.risk_controller.emergency_halt_all(action.reason, action.operator)
            return {"success": success, "message": "紧急暂停交易" if success else "操作失败"}
        
        @self.app.post("/api/risk/emergency_close")
        async def emergency_close(action: RiskAction):
            """紧急平仓"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            if not action.confirmation_code:
                raise HTTPException(status_code=400, detail="需要确认码")
            
            success = await self.risk_controller.emergency_close_all(
                action.reason, action.operator, action.confirmation_code
            )
            return {"success": success, "message": "紧急平仓" if success else "操作失败"}
        
        @self.app.post("/api/risk/halt_strategy")
        async def halt_strategy(action: RiskAction):
            """暂停策略"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            if not action.target:
                raise HTTPException(status_code=400, detail="需要指定策略名称")
            
            success = await self.risk_controller.halt_strategy(
                action.target, action.reason, action.operator
            )
            return {"success": success, "message": f"暂停策略 {action.target}" if success else "操作失败"}
        
        @self.app.post("/api/risk/resume_trading")
        async def resume_trading(action: RiskAction):
            """恢复交易"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            success = await self.risk_controller.resume_trading(action.reason, action.operator)
            return {"success": success, "message": "恢复交易" if success else "操作失败"}
        
        @self.app.post("/api/risk/update_position_limit")
        async def update_position_limit(update: PositionLimitUpdate):
            """更新仓位限制"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            success = await self.risk_controller.update_position_limit(
                update.symbol, update.new_limit, update.reason, update.operator
            )
            return {"success": success, "message": f"更新 {update.symbol} 仓位限制" if success else "操作失败"}
        
        @self.app.post("/api/risk/set_stop_loss")
        async def set_stop_loss(update: StopLossUpdate):
            """设置止损"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            success = await self.risk_controller.set_stop_loss(
                update.symbol, update.price, update.reason, update.operator
            )
            return {"success": success, "message": f"设置 {update.symbol} 止损" if success else "操作失败"}
        
        @self.app.get("/api/operation_log")
        async def get_operation_log(limit: int = 100):
            """获取操作日志"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.risk_controller.get_operation_log(limit)
        
        # ========== WebSocket实时数据 ==========
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket实时数据推送"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            logger.info(f"WebSocket连接建立，当前连接数: {len(self.websocket_connections)}")
            
            try:
                while True:
                    if self._services_ready():
                        # 获取实时数据
                        data = await self._get_realtime_data()
                        await websocket.send_text(json.dumps(data, default=str))
                    else:
                        # 服务未就绪时发送状态信息
                        await websocket.send_text(json.dumps({
                            "error": "核心服务未连接",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    await asyncio.sleep(1)  # 每秒推送一次
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                logger.info(f"WebSocket连接断开，当前连接数: {len(self.websocket_connections)}")
            except Exception as e:
                logger.error(f"WebSocket错误: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
    
    def connect_services(self, trading_system):
        """连接核心交易系统"""
        try:
            self.data_provider = DataProvider(trading_system)
            self.risk_controller = WebRiskController(trading_system)
            
            logger.info("Web监控系统已连接到核心交易系统")
            return True
            
        except Exception as e:
            logger.error(f"连接核心交易系统失败: {e}")
            return False
    
    def _services_ready(self) -> bool:
        """检查服务是否就绪"""
        return self.data_provider is not None and self.risk_controller is not None
    
    async def _get_realtime_data(self) -> Dict:
        """获取实时数据用于WebSocket推送"""
        try:
            return {
                "type": "realtime_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "system_status": await self.data_provider.get_system_status(),
                    "risk_metrics": await self.data_provider.get_risk_metrics(),
                    "statistics": await self.data_provider.get_statistics(),
                    "active_orders_count": len(await self.data_provider.get_orders(active_only=True)),
                    "positions_count": len(await self.data_provider.get_positions())
                }
            }
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return {
                "type": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def broadcast_alert(self, alert_data: Dict):
        """广播风险预警到所有WebSocket连接"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "risk_alert",
            "timestamp": datetime.now().isoformat(),
            "data": alert_data
        }
        
        # 向所有连接的客户端发送预警
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except:
                disconnected.append(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            self.websocket_connections.remove(ws)

# 创建全局应用实例
web_app = ARBIGWebApp()
app = web_app.app

def run_web_service(host: str = "0.0.0.0", port: int = 8000, **kwargs):
    """运行Web监控服务"""
    logger.info(f"启动ARBIG Web监控服务: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, **kwargs)

if __name__ == "__main__":
    run_web_service()
