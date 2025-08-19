#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ARBIG系统服务启动脚本
"""

import subprocess
import time
import sys
import os
from datetime import datetime

def run_command(cmd, background=False):
    """执行命令"""
    try:
        if background:
            process = subprocess.Popen(cmd, shell=True)
            return process.pid
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_port(port):
    """检查端口是否被占用"""
    success, stdout, stderr = run_command(f"netstat -tlnp | grep ':{port}'")
    return bool(stdout.strip())

def check_service_response(url, timeout=10):
    """检查服务是否响应"""
    for i in range(timeout):
        success, stdout, stderr = run_command(f"curl -s --connect-timeout 2 {url}")
        if success and stdout.strip():
            return True
        time.sleep(1)
    return False

def kill_existing_services():
    """杀掉现有的服务进程"""
    print("🔄 清理现有服务进程...")
    
    # 杀掉可能存在的进程
    services_to_kill = [
        "python.*trading_service/main.py",
        "python.*strategy_service/main.py", 
        "python.*web_admin_service/main.py"
    ]
    
    for pattern in services_to_kill:
        run_command(f"pkill -f '{pattern}'")
    
    # 杀掉占用端口的进程
    ports_to_free = [8001, 8002, 8080]
    for port in ports_to_free:
        run_command(f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true")
    
    time.sleep(2)
    print("✅ 服务进程清理完成")

def start_trading_service():
    """启动交易服务"""
    print("\n🚀 启动交易服务 (端口 8001)...")
    
    if check_port(8001):
        print("⚠️  端口8001已被占用，尝试清理...")
        run_command("lsof -ti:8001 | xargs kill -9 2>/dev/null || true")
        time.sleep(2)
    
    os.chdir("/root/ARBIG/services/trading_service")
    cmd = "conda run -n vnpy python main.py --port 8001 > /root/ARBIG/logs/trading_service.log 2>&1 &"
    pid = run_command(cmd, background=True)
    
    print(f"   进程ID: {pid}")
    print("   等待服务启动...")
    
    if check_service_response("http://localhost:8001/"):
        print("✅ 交易服务启动成功")
        return True
    else:
        print("❌ 交易服务启动失败")
        return False

def start_strategy_service():
    """启动策略服务"""
    print("\n🧠 启动策略服务 (端口 8002)...")
    
    if check_port(8002):
        print("⚠️  端口8002已被占用，尝试清理...")
        run_command("lsof -ti:8002 | xargs kill -9 2>/dev/null || true")
        time.sleep(2)
    
    os.chdir("/root/ARBIG/services/strategy_service")
    cmd = "conda run -n vnpy python main.py > /root/ARBIG/logs/strategy_service.log 2>&1 &"
    pid = run_command(cmd, background=True)
    
    print(f"   进程ID: {pid}")
    print("   等待服务启动...")
    
    if check_service_response("http://localhost:8002/"):
        print("✅ 策略服务启动成功")
        return True
    else:
        print("❌ 策略服务启动失败")
        return False

def start_web_admin_service():
    """启动Web管理服务"""
    print("\n🌐 启动Web管理服务 (端口 8080)...")
    
    if check_port(8080):
        print("⚠️  端口8080已被占用，尝试清理...")
        run_command("lsof -ti:8080 | xargs kill -9 2>/dev/null || true")
        time.sleep(2)
    
    os.chdir("/root/ARBIG/services/web_admin_service")
    cmd = "conda run -n vnpy python main.py --port 8080 > /root/ARBIG/logs/web_admin_service.log 2>&1 &"
    pid = run_command(cmd, background=True)
    
    print(f"   进程ID: {pid}")
    print("   等待服务启动...")
    
    if check_service_response("http://localhost:8080/"):
        print("✅ Web管理服务启动成功")
        return True
    else:
        print("❌ Web管理服务启动失败")
        return False

def main():
    """主函数"""
    print("🚀 ARBIG系统服务启动器")
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 切换到项目根目录
    os.chdir("/root/ARBIG")
    
    # 创建日志目录
    os.makedirs("/root/ARBIG/logs", exist_ok=True)
    
    # 清理现有服务
    kill_existing_services()
    
    # 启动服务
    services_started = []
    
    if start_trading_service():
        services_started.append("交易服务")
    
    if start_strategy_service():
        services_started.append("策略服务")
    
    if start_web_admin_service():
        services_started.append("Web管理服务")
    
    # 启动总结
    print("\n" + "=" * 60)
    print("📋 启动总结")
    print(f"✅ 成功启动的服务: {len(services_started)}/3")
    
    for service in services_started:
        print(f"   • {service}")
    
    if len(services_started) == 3:
        print("\n🎉 所有服务启动成功！")
        print("\n🌍 访问地址:")
        print("   • 交易服务: http://localhost:8001")
        print("   • 策略服务: http://localhost:8002") 
        print("   • Web管理界面: http://localhost:8080")
        print("\n📊 运行系统测试:")
        print("   python scripts/simple_system_test.py")
    else:
        failed_services = 3 - len(services_started)
        print(f"\n⚠️  有 {failed_services} 个服务启动失败")
        print("💡 建议检查日志文件:")
        print("   • /root/ARBIG/logs/trading_service.log")
        print("   • /root/ARBIG/logs/strategy_service.log")
        print("   • /root/ARBIG/logs/web_admin_service.log")

if __name__ == "__main__":
    main()
