#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG量化交易系统统一启动脚本
简化的启动管理，支持不同的启动模式
"""

import sys
import os
import subprocess
import time
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    # 检查核心依赖
    core_deps = ["vnpy", "fastapi", "uvicorn", "pandas", "numpy"]
    missing_deps = []
    
    for dep in core_deps:
        try:
            __import__(dep)
            print(f"✅ {dep}: 已安装")
        except ImportError:
            print(f"❌ {dep}: 未安装")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n❌ 缺少依赖包: {', '.join(missing_deps)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    # 检查配置文件
    config_files = ["config/ctp_sim.json", "config/config.py"]
    for config_file in config_files:
        if not Path(config_file).exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        else:
            print(f"✅ 配置文件: {config_file}")
    
    return True

def start_service(name, command, port, check_port=True):
    """启动服务"""
    print(f"\n🚀 启动 {name}...")
    
    if check_port:
        # 检查端口是否被占用
        result = subprocess.run(
            f"netstat -tlnp | grep ':{port} '",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"⚠️  端口 {port} 已被占用")
            print(f"占用详情: {result.stdout.strip()}")
            return None
    
    try:
        # 启动服务
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 等待服务启动
        time.sleep(3)
        
        if process.poll() is None:
            print(f"✅ {name} 启动成功 (PID: {process.pid})")
            return process
        else:
            print(f"❌ {name} 启动失败")
            return None
            
    except Exception as e:
        print(f"❌ 启动 {name} 时发生错误: {e}")
        return None

def show_menu():
    """显示启动菜单"""
    print("\n" + "="*60)
    print("🏛️  ARBIG量化交易系统 v2.0")
    print("🔄 微服务架构 - 统一启动管理")
    print("="*60)
    print("\n请选择启动模式:")
    print("1. 🚀 启动完整系统 (推荐)")
    print("2. 🔧 仅启动Web管理界面")
    print("3. 📊 仅启动核心交易服务")
    print("4. 🎯 仅启动策略管理服务")
    print("5. 🧪 运行系统测试")
    print("0. 👋 退出")
    print("="*60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG量化交易系统启动器')
    parser.add_argument('--mode', type=str, choices=['full', 'web', 'trading', 'strategy', 'test'],
                       help='启动模式: full(完整系统), web(Web界面), trading(交易服务), strategy(策略服务), test(测试)')
    parser.add_argument('--auto', action='store_true', help='自动启动，不显示菜单')
    
    args = parser.parse_args()
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请修复后重试")
        sys.exit(1)
    
    # 自动模式
    if args.auto and args.mode:
        if args.mode == 'full':
            start_full_system()
        elif args.mode == 'web':
            start_web_only()
        elif args.mode == 'trading':
            start_trading_only()
        elif args.mode == 'strategy':
            start_strategy_only()
        elif args.mode == 'test':
            run_tests()
        return
    
    # 交互模式
    while True:
        show_menu()
        try:
            choice = input("\n请选择 (0-5): ").strip()

            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                start_full_system()
                break
            elif choice == "2":
                start_web_only()
                break
            elif choice == "3":
                start_trading_only()
                break
            elif choice == "4":
                start_strategy_only()
                break
            elif choice == "5":
                run_tests()
                input("\n按Enter键继续...")
            else:
                print("❌ 无效选项，请重新选择")
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break

def start_full_system():
    """启动完整系统"""
    print("\n🚀 启动完整ARBIG系统...")

    processes = []

    # 启动核心交易服务
    trading_process = start_service(
        "核心交易服务",
        "conda run -n vnpy python services/trading_service/main.py --port 8001",
        8001
    )

    if not trading_process:
        print("❌ 核心交易服务启动失败")
        return
    processes.append(trading_process)

    # 启动策略管理服务
    strategy_process = start_service(
        "策略管理服务",
        "conda run -n vnpy python services/strategy_service/main.py --port 8002",
        8002
    )

    if not strategy_process:
        print("⚠️  策略管理服务启动失败，但系统将继续运行")
    else:
        processes.append(strategy_process)

    # 启动Web管理服务
    web_process = start_service(
        "Web管理服务",
        "conda run -n vnpy python services/web_admin_service/main.py --port 80",
        80
    )

    if not web_process:
        print("❌ Web管理服务启动失败")
        for p in processes:
            p.terminate()
        return
    processes.append(web_process)

    print("\n✅ ARBIG完整系统启动成功！")
    print("🎛️  Web管理界面: http://localhost")
    print("📊 交易页面: http://localhost/trading")
    print("🎯 策略管理: http://localhost/strategy")
    print("📖 交易API文档: http://localhost:8001/docs")
    if strategy_process:
        print("🔧 策略API文档: http://localhost:8002/docs")

    try:
        input("\n按Enter键停止系统...")
    except KeyboardInterrupt:
        pass

    print("\n🛑 正在停止系统...")
    for process in processes:
        process.terminate()
    print("✅ 系统已停止")

def start_web_only():
    """仅启动Web管理界面"""
    print("\n🔧 启动Web管理界面...")
    
    web_process = start_service(
        "Web管理服务",
        "conda run -n vnpy python services/web_admin_service/main.py --port 8080",
        8080
    )
    
    if web_process:
        print("\n✅ Web管理界面启动成功！")
        print("🎛️  访问地址: http://localhost")
        
        try:
            input("\n按Enter键停止服务...")
        except KeyboardInterrupt:
            pass
        
        web_process.terminate()
        print("✅ Web服务已停止")

def start_trading_only():
    """仅启动核心交易服务"""
    print("\n📊 启动核心交易服务...")
    
    trading_process = start_service(
        "核心交易服务",
        "conda run -n vnpy python services/trading_service/main.py --port 8001",
        8001
    )
    
    if trading_process:
        print("\n✅ 核心交易服务启动成功！")
        print("📖 API文档: http://localhost:8001/docs")
        
        try:
            input("\n按Enter键停止服务...")
        except KeyboardInterrupt:
            pass
        
        trading_process.terminate()
        print("✅ 交易服务已停止")

def start_strategy_only():
    """仅启动策略管理服务"""
    print("\n🎯 启动策略管理服务...")

    strategy_process = start_service(
        "策略管理服务",
        "conda run -n vnpy python services/strategy_service/main.py --port 8002",
        8002
    )

    if strategy_process:
        print("\n✅ 策略管理服务启动成功！")
        print("🔧 策略服务API: http://localhost:8002")
        print("📖 API文档: http://localhost:8002/docs")

        try:
            input("\n按Enter键停止服务...")
        except KeyboardInterrupt:
            pass

        strategy_process.terminate()
        print("✅ 策略服务已停止")

def run_tests():
    """运行系统测试"""
    print("\n🧪 运行系统测试...")
    
    test_files = [
        "tests/ctp_connection_test.py",
        "tests/test_order_placement.py",
        "tests/run_all_tests.py"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n▶️  运行 {test_file}...")
            result = subprocess.run(
                f"conda run -n vnpy python {test_file}",
                shell=True
            )
            if result.returncode == 0:
                print(f"✅ {test_file} 测试通过")
            else:
                print(f"❌ {test_file} 测试失败")
        else:
            print(f"⚠️  测试文件不存在: {test_file}")

if __name__ == "__main__":
    main()
