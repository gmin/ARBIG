#!/usr/bin/env python3
"""
测试不同端口的API可用性
"""

import requests
import time

def test_port(port, service_name):
    """测试指定端口的服务"""
    print(f"\n🧪 测试 {service_name} (端口 {port})")
    
    try:
        # 测试根路径
        response = requests.get(f"http://localhost:{port}/", timeout=3)
        if response.status_code == 200:
            print(f"✅ {service_name} 根路径可访问")
            
            # 测试回测健康检查
            try:
                response = requests.get(f"http://localhost:{port}/backtest/health", timeout=3)
                if response.status_code == 200:
                    print(f"✅ {service_name} 回测API可用")
                    data = response.json()
                    print(f"   响应: {data}")
                    return True
                else:
                    print(f"⚠️ {service_name} 回测API返回状态码: {response.status_code}")
            except Exception as e:
                print(f"⚠️ {service_name} 回测API测试失败: {e}")
        else:
            print(f"⚠️ {service_name} 根路径返回状态码: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ {service_name} 连接失败 - 服务未启动")
    except requests.exceptions.Timeout:
        print(f"❌ {service_name} 连接超时")
    except Exception as e:
        print(f"❌ {service_name} 测试异常: {e}")
    
    return False

def main():
    """主函数"""
    print("🔍 API端口测试工具")
    print("=" * 40)
    
    # 测试不同端口
    ports_to_test = [
        (8002, "策略服务"),
        (8003, "简化回测服务"),
        (8001, "其他服务"),
        (8000, "其他服务")
    ]
    
    results = []
    for port, service_name in ports_to_test:
        result = test_port(port, service_name)
        results.append((port, service_name, result))
        time.sleep(1)  # 避免请求过快
    
    print("\n" + "=" * 40)
    print("📊 测试结果总结:")
    
    available_services = []
    for port, service_name, result in results:
        status = "✅ 可用" if result else "❌ 不可用"
        print(f"端口 {port} ({service_name}): {status}")
        if result:
            available_services.append((port, service_name))
    
    if available_services:
        print(f"\n🎉 发现 {len(available_services)} 个可用服务:")
        for port, service_name in available_services:
            print(f"  - {service_name}: http://localhost:{port}")
    else:
        print("\n⚠️ 没有发现可用的回测服务")
        print("建议:")
        print("1. 启动简化服务: python simple_backtest_server.py")
        print("2. 检查策略服务启动日志")

if __name__ == "__main__":
    main()
