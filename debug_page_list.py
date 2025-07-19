#!/usr/bin/env python3
"""
显示所有可用的调试页面
"""

import requests
import time

def test_debug_pages():
    """测试所有调试页面"""
    print("🔍 ARBIG 调试页面列表")
    print("=" * 60)
    
    pages = [
        ("主页面", "/", "主要的Web管理界面"),
        ("调试页面", "/debug.html", "全面的系统调试工具"),
        ("简单测试", "/test_simple.html", "基础功能测试"),
        ("静态测试", "/static_test.html", "静态资源测试"),
        ("API测试", "/test_api.html", "API接口测试"),
        ("最小测试", "/minimal_test.html", "最小功能测试"),
        ("紧急调试", "/emergency_debug.html", "紧急问题调试"),
        ("持仓调试", "/debug_positions.html", "持仓信息调试"),
        ("策略监控", "/strategy_monitor.html?strategy=shfe_quant", "策略监控页面"),
        ("API文档", "/api/docs", "API接口文档"),
        ("系统状态", "/api/v1/system/status", "系统状态JSON")
    ]
    
    print(f"{'页面名称':<12} {'状态':<8} {'URL':<40} {'说明'}")
    print("-" * 80)
    
    working_pages = []
    
    for name, url, description in pages:
        try:
            full_url = f"http://localhost:8000{url}"
            response = requests.get(full_url, timeout=3)
            
            if response.status_code == 200:
                status = "✅ 正常"
                working_pages.append((name, url, description))
            else:
                status = f"❌ {response.status_code}"
                
        except Exception as e:
            status = "❌ 错误"
            
        print(f"{name:<12} {status:<8} {url:<40} {description}")
    
    print("\n" + "=" * 60)
    print("🎯 推荐的调试顺序:")
    print("\n1. 首先尝试简单页面:")
    
    simple_pages = [
        ("简单测试", "/test_simple.html"),
        ("静态测试", "/static_test.html"),
        ("紧急调试", "/emergency_debug.html")
    ]
    
    for name, url in simple_pages:
        print(f"   • {name}: http://您的转发地址:8000{url}")
    
    print("\n2. 如果简单页面正常，再尝试:")
    print(f"   • 调试页面: http://您的转发地址:8000/debug.html")
    print(f"   • 主页面: http://您的转发地址:8000/")
    
    print("\n3. 检查API状态:")
    print(f"   • 系统状态: http://您的转发地址:8000/api/v1/system/status")
    print(f"   • API文档: http://您的转发地址:8000/api/docs")
    
    print("\n🔧 如果所有调试页面都正常，但主页面空白:")
    print("   这说明问题在主页面的JavaScript代码中")
    print("   请在浏览器中按F12查看控制台错误信息")
    
    print(f"\n⏰ 检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return working_pages

if __name__ == "__main__":
    working_pages = test_debug_pages()
    
    if len(working_pages) > 5:
        print(f"\n✅ 发现 {len(working_pages)} 个正常工作的页面")
        print("   服务器端完全正常，问题可能在浏览器端")
    else:
        print(f"\n⚠️ 只有 {len(working_pages)} 个页面正常工作")
        print("   可能存在服务器端问题")
