"""
CTP网关集成模块
负责将CTP网关集成到trading_service中，提供真实的行情和交易功能
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest, OrderRequest, CancelRequest
from vnpy.trader.constant import Exchange, Direction, OrderType, Offset
from vnpy.trader.event import EVENT_CONTRACT, EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_ACCOUNT, EVENT_POSITION

from utils.logger import get_logger
from config.config import get_main_contract_symbol, get_auto_subscribe_contracts

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
        
        # 调用回调函数
        for callback in self.tick_callbacks:
            try:
                callback(tick_data)
            except Exception as e:
                logger.error(f"行情回调执行失败: {e}")
    
    def _on_order(self, event):
        """处理订单更新"""
        order = event.data
        self.orders[order.orderid] = order
        
        # 调用回调函数
        for callback in self.order_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"订单回调执行失败: {e}")
    
    def _on_trade(self, event):
        """处理成交回报"""
        trade = event.data
        self.trades[trade.tradeid] = trade
        
        # 调用回调函数
        for callback in self.trade_callbacks:
            try:
                callback(trade)
            except Exception as e:
                logger.error(f"成交回调执行失败: {e}")
    
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
        """处理持仓更新"""
        position = event.data
        position_key = f"{position.symbol}_{position.direction.value}"
        self.positions[position_key] = position
    
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

    def send_order(self, symbol: str, direction: str, volume: int, price: float = 0, order_type: str = "MARKET", offset: str = "OPEN") -> Optional[str]:
        """发送订单"""
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
            vnpy_offset = self._convert_offset(offset.upper())

            # 调整价格精度
            order_price = self._round_price(symbol, order_price)

            req = OrderRequest(
                symbol=symbol,
                exchange=Exchange.SHFE,
                direction=vnpy_direction,
                type=vnpy_order_type,
                volume=volume,
                price=order_price,
                offset=vnpy_offset,
                reference=f"ARBIG_{int(time.time())}"
            )
            
            # 发送订单
            order_id = self.ctp_gateway.send_order(req)
            
            if order_id:
                logger.info(f"✅ 订单发送成功: {symbol} {direction} {volume}@{order_price} ({offset}) [订单ID: {order_id}]")
                return order_id
            else:
                logger.error(f"❌ 订单发送失败: {symbol} {direction} {volume}@{order_price} ({offset})")
                return None

        except Exception as e:
            logger.error(f"发送订单异常: {e}")
            return None

    def _convert_offset(self, offset: str) -> Offset:
        """转换开平仓类型 - 上海期货交易所需要区分平今平昨"""
        offset_map = {
            'OPEN': Offset.OPEN,
            'CLOSE': Offset.CLOSETODAY,  # 修改：SHFE默认使用平今仓
            'CLOSE_TODAY': Offset.CLOSETODAY,
            'CLOSE_YESTERDAY': Offset.CLOSEYESTERDAY
        }
        result = offset_map.get(offset, Offset.OPEN)
        logger.info(f"开平仓转换: {offset} -> {result}")
        return result
    
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
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        if not self.account:
            return None

        # 基础账户信息
        balance = getattr(self.account, 'balance', 0)
        available = getattr(self.account, 'available', 0)
        margin = getattr(self.account, 'margin', 0)
        commission = getattr(self.account, 'commission', 0)
        close_profit = getattr(self.account, 'close_profit', 0)
        frozen = getattr(self.account, 'frozen', 0)
        pre_balance = getattr(self.account, 'pre_balance', 0)

        # 计算衍生指标
        total_assets = balance + close_profit  # 总资产
        net_assets = balance - margin  # 净资产
        risk_ratio = (margin / balance * 100) if balance > 0 else 0  # 风险度
        margin_ratio = (margin / available * 100) if available > 0 else 0  # 保证金率
        daily_pnl = balance - pre_balance  # 当日盈亏

        # 计算可开仓手数（假设每手保证金10000元）
        margin_per_lot = 10000
        available_lots = int(available / margin_per_lot) if available > 0 else 0

        # 计算持仓相关信息
        position_value = 0  # 持仓市值
        unrealized_pnl = 0  # 未实现盈亏

        # 从持仓数据计算
        for symbol, position in self.positions.items():
            if hasattr(position, 'volume') and position.volume > 0:
                pos_value = getattr(position, 'volume', 0) * getattr(position, 'price', 0)
                position_value += pos_value
                unrealized_pnl += getattr(position, 'pnl', 0)

        return {
            # 基础信息
            'accountid': getattr(self.account, 'accountid', 'CTP_ACCOUNT'),
            'balance': balance,
            'available': available,
            'margin': margin,
            'commission': commission,
            'close_profit': close_profit,
            'frozen': frozen,
            'pre_balance': pre_balance,

            # 衍生指标
            'total_assets': total_assets,
            'net_assets': net_assets,
            'risk_ratio': round(risk_ratio, 2),
            'margin_ratio': round(margin_ratio, 2),
            'daily_pnl': daily_pnl,
            'available_lots': available_lots,

            # 持仓相关
            'position_value': position_value,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': close_profit,  # 已实现盈亏

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

            # 调试日志
            logger.info(f"查询持仓 {symbol}: long_key={long_key}, short_key={short_key}")
            logger.info(f"持仓数据: long_pos={long_pos is not None}, short_pos={short_pos is not None}")
            if long_pos:
                logger.info(f"多单: volume={long_pos.volume}, price={long_pos.price}")
            if short_pos:
                logger.info(f"空单: volume={short_pos.volume}, price={short_pos.price}")

            # 获取当前行情价格 - 直接从ticks字典获取
            current_price = 0
            if symbol in self.ticks:
                current_price = self.ticks[symbol].last_price

            # 直接使用vnpy计算的盈亏数据
            long_pnl = long_pos.pnl if long_pos else 0
            short_pnl = short_pos.pnl if short_pos else 0

            return {
                'symbol': symbol,
                'long_position': long_pos.volume if long_pos else 0,
                'short_position': short_pos.volume if short_pos else 0,
                'net_position': (long_pos.volume if long_pos else 0) - (short_pos.volume if short_pos else 0),
                'long_price': long_pos.price if long_pos else 0,
                'short_price': short_pos.price if short_pos else 0,
                'current_price': current_price,
                'long_pnl': long_pnl,
                'short_pnl': short_pnl,
                'total_pnl': long_pnl + short_pnl
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
                        'short_price': 0
                    }

                # 处理方向值的大小写问题
                direction = position.direction.value.upper()
                if direction == 'LONG':
                    positions[symbol]['long_position'] = position.volume
                    positions[symbol]['long_price'] = position.price
                elif direction == 'SHORT':
                    positions[symbol]['short_position'] = position.volume
                    positions[symbol]['short_price'] = position.price

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

    def get_smart_offset(self, symbol: str, direction: str) -> str:
        """智能判断开平仓类型 - 禁用智能平仓，允许双向持仓"""
        position_info = self.get_position_info(symbol)

        logger.info(f"开平仓判断: {symbol} {direction}, 多头持仓={position_info['long_position']}, 空头持仓={position_info['short_position']}")
        logger.info(f"禁用智能平仓，允许双向持仓，总是开仓")

        # 总是开仓，允许双向持仓
        return 'OPEN'
    
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
