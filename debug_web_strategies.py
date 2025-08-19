#!/usr/bin/env python3
"""
调试Web服务策略加载问题
"""

import requests
import json

def test_strategy_api():
    """测试策略API"""
    print("🔍 测试策略API")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:8002/backtest/strategies", timeout=5)
        
        print(f"📊 HTTP状态码: {response.status_code}")
        print(f"📊 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 响应数据:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # 检查数据结构
                if isinstance(data, dict):
                    success = data.get('success', False)
                    print(f"📊 success字段: {success}")
                    
                    if 'data' in data:
                        data_field = data['data']
                        print(f"📊 data字段类型: {type(data_field)}")
                        
                        if isinstance(data_field, dict) and 'strategies' in data_field:
                            strategies = data_field['strategies']
                            print(f"📊 strategies字段类型: {type(strategies)}")
                            print(f"📊 strategies长度: {len(strategies) if hasattr(strategies, '__len__') else 'N/A'}")
                            
                            if isinstance(strategies, list):
                                print(f"📊 策略列表: {strategies}")
                            elif isinstance(strategies, dict):
                                print(f"📊 策略字典: {list(strategies.keys())}")
                        else:
                            print(f"❌ data字段中没有strategies: {data_field}")
                    else:
                        print(f"❌ 响应中没有data字段")
                else:
                    print(f"❌ 响应不是字典格式: {type(data)}")
                
                return data
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"📊 原始响应: {response.text[:500]}")
                return None
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"📊 错误响应: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 策略服务不可用")
        return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None

def test_web_service():
    """测试Web服务"""
    print("\n🌐 测试Web服务")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost/strategy", timeout=5)
        
        print(f"📊 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Web服务策略页面可访问")
            
            # 检查页面内容
            content = response.text
            if 'strategy-table' in content:
                print("✅ 策略表格元素存在")
            else:
                print("❌ 策略表格元素不存在")
                
            if 'loadStrategyStatus' in content:
                print("✅ 策略加载函数存在")
            else:
                print("❌ 策略加载函数不存在")
                
        else:
            print(f"❌ Web服务访问失败: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: Web服务不可用")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def simulate_web_request():
    """模拟Web服务的策略加载请求"""
    print("\n🧪 模拟Web服务策略加载")
    print("=" * 40)
    
    try:
        # 模拟Web服务的JavaScript请求
        response = requests.get("http://localhost:8002/backtest/strategies", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            
            # 模拟JavaScript代码的逻辑
            strategies = result.get('data', {}).get('strategies', []) if result.get('success') else []
            
            print(f"📊 解析后的策略列表: {strategies}")
            print(f"📊 策略数量: {len(strategies)}")
            
            if len(strategies) == 0:
                print("❌ 策略列表为空 - 这就是Web页面显示0个策略的原因")
                
                # 分析原因
                print("\n🔍 分析原因:")
                if not result.get('success'):
                    print("  - API返回success=False")
                elif 'data' not in result:
                    print("  - API响应中没有data字段")
                elif 'strategies' not in result.get('data', {}):
                    print("  - data字段中没有strategies")
                else:
                    print("  - strategies字段为空")
                    
            else:
                print("✅ 策略列表不为空")
                for i, strategy in enumerate(strategies):
                    print(f"  {i+1}. {strategy}")
                    
            return strategies
            
        else:
            print(f"❌ API请求失败: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 模拟请求失败: {e}")
        return []

def main():
    """主函数"""
    print("🎯 Web服务策略加载调试工具")
    print("=" * 50)
    
    # 1. 测试策略API
    api_data = test_strategy_api()
    
    # 2. 测试Web服务
    test_web_service()
    
    # 3. 模拟Web请求
    web_strategies = simulate_web_request()
    
    # 4. 总结
    print("\n" + "=" * 50)
    print("🎯 调试总结")
    print("=" * 50)
    
    if api_data:
        api_strategies = api_data.get('data', {}).get('strategies', [])
        print(f"API返回策略数: {len(api_strategies) if hasattr(api_strategies, '__len__') else 'N/A'}")
    else:
        print("API返回策略数: 无法获取")
        
    print(f"Web解析策略数: {len(web_strategies)}")
    
    if api_data and len(web_strategies) == 0:
        print("\n💡 问题可能出现在:")
        print("1. API数据格式与Web服务期望不匹配")
        print("2. JavaScript代码解析逻辑有问题")
        print("3. 跨域请求被阻止")
        print("4. API响应格式发生变化")

if __name__ == "__main__":
    main()
