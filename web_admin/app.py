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

    def __init__(self, demo_mode=True):
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

        # === 新增：注册API路由 ===
        self.app.include_router(system_router)
        self.app.include_router(services_router)
        self.app.include_router(strategies_router)
        self.app.include_router(data_router)

        # 核心组件
        self.demo_mode = demo_mode
        self.data_provider = None
        self.risk_controller = None
        self.websocket_connections = []
        
        # 设置路由
        self.setup_routes()
        
        # 挂载静态文件（前端页面）
        self.static_dir = Path(__file__).parent / "static"
        if self.static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")

    def _get_demo_data(self, data_type: str):
        """获取演示数据"""
        if data_type == "system_status":
            return {
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "market_data": "RUNNING",
                    "account": "RUNNING",
                    "trading": "RUNNING",
                    "risk": "RUNNING"
                },
                "risk_level": "LOW",
                "trading_halted": False,
                "connections": {
                    "ctp_md": True,
                    "ctp_td": True
                }
            }
        elif data_type == "positions":
            return [
                {
                    "symbol": "au2507",
                    "direction": "LONG",
                    "volume": 0,
                    "frozen": 0,
                    "price": 0.0,
                    "pnl": 0.0,
                    "margin": 0.0
                }
            ]
        elif data_type == "orders":
            return []
        elif data_type == "trades":
            return [
                {
                    "trade_id": "20250709001",
                    "symbol": "au2507",
                    "direction": "LONG",
                    "volume": 1,
                    "price": 763.44,
                    "time": "2025-07-09 14:37:30",
                    "commission": 14.30
                },
                {
                    "trade_id": "20250709002",
                    "symbol": "au2507",
                    "direction": "SHORT",
                    "volume": 1,
                    "price": 761.74,
                    "time": "2025-07-09 14:37:35",
                    "commission": 14.30
                }
            ]
        elif data_type == "market_data":
            return {
                "au2507": {
                    "symbol": "au2507",
                    "last_price": 764.6,
                    "bid_price": 762.86,
                    "ask_price": 764.46,
                    "volume": 125840,
                    "turnover": 9623456780.0,
                    "open_price": 765.2,
                    "high_price": 768.8,
                    "low_price": 761.4,
                    "pre_close": 765.0,
                    "timestamp": datetime.now().isoformat()
                }
            }
        elif data_type == "risk_metrics":
            return {
                "total_pnl": -2860.0,
                "daily_pnl": -2860.0,
                "max_drawdown": -2860.0,
                "win_rate": 0.0,
                "sharpe_ratio": 0.0,
                "total_trades": 2,
                "winning_trades": 0,
                "losing_trades": 1,
                "avg_win": 0.0,
                "avg_loss": -2860.0,
                "risk_level": "LOW",
                "position_ratio": 0.0
            }
        elif data_type == "account_info":
            return {
                "account_id": "888888888",
                "balance": 20473016.0,
                "available": 20473016.0,
                "frozen": 0.0,
                "margin": 0.0,
                "commission": 28.60,
                "close_profit": -2860.0,
                "position_profit": 0.0,
                "pre_balance": 20475876.0,
                "deposit": 0.0,
                "withdraw": 0.0
            }
        elif data_type == "trading_stats":
            return {
                "trading": {
                    "total_orders": 4,
                    "active_orders": 0,
                    "total_trades": 2,
                    "total_turnover": 1525180.0
                },
                "performance": {
                    "total_pnl": -2860.0,
                    "win_rate": 0.0,
                    "profit_factor": 0.0,
                    "max_drawdown": -2860.0
                }
            }
        elif data_type == "strategies":
            return [
                {
                    "name": "SHFE_Gold_Strategy",
                    "status": "STOPPED",
                    "pnl": -2860.0,
                    "position": 0,
                    "description": "上海期货交易所黄金量化策略",
                    "start_time": "2025-07-09 09:00:00",
                    "last_signal": "2025-07-09 14:37:35",
                    "total_trades": 2,
                    "win_rate": 0.0
                },
                {
                    "name": "Demo_Strategy",
                    "status": "RUNNING",
                    "pnl": 0.0,
                    "position": 0,
                    "description": "演示策略",
                    "start_time": "2025-07-09 15:00:00",
                    "last_signal": "无",
                    "total_trades": 0,
                    "win_rate": 0.0
                }
            ]
        return {}
    
    def setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """根路径 - 返回主页面"""
            try:
                with open(os.path.join(self.static_dir, "index.html"), "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return HTMLResponse("""
                <html>
                <head><title>ARBIG监控系统</title></head>
                <body>
                    <h1>ARBIG监控与风控系统</h1>
                    <p>状态: 运行中</p>
                    <p>版本: 1.0.0</p>
                    <p>静态文件未找到，请检查 static/index.html</p>
                </body>
                </html>
                """)

        @self.app.get("/api/info")
        async def api_info():
            """API信息"""
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
        
        @self.app.get("/api/status")
        async def get_system_status():
            """获取系统状态"""
            if self.demo_mode:
                return self._get_demo_data("system_status")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_system_status()

        @self.app.get("/api/positions")
        async def get_positions():
            """获取持仓信息"""
            if self.demo_mode:
                return self._get_demo_data("positions")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_positions()

        @self.app.get("/api/orders")
        async def get_orders(active_only: bool = False):
            """获取订单信息"""
            if self.demo_mode:
                return self._get_demo_data("orders")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_orders(active_only)

        @self.app.get("/api/trades")
        async def get_trades(limit: int = 100):
            """获取成交信息"""
            if self.demo_mode:
                return self._get_demo_data("trades")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")
            
            return await self.data_provider.get_trades(limit)
        
        @self.app.get("/api/market_data")
        async def get_market_data():
            """获取行情数据"""
            if self.demo_mode:
                return self._get_demo_data("market_data")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_market_data()

        @self.app.get("/api/risk_metrics")
        async def get_risk_metrics():
            """获取风险指标"""
            if self.demo_mode:
                return self._get_demo_data("risk_metrics")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_risk_metrics()

        @self.app.get("/api/statistics")
        async def get_statistics():
            """获取统计信息"""
            if self.demo_mode:
                return self._get_demo_data("trading_stats")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_statistics()

        @self.app.get("/api/account")
        async def get_account_info():
            """获取账户信息"""
            if self.demo_mode:
                return self._get_demo_data("account_info")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_account_info()

        @self.app.get("/api/strategies")
        async def get_strategies():
            """获取策略列表"""
            if self.demo_mode:
                return self._get_demo_data("strategies")

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            return await self.data_provider.get_strategies()

        @self.app.post("/api/strategies/start")
        async def start_strategy(request: dict):
            """启动策略"""
            if self.demo_mode:
                return {"success": True, "message": f"策略 {request.get('strategy_name')} 启动成功（演示模式）"}

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.start_strategy(request.get('strategy_name'))
                return {"success": True, "data": result, "message": "策略启动成功"}
            except Exception as e:
                logger.error(f"启动策略失败: {e}")
                return {"success": False, "message": f"启动策略失败: {str(e)}"}

        @self.app.post("/api/strategies/stop")
        async def stop_strategy(request: dict):
            """停止策略"""
            if self.demo_mode:
                return {"success": True, "message": f"策略 {request.get('strategy_name')} 停止成功（演示模式）"}

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.stop_strategy(request.get('strategy_name'))
                return {"success": True, "data": result, "message": "策略停止成功"}
            except Exception as e:
                logger.error(f"停止策略失败: {e}")
                return {"success": False, "message": f"停止策略失败: {str(e)}"}

        @self.app.post("/api/strategies/halt")
        async def halt_strategy(request: dict):
            """暂停策略"""
            if self.demo_mode:
                return {"success": True, "message": f"策略 {request.get('strategy_name')} 暂停成功（演示模式）"}

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.halt_strategy(
                    request.get('strategy_name'),
                    request.get('reason')
                )
                return {"success": True, "data": result, "message": "策略暂停成功"}
            except Exception as e:
                logger.error(f"暂停策略失败: {e}")
                return {"success": False, "message": f"暂停策略失败: {str(e)}"}

        @self.app.get("/api/strategies/{strategy_name}/params")
        async def get_strategy_params(strategy_name: str):
            """获取策略参数"""
            if self.demo_mode:
                # 演示模式返回模拟参数
                return {
                    "success": True,
                    "data": {
                        "ma_short": 5,
                        "ma_long": 20,
                        "rsi_period": 14,
                        "rsi_overbought": 70,
                        "stop_loss": 0.05,
                        "take_profit": 0.08,
                        "position_size": 1,
                        "max_position": 5,
                        "risk_factor": 0.02,
                        "add_interval": 50,
                        "position_mode": "fixed",
                        "position_multiplier": 1.0
                    }
                }

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.get_strategy_params(strategy_name)
                return {"success": True, "data": result}
            except Exception as e:
                logger.error(f"获取策略参数失败: {e}")
                return {"success": False, "message": f"获取策略参数失败: {str(e)}"}

        @self.app.post("/api/strategies/{strategy_name}/params")
        async def update_strategy_params(strategy_name: str, params: dict):
            """更新策略参数"""
            if self.demo_mode:
                logger.info(f"演示模式：更新策略 {strategy_name} 参数: {params}")
                return {"success": True, "message": f"策略 {strategy_name} 参数更新成功（演示模式）"}

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.update_strategy_params(strategy_name, params)
                return {"success": True, "data": result, "message": "策略参数更新成功"}
            except Exception as e:
                logger.error(f"更新策略参数失败: {e}")
                return {"success": False, "message": f"更新策略参数失败: {str(e)}"}

        @self.app.post("/api/strategies/{strategy_name}/backtest")
        async def run_backtest(strategy_name: str, config: dict):
            """运行历史回测"""
            if self.demo_mode:
                # 演示模式返回模拟回测结果
                import random
                return {
                    "success": True,
                    "data": {
                        "total_return": round(random.uniform(-0.1, 0.3), 4),
                        "annual_return": round(random.uniform(-0.05, 0.25), 4),
                        "max_drawdown": round(random.uniform(0.02, 0.15), 4),
                        "sharpe_ratio": round(random.uniform(0.5, 2.5), 2),
                        "win_rate": round(random.uniform(0.4, 0.8), 2),
                        "total_trades": random.randint(50, 200),
                        "start_date": config.get("start_date", "2024-01-01"),
                        "end_date": config.get("end_date", "2024-12-31"),
                        "initial_capital": config.get("initial_capital", 100000)
                    },
                    "message": "回测完成（演示模式）"
                }

            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.run_backtest(strategy_name, config)
                return {"success": True, "data": result, "message": "回测完成"}
            except Exception as e:
                logger.error(f"运行回测失败: {e}")
                return {"success": False, "message": f"运行回测失败: {str(e)}"}

        # ========== 交易操作API ==========

        @self.app.post("/api/orders")
        async def submit_order(order: OrderRequest):
            """手动下单"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.submit_order(order)
                return {"success": True, "data": result, "message": "下单成功"}
            except Exception as e:
                logger.error(f"下单失败: {e}")
                return {"success": False, "message": f"下单失败: {str(e)}"}

        @self.app.delete("/api/orders/{order_id}")
        async def cancel_order(order_id: str):
            """撤销订单"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.cancel_order(order_id)
                return {"success": True, "data": result, "message": "撤单成功"}
            except Exception as e:
                logger.error(f"撤单失败: {e}")
                return {"success": False, "message": f"撤单失败: {str(e)}"}

        @self.app.post("/api/orders/{order_id}/modify")
        async def modify_order(order_id: str, modification: OrderModification):
            """修改订单"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="核心服务未连接")

            try:
                result = await self.data_provider.modify_order(order_id, modification)
                return {"success": True, "data": result, "message": "订单修改成功"}
            except Exception as e:
                logger.error(f"订单修改失败: {e}")
                return {"success": False, "message": f"订单修改失败: {str(e)}"}

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
