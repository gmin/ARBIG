#!/usr/bin/env python3
"""
ARBIG服务启动管理脚本
统一管理策略服务和专业回测服务的启动
"""

import subprocess
import time
import sys
import os
import signal
import requests
from typing import List, Dict

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.services = []
        self.running = True
    
    def start_service(self, name: str, command: List[str], port: int, check_url: str = None):
        """启动服务"""
        print(f"🚀 启动 {name}...")
        
        try:
            # 启动服务进程
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # 记录服务信息
            service_info = {
                "name": name,
                "process": process,
                "port": port,
                "check_url": check_url,
                "command": " ".join(command)
            }
            self.services.append(service_info)
            
            print(f"✅ {name} 启动中... (PID: {process.pid})")
            
            # 等待服务启动
            if check_url:
                self.wait_for_service(name, check_url, port)
            
            return True
            
        except Exception as e:
            print(f"❌ {name} 启动失败: {e}")
            return False
    
    def wait_for_service(self, name: str, check_url: str, port: int, timeout: int = 30):
        """等待服务启动完成"""
        print(f"⏳ 等待 {name} 启动完成...")
        
        for i in range(timeout):
            try:
                response = requests.get(check_url, timeout=2)
                if response.status_code == 200:
                    print(f"✅ {name} 启动成功! (端口: {port})")
                    return True
            except:
                pass
            
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                print(f"   等待中... ({i}/{timeout}秒)")
        
        print(f"⚠️ {name} 启动超时，但进程可能仍在启动中")
        return False
    
    def check_services_status(self):
        """检查所有服务状态"""
        print("\n📊 服务状态检查:")
        print("=" * 50)
        
        for service in self.services:
            name = service["name"]
            process = service["process"]
            port = service["port"]
            check_url = service["check_url"]
            
            # 检查进程状态
            if process.poll() is None:
                process_status = "✅ 运行中"
            else:
                process_status = f"❌ 已停止 (退出码: {process.returncode})"
            
            # 检查网络状态
            network_status = "❌ 不可达"
            if check_url:
                try:
                    response = requests.get(check_url, timeout=3)
                    if response.status_code == 200:
                        network_status = "✅ 可访问"
                except:
                    pass
            
            print(f"{name}:")
            print(f"  进程状态: {process_status}")
            print(f"  网络状态: {network_status}")
            print(f"  端口: {port}")
            print(f"  PID: {process.pid}")
            print()
    
    def stop_all_services(self):
        """停止所有服务"""
        print("\n🛑 停止所有服务...")
        
        for service in self.services:
            name = service["name"]
            process = service["process"]
            
            if process.poll() is None:
                print(f"🛑 停止 {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ {name} 已停止")
                except subprocess.TimeoutExpired:
                    print(f"⚠️ {name} 强制停止...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"❌ 停止 {name} 失败: {e}")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在停止服务...")
        self.running = False
        self.stop_all_services()
        sys.exit(0)

def main():
    """主函数"""
    print("🎯 ARBIG服务管理器")
    print("=" * 50)
    
    manager = ServiceManager()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    # 定义服务配置
    services_config = [
        {
            "name": "策略服务",
            "command": [sys.executable, "services/strategy_service/main.py"],
            "port": 8002,
            "check_url": "http://localhost:8002/"
        },
        {
            "name": "专业回测服务",
            "command": [sys.executable, "services/strategy_service/backtesting/professional_backtest_server.py"],
            "port": 8003,
            "check_url": "http://localhost:8003/"
        }
    ]
    
    # 启动所有服务
    print("🚀 启动ARBIG服务集群...")
    success_count = 0
    
    for config in services_config:
        if manager.start_service(**config):
            success_count += 1
        time.sleep(2)  # 服务间启动间隔
    
    print(f"\n🎉 服务启动完成: {success_count}/{len(services_config)} 个服务成功启动")
    
    if success_count > 0:
        print("\n📍 服务访问地址:")
        print("  策略服务: http://localhost:8002")
        print("  策略API文档: http://localhost:8002/docs")
        print("  专业回测服务: http://localhost:8003")
        print("  回测API文档: http://localhost:8003/docs")
        
        print("\n🧪 快速测试命令:")
        print("  curl http://localhost:8002/")
        print("  curl http://localhost:8002/strategies/large_order_following/quick_test -X POST -H 'Content-Type: application/json' -d '{\"test_days\": 7}'")
        print("  curl http://localhost:8003/backtest/health")
        
        # 定期检查服务状态
        try:
            while manager.running:
                time.sleep(30)  # 每30秒检查一次
                manager.check_services_status()
        except KeyboardInterrupt:
            pass
    
    manager.stop_all_services()
    print("👋 所有服务已停止")

if __name__ == "__main__":
    main()
