#!/usr/bin/env python3
"""
测试账户查询功能
"""

import sys
import os
import time
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_account_query():
    """测试账户查询功能"""
    try:
        # 导入必要的模块
        import json
        from vnpy.event import EventEngine
        from vnpy_ctp import CtpGateway

        logger.info("开始测试账户查询功能...")

        # 1. 加载CTP配置
        config_file = "config/ctp_sim.json"
        if not os.path.exists(config_file):
            logger.error(f"❌ 配置文件不存在: {config_file}")
            return False

        with open(config_file, 'r', encoding='utf-8') as f:
            ctp_config = json.load(f)

        logger.info("✓ 配置文件加载成功")

        # 2. 转换为vnpy格式
        vnpy_config = {
            "用户名": ctp_config["用户名"],
            "密码": ctp_config["密码"],
            "经纪商代码": ctp_config["经纪商代码"],
            "交易服务器": f"tcp://{ctp_config['交易服务器']}",
            "行情服务器": f"tcp://{ctp_config['行情服务器']}",
            "产品名称": ctp_config.get("产品名称", "simnow_client_test"),
            "授权编码": ctp_config.get("授权编码", "0000000000000000")
        }

        # 3. 创建事件引擎和CTP网关
        event_engine = EventEngine()
        ctp_gateway = CtpGateway(event_engine, "CTP")
        logger.info("✓ CTP网关创建成功")

        # 4. 连接CTP
        logger.info("正在连接CTP...")
        ctp_gateway.connect(vnpy_config)

        # 5. 等待连接和登录
        logger.info("等待连接和登录...")
        for i in range(15):
            time.sleep(1)
            if hasattr(ctp_gateway, 'td_api') and ctp_gateway.td_api:
                td_connected = getattr(ctp_gateway.td_api, 'connect_status', False)
                td_login = getattr(ctp_gateway.td_api, 'login_status', False)

                if td_connected and td_login:
                    logger.info(f"✓ 交易连接已建立并登录成功 (耗时{i+1}秒)")
                    break
                elif i % 3 == 0:
                    logger.info(f"等待中... 连接:{td_connected} 登录:{td_login}")
        else:
            logger.error("❌ 交易连接或登录超时")
            if hasattr(ctp_gateway, 'td_api') and ctp_gateway.td_api:
                logger.error(f"连接状态: {getattr(ctp_gateway.td_api, 'connect_status', False)}")
                logger.error(f"登录状态: {getattr(ctp_gateway.td_api, 'login_status', False)}")
            return False

        # 7. 查询账户信息
        logger.info("正在查询账户信息...")
        account_info = None

        # 注册账户信息回调
        from vnpy.trader.event import EVENT_ACCOUNT
        def on_account(event):
            nonlocal account_info
            account_info = event.data
            logger.info("✓ 收到账户信息")

        event_engine.register(EVENT_ACCOUNT, on_account)

        # 发送查询请求
        ctp_gateway.query_account()
        logger.info("✓ 账户查询请求已发送")

        # 8. 等待账户信息返回
        logger.info("等待账户信息返回...")
        for i in range(10):  # 等待最多10秒
            time.sleep(1)
            if account_info:
                logger.info("✓ 账户信息已返回")
                break
            logger.info(f"等待中... {i+1}/10")
        else:
            logger.error("❌ 账户信息查询超时")
            return False

        # 9. 显示账户信息
        logger.info("="*50)
        logger.info("📊 账户信息:")
        logger.info(f"  账户ID: {account_info.accountid}")
        logger.info(f"  总资金: {account_info.balance:,.2f}")
        logger.info(f"  可用资金: {account_info.available:,.2f}")
        logger.info(f"  冻结资金: {account_info.frozen:,.2f}")
        logger.info(f"  保证金: {account_info.balance - account_info.available:,.2f}")
        logger.info(f"  更新时间: {account_info.datetime}")
        logger.info("="*50)

        return True

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        try:
            if 'ctp_gateway' in locals():
                ctp_gateway.close()
                logger.info("✓ CTP连接已断开")
            if 'event_engine' in locals():
                event_engine.stop()
        except:
            pass

if __name__ == "__main__":
    logger.info("🚀 开始账户查询测试")
    success = test_account_query()
    if success:
        logger.info("🎉 测试成功！")
        sys.exit(0)
    else:
        logger.error("❌ 测试失败！")
        sys.exit(1)
