"""
CTP仿真网关
提供CTP仿真环境的交易和行情接口
"""

import os
import sys
import time
from typing import Dict, Optional, List, Callable
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 添加CTP库路径
lib_path = os.path.join(project_root, 'libs', 'ctp_sim')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

try:
    from vnpy_ctp import CtpGateway
except ImportError:
    print("警告: 无法导入vnpy_ctp，请确保已正确安装CTP仿真库")
    CtpGateway = None

try:
    from vnpy.event import EventEngine
except ImportError:
    print("警告: 无法导入vnpy.event，请确保已正确安装vnpy")
    EventEngine = None

from vnpy.trader.object import TickData, OrderData, TradeData, PositionData, SubscribeRequest
from vnpy.trader.constant import Exchange, Direction, Offset, OrderType

from utils.logger import get_logger
from .config import CtpConfig

logger = get_logger(__name__)

class CtpWrapper:
    """
    CTP网关包装类，用于连接CTP交易环境
    """
    
    def __init__(self, config: CtpConfig = None):
        """
        初始化CTP网关包装
        
        Args:
            config: CTP配置对象，如果为None则使用默认配置
        """
        # 检查EventEngine是否可用
        if EventEngine is None:
            raise ImportError("EventEngine未正确导入，请确保vnpy.event模块已安装")
        
        # 检查CtpGateway是否可用
        if CtpGateway is None:
            raise ImportError("CtpGateway未正确导入，请确保vnpy_ctp模块已安装")
        
        self.event_engine = EventEngine()
        self.config = config or CtpConfig()
        self.gateway: Optional[CtpGateway] = None
        self.connected = False
        self.trading_connected = False
        self.market_connected = False
        
        # 数据回调函数
        self.on_tick: Optional[Callable] = None
        self.on_order: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_position: Optional[Callable] = None
        
        # 数据缓存
        self.ticks: Dict[str, TickData] = {}
        self.orders: Dict[str, OrderData] = {}
        self.trades: Dict[str, TradeData] = {}
        self.positions: Dict[str, PositionData] = {}
        
        # 验证配置
        try:
            self.config.validate_config()
        except Exception as e:
            logger.error(f"CTP仿真配置验证失败: {str(e)}")
            raise
            
    def connect(self) -> bool:
        """
        连接CTP仿真环境
        
        Returns:
            bool: 连接是否成功
        """
        try:
            if not CtpGateway or not EventEngine:
                logger.error("CTP Gateway或EventEngine未正确加载")
                return False
                
            # 创建事件引擎
            self.event_engine.start()
                
            # 获取配置
            trading_config = self.config.get_trading_config()
            market_config = self.config.get_market_config()
            
            # 创建完整的配置（包含交易和行情信息）
            full_config = {
                "用户名": trading_config.get("用户名"),
                "密码": trading_config.get("密码"),
                "经纪商代码": trading_config.get("经纪商代码"),
                "交易服务器": trading_config.get("交易服务器"),
                "行情服务器": market_config.get("行情服务器"),
                "产品名称": trading_config.get("产品名称"),
                "授权编码": trading_config.get("授权编码")
            }
            print("[DEBUG] full_config:", full_config)
            
            # 创建CTP Gateway
            self.gateway = CtpGateway(self.event_engine, "CTP_SIM")
            
            # 设置回调函数
            self.gateway.on_tick = self._on_tick
            self.gateway.on_order = self._on_order
            self.gateway.on_trade = self._on_trade
            self.gateway.on_position = self._on_position
            
            # 连接CTP服务器（同时连接交易和行情）
            logger.info("正在连接CTP仿真交易服务器...")
            self.gateway.connect(full_config)
            
            # 等待连接完成
            for _ in range(15):  # 最多等待15秒
                if self.gateway.td_api.connect_status:
                    self.trading_connected = True
                    logger.info("CTP仿真交易服务器连接成功")
                    break
                time.sleep(1)
                
            if not self.trading_connected:
                logger.error("CTP仿真交易服务器连接超时")
                return False
                
            # 等待行情连接完成
            for _ in range(10):  # 最多等待10秒
                if self.gateway.md_api.connect_status:
                    self.market_connected = True
                    logger.info("CTP仿真行情服务器连接成功")
                    break
                time.sleep(1)
                
            if not self.market_connected:
                logger.warning("CTP仿真行情服务器连接失败，但交易功能可用")
                
            self.connected = self.trading_connected
            return self.connected
            
        except Exception as e:
            logger.error(f"连接CTP仿真环境失败: {str(e)}")
            return False
            
    def subscribe(self, symbols: List[str]) -> bool:
        """
        订阅合约行情
        
        Args:
            symbols: 合约代码列表，如 ["AU2406", "AU2412"]
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.connected:
                logger.error("CTP仿真环境未连接")
                return False
                
            if not self.market_connected:
                logger.error("CTP仿真行情服务器未连接")
                return False
                
            # 订阅合约
            for symbol in symbols:
                # 创建 SubscribeRequest 对象
                req = SubscribeRequest(
                    symbol=symbol,
                    exchange=Exchange.SHFE
                )
                self.gateway.subscribe(req)
                logger.info(f"订阅合约 {symbol} 成功")
                
            return True
            
        except Exception as e:
            logger.error(f"订阅合约失败: {str(e)}")
            return False
            
    def send_order(self, symbol: str, direction: Direction, offset: Offset, 
                   volume: float, price: float = 0.0, order_type: OrderType = OrderType.LIMIT) -> str:
        """
        发送订单
        
        Args:
            symbol: 合约代码
            direction: 买卖方向
            offset: 开平方向
            volume: 数量
            price: 价格，市价单为0
            order_type: 订单类型
            
        Returns:
            str: 订单ID
        """
        try:
            if not self.connected:
                logger.error("CTP仿真环境未连接")
                return ""
                
            if not self.trading_connected:
                logger.error("CTP仿真交易服务器未连接")
                return ""
                
            # 发送订单
            order_id = self.gateway.send_order(symbol, direction, offset, volume, price, order_type)
            logger.info(f"发送订单成功: {symbol} {direction.value} {offset.value} {volume}@{price}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"发送订单失败: {str(e)}")
            return ""
            
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 撤销是否成功
        """
        try:
            if not self.connected:
                logger.error("CTP仿真环境未连接")
                return False
                
            # 撤销订单
            self.gateway.cancel_order(order_id)
            logger.info(f"撤销订单成功: {order_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"撤销订单失败: {str(e)}")
            return False
            
    def get_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取合约最新行情
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[TickData]: 最新行情数据
        """
        return self.ticks.get(symbol)
        
    def get_position(self, symbol: str) -> Optional[PositionData]:
        """
        获取合约持仓
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[PositionData]: 持仓数据
        """
        return self.positions.get(symbol)
        
    def get_all_positions(self) -> Dict[str, PositionData]:
        """
        获取所有持仓
        
        Returns:
            Dict: 所有持仓数据
        """
        return self.positions.copy()
        
    def disconnect(self):
        """
        断开CTP仿真环境连接
        """
        try:
            if self.gateway:
                self.gateway.close()
                
            if self.event_engine:
                self.event_engine.stop()
                
            self.connected = False
            self.trading_connected = False
            self.market_connected = False
            logger.info("CTP仿真环境已断开")
                
        except Exception as e:
            logger.error(f"断开CTP仿真环境失败: {str(e)}")
            
    def _on_tick(self, tick: TickData):
        """
        Tick数据回调
        """
        try:
            logger.info(f"收到Tick数据: {tick.symbol} 最新价: {tick.last_price}")
            self.ticks[tick.symbol] = tick
            if self.on_tick:
                self.on_tick(tick)
                
        except Exception as e:
            logger.error(f"处理Tick数据失败: {str(e)}")
            
    def _on_order(self, order: OrderData):
        """
        订单数据回调
        """
        try:
            self.orders[order.orderid] = order
            if self.on_order:
                self.on_order(order)
                
        except Exception as e:
            logger.error(f"处理订单数据失败: {str(e)}")
            
    def _on_trade(self, trade: TradeData):
        """
        成交数据回调
        """
        try:
            self.trades[trade.tradeid] = trade
            if self.on_trade:
                self.on_trade(trade)
                
        except Exception as e:
            logger.error(f"处理成交数据失败: {str(e)}")
            
    def _on_position(self, position: PositionData):
        """
        持仓数据回调
        """
        try:
            key = f"{position.symbol}_{position.direction.value}"
            self.positions[key] = position
            if self.on_position:
                self.on_position(position)
                
        except Exception as e:
            logger.error(f"处理持仓数据失败: {str(e)}") 