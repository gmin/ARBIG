#!/usr/bin/env python3
"""
诊断Web页面显示问题
"""

import os
import subprocess
import json
import time

def run_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令超时"
    except Exception as e:
        return -1, "", str(e)

def check_process():
    """检查进程状态"""
    print("🔍 检查进程状态...")
    
    # 检查Python进程
    code, stdout, stderr = run_command("ps aux | grep python | grep main.py")
    if code == 0 and stdout.strip():
        print("✅ ARBIG进程正在运行:")
        for line in stdout.strip().split('\n'):
            if 'main.py' in line:
                print(f"   {line}")
    else:
        print("❌ 未找到ARBIG进程")
    
    # 检查端口占用
    code, stdout, stderr = run_command("netstat -tlnp | grep :8000")
    if code == 0 and stdout.strip():
        print("✅ 端口8000正在监听:")
        print(f"   {stdout.strip()}")
    else:
        print("❌ 端口8000未被占用")

def check_api():
    """检查API响应"""
    print("\n🌐 检查API响应...")
    
    # 测试系统状态API
    code, stdout, stderr = run_command("curl -s -w '%{http_code}' http://localhost:8000/api/v1/system/status")
    if code == 0:
        if stdout.endswith('200'):
            print("✅ 系统状态API响应正常 (HTTP 200)")
            # 尝试解析JSON
            json_part = stdout[:-3]  # 移除HTTP状态码
            try:
                data = json.loads(json_part)
                if data.get('success'):
                    print(f"   系统状态: {data.get('data', {}).get('system_status', 'unknown')}")
                else:
                    print(f"   API返回错误: {data.get('message', 'unknown')}")
            except:
                print("   JSON解析失败")
        else:
            print(f"❌ 系统状态API响应异常 (HTTP {stdout[-3:]})")
    else:
        print("❌ 无法连接到系统状态API")

def check_web_content():
    """检查Web页面内容"""
    print("\n📄 检查Web页面内容...")
    
    # 测试主页
    code, stdout, stderr = run_command("curl -s -w '%{http_code}' http://localhost:8000/")
    if code == 0:
        if stdout.endswith('200'):
            print("✅ 主页响应正常 (HTTP 200)")
            content = stdout[:-3]
            if '<!DOCTYPE html>' in content:
                print("   ✅ 返回HTML内容")
                if 'ARBIG' in content:
                    print("   ✅ 包含ARBIG标识")
                else:
                    print("   ⚠️ 未包含ARBIG标识")
            else:
                print("   ❌ 未返回HTML内容")
                print(f"   实际内容: {content[:200]}...")
        else:
            print(f"❌ 主页响应异常 (HTTP {stdout[-3:]})")
    else:
        print("❌ 无法访问主页")

def check_static_files():
    """检查静态文件"""
    print("\n📁 检查静态文件...")
    
    files_to_check = [
        "/root/ARBIG/web_admin/static/index.html",
        "/root/ARBIG/web_admin/static/strategy_monitor.html"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} (大小: {size} 字节)")
            
            # 检查文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # 读取前500字符
                    if '<!DOCTYPE html>' in content:
                        print("   ✅ HTML格式正确")
                    else:
                        print("   ❌ HTML格式异常")
            except Exception as e:
                print(f"   ❌ 读取文件失败: {e}")
        else:
            print(f"❌ {file_path} 不存在")

def check_network():
    """检查网络配置"""
    print("\n🌍 检查网络配置...")
    
    # 检查监听地址
    code, stdout, stderr = run_command("ss -tlnp | grep :8000")
    if code == 0 and stdout.strip():
        print("✅ 端口监听详情:")
        for line in stdout.strip().split('\n'):
            print(f"   {line}")
            if '0.0.0.0:8000' in line:
                print("   ✅ 监听所有网络接口")
            elif '127.0.0.1:8000' in line:
                print("   ⚠️ 仅监听本地接口")
    
    # 检查防火墙
    code, stdout, stderr = run_command("ufw status")
    if code == 0:
        if 'inactive' in stdout.lower():
            print("✅ UFW防火墙已关闭")
        else:
            print("⚠️ UFW防火墙已启用:")
            print(f"   {stdout}")

def check_browser_compatibility():
    """检查浏览器兼容性"""
    print("\n🌐 浏览器兼容性检查...")
    
    # 创建一个简单的测试页面
    test_html = """<!DOCTYPE html>
<html>
<head><title>测试页面</title></head>
<body>
<h1>如果您能看到这个页面，说明Web服务器工作正常</h1>
<p>当前时间: <span id="time"></span></p>
<script>
document.getElementById('time').textContent = new Date().toLocaleString();
</script>
</body>
</html>"""
    
    try:
        with open('/root/ARBIG/web_admin/static/test_simple.html', 'w', encoding='utf-8') as f:
            f.write(test_html)
        print("✅ 创建了简单测试页面: /test_simple.html")
        
        # 测试访问
        code, stdout, stderr = run_command("curl -s http://localhost:8000/test_simple.html")
        if code == 0 and '测试页面' in stdout:
            print("✅ 简单测试页面可以正常访问")
        else:
            print("❌ 简单测试页面无法访问")
            
    except Exception as e:
        print(f"❌ 创建测试页面失败: {e}")

def generate_report():
    """生成诊断报告"""
    print("\n" + "="*60)
    print("📋 诊断报告总结")
    print("="*60)
    
    print("\n🔧 可能的解决方案:")
    print("1. 浏览器问题:")
    print("   - 清空浏览器缓存 (Ctrl+Shift+R)")
    print("   - 尝试无痕模式")
    print("   - 尝试不同的浏览器")
    
    print("\n2. 网络问题:")
    print("   - 检查端口转发配置")
    print("   - 确认防火墙设置")
    print("   - 尝试直接访问服务器IP")
    
    print("\n3. 内容问题:")
    print("   - 检查HTML文件是否损坏")
    print("   - 检查JavaScript是否有错误")
    print("   - 查看浏览器开发者工具")
    
    print("\n4. 服务器问题:")
    print("   - 重启Web服务")
    print("   - 检查服务器日志")
    print("   - 尝试不同的端口")
    
    print("\n🌐 测试地址:")
    print("- 简单测试页面: http://您的转发地址:8000/test_simple.html")
    print("- API状态: http://您的转发地址:8000/api/v1/system/status")
    print("- 主页面: http://您的转发地址:8000/")

def main():
    print("🔍 ARBIG Web页面问题诊断工具")
    print("="*60)
    
    check_process()
    check_api()
    check_web_content()
    check_static_files()
    check_network()
    check_browser_compatibility()
    generate_report()
    
    print(f"\n⏰ 诊断完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
