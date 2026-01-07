#!/usr/bin/env python3
"""
ARBIG系统强力清理脚本
彻底清理所有相关进程和端口
"""

import subprocess
import time
import sys
import os

def run_command(cmd, description="", ignore_errors=True):
    """运行命令"""
    if description:
        print(f"🔧 {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            if not ignore_errors:
                print(f"   ❌ 错误: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 超时")
        return False
    except Exception as e:
        if not ignore_errors:
            print(f"   ❌ 异常: {e}")
        return False

def force_cleanup():
    """强力清理"""
    print("🛑 ARBIG系统强力清理")
    print("=" * 50)
    
    # 1. 查看当前状态
    print("\n📊 清理前状态检查:")
    run_command("ps aux | grep python | grep -E '(main.py|start_with_logs|trading_service|strategy_service|web_admin_service)' | grep -v grep", "Python进程")
    run_command("netstat -tlnp | grep -E '(8001|8002|8003|80)'", "端口占用")
    
    # 2. 停止start_with_logs进程
    print("\n🛑 停止启动脚本进程:")
    run_command("pkill -f 'start_with_logs'", "停止start_with_logs")
    run_command("pkill -9 -f 'start_with_logs'", "强制停止start_with_logs")
    
    # 3. 停止各个服务进程
    print("\n🛑 停止服务进程:")
    services = [
        "trading_service/main.py",
        "strategy_service/main.py", 
        "web_admin_service/main.py",
        "professional_backtest_server.py"
    ]
    
    for service in services:
        run_command(f"pkill -f '{service}'", f"停止 {service}")
        time.sleep(0.5)
        run_command(f"pkill -9 -f '{service}'", f"强制停止 {service}")
    
    # 4. 停止所有相关Python进程
    print("\n🛑 停止所有相关Python进程:")
    run_command("pkill -f 'python.*main.py'", "停止Python main.py进程")
    run_command("pkill -9 -f 'python.*main.py'", "强制停止Python main.py进程")
    run_command("pkill -f 'uvicorn'", "停止uvicorn进程")
    run_command("pkill -9 -f 'uvicorn'", "强制停止uvicorn进程")
    run_command("pkill -f 'conda run'", "停止conda run进程")
    run_command("pkill -9 -f 'conda run'", "强制停止conda run进程")
    
    # 5. 强制释放端口
    print("\n🔓 强制释放端口:")
    ports = [8001, 8002, 8003, 80]
    for port in ports:
        run_command(f"sudo fuser -k {port}/tcp", f"释放端口 {port}")
        time.sleep(0.2)
    
    # 6. 使用lsof强制释放端口
    print("\n🔓 使用lsof强制释放端口:")
    for port in ports:
        # 查找占用端口的进程
        result = subprocess.run(f"lsof -ti :{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    run_command(f"kill -9 {pid.strip()}", f"强制杀死进程 {pid.strip()} (端口 {port})")
    
    # 7. 等待清理完成
    print("\n⏳ 等待清理完成...")
    time.sleep(5)
    
    # 8. 验证清理结果
    print("\n✅ 清理结果验证:")
    
    # 检查剩余进程
    result = subprocess.run(
        "ps aux | grep python | grep -E '(main.py|start_with_logs|trading_service|strategy_service|web_admin_service)' | grep -v grep",
        shell=True, capture_output=True, text=True
    )
    
    if result.stdout.strip():
        print("⚠️ 仍有进程残留:")
        for line in result.stdout.strip().split('\n'):
            parts = line.split()
            pid = parts[1]
            cmd = ' '.join(parts[10:])
            print(f"   PID {pid}: {cmd}")
            # 强制杀死残留进程
            run_command(f"kill -9 {pid}", f"强制杀死残留进程 {pid}")
    else:
        print("✅ 没有残留进程")
    
    # 检查端口占用
    result = subprocess.run(
        "netstat -tlnp | grep -E '(8001|8002|8003|80)'",
        shell=True, capture_output=True, text=True
    )
    
    if result.stdout.strip():
        print("⚠️ 仍有端口被占用:")
        print(result.stdout)
        
        # 再次尝试释放
        for port in ports:
            run_command(f"sudo fuser -k {port}/tcp", f"再次释放端口 {port}")
    else:
        print("✅ 所有端口已释放")
    
    print("\n" + "=" * 50)
    print("🎯 强力清理完成")
    print("=" * 50)

def check_cleanup_result():
    """检查清理结果"""
    print("\n🔍 最终状态检查:")
    print("-" * 30)
    
    # 检查进程
    result = subprocess.run(
        "ps aux | grep python | grep -E '(main.py|start_with_logs|trading_service|strategy_service|web_admin_service)' | grep -v grep",
        shell=True, capture_output=True, text=True
    )
    
    if result.stdout.strip():
        print("❌ 仍有进程运行:")
        print(result.stdout)
        return False
    else:
        print("✅ 没有相关进程运行")
    
    # 检查端口
    result = subprocess.run(
        "netstat -tlnp | grep -E '(8001|8002|8003|80)'",
        shell=True, capture_output=True, text=True
    )
    
    if result.stdout.strip():
        print("❌ 仍有端口被占用:")
        print(result.stdout)
        return False
    else:
        print("✅ 所有端口已释放")
    
    return True

def main():
    """主函数"""
    print("⚠️  这将强制停止所有ARBIG相关进程")
    response = input("确定要继续吗？(y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("❌ 清理已取消")
        return
    
    # 执行强力清理
    force_cleanup()
    
    # 检查清理结果
    success = check_cleanup_result()
    
    if success:
        print("\n🎉 清理成功！现在可以重新启动系统了")
        print("运行: python start_with_logs.py")
    else:
        print("\n⚠️ 清理可能不完整，建议重启系统或手动检查")

if __name__ == "__main__":
    main()