#!/usr/bin/env python3
"""
ARBIG 量化交易系统启动脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    ARBIG 量化交易系统                          ║
    ║                  Algorithmic Trading System                  ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  🎛️  Web管理系统 (web_admin)    - 交易管理、风控、监控        ║
    ║  🔧  交易API服务 (trading_api)  - 核心业务API接口            ║
    ║  ⚙️   核心系统 (core)           - 交易引擎、服务组件          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    # 检查vnpy环境
    try:
        import vnpy
        print(f"✅ VNPy版本: {vnpy.__version__}")
    except ImportError:
        print("❌ 未找到VNPy，请确保在vnpy环境中运行")
        return False
    
    # 检查配置文件
    config_files = [
        "config/ctp_sim.json",
        "config.yaml"
    ]
    
    for config_file in config_files:
        if not Path(config_file).exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        else:
            print(f"✅ 配置文件: {config_file}")
    
    return True

def start_service(service_name, command, port=None):
    """启动服务"""
    print(f"\n🚀 启动 {service_name}...")
    
    try:
        # 检查端口是否被占用
        if port:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"⚠️  端口 {port} 已被占用，{service_name} 可能已在运行")
                return None
        
        # 启动服务
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待一下确保服务启动
        time.sleep(2)
        
        if process.poll() is None:
            print(f"✅ {service_name} 启动成功 (PID: {process.pid})")
            if port:
                print(f"   访问地址: http://localhost:{port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {service_name} 启动失败")
            print(f"   错误信息: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ 启动 {service_name} 时发生错误: {e}")
        return None

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请修复后重试")
        return 1
    
    print("\n✅ 环境检查通过")
    
    # 显示启动选项
    print("\n📋 启动选项:")
    print("1. 启动Web管理系统 (web_admin)")
    print("2. 启动交易API服务 (trading_api)")
    print("3. 启动完整系统 (web_admin + trading_api)")
    print("4. 运行下单测试")
    print("5. 运行信号监控测试")
    print("0. 退出")
    
    while True:
        try:
            choice = input("\n请选择启动选项 (0-5): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                return 0
            
            elif choice == "1":
                # 启动Web管理系统
                process = start_service(
                    "Web管理系统",
                    "python -m web_admin.app",
                    8000
                )
                if process:
                    print("\n🎛️  Web管理系统已启动")
                    print("   功能: 交易管理、风控管理、系统监控")
                    print("   访问: http://localhost:8000")
                    input("\n按Enter键停止服务...")
                    process.terminate()
                break
            
            elif choice == "2":
                # 启动交易API服务
                process = start_service(
                    "交易API服务",
                    "python -m trading_api.app",
                    8001
                )
                if process:
                    print("\n🔧 交易API服务已启动")
                    print("   功能: 交易API、账户API、行情API")
                    print("   访问: http://localhost:8001")
                    input("\n按Enter键停止服务...")
                    process.terminate()
                break
            
            elif choice == "3":
                # 启动完整系统
                print("\n🚀 启动完整ARBIG系统...")
                
                # 启动交易API服务
                api_process = start_service(
                    "交易API服务",
                    "python -m trading_api.app",
                    8001
                )
                
                # 启动Web管理系统
                web_process = start_service(
                    "Web管理系统", 
                    "python -m web_admin.app",
                    8000
                )
                
                if api_process and web_process:
                    print("\n🎉 ARBIG系统启动完成！")
                    print("   🔧 交易API服务: http://localhost:8001")
                    print("   🎛️  Web管理系统: http://localhost:8000")
                    print("\n系统功能:")
                    print("   • 实时交易监控")
                    print("   • 交易信号跟踪") 
                    print("   • 风控管理")
                    print("   • 紧急暂停/平仓")
                    print("   • 系统状态监控")
                    
                    input("\n按Enter键停止所有服务...")
                    
                    if api_process:
                        api_process.terminate()
                    if web_process:
                        web_process.terminate()
                    
                    print("✅ 所有服务已停止")
                break
            
            elif choice == "4":
                # 运行下单测试
                print("\n🧪 运行下单测试...")
                result = subprocess.run(
                    "python test_order_placement.py",
                    shell=True
                )
                if result.returncode == 0:
                    print("✅ 下单测试完成")
                else:
                    print("❌ 下单测试失败")
                input("\n按Enter键继续...")
            
            elif choice == "5":
                # 运行信号监控测试
                print("\n🧪 运行信号监控测试...")
                result = subprocess.run(
                    "python test_signal_monitoring.py",
                    shell=True
                )
                if result.returncode == 0:
                    print("✅ 信号监控测试完成")
                else:
                    print("❌ 信号监控测试失败")
                input("\n按Enter键继续...")
            
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            return 0
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
