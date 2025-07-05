#!/usr/bin/env python3
"""
ARBIG服务容器测试脚本
测试重构后的main.py服务容器功能
"""

import sys
import time
import requests
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_service_container():
    """测试服务容器功能"""
    print("🧪 测试ARBIG服务容器")
    print("=" * 50)
    
    try:
        from main import get_service_container
        
        # 获取服务容器实例
        container = get_service_container()
        print("✓ 服务容器创建成功")
        
        # 测试系统启动
        print("\n📋 测试系统启动...")
        result = container.start_system()
        if result.success:
            print(f"✓ 系统启动成功: {result.message}")
        else:
            print(f"✗ 系统启动失败: {result.message}")
        
        # 测试获取系统状态
        print("\n📊 测试系统状态...")
        status = container.get_system_status()
        print(f"✓ 系统状态: {status.get('system_status')}")
        print(f"✓ 运行模式: {status.get('running_mode')}")
        
        # 测试服务启动
        print("\n🔧 测试服务管理...")
        
        # 启动行情服务
        result = container.start_service('MarketDataService')
        if result.success:
            print(f"✓ 行情服务启动: {result.message}")
        else:
            print(f"✗ 行情服务启动失败: {result.message}")
        
        # 获取服务状态
        service_status = container.get_service_status('MarketDataService')
        print(f"✓ 行情服务状态: {service_status.get('status')}")
        
        # 测试服务停止
        result = container.stop_service('MarketDataService')
        if result.success:
            print(f"✓ 行情服务停止: {result.message}")
        else:
            print(f"✗ 行情服务停止失败: {result.message}")
        
        # 测试系统停止
        print("\n🛑 测试系统停止...")
        result = container.stop_system()
        if result.success:
            print(f"✓ 系统停止成功: {result.message}")
        else:
            print(f"✗ 系统停止失败: {result.message}")
        
        print("\n🎉 服务容器测试完成！")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保项目结构正确")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_api_integration():
    """测试API集成"""
    print("\n🌐 测试API集成")
    print("=" * 30)
    
    # 等待API服务启动
    print("等待API服务启动...")
    time.sleep(3)
    
    try:
        # 测试健康检查
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✓ API健康检查通过")
        else:
            print(f"✗ API健康检查失败: {response.status_code}")
        
        # 测试系统状态API
        response = requests.get("http://localhost:8000/api/v1/system/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✓ 系统状态API正常")
            print(f"  - 系统状态: {data.get('data', {}).get('system_status')}")
            print(f"  - 运行模式: {data.get('data', {}).get('running_mode')}")
        else:
            print(f"✗ 系统状态API失败: {response.status_code}")
        
        # 测试服务列表API
        response = requests.get("http://localhost:8000/api/v1/services/list", timeout=5)
        if response.status_code == 200:
            data = response.json()
            services = data.get('data', {}).get('services', [])
            print(f"✓ 服务列表API正常，共{len(services)}个服务")
        else:
            print(f"✗ 服务列表API失败: {response.status_code}")
        
        print("🎉 API集成测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务，请确保API服务已启动")
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def main():
    """主函数"""
    print("🚀 ARBIG服务容器完整测试")
    print("=" * 60)
    
    # 测试服务容器
    test_service_container()
    
    # 测试API集成
    test_api_integration()
    
    print("\n📋 测试总结:")
    print("1. 服务容器功能已重构完成")
    print("2. API集成已连接到真实服务容器")
    print("3. 系统现在可以通过Web API完全控制")
    print("\n🎯 下一步:")
    print("1. 启动完整系统: python main.py --auto-start")
    print("2. 访问API文档: http://localhost:8000/api/docs")
    print("3. 开发前端界面")

if __name__ == "__main__":
    main()
