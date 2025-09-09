#!/usr/bin/env python3
"""
测试GFD默认参数
"""

import requests
import json
import time

def test_gfd_default():
    """测试GFD默认参数"""
    print("🎯 测试GFD默认参数")
    print("=" * 50)
    
    # 检查交易服务状态
    try:
        response = requests.get("http://localhost:8001/health")
        if response.status_code == 200:
            print("✅ 交易服务运行正常")
        else:
            print("❌ 交易服务异常")
            return
    except Exception as e:
        print(f"❌ 无法连接交易服务: {e}")
        return
    
    # 测试开多订单
    print("\n🧪 测试开多订单（不指定time_condition参数，应该默认为GFD）")
    print("=" * 50)

    order_data_long = {
        "symbol": "au2510",
        "direction": "BUY",
        "volume": 1,
        "price": 830.0,
        "order_type": "LIMIT"
        # 注意：没有指定time_condition，应该默认为GFD
    }

    print(f"📤 发送开多订单:")
    print(f"   合约: {order_data_long['symbol']}")
    print(f"   方向: {order_data_long['direction']} (开多)")
    print(f"   数量: {order_data_long['volume']}")
    print(f"   价格: {order_data_long['price']}")
    print(f"   时间条件: 未指定（应该默认为GFD激进价格）")

    try:
        response = requests.post(
            "http://localhost:8001/real_trading/order",
            json=order_data_long,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 开多订单发送成功: {result.get('order_id', 'N/A')}")
        else:
            print(f"❌ 开多订单发送失败: {response.status_code} - {response.text}")
            return

    except Exception as e:
        print(f"❌ 发送开多订单异常: {e}")
        return

    print("⏳ 等待开多订单处理...")
    time.sleep(3)

    # 测试开空订单
    print("\n🧪 测试开空订单（不指定time_condition参数，应该默认为GFD）")
    print("=" * 50)

    order_data_short = {
        "symbol": "au2510",
        "direction": "SELL",
        "volume": 1,
        "price": 829.0,
        "order_type": "LIMIT"
        # 注意：没有指定time_condition，应该默认为GFD
    }

    print(f"📤 发送开空订单:")
    print(f"   合约: {order_data_short['symbol']}")
    print(f"   方向: {order_data_short['direction']} (开空)")
    print(f"   数量: {order_data_short['volume']}")
    print(f"   价格: {order_data_short['price']}")
    print(f"   时间条件: 未指定（应该默认为GFD激进价格）")

    try:
        response = requests.post(
            "http://localhost:8001/real_trading/order",
            json=order_data_short,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 开空订单发送成功: {result.get('order_id', 'N/A')}")
        else:
            print(f"❌ 开空订单发送失败: {response.status_code} - {response.text}")
            return

    except Exception as e:
        print(f"❌ 发送开空订单异常: {e}")
        return
    
    print("⏳ 等待开空订单处理...")
    time.sleep(3)
    
    # 获取订单列表
    try:
        response = requests.get("http://localhost:8001/real_trading/orders")
        if response.status_code == 200:
            orders = response.json()
            print(f"📊 当前订单总数: {len(orders)}")
            
            if orders:
                latest_order = orders[-1]  # 获取最新订单
                print(f"\n📋 最新订单详情:")
                print(f"   订单ID: {latest_order.get('order_id', 'N/A')}")
                print(f"   状态: {latest_order.get('status', 'N/A')}")
                print(f"   价格: {latest_order.get('price', 'N/A')}")
                print(f"   成交数量: {latest_order.get('traded', 'N/A')}")
                
                print(f"\n📊 订单状态: {latest_order.get('status', 'N/A')}")
        else:
            print(f"❌ 获取订单失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取订单异常: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 测试结果")
    print("=" * 50)
    print("✅ 开多和开空订单测试完成")
    print("💡 检查日志确认：")
    print("   - 默认使用GFD激进价格策略")
    print("   - 应该看到 '🚀 发送GFD订单(激进价格)'")
    print("   - 开多订单使用激进买入价（卖一价+0.02）")
    print("   - 开空订单使用激进卖出价（买一价-0.02）")
    print("   - 订单应该立即成交，解决重复下单问题")

if __name__ == "__main__":
    test_gfd_default()
