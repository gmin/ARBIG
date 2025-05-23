"""
数据管理器
"""
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd
from pymongo import MongoClient

from ..config import MONGODB_URI, DB_NAME


class DataManager:
    """
    数据管理器
    """
    def __init__(self):
        """
        初始化数据管理器
        """
        # 连接MongoDB
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]

        # 创建集合
        self.tick_collection = self.db["ticks"]
        self.bar_collection = self.db["bars"]
        self.trade_collection = self.db["trades"]
        self.order_collection = self.db["orders"]

        # 创建索引
        self._create_indexes()

    def _create_indexes(self):
        """
        创建数据库索引
        """
        # Tick数据索引
        self.tick_collection.create_index([
            ("symbol", 1),
            ("datetime", 1)
        ])

        # Bar数据索引
        self.bar_collection.create_index([
            ("symbol", 1),
            ("datetime", 1)
        ])

        # 交易数据索引
        self.trade_collection.create_index([
            ("symbol", 1),
            ("datetime", 1)
        ])

        # 订单数据索引
        self.order_collection.create_index([
            ("symbol", 1),
            ("datetime", 1)
        ])

    def save_tick(self, tick_data: Dict):
        """
        保存Tick数据
        """
        try:
            self.tick_collection.insert_one(tick_data)
        except Exception as e:
            logger.error(f"保存Tick数据失败: {e}")

    def save_bar(self, bar_data: Dict):
        """
        保存Bar数据
        """
        try:
            self.bar_collection.insert_one(bar_data)
        except Exception as e:
            logger.error(f"保存Bar数据失败: {e}")

    def save_trade(self, trade_data: Dict):
        """
        保存交易数据
        """
        try:
            self.trade_collection.insert_one(trade_data)
        except Exception as e:
            logger.error(f"保存交易数据失败: {e}")

    def save_order(self, order_data: Dict):
        """
        保存订单数据
        """
        try:
            self.order_collection.insert_one(order_data)
        except Exception as e:
            logger.error(f"保存订单数据失败: {e}")

    def get_tick_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        获取Tick数据
        """
        try:
            return list(self.tick_collection.find({
                "symbol": symbol,
                "datetime": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("datetime", 1))
        except Exception as e:
            logger.error(f"获取Tick数据失败: {e}")
            return []

    def get_bar_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        获取Bar数据
        """
        try:
            return list(self.bar_collection.find({
                "symbol": symbol,
                "datetime": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("datetime", 1))
        except Exception as e:
            logger.error(f"获取Bar数据失败: {e}")
            return []

    def get_trade_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        获取交易数据
        """
        try:
            return list(self.trade_collection.find({
                "symbol": symbol,
                "datetime": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("datetime", 1))
        except Exception as e:
            logger.error(f"获取交易数据失败: {e}")
            return []

    def get_order_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        获取订单数据
        """
        try:
            return list(self.order_collection.find({
                "symbol": symbol,
                "datetime": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("datetime", 1))
        except Exception as e:
            logger.error(f"获取订单数据失败: {e}")
            return []

    def get_daily_summary(self, date: datetime) -> Dict:
        """
        获取每日交易汇总
        """
        try:
            # 获取当日交易数据
            trades = list(self.trade_collection.find({
                "datetime": {
                    "$gte": date.replace(hour=0, minute=0, second=0, microsecond=0),
                    "$lt": date.replace(hour=23, minute=59, second=59, microsecond=999999)
                }
            }))

            # 计算汇总数据
            total_volume = sum(trade["volume"] for trade in trades)
            total_value = sum(trade["volume"] * trade["price"] for trade in trades)
            total_trades = len(trades)

            return {
                "date": date,
                "total_volume": total_volume,
                "total_value": total_value,
                "total_trades": total_trades
            }
        except Exception as e:
            logger.error(f"获取每日汇总数据失败: {e}")
            return {}

    def close(self):
        """
        关闭数据库连接
        """
        self.client.close() 
