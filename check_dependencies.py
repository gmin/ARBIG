#!/usr/bin/env python3
"""
检查ARBIG系统依赖包安装情况
"""

import sys
import importlib

def check_dependency(module_name, package_name=None):
    """检查单个依赖包"""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name or module_name}: {version}")
        return True
    except ImportError:
        print(f"❌ {package_name or module_name}: 未安装")
        return False

def main():
    """主函数"""
    print("🔍 ARBIG系统依赖检查")
    print("=" * 50)
    
    # 核心交易依赖
    print("\n📊 核心交易依赖:")
    core_deps = [
        ("vnpy", "VeNpy"),
        ("vnpy_ctp", "VeNpy-CTP"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
    ]
    
    core_ok = all(check_dependency(mod, name) for mod, name in core_deps)
    
    # Web服务依赖
    print("\n🌐 Web服务依赖:")
    web_deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("websockets", "WebSockets"),
        ("pydantic", "Pydantic"),
    ]
    
    web_ok = all(check_dependency(mod, name) for mod, name in web_deps)
    
    # 系统工具依赖
    print("\n🔧 系统工具依赖:")
    tool_deps = [
        ("psutil", "PSUtil"),
        ("yaml", "PyYAML"),
        ("pytest", "PyTest"),
        ("loguru", "Loguru"),
    ]
    
    tool_ok = all(check_dependency(mod, name) for mod, name in tool_deps)
    
    # 总结
    print("\n" + "=" * 50)
    if core_ok and web_ok and tool_ok:
        print("🎉 所有依赖安装完成！")
        print("\n📋 下一步:")
        print("1. 配置CTP账户: vi config/ctp_sim.json")
        print("2. 启动Web服务: python web_admin/run_web_monitor.py --mode standalone")
        print("3. 访问监控界面: http://localhost:8000")
        return 0
    else:
        print("❌ 部分依赖缺失，请运行: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    exit(main())
