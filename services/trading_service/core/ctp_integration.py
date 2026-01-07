"""
CTP网关集成模块
负责将CTP网关集成到trading_service中，提供真实的行情和交易功能
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from datetime import datetime, timedelta

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest, OrderRequest, CancelRequest
from vnpy.trader.constant import Exchange, Direction, OrderType, Offset
from vnpy.trader.event import EVENT_CONTRACT, EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_ACCOUNT, EVENT_POSITION

from utils.logger import get_logger
from config.config import get_main_contract_symbol, get_auto_subscribe_contracts
from shared.utils.trading_logger import get_trading_logger

logger = get_logger(__name__)

class CtpIntegration:
    """CTP网关集成类"""
    
    def __init__(self):
        """初始化CTP集成"""
        self.event_engine = None
        self.main_engine = None
        self.ctp_gateway = None
        self.config = None
        
        # 连接状态
        self.td_connected = False
        self.md_connected = False
        self.td_login_status = False
        self.md_login_status = False
        
        # 数据缓存
        self.contracts = {}
        self.ticks = {}
        self.orders = {}
        self.trades = {}
        self.positions = {}  # 持仓数据
        self.account = None
        
        # 回调函数
        self.tick_callbacks: list[Callable] = []
        self.order_callbacks: list[Callable] = []
        self.trade_callbacks: list[Callable] = []
        self.account_callbacks: list[Callable] = []


        
        # 运行状态
        self.running = False

        # 交易日志管理器
        self.trading_logger = get_trading_logger()
        self.current_strategy = None  # 当前运行的策略名称
        
    async def initialize(self) -> bool:
        """初始化CTP连接"""
        try:
            # 加载配置
            if not await self._load_config():
                return False
            
            # 创建引擎
            self.event_engine = EventEngine()
            self.main_engine = MainEngine(self.event_engine)
            
            # 添加CTP网关
            self.main_engine.add_gateway(CtpGateway, "CTP")
            self.ctp_gateway = self.main_engine.get_gateway("CTP")
            
            # 注册事件处理
            self._register_event_handlers()
            
            logger.info("✅ CTP集成初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ CTP集成初始化失败: {e}")
            return False
    
    async def _load_config(self) -> bool:
        """加载CTP配置"""
        try:
            config_file = Path("config/ctp_sim.json")
            if not config_file.exists():
                logger.error("CTP配置文件不存在: config/ctp_sim.json")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = json.load(f)
            
            # 转换为vnpy格式
            self.config = {
                "用户名": raw_config["用户名"],
                "密码": raw_config["密码"],
                "经纪商代码": raw_config["经纪商代码"],
                "交易服务器": f"tcp://{raw_config['交易服务器']}",
                "行情服务器": f"tcp://{raw_config['行情服务器']}",
                "产品名称": raw_config.get("产品名称", "simnow_client_test"),
                "授权编码": raw_config.get("授权编码", "0000000000000000")
            }
            
            logger.info(f"✅ CTP配置加载成功: {raw_config['用户名']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 加载CTP配置失败: {e}")
            return False
    
    def _register_event_handlers(self):
        """注册事件处理函数"""
        self.event_engine.register(EVENT_TICK, self._on_tick)
        self.event_engine.register(EVENT_ORDER, self._on_order)
        self.event_engine.register(EVENT_TRADE, self._on_trade)
        self.event_engine.register(EVENT_ACCOUNT, self._on_account)
        self.event_engine.register(EVENT_CONTRACT, self._on_contract)
        self.event_engine.register(EVENT_POSITION, self._on_position)
    
    async def connect(self) -> bool:
        """连接CTP服务器"""
        try:
            if not self.config:
                logger.error("CTP配置未加载")
                return False
            
            logger.info("🔄 开始连接CTP服务器...")
            
            # 连接CTP
            self.ctp_gateway.connect(self.config)
            
            # 等待连接建立
            for i in range(30):  # 等待30秒
                await asyncio.sleep(1)
                
                # 检查连接状态
                if hasattr(self.ctp_gateway, 'td_api'):
                    self.td_connected = getattr(self.ctp_gateway.td_api, 'connect_status', False)
                    self.td_login_status = getattr(self.ctp_gateway.td_api, 'login_status', False)
                
                if hasattr(self.ctp_gateway, 'md_api'):
                    self.md_connected = getattr(self.ctp_gateway.md_api, 'connect_status', False)
                    self.md_login_status = getattr(self.ctp_gateway.md_api, 'login_status', False)
                
                # 如果都连接成功，跳出循环
                if self.td_login_status and self.md_login_status:
                    break
                
                if i % 5 == 0:
                    logger.info(f"等待CTP连接... {i+1}/30")
            
            # 检查最终状态
            success = self.td_login_status and self.md_login_status
            
            if success:
                logger.info("✅ CTP连接成功")
                logger.info(f"  交易服务器: {'✓' if self.td_login_status else '✗'}")
                logger.info(f"  行情服务器: {'✓' if self.md_login_status else '✗'}")
                
                # 订阅主力合约
                await self._subscribe_main_contracts()
                
                self.running = True
                return True
            else:
                logger.error("❌ CTP连接失败")
                logger.error(f"  交易服务器: {'✓' if self.td_login_status else '✗'}")
                logger.error(f"  行情服务器: {'✓' if self.md_login_status else '✗'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ CTP连接异常: {e}")
            return False
    
    async def _subscribe_main_contracts(self):
        """订阅主力合约"""
        try:
            # 等待合约数据
            logger.info("等待合约数据...")
            await asyncio.sleep(5)

            # 获取所有合约
            all_contracts = self.main_engine.get_all_contracts()
            if not all_contracts:
                logger.warning("未收到合约数据，尝试手动订阅主力合约")
                # 手动订阅主力合约
                await self._manual_subscribe_main_contract()
                return

            # 优先使用配置文件中的主力合约
            main_symbol = get_main_contract_symbol()
            logger.info(f"配置文件中的主力合约: {main_symbol}")

            # 检查配置的主力合约是否在可用合约中
            target_contract = None
            for contract in all_contracts:
                if contract.symbol == main_symbol and contract.exchange == Exchange.SHFE:
                    target_contract = contract
                    break

            if target_contract:
                # 订阅配置文件中指定的主力合约
                req = SubscribeRequest(
                    symbol=target_contract.symbol,
                    exchange=target_contract.exchange
                )
                self.ctp_gateway.subscribe(req)
                logger.info(f"✅ 已订阅配置的主力合约: {target_contract.symbol}")
            else:
                # 如果配置的合约不可用，筛选黄金合约作为备选
                gold_contracts = [c for c in all_contracts if c.symbol.startswith("au") and c.exchange == Exchange.SHFE]

                if gold_contracts:
                    # 选择第一个可用的黄金合约作为备选
                    backup_contract = gold_contracts[0]
                    req = SubscribeRequest(
                        symbol=backup_contract.symbol,
                        exchange=backup_contract.exchange
                    )
                    self.ctp_gateway.subscribe(req)
                    logger.warning(f"⚠️ 配置的合约{main_symbol}不可用，使用备选合约: {backup_contract.symbol}")
                else:
                    logger.warning("未找到任何黄金合约，尝试手动订阅主力合约")
                    await self._manual_subscribe_main_contract()

        except Exception as e:
            logger.error(f"订阅合约失败: {e}")
            # 失败时也尝试手动订阅
            await self._manual_subscribe_main_contract()

    async def _manual_subscribe_main_contract(self):
        """手动订阅主力合约"""
        try:
            main_symbol = get_main_contract_symbol()
            logger.info(f"手动订阅主力合约: {main_symbol}...")
            req = SubscribeRequest(
                symbol=main_symbol,
                exchange=Exchange.SHFE
            )
            self.ctp_gateway.subscribe(req)
            logger.info(f"✅ 已手动订阅主力合约: {main_symbol}")

            # 等待行情数据
            await asyncio.sleep(3)
            if main_symbol in self.ticks:
                logger.info(f"✅ {main_symbol}行情数据接收成功")
            else:
                logger.warning(f"⚠️ {main_symbol}行情数据未收到，可能需要等待")

        except Exception as e:
            logger.error(f"手动订阅主力合约失败: {e}")
    
    def _on_tick(self, event):
        """处理行情数据"""
        tick = event.data

        # 📈 关键调试：验证tick回调是否被触发（每10秒打印一次，避免日志过多）
        current_time = time.time()
        if not hasattr(self, '_last_tick_log_time'):
            self._last_tick_log_time = 0

        if current_time - self._last_tick_log_time > 10:  # 每10秒打印一次
            logger.info(f"📈📈📈 [交易服务] CTP行情回调被触发！📈📈📈")
            logger.info(f"📈 [交易服务] 合约: {tick.symbol}")
            logger.info(f"📈 [交易服务] 最新价: {tick.last_price}")
            logger.info(f"📈 [交易服务] 买一价: {tick.bid_price_1}")
            logger.info(f"📈 [交易服务] 卖一价: {tick.ask_price_1}")
            logger.info(f"📈 [交易服务] 成交量: {tick.volume}")
            self._last_tick_log_time = current_time

        self.ticks[tick.symbol] = tick

        # 转换为标准格式
        tick_data = {
            'symbol': tick.symbol,
            'timestamp': time.time() * 1000,
            'last_price': tick.last_price,
            'volume': tick.volume,
            'bid_price': tick.bid_price_1,
            'ask_price': tick.ask_price_1,
            'bid_volume': tick.bid_volume_1,
            'ask_volume': tick.ask_volume_1,
            'high_price': tick.high_price,
            'low_price': tick.low_price,
            'open_price': tick.open_price
        }

        # 🔌 WebSocket 推送 tick 数据
        self._ws_push_tick(tick_data)

        # 调用回调函数
        for callback in self.tick_callbacks:
            try:
                callback(tick_data)
            except Exception as e:
                logger.error(f"行情回调执行失败: {e}")
    
    def _on_order(self, event):
        """处理订单更新"""
        order = event.data

        # 🔥 关键调试：验证订单回调是否被触发
        logger.info(f"📋📋📋 [交易服务] CTP订单回调被触发！📋📋📋")
        logger.info(f"📋 [交易服务] 订单ID: {order.orderid}")
        logger.info(f"📋 [交易服务] 合约: {getattr(order, 'symbol', 'N/A')}")
        logger.info(f"📋 [交易服务] 状态: {getattr(order, 'status', 'N/A')}")
        logger.info(f"📋 [交易服务] 方向: {getattr(order, 'direction', 'N/A')}")
        logger.info(f"📋 [交易服务] 数量: {getattr(order, 'volume', 'N/A')}")
        logger.info(f"📋 [交易服务] 已成交: {getattr(order, 'traded', 'N/A')}")

        # 🚨 如果订单被拒绝，记录详细错误信息
        if hasattr(order, 'status') and str(order.status) == 'Status.REJECTED':
            logger.error(f"🚨 订单被拒绝详情:")
            logger.error(f"   订单ID: {getattr(order, 'orderid', 'N/A')}")
            logger.error(f"   订单引用: {getattr(order, 'reference', 'N/A')}")
            logger.error(f"   合约代码: {getattr(order, 'symbol', 'N/A')}")
            logger.error(f"   买卖方向: {getattr(order, 'direction', 'N/A')}")
            logger.error(f"   订单类型: {getattr(order, 'type', 'N/A')}")
            logger.error(f"   开平仓: {getattr(order, 'offset', 'N/A')}")
            logger.error(f"   订单价格: {getattr(order, 'price', 'N/A')}")
            logger.error(f"   订单数量: {getattr(order, 'volume', 'N/A')}")
            logger.error(f"   状态消息: {getattr(order, 'msg', 'N/A')}")

            # 尝试获取CTP特有的错误信息
            if hasattr(order, 'gateway_name'):
                logger.error(f"   网关: {order.gateway_name}")
            if hasattr(order, 'status_msg'):
                logger.error(f"   CTP状态消息: {order.status_msg}")
            if hasattr(order, 'error_id'):
                logger.error(f"   CTP错误ID: {order.error_id}")
            if hasattr(order, 'error_msg'):
                logger.error(f"   CTP错误消息: {order.error_msg}")
            if hasattr(order, 'datetime'):
                logger.error(f"   时间: {order.datetime}")

            # 记录所有可用属性（用于调试）
            all_attrs = [attr for attr in dir(order) if not attr.startswith('_') and not callable(getattr(order, attr))]
            logger.error(f"   可用属性: {all_attrs}")

            # 尝试记录属性值
            for attr in ['InsertTime', 'UpdateTime', 'CancelTime', 'StatusMsg', 'ErrorID', 'ErrorMsg']:
                if hasattr(order, attr):
                    logger.error(f"   {attr}: {getattr(order, attr)}")

            # 检查extra字段中的错误信息
            if hasattr(order, 'extra') and order.extra:
                logger.error(f"   Extra信息: {order.extra}")
                # 如果extra是字典，尝试获取错误信息
                if isinstance(order.extra, dict):
                    for key, value in order.extra.items():
                        if 'error' in key.lower() or 'msg' in key.lower():
                            logger.error(f"   {key}: {value}")

        self.orders[order.orderid] = order

        # 🔌 WebSocket 推送订单数据
        order_data = {
            'order_id': order.orderid,
            'symbol': getattr(order, 'symbol', ''),
            'direction': getattr(order, 'direction', '').value if hasattr(getattr(order, 'direction', ''), 'value') else str(getattr(order, 'direction', '')),
            'offset': getattr(order, 'offset', '').value if hasattr(getattr(order, 'offset', ''), 'value') else str(getattr(order, 'offset', '')),
            'status': getattr(order, 'status', '').value if hasattr(getattr(order, 'status', ''), 'value') else str(getattr(order, 'status', '')),
            'volume': getattr(order, 'volume', 0),
            'traded': getattr(order, 'traded', 0),
            'price': getattr(order, 'price', 0),
            'datetime': str(getattr(order, 'datetime', ''))
        }
        self._ws_push_order(order_data)

        # 调用回调函数
        for callback in self.order_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"订单回调执行失败: {e}")

        logger.info(f"📋📋📋 [交易服务] CTP订单回调处理完成！📋📋📋")
    
    def _on_trade(self, event):
        """处理成交回报"""
        trade = event.data

        # 🔥 关键调试：验证成交回调是否被触发
        logger.info(f"🔥🔥🔥 [交易服务] CTP成交回调被触发！🔥🔥🔥")
        logger.info(f"🔥 [交易服务] 成交ID: {trade.tradeid}")
        logger.info(f"🔥 [交易服务] 订单ID: {getattr(trade, 'orderid', 'N/A')}")
        logger.info(f"🔥 [交易服务] 合约: {getattr(trade, 'symbol', 'N/A')}")
        logger.info(f"🔥 [交易服务] 方向: {getattr(trade, 'direction', 'N/A')}")
        logger.info(f"🔥 [交易服务] 数量: {getattr(trade, 'volume', 'N/A')}")
        logger.info(f"🔥 [交易服务] 价格: {getattr(trade, 'price', 'N/A')}")

        # 存储成交数据
        self.trades[trade.tradeid] = trade
        logger.info(f"🔥 [交易服务] 成交数据已存储，当前总成交数: {len(self.trades)}")

        # 🔌 WebSocket 推送成交数据
        direction_val = getattr(trade, 'direction', '')
        offset_val = getattr(trade, 'offset', '')
        direction_str = direction_val.value if hasattr(direction_val, 'value') else str(direction_val)
        offset_str = offset_val.value if hasattr(offset_val, 'value') else str(offset_val)

        logger.info(f"🔥 [成交详情] direction={direction_val}({direction_str}) offset={offset_val}({offset_str})")

        trade_data = {
            'trade_id': trade.tradeid,
            'order_id': getattr(trade, 'orderid', ''),
            'symbol': getattr(trade, 'symbol', ''),
            'direction': direction_str,
            'offset': offset_str,
            'volume': getattr(trade, 'volume', 0),
            'price': getattr(trade, 'price', 0),
            'datetime': str(getattr(trade, 'datetime', ''))
        }
        self._ws_push_trade(trade_data)

        # 调用回调函数
        for callback in self.trade_callbacks:
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"成交回调执行失败: {e}")

        logger.info(f"🔥🔥🔥 [交易服务] CTP成交回调处理完成！🔥🔥🔥")
    
    def _on_account(self, event):
        """处理账户更新"""
        account = event.data
        self.account = account
        
        # 调用回调函数
        for callback in self.account_callbacks:
            try:
                callback(account)
            except Exception as e:
                logger.error(f"账户回调执行失败: {e}")
    
    def _on_contract(self, event):
        """处理合约信息"""
        contract = event.data
        self.contracts[contract.symbol] = contract

    def _on_position(self, event):
        """处理持仓更新 - 仅缓存CTP原始持仓数据，均价计算由策略服务处理"""
        position = event.data
        position_key = f"{position.symbol}_{position.direction.value}"
        self.positions[position_key] = position
        logger.debug(f"📍 [持仓缓存] {position.symbol} {position.direction.value}: {position.volume}手(昨{position.yd_volume})")

    def refresh_positions(self):
        """主动刷新持仓数据 - 从CTP网关重新查询

        关键：清空缓存后重新查询，确保获取最新的今昨仓数据
        特别是跨越结算时间（15:00-21:00）后，今仓会变成昨仓
        """
        try:
            if not self.td_connected or not self.td_login_status:
                logger.warning("⚠️ 交易服务器未连接，无法刷新持仓")
                return False

            # 🔧 关键：清空旧的缓存数据，强制使用CTP返回的最新数据
            old_positions = self.positions.copy()
            self.positions.clear()

            logger.info("🔄 [持仓刷新] 清空缓存，主动查询CTP持仓数据...")
            self.ctp_gateway.query_position()

            # 等待CTP返回数据（最多等待2秒）
            import time
            max_wait = 2.0
            wait_interval = 0.1
            waited = 0

            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval
                if len(self.positions) > 0:
                    break

            if len(self.positions) == 0 and len(old_positions) > 0:
                # 如果没有收到新数据，恢复旧数据（可能是无持仓）
                logger.warning(f"⚠️ [持仓刷新] 未收到CTP数据，可能无持仓")

            logger.info(f"✅ [持仓刷新] 完成，当前持仓数: {len(self.positions)}")
            return True

        except Exception as e:
            logger.error(f"❌ [持仓刷新] 失败: {e}")
            return False
    
    def _round_price(self, symbol: str, price: float) -> float:
        """根据合约的最小变动单位调整价格精度"""
        try:
            # 获取合约信息
            if symbol in self.contracts:
                contract = self.contracts[symbol]
                pricetick = contract.pricetick
                if pricetick > 0:
                    # 将价格调整为最小变动单位的倍数
                    return round(price / pricetick) * pricetick

            # 默认精度处理（黄金期货通常是0.02）
            if symbol.startswith('au'):
                return round(price / 0.02) * 0.02
            else:
                return round(price, 2)

        except Exception as e:
            logger.warning(f"价格精度调整失败: {e}, 使用原价格: {price}")
            return price

    def send_order(self, symbol: str, direction: str, volume: int, price: float = 0, order_type: str = "MARKET", offset: str = "OPEN", time_condition: str = "GFD") -> Optional[str]:
        """
        发送订单

        Args:
            symbol: 合约代码
            direction: 买卖方向 (BUY/SELL)
            volume: 数量
            price: 价格
            order_type: 订单类型 (MARKET/LIMIT)
            offset: 开平仓 (OPEN/CLOSE/AUTO)
            time_condition: 订单有效期类型
                - "GFD": Good For Day - 当日有效 (使用激进价格确保立即成交)
                - "GFD": 当日有效
                - "GFS": 本节有效

        Returns:
            Optional[str]: 订单ID
        """
        try:
            if not self.td_login_status:
                logger.error("交易服务器未连接，无法发送订单")
                return None

            # 转换方向
            vnpy_direction = Direction.LONG if direction.upper() == 'BUY' else Direction.SHORT

            # 转换订单类型 - CTP只支持限价单，所有订单都用限价单
            vnpy_order_type = OrderType.LIMIT

            if order_type == "MARKET":
                # 市价单用限价单模拟，使用对手价确保立即成交
                if symbol in self.ticks:
                    tick = self.ticks[symbol]
                    current_price = tick.last_price
                    if direction == "BUY":
                        # 买单使用卖一价，确保立即成交
                        if tick.ask_price_1 > 0:
                            order_price = tick.ask_price_1
                        else:
                            # 如果没有卖一价，使用当前价格+0.2%
                            order_price = current_price * 1.002
                    else:
                        # 卖单使用买一价，确保立即成交
                        if tick.bid_price_1 > 0:
                            order_price = tick.bid_price_1
                        else:
                            # 如果没有买一价，使用当前价格-0.2%
                            order_price = current_price * 0.998

                    # 价格精度调整到最小变动价位
                    order_price = round(order_price, 2)  # 黄金精度到分

                    logger.info(f"市价单转限价单: {symbol} {direction} 当前价={current_price}, 买一价={tick.bid_price_1}, 卖一价={tick.ask_price_1}, 最终价格={order_price}")
                else:
                    # 如果没有行情数据，使用传入的价格或合理默认价格
                    order_price = price if price > 0 else 800.0
                    logger.warning(f"无行情数据，使用价格: {order_price}")
            else:
                # 限价单直接使用传入价格
                order_price = price

            # 转换开平仓类型
            vnpy_offset = self._convert_offset(offset.upper(), symbol, direction)

            # 调整价格精度
            order_price = self._round_price(symbol, order_price)

            # 根据time_condition选择价格策略（保留条件判断便于后续调试）
            logger.info(f"🔍 订单类型: time_condition='{time_condition}'")

            # 确定使用的价格和订单引用
            if time_condition.upper() == "GFD":
                # GFD订单：使用激进价格确保立即成交
                final_price = self._calculate_aggressive_price(symbol, vnpy_direction, order_price)
                if final_price is None:
                    final_price = order_price
                order_reference = f"GFD_AGG_{int(time.time())}"  # 激进价格GFD订单
                logger.info(f"🚀 发送GFD订单(激进价格): {symbol} {direction} {volume}@{final_price} ({offset})")
            else:
                # 其他time_condition：使用用户指定价格（便于调试其他订单类型）
                final_price = order_price
                order_reference = f"ARBIG_{int(time.time())}"  # 标准订单
                logger.info(f"🚀 发送标准订单: {symbol} {direction} {volume}@{final_price} ({offset}) [{time_condition}]")

            # 统一发送GFD订单（所有订单都是GFD类型）
            req = OrderRequest(
                symbol=symbol,
                exchange=Exchange.SHFE,
                direction=vnpy_direction,
                type=vnpy_order_type,  # 都是限价单
                volume=volume,
                price=final_price,
                offset=vnpy_offset,
                reference=order_reference
            )

            # 发送订单前检查网关状态
            logger.info(f"🔍 发送订单前检查: td_login_status={self.td_login_status}, ctp_gateway={self.ctp_gateway is not None}")

            order_id = self.ctp_gateway.send_order(req)

            logger.info(f"🔍 CTP网关返回订单ID: {order_id}")

            if order_id:
                logger.info(f"✅ 订单发送成功: {symbol} {direction} {volume}@{order_price} ({offset}) [订单ID: {order_id}]")

                # 记录订单日志
                self.trading_logger.log_order(
                    strategy_name=self.current_strategy or "MANUAL",
                    symbol=symbol,
                    direction=direction,
                    offset=offset,
                    volume=volume,
                    price=order_price,
                    order_id=order_id,
                    message=f"订单发送成功: {direction} {volume}手@{order_price}",
                    details={
                        'order_type': order_type,
                        'original_price': price,
                        'final_price': order_price
                    },
                    is_success=True
                )

                return order_id
            else:
                logger.error(f"❌ 订单发送失败: {symbol} {direction} {volume}@{order_price} ({offset})")

                # 记录失败日志
                self.trading_logger.log_order(
                    strategy_name=self.current_strategy or "MANUAL",
                    symbol=symbol,
                    direction=direction,
                    offset=offset,
                    volume=volume,
                    price=order_price,
                    order_id="",
                    message=f"订单发送失败: {direction} {volume}手@{order_price}",
                    is_success=False,
                    error_code="ORDER_SEND_FAILED",
                    error_message="CTP网关返回空订单ID"
                )

                return None

        except Exception as e:
            logger.error(f"发送订单异常: {e}")

            # 记录异常日志
            self.trading_logger.log_error(
                strategy_name=self.current_strategy or "MANUAL",
                error_type="ORDER_EXCEPTION",
                error_message=str(e),
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'volume': volume,
                    'price': price,
                    'offset': offset
                },
                symbol=symbol
            )

            return None

    def set_current_strategy(self, strategy_name: str):
        """设置当前运行的策略名称"""
        self.current_strategy = strategy_name
        logger.info(f"设置当前策略: {strategy_name}")



    def _get_tick_size(self, symbol: str) -> float:
        """
        获取合约的最小变动价位

        Args:
            symbol: 合约代码

        Returns:
            float: 最小变动价位
        """
        # 根据合约类型返回最小变动价位
        if symbol.startswith('au'):  # 黄金期货
            return 0.02
        elif symbol.startswith('ag'):  # 白银期货
            return 1.0
        elif symbol.startswith('cu'):  # 铜期货
            return 10.0
        elif symbol.startswith('al'):  # 铝期货
            return 5.0
        elif symbol.startswith('zn'):  # 锌期货
            return 5.0
        elif symbol.startswith('pb'):  # 铅期货
            return 5.0
        elif symbol.startswith('ni'):  # 镍期货
            return 10.0
        elif symbol.startswith('sn'):  # 锡期货
            return 10.0
        else:
            # 默认最小变动价位
            return 0.01

    def _calculate_aggressive_price(self, symbol: str, direction: Direction, fallback_price: float) -> Optional[float]:
        """
        计算激进价格 - 确保GFD订单立即成交
        买单使用卖一价+最小变动价位，卖单使用买一价-最小变动价位

        Args:
            symbol: 合约代码
            direction: 买卖方向
            fallback_price: 备用价格

        Returns:
            Optional[float]: 激进价格，None表示无法计算
        """
        try:
            # 获取当前行情
            tick = self.ticks.get(symbol)
            if not tick:
                logger.warning(f"❌ 无法获取{symbol}的行情数据，使用备用价格")
                return self._round_price(symbol, fallback_price)

            # 获取合约的最小变动价位
            tick_size = self._get_tick_size(symbol)
            aggressive_price = None

            # 根据方向计算激进价格
            if direction == Direction.LONG:
                # 买入：优先使用卖一价，确保立即成交
                if hasattr(tick, 'ask_price_1') and tick.ask_price_1 > 0:
                    aggressive_price = tick.ask_price_1 + tick_size  # 增加一个最小变动价位确保成交
                    logger.info(f"🎯 激进买入价: 卖一价({tick.ask_price_1})+{tick_size} = {aggressive_price}")
                elif hasattr(tick, 'last_price') and tick.last_price > 0:
                    # 如果没有卖一价，使用最新价+2个最小变动价位
                    aggressive_price = tick.last_price + (tick_size * 2)
                    logger.info(f"🎯 激进买入价: 最新价({tick.last_price})+{tick_size * 2} = {aggressive_price}")
            else:
                # 卖出：优先使用买一价，确保立即成交
                if hasattr(tick, 'bid_price_1') and tick.bid_price_1 > 0:
                    aggressive_price = tick.bid_price_1 - tick_size  # 减少一个最小变动价位确保成交
                    logger.info(f"🎯 激进卖出价: 买一价({tick.bid_price_1})-{tick_size} = {aggressive_price}")
                elif hasattr(tick, 'last_price') and tick.last_price > 0:
                    # 如果没有买一价，使用最新价-2个最小变动价位
                    aggressive_price = tick.last_price - (tick_size * 2)
                    logger.info(f"🎯 激进卖出价: 最新价({tick.last_price})-{tick_size * 2} = {aggressive_price}")

            # 如果计算出了价格，进行精度调整
            if aggressive_price is not None:
                aggressive_price = self._round_price(symbol, aggressive_price)
                return aggressive_price
            else:
                # 无法计算激进价格，使用备用价格
                logger.warning(f"❌ 无法计算{symbol}的激进价格，使用备用价格: {fallback_price}")
                return self._round_price(symbol, fallback_price)

        except Exception as e:
            logger.error(f"计算激进价格失败: {e}")
            return self._round_price(symbol, fallback_price)

    def _send_standard_order(self, symbol: str, direction: Direction, offset: Offset, volume: int, price: float) -> Optional[str]:
        """发送标准订单（GFD）"""
        try:
            req = OrderRequest(
                symbol=symbol,
                exchange=Exchange.SHFE,
                direction=direction,
                type=OrderType.LIMIT,
                volume=volume,
                price=price,
                offset=offset,
                reference=f"ARBIG_{int(time.time())}"
            )

            return self.ctp_gateway.send_order(req)

        except Exception as e:
            logger.error(f"发送标准订单失败: {e}")
            return None

    def _get_ctp_offset_flag(self, offset: Offset) -> str:
        """转换vnpy的Offset为CTP的开平仓标志"""
        if offset == Offset.OPEN:
            return '0'  # 开仓
        elif offset == Offset.CLOSE:
            return '1'  # 平仓
        elif offset == Offset.CLOSETODAY:
            return '3'  # 平今
        elif offset == Offset.CLOSEYESTERDAY:
            return '4'  # 平昨
        else:
            return '0'  # 默认开仓

    def _get_request_id(self) -> int:
        """获取请求ID"""
        if not hasattr(self, '_request_id'):
            self._request_id = 1
        else:
            self._request_id += 1
        return self._request_id

    def _convert_offset(self, offset: str, symbol: str = None, direction: str = None) -> Offset:
        """转换开平仓类型 - 上海期货交易所需要区分平今平昨"""
        # 处理AUTO：智能判断开平仓
        if offset == 'AUTO':
            # AUTO应该是平仓，使用智能平仓逻辑
            result = self._smart_close_offset(symbol, direction)
            logger.info(f"开平仓转换: {offset} -> {result} (智能平仓)")
            return result

        offset_map = {
            'OPEN': Offset.OPEN,
            'CLOSE': self._smart_close_offset(symbol, direction),  # 修改：使用智能平仓逻辑
            'CLOSE_TODAY': Offset.CLOSETODAY,
            'CLOSE_YESTERDAY': Offset.CLOSEYESTERDAY,
            'CLOSETODAY': Offset.CLOSETODAY,  # 添加：支持CLOSETODAY格式
            'CLOSEYESTERDAY': Offset.CLOSEYESTERDAY  # 添加：支持CLOSEYESTERDAY格式
        }
        result = offset_map.get(offset, Offset.OPEN)
        logger.info(f"开平仓转换: {offset} -> {result}")
        return result

    def _smart_close_offset(self, symbol: str = None, direction: str = None) -> Offset:
        """智能判断平今仓还是平昨仓 - 优先平昨仓（更稳定），再平今仓"""
        if not symbol or not direction:
            logger.warning("⚠️ 缺少合约或方向信息，使用默认平昨仓")
            return Offset.CLOSEYESTERDAY

        try:
            # 根据交易方向确定要查询的持仓方向
            if direction.upper() == "BUY":
                # 买入平仓 = 平空仓
                position_direction = "SHORT"
                action_desc = "平空仓"
            elif direction.upper() == "SELL":
                # 卖出平仓 = 平多仓
                position_direction = "LONG"
                action_desc = "平多仓"
            else:
                logger.warning(f"⚠️ 未知交易方向: {direction}，使用默认平昨仓")
                return Offset.CLOSEYESTERDAY

            # 查询对应方向持仓的今昨仓详情
            position_detail = self.get_position_detail(symbol, position_direction)
            if not position_detail:
                logger.warning(f"⚠️ {symbol} 无法获取{position_direction}持仓详情，使用默认平昨仓")
                return Offset.CLOSEYESTERDAY

            today_pos = position_detail.today_position
            yesterday_pos = position_detail.yesterday_position

            logger.info(f"🔍 {action_desc}分析: {symbol} {position_direction} 今仓{today_pos}手, 昨仓{yesterday_pos}手")

            # 🔧 修改策略：优先平昨仓（更稳定，不受时间限制），再平今仓
            # 原因：平今仓在某些时段可能被交易所拒绝（如夜盘某些时段）
            if yesterday_pos > 0:
                logger.info(f"✅ 优先平昨仓: {symbol} {position_direction} 昨仓{yesterday_pos}手（更稳定）")
                return Offset.CLOSEYESTERDAY
            elif today_pos > 0:
                logger.info(f"✅ 平今仓: {symbol} {position_direction} 今仓{today_pos}手（备选方案）")
                return Offset.CLOSETODAY
            else:
                logger.warning(f"⚠️ {symbol} {position_direction} 无持仓可平，使用默认平昨仓")
                return Offset.CLOSEYESTERDAY

        except Exception as e:
            logger.error(f"⚠️ 智能平仓判断异常: {e}")
            return Offset.CLOSEYESTERDAY

    def _calculate_total_margin(self) -> float:
        """计算总保证金"""
        total_margin = 0.0

        # 尝试从vnpy持仓对象获取实际保证金
        for position in self.positions.values():
            if hasattr(position, 'volume') and position.volume > 0:
                # 检查各种可能的保证金字段
                margin_fields = ['margin', 'frozen', 'margin_used', 'position_margin', 'use_margin']
                for field in margin_fields:
                    if hasattr(position, field):
                        value = getattr(position, field)
                        if field in ['margin', 'frozen', 'margin_used', 'position_margin', 'use_margin'] and value > 0:
                            total_margin += value

        # 如果没有找到保证金字段，使用计算方式
        if total_margin == 0:
            positions_info = self.get_position_info()
            if isinstance(positions_info, dict):
                for symbol, pos_info in positions_info.items():
                    if isinstance(pos_info, dict):
                        long_pos = pos_info.get('long_position', 0)
                        short_pos = pos_info.get('short_position', 0)
                        total_volume = long_pos + short_pos

                        if total_volume > 0:
                            # 获取当前价格
                            current_price = 775.0  # 默认价格
                            if symbol in self.ticks:
                                current_price = self.ticks[symbol].last_price

                            # 根据实际情况调整保证金率
                            # 217117.60 / (2手 × 777价格 × 1000) = 0.1397 ≈ 13.97%
                            contract_value = current_price * 1000  # 每手合约价值
                            margin_rate = 0.1397  # 13.97%保证金率（根据实际数据调整）
                            position_margin = contract_value * margin_rate * total_volume
                            total_margin += position_margin

        return round(total_margin, 2)

    def _calculate_close_profit(self) -> float:
        """计算平仓盈亏（从CTP账户数据获取）"""
        # 直接从CTP账户数据获取平仓盈亏
        if hasattr(self, 'account_data') and self.account_data:
            # CTP账户数据中的CloseProfit字段就是平仓盈亏
            close_profit = self.account_data.get('close_profit', 0.0)
            if close_profit != 0:
                return float(close_profit)

        # 如果CTP没有提供，尝试从成交记录计算
        return self._calculate_realized_pnl_from_trades()

    def _calculate_commission(self) -> float:
        """计算手续费（开仓2元/手，平仓0元/手）"""
        # 优先从CTP账户数据获取手续费
        if hasattr(self, 'account_data') and self.account_data:
            commission = self.account_data.get('commission', 0.0)
            if commission != 0:
                return float(commission)

        # 如果CTP没有提供，根据实际规则计算
        total_commission = 0.0

        # 从成交记录计算手续费
        for trade in self.trades.values():
            if hasattr(trade, 'commission'):
                # 如果成交记录中有手续费字段，直接使用
                total_commission += float(getattr(trade, 'commission', 0))
            elif hasattr(trade, 'volume') and hasattr(trade, 'offset'):
                # 根据开平仓类型计算手续费
                volume = trade.volume
                offset_str = str(trade.offset).upper()

                if 'OPEN' in offset_str:
                    # 开仓手续费：2元/手
                    total_commission += volume * 2.0
                else:
                    # 平仓手续费：0元/手
                    total_commission += volume * 0.0

        return total_commission

    def _calculate_realized_pnl_from_trades(self) -> float:
        """从成交记录计算已实现盈亏"""
        realized_pnl = 0.0

        # 简化的盈亏计算：配对开平仓交易
        open_trades = {}  # 存储开仓交易 {symbol_direction: [trades]}

        for trade in self.trades.values():
            if not hasattr(trade, 'symbol') or not hasattr(trade, 'offset'):
                continue

            symbol = trade.symbol
            offset_str = str(trade.offset).upper()
            direction = str(getattr(trade, 'direction', '')).upper()
            volume = getattr(trade, 'volume', 0)
            price = getattr(trade, 'price', 0)

            if 'OPEN' in offset_str:
                # 开仓交易
                key = f"{symbol}_{direction}"
                if key not in open_trades:
                    open_trades[key] = []
                open_trades[key].append({
                    'volume': volume,
                    'price': price,
                    'direction': direction
                })
            elif 'CLOSE' in offset_str:
                # 平仓交易，计算盈亏
                # 平仓方向与开仓方向相反
                open_direction = 'LONG' if 'SELL' in direction else 'SHORT'
                key = f"{symbol}_{open_direction}"

                if key in open_trades and open_trades[key]:
                    # 找到对应的开仓交易计算盈亏
                    open_trade = open_trades[key].pop(0)  # FIFO

                    # 如果成交记录中有盈亏字段，直接使用
                    if hasattr(trade, 'pnl'):
                        realized_pnl += float(getattr(trade, 'pnl', 0))
                    else:
                        # 否则根据价格差计算（使用实际的合约信息）
                        price_diff = price - open_trade['price']
                        if open_direction == 'SHORT':
                            price_diff = -price_diff  # 空单盈亏相反

                        # 从合约信息获取合约乘数，如果没有则使用默认值
                        contract_size = self._get_contract_size(symbol)
                        pnl = price_diff * min(volume, open_trade['volume']) * contract_size
                        realized_pnl += pnl

        return realized_pnl

    def _get_contract_size(self, symbol: str) -> float:
        """获取合约乘数（从CTP合约信息获取）"""
        # 从CTP合约信息获取
        if symbol in self.contracts:
            contract = self.contracts[symbol]
            if hasattr(contract, 'size'):
                return float(contract.size)

        # 根据合约代码推断（黄金期货通常是1000克/手）
        if symbol.startswith('au'):
            return 1000.0  # 黄金期货
        elif symbol.startswith('ag'):
            return 15000.0  # 白银期货
        else:
            return 1.0  # 默认值

    def _calculate_daily_pnl(self) -> float:
        """计算当日盈亏"""
        # 从持仓盈亏 + 平仓盈亏计算
        total_pnl = 0
        for position in self.positions.values():
            if hasattr(position, 'pnl'):
                total_pnl += position.pnl
        return total_pnl

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        try:
            if not self.td_login_status:
                logger.error("交易服务器未连接，无法撤销订单")
                return False
            
            # 创建撤销请求
            req = CancelRequest(
                orderid=order_id,
                symbol="",  # vnpy会自动填充
                exchange=Exchange.SHFE
            )
            
            # 发送撤销请求
            self.ctp_gateway.cancel_order(req)
            logger.info(f"✅ 撤销订单: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"撤销订单异常: {e}")
            return False
    
    def get_latest_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取最新行情"""
        tick = self.ticks.get(symbol)
        if not tick:
            return None
        
        return {
            'symbol': tick.symbol,
            'timestamp': time.time() * 1000,
            'last_price': tick.last_price,
            'volume': tick.volume,
            'bid_price': tick.bid_price_1,
            'ask_price': tick.ask_price_1,
            'bid_volume': tick.bid_volume_1,
            'ask_volume': tick.ask_volume_1,
            'high_price': tick.high_price,
            'low_price': tick.low_price,
            'open_price': tick.open_price
        }

    def get_trades_by_strategy(self, strategy_name: str, since_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取成交数据（交易服务不做任何过滤，返回所有原始数据）"""
        trades = []

        logger.info(f"🔍 [交易服务] 查询成交数据，CTP总成交数: {len(self.trades)}")

        for trade_id, trade in self.trades.items():
            try:
                # 🔧 交易服务只负责数据转换，不做任何业务逻辑过滤
                order_id = getattr(trade, 'orderid', '') or getattr(trade, 'orderref', '')

                # 构造标准格式的成交数据
                trade_data = {
                    'trade_id': trade_id,
                    'order_id': order_id,
                    'symbol': getattr(trade, 'symbol', ''),
                    'direction': str(getattr(trade, 'direction', '')).upper(),
                    'offset': str(getattr(trade, 'offset', 'OPEN')).upper(),
                    'price': float(getattr(trade, 'price', 0.0)),
                    'volume': int(getattr(trade, 'volume', 0)),
                    'datetime': datetime.now().isoformat(),  # 简化时间处理
                }

                trades.append(trade_data)
                logger.debug(f"🔍 [交易服务] 成交数据: {trade_id} -> 订单ID: {order_id}")

            except Exception as e:
                logger.warning(f"[交易服务] 处理成交数据失败: {e}")
                continue

        logger.info(f"🔍 [交易服务] 返回 {len(trades)} 笔成交数据")
        return trades

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        if not self.account:
            return None

        # 基础账户信息（从CTP实际可用字段获取）
        balance = getattr(self.account, 'balance', 0)
        available = getattr(self.account, 'available', 0)
        frozen = getattr(self.account, 'frozen', 0)

        # 检查是否有风险度相关字段
        risk_fields = ['risk_ratio', 'risk_degree', 'margin_ratio', 'risk_rate']
        ctp_risk_ratio = 0
        for field in risk_fields:
            if hasattr(self.account, field):
                value = getattr(self.account, field)
                if field in ['risk_ratio', 'risk_degree', 'risk_rate'] and value > 0:
                    ctp_risk_ratio = value

        # 计算保证金（从持仓计算）
        margin = self._calculate_total_margin()

        # 计算缺失字段（CTP不直接提供）
        commission = self._calculate_commission()  # 从成交记录动态计算手续费

        # 优先使用精确的已实现盈亏，否则使用估算
        realized_pnl = self._calculate_realized_pnl_from_trades()
        if abs(realized_pnl) < 10:  # 如果计算结果很小，使用估算方法
            close_profit = self._calculate_close_profit()
        else:
            close_profit = realized_pnl

        pre_balance = balance - self._calculate_daily_pnl()  # 估算昨日余额

        # 计算衍生指标
        total_assets = balance + close_profit  # 总资产
        net_assets = balance - margin  # 净资产

        # 风险度：优先使用CTP提供的，否则自己计算
        if ctp_risk_ratio > 0:
            risk_ratio = ctp_risk_ratio * 100  # CTP可能返回小数形式
        else:
            risk_ratio = (margin / balance * 100) if balance > 0 else 0  # 自己计算

        margin_ratio = (margin / available * 100) if available > 0 else 0  # 保证金率
        daily_pnl = balance - pre_balance  # 当日盈亏

        # 计算可开仓手数（基于实际保证金需求）
        avg_margin_per_lot = 62000  # 黄金期货每手约6.2万保证金
        available_lots = int(available / avg_margin_per_lot) if available > 0 else 0

        # 计算持仓相关信息
        position_value = 0.0  # 持仓市值
        position_pnl = 0.0   # 持仓盈亏（未实现盈亏）

        # 从持仓数据计算
        for symbol, position in self.positions.items():
            if hasattr(position, 'volume') and position.volume > 0:
                # 持仓市值
                current_price = 775.0  # 默认价格
                if position.symbol in self.ticks:
                    current_price = self.ticks[position.symbol].last_price
                pos_value = position.volume * current_price * 1000  # 每手1000克
                position_value += pos_value

                # 持仓盈亏
                position_pnl += getattr(position, 'pnl', 0)

        return {
            # 基础信息
            'accountid': getattr(self.account, 'accountid', 'CTP_ACCOUNT'),
            'balance': round(balance, 2),
            'available': round(available, 2),
            'margin': round(margin, 2),
            'commission': round(commission, 2),
            'close_profit': round(close_profit, 2),
            'frozen': round(frozen, 2),
            'pre_balance': round(pre_balance, 2),

            # 衍生指标
            'total_assets': round(total_assets, 2),
            'net_assets': round(net_assets, 2),
            'risk_ratio': round(risk_ratio, 2),
            'margin_ratio': round(margin_ratio, 2),
            'daily_pnl': round(daily_pnl, 2),
            'available_lots': available_lots,

            # 持仓相关
            'position_value': round(position_value, 2),
            'position_pnl': round(position_pnl, 2),      # 持仓盈亏（原未实现盈亏）
            'close_pnl': round(close_profit, 2),         # 平仓盈亏（原已实现盈亏）
            'total_pnl': round(position_pnl + close_profit, 2),  # 总盈亏

            # 兼容旧字段名
            'unrealized_pnl': round(position_pnl, 2),    # 兼容：未实现盈亏 -> 持仓盈亏
            'realized_pnl': round(close_profit, 2),      # 兼容：已实现盈亏 -> 平仓盈亏

            # 其他信息
            'currency': 'CNY',
            'gateway_name': getattr(self.account, 'gateway_name', 'CTP'),
            'update_time': datetime.now().isoformat()
        }

    def get_position_info(self, symbol: str = None) -> Dict[str, Any]:
        """获取持仓信息"""
        if symbol:
            # 获取指定合约的持仓（处理大小写问题）
            long_key = f"{symbol}_Long"  # vnpy使用首字母大写
            short_key = f"{symbol}_Short"

            long_pos = self.positions.get(long_key)
            short_pos = self.positions.get(short_key)

            # vnpy 已计算盈亏
            long_pnl = long_pos.pnl if long_pos else 0
            short_pnl = short_pos.pnl if short_pos else 0

            # 获取今昨仓信息
            long_today = 0
            long_yesterday = 0
            short_today = 0
            short_yesterday = 0

            if long_pos:
                long_yd_volume = getattr(long_pos, 'yd_volume', 0)
                long_yesterday = long_yd_volume
                long_today = max(0, long_pos.volume - long_yd_volume)

            if short_pos:
                short_yd_volume = getattr(short_pos, 'yd_volume', 0)
                short_yesterday = short_yd_volume
                short_today = max(0, short_pos.volume - short_yd_volume)

            return {
                'symbol': symbol,
                'long_position': long_pos.volume if long_pos else 0,
                'short_position': short_pos.volume if short_pos else 0,
                'net_position': (long_pos.volume if long_pos else 0) - (short_pos.volume if short_pos else 0),
                'long_price': long_pos.price if long_pos else 0,
                'short_price': short_pos.price if short_pos else 0,
                'long_pnl': long_pnl,
                'short_pnl': short_pnl,
                'total_pnl': long_pnl + short_pnl,
                # 今昨仓详细信息
                'long_today': long_today,
                'long_yesterday': long_yesterday,
                'short_today': short_today,
                'short_yesterday': short_yesterday,
                'position_detail': {
                    'long': {
                        'total': long_pos.volume if long_pos else 0,
                        'today': long_today,
                        'yesterday': long_yesterday
                    },
                    'short': {
                        'total': short_pos.volume if short_pos else 0,
                        'today': short_today,
                        'yesterday': short_yesterday
                    }
                }
            }
        else:
            # 获取所有持仓
            positions = {}
            for key, position in self.positions.items():
                symbol = position.symbol
                if symbol not in positions:
                    positions[symbol] = {
                        'symbol': symbol,
                        'long_position': 0,
                        'short_position': 0,
                        'net_position': 0,
                        'long_price': 0,
                        'short_price': 0,
                        'long_today': 0,
                        'long_yesterday': 0,
                        'short_today': 0,
                        'short_yesterday': 0,
                        'position_detail': {
                            'long': {'total': 0, 'today': 0, 'yesterday': 0},
                            'short': {'total': 0, 'today': 0, 'yesterday': 0}
                        }
                    }

                # 处理方向值的大小写问题
                direction = position.direction.value.upper()
                yd_volume = getattr(position, 'yd_volume', 0)
                today_volume = max(0, position.volume - yd_volume)

                if direction == 'LONG':
                    positions[symbol]['long_position'] = position.volume
                    positions[symbol]['long_price'] = position.price
                    positions[symbol]['long_today'] = today_volume
                    positions[symbol]['long_yesterday'] = yd_volume
                    positions[symbol]['position_detail']['long'] = {
                        'total': position.volume,
                        'today': today_volume,
                        'yesterday': yd_volume
                    }
                elif direction == 'SHORT':
                    positions[symbol]['short_position'] = position.volume
                    positions[symbol]['short_price'] = position.price
                    positions[symbol]['short_today'] = today_volume
                    positions[symbol]['short_yesterday'] = yd_volume
                    positions[symbol]['position_detail']['short'] = {
                        'total': position.volume,
                        'today': today_volume,
                        'yesterday': yd_volume
                    }

                # 获取当前行情价格
                if symbol in self.ticks:
                    positions[symbol]['current_price'] = self.ticks[symbol].last_price
                else:
                    positions[symbol]['current_price'] = 0

                positions[symbol]['net_position'] = positions[symbol]['long_position'] - positions[symbol]['short_position']

                # 直接使用vnpy计算的盈亏数据
                long_pnl = 0
                short_pnl = 0

                # 查找对应的持仓对象获取盈亏
                long_key = f"{symbol}_Long"
                short_key = f"{symbol}_Short"

                if long_key in self.positions:
                    long_pnl = self.positions[long_key].pnl

                if short_key in self.positions:
                    short_pnl = self.positions[short_key].pnl

                positions[symbol]['long_pnl'] = long_pnl
                positions[symbol]['short_pnl'] = short_pnl
                positions[symbol]['total_pnl'] = long_pnl + short_pnl

            return positions

    def get_position_detail(self, symbol: str, direction: str):
        """获取仓位详情，包含今昨仓信息

        直接使用CTP返回的yd_volume（昨仓数量），不做任何自己的计算
        """
        try:
            # 🔧 关键：在查询前主动刷新持仓数据，确保获取最新数据
            self.refresh_positions()

            # 查找对应的持仓记录
            direction_key = f"{symbol}_{direction.title()}"  # 如 "au2510_Long"

            if direction_key in self.positions:
                position = self.positions[direction_key]

                # 创建仓位详情对象
                class PositionDetail:
                    def __init__(self, position):
                        self.symbol = position.symbol
                        self.direction = position.direction
                        self.volume = position.volume
                        self.price = position.price

                        # 🎯 直接使用CTP返回的yd_volume，不做任何自己的计算
                        # CTP的yd_volume就是昨仓数量，今仓 = 总持仓 - 昨仓
                        yd_volume = getattr(position, 'yd_volume', 0)

                        self.yesterday_position = int(yd_volume)
                        self.today_position = int(position.volume - yd_volume)

                        logger.info(f"🔍 [持仓详情] {position.symbol} {position.direction.value}: "
                                   f"总持仓={position.volume}手, 今仓={self.today_position}手, 昨仓={self.yesterday_position}手")

                return PositionDetail(position)

            return None

        except Exception as e:
            logger.error(f"获取仓位详情失败: {e}")
            return None

    def get_smart_offset(self, symbol: str, direction: str) -> str:
        """智能判断开平仓类型 - 禁用智能平仓，允许双向持仓"""
        position_info = self.get_position_info(symbol)

        logger.info(f"开平仓判断: {symbol} {direction}, 多头持仓={position_info['long_position']}, 空头持仓={position_info['short_position']}")
        logger.info(f"禁用智能平仓，允许双向持仓，总是开仓")

        # 总是开仓，允许双向持仓
        return 'OPEN'

    def get_historical_data(self, symbol: str, interval: str = "1m", count: int = 100):
        """获取历史K线数据"""
        try:
            from vnpy.trader.constant import Interval
            from vnpy.trader.object import HistoryRequest
            from datetime import datetime, timedelta

            # 转换时间周期
            interval_map = {
                "1m": Interval.MINUTE,
                "5m": Interval.MINUTE * 5,
                "15m": Interval.MINUTE * 15,
                "30m": Interval.MINUTE * 30,
                "1h": Interval.HOUR,
                "1d": Interval.DAILY
            }

            vnpy_interval = interval_map.get(interval, Interval.MINUTE)

            # 计算开始时间
            end_time = datetime.now()
            if interval == "1d":
                start_time = end_time - timedelta(days=count + 10)
            elif interval == "1h":
                start_time = end_time - timedelta(hours=count + 24)
            else:
                start_time = end_time - timedelta(minutes=count * 5 + 60)

            # 创建历史数据请求
            req = HistoryRequest(
                symbol=symbol,
                exchange=self.contracts[symbol].exchange if symbol in self.contracts else None,
                start=start_time,
                end=end_time,
                interval=vnpy_interval
            )

            # 获取历史数据
            if hasattr(self.main_engine, 'query_history'):
                bars = self.main_engine.query_history(req, self.gateway_name)

                # 转换为标准格式
                historical_data = []
                for bar in bars[-count:]:  # 只返回请求的数量
                    historical_data.append({
                        'symbol': bar.symbol,
                        'datetime': bar.datetime.isoformat(),
                        'open': bar.open_price,
                        'high': bar.high_price,
                        'low': bar.low_price,
                        'close': bar.close_price,
                        'volume': bar.volume,
                        'interval': interval
                    })

                logger.info(f"获取历史数据成功: {symbol} {interval} {len(historical_data)}条")
                return historical_data
            else:
                logger.warning("CTP网关不支持历史数据查询")
                return []

        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
            return []

    def get_simulated_historical_data(self, symbol: str, interval: str = "1m", count: int = 100):
        """生成模拟历史数据用于回测（当CTP历史数据不可用时）"""
        try:
            import random
            from datetime import datetime, timedelta

            # 获取当前价格作为基准
            current_price = 775.0  # 默认黄金价格
            if symbol in self.ticks:
                current_price = self.ticks[symbol].last_price

            # 生成模拟数据
            historical_data = []
            base_time = datetime.now() - timedelta(minutes=count)

            for i in range(count):
                # 模拟价格波动
                price_change = random.uniform(-0.5, 0.5)  # ±0.5%的波动
                open_price = current_price * (1 + price_change / 100)

                high_price = open_price * (1 + random.uniform(0, 0.3) / 100)
                low_price = open_price * (1 - random.uniform(0, 0.3) / 100)
                close_price = open_price + random.uniform(-0.2, 0.2)

                volume = random.randint(10, 100)

                bar_time = base_time + timedelta(minutes=i)

                historical_data.append({
                    'symbol': symbol,
                    'datetime': bar_time.isoformat(),
                    'open': round(open_price, 2),
                    'high': round(high_price, 2),
                    'low': round(low_price, 2),
                    'close': round(close_price, 2),
                    'volume': volume,
                    'interval': interval
                })

                # 更新基准价格
                current_price = close_price

            logger.info(f"生成模拟历史数据: {symbol} {interval} {len(historical_data)}条")
            return historical_data

        except Exception as e:
            logger.error(f"生成模拟历史数据失败: {e}")
            return []
    
    def add_tick_callback(self, callback: Callable):
        """添加行情回调"""
        self.tick_callbacks.append(callback)

    def add_order_callback(self, callback: Callable):
        """添加订单回调"""
        self.order_callbacks.append(callback)

    def add_trade_callback(self, callback: Callable):
        """添加成交回调"""
        self.trade_callbacks.append(callback)

    def add_account_callback(self, callback: Callable):
        """添加账户回调"""
        self.account_callbacks.append(callback)

    # ==================== WebSocket 推送方法 ====================

    def _ws_push_tick(self, tick_data: Dict[str, Any]):
        """通过 WebSocket 推送 tick 数据"""
        try:
            from services.trading_service.api.websocket_api import get_trading_ws_manager
            import asyncio

            ws_manager = get_trading_ws_manager()
            if ws_manager.active_connections:
                # 在事件循环中调度异步推送
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(ws_manager.push_tick(tick_data))
                    else:
                        loop.run_until_complete(ws_manager.push_tick(tick_data))
                except RuntimeError:
                    # 没有事件循环，创建新的
                    asyncio.run(ws_manager.push_tick(tick_data))
            else:
                # 每10秒打印一次无连接提示
                current_time = time.time()
                if not hasattr(self, '_last_ws_no_conn_log'):
                    self._last_ws_no_conn_log = 0
                if current_time - self._last_ws_no_conn_log > 10:
                    logger.debug(f"🔌 [WS] 无活跃连接，跳过tick推送")
                    self._last_ws_no_conn_log = current_time
        except Exception as e:
            logger.error(f"🔌 [WS] tick推送异常: {e}")

    def _ws_push_order(self, order_data: Dict[str, Any]):
        """通过 WebSocket 推送订单数据"""
        try:
            from services.trading_service.api.websocket_api import get_trading_ws_manager
            import asyncio

            ws_manager = get_trading_ws_manager()
            logger.info(f"🔌 [WebSocket] 推送订单数据: {order_data.get('order_id')}")

            if ws_manager.active_connections:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(ws_manager.push_order(order_data))
                    else:
                        loop.run_until_complete(ws_manager.push_order(order_data))
                except RuntimeError:
                    asyncio.run(ws_manager.push_order(order_data))
            else:
                logger.debug(f"🔌 [WebSocket] 无连接，跳过订单推送")
        except Exception as e:
            logger.error(f"🔌 [WebSocket] 推送订单失败: {e}")

    def _ws_push_trade(self, trade_data: Dict[str, Any]):
        """通过 WebSocket 推送成交数据"""
        try:
            from services.trading_service.api.websocket_api import get_trading_ws_manager
            import asyncio

            ws_manager = get_trading_ws_manager()
            logger.info(f"🔌 [WebSocket] 推送成交数据: {trade_data.get('trade_id')}")

            if ws_manager.active_connections:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(ws_manager.push_trade(trade_data))
                    else:
                        loop.run_until_complete(ws_manager.push_trade(trade_data))
                except RuntimeError:
                    asyncio.run(ws_manager.push_trade(trade_data))
            else:
                logger.debug(f"🔌 [WebSocket] 无连接，跳过成交推送")
        except Exception as e:
            logger.error(f"🔌 [WebSocket] 推送成交失败: {e}")
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """获取所有订单信息"""
        orders = []
        for order_id, order in self.orders.items():
            try:
                order_data = {
                    'order_id': order_id,
                    'symbol': getattr(order, 'symbol', 'N/A'),
                    'direction': getattr(order, 'direction', 'N/A'),
                    'volume': getattr(order, 'volume', 0),
                    'price': getattr(order, 'price', 0.0),
                    'traded': getattr(order, 'traded', 0),
                    'status': str(getattr(order, 'status', 'N/A')),
                    'type': str(getattr(order, 'type', 'N/A')),
                    'offset': str(getattr(order, 'offset', 'N/A')),
                    'reference': getattr(order, 'reference', 'N/A'),
                    'datetime': getattr(order, 'datetime', None),
                    'msg': getattr(order, 'msg', 'N/A')
                }
                orders.append(order_data)
            except Exception as e:
                logger.error(f"处理订单数据失败: {e}")
                continue

        return orders

    def get_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            'running': self.running,
            'td_connected': self.td_connected,
            'md_connected': self.md_connected,
            'td_login_status': self.td_login_status,
            'md_login_status': self.md_login_status,
            'contracts_count': len(self.contracts),
            'subscribed_symbols': list(self.ticks.keys()),
            'orders_count': len(self.orders),
            'trades_count': len(self.trades)
        }
    
    async def disconnect(self):
        """断开CTP连接"""
        try:
            self.running = False
            
            if self.ctp_gateway:
                self.ctp_gateway.close()
            
            if self.main_engine:
                self.main_engine.close()
            
            logger.info("✅ CTP连接已断开")
            
        except Exception as e:
            logger.error(f"断开CTP连接异常: {e}")

# 全局实例
_ctp_integration = None

def get_ctp_integration() -> CtpIntegration:
    """获取CTP集成实例"""
    global _ctp_integration
    if _ctp_integration is None:
        _ctp_integration = CtpIntegration()
    return _ctp_integration
