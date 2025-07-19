#!/usr/bin/env python3
"""
ARBIG交易功能综合测试脚本
提供多种测试选项
"""

import sys
import time
import subprocess
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

def show_menu():
    """显示测试菜单"""
    print("\n" + "=" * 60)
    print("🧪 ARBIG交易功能测试")
    print("=" * 60)
    print("请选择测试方式:")
    print()
    print("1. 快速下单测试 (直接调用服务)")
    print("2. Web API下单测试 (通过API接口)")
    print("3. 完整交易测试 (详细测试流程)")
    print("4. 启动Web界面进行手动测试")
    print("5. 查看测试说明")
    print("0. 退出")
    print()

def run_quick_order_test():
    """运行快速下单测试"""
    try:
        logger.info("🚀 启动快速下单测试...")
        result = subprocess.run([sys.executable, "quick_order_test.py"], 
                              cwd=project_root, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"快速下单测试失败: {e}")
        return False

def run_web_api_test():
    """运行Web API测试"""
    try:
        logger.info("🌐 启动Web API下单测试...")
        
        # 首先启动后端服务
        logger.info("启动后端服务...")
        backend_process = subprocess.Popen([
            sys.executable, "main.py", "--auto-start"
        ], cwd=project_root)
        
        # 等待后端启动
        time.sleep(8)
        
        # 运行Web API测试
        result = subprocess.run([sys.executable, "test_web_trading.py"], 
                              cwd=project_root, capture_output=False)
        
        # 停止后端服务
        backend_process.terminate()
        backend_process.wait()
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Web API测试失败: {e}")
        return False

def run_full_trading_test():
    """运行完整交易测试"""
    try:
        logger.info("🔬 启动完整交易测试...")
        result = subprocess.run([sys.executable, "test_trading.py"], 
                              cwd=project_root, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"完整交易测试失败: {e}")
        return False

def start_web_interface():
    """启动Web界面进行手动测试"""
    try:
        logger.info("🎨 启动Web界面...")
        
        # 启动后端服务
        logger.info("启动后端服务...")
        backend_process = subprocess.Popen([
            sys.executable, "main.py", "--auto-start"
        ], cwd=project_root)
        
        # 等待后端启动
        time.sleep(5)
        
        # 启动前端服务
        frontend_dir = project_root / "web_monitor" / "frontend"
        if frontend_dir.exists():
            logger.info("启动前端服务...")
            logger.info("前端地址: http://localhost:3000")
            logger.info("API文档: http://localhost:8000/api/docs")
            logger.info("按 Ctrl+C 停止服务")
            
            try:
                subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)
            except KeyboardInterrupt:
                logger.info("用户停止服务")
        else:
            logger.warning("前端目录不存在，仅启动后端服务")
            logger.info("API文档: http://localhost:8000/api/docs")
            logger.info("按 Ctrl+C 停止服务")
            
            try:
                backend_process.wait()
            except KeyboardInterrupt:
                logger.info("用户停止服务")
        
        # 停止后端服务
        backend_process.terminate()
        backend_process.wait()
        
        return True
        
    except Exception as e:
        logger.error(f"启动Web界面失败: {e}")
        return False

def show_test_instructions():
    """显示测试说明"""
    print("\n" + "=" * 60)
    print("📖 ARBIG交易测试说明")
    print("=" * 60)
    print()
    print("🎯 测试目标:")
    print("验证ARBIG系统的下单功能是否正常工作")
    print()
    print("📋 测试内容:")
    print("1. CTP连接测试")
    print("2. 账户信息查询")
    print("3. 行情数据获取")
    print("4. 限价单发送")
    print("5. 订单状态查询")
    print("6. 订单撤销")
    print()
    print("⚠️ 注意事项:")
    print("1. 测试使用的是CTP仿真环境")
    print("2. 测试订单价格设置较低，不会立即成交")
    print("3. 所有测试订单会在测试结束后自动撤销")
    print("4. 请确保CTP账户有足够的资金")
    print("5. 测试期间请勿手动操作CTP客户端")
    print()
    print("🔧 测试方式说明:")
    print("1. 快速测试: 直接调用交易服务，速度快")
    print("2. Web API测试: 通过Web API接口，测试完整链路")
    print("3. 完整测试: 详细的测试流程，包含所有步骤")
    print("4. Web界面: 通过浏览器手动测试")
    print()
    print("📊 测试结果:")
    print("- ✓ 表示测试通过")
    print("- ✗ 表示测试失败")
    print("- ⚠ 表示警告或需要注意的问题")
    print()

def main():
    """主函数"""
    while True:
        show_menu()
        
        try:
            choice = input("请选择 (0-5): ").strip()
            
            if choice == "0":
                print("👋 退出测试")
                break
            elif choice == "1":
                success = run_quick_order_test()
                if success:
                    print("✅ 快速下单测试完成")
                else:
                    print("❌ 快速下单测试失败")
            elif choice == "2":
                success = run_web_api_test()
                if success:
                    print("✅ Web API测试完成")
                else:
                    print("❌ Web API测试失败")
            elif choice == "3":
                success = run_full_trading_test()
                if success:
                    print("✅ 完整交易测试完成")
                else:
                    print("❌ 完整交易测试失败")
            elif choice == "4":
                start_web_interface()
            elif choice == "5":
                show_test_instructions()
            else:
                print("❌ 无效选择，请重新输入")
            
            if choice in ["1", "2", "3"]:
                input("\n按回车键继续...")
                
        except KeyboardInterrupt:
            print("\n👋 退出测试")
            break
        except Exception as e:
            print(f"❌ 操作异常: {e}")
            input("\n按回车键继续...")

if __name__ == "__main__":
    main()
