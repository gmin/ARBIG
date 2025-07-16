#!/usr/bin/env python3
"""
在80端口启动ARBIG Web服务
"""

import sys
import os
sys.path.append('/root/ARBIG')

from web_admin.api.main import start_api_server

if __name__ == "__main__":
    print("🚀 启动ARBIG Web服务在80端口...")
    print("外网访问地址: http://47.86.36.249")
    print("策略监控页面: http://47.86.36.249/strategy_monitor.html?strategy=shfe_quant")
    
    try:
        start_api_server(host="0.0.0.0", port=80, reload=False)
    except PermissionError:
        print("❌ 权限错误：80端口需要root权限")
        print("尝试使用8080端口...")
        start_api_server(host="0.0.0.0", port=8080, reload=False)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("回退到8000端口...")
        start_api_server(host="0.0.0.0", port=8000, reload=False)
