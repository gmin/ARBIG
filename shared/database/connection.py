"""
数据库连接管理器
提供MySQL连接的统一管理（Redis已移除）
"""

import asyncio
import aiomysql
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """数据库连接管理器（仅MySQL，Redis已移除）"""

    def __init__(self):
        """初始化数据库管理器"""
        self.mysql_pool = None
        self._mysql_config = None
        
    async def init_mysql(self, config: Dict[str, Any]):
        """初始化MySQL连接池"""
        try:
            self._mysql_config = config
            self.mysql_pool = await aiomysql.create_pool(
                host=config.get('host', 'localhost'),
                port=config.get('port', 3306),
                user=config.get('user', 'root'),
                password=config.get('password', ''),
                db=config.get('database', 'arbig_trading'),
                charset=config.get('charset', 'utf8mb4'),
                autocommit=True,
                minsize=config.get('minsize', 5),
                maxsize=config.get('maxsize', 20),
                echo=config.get('echo', False)
            )
            logger.info("✅ MySQL连接池初始化成功")
            return True
        except Exception as e:
            logger.error(f"❌ MySQL连接池初始化失败: {e}")
            return False
    

    
    @asynccontextmanager
    async def get_mysql_connection(self):
        """获取MySQL连接的上下文管理器"""
        if not self.mysql_pool:
            raise RuntimeError("MySQL连接池未初始化")
        
        conn = await self.mysql_pool.acquire()
        try:
            yield conn
        finally:
            self.mysql_pool.release(conn)
    
    async def execute_query(self, query: str, params: tuple = None) -> list:
        """执行查询语句"""
        async with self.get_mysql_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                result = await cursor.fetchall()
                return result
    
    async def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新语句"""
        async with self.get_mysql_connection() as conn:
            async with conn.cursor() as cursor:
                affected_rows = await cursor.execute(query, params)
                return affected_rows
    
    async def execute_insert(self, query: str, params: tuple = None) -> int:
        """执行插入语句，返回插入的ID"""
        async with self.get_mysql_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor.lastrowid
    
    async def close(self):
        """关闭所有连接"""
        if self.mysql_pool:
            self.mysql_pool.close()
            await self.mysql_pool.wait_closed()
            logger.info("MySQL连接池已关闭")
        
        if self.redis_client:
            self.redis_client.close()
            await self.redis_client.wait_closed()
            logger.info("Redis连接已关闭")

# 全局数据库管理器实例
db_manager = DatabaseManager()

# init_database函数已移除，请直接使用 db_manager.init_mysql()

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager

# MarketDataRedis类已完全移除，Redis功能不再需要
