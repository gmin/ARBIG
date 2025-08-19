"""
行情订阅服务演示
展示如何使用MarketDataService订阅和接收行情数据
"""

import time
import signal
import sys
from datetime import datetime

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class MarketDataDemo:
    """行情数据演示类"""
    
    def __init__(self):
        """初始化演示程序"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.market_data_service = None
        self.running = True
        
        # 统计信息
        self.tick_count = 0
        self.start_time = None
        self.last_tick_time = {}
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"收到信号 {signum}，准备退出...")
        self.running = False
    
    def setup(self) -> bool:
        """设置演示环境"""
        try:
            logger.info("="*60)
            logger.info("ARBIG行情订阅服务演示")
            logger.info("="*60)
            logger.info("正在初始化系统组件...")
            
            # 启动事件引擎
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            
            # 创建CTP网关
            logger.info("正在连接CTP服务器...")
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            
            if not self.ctp_gateway.connect():
                logger.error("✗ CTP连接失败，请检查网络和配置")
                return False
            
            logger.info("✓ CTP服务器连接成功")
            
            # 创建行情服务
            service_config = ServiceConfig(
                name="market_data",
                enabled=True,
                config={
                    'symbols': ['au2509', 'au2512', 'au2601'],  # 黄金主力合约
                    'cache_size': 1000
                }
            )
            
            self.market_data_service = MarketDataService(
                self.event_engine,
                service_config,
                self.ctp_gateway
            )
            
            # 添加Tick回调
            self.market_data_service.add_tick_callback(self._on_tick)
            
            logger.info("✓ 行情服务创建成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def start_market_data_service(self) -> bool:
        """启动行情服务"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("启动行情订阅服务")
            logger.info("-"*40)
            
            # 启动服务
            if not self.market_data_service.start():
                logger.error("✗ 行情服务启动失败")
                return False
            
            logger.info("✓ 行情服务启动成功")
            
            # 手动订阅额外合约
            additional_symbols = ['au2603', 'au2606']
            for symbol in additional_symbols:
                success = self.market_data_service.subscribe_symbol(symbol, 'demo_client')
                if success:
                    logger.info(f"✓ 手动订阅成功: {symbol}")
                else:
                    logger.warning(f"⚠ 手动订阅失败: {symbol}")
            
            # 显示订阅状态
            subscription_status = self.market_data_service.get_subscription_status()
            logger.info(f"当前订阅合约: {list(subscription_status.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 启动行情服务失败: {e}")
            return False
    
    def _on_tick(self, tick) -> None:
        """Tick数据回调函数"""
        try:
            self.tick_count += 1
            current_time = datetime.now()
            
            # 记录最后更新时间
            self.last_tick_time[tick.symbol] = current_time
            
            # 每10个Tick显示一次统计
            if self.tick_count % 10 == 0:
                elapsed = (current_time - self.start_time).total_seconds()
                rate = self.tick_count / elapsed if elapsed > 0 else 0
                logger.info(f"📊 已接收 {self.tick_count} 个Tick，速率: {rate:.1f} tick/秒")
            
            # 显示行情信息（每个合约每5秒最多显示一次）
            last_display = getattr(self, f'_last_display_{tick.symbol}', None)
            if not last_display or (current_time - last_display).total_seconds() >= 5:
                self._display_tick_info(tick)
                setattr(self, f'_last_display_{tick.symbol}', current_time)
            
        except Exception as e:
            logger.error(f"处理Tick数据失败: {e}")
    
    def _display_tick_info(self, tick) -> None:
        """显示Tick信息"""
        try:
            logger.info(
                f"📈 {tick.symbol}: "
                f"最新价={tick.last_price:.2f}, "
                f"买一={tick.bid_price_1:.2f}({tick.bid_volume_1}), "
                f"卖一={tick.ask_price_1:.2f}({tick.ask_volume_1}), "
                f"成交量={tick.volume}, "
                f"时间={tick.datetime.strftime('%H:%M:%S')}"
            )
        except Exception as e:
            logger.error(f"显示Tick信息失败: {e}")
    
    def monitor_service(self) -> None:
        """监控服务状态"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("开始监控行情数据")
            logger.info("-"*40)
            logger.info("按 Ctrl+C 退出程序")
            
            self.start_time = datetime.now()
            last_stats_time = self.start_time
            
            while self.running:
                time.sleep(1)
                current_time = datetime.now()
                
                # 每30秒显示一次统计信息
                if (current_time - last_stats_time).total_seconds() >= 30:
                    self._display_statistics()
                    last_stats_time = current_time
                
                # 检查服务状态
                if self.market_data_service.get_status().value != "RUNNING":
                    logger.error("⚠ 行情服务状态异常，尝试重启...")
                    break
            
        except KeyboardInterrupt:
            logger.info("收到退出信号")
        except Exception as e:
            logger.error(f"监控过程出错: {e}")
    
    def _display_statistics(self) -> None:
        """显示统计信息"""
        try:
            current_time = datetime.now()
            elapsed = (current_time - self.start_time).total_seconds()
            
            logger.info("\n" + "="*50)
            logger.info("📊 行情服务统计信息")
            logger.info("="*50)
            
            # 基本统计
            logger.info(f"运行时间: {elapsed:.0f} 秒")
            logger.info(f"总Tick数: {self.tick_count}")
            logger.info(f"平均速率: {self.tick_count/elapsed:.1f} tick/秒" if elapsed > 0 else "计算中...")
            
            # 合约活跃度
            logger.info("\n合约活跃度:")
            for symbol, last_time in self.last_tick_time.items():
                seconds_ago = (current_time - last_time).total_seconds()
                status = "🟢 活跃" if seconds_ago < 10 else "🟡 较慢" if seconds_ago < 60 else "🔴 停滞"
                logger.info(f"  {symbol}: {status} (最后更新: {seconds_ago:.0f}秒前)")
            
            # 服务统计
            service_stats = self.market_data_service.get_statistics()
            logger.info(f"\n服务状态: {service_stats['status']}")
            logger.info(f"订阅合约数: {service_stats['subscribed_symbols']}")
            logger.info(f"缓存Tick数: {service_stats['cached_ticks']}")
            
            # 网关状态
            gateway_stats = self.ctp_gateway.get_status_info()
            logger.info(f"\nCTP连接状态:")
            logger.info(f"  行情服务器: {'✓ 已连接' if gateway_stats['md_connected'] else '✗ 未连接'}")
            logger.info(f"  交易服务器: {'✓ 已连接' if gateway_stats['td_connected'] else '✗ 未连接'}")
            logger.info(f"  合约数量: {gateway_stats['contracts_count']}")
            
        except Exception as e:
            logger.error(f"显示统计信息失败: {e}")
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("正在清理资源...")
            logger.info("-"*40)
            
            # 显示最终统计
            if self.start_time:
                self._display_statistics()
            
            # 停止行情服务
            if self.market_data_service:
                self.market_data_service.stop()
                logger.info("✓ 行情服务已停止")
            
            # 断开CTP连接
            if self.ctp_gateway:
                self.ctp_gateway.disconnect()
                logger.info("✓ CTP连接已断开")
            
            # 停止事件引擎
            if self.event_engine:
                self.event_engine.stop()
                logger.info("✓ 事件引擎已停止")
            
            logger.info("✓ 资源清理完成")
            
        except Exception as e:
            logger.error(f"✗ 清理资源失败: {e}")
    
    def run(self) -> bool:
        """运行演示程序"""
        try:
            # 设置环境
            if not self.setup():
                return False
            
            # 启动行情服务
            if not self.start_market_data_service():
                return False
            
            # 监控服务
            self.monitor_service()
            
            return True
            
        except Exception as e:
            logger.error(f"演示程序运行失败: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """主函数"""
    demo = MarketDataDemo()
    success = demo.run()
    
    if success:
        logger.info("🎉 演示程序正常结束")
        return 0
    else:
        logger.error("❌ 演示程序异常结束")
        return 1

if __name__ == "__main__":
    exit(main())
