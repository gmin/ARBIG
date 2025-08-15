#!/usr/bin/env python3
"""
启动ARBIG系统并显示实时日志
"""

import sys
import os
import subprocess
import time
import signal
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def start_service_with_logs(service_name, command, port):
    """启动服务并显示日志"""
    print(f"🚀 启动 {service_name}...")
    
    try:
        # 启动服务，不重定向输出
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=project_root,
            universal_newlines=True
        )
        
        # 等待服务启动
        time.sleep(3)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            print(f"✅ {service_name} 启动成功 (PID: {process.pid})")
            return process
        else:
            print(f"❌ {service_name} 启动失败")
            return None
            
    except Exception as e:
        print(f"❌ 启动 {service_name} 时出错: {e}")
        return None

def monitor_log_file():
    """监控日志文件并显示"""
    log_dir = project_root / "logs"
    if not log_dir.exists():
        return
    
    # 找到最新的日志文件
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        return
    
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    
    print(f"📊 监控日志文件: {latest_log}")
    print("=" * 80)
    
    try:
        # 使用tail -f监控日志文件
        process = subprocess.Popen(
            f"tail -f {latest_log}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
                
    except Exception as e:
        print(f"❌ 监控日志时出错: {e}")

def main():
    """主函数"""
    print("🔍 检查运行环境...")
    
    # 检查conda环境
    try:
        result = subprocess.run("conda run -n vnpy python -c 'import vnpy'", 
                              shell=True, capture_output=True)
        if result.returncode == 0:
            print("✅ vnpy: 已安装")
        else:
            print("❌ vnpy: 未安装或环境有问题")
            return
    except:
        print("❌ conda环境检查失败")
        return
    
    print("\n🚀 启动ARBIG系统...")
    
    processes = []
    
    # 启动各个服务
    services = [
        ("核心交易服务", "conda run -n vnpy python services/trading_service/main.py --port 8001", 8001),
        ("策略管理服务", "conda run -n vnpy python services/strategy_service/main.py --port 8002", 8002),
        ("Web管理服务", "conda run -n vnpy python services/web_admin_service/main.py --port 80", 80),
    ]
    
    for service_name, command, port in services:
        process = start_service_with_logs(service_name, command, port)
        if process:
            processes.append((service_name, process))
        else:
            print(f"❌ {service_name} 启动失败，停止启动流程")
            # 停止已启动的服务
            for _, p in processes:
                p.terminate()
            return
    
    print("\n✅ ARBIG系统启动成功！")
    print("🎛️  Web管理界面: http://localhost")
    print("📊 交易页面: http://localhost/trading")
    print("🎯 策略管理: http://localhost/strategy")
    print("📖 交易API文档: http://localhost:8001/docs")
    print("🔧 策略API文档: http://localhost:8002/docs")
    print("\n" + "=" * 80)
    print("📊 实时日志输出 (按Ctrl+C停止系统):")
    print("=" * 80)
    
    # 定义信号处理函数
    def signal_handler(sig, frame):
        print("\n\n⏹️  正在停止ARBIG系统...")
        for service_name, process in processes:
            print(f"停止 {service_name}...")
            process.terminate()
        
        # 等待进程结束
        time.sleep(2)
        for service_name, process in processes:
            if process.poll() is None:
                print(f"强制停止 {service_name}...")
                process.kill()
        
        print("✅ ARBIG系统已停止")
        sys.exit(0)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动日志监控线程
    log_thread = threading.Thread(target=monitor_log_file, daemon=True)
    log_thread.start()
    
    # 主循环 - 保持程序运行
    try:
        while True:
            # 检查所有进程是否还在运行
            for service_name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️  {service_name} 意外停止")
            
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
