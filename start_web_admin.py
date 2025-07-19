#!/usr/bin/env python3
"""
ARBIG Web管理系统启动脚本
独立启动Web管理界面，可以通过Web页面管理各个服务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web_admin.standalone_app import run_standalone_web_service
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    print("🚀 启动ARBIG Web管理系统")
    print("=" * 50)
    print("通过Web界面管理ARBIG系统各个服务")
    print("访问地址: http://localhost:8000")
    print("=" * 50)
    
    try:
        run_standalone_web_service(host="0.0.0.0", port=8080)
    except KeyboardInterrupt:
        print("\n👋 Web管理系统已关闭")
    except Exception as e:
        logger.error(f"启动Web管理系统失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
