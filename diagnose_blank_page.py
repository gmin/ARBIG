#!/usr/bin/env python3
"""
诊断Web页面空白问题
"""

import requests
import json
import subprocess
import time

def test_web_pages():
    """测试各个Web页面"""
    print("🔍 测试Web页面访问...")
    
    pages = [
        ("主页面", "http://localhost:8000/"),
        ("测试页面", "http://localhost:8000/test_simple.html"),
        ("API状态", "http://localhost:8000/api/v1/system/status"),
        ("API文档", "http://localhost:8000/api/docs")
    ]
    
    for name, url in pages:
        try:
            response = requests.get(url, timeout=5)
            print(f"✅ {name}: HTTP {response.status_code}")
            
            if 'json' in response.headers.get('content-type', ''):
                try:
                    data = response.json()
                    print(f"   JSON响应: {data.get('success', 'N/A')}")
                except:
                    print("   JSON解析失败")
            else:
                content_length = len(response.text)
                print(f"   内容长度: {content_length} 字符")
                
                if content_length < 100:
                    print(f"   内容预览: {response.text[:100]}")
                    
        except Exception as e:
            print(f"❌ {name}: {e}")

def check_browser_compatibility():
    """检查浏览器兼容性问题"""
    print("\n🌐 浏览器兼容性检查...")
    
    print("常见的页面空白原因:")
    print("1. JavaScript错误 - 检查浏览器控制台(F12)")
    print("2. 网络问题 - 检查网络连接")
    print("3. 缓存问题 - 尝试强制刷新(Ctrl+Shift+R)")
    print("4. 浏览器扩展 - 尝试无痕模式")
    print("5. WebSocket连接失败 - 检查WebSocket支持")

def check_system_resources():
    """检查系统资源"""
    print("\n💻 系统资源检查...")
    
    try:
        # 检查进程
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        python_processes = [line for line in result.stdout.split('\n') if 'python' in line and 'main.py' in line]
        
        if python_processes:
            print("✅ ARBIG进程正在运行:")
            for proc in python_processes:
                parts = proc.split()
                if len(parts) >= 11:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    print(f"   PID: {pid}, CPU: {cpu}%, 内存: {mem}%")
        else:
            print("❌ 未找到ARBIG进程")
            
        # 检查端口
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        port_8000 = [line for line in result.stdout.split('\n') if ':8000' in line]
        
        if port_8000:
            print("✅ 端口8000正在监听:")
            for port in port_8000:
                print(f"   {port.strip()}")
        else:
            print("❌ 端口8000未在监听")
            
    except Exception as e:
        print(f"❌ 系统检查失败: {e}")

def generate_solutions():
    """生成解决方案"""
    print("\n🔧 解决方案建议:")
    
    print("\n1. 浏览器端解决方案:")
    print("   • 按F12打开开发者工具，查看Console标签页的错误信息")
    print("   • 按Ctrl+Shift+R强制刷新页面")
    print("   • 尝试无痕模式访问")
    print("   • 尝试不同的浏览器")
    print("   • 清空浏览器缓存和Cookie")
    
    print("\n2. 网络端解决方案:")
    print("   • 检查网络连接是否正常")
    print("   • 确认端口转发配置正确")
    print("   • 尝试直接访问服务器IP")
    
    print("\n3. 服务端解决方案:")
    print("   • 重启ARBIG系统")
    print("   • 检查系统日志")
    print("   • 尝试演示模式启动")
    
    print("\n4. 测试页面:")
    print("   • 访问测试页面: http://您的转发地址:8000/test_simple.html")
    print("   • 如果测试页面正常，说明服务器工作正常，问题在主页面")
    
    print("\n5. 重启系统命令:")
    print("   pkill -f 'python.*main.py'")
    print("   sleep 2")
    print("   cd /root/ARBIG")
    print("   python main.py --auto-start --daemon")

def main():
    print("🔍 ARBIG Web页面空白问题诊断工具")
    print("=" * 60)
    
    test_web_pages()
    check_system_resources()
    check_browser_compatibility()
    generate_solutions()
    
    print(f"\n⏰ 诊断完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 如果问题仍然存在，请:")
    print("1. 在浏览器中按F12查看控制台错误")
    print("2. 尝试访问测试页面确认服务器状态")
    print("3. 考虑重启系统")

if __name__ == "__main__":
    main()
