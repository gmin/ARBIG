#!/usr/bin/env python3
"""
使用ctp.json配置文件的CTP连接测试
"""

import json
import time
import logging
from pathlib import Path
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange
from vnpy.trader.event import EVENT_LOG

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
        logger.info("2. 创建事件引擎...")
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        
        # 添加网关
        logger.info("3. 添加CTP网关...")
        main_engine.add_gateway(CtpGateway, "CTP")
        ctp_gateway = main_engine.get_gateway("CTP")
        
        # 注册日志事件
        def handle_log(event):
            if event.type == EVENT_LOG:
                logger.info(f"[CTP日志] {event.data}")
        
        event_engine.register(EVENT_LOG, handle_log)
        
        # 连接
        logger.info("4. 开始连接...")
        ctp_gateway.connect(config)
        
        # 等待连接和登录
        logger.info("5. 等待连接和登录(10秒)...")
        time.sleep(10)
        
        # 检查状态
        logger.info("6. 检查连接状态...")
        
        td_connected = False
        md_connected = False
        td_login = False
        md_login = False
        td_error = ""
        md_error = ""
        
        if hasattr(ctp_gateway, 'td_api'):
            td_connected = getattr(ctp_gateway.td_api, 'connect_status', False)
            td_login = getattr(ctp_gateway.td_api, 'login_status', False)
            if hasattr(ctp_gateway.td_api, 'error_message'):
                td_error = ctp_gateway.td_api.error_message
            
        if hasattr(ctp_gateway, 'md_api'):
            md_connected = getattr(ctp_gateway.md_api, 'connect_status', False)
            md_login = getattr(ctp_gateway.md_api, 'login_status', False)
            if hasattr(ctp_gateway.md_api, 'error_message'):
                md_error = ctp_gateway.md_api.error_message
        
        logger.info(f"   交易连接: {'✓ 成功' if td_connected else '✗ 失败'}")
        logger.info(f"   交易登录: {'✓ 成功' if td_login else '✗ 失败'}")
        if td_error:
            logger.error(f"   交易错误: {td_error}")
            
        logger.info(f"   行情连接: {'✓ 成功' if md_connected else '✗ 失败'}")
        logger.info(f"   行情登录: {'✓ 成功' if md_login else '✗ 失败'}")
        if md_error:
            logger.error(f"   行情错误: {md_error}")
        
        # 如果行情服务器登录成功，直接订阅行情
        if md_login:
            logger.info("8. 尝试订阅行情...")
            try:
                # 订阅黄金合约
                gold_symbols = ["au2508", "au2512", "au2612"]
                for symbol in gold_symbols:
                    req = SubscribeRequest(
                        symbol=symbol,
                        exchange=Exchange.SHFE
                    )
                    ctp_gateway.subscribe(req)
                    logger.info(f"   已订阅: {symbol}")
            except Exception as e:
                logger.warning(f"   订阅行情失败: {e}")
        
        # 输出总结
        logger.info("\n" + "="*60)
        logger.info("CTP连接测试总结")
        logger.info("="*60)
        logger.info(f"交易服务器连接: {'✓ 成功' if td_connected else '✗ 失败'}")
        logger.info(f"交易服务器登录: {'✓ 成功' if td_login else '✗ 失败'}")
        logger.info(f"行情服务器连接: {'✓ 成功' if md_connected else '✗ 失败'}")
        logger.info(f"行情服务器登录: {'✓ 成功' if md_login else '✗ 失败'}")
        
        if td_login and md_login:
            logger.info("✓ 完全连接成功！")
        else:
            logger.info("✗ 连接或登录失败")
        
        # 清理
        logger.info("9. 清理资源...")
        ctp_gateway.close()
        time.sleep(1)
        main_engine.close()
        
        logger.info("✓ 测试完成")
        return td_login and md_login
        
    except Exception as e:
        logger.error(f"测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_with_config() 