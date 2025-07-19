"""
市场数据客户端 - 统一的行情数据访问接口
所有需要行情数据的模块都通过此客户端从Redis获取数据
"""

from typing import Optional, Dict, List
from datetime import datetime
import json

from .storage import RedisStorage
from .types import TickData
from utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataClient:
    """
    市场数据客户端
    提供统一的行情数据访问接口，所有数据从Redis读取
    """
    
    def __init__(self, redis_config: Dict):
        """
        初始化市场数据客户端
        
        Args:
            redis_config: Redis配置
        """
        self.redis_storage = RedisStorage(redis_config)
        self.redis_storage.connect()
        logger.info("市场数据客户端初始化完成")
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取最新Tick数据
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[TickData]: 最新Tick数据
        """
        try:
            tick_dict = self.redis_storage.get_tick(symbol)
            if not tick_dict:
                logger.debug(f"Redis中未找到合约 {symbol} 的行情数据")
                return None
            
            # 将Redis中的字符串数据转换回TickData对象
            tick = TickData(
                symbol=tick_dict.get('symbol', symbol),
                last_price=float(tick_dict.get('last_price', 0)),
                volume=float(tick_dict.get('volume', 0)),
                turnover=float(tick_dict.get('turnover', 0)),
                open_interest=float(tick_dict.get('open_interest', 0)),
                time=datetime.fromisoformat(tick_dict.get('time', datetime.now().isoformat())),
                bid_price_1=float(tick_dict.get('bid_price_1', 0)),
                ask_price_1=float(tick_dict.get('ask_price_1', 0)),
                bid_volume_1=float(tick_dict.get('bid_volume_1', 0)),
                ask_volume_1=float(tick_dict.get('ask_volume_1', 0))
            )
            
            logger.debug(f"从Redis获取到 {symbol} 的行情数据: {tick.last_price}")
            return tick
            
        except (ValueError, TypeError) as e:
            logger.error(f"从Redis恢复Tick数据失败: {symbol}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"获取行情数据失败: {symbol}, 错误: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取最新价格
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[float]: 最新价格
        """
        tick = self.get_latest_tick(symbol)
        return tick.last_price if tick and tick.last_price > 0 else None
    
    def get_bid_ask_price(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """
        获取买一价和卖一价
        
        Args:
            symbol: 合约代码
            
        Returns:
            tuple: (买一价, 卖一价)
        """
        tick = self.get_latest_tick(symbol)
        if not tick:
            return None, None
        
        bid_price = tick.bid_price_1 if tick.bid_price_1 > 0 else None
        ask_price = tick.ask_price_1 if tick.ask_price_1 > 0 else None
        
        return bid_price, ask_price
    
    def get_market_price_for_order(self, symbol: str, direction: str) -> Optional[float]:
        """
        根据订单方向获取合适的市场价格
        
        Args:
            symbol: 合约代码
            direction: 订单方向 ('long' 或 'short')
            
        Returns:
            Optional[float]: 合适的市场价格
        """
        tick = self.get_latest_tick(symbol)
        if not tick or tick.last_price <= 0:
            logger.warning(f"无法获取 {symbol} 的有效行情数据")
            return None
        
        direction_lower = direction.lower()
        
        if direction_lower == 'long':
            # 买入：优先使用卖一价，否则最新价+0.05元
            if tick.ask_price_1 > 0:
                price = tick.ask_price_1
                logger.debug(f"买入使用卖一价: {price}")
            else:
                price = tick.last_price + 0.05
                logger.debug(f"买入使用最新价+0.05元: {price}")
        else:
            # 卖出：优先使用买一价，否则最新价-0.05元
            if tick.bid_price_1 > 0:
                price = tick.bid_price_1
                logger.debug(f"卖出使用买一价: {price}")
            else:
                price = tick.last_price - 0.05
                logger.debug(f"卖出使用最新价-0.05元: {price}")
        
        return price
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        批量获取多个合约的最新价格
        
        Args:
            symbols: 合约代码列表
            
        Returns:
            Dict[str, Optional[float]]: 合约代码到价格的映射
        """
        result = {}
        for symbol in symbols:
            result[symbol] = self.get_latest_price(symbol)
        return result
    
    def is_price_valid(self, symbol: str, price: float, tolerance: float = 0.1) -> bool:
        """
        检查价格是否合理（与最新价格的偏差在容忍范围内）
        
        Args:
            symbol: 合约代码
            price: 待检查的价格
            tolerance: 容忍偏差比例（默认10%）
            
        Returns:
            bool: 价格是否合理
        """
        latest_price = self.get_latest_price(symbol)
        if not latest_price:
            return True  # 无法获取参考价格时，认为价格有效
        
        deviation = abs(price - latest_price) / latest_price
        is_valid = deviation <= tolerance
        
        if not is_valid:
            logger.warning(f"价格异常: {symbol} 当前价格 {latest_price}, 检查价格 {price}, 偏差 {deviation:.2%}")
        
        return is_valid


# 全局市场数据客户端实例
_market_data_client: Optional[MarketDataClient] = None


def get_market_data_client(redis_config: Optional[Dict] = None) -> Optional[MarketDataClient]:
    """
    获取全局市场数据客户端实例
    
    Args:
        redis_config: Redis配置（仅在首次调用时需要）
        
    Returns:
        Optional[MarketDataClient]: 市场数据客户端实例
    """
    global _market_data_client
    
    if _market_data_client is None and redis_config:
        try:
            _market_data_client = MarketDataClient(redis_config)
        except Exception as e:
            logger.error(f"创建市场数据客户端失败: {e}")
            return None
    
    return _market_data_client


def init_market_data_client(redis_config: Dict) -> bool:
    """
    初始化全局市场数据客户端
    
    Args:
        redis_config: Redis配置
        
    Returns:
        bool: 是否初始化成功
    """
    global _market_data_client
    
    try:
        _market_data_client = MarketDataClient(redis_config)
        logger.info("全局市场数据客户端初始化成功")
        return True
    except Exception as e:
        logger.error(f"初始化全局市场数据客户端失败: {e}")
        return False
