#!/usr/bin/env python3
"""
测试服务连接状态
"""

import requests
import time

def test_connection():
    """测试服务连接"""
    ports = [8001, 8002, 8003]  # 常见的服务端口
    
    for port in ports:
        try:
            print(f"🔍 测试端口 {port}...")
            response = requests.get(f"http://localhost:{port}/", timeout=5)
            print(f"✅ 端口 {port} 可访问: {response.status_code}")
            
            # 尝试访问API文档
            try:
                docs_response = requests.get(f"http://localhost:{port}/docs", timeout=5)
                print(f"📚 API文档: http://localhost:{port}/docs ({docs_response.status_code})")
            except:
                pass
                
        except Exception as e:
            print(f"❌ 端口 {port} 不可访问: {e}")
    
    print("\n💡 如果所有端口都不可访问，请确认服务已启动")

if __name__ == "__main__":
    test_connection()
