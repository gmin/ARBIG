#!/usr/bin/env python3
"""
实时日志查看工具
"""

import os
import time
import subprocess
from datetime import datetime

def get_latest_log_file():
    """获取最新的日志文件"""
    log_dir = "/root/ARBIG/logs"
    if not os.path.exists(log_dir):
        return None
    
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    if not log_files:
        return None
    
    # 获取最新的日志文件
    latest_file = max(log_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
    return os.path.join(log_dir, latest_file)

def watch_logs(keywords=None):
    """实时监控日志"""
    log_file = get_latest_log_file()
    if not log_file:
        print("❌ 没有找到日志文件")
        return
    
    print(f"📊 监控日志文件: {log_file}")
    if keywords:
        print(f"🔍 过滤关键词: {', '.join(keywords)}")
    print("=" * 80)
    
    try:
        # 使用tail -f命令实时监控日志
        if keywords:
            # 使用grep过滤关键词
            cmd = f"tail -f {log_file} | grep -E '({'|'.join(keywords)})'"
        else:
            cmd = f"tail -f {log_file}"
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, universal_newlines=True)
        
        print("🚀 开始实时监控日志 (按Ctrl+C停止)...")
        print("-" * 80)
        
        for line in iter(process.stdout.readline, ''):
            if line:
                # 添加时间戳
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {line.rstrip()}")
        
    except KeyboardInterrupt:
        print("\n⏹️  停止日志监控")
        process.terminate()
    except Exception as e:
        print(f"❌ 监控日志时出错: {e}")

def show_recent_logs(lines=50, keywords=None):
    """显示最近的日志"""
    log_file = get_latest_log_file()
    if not log_file:
        print("❌ 没有找到日志文件")
        return
    
    print(f"📊 显示最近{lines}行日志: {log_file}")
    if keywords:
        print(f"🔍 过滤关键词: {', '.join(keywords)}")
    print("=" * 80)
    
    try:
        if keywords:
            cmd = f"tail -{lines} {log_file} | grep -E '({'|'.join(keywords)})'"
        else:
            cmd = f"tail -{lines} {log_file}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        else:
            print("没有匹配的日志内容")
            
    except Exception as e:
        print(f"❌ 读取日志时出错: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("📋 ARBIG日志查看工具")
        print()
        print("用法:")
        print("  python scripts/watch_logs.py watch [关键词...]     # 实时监控日志")
        print("  python scripts/watch_logs.py recent [行数] [关键词...]  # 显示最近日志")
        print()
        print("示例:")
        print("  python scripts/watch_logs.py watch                # 监控所有日志")
        print("  python scripts/watch_logs.py watch CTP 连接       # 监控CTP连接相关日志")
        print("  python scripts/watch_logs.py recent 100           # 显示最近100行日志")
        print("  python scripts/watch_logs.py recent 50 今仓 昨仓  # 显示最近50行包含今昨仓的日志")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "watch":
        keywords = sys.argv[2:] if len(sys.argv) > 2 else None
        watch_logs(keywords)
    elif command == "recent":
        lines = 50
        keywords = None
        
        if len(sys.argv) > 2:
            try:
                lines = int(sys.argv[2])
                keywords = sys.argv[3:] if len(sys.argv) > 3 else None
            except ValueError:
                keywords = sys.argv[2:]
        
        show_recent_logs(lines, keywords)
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
