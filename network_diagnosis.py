#!/usr/bin/env python3
"""
网络连接和端口转发诊断工具
"""

import subprocess
import socket
import requests
import time
import json

def check_local_service():
    """检查本地服务状态"""
    print("🔍 检查本地服务状态...")
    
    # 检查端口监听
    try:
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        port_8000_lines = [line for line in result.stdout.split('\n') if ':8000' in line]
        
        if port_8000_lines:
            print("✅ 端口8000正在监听:")
            for line in port_8000_lines:
                print(f"   {line.strip()}")
        else:
            print("❌ 端口8000未在监听")
            return False
            
    except Exception as e:
        print(f"❌ 检查端口失败: {e}")
        return False
    
    # 检查本地连接
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        print(f"✅ 本地连接正常: HTTP {response.status_code}")
        print(f"   内容长度: {len(response.text)} 字符")
        return True
    except Exception as e:
        print(f"❌ 本地连接失败: {e}")
        return False

def check_network_interfaces():
    """检查网络接口"""
    print("\n🌐 检查网络接口...")
    
    try:
        # 获取IP地址
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        interfaces = {}
        current_interface = None
        
        for line in lines:
            if line.startswith(' ') == False and ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    current_interface = parts[1].strip()
                    interfaces[current_interface] = []
            elif 'inet ' in line and current_interface:
                inet_part = line.strip().split('inet ')[1].split(' ')[0]
                interfaces[current_interface].append(inet_part)
        
        for interface, ips in interfaces.items():
            if ips and interface != 'lo':
                print(f"✅ 网络接口 {interface}:")
                for ip in ips:
                    print(f"   IP地址: {ip}")
                    
    except Exception as e:
        print(f"❌ 检查网络接口失败: {e}")

def check_firewall():
    """检查防火墙状态"""
    print("\n🛡️ 检查防火墙状态...")
    
    # 检查ufw
    try:
        result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
        if 'inactive' in result.stdout.lower():
            print("✅ UFW防火墙已关闭")
        else:
            print("⚠️ UFW防火墙已启用:")
            print(result.stdout)
    except:
        print("ℹ️ UFW未安装或无法检查")
    
    # 检查iptables
    try:
        result = subprocess.run(['iptables', '-L'], capture_output=True, text=True)
        if 'Chain INPUT (policy ACCEPT)' in result.stdout:
            print("✅ iptables默认允许连接")
        else:
            print("⚠️ iptables可能有限制规则")
    except:
        print("ℹ️ 无法检查iptables")

def test_external_access():
    """测试外部访问"""
    print("\n🌍 测试外部访问...")
    
    # 获取外网IP
    try:
        response = requests.get('http://httpbin.org/ip', timeout=5)
        external_ip = response.json().get('origin', '未知')
        print(f"✅ 外网IP: {external_ip}")
    except:
        print("❌ 无法获取外网IP")
    
    # 测试端口连通性
    print("\n🔌 端口连通性测试:")
    print("   请在您的本地电脑上运行以下命令测试连通性:")
    print("   telnet 您的服务器IP 8000")
    print("   或者: nc -zv 您的服务器IP 8000")

def check_cloud_provider():
    """检查云服务商配置"""
    print("\n☁️ 云服务商配置检查...")
    
    print("常见的云服务商端口转发问题:")
    print("1. 阿里云ECS:")
    print("   - 检查安全组规则是否开放8000端口")
    print("   - 确认入方向规则允许0.0.0.0/0访问8000端口")
    
    print("2. 腾讯云CVM:")
    print("   - 检查安全组是否开放8000端口")
    print("   - 确认防火墙规则")
    
    print("3. AWS EC2:")
    print("   - 检查Security Group的Inbound Rules")
    print("   - 确认8000端口对0.0.0.0/0开放")
    
    print("4. 其他云服务商:")
    print("   - 检查网络安全组/防火墙规则")
    print("   - 确认端口转发配置")

def generate_solutions():
    """生成解决方案"""
    print("\n🔧 解决方案:")
    
    print("1. 如果本地访问正常，但外部访问失败:")
    print("   • 检查云服务商的安全组配置")
    print("   • 确认8000端口已对外开放")
    print("   • 检查服务器防火墙设置")
    
    print("2. 如果页面能访问但显示空白:")
    print("   • 问题可能在浏览器端")
    print("   • 检查浏览器控制台错误")
    print("   • 尝试不同的浏览器")
    
    print("3. 临时解决方案:")
    print("   • 尝试使用不同的端口")
    print("   • 使用SSH隧道: ssh -L 8000:localhost:8000 user@server")
    
    print("4. 调试命令:")
    print("   • 本地测试: curl http://localhost:8000/")
    print("   • 远程测试: curl http://服务器IP:8000/")
    print("   • 端口测试: telnet 服务器IP 8000")

def main():
    print("🔍 ARBIG 网络连接诊断工具")
    print("=" * 60)
    
    # 检查本地服务
    local_ok = check_local_service()
    
    # 检查网络配置
    check_network_interfaces()
    check_firewall()
    
    # 外部访问测试
    test_external_access()
    
    # 云服务商配置
    check_cloud_provider()
    
    # 生成解决方案
    generate_solutions()
    
    print(f"\n⏰ 诊断完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if local_ok:
        print("\n✅ 本地服务正常，问题可能在:")
        print("   1. 云服务商安全组配置")
        print("   2. 网络防火墙设置") 
        print("   3. 端口转发配置")
        print("   4. 浏览器端问题")
    else:
        print("\n❌ 本地服务异常，需要先修复服务器端问题")

if __name__ == "__main__":
    main()
