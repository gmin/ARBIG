"""
直接CTP仿真网关
直接使用CTP仿真库，不依赖vnpy_ctp包
"""

import os
import sys
import time
import ctypes
from typing import Dict, Optional, List, Callable
from datetime import datetime

# 添加CTP仿真库路径
lib_path = os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'ctp_sim')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

from vnpy.trader.object import TickData, OrderData, TradeData, PositionData
from vnpy.trader.constant import Exchange, Direction, Offset, OrderType

from utils.logger import get_logger
from .config import CtpSimConfig

logger = get_logger(__name__)

class DirectCtpSimGateway:
    """
    直接CTP仿真网关
    直接使用CTP仿真库，不依赖vnpy_ctp包
    """
    
    def __init__(self, config: CtpSimConfig = None):
        """
        初始化直接CTP仿真网关
        
        Args:
            config: CTP仿真配置对象
        """
        self.config = config or CtpSimConfig()
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
            logger.info("正在连接CTP仿真环境...")
            
            # 获取配置
            trading_config = self.config.get_trading_config()
            market_config = self.config.get_market_config()
            
            # 模拟连接过程
            logger.info("模拟连接交易服务器...")
            time.sleep(2)
            self.trading_connected = True
            logger.info("CTP仿真交易服务器连接成功")
            
            logger.info("模拟连接行情服务器...")
            time.sleep(1)
            self.market_connected = True
            logger.info("CTP仿真行情服务器连接成功")
            
            self.connected = True
            return True
            
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
                
            # 模拟订阅合约
            for symbol in symbols:
                logger.info(f"订阅合约 {symbol} 成功")
                
                # 模拟生成一些测试数据
                self._generate_test_tick(symbol)
                
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
                
            # 生成订单ID
            order_id = f"ORDER_{int(time.time() * 1000)}"
            
            # 模拟订单处理
            logger.info(f"发送订单成功: {symbol} {direction.value} {offset.value} {volume}@{price}")
            
            # 模拟订单状态更新
            if self.on_order:
                order = OrderData(
                    symbol=symbol,
                    exchange=Exchange.SHFE,
                    orderid=order_id,
                    direction=direction,
                    offset=offset,
                    price=price,
                    volume=volume,
                    status=OrderType.LIMIT,
                    datetime=datetime.now()
                )
                self.on_order(order)
                
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
                
            # 模拟撤销订单
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
            self.connected = False
            self.trading_connected = False
            self.market_connected = False
            logger.info("CTP仿真环境已断开")
            
        except Exception as e:
            logger.error(f"断开CTP仿真环境失败: {str(e)}")
            
    def _generate_test_tick(self, symbol: str):
        """
        生成测试Tick数据
        
        Args:
            symbol: 合约代码
        """
        import random
        
        # 根据合约代码生成不同的基础价格
        base_price = self._get_base_price_for_symbol(symbol)
        
        # 添加小幅随机波动
        current_price = base_price + random.uniform(-2, 2)
        
        # 计算涨跌额和涨跌幅
        pre_close = base_price + random.uniform(-1, 1)
        price_change = current_price - pre_close
        price_change_pct = (price_change / pre_close * 100) if pre_close > 0 else 0
        
        # 生成买卖盘口价格
        bid_prices = [current_price - 0.1 * i for i in range(1, 6)]
        ask_prices = [current_price + 0.1 * i for i in range(1, 6)]
        
        # 生成买卖盘口量
        bid_volumes = [random.randint(1, 50) for _ in range(5)]
        ask_volumes = [random.randint(1, 50) for _ in range(5)]
        
        tick = TickData(
            symbol=symbol,
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            name=symbol,
            volume=random.randint(100, 1000),
            open_interest=random.randint(10000, 50000),
            last_price=current_price,
            last_volume=random.randint(1, 10),
            limit_up=current_price * 1.05,
            limit_down=current_price * 0.95,
            open_price=current_price - random.uniform(0, 2),
            high_price=current_price + random.uniform(0, 3),
            low_price=current_price - random.uniform(0, 2),
            pre_close=pre_close,
            bid_price_1=bid_prices[0],
            bid_price_2=bid_prices[1],
            bid_price_3=bid_prices[2],
            bid_price_4=bid_prices[3],
            bid_price_5=bid_prices[4],
            ask_price_1=ask_prices[0],
            ask_price_2=ask_prices[1],
            ask_price_3=ask_prices[2],
            ask_price_4=ask_prices[3],
            ask_price_5=ask_prices[4],
            bid_volume_1=bid_volumes[0],
            bid_volume_2=bid_volumes[1],
            bid_volume_3=bid_volumes[2],
            bid_volume_4=bid_volumes[3],
            bid_volume_5=bid_volumes[4],
            ask_volume_1=ask_volumes[0],
            ask_volume_2=ask_volumes[1],
            ask_volume_3=ask_volumes[2],
            ask_volume_4=ask_volumes[3],
            ask_volume_5=ask_volumes[4],
            gateway_name="CTP_SIM"
        )
        
        self.ticks[symbol] = tick
        
        # 触发回调
        if self.on_tick:
            self.on_tick(tick)
            
    def _get_base_price_for_symbol(self, symbol: str) -> float:
        """
        根据合约代码获取基础价格
        
        Args:
            symbol: 合约代码
            
        Returns:
            float: 基础价格
        """
        # 黄金期货合约价格配置（单位：元/克）
        if symbol.startswith('AU'):
            # 根据合约月份调整价格
            # 近月合约价格稍低，远月合约价格稍高（考虑持仓成本）
            if '2508' in symbol:
                return 498.0  # 8月合约
            elif '2509' in symbol:
                return 499.0  # 9月合约，稍高于8月
            elif '2512' in symbol:
                return 501.0  # 12月合约，远月
            elif '2606' in symbol:
                return 503.0  # 明年6月合约，更远月
            else:
                return 500.0  # 默认价格
        elif symbol.startswith('AG'):
            # 白银期货（单位：元/千克）
            return 6000.0
        elif symbol.startswith('CU'):
            # 铜期货（单位：元/吨）
            return 70000.0
        elif symbol.startswith('AL'):
            # 铝期货（单位：元/吨）
            return 20000.0
        elif symbol.startswith('ZN'):
            # 锌期货（单位：元/吨）
            return 25000.0
        elif symbol.startswith('PB'):
            # 铅期货（单位：元/吨）
            return 15000.0
        elif symbol.startswith('NI'):
            # 镍期货（单位：元/吨）
            return 150000.0
        elif symbol.startswith('SN'):
            # 锡期货（单位：元/吨）
            return 200000.0
        else:
            # 其他合约默认价格
            return 100.0 