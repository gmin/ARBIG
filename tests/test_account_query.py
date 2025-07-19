#!/usr/bin/env python3
"""
测试账户查询功能
"""

import sys
import time
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_account_query():
    """测试账户查询功能"""
    try:
        # 导入必要的模块
        from core.config_manager import ConfigManager
        from gateways.ctp_gateway import CtpGatewayWrapper
        
        logger.info("开始测试账户查询功能...")
        
        # 1. 初始化配置管理器
        config_manager = ConfigManager()
        logger.info("✓ 配置管理器初始化成功")
        
        # 2. 创建CTP网关
        ctp_gateway = CtpGatewayWrapper(config_manager)
        logger.info("✓ CTP网关创建成功")
        
        # 3. 连接CTP
        logger.info("正在连接CTP...")
        if not ctp_gateway.connect():
            logger.error("❌ CTP连接失败")
            return False
        
        logger.info("✓ CTP连接成功")
        
        # 4. 等待连接稳定
        logger.info("等待连接稳定...")
        time.sleep(3)
        
        # 5. 检查连接状态
        if not ctp_gateway.is_td_connected():
            logger.error("❌ 交易连接未建立")
            return False
        
        logger.info("✓ 交易连接已建立")
        
        # 6. 查询账户信息
        logger.info("正在查询账户信息...")
        if not ctp_gateway.query_account():
            logger.error("❌ 账户查询请求发送失败")
            return False
        
        logger.info("✓ 账户查询请求已发送")
        
        # 7. 等待账户信息返回
        logger.info("等待账户信息返回...")
        for i in range(10):  # 等待最多10秒
            time.sleep(1)
            if ctp_gateway.account:
                logger.info("✓ 账户信息已返回")
                break
            logger.info(f"等待中... {i+1}/10")
        else:
            logger.error("❌ 账户信息查询超时")
            return False
        
        # 8. 显示账户信息
        account = ctp_gateway.account
        logger.info("="*50)
        logger.info("📊 账户信息:")
        logger.info(f"  账户ID: {account.accountid}")
        logger.info(f"  总资金: {account.balance:,.2f}")
        logger.info(f"  可用资金: {account.available:,.2f}")
        logger.info(f"  冻结资金: {account.frozen:,.2f}")
        logger.info(f"  保证金: {account.balance - account.available:,.2f}")
        logger.info(f"  更新时间: {account.datetime}")
        logger.info("="*50)
        
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False
    finally:
        # 清理资源
        try:
            if 'ctp_gateway' in locals():
                ctp_gateway.disconnect()
                logger.info("✓ CTP连接已断开")
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
