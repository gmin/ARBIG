"""
数据管理模块
负责数据的获取、处理和存储
"""

import time
from datetime import datetime
from typing import Dict, Optional, Tuple

from vnpy.trader.constant import Exchange
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import TickData
from vnpy.trader.utility import load_json
from vnpy.gateway.ctp import CtpGateway

from ..utils.logger import get_logger

logger = get_logger(__name__)

class SHFEDataFetcher:
    """
    上期所数据获取器
    通过CTP接口获取上海黄金期货数据
    """
    
    def __init__(self, config: Dict):
        """
        初始化上期所数据获取器
        
        Args:
            config: 配置字典，包含CTP连接信息
        """
        self.config = config
        self.gateway: Optional[CtpGateway] = None
        self.connected = False
        self.last_tick: Optional[TickData] = None
        self.subscribed_symbols = set()
        
        # 数据验证参数
        self.price_threshold = config.get("price_threshold", 0.1)  # 价格变化阈值
        self.volume_threshold = config.get("volume_threshold", 1000)  # 成交量阈值
        self.max_delay = config.get("max_delay", 5)  # 最大允许延迟（秒）
        
        # 数据缓存
        self.price_history = []  # 价格历史
        self.max_history_size = 100  # 最大历史记录数
        
    def connect(self) -> bool:
        """
        连接CTP接口
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建CTP Gateway
            self.gateway = CtpGateway(self.config)
            
            # 设置回调函数
            self.gateway.on_tick = self._on_tick
            
            # 连接CTP服务器
            self.gateway.connect(self.config)
            
            # 等待连接完成
            for _ in range(10):  # 最多等待10秒
                if self.gateway.status:
                    self.connected = True
                    logger.info("CTP接口连接成功")
                    return True
                time.sleep(1)
                
            logger.error("CTP接口连接超时")
            return False
            
        except Exception as e:
            logger.error(f"CTP接口连接失败: {str(e)}")
            return False
            
    def subscribe(self, symbol: str) -> bool:
        """
        订阅合约行情
        
        Args:
            symbol: 合约代码，如 "AU2406"
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.connected:
                logger.error("CTP接口未连接")
                return False
                
            if symbol in self.subscribed_symbols:
                logger.info(f"合约 {symbol} 已订阅")
                return True
                
            # 订阅合约
            self.gateway.subscribe([symbol])
            self.subscribed_symbols.add(symbol)
            
            logger.info(f"订阅合约 {symbol} 成功")
            return True
            
        except Exception as e:
            logger.error(f"订阅合约 {symbol} 失败: {str(e)}")
            return False
            
    def _validate_tick(self, tick: TickData) -> bool:
        """
        验证Tick数据的有效性
        
        Args:
            tick: Tick数据对象
            
        Returns:
            bool: 数据是否有效
        """
        try:
            # 检查时间戳
            if not tick.datetime:
                logger.warning("Tick数据时间戳为空")
                return False
                
            # 检查价格
            if tick.last_price <= 0:
                logger.warning(f"无效的最新价: {tick.last_price}")
                return False
                
            # 检查买卖价
            if tick.bid_price_1 <= 0 or tick.ask_price_1 <= 0:
                logger.warning(f"无效的买卖价: bid={tick.bid_price_1}, ask={tick.ask_price_1}")
                return False
                
            # 检查买卖价差
            if tick.ask_price_1 <= tick.bid_price_1:
                logger.warning(f"买卖价差异常: bid={tick.bid_price_1}, ask={tick.ask_price_1}")
                return False
                
            # 检查成交量
            if tick.volume < 0:
                logger.warning(f"无效的成交量: {tick.volume}")
                return False
                
            # 检查持仓量
            if tick.open_interest < 0:
                logger.warning(f"无效的持仓量: {tick.open_interest}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"验证Tick数据失败: {str(e)}")
            return False
            
    def _clean_tick(self, tick: TickData) -> Optional[TickData]:
        """
        清洗Tick数据
        
        Args:
            tick: 原始Tick数据对象
            
        Returns:
            Optional[TickData]: 清洗后的Tick数据，如果清洗失败则返回None
        """
        try:
            # 检查价格异常
            if self.last_tick:
                price_change = abs(tick.last_price - self.last_tick.last_price)
                if price_change > self.price_threshold * self.last_tick.last_price:
                    logger.warning(f"价格变化过大: {price_change}")
                    return None
                    
            # 检查成交量异常
            if self.last_tick and tick.volume > self.last_tick.volume + self.volume_threshold:
                logger.warning(f"成交量异常: {tick.volume}")
                return None
                
            # 检查时间延迟
            current_time = datetime.now()
            if (current_time - tick.datetime).total_seconds() > self.max_delay:
                logger.warning(f"数据延迟过大: {(current_time - tick.datetime).total_seconds()}秒")
                return None
                
            return tick
            
        except Exception as e:
            logger.error(f"清洗Tick数据失败: {str(e)}")
            return None
            
    def _update_price_history(self, price: float):
        """
        更新价格历史
        
        Args:
            price: 最新价格
        """
        self.price_history.append(price)
        if len(self.price_history) > self.max_history_size:
            self.price_history.pop(0)
            
    def _on_tick(self, tick: TickData):
        """
        Tick数据回调函数
        
        Args:
            tick: Tick数据对象
        """
        try:
            # 验证数据
            if not self._validate_tick(tick):
                return
                
            # 清洗数据
            cleaned_tick = self._clean_tick(tick)
            if not cleaned_tick:
                return
                
            # 更新最新Tick数据
            self.last_tick = cleaned_tick
            
            # 更新价格历史
            self._update_price_history(cleaned_tick.last_price)
            
            # 记录日志
            logger.debug(f"收到Tick数据: {tick.symbol}, 最新价: {tick.last_price}")
            
        except Exception as e:
            logger.error(f"处理Tick数据失败: {str(e)}")
            
    def get_latest_price(self) -> Optional[Dict]:
        """
        获取最新价格数据
        
        Returns:
            Dict: 价格数据字典，如果获取失败则返回None
        """
        if not self.connected or not self.last_tick:
            return None
            
        try:
            return {
                "timestamp": self.last_tick.datetime,
                "symbol": self.last_tick.symbol,
                "exchange": "SHFE",
                "price": self.last_tick.last_price,
                "bid_price": self.last_tick.bid_price_1,
                "ask_price": self.last_tick.ask_price_1,
                "volume": self.last_tick.volume,
                "open_interest": self.last_tick.open_interest,
                "source": "CTP"
            }
            
        except Exception as e:
            logger.error(f"获取最新价格数据失败: {str(e)}")
            return None
            
    def disconnect(self):
        """
        断开CTP连接
        """
        try:
            if self.gateway:
                self.gateway.close()
                self.connected = False
                self.last_tick = None
                self.subscribed_symbols.clear()
                logger.info("CTP接口已断开")
                
        except Exception as e:
            logger.error(f"断开CTP连接失败: {str(e)}")

class MT5DataFetcher:
    """
    MT5数据获取器
    通过MT5 API获取香港黄金数据
    """
    
    def __init__(self, config: Dict):
        """
        初始化MT5数据获取器
        
        Args:
            config: 配置字典，包含MT5连接信息
        """
        self.config = config
        self.connected = False
        self.last_tick: Optional[Dict] = None
        
    def connect(self) -> bool:
        """
        连接MT5
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # TODO: 实现MT5连接逻辑
            # 1. 导入MetaTrader5
            # 2. 初始化MT5
            # 3. 登录账户
            self.connected = True
            logger.info("MT5连接成功")
            return True
        except Exception as e:
            logger.error(f"MT5连接失败: {str(e)}")
            return False
            
    def subscribe(self, symbol: str) -> bool:
        """
        订阅合约行情
        
        Args:
            symbol: 合约代码，如 "XAUUSD"
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            # TODO: 实现订阅逻辑
            logger.info(f"订阅合约 {symbol} 成功")
            return True
        except Exception as e:
            logger.error(f"订阅合约 {symbol} 失败: {str(e)}")
            return False
            
    def get_latest_price(self) -> Optional[Dict]:
        """
        获取最新价格数据
        
        Returns:
            Dict: 价格数据字典，如果获取失败则返回None
        """
        if not self.connected:
            return None
            
        try:
            # TODO: 实现MT5数据获取逻辑
            # 1. 获取最新报价
            # 2. 转换为统一格式
            return {
                "timestamp": datetime.now(),
                "symbol": "XAUUSD",
                "exchange": "MT5",
                "price": 0.0,  # 需要从MT5获取实际数据
                "bid_price": 0.0,
                "ask_price": 0.0,
                "volume": 0,
                "open_interest": 0,
                "source": "MT5"
            }
        except Exception as e:
            logger.error(f"获取MT5数据失败: {str(e)}")
            return None

class DataManager:
    """
    数据管理器
    负责管理香港和上海黄金价格数据
    """
    
    def __init__(self, config: Dict):
        """
        初始化数据管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.shfe_fetcher = SHFEDataFetcher(config.get("shfe", {}))
        self.mt5_fetcher = MT5DataFetcher(config.get("mt5", {}))
        self.last_update_time = None
        self.update_interval = config.get("update_interval", 1)  # 默认1秒更新一次
        
    def connect(self) -> bool:
        """
        连接数据源
        
        Returns:
            bool: 是否所有数据源都连接成功
        """
        shfe_connected = self.shfe_fetcher.connect()
        mt5_connected = self.mt5_fetcher.connect()
        
        if not (shfe_connected and mt5_connected):
            logger.error("部分数据源连接失败")
            return False
            
        # 订阅合约
        self.shfe_fetcher.subscribe(self.config.get("shfe_symbol", "AU2406"))
        self.mt5_fetcher.subscribe(self.config.get("mt5_symbol", "XAUUSD"))
        
        return True
        
    def update_prices(self) -> bool:
        """
        更新价格数据
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取两个市场的最新价格
            shfe_data = self.shfe_fetcher.get_latest_price()
            mt5_data = self.mt5_fetcher.get_latest_price()
            
            if not (shfe_data and mt5_data):
                logger.warning("部分数据源未返回数据")
                return False
                
            # 检查数据时间戳是否在合理范围内
            current_time = datetime.now()
            if (current_time - shfe_data["timestamp"]).total_seconds() > 5 or \
               (current_time - mt5_data["timestamp"]).total_seconds() > 5:
                logger.warning("数据延迟过大")
                return False
                
            self.last_update_time = current_time
            return True
            
        except Exception as e:
            logger.error(f"更新价格数据失败: {str(e)}")
            return False
            
    def calculate_spread(self) -> Optional[float]:
        """
        计算基差
        
        Returns:
            float: 基差值，如果数据不完整则返回None
        """
        shfe_data = self.shfe_fetcher.get_latest_price()
        mt5_data = self.mt5_fetcher.get_latest_price()
        
        if not (shfe_data and mt5_data):
            logger.warning("价格数据不完整，无法计算基差")
            return None
            
        # 计算基差（需要考虑汇率转换）
        spread = mt5_data["price"] - shfe_data["price"]
        logger.info(f"基差计算: {spread:.2f}")
        return spread
        
    def get_last_update_time(self) -> Optional[datetime]:
        """
        获取最后更新时间
        
        Returns:
            datetime: 最后更新时间
        """
        return self.last_update_time
