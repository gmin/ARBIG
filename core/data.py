"""
数据管理模块
负责数据的获取、处理和存储
"""

import time
from datetime import datetime
from typing import Dict, Optional, Tuple

from vnpy.trader.constant import Exchange
from vnpy.trader.object import TickData

from core.shfe.gateway import SHFEGateway
from utils.logger import get_logger

logger = get_logger(__name__)

class DataManager:
    """
    数据管理器
    统一管理多个数据源的数据获取和处理
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化数据管理器
        
        Args:
            config: 配置字典，包含各个数据源的配置信息
        """
        self.config = config or {}
        
        # 初始化数据源
        self.shfe_gateway = SHFEGateway(self.config.get("shfe"))
        
        # 数据缓存
        self.last_update_time: Optional[datetime] = None
        self.price_cache: Dict[str, Dict] = {}
        
    def connect(self) -> bool:
        """
        连接所有数据源
        
        Returns:
            bool: 是否所有数据源都连接成功
        """
        try:
            # 连接上海黄金期货
            if not self.shfe_gateway.connect():
                logger.error("上海黄金期货连接失败")
                return False

            logger.info("数据源连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接数据源失败: {str(e)}")
            return False
            
    def subscribe(self, symbol: str, source: str) -> bool:
        """
        订阅指定数据源的合约

        Args:
            symbol: 合约代码
            source: 数据源，目前仅支持："shfe"

        Returns:
            bool: 订阅是否成功
        """
        try:
            if source == "shfe":
                return self.shfe_gateway.subscribe(symbol)
            else:
                logger.error(f"未知的数据源: {source}")
                return False
                
        except Exception as e:
            logger.error(f"订阅合约失败: {str(e)}")
            return False
            
    def update_prices(self) -> bool:
        """
        更新所有数据源的价格数据
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 更新上海黄金期货价格
            shfe_price = self.shfe_gateway.get_latest_price()
            if shfe_price:
                self.price_cache["shfe"] = shfe_price
                
            # 更新最后更新时间
            self.last_update_time = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"更新价格数据失败: {str(e)}")
            return False
            
    def calculate_spread(self) -> Optional[float]:
        """
        计算价差
        
        Returns:
            Optional[float]: 价差，如果计算失败则返回None
        """
        try:
            # 检查是否有足够的价格数据
            if "shfe" not in self.price_cache:
                return None

            # 获取价格
            shfe_price = self.price_cache["shfe"]["last_price"]

            # 由于不再使用MT5，这里返回一个模拟价差
            spread = 0.0
            
            return spread
            
        except Exception as e:
            logger.error(f"计算价差失败: {str(e)}")
            return None
            
    def get_last_update_time(self) -> Optional[datetime]:
        """
        获取最后更新时间
        
        Returns:
            Optional[datetime]: 最后更新时间
        """
        return self.last_update_time
        
    def disconnect(self):
        """
        断开所有数据源连接
        """
        try:
            # 断开上海黄金期货连接
            self.shfe_gateway.disconnect()

            logger.info("数据源已断开连接")
            
        except Exception as e:
            logger.error(f"断开数据源连接失败: {str(e)}")
