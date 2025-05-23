"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "gold_arbitrage")

# 交易配置
SHANGHAI_GATEWAY = {
    "name": "CTP",
    "host": os.getenv("SH_CTP_HOST", ""),
    "port": int(os.getenv("SH_CTP_PORT", "17001")),
    "user": os.getenv("SH_CTP_USER", ""),
    "password": os.getenv("SH_CTP_PASSWORD", ""),
    "broker_id": os.getenv("SH_CTP_BROKER_ID", ""),
    "app_id": os.getenv("SH_CTP_APP_ID", ""),
    "auth_code": os.getenv("SH_CTP_AUTH_CODE", ""),
}

HONGKONG_GATEWAY = {
    "name": "IB",  # 或其他支持的接口
    "host": os.getenv("HK_IB_HOST", "127.0.0.1"),
    "port": int(os.getenv("HK_IB_PORT", "7496")),
    "client_id": int(os.getenv("HK_IB_CLIENT_ID", "1")),
}

# 策略参数
STRATEGY_PARAMS = {
    "base_spread_threshold": 0.5,  # 基础价差阈值
    "max_position": 10,  # 最大持仓
    "min_profit": 0.2,  # 最小利润要求
    "max_loss": 1.0,  # 最大亏损限制
    "order_timeout": 5,  # 订单超时时间（秒）
}

# 风控参数
RISK_PARAMS = {
    "max_daily_loss": 10000,  # 每日最大亏损
    "max_position_value": 1000000,  # 最大持仓价值
    "max_slippage": 0.1,  # 最大滑点
    "min_liquidity": 1000000,  # 最小流动性要求
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "1 day",
    "retention": "7 days",
} 