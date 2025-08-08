#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARBIG量化交易系统主程序 - 单体架构版本
整合核心系统和Web管理界面到一个进程中
"""

import sys
import os
import argparse
import time
import asyncio
import threading
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.system_controller import SystemController
from web_admin.api.system_connector import get_system_connector
from utils.logger import get_logger

logger = get_logger(__name__)

class ARBIGApplication:
    """ARBIG单体应用程序"""

    def __init__(self):
        """初始化应用程序"""
        self.system_controller = SystemController()
        self.web_server = None
        self.web_thread = None

        # 初始化系统连接器，传入系统控制器实例
        connector = get_system_connector()
        connector.set_system_controller(self.system_controller)

        logger.info("ARBIG单体应用程序初始化完成")

    def start_system(self, auto_start: bool = False) -> bool:
        """启动核心系统"""
        try:
            if auto_start:
                logger.info("🚀 自动启动核心系统")
                result = self.system_controller.start_system()
                if not result.success:
                    logger.error(f"核心系统启动失败: {result.message}")
                    return False

                logger.info("✅ 核心系统自动启动成功")
                return True
            else:
                logger.info("📋 手动启动模式 - 核心系统已准备就绪")
                return True

        except Exception as e:
            logger.error(f"启动核心系统失败: {e}")
            return False

    def start_web_server(self, host: str = "0.0.0.0", port: int = 8080,
                        reload: bool = False) -> bool:
        """启动Web服务器"""
        try:
            logger.info("🌐 启动Web服务器")
            logger.info(f"📍 地址: http://{host}:{port}")

            def run_server():
                """在独立线程中运行Web服务器"""
                try:
                    uvicorn.run(
                        "web_admin.api.main:app",
                        host=host,
                        port=port,
                        reload=reload,
                        log_level="info",
                        access_log=True
                    )
                except Exception as e:
                    logger.error(f"Web服务器运行异常: {e}")

            # 在独立线程中启动Web服务器
            self.web_thread = threading.Thread(target=run_server, daemon=True)
            self.web_thread.start()

            # 等待一下确保服务器启动
            time.sleep(2)

            logger.info("✅ Web服务器启动成功")
            return True

        except Exception as e:
            logger.error(f"启动Web服务器失败: {e}")
            return False

    def stop_system(self):
        """停止系统"""
        try:
            logger.info("正在停止ARBIG系统...")

            # 停止核心系统
            result = self.system_controller.stop_system()
            if result.success:
                logger.info("✅ 核心系统已停止")
            else:
                logger.error(f"核心系统停止失败: {result.message}")

            logger.info("✅ ARBIG系统已完全停止")

        except Exception as e:
            logger.error(f"停止系统时发生错误: {e}")

    def run(self, with_web: bool = True, web_host: str = "0.0.0.0",
            web_port: int = 8080, web_reload: bool = False):
        """运行应用程序主循环"""
        try:
            logger.info("="*60)
            logger.info("🎯 ARBIG量化交易系统运行中")
            logger.info("="*60)

            if with_web:
                logger.info("💻 Web管理界面: http://{}:{}".format(web_host, web_port))
                logger.info("🔧 系统控制: 通过Web界面进行")
            else:
                logger.info("🔧 系统控制: 仅命令行模式")

            logger.info("⏹️  退出系统: 按 Ctrl+C")
            logger.info("="*60)

            if with_web:
                # 启动Web服务器
                if not self.start_web_server(web_host, web_port, web_reload):
                    logger.error("Web服务器启动失败")
                    return

            # 运行系统控制器主循环
            self.system_controller.run()

        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"运行时发生错误: {e}")
        finally:
            self.stop_system()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG量化交易系统 v2.0 - 单体架构')
    parser.add_argument('--auto-start', action='store_true',
                       help='自动启动所有服务（包括CTP连接和交易服务）')
    parser.add_argument('--config', type=str, default='config.json',
                       help='配置文件路径')
    parser.add_argument('--headless', action='store_true',
                       help='无头模式：不启动Web界面')
    parser.add_argument('--web-only', action='store_true',
                       help='仅Web模式：只启动Web界面（调试用）')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Web服务器主机地址')
    parser.add_argument('--port', type=int, default=8080,
                       help='Web服务器端口')
    parser.add_argument('--reload', action='store_true',
                       help='开发模式：Web服务器自动重载')
    parser.add_argument('--version', action='version', version='ARBIG v2.0.0 - 单体架构')

    args = parser.parse_args()

    # 显示启动信息
    logger.info("="*60)
    logger.info("🏛️  ARBIG量化交易系统 v2.0")
    logger.info("🔄 单体架构版本 - 统一进程设计")
    logger.info("="*60)

    # 创建应用程序实例
    app = ARBIGApplication()

    try:
        # 启动核心系统
        if not args.web_only:
            if not app.start_system(auto_start=args.auto_start):
                logger.error("❌ 核心系统启动失败")
                sys.exit(1)

        # 确定是否启动Web界面
        with_web = not args.headless

        # 运行应用程序
        app.run(
            with_web=with_web,
            web_host=args.host,
            web_port=args.port,
            web_reload=args.reload
        )

    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-

"""
ARBIG量化交易系统主程序 - 重构版本
专注于系统核心控制，Web界面通过独立服务提供
"""

import sys
import os
import argparse
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.system_controller import SystemController
from utils.logger import get_logger

logger = get_logger(__name__)

class ARBIGMain:
    """ARBIG主程序类 - 简化版本"""
    
    def __init__(self):
        """初始化主程序"""
        self.system_controller = SystemController()
        logger.info("ARBIG主程序初始化完成")
    
    def start(self, auto_start: bool = False) -> bool:
        """启动系统"""
        try:
            if auto_start:
                logger.info("🚀 自动启动模式")
                result = self.system_controller.start_system()
                if not result.success:
                    logger.error(f"系统启动失败: {result.message}")
                    return False
                
                logger.info("✅ 系统自动启动成功")
                return True
            else:
                logger.info("📋 手动启动模式")
                logger.info("系统已准备就绪，等待通过Web界面启动")
                return True
                
        except Exception as e:
            logger.error(f"启动失败: {e}")
            return False
    
    def stop(self):
        """停止系统"""
        try:
            logger.info("正在停止ARBIG系统...")
            result = self.system_controller.stop_system()
            if result.success:
                logger.info("✅ ARBIG系统已完全停止")
            else:
                logger.error(f"系统停止失败: {result.message}")
                
        except Exception as e:
            logger.error(f"停止系统时发生错误: {e}")
    
    def run(self):
        """运行主循环"""
        try:
            logger.info("="*60)
            logger.info("🎯 ARBIG量化交易系统运行中")
            logger.info("="*60)
            logger.info("💻 Web管理界面: http://localhost:80")
            logger.info("🔧 系统控制: 通过Web界面进行")
            logger.info("⏹️  退出系统: 按 Ctrl+C")
            logger.info("="*60)
            
            # 运行系统控制器主循环
            self.system_controller.run()
                
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"运行时发生错误: {e}")
        finally:
            self.stop()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG量化交易系统 v2.0')
    parser.add_argument('--auto-start', action='store_true', 
                       help='自动启动所有服务（包括CTP连接和交易服务）')
    parser.add_argument('--config', type=str, default='config.json',
                       help='配置文件路径')
    parser.add_argument('--version', action='version', version='ARBIG v2.0.0')
    
    args = parser.parse_args()
    
    # 显示启动信息
    logger.info("="*60)
    logger.info("🏛️  ARBIG量化交易系统 v2.0")
    logger.info("🔄 架构重构版本 - 清晰分层设计")
    logger.info("="*60)
    
    # 创建主程序实例
    app = ARBIGMain()
    
    try:
        # 启动系统
        if app.start(auto_start=args.auto_start):
            # 运行主循环
            app.run()
        else:
            logger.error("❌ 系统启动失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
