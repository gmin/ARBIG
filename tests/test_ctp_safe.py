#!/usr/bin/env python3
"""
安全的CTP连接测试
详细检查订阅状态和数据接收
"""

import os
import sys
import time

# 设置locale
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ctp import CtpWrapper, CtpConfig

def test_ctp_safe():
    """安全的CTP测试"""
    print("=" * 60)
    print("CTP连接测试 - 详细订阅状态检查")
    print("=" * 60)
    
    try:
        # 1. 创建配置
        print("1. 创建配置...")
        config = CtpConfig("config/ctp_sim.json")
        print(f"   配置加载成功")
        
        # 2. 创建网关
        print("2. 创建网关...")
        gateway = CtpWrapper(config)
        print("   网关创建成功")
        
        # 3. 连接CTP
        print("3. 连接CTP...")
        if gateway.connect():
            print("   ✓ CTP连接成功")
            print(f"   交易连接状态: {gateway.trading_connected}")
            print(f"   行情连接状态: {gateway.market_connected}")
            print(f"   总体连接状态: {gateway.connected}")
        else:
            print("   ✗ CTP连接失败")
            return False
        
        # 4. 详细订阅检查
        print("4. 详细订阅检查...")
        test_symbols = ["AU2509", "AU2512"]
        subscribed_symbols = []
        subscription_results = {}
        
        for symbol in test_symbols:
            print(f"   正在订阅 {symbol}...")
            
            # 订阅前检查
            print(f"     订阅前状态检查...")
            print(f"       行情连接状态: {gateway.market_connected}")
            print(f"       网关连接状态: {gateway.connected}")
            
            # 执行订阅
            subscription_success = gateway.subscribe([symbol])
            subscription_results[symbol] = subscription_success
            
            if subscription_success:
                print(f"     ✓ {symbol} 订阅调用成功")
                subscribed_symbols.append(symbol)
                
                # 订阅后立即检查
                print(f"     订阅后状态检查...")
                print(f"       行情连接状态: {gateway.market_connected}")
                print(f"       网关连接状态: {gateway.connected}")
                
                # 检查网关内部状态
                if hasattr(gateway, 'gateway') and gateway.gateway:
                    if hasattr(gateway.gateway, 'md_api'):
                        md_api = gateway.gateway.md_api
                        print(f"       行情API状态: {getattr(md_api, 'connect_status', 'Unknown')}")
                        if hasattr(md_api, 'subscribed_symbols'):
                            print(f"       已订阅合约: {list(md_api.subscribed_symbols)}")
                
            else:
                print(f"     ✗ {symbol} 订阅调用失败")
        
        # 5. 订阅结果总结
        print("5. 订阅结果总结...")
        print(f"   订阅调用结果:")
        for symbol, success in subscription_results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"     {symbol}: {status}")
        
        print(f"   成功订阅数量: {len(subscribed_symbols)}/{len(test_symbols)}")
        if subscribed_symbols:
            print(f"   成功订阅的合约: {subscribed_symbols}")
        
        # 6. 等待并检查数据
        print("6. 等待数据检查...")
        print("   开始监听数据，等待30秒...")
        
        data_received = {}
        start_time = time.time()
        
        for i in range(30):  # 等待30秒
            current_time = time.time()
            elapsed = current_time - start_time
            
            print(f"\r等待中... ({elapsed:.0f}/30秒)", end="", flush=True)
            
            # 检查每个已订阅合约的数据
            for symbol in subscribed_symbols:
                tick = gateway.get_tick(symbol)
                if tick and symbol not in data_received:
                    data_received[symbol] = tick
                    print(f"\n   ✓ {symbol} 收到数据: 最新价={tick.last_price}")
            
            # 如果收到所有数据，提前结束
            if len(data_received) == len(subscribed_symbols):
                print(f"\n   ✓ 已收到所有 {len(subscribed_symbols)} 个合约的数据!")
                break
                
            time.sleep(1)
        
        print(f"\n   数据接收总结:")
        print(f"   收到数据的合约: {list(data_received.keys())}")
        print(f"   数据接收率: {len(data_received)}/{len(subscribed_symbols)}")
        
        # 7. 详细数据检查
        if data_received:
            print("7. 详细数据检查...")
            for symbol, tick in data_received.items():
                print(f"\n   {symbol} 详细数据:")
                print(f"     合约代码: {tick.symbol}")
                print(f"     交易所: {tick.exchange}")
                print(f"     最新价: {tick.last_price}")
                print(f"     最新量: {tick.last_volume}")
                print(f"     时间: {tick.datetime}")
                print(f"     买一价: {tick.bid_price_1} 买一量: {tick.bid_volume_1}")
                print(f"     卖一价: {tick.ask_price_1} 卖一量: {tick.ask_volume_1}")
        else:
            print("7. 未收到数据分析...")
            print("   可能的原因:")
            print("   1. 不在交易时间内")
            print("   2. 合约代码不正确")
            print("   3. 经纪商服务器配置问题")
            print("   4. 订阅虽然成功但数据推送有问题")
        
        # 8. 断开连接
        print("8. 断开连接...")
        gateway.disconnect()
        print("   ✓ 连接已断开")
        
        print("\n" + "=" * 60)
        print("✓ 测试完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"   ✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ctp_safe()
    if success:
        print("\n✓ 测试成功")
    else:
        print("\n✗ 测试失败") 