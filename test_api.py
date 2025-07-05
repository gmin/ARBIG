#!/usr/bin/env python3
"""
ARBIG Web API 测试启动脚本
用于测试新的Web API框架
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    print("🚀 启动ARBIG Web API测试服务器")
    print("=" * 50)
    
    try:
        from web_monitor.api.main import start_api_server
        
        print("📋 API信息:")
        print("  - 服务地址: http://localhost:8000")
        print("  - API文档: http://localhost:8000/api/docs")
        print("  - 健康检查: http://localhost:8000/health")
        print("  - 系统状态: http://localhost:8000/api/v1/system/status")
        print()
        print("🔧 可用的API端点:")
        print("  - 系统控制: /api/v1/system/*")
        print("  - 服务管理: /api/v1/services/*")
        print("  - 策略管理: /api/v1/strategies/*")
        print("  - 数据查询: /api/v1/data/*")
        print()
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)
        
        # 启动API服务器
        start_api_server(
            host="0.0.0.0",
            port=8000,
            reload=True  # 开发模式，代码变更自动重载
        )
        
    except KeyboardInterrupt:
        print("\n👋 API服务器已停止")
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所需依赖: pip install fastapi uvicorn")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()
