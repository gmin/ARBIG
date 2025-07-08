"""
数据存储模块
负责数据的持久化存储和缓存
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pymongo
from pymongo import MongoClient
import redis
from redis import Redis

from utils.logger import get_logger

logger = get_logger(__name__)

class MongoDBStorage:
    """
    MongoDB存储类
    用于存储历史数据
    """
    
    def __init__(self, config: Dict):
        """
        初始化MongoDB存储
        
        Args:
            config: MongoDB配置字典
        """
        self.config = config
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collections = {}
        
    def connect(self) -> bool:
        """
        连接MongoDB数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 连接MongoDB
            self.client = MongoClient(
                host=self.config['host'],
                port=self.config['port']
            )
            
            # 选择数据库
            self.db = self.client[self.config['database']]
            
            # 初始化集合
            for key, collection_name in self.config['collections'].items():
                self.collections[key] = self.db[collection_name]
                
            # 创建索引
            self._create_indexes()
            
            logger.info("MongoDB连接成功")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            return False
            
    def _create_indexes(self):
        """
        创建必要的索引
        """
        # 为tick数据创建索引
        self.collections['tick_data'].create_index([
            ("timestamp", pymongo.DESCENDING),
            ("symbol", pymongo.ASCENDING)
        ])
        
        # 为交易数据创建索引
        self.collections['trade_data'].create_index([
            ("timestamp", pymongo.DESCENDING),
            ("symbol", pymongo.ASCENDING)
        ])
        
        # 为持仓数据创建索引
        self.collections['position_data'].create_index([
            ("timestamp", pymongo.DESCENDING),
            ("symbol", pymongo.ASCENDING)
        ])
        
    def save_tick(self, tick_data: Dict) -> bool:
        """
        保存Tick数据
        
        Args:
            tick_data: Tick数据字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 添加时间戳
            if 'timestamp' not in tick_data:
                tick_data['timestamp'] = datetime.now()
                
            # 保存数据
            self.collections['tick_data'].insert_one(tick_data)
            return True
            
        except Exception as e:
            logger.error(f"保存Tick数据失败: {str(e)}")
            return False
            
    def save_trade(self, trade_data: Dict) -> bool:
        """
        保存交易数据
        
        Args:
            trade_data: 交易数据字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 添加时间戳
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.now()
                
            # 保存数据
            self.collections['trade_data'].insert_one(trade_data)
            return True
            
        except Exception as e:
            logger.error(f"保存交易数据失败: {str(e)}")
            return False
            
    def save_position(self, position_data: Dict) -> bool:
        """
        保存持仓数据
        
        Args:
            position_data: 持仓数据字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 添加时间戳
            if 'timestamp' not in position_data:
                position_data['timestamp'] = datetime.now()
                
            # 保存数据
            self.collections['position_data'].insert_one(position_data)
            return True
            
        except Exception as e:
            logger.error(f"保存持仓数据失败: {str(e)}")
            return False
            
    def get_tick_history(self, 
                        symbol: str, 
                        start_time: datetime, 
                        end_time: datetime) -> List[Dict]:
        """
        获取历史Tick数据
        
        Args:
            symbol: 合约代码
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[Dict]: Tick数据列表
        """
        try:
            query = {
                'symbol': symbol,
                'timestamp': {
                    '$gte': start_time,
                    '$lte': end_time
                }
            }
            
            cursor = self.collections['tick_data'].find(query)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"获取历史Tick数据失败: {str(e)}")
            return []
            
    def cleanup_old_data(self, days: int = 30) -> bool:
        """
        清理旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            bool: 清理是否成功
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 清理各个集合的旧数据
            for collection in self.collections.values():
                collection.delete_many({
                    'timestamp': {'$lt': cutoff_time}
                })
                
            return True
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")
            return False

class RedisStorage:
    """
    Redis存储类
    用于缓存实时数据
    """
    
    def __init__(self, config: Dict):
        """
        初始化Redis存储
        
        Args:
            config: Redis配置字典
        """
        self.config = config
        self.client: Optional[Redis] = None
        
    def connect(self) -> bool:
        """
        连接Redis服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client = Redis(
                host=self.config['host'],
                port=self.config['port'],
                db=self.config['db']
            )
            
            # 测试连接
            self.client.ping()
            
            logger.info("Redis连接成功")
            return True
            
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            return False
            
    def save_tick(self, symbol: str, tick_data: Dict) -> bool:
        """
        保存实时Tick数据
        
        Args:
            symbol: 合约代码
            tick_data: Tick数据字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            key = f"tick:{symbol}"
            self.client.hmset(key, tick_data)
            return True
            
        except Exception as e:
            logger.error(f"保存实时Tick数据失败: {str(e)}")
            return False
            
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """
        获取实时Tick数据
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[Dict]: Tick数据字典，如果不存在则返回None
        """
        try:
            key = f"tick:{symbol}"
            data = self.client.hgetall(key)
            return data if data else None
            
        except Exception as e:
            logger.error(f"获取实时Tick数据失败: {str(e)}")
            return None
            
    def save_spread(self, spread: float) -> bool:
        """
        保存基差数据
        
        Args:
            spread: 基差值
            
        Returns:
            bool: 保存是否成功
        """
        try:
            key = "spread:latest"
            self.client.set(key, str(spread))
            return True
            
        except Exception as e:
            logger.error(f"保存基差数据失败: {str(e)}")
            return False
            
    def get_spread(self) -> Optional[float]:
        """
        获取最新基差数据
        
        Returns:
            Optional[float]: 基差值，如果不存在则返回None
        """
        try:
            key = "spread:latest"
            data = self.client.get(key)
            return float(data) if data else None
            
        except Exception as e:
            logger.error(f"获取基差数据失败: {str(e)}")
            return None

class StorageManager:
    """
    存储管理器
    统一管理MongoDB和Redis存储
    """
    
    def __init__(self, config: Dict):
        """
        初始化存储管理器
        
        Args:
            config: 存储配置字典
        """
        self.config = config
        self.mongodb = MongoDBStorage(config['mongodb'])
        self.redis = RedisStorage(config['redis'])
        
    def connect(self) -> bool:
        """
        连接所有存储
        
        Returns:
            bool: 是否所有存储都连接成功
        """
        mongodb_connected = self.mongodb.connect()
        redis_connected = self.redis.connect()
        
        return mongodb_connected and redis_connected
        
    def save_tick(self, tick_data: Dict) -> bool:
        """
        保存Tick数据（同时保存到MongoDB和Redis）
        
        Args:
            tick_data: Tick数据字典
            
        Returns:
            bool: 保存是否成功
        """
        # 保存到Redis（实时数据）
        redis_success = self.redis.save_tick(
            tick_data['symbol'],
            tick_data
        )
        
        # 保存到MongoDB（历史数据）
        mongodb_success = self.mongodb.save_tick(tick_data)
        
        return redis_success and mongodb_success
        
    def save_trade(self, trade_data: Dict) -> bool:
        """
        保存交易数据
        
        Args:
            trade_data: 交易数据字典
            
        Returns:
            bool: 保存是否成功
        """
        return self.mongodb.save_trade(trade_data)
        
    def save_position(self, position_data: Dict) -> bool:
        """
        保存持仓数据
        
        Args:
            position_data: 持仓数据字典
            
        Returns:
            bool: 保存是否成功
        """
        return self.mongodb.save_position(position_data)
        
    def save_spread(self, spread: float) -> bool:
        """
        保存基差数据
        
        Args:
            spread: 基差值
            
        Returns:
            bool: 保存是否成功
        """
        return self.redis.save_spread(spread)
        
    def get_tick_history(self, 
                        symbol: str, 
                        start_time: datetime, 
                        end_time: datetime) -> List[Dict]:
        """
        获取历史Tick数据
        
        Args:
            symbol: 合约代码
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[Dict]: Tick数据列表
        """
        return self.mongodb.get_tick_history(symbol, start_time, end_time)
        
    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """
        获取最新Tick数据
        
        Args:
            symbol: 合约代码
            
        Returns:
            Optional[Dict]: Tick数据字典
        """
        return self.redis.get_tick(symbol)
        
    def get_latest_spread(self) -> Optional[float]:
        """
        获取最新基差数据
        
        Returns:
            Optional[float]: 基差值
        """
        return self.redis.get_spread()
        
    def cleanup_old_data(self, days: int = 30) -> bool:
        """
        清理旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            bool: 清理是否成功
        """
        return self.mongodb.cleanup_old_data(days) 