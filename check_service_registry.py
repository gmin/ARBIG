#!/usr/bin/env python3
"""
检查服务注册表状态
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_service_registry():
    """检查服务注册表"""
    print("🔍 检查服务注册表状态")
    print("=" * 40)
    
    try:
        from shared.utils.service_client import get_service_registry
        
        registry = get_service_registry()
        
        print(f"📊 注册的服务数量: {len(registry.services)}")
        
        for service_name, service_info in registry.services.items():
            print(f"\n📋 服务: {service_name}")
            print(f"  显示名: {service_info.display_name}")
            print(f"  主机: {service_info.host}")
            print(f"  端口: {service_info.port}")
            print(f"  状态: {service_info.status}")
            print(f"  版本: {service_info.version}")
            
            # 检查客户端
            client = registry.get_client(service_name)
            if client:
                print(f"  客户端URL: {client.base_url}")
            else:
                print(f"  客户端: 未创建")
        
        return registry
        
    except Exception as e:
        print(f"❌ 检查服务注册表失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_trading_service_call():
    """测试trading_service调用"""
    print("\n🧪 测试trading_service调用")
    print("=" * 40)
    
    try:
        from shared.utils.service_client import call_service
        import asyncio
        
        async def test_call():
            response = await call_service("trading_service", "GET", "/health")
            return response
        
        response = asyncio.run(test_call())
        
        print(f"📊 调用结果:")
        print(f"  成功: {response.success}")
        print(f"  消息: {response.message}")
        print(f"  数据: {response.data}")
        
        return response.success
        
    except Exception as e:
        print(f"❌ 测试调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🎯 服务注册表诊断工具")
    print("=" * 50)
    
    # 检查服务注册表
    registry = check_service_registry()
    
    # 测试trading_service调用
    if registry:
        success = test_trading_service_call()
        
        print("\n" + "=" * 50)
        print("🎯 诊断结果")
        print("=" * 50)
        
        if success:
            print("✅ trading_service调用成功")
        else:
            print("❌ trading_service调用失败")
            print("💡 建议:")
            print("  1. 检查trading_service是否在8004端口运行")
            print("  2. 重启Web服务以重新注册服务")
            print("  3. 检查服务注册表的端口配置")

if __name__ == "__main__":
    main()
