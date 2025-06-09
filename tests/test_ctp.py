"""
CTP连接测试脚本
"""

import time
from core.data import SHFEDataFetcher

def test_ctp_connection():
    """
    测试CTP连接
    """
    # 创建数据获取器
    fetcher = SHFEDataFetcher()
    
    # 连接CTP
    if not fetcher.connect():
        print("CTP连接失败")
        return
        
    # 订阅合约
    symbol = "AU2406"  # 黄金期货主力合约
    if not fetcher.subscribe(symbol):
        print(f"订阅合约 {symbol} 失败")
        return
        
    print(f"成功订阅合约 {symbol}")
    
    # 等待数据
    print("等待数据...")
    for _ in range(10):  # 等待10秒
        price_data = fetcher.get_latest_price()
        if price_data:
            print(f"收到数据: {price_data}")
            break
        time.sleep(1)
        
    # 断开连接
    fetcher.disconnect()
    print("测试完成")

if __name__ == "__main__":
    test_ctp_connection() 