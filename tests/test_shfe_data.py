"""
测试获取上海黄金期货模拟盘数据
"""

import time
from datetime import datetime

from core.shfe.gateway import SHFEGateway
from core.utils.logger import get_logger

logger = get_logger(__name__)

def test_shfe_data():
    """
    测试获取上海黄金期货数据
    """
    try:
        # 创建 Gateway
        gateway = SHFEGateway()
        
        # 连接
        if not gateway.connect():
            logger.error("连接失败")
            return
            
        # 订阅合约
        symbol = "AU2406"  # 上海黄金期货主力合约
        if not gateway.subscribe(symbol):
            logger.error(f"订阅合约 {symbol} 失败")
            return
            
        # 获取数据
        for _ in range(10):  # 获取10次数据
            price_data = gateway.get_latest_price()
            if price_data:
                logger.info(f"获取到价格数据: {price_data}")
            else:
                logger.warning("未获取到价格数据")
            time.sleep(1)  # 每秒获取一次
            
        # 断开连接
        gateway.disconnect()
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_shfe_data() 