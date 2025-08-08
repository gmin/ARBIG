#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG Web管理界面启动脚本
独立启动Web管理界面，连接到ARBIG核心系统
"""

import sys
import os
import argparse
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_admin.api.system_connector import get_system_connector
from utils.logger import get_logger

logger = get_logger(__name__)

def initialize_web_admin(use_new_architecture: bool = True):
    """初始化Web管理界面"""
    try:
        logger.info("="*60)
        logger.info("🌐 启动ARBIG Web管理界面")
        logger.info("="*60)
        
        # 初始化系统连接器
        connector = get_system_connector()
        connector.initialize(use_new_architecture=use_new_architecture)
        
        architecture_info = connector.get_architecture_info()
        logger.info(f"架构版本: {architecture_info['architecture_version']}")
        logger.info(f"使用新架构: {architecture_info['use_new_architecture']}")
        
        logger.info("✅ Web管理界面初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ Web管理界面初始化失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG Web管理界面')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='服务器主机地址')
    parser.add_argument('--port', type=int, default=80,
                       help='服务器端口')
    parser.add_argument('--reload', action='store_true',
                       help='开发模式：自动重载')
    parser.add_argument('--legacy', action='store_true',
                       help='使用遗留架构（兼容模式）')
    parser.add_argument('--log-level', type=str, default='info',
                       choices=['debug', 'info', 'warning', 'error'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    # 初始化Web管理界面
    use_new_architecture = not args.legacy
    if not initialize_web_admin(use_new_architecture=use_new_architecture):
        logger.error("Web管理界面初始化失败，退出")
        sys.exit(1)
    
    # 启动Web服务器
    try:
        logger.info("="*60)
        logger.info("🚀 启动Web服务器")
        logger.info(f"📍 地址: http://{args.host}:{args.port}")
        logger.info(f"🔧 开发模式: {'是' if args.reload else '否'}")
        logger.info(f"🏛️ 架构模式: {'新架构' if use_new_architecture else '遗留架构'}")
        logger.info("="*60)
        
        # 启动uvicorn服务器
        uvicorn.run(
            "web_admin.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号，正在关闭Web服务器...")
    except Exception as e:
        logger.error(f"Web服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
