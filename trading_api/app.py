"""
ARBIG 交易API服务
提供交易、账户、行情、风控等核心业务API接口
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.trading_service import TradingService
from core.services.risk_service import RiskService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

# Pydantic模型定义
class RiskAction(BaseModel):
    action: str
    target: Optional[str] = None
    value: Optional[float] = None
    reason: str
    confirmation_code: Optional[str] = None

class PositionLimitUpdate(BaseModel):
    symbol: str
    new_limit: float
    reason: str

class StopLossUpdate(BaseModel):
    symbol: str
    price: float
    reason: str

class SystemStatus(BaseModel):
    timestamp: datetime
    services: Dict[str, str]
    risk_level: str
    trading_halted: bool
    connections: Dict[str, bool]

class WebRiskController:
    """Web风控控制器"""
    
    def __init__(self, risk_service: RiskService, trading_service: TradingService):
        self.risk_service = risk_service
        self.trading_service = trading_service
        self.operation_log = []
        
    def emergency_halt_all(self, reason: str, operator: str) -> bool:
        """紧急暂停所有交易"""
        try:
            self.risk_service._halt_trading(f"人工干预: {reason}")
            self._log_operation(operator, "EMERGENCY_HALT_ALL", reason)
            logger.critical(f"[人工干预] 紧急暂停所有交易 - 操作员: {operator}, 原因: {reason}")
            return True
        except Exception as e:
            logger.error(f"紧急暂停失败: {e}")
            return False
    
    def emergency_close_all(self, reason: str, operator: str, confirmation_code: str) -> bool:
        """紧急平仓所有持仓"""
        if confirmation_code != "EMERGENCY_CLOSE_123":
            return False
            
        try:
            # 获取所有活跃订单并撤销
            active_orders = self.trading_service.get_active_orders()
            for order in active_orders:
                self.trading_service.cancel_order(order.orderid)
            
            # TODO: 实现平仓逻辑
            self._log_operation(operator, "EMERGENCY_CLOSE_ALL", reason)
            logger.critical(f"[人工干预] 紧急平仓所有持仓 - 操作员: {operator}, 原因: {reason}")
            return True
        except Exception as e:
            logger.error(f"紧急平仓失败: {e}")
            return False
    
    def halt_strategy(self, strategy_name: str, reason: str, operator: str) -> bool:
        """暂停特定策略"""
        try:
            # 撤销策略的所有活跃订单
            cancelled_count = self.trading_service.cancel_strategy_orders(strategy_name)
            self._log_operation(operator, "HALT_STRATEGY", f"{strategy_name}: {reason}")
            logger.warning(f"[人工干预] 暂停策略 {strategy_name} - 操作员: {operator}, 撤销订单: {cancelled_count}")
            return True
        except Exception as e:
            logger.error(f"暂停策略失败: {e}")
            return False
    
    def resume_trading(self, reason: str, operator: str) -> bool:
        """恢复交易"""
        try:
            self.risk_service.resume_trading()
            self._log_operation(operator, "RESUME_TRADING", reason)
            logger.info(f"[人工干预] 恢复交易 - 操作员: {operator}, 原因: {reason}")
            return True
        except Exception as e:
            logger.error(f"恢复交易失败: {e}")
            return False
    
    def update_position_limit(self, symbol: str, new_limit: float, reason: str, operator: str) -> bool:
        """更新仓位限制"""
        try:
            old_limit = self.risk_service.position_limits.get(symbol, 0)
            self.risk_service.position_limits[symbol] = new_limit
            self._log_operation(operator, "UPDATE_POSITION_LIMIT", 
                              f"{symbol}: {old_limit} -> {new_limit}, {reason}")
            logger.info(f"[人工干预] 更新仓位限制 {symbol}: {old_limit} -> {new_limit}")
            return True
        except Exception as e:
            logger.error(f"更新仓位限制失败: {e}")
            return False
    
    def set_stop_loss(self, symbol: str, price: float, reason: str, operator: str) -> bool:
        """设置止损价格"""
        try:
            # TODO: 实现止损价格设置逻辑
            self._log_operation(operator, "SET_STOP_LOSS", f"{symbol}: {price}, {reason}")
            logger.info(f"[人工干预] 设置止损 {symbol}: {price}")
            return True
        except Exception as e:
            logger.error(f"设置止损失败: {e}")
            return False
    
    def _log_operation(self, operator: str, action: str, details: str):
        """记录操作日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operator': operator,
            'action': action,
            'details': details
        }
        self.operation_log.append(log_entry)
        
        # 保持最近1000条记录
        if len(self.operation_log) > 1000:
            self.operation_log = self.operation_log[-1000:]

class ARBIGWebApp:
    """ARBIG Web应用"""
    
    def __init__(self):
        self.app = FastAPI(title="ARBIG监控与风控系统", version="1.0.0")
        self.setup_cors()
        
        # 核心组件（这些需要从外部注入或连接）
        self.event_engine = None
        self.ctp_gateway = None
        self.market_data_service = None
        self.account_service = None
        self.trading_service = None
        self.risk_service = None
        
        # Web组件
        self.risk_controller = None
        self.websocket_connections = []
        
        # 设置路由
        self.setup_routes()
        
    def setup_cors(self):
        """设置CORS"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def root():
            return {"message": "ARBIG监控与风控系统", "status": "running"}
        
        @self.app.get("/api/status")
        async def get_system_status():
            """获取系统状态"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            return SystemStatus(
                timestamp=datetime.now(),
                services={
                    "market_data": self.market_data_service.get_status().value,
                    "account": self.account_service.get_status().value,
                    "trading": self.trading_service.get_status().value,
                    "risk": self.risk_service.get_status().value
                },
                risk_level=self.risk_service.risk_level,
                trading_halted=self.risk_service.is_trading_halted,
                connections={
                    "ctp_md": self.ctp_gateway.is_md_connected(),
                    "ctp_td": self.ctp_gateway.is_td_connected()
                }
            )
        
        @self.app.get("/api/positions")
        async def get_positions():
            """获取持仓信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            positions = self.account_service.get_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "direction": pos.direction.value,
                    "volume": pos.volume,
                    "price": pos.price,
                    "pnl": pos.pnl,
                    "frozen": pos.frozen
                }
                for pos in positions
            ]
        
        @self.app.get("/api/orders")
        async def get_orders(active_only: bool = False):
            """获取订单信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            if active_only:
                orders = self.trading_service.get_active_orders()
            else:
                orders = self.trading_service.get_orders()
            
            return [
                {
                    "orderid": order.orderid,
                    "symbol": order.symbol,
                    "direction": order.direction.value,
                    "volume": order.volume,
                    "price": order.price,
                    "status": order.status.value,
                    "traded": order.traded,
                    "datetime": order.datetime.isoformat()
                }
                for order in orders
            ]
        
        @self.app.get("/api/trades")
        async def get_trades():
            """获取成交信息"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            trades = self.trading_service.get_trades()
            return [
                {
                    "tradeid": trade.tradeid,
                    "orderid": trade.orderid,
                    "symbol": trade.symbol,
                    "direction": trade.direction.value,
                    "volume": trade.volume,
                    "price": trade.price,
                    "datetime": trade.datetime.isoformat()
                }
                for trade in trades
            ]
        
        @self.app.get("/api/market_data")
        async def get_market_data():
            """获取行情数据"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            ticks = self.market_data_service.get_all_ticks()
            return [
                {
                    "symbol": tick.symbol,
                    "last_price": tick.last_price,
                    "bid_price_1": tick.bid_price_1,
                    "ask_price_1": tick.ask_price_1,
                    "bid_volume_1": tick.bid_volume_1,
                    "ask_volume_1": tick.ask_volume_1,
                    "volume": tick.volume,
                    "datetime": tick.datetime.isoformat()
                }
                for tick in ticks.values()
            ]
        
        @self.app.get("/api/risk_metrics")
        async def get_risk_metrics():
            """获取风险指标"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            metrics = self.risk_service.get_risk_metrics()
            return {
                "timestamp": metrics.timestamp.isoformat(),
                "daily_pnl": metrics.daily_pnl,
                "total_pnl": metrics.total_pnl,
                "max_drawdown": metrics.max_drawdown,
                "position_ratio": metrics.position_ratio,
                "margin_ratio": metrics.margin_ratio,
                "risk_level": metrics.risk_level
            }
        
        @self.app.post("/api/risk/emergency_halt")
        async def emergency_halt(action: RiskAction):
            """紧急暂停交易"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            success = self.risk_controller.emergency_halt_all(action.reason, "web_operator")
            return {"success": success, "message": "紧急暂停" if success else "操作失败"}
        
        @self.app.post("/api/risk/emergency_close")
        async def emergency_close(action: RiskAction):
            """紧急平仓"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            if not action.confirmation_code:
                raise HTTPException(status_code=400, detail="需要确认码")
            
            success = self.risk_controller.emergency_close_all(
                action.reason, "web_operator", action.confirmation_code
            )
            return {"success": success, "message": "紧急平仓" if success else "操作失败"}
        
        @self.app.post("/api/risk/halt_strategy")
        async def halt_strategy(action: RiskAction):
            """暂停策略"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            if not action.target:
                raise HTTPException(status_code=400, detail="需要指定策略名称")
            
            success = self.risk_controller.halt_strategy(action.target, action.reason, "web_operator")
            return {"success": success, "message": f"暂停策略 {action.target}" if success else "操作失败"}
        
        @self.app.post("/api/risk/resume_trading")
        async def resume_trading(action: RiskAction):
            """恢复交易"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            success = self.risk_controller.resume_trading(action.reason, "web_operator")
            return {"success": success, "message": "恢复交易" if success else "操作失败"}
        
        @self.app.post("/api/risk/update_position_limit")
        async def update_position_limit(update: PositionLimitUpdate):
            """更新仓位限制"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            success = self.risk_controller.update_position_limit(
                update.symbol, update.new_limit, update.reason, "web_operator"
            )
            return {"success": success, "message": f"更新 {update.symbol} 仓位限制" if success else "操作失败"}
        
        @self.app.post("/api/risk/set_stop_loss")
        async def set_stop_loss(update: StopLossUpdate):
            """设置止损"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            success = self.risk_controller.set_stop_loss(
                update.symbol, update.price, update.reason, "web_operator"
            )
            return {"success": success, "message": f"设置 {update.symbol} 止损" if success else "操作失败"}
        
        @self.app.get("/api/operation_log")
        async def get_operation_log():
            """获取操作日志"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")
            
            return self.risk_controller.operation_log[-100:]  # 返回最近100条
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket连接"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # 发送实时数据
                    if self._services_ready():
                        data = await self._get_realtime_data()
                        await websocket.send_text(json.dumps(data))
                    
                    await asyncio.sleep(1)  # 每秒发送一次
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    def connect_services(self, event_engine, ctp_gateway, market_data_service, 
                        account_service, trading_service, risk_service):
        """连接核心服务"""
        self.event_engine = event_engine
        self.ctp_gateway = ctp_gateway
        self.market_data_service = market_data_service
        self.account_service = account_service
        self.trading_service = trading_service
        self.risk_service = risk_service
        
        # 创建风控控制器
        self.risk_controller = WebRiskController(risk_service, trading_service)
        
        logger.info("Web服务已连接到核心交易系统")
    
    def _services_ready(self) -> bool:
        """检查服务是否就绪"""
        return all([
            self.event_engine,
            self.ctp_gateway,
            self.market_data_service,
            self.account_service,
            self.trading_service,
            self.risk_service,
            self.risk_controller
        ])
    
    async def _get_realtime_data(self) -> Dict:
        """获取实时数据"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "system_status": {
                    "risk_level": self.risk_service.risk_level,
                    "trading_halted": self.risk_service.is_trading_halted,
                    "connections": {
                        "ctp_md": self.ctp_gateway.is_md_connected(),
                        "ctp_td": self.ctp_gateway.is_td_connected()
                    }
                },
                "statistics": {
                    "trading": self.trading_service.get_statistics(),
                    "risk": self.risk_service.get_statistics()
                }
            }
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return {"error": str(e)}

# 全局Web应用实例
web_app = ARBIGWebApp()
app = web_app.app

def run_web_service(host: str = "0.0.0.0", port: int = 8000):
    """运行Web服务"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_web_service()
