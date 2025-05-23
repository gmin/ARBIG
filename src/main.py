"""
主程序入口
"""
import sys
import os
from datetime import datetime
from loguru import logger

from vnpy.trader.app import create_app
from vnpy.trader.engine import MainEngine
from vnpy.gateway.ctp import CtpGateway
from vnpy.gateway.ib import IbGateway
from vnpy.app.cta_strategy import CtaStrategyApp

from .config import SHANGHAI_GATEWAY, HONGKONG_GATEWAY, LOG_CONFIG
from .strategy.arbitrage_strategy import GoldArbitrageStrategy
from .risk.risk_manager import RiskManager
from .data.data_manager import DataManager


def setup_logger():
    """
    配置日志
    """
    logger.remove()  # 移除默认的处理器
    logger.add(
        sys.stdout,
        format=LOG_CONFIG["format"],
        level=LOG_CONFIG["level"]
    )
    logger.add(
        "logs/gold_arbitrage_{time}.log",
        rotation=LOG_CONFIG["rotation"],
        retention=LOG_CONFIG["retention"],
        format=LOG_CONFIG["format"],
        level=LOG_CONFIG["level"]
    )


def main():
    """
    主程序入口
    """
    # 创建日志目录
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # 配置日志
    setup_logger()
    logger.info("启动黄金跨市场套利系统")

    # 创建主引擎
    main_engine = MainEngine()

    # 添加交易接口
    main_engine.add_gateway(CtpGateway)
    main_engine.add_gateway(IbGateway)

    # 添加功能应用
    main_engine.add_app(CtaStrategyApp)

    # 创建风控管理器
    risk_manager = RiskManager()

    # 创建数据管理器
    data_manager = DataManager()

    try:
        # 连接交易接口
        main_engine.connect(SHANGHAI_GATEWAY, "SH")
        main_engine.connect(HONGKONG_GATEWAY, "HK")

        # 创建策略实例
        strategy_name = "GoldArbitrage"
        strategy_setting = {
            "base_spread_threshold": 0.5,
            "max_position": 10,
            "min_profit": 0.2,
            "max_loss": 1.0,
            "order_timeout": 5
        }

        # 订阅行情
        main_engine.subscribe(["SH.AU", "HK.AU"], "SH")
        main_engine.subscribe(["SH.AU", "HK.AU"], "HK")

        # 启动策略
        main_engine.init_strategy(strategy_name, GoldArbitrageStrategy, strategy_setting)
        main_engine.start_strategy(strategy_name)

        # 主循环
        while True:
            # 检查风控状态
            risk_status = risk_manager.get_risk_status()
            if not risk_status["trading_enabled"]:
                logger.warning("交易已被风控系统禁用")
                break

            # 获取每日汇总数据
            daily_summary = data_manager.get_daily_summary(datetime.now())
            logger.info(f"每日交易汇总: {daily_summary}")

            # 等待一段时间
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
    finally:
        # 停止策略
        main_engine.stop_strategy(strategy_name)

        # 断开连接
        main_engine.close()

        # 关闭数据管理器
        data_manager.close()

        logger.info("程序退出")


if __name__ == "__main__":
    main() 
