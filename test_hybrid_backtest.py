#!/usr/bin/env python3
"""
混合回测方案测试
测试策略管理页面的轻量回测和专业回测服务的集成
"""

import requests
import json
import time
from datetime import datetime

def test_strategy_service():
    """测试策略服务"""
    print("🧪 测试策略服务...")
    
    try:
        response = requests.get("http://localhost:8002/", timeout=5)
        if response.status_code == 200:
            print("✅ 策略服务可访问")
            return True
        else:
            print(f"⚠️ 策略服务返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 策略服务不可访问: {e}")
        return False

def test_professional_backtest_service():
    """测试专业回测服务"""
    print("🧪 测试专业回测服务...")
    
    try:
        response = requests.get("http://localhost:8003/health", timeout=5)
        if response.status_code == 200:
            print("✅ 专业回测服务可访问")
            return True
        else:
            print(f"⚠️ 专业回测服务返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 专业回测服务不可访问: {e}")
        return False

def test_strategy_quick_test():
    """测试策略快速测试功能"""
    print("\n🧪 测试策略快速测试...")
    
    test_data = {
        "test_days": 7,
        "capital": 100000,
        "max_position": 5
    }
    
    try:
        response = requests.post(
            "http://localhost:8002/strategies/large_order_following/quick_test",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 策略快速测试成功")
            print(f"   策略ID: {result.get('strategy_id')}")
            print(f"   测试周期: {result.get('test_period')}")
            
            metrics = result.get('key_metrics', {})
            print(f"   总收益率: {metrics.get('total_return', 0):.2%}")
            print(f"   最大回撤: {metrics.get('max_drawdown', 0):.2%}")
            print(f"   夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"   胜率: {metrics.get('win_rate', 0):.2%}")
            print(f"   建议: {result.get('recommendation', '无')}")
            
            return True
        else:
            print(f"❌ 策略快速测试失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 策略快速测试异常: {e}")
        return False

def test_backtest_proxy():
    """测试回测代理功能"""
    print("\n🧪 测试回测代理...")
    
    proxy_data = {
        "backtest_type": "quick",
        "parameters": {
            "days": 10,
            "max_position": 8
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8002/strategies/large_order_following/backtest_proxy",
            json=proxy_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 回测代理成功")
            print(f"   策略ID: {result.get('strategy_id')}")
            print(f"   回测类型: {result.get('backtest_type')}")
            print(f"   专业服务URL: {result.get('professional_service_url')}")
            return True
        else:
            print(f"❌ 回测代理失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 回测代理异常: {e}")
        return False

def test_strategy_sync():
    """测试策略同步功能"""
    print("\n🧪 测试策略同步...")
    
    try:
        response = requests.post(
            "http://localhost:8002/strategies/large_order_following/sync_to_backtest",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 策略同步成功")
            print(f"   消息: {result.get('message')}")
            return True
        else:
            print(f"⚠️ 策略同步失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"⚠️ 策略同步异常: {e}")
        return False

def test_backtest_history():
    """测试回测历史查询"""
    print("\n🧪 测试回测历史查询...")
    
    try:
        response = requests.get(
            "http://localhost:8002/strategies/large_order_following/backtest_history",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 回测历史查询成功")
            history = result.get('history', [])
            print(f"   历史记录数: {len(history)}")
            
            if history:
                latest = history[0]
                print(f"   最新记录: {latest.get('test_id')}")
                print(f"   时间: {latest.get('timestamp')}")
            
            return True
        else:
            print(f"❌ 回测历史查询失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 回测历史查询异常: {e}")
        return False

def test_professional_backtest_direct():
    """直接测试专业回测服务"""
    print("\n🧪 直接测试专业回测服务...")
    
    test_data = {
        "strategy_name": "LargeOrderFollowing",
        "strategy_setting": {"max_position": 5},
        "days": 7
    }
    
    try:
        response = requests.post(
            "http://localhost:8003/backtest/quick",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 专业回测服务直接调用成功")
            
            data = result.get('data', {})
            basic_result = data.get('basic_result', {})
            print(f"   总收益率: {basic_result.get('total_return', 0):.2%}")
            print(f"   交易次数: {basic_result.get('total_trade_count', 0)}")
            
            return True
        else:
            print(f"❌ 专业回测服务调用失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 专业回测服务调用异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 混合回测方案测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now()}")
    print("=" * 60)
    
    # 测试项目列表
    tests = [
        ("策略服务连通性", test_strategy_service),
        ("专业回测服务连通性", test_professional_backtest_service),
        ("策略快速测试", test_strategy_quick_test),
        ("策略同步", test_strategy_sync),
        ("回测代理", test_backtest_proxy),
        ("回测历史查询", test_backtest_history),
        ("专业回测直接调用", test_professional_backtest_direct),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # 测试间隔
    
    # 测试结果总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 混合回测方案完全可用!")
        print("\n📝 使用建议:")
        print("1. 策略开发时使用快速测试: /strategies/{id}/quick_test")
        print("2. 深度分析时使用回测代理: /strategies/{id}/backtest_proxy")
        print("3. 专业分析直接访问: http://localhost:8003/docs")
    elif passed >= total * 0.7:
        print("✅ 混合回测方案基本可用!")
        print("⚠️ 部分功能可能需要调整")
    else:
        print("⚠️ 混合回测方案需要进一步配置")
        print("🔧 请检查服务启动状态和网络连接")

if __name__ == "__main__":
    main()
