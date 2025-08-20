"""
CTP网关封装
基于vnpy-ctp实现的CTP接口封装，提供统一的接口
"""

import json
import time
from typing import Dict, List, Optional, Callable
from pathlib import Path

from vnpy.event import EventEngine as VnpyEventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway as VnpyCtpGateway
from vnpy.trader.object import (
    SubscribeRequest, OrderRequest as VnpyOrderRequest, 
    CancelRequest, TickData, OrderData, TradeData, 
    AccountData, PositionData, ContractData
)
from vnpy.trader.constant import Exchange
from vnpy.trader.event import (
    EVENT_TICK, EVENT_ORDER, EVENT_TRADE, 
    EVENT_ACCOUNT, EVENT_POSITION, EVENT_CONTRACT, EVENT_LOG
)

from core.types import OrderRequest, ServiceStatus
from utils.logger import get_logger

logger = get_logger(__name__)

class CtpGatewayWrapper:
    """CTP网关封装类"""
    
    def __init__(self):
        """初始化CTP网关"""
        self.status = ServiceStatus.STOPPED
        
        # vnpy组件
        self.vnpy_event_engine = VnpyEventEngine()
        self.main_engine = MainEngine(self.vnpy_event_engine)
        self.ctp_gateway: Optional[VnpyCtpGateway] = None
        
        # 连接状态
        self.td_connected = False
        self.md_connected = False
        self.td_login_status = False
        self.md_login_status = False
        
        # 数据缓存
        self.contracts: Dict[str, ContractData] = {}
        self.ticks: Dict[str, TickData] = {}
        self.orders: Dict[str, OrderData] = {}
        self.trades: Dict[str, TradeData] = {}
        self.account: Optional[AccountData] = None
        self.positions: Dict[str, PositionData] = {}
        
        # 回调函数
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        self.order_callbacks: List[Callable[[OrderData], None]] = []
        self.trade_callbacks: List[Callable[[TradeData], None]] = []
        self.account_callbacks: List[Callable[[AccountData], None]] = []
        self.position_callbacks: List[Callable[[PositionData], None]] = []
        
        # 初始化
        self._init_gateway()
        self._register_events()
        
        logger.info("CTP网关封装初始化完成")
    
    def _init_gateway(self) -> None:
        """初始化CTP网关"""
        try:
            # 添加CTP网关
            self.main_engine.add_gateway(VnpyCtpGateway, "CTP")
            self.ctp_gateway = self.main_engine.get_gateway("CTP")
            
            if not self.ctp_gateway:
                raise Exception("无法获取CTP网关实例")
                
            logger.info("CTP网关实例创建成功")
            
        except Exception as e:
            logger.error(f"初始化CTP网关失败: {e}")
            raise
    
    def _register_events(self) -> None:
        """注册事件处理函数"""
        self.vnpy_event_engine.register(EVENT_TICK, self._on_tick)
        self.vnpy_event_engine.register(EVENT_ORDER, self._on_order)
        self.vnpy_event_engine.register(EVENT_TRADE, self._on_trade)
        self.vnpy_event_engine.register(EVENT_ACCOUNT, self._on_account)
        self.vnpy_event_engine.register(EVENT_POSITION, self._on_position)
        self.vnpy_event_engine.register(EVENT_CONTRACT, self._on_contract)
        self.vnpy_event_engine.register(EVENT_LOG, self._on_log)
        
        logger.info("事件处理函数注册完成")
    
    def _load_ctp_config(self) -> Dict[str, str]:
        """加载CTP配置"""
        try:
            # 从JSON配置文件读取
            json_config_path = Path("config/ctp_sim.json")
            if not json_config_path.exists():
                raise FileNotFoundError(f"CTP配置文件不存在: {json_config_path}")

            with open(json_config_path, 'r', encoding='utf-8') as f:
                json_config = json.load(f)

            # 转换为vnpy格式
            setting = {
                "用户名": json_config.get("用户名", ""),
                "密码": json_config.get("密码", ""),
                "经纪商代码": json_config.get("经纪商代码", ""),
                "交易服务器": f"tcp://{json_config.get('交易服务器', '')}",
                "行情服务器": f"tcp://{json_config.get('行情服务器', '')}",
                "产品名称": json_config.get("产品名称", ""),
                "授权编码": json_config.get("授权编码", "")
            }

            logger.info("从JSON配置文件加载CTP配置")
            return setting

        except Exception as e:
            logger.error(f"加载CTP配置失败: {e}")
            raise
    
    def connect(self) -> bool:
        """连接CTP服务器"""
        try:
            if self.status == ServiceStatus.RUNNING:
                logger.warning("CTP网关已连接")
                return True
            
            self.status = ServiceStatus.STARTING
            
            # 加载配置
            setting = self._load_ctp_config()
            
            logger.info("开始连接CTP服务器...")
            logger.info(f"交易服务器: {setting['交易服务器']}")
            logger.info(f"行情服务器: {setting['行情服务器']}")
            logger.info(f"用户名: {setting['用户名']}")
            
            # 连接CTP
            self.ctp_gateway.connect(setting)
            
            # 等待连接建立
            logger.info("等待连接建立...")
            max_wait_time = 30  # 最大等待30秒
            wait_time = 0
            
            while wait_time < max_wait_time:
                time.sleep(1)
                wait_time += 1

                # 检查连接状态
                self._update_connection_status()

                # 检查连接状态并记录详细信息
                md_status = self.md_connected and self.md_login_status
                td_status = self.td_connected and self.td_login_status

                if wait_time % 5 == 0:
                    logger.info(f"等待连接... {wait_time}/{max_wait_time}秒")
                    logger.info(f"  行情连接: {self.md_connected}, 行情登录: {self.md_login_status}")
                    logger.info(f"  交易连接: {self.td_connected}, 交易登录: {self.td_login_status}")

                # 理想情况：交易和行情都连接成功
                if md_status and td_status:
                    self.status = ServiceStatus.RUNNING
                    logger.info("CTP网关连接成功 - 完整连接（交易+行情）")

                    # 连接成功后，初始化查询历史数据
                    logger.info("连接成功，开始初始化查询历史数据...")
                    time.sleep(2)  # 等待连接稳定
                    self.init_query()

                    return True

                # 如果等待时间超过20秒，检查是否至少有一个连接成功
                if wait_time >= 20:
                    if md_status and not td_status:
                        logger.warning("⚠️ 交易连接失败，仅行情连接成功")
                        logger.warning("⚠️ 这将限制交易功能，只能查看行情数据")
                        logger.warning("⚠️ 无法进行下单、撤单、查询持仓等交易操作")
                        self.status = ServiceStatus.RUNNING
                        return True
                    elif td_status and not md_status:
                        logger.warning("⚠️ 行情连接失败，仅交易连接成功")
                        logger.warning("⚠️ 可以交易但无法获取实时行情数据")
                        self.status = ServiceStatus.RUNNING

                        # 交易连接成功后，初始化查询历史数据
                        logger.info("交易连接成功，开始初始化查询历史数据...")
                        time.sleep(2)  # 等待连接稳定
                        self.init_query()

                        return True
                    else:
                        logger.error("❌ 交易和行情连接都失败")
                        break
            
            # 连接超时
            logger.error("CTP连接超时")
            self.status = ServiceStatus.ERROR
            return False
            
        except Exception as e:
            logger.error(f"连接CTP失败: {e}")
            self.status = ServiceStatus.ERROR
            return False
    
    def disconnect(self) -> None:
        """断开CTP连接"""
        try:
            if self.status == ServiceStatus.STOPPED:
                return
            
            logger.info("断开CTP连接...")
            
            if self.ctp_gateway:
                self.ctp_gateway.close()
            
            # 清理数据
            self.contracts.clear()
            self.ticks.clear()
            self.orders.clear()
            self.trades.clear()
            self.positions.clear()
            self.account = None
            
            # 重置状态
            self.td_connected = False
            self.md_connected = False
            self.td_login_status = False
            self.md_login_status = False
            
            self.status = ServiceStatus.STOPPED
            logger.info("CTP连接已断开")
            
        except Exception as e:
            logger.error(f"断开CTP连接失败: {e}")
    
    def _update_connection_status(self) -> None:
        """更新连接状态"""
        try:
            if hasattr(self.ctp_gateway, 'md_api') and self.ctp_gateway.md_api:
                self.md_connected = getattr(self.ctp_gateway.md_api, 'connect_status', False)
                self.md_login_status = getattr(self.ctp_gateway.md_api, 'login_status', False)
            
            if hasattr(self.ctp_gateway, 'td_api') and self.ctp_gateway.td_api:
                self.td_connected = getattr(self.ctp_gateway.td_api, 'connect_status', False)
                self.td_login_status = getattr(self.ctp_gateway.td_api, 'login_status', False)
                
        except Exception as e:
            logger.error(f"更新连接状态失败: {e}")
    
    def subscribe(self, symbol: str, exchange: str = "SHFE") -> bool:
        """
        订阅合约行情
        
        Args:
            symbol: 合约代码
            exchange: 交易所代码
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.md_connected or not self.md_login_status:
                logger.error("行情服务器未连接，无法订阅")
                return False
            
            # 创建订阅请求
            req = SubscribeRequest(
                symbol=symbol,
                exchange=Exchange.SHFE if exchange == "SHFE" else Exchange.SHFE
            )
            
            # 发送订阅请求
            self.ctp_gateway.subscribe(req)
            logger.info(f"订阅合约: {symbol}.{exchange}")
            return True
            
        except Exception as e:
            logger.error(f"订阅合约失败: {symbol}, 错误: {e}")
            return False
    
    def unsubscribe(self, symbol: str, exchange: str = "SHFE") -> bool:
        """
        取消订阅合约行情
        
        Args:
            symbol: 合约代码
            exchange: 交易所代码
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            # vnpy的CTP网关没有直接的取消订阅方法
            # 这里只是从本地缓存中移除
            vt_symbol = f"{symbol}.{exchange}"
            self.ticks.pop(vt_symbol, None)
            
            logger.info(f"取消订阅合约: {symbol}.{exchange}")
            return True
            
        except Exception as e:
            logger.error(f"取消订阅合约失败: {symbol}, 错误: {e}")
            return False
    
    def send_order(self, order_req: OrderRequest) -> Optional[str]:
        """
        发送订单
        
        Args:
            order_req: 订单请求
            
        Returns:
            Optional[str]: 订单引用号
        """
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法发送订单")
                return None
            
            # 转换为vnpy订单请求
            vnpy_req = VnpyOrderRequest(
                symbol=order_req.symbol,
                exchange=Exchange.SHFE,
                direction=order_req.direction,
                type=order_req.type,
                volume=order_req.volume,
                price=order_req.price,
                offset=order_req.offset,
                reference=order_req.reference
            )
            
            # 发送订单
            vt_orderid = self.ctp_gateway.send_order(vnpy_req)
            logger.info(f"发送订单: {order_req.symbol} {order_req.direction.value} {order_req.volume}@{order_req.price}")
            return vt_orderid
            
        except Exception as e:
            logger.error(f"发送订单失败: {e}")
            return None
    
    def cancel_order(self, vt_orderid: str) -> bool:
        """
        撤销订单
        
        Args:
            vt_orderid: vnpy订单ID
            
        Returns:
            bool: 撤销是否成功
        """
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法撤销订单")
                return False
            
            # 创建撤销请求
            req = CancelRequest(orderid=vt_orderid, symbol="", exchange=Exchange.SHFE)
            
            # 发送撤销请求
            self.ctp_gateway.cancel_order(req)
            logger.info(f"撤销订单: {vt_orderid}")
            return True
            
        except Exception as e:
            logger.error(f"撤销订单失败: {e}")
            return False
    
    def query_account(self) -> bool:
        """查询账户信息"""
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法查询账户")
                return False
            
            self.ctp_gateway.query_account()
            return True
            
        except Exception as e:
            logger.error(f"查询账户信息失败: {e}")
            return False
    
    def query_position(self) -> bool:
        """查询持仓信息"""
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法查询持仓")
                return False

            self.ctp_gateway.query_position()
            return True

        except Exception as e:
            logger.error(f"查询持仓信息失败: {e}")
            return False

    def query_history(self) -> bool:
        """查询历史数据（订单和成交）"""
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法查询历史数据")
                return False

            logger.info("开始查询历史订单和成交数据...")

            # 方法1: 尝试直接访问CTP API的查询方法
            try:
                # 获取CTP网关的td_api（交易API）
                if hasattr(self.ctp_gateway, 'td_api') and self.ctp_gateway.td_api:
                    td_api = self.ctp_gateway.td_api
                    logger.info("找到CTP交易API，尝试查询历史数据")

                    # 查询历史订单
                    if hasattr(td_api, 'reqQryOrder'):
                        logger.info("调用reqQryOrder查询历史订单")
                        # 创建查询请求结构
                        req = {}  # 空的查询请求，获取所有订单
                        td_api.reqQryOrder(req, self.get_next_request_id())
                        time.sleep(1)  # 避免查询过快

                    # 查询历史成交
                    if hasattr(td_api, 'reqQryTrade'):
                        logger.info("调用reqQryTrade查询历史成交")
                        req = {}  # 空的查询请求，获取所有成交
                        td_api.reqQryTrade(req, self.get_next_request_id())
                        time.sleep(1)

                    logger.info("历史数据查询请求已发送")
                    return True

            except Exception as e:
                logger.warning(f"直接API查询失败: {e}")

            # 方法2: 检查是否有其他查询方法
            logger.info("尝试其他查询方法...")

            # 在vnpy中，历史数据通常在连接后自动获取
            # 我们可以等待一段时间让数据自动加载
            logger.info("等待CTP自动加载历史数据...")
            time.sleep(3)

            # 检查是否已经有数据了
            orders_count = len(self.ctp_gateway.orders) if hasattr(self.ctp_gateway, 'orders') else 0
            trades_count = len(self.ctp_gateway.trades) if hasattr(self.ctp_gateway, 'trades') else 0

            logger.info(f"当前数据状态: 订单={orders_count}, 成交={trades_count}")

            return True

        except Exception as e:
            logger.error(f"查询历史数据失败: {e}")
            return False

    def get_next_request_id(self) -> int:
        """获取下一个请求ID"""
        if not hasattr(self, '_request_id'):
            self._request_id = 1
        else:
            self._request_id += 1
        return self._request_id

    def init_query(self) -> bool:
        """初始化查询（查询账户、持仓、历史数据）"""
        try:
            if not self.td_connected or not self.td_login_status:
                logger.error("交易服务器未连接，无法初始化查询")
                return False

            logger.info("开始初始化查询...")

            # 查询账户信息
            self.query_account()
            time.sleep(1)  # 避免查询过快

            # 查询持仓信息
            self.query_position()
            time.sleep(1)

            # 查询历史数据
            self.query_history()

            logger.info("初始化查询完成")
            return True

        except Exception as e:
            logger.error(f"初始化查询失败: {e}")
            return False

    # ========== 事件处理方法 ==========

    def _on_tick(self, event) -> None:
        """处理Tick事件"""
        try:
            tick: TickData = event.data

            # 缓存Tick数据
            self.ticks[tick.vt_symbol] = tick

            # 调用回调函数
            for callback in self.tick_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Tick回调函数执行失败: {e}")

            logger.debug(f"收到Tick: {tick.symbol} @ {tick.last_price}")

        except Exception as e:
            logger.error(f"处理Tick事件失败: {e}")

    def _on_order(self, event) -> None:
        """处理订单事件"""
        try:
            order: OrderData = event.data

            # 缓存订单数据
            self.orders[order.vt_orderid] = order

            # 调用回调函数
            for callback in self.order_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"订单回调函数执行失败: {e}")

            logger.debug(f"订单更新: {order.vt_orderid} {order.status.value}")

        except Exception as e:
            logger.error(f"处理订单事件失败: {e}")

    def _on_trade(self, event) -> None:
        """处理成交事件"""
        try:
            trade: TradeData = event.data

            # 缓存成交数据
            self.trades[trade.vt_tradeid] = trade

            # 调用回调函数
            for callback in self.trade_callbacks:
                try:
                    callback(trade)
                except Exception as e:
                    logger.error(f"成交回调函数执行失败: {e}")

            logger.info(f"成交通知: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")

        except Exception as e:
            logger.error(f"处理成交事件失败: {e}")

    def _on_account(self, event) -> None:
        """处理账户事件"""
        try:
            account: AccountData = event.data

            # 缓存账户数据
            self.account = account

            # 调用回调函数
            for callback in self.account_callbacks:
                try:
                    callback(account)
                except Exception as e:
                    logger.error(f"账户回调函数执行失败: {e}")

            logger.debug(f"账户更新: 可用资金 {account.available}")

        except Exception as e:
            logger.error(f"处理账户事件失败: {e}")

    def _on_position(self, event) -> None:
        """处理持仓事件"""
        try:
            position: PositionData = event.data

            # 缓存持仓数据
            self.positions[position.vt_positionid] = position

            # 调用回调函数
            for callback in self.position_callbacks:
                try:
                    callback(position)
                except Exception as e:
                    logger.error(f"持仓回调函数执行失败: {e}")

            logger.debug(f"持仓更新: {position.symbol} {position.direction.value} {position.volume}")

        except Exception as e:
            logger.error(f"处理持仓事件失败: {e}")

    def _on_contract(self, event) -> None:
        """处理合约事件"""
        try:
            contract: ContractData = event.data

            # 缓存合约数据
            self.contracts[contract.vt_symbol] = contract

            # 记录黄金合约
            if contract.symbol.startswith(("au", "AU")):
                logger.info(f"发现黄金合约: {contract.vt_symbol} - {contract.name}")

        except Exception as e:
            logger.error(f"处理合约事件失败: {e}")

    def _on_log(self, event) -> None:
        """处理日志事件"""
        try:
            log_data = event.data
            logger.debug(f"[CTP日志] {log_data}")

        except Exception as e:
            logger.error(f"处理日志事件失败: {e}")

    # ========== 回调函数管理 ==========

    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """添加Tick回调函数"""
        if callback not in self.tick_callbacks:
            self.tick_callbacks.append(callback)

    def add_order_callback(self, callback: Callable[[OrderData], None]) -> None:
        """添加订单回调函数"""
        if callback not in self.order_callbacks:
            self.order_callbacks.append(callback)

    def add_trade_callback(self, callback: Callable[[TradeData], None]) -> None:
        """添加成交回调函数"""
        if callback not in self.trade_callbacks:
            self.trade_callbacks.append(callback)

    def add_account_callback(self, callback: Callable[[AccountData], None]) -> None:
        """添加账户回调函数"""
        if callback not in self.account_callbacks:
            self.account_callbacks.append(callback)

    def add_position_callback(self, callback: Callable[[PositionData], None]) -> None:
        """添加持仓回调函数"""
        if callback not in self.position_callbacks:
            self.position_callbacks.append(callback)

    # ========== 状态查询方法 ==========

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.status == ServiceStatus.RUNNING

    def is_md_connected(self) -> bool:
        """检查行情服务器是否已连接"""
        self._update_connection_status()  # 实时更新状态
        return self.md_connected and self.md_login_status

    def is_td_connected(self) -> bool:
        """检查交易服务器是否已连接"""
        self._update_connection_status()  # 实时更新状态
        return self.td_connected and self.td_login_status

    def get_contracts(self) -> Dict[str, ContractData]:
        """获取所有合约"""
        return self.contracts.copy()

    def get_ticks(self) -> Dict[str, TickData]:
        """获取所有Tick数据"""
        return self.ticks.copy()

    def get_latest_tick(self, symbol: str, exchange: str = "SHFE") -> Optional[TickData]:
        """获取最新Tick数据"""
        vt_symbol = f"{symbol}.{exchange}"
        return self.ticks.get(vt_symbol)

    def get_status_info(self) -> Dict[str, any]:
        """获取状态信息"""
        return {
            'status': self.status.value,
            'md_connected': self.md_connected,
            'md_login_status': self.md_login_status,
            'td_connected': self.td_connected,
            'td_login_status': self.td_login_status,
            'contracts_count': len(self.contracts),
            'ticks_count': len(self.ticks),
            'orders_count': len(self.orders),
            'trades_count': len(self.trades),
            'positions_count': len(self.positions),
            'account_available': self.account.available if self.account else 0
        }
