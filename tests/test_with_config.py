#!/usr/bin/env python3
"""
使用ctp.json配置文件的CTP连接测试
"""

import time
import json
import logging
from pathlib import Path
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange
from vnpy.trader.event import EVENT_LOG, EVENT_CONTRACT, EVENT_TICK, EVENT_ACCOUNT, EVENT_POSITION

def setup_logging():
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("config_test")

def load_config():
    """加载配置文件"""
    config_file = Path("config/ctp_sim.json")
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config

def test_with_config():
    """使用配置文件的连接测试"""
    logger = setup_logging()
    
    try:
        # 加载配置
        logger.info("1. 加载配置文件...")
        config = load_config()
        logger.info(f"   配置文件: config/ctp_sim.json")
        logger.info(f"   用户名: {config['用户名']}")
        logger.info(f"   经纪商代码: {config['经纪商代码']}")
        logger.info(f"   交易服务器: {config['交易服务器']}")
        logger.info(f"   行情服务器: {config['行情服务器']}")
        
        # 创建事件引擎
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        
        # 添加网关
        main_engine.add_gateway(CtpGateway, "CTP")
        ctp_gateway = main_engine.get_gateway("CTP")
        
        # 合约收集
        contracts = []
        def on_contract(event):
            contract = event.data
            contracts.append(contract)
        def on_tick(event):
            tick = event.data
            logger.info(f"Tick: {tick.symbol} 最新价={tick.last_price} 量={tick.volume}")
        def on_account(event):
            account = event.data
            logger.info(f"账户资金: {account.accountid} 可用: {account.available} 权益: {account.balance}")
        def on_position(event):
            pos = event.data
            logger.info(f"持仓: {pos.symbol} {pos.direction.value} 持仓量: {pos.volume} 可用: {pos.available}")
        def on_log(event):
            logger.info(f"[CTP日志] {event.data}")

        # 注册事件回调
        event_engine.register(EVENT_CONTRACT, on_contract)
        event_engine.register(EVENT_TICK, on_tick)
        event_engine.register(EVENT_ACCOUNT, on_account)
        event_engine.register(EVENT_POSITION, on_position)
        event_engine.register(EVENT_LOG, on_log)

        # 启动事件引擎（MainEngine会自动启动，无需手动调用）
        # event_engine.start()

        # 连接CTP
        logger.info("2. 连接CTP...")
        ctp_gateway.connect(config)
        
        # 等待连接和合约推送
        logger.info("3. 等待连接和合约推送(30秒)...")
        time.sleep(30)

        # 打印所有收到的合约信息，便于调试
        if contracts:
            logger.info(f"共收到 {len(contracts)} 个合约，部分合约信息如下：")
            for c in contracts[:10]:  # 只打印前10个
                logger.info(f"symbol={c.symbol}, exchange={c.exchange}, open_interest={getattr(c, 'open_interest', None)}")

        # 自动识别主力合约（持仓量最大）
        main_contract = None
        if contracts:
            # 只筛选黄金合约（以au开头，SHFE交易所）
            gold_contracts = [c for c in contracts if c.symbol.startswith("au") and c.exchange == Exchange.SHFE]
            if gold_contracts:
                main_contract = max(gold_contracts, key=lambda c: getattr(c, 'open_interest', 0) or 0)
            else:
                main_contract = max(contracts, key=lambda c: getattr(c, 'open_interest', 0) or 0)
        if main_contract:
            logger.info(f"主力合约: {main_contract.symbol} 持仓量: {getattr(main_contract, 'open_interest', 0)}")
            req = SubscribeRequest(symbol=main_contract.symbol, exchange=main_contract.exchange)
            ctp_gateway.subscribe(req)
            logger.info(f"已订阅主力合约: {main_contract.symbol}")
        else:
            logger.warning("未能识别主力合约，未订阅行情")

        # 等待行情和账户数据推送
        logger.info("4. 等待行情和账户数据推送(60秒)...")
        time.sleep(60)

        # 断开连接，清理资源
        logger.info("5. 断开连接，清理资源...")
        ctp_gateway.close()
        time.sleep(1)
        main_engine.close()
        
        logger.info("✓ 测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_with_config() 