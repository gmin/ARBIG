"""
ARBIG 交易API服务
提供交易、账户、行情、风控等核心业务API接口
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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

        # 挂载静态文件（Web界面）
        self.setup_static_files()

        # 尝试自动连接CTP（用于测试）
        self.auto_connect_ctp()
        
    def setup_cors(self):
        """设置CORS"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_static_files(self):
        """设置静态文件服务"""
        try:
            # 挂载web_admin的静态文件
            static_dir = Path(__file__).parent.parent / "web_admin" / "static"
            if static_dir.exists():
                self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
                logger.info(f"挂载静态文件目录: {static_dir}")

                # 添加根路径重定向到主页
                @self.app.get("/", response_class=HTMLResponse)
                async def serve_index():
                    index_file = static_dir / "index.html"
                    if index_file.exists():
                        return HTMLResponse(content=index_file.read_text(encoding='utf-8'))
                    else:
                        return {"message": "ARBIG监控与风控系统", "status": "running", "note": "Web界面文件未找到"}
            else:
                logger.warning(f"静态文件目录不存在: {static_dir}")
        except Exception as e:
            logger.error(f"设置静态文件失败: {e}")
    
    def setup_routes(self):
        """设置路由"""
        
        # 根路径已在setup_static_files中定义
        
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

        @self.app.get("/api/history/orders")
        async def get_history_orders(limit: int = 100):
            """获取CTP历史订单"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")

            try:
                if not hasattr(self, 'ctp_gateway') or not self.ctp_gateway:
                    raise HTTPException(status_code=503, detail="CTP网关未连接")

                if not hasattr(self.ctp_gateway, 'td_api') or not self.ctp_gateway.td_api:
                    raise HTTPException(status_code=503, detail="CTP交易API未连接")

                td_api = self.ctp_gateway.td_api
                received_orders = []

                def order_callback(data, error, reqid, last):
                    if error and error.ErrorID != 0:
                        logger.error(f"历史订单查询错误: {error.ErrorID} - {error.ErrorMsg}")
                    elif data:
                        received_orders.append(data)

                # 设置回调
                original_callback = getattr(td_api, 'onRspQryOrder', None)
                td_api.onRspQryOrder = order_callback

                # 发送查询请求
                result = td_api.reqQryOrder({}, int(time.time() * 1000) % 1000000)
                if result != 0:
                    raise HTTPException(status_code=500, detail=f"历史订单查询请求失败: {result}")

                # 等待响应
                for i in range(10):
                    await asyncio.sleep(0.5)
                    if len(received_orders) > 0:
                        break

                # 恢复原始回调
                if original_callback:
                    td_api.onRspQryOrder = original_callback

                # 转换为API响应格式
                formatted_orders = []
                for order in received_orders[:limit]:
                    formatted_order = {
                        "order_id": order.get('OrderSysID', order.get('OrderLocalID', 'N/A')),
                        "order_ref": order.get('OrderRef', 'N/A'),
                        "symbol": order.get('InstrumentID', 'N/A'),
                        "direction": "买入" if order.get('Direction') == '0' else "卖出",
                        "volume": int(order.get('VolumeTotalOriginal', 0)),
                        "price": float(order.get('LimitPrice', 0)),
                        "status": order.get('StatusMsg', 'N/A'),
                        "order_status": order.get('OrderStatus', 'N/A'),
                        "traded_volume": int(order.get('VolumeTraded', 0)),
                        "remaining_volume": int(order.get('VolumeTotal', 0)),
                        "insert_date": order.get('InsertDate', 'N/A'),
                        "insert_time": order.get('InsertTime', 'N/A'),
                        "exchange": order.get('ExchangeID', 'N/A'),
                        "session_id": order.get('SessionID', 'N/A')
                    }
                    formatted_orders.append(formatted_order)

                logger.info(f"获取到 {len(formatted_orders)} 条历史订单")
                return {
                    "success": True,
                    "message": f"历史订单获取成功，共{len(formatted_orders)}条记录",
                    "data": {"orders": formatted_orders}
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取历史订单失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取历史订单失败: {str(e)}")

        @self.app.get("/api/history/trades")
        async def get_history_trades(limit: int = 100):
            """获取CTP历史成交"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")

            try:
                if not hasattr(self, 'ctp_gateway') or not self.ctp_gateway:
                    raise HTTPException(status_code=503, detail="CTP网关未连接")

                if not hasattr(self.ctp_gateway, 'td_api') or not self.ctp_gateway.td_api:
                    raise HTTPException(status_code=503, detail="CTP交易API未连接")

                td_api = self.ctp_gateway.td_api
                received_trades = []

                def trade_callback(data, error, reqid, last):
                    if error and error.ErrorID != 0:
                        logger.error(f"历史成交查询错误: {error.ErrorID} - {error.ErrorMsg}")
                    elif data:
                        received_trades.append(data)

                # 设置回调
                original_callback = getattr(td_api, 'onRspQryTrade', None)
                td_api.onRspQryTrade = trade_callback

                # 发送查询请求
                result = td_api.reqQryTrade({}, int(time.time() * 1000) % 1000000)
                if result != 0:
                    raise HTTPException(status_code=500, detail=f"历史成交查询请求失败: {result}")

                # 等待响应
                for i in range(10):
                    await asyncio.sleep(0.5)
                    if len(received_trades) > 0:
                        break

                # 恢复原始回调
                if original_callback:
                    td_api.onRspQryTrade = original_callback

                # 转换为API响应格式
                formatted_trades = []
                for trade in received_trades[:limit]:
                    formatted_trade = {
                        "trade_id": trade.get('TradeID', 'N/A'),
                        "order_id": trade.get('OrderSysID', 'N/A'),
                        "order_ref": trade.get('OrderRef', 'N/A'),
                        "symbol": trade.get('InstrumentID', 'N/A'),
                        "direction": "买入" if trade.get('Direction') == '0' else "卖出",
                        "volume": int(trade.get('Volume', 0)),
                        "price": float(trade.get('Price', 0)),
                        "trade_date": trade.get('TradeDate', 'N/A'),
                        "trade_time": trade.get('TradeTime', 'N/A'),
                        "exchange": trade.get('ExchangeID', 'N/A'),
                        "amount": float(trade.get('Price', 0)) * int(trade.get('Volume', 0)) * 1000  # 黄金每手1000克
                    }
                    formatted_trades.append(formatted_trade)

                logger.info(f"获取到 {len(formatted_trades)} 条历史成交")
                return {
                    "success": True,
                    "message": f"历史成交获取成功，共{len(formatted_trades)}条记录",
                    "data": {"trades": formatted_trades}
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取历史成交失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取历史成交失败: {str(e)}")

        @self.app.get("/api/trading/summary")
        async def get_trading_summary():
            """获取交易汇总统计"""
            if not self._services_ready():
                raise HTTPException(status_code=503, detail="服务未就绪")

            try:
                # 获取历史数据
                history_orders_response = await get_history_orders()
                history_trades_response = await get_history_trades()

                if not history_orders_response.get('success') or not history_trades_response.get('success'):
                    # 如果历史查询失败，返回空汇总
                    return {
                        "success": True,
                        "message": "历史数据查询失败，返回空汇总",
                        "data": {
                            'total_orders': 0,
                            'successful_orders': 0,
                            'rejected_orders': 0,
                            'success_rate': 0,
                            'total_trades': 0,
                            'total_trade_amount': 0,
                            'today_orders': 0,
                            'today_trades': 0,
                            'today_trade_amount': 0,
                            'last_update': datetime.now().isoformat()
                        }
                    }

                history_orders = history_orders_response['data']['orders']
                history_trades = history_trades_response['data']['trades']

                # 统计订单状态
                total_orders = len(history_orders)
                successful_orders = len([o for o in history_orders if o.get('order_status') == '0'])  # 全部成交
                rejected_orders = len([o for o in history_orders if o.get('order_status') == '5'])   # 已撤单

                # 统计成交金额
                total_trade_amount = sum(t.get('amount', 0) for t in history_trades)

                # 计算今日数据
                today = datetime.now().strftime('%Y%m%d')
                today_orders = [o for o in history_orders if o.get('insert_date') == today]
                today_trades = [t for t in history_trades if t.get('trade_date') == today]

                today_trade_amount = sum(t.get('amount', 0) for t in today_trades)

                summary = {
                    'total_orders': total_orders,
                    'successful_orders': successful_orders,
                    'rejected_orders': rejected_orders,
                    'success_rate': (successful_orders / total_orders * 100) if total_orders > 0 else 0,
                    'total_trades': len(history_trades),
                    'total_trade_amount': total_trade_amount,
                    'today_orders': len(today_orders),
                    'today_trades': len(today_trades),
                    'today_trade_amount': today_trade_amount,
                    'last_update': datetime.now().isoformat()
                }

                return {
                    "success": True,
                    "message": "交易汇总获取成功",
                    "data": summary
                }

            except Exception as e:
                logger.error(f"获取交易汇总失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取交易汇总失败: {str(e)}")
        
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
    
    def auto_connect_ctp(self):
        """自动连接CTP（用于测试）"""
        try:
            import json
            from vnpy_ctp import CtpGateway
            from vnpy.event import EventEngine

            # 加载CTP配置
            config_path = Path(__file__).parent.parent / "config" / "ctp_sim.json"
            if not config_path.exists():
                logger.warning("CTP配置文件不存在，跳过自动连接")
                return

            with open(config_path, 'r') as f:
                config = json.load(f)

            # 创建事件引擎和CTP网关
            self.event_engine = EventEngine()
            self.ctp_gateway = CtpGateway(self.event_engine, 'CTP')

            # 连接配置
            vnpy_config = {
                '用户名': config['用户名'],
                '密码': config['密码'],
                '经纪商代码': config['经纪商代码'],
                '交易服务器': config['交易服务器'],
                '行情服务器': config['行情服务器'],
                '产品名称': config['产品名称'],
                '授权编码': config['授权编码']
            }

            logger.info("正在连接CTP...")
            self.ctp_gateway.connect(vnpy_config)

            # 等待连接建立
            import time
            time.sleep(8)

            if hasattr(self.ctp_gateway, 'td_api') and self.ctp_gateway.td_api:
                logger.info("CTP连接成功，历史查询功能可用")
            else:
                logger.warning("CTP连接失败，历史查询功能不可用")

        except Exception as e:
            logger.error(f"自动连接CTP失败: {e}")

    def _services_ready(self) -> bool:
        """检查服务是否就绪"""
        # 对于历史查询，只需要CTP网关连接即可
        if hasattr(self, 'ctp_gateway') and self.ctp_gateway:
            return hasattr(self.ctp_gateway, 'td_api') and self.ctp_gateway.td_api

        # 完整服务检查
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
