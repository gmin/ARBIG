#!/usr/bin/env python3
"""
ARBIG系统快速帮助
"""

def show_help():
    print("🚀 ARBIG量化交易系统 - 快速帮助")
    print("=" * 50)
    
    print("\n📋 推荐启动方式:")
    print("python start_arbig.py")
    print("然后选择选项1: 启动ARBIG Web管理系统")
    
    print("\n🌐 访问地址:")
    print("- 主页面: http://localhost:8000")
    print("- 策略监控: http://localhost:8000/strategy_monitor.html?strategy=shfe_quant")
    print("- API文档: http://localhost:8000/api/docs")
    
    print("\n⚙️ 其他启动方式:")
    print("python main.py --auto-start --demo-mode  # 演示模式")
    print("python main.py --auto-start              # 完整交易模式")
    print("python main.py --api-only               # 仅API服务")
    
    print("\n🔧 测试功能:")
    print("python run_all_tests.py                 # 运行所有测试")
    print("python run_trading_tests.py             # 运行交易测试")
    print("python tests/test_order_placement.py    # 下单测试")
    
    print("\n📊 诊断工具:")
    print("python diagnose_web_issue.py            # Web问题诊断")
    
    print("\n🔧 诊断工具:")
    print("python help.py --check                  # 检查系统状态")
    print("python help.py --diagnose               # 诊断常见问题")

    print("\n⚠️ 重要提醒:")
    print("1. 必须在vnpy环境下运行:")
    print("   conda activate vnpy")
    print("2. 确保在ARBIG目录下运行")
    print("3. 首次运行建议使用演示模式测试")

def check_system():
    """检查系统状态"""
    import subprocess
    import requests

    print("🔍 ARBIG系统状态检查")
    print("=" * 40)

    # 检查进程
    try:
        result = subprocess.run("ps aux | grep python | grep main.py",
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print("✅ ARBIG进程正在运行")
        else:
            print("❌ ARBIG进程未运行")
    except:
        print("❌ 无法检查进程状态")

    # 检查端口
    try:
        result = subprocess.run("netstat -tlnp | grep :8000",
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print("✅ 端口8000正在监听")
        else:
            print("❌ 端口8000未被占用")
    except:
        print("❌ 无法检查端口状态")

    # 检查API
    try:
        response = requests.get("http://localhost:8000/api/v1/system/status", timeout=5)
        if response.status_code == 200:
            print("✅ API服务正常")
        else:
            print(f"❌ API服务异常: {response.status_code}")
    except:
        print("❌ 无法连接API服务")

def diagnose():
    """诊断常见问题"""
    print("🔧 ARBIG问题诊断")
    print("=" * 40)

    print("\n1. 检查Python环境:")
    import sys
    print(f"   Python版本: {sys.version}")
    print(f"   当前路径: {sys.executable}")

    print("\n2. 检查vnpy环境:")
    try:
        import vnpy
        print(f"   ✅ VNPy版本: {vnpy.__version__}")
    except ImportError:
        print("   ❌ VNPy未安装或环境不正确")

    print("\n3. 检查配置文件:")
    from pathlib import Path
    config_files = ["config/ctp_sim.json", "config.yaml"]
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"   ✅ {config_file}")
        else:
            print(f"   ❌ {config_file} 不存在")

    print("\n4. 建议解决方案:")
    print("   - 确保在vnpy环境下运行: conda activate vnpy")
    print("   - 检查配置文件是否正确")
    print("   - 尝试重启系统: python start_arbig.py")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            check_system()
        elif sys.argv[1] == "--diagnose":
            diagnose()
        else:
            show_help()
    else:
        show_help()
