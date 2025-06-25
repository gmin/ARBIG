"""
AU2509合约行情数据测试脚本
持续监控AU2509合约的行情变化
"""

import time
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ctp_sim import DirectCtpSimGateway, CtpSimConfig
from vnpy.trader.constant import Direction, Offset, OrderType

def format_tick_data(tick):
    """
    格式化Tick数据显示
    
    Args:
        tick: TickData对象
    """
    print(f"\n{'='*60}")
    print(f"AU2509合约行情数据 - {tick.datetime.strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"合约代码: {tick.symbol}")
    print(f"交易所: {tick.exchange.value}")
    print(f"最新价: {tick.last_price:.2f}")
    print(f"最新量: {tick.last_volume}")
    print(f"成交量: {tick.volume}")
    print(f"持仓量: {tick.open_interest}")
    print(f"涨跌额: {tick.last_price - tick.pre_close:.2f}")
    print(f"涨跌幅: {((tick.last_price - tick.pre_close) / tick.pre_close * 100):.2f}%")
    print(f"涨停价: {tick.limit_up:.2f}")
    print(f"跌停价: {tick.limit_down:.2f}")
    print(f"开盘价: {tick.open_price:.2f}")
    print(f"最高价: {tick.high_price:.2f}")
    print(f"最低价: {tick.low_price:.2f}")
    print(f"昨收价: {tick.pre_close:.2f}")
    print(f"\n买卖盘口:")
    print(f"  买一: {tick.bid_price_1:.2f} ({tick.bid_volume_1})")
    print(f"  买二: {tick.bid_price_2:.2f} ({tick.bid_volume_2})")
    print(f"  买三: {tick.bid_price_3:.2f} ({tick.bid_volume_3})")
    print(f"  买四: {tick.bid_price_4:.2f} ({tick.bid_volume_4})")
    print(f"  买五: {tick.bid_price_5:.2f} ({tick.bid_volume_5})")
    print(f"  卖一: {tick.ask_price_1:.2f} ({tick.ask_volume_1})")
    print(f"  卖二: {tick.ask_price_2:.2f} ({tick.ask_volume_2})")
    print(f"  卖三: {tick.ask_price_3:.2f} ({tick.ask_volume_3})")
    print(f"  卖四: {tick.ask_price_4:.2f} ({tick.ask_volume_4})")
    print(f"  卖五: {tick.ask_price_5:.2f} ({tick.ask_volume_5})")
    print(f"买卖价差: {tick.ask_price_1 - tick.bid_price_1:.2f}")
    print(f"价差比例: {((tick.ask_price_1 - tick.bid_price_1) / tick.last_price * 100):.3f}%")

def test_au2509_continuous_monitoring():
    """
    持续监控AU2509合约行情
    """
    print("AU2509合约持续行情监控")
    print("按Ctrl+C停止监控")
    print()
    
    try:
        # 创建网关
        gateway = DirectCtpSimGateway()
        
        # 连接仿真环境
        print("正在连接CTP仿真环境...")
        if not gateway.connect():
            print("✗ 无法连接CTP仿真环境")
            return
            
        # 订阅AU2509合约
        print("正在订阅AU2509合约...")
        if not gateway.subscribe(["AU2509"]):
            print("✗ 无法订阅AU2509合约")
            return
            
        print("✓ 开始监控AU2509合约行情...")
        print("按Ctrl+C停止监控\n")
        
        # 持续监控行情
        tick_count = 0
        last_tick = None
        
        while True:
            tick = gateway.get_tick("AU2509")
            if tick:
                tick_count += 1
                
                # 显示详细行情数据
                format_tick_data(tick)
                
                # 显示价格变化
                if last_tick:
                    price_change = tick.last_price - last_tick.last_price
                    print(f"价格变化: {price_change:+.2f}")
                    
                last_tick = tick
                print(f"已接收 {tick_count} 条行情数据")
                
            time.sleep(2)  # 每2秒更新一次
            
    except KeyboardInterrupt:
        print("\n\n停止监控...")
        if gateway:
            gateway.disconnect()
        print("监控已停止")
    except Exception as e:
        print(f"\n监控过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def test_au2509_single_tick():
    """
    测试单次获取AU2509行情
    """
    print("AU2509合约单次行情测试")
    print()
    
    try:
        # 创建网关
        gateway = DirectCtpSimGateway()
        
        # 连接仿真环境
        print("正在连接CTP仿真环境...")
        if not gateway.connect():
            print("✗ 无法连接CTP仿真环境")
            return
            
        # 订阅AU2509合约
        print("正在订阅AU2509合约...")
        if not gateway.subscribe(["AU2509"]):
            print("✗ 无法订阅AU2509合约")
            return
            
        # 等待行情数据
        print("等待行情数据...")
        for i in range(10):
            time.sleep(1)
            tick = gateway.get_tick("AU2509")
            if tick:
                print("✓ 收到AU2509行情数据")
                format_tick_data(tick)
                break
            print(f"等待中... ({i+1}/10)")
        else:
            print("✗ 未收到行情数据")
            
        # 断开连接
        gateway.disconnect()
        print("测试完成")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """
    主函数
    """
    print("AU2509合约行情数据测试")
    print("1. 单次行情测试")
    print("2. 持续行情监控")
    print()
    
    try:
        choice = input("请选择测试模式 (1/2): ").strip()
        
        if choice == "1":
            test_au2509_single_tick()
        elif choice == "2":
            test_au2509_continuous_monitoring()
        else:
            print("无效选择，默认执行单次测试")
            test_au2509_single_tick()
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main() 