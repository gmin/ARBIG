"""
真实CTP仿真连接测试
尝试连接真实的CTP仿真服务器并获取行情数据
"""

import time
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ctp import CtpWrapper, CtpConfig
from vnpy.trader.constant import Direction, Offset, OrderType

def test_real_ctp_connection():
    """
    测试真实CTP仿真连接
    """
    print("真实CTP仿真连接测试")
    print("=" * 50)
    
    try:
        # 创建配置对象
        config = CtpConfig("config/ctp.json")
        
        # 显示配置信息
        print("CTP仿真配置信息:")
        print(f"  用户名: {config.config.get('用户名')}")
        print(f"  经纪商代码: {config.config.get('BROKEID')}")
        print(f"  交易服务器: {config.config.get('td_server')}")
        print(f"  行情服务器: {config.config.get('md_server')}")
        print(f"  APPID: {config.config.get('APPID')}")
        print()
        
        # 创建网关
        gateway = CtpWrapper(config)
        
        # 连接CTP仿真环境
        print("正在连接CTP仿真环境...")
        if not gateway.connect():
            print("✗ 无法连接CTP仿真环境")
            return False
            
        print("✓ CTP仿真环境连接成功")
        
        # 订阅AU2509合约
        print("正在订阅AU2509合约...")
        if not gateway.subscribe(["AU2509"]):
            print("✗ 无法订阅AU2509合约")
            return False
            
        print("✓ AU2509合约订阅成功")
        
        # 等待并获取行情数据
        print("等待行情数据...")
        for i in range(20):  # 等待20秒
            time.sleep(1)
            tick = gateway.get_tick("AU2509")
            if tick:
                print("✓ 收到真实AU2509行情数据")
                print(f"  最新价: {tick.last_price}")
                print(f"  成交量: {tick.volume}")
                print(f"  持仓量: {tick.open_interest}")
                print(f"  买一价: {tick.bid_price_1}")
                print(f"  卖一价: {tick.ask_price_1}")
                print(f"  时间: {tick.datetime}")
                break
            print(f"等待中... ({i+1}/20)")
        else:
            print("✗ 未收到行情数据")
            
        # 断开连接
        gateway.disconnect()
        print("测试完成")
        
        return True
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """
    测试配置加载
    """
    print("配置加载测试")
    print("=" * 30)
    
    try:
        config = CtpConfig("config/ctp.json")
        
        print("✓ 配置文件加载成功")
        print(f"  配置内容: {config.config}")
        
        # 测试配置验证
        config.validate_config()
        print("✓ 配置验证通过")
        
        # 测试交易配置
        trading_config = config.get_trading_config()
        print(f"  交易配置: {trading_config}")
        
        # 测试行情配置
        market_config = config.get_market_config()
        print(f"  行情配置: {market_config}")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    主函数
    """
    print("真实CTP仿真连接测试")
    print("1. 配置加载测试")
    print("2. 真实连接测试")
    print()
    
    try:
        choice = input("请选择测试模式 (1/2): ").strip()
        
        if choice == "1":
            test_config_loading()
        elif choice == "2":
            test_real_ctp_connection()
        else:
            print("无效选择，默认执行配置加载测试")
            test_config_loading()
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main() 