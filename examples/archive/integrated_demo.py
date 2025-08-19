"""
ARBIG综合服务演示
同时展示行情订阅服务和账户信息服务的协同工作
"""

import time
import signal
import sys
from datetime import datetime

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class IntegratedDemo:
    """综合服务演示类"""
    
    def __init__(self):
        """初始化演示程序"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.market_data_service = None
        self.account_service = None
        self.running = True
        
        # 统计信息
        self.tick_count = 0
        self.account_updates = 0
        self.position_updates = 0
        self.start_time = None
        self.last_prices = {}
        
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
            logger.info("ARBIG综合服务演示")
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
            market_config = ServiceConfig(
                name="market_data",
                enabled=True,
                config={
                    'symbols': ['au2509', 'au2512', 'au2601'],
                    'cache_size': 1000
                }
            )
            
            self.market_data_service = MarketDataService(
                self.event_engine,
                market_config,
                self.ctp_gateway
            )
            
            # 创建账户服务
            account_config = ServiceConfig(
                name="account",
                enabled=True,
                config={
                    'update_interval': 30,
                    'position_sync': True,
                    'auto_query_after_trade': True
                }
            )
            
            self.account_service = AccountService(
                self.event_engine,
                account_config,
                self.ctp_gateway
            )
            
            # 添加回调
            self.market_data_service.add_tick_callback(self._on_tick)
            self.account_service.add_account_callback(self._on_account)
            self.account_service.add_position_callback(self._on_position)
            
            logger.info("✓ 服务组件创建成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def start_services(self) -> bool:
        """启动所有服务"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("启动ARBIG核心服务")
            logger.info("-"*40)
            
            # 启动行情服务
            if not self.market_data_service.start():
                logger.error("✗ 行情服务启动失败")
                return False
            logger.info("✓ 行情服务启动成功")
            
            # 启动账户服务
            if not self.account_service.start():
                logger.error("✗ 账户服务启动失败")
                return False
            logger.info("✓ 账户服务启动成功")
            
            # 等待服务稳定
            logger.info("等待服务稳定...")
            time.sleep(5)
            
            # 显示初始状态
            self._display_service_status()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 启动服务失败: {e}")
            return False
    
    def _display_service_status(self) -> None:
        """显示服务状态"""
        try:
            logger.info("\n📊 服务状态概览:")
            
            # 行情服务状态
            market_stats = self.market_data_service.get_statistics()
            logger.info(f"  📈 行情服务: {market_stats['status']}")
            logger.info(f"    订阅合约: {market_stats['subscribed_symbols']}")
            logger.info(f"    缓存Tick: {market_stats['cached_ticks']}")
            
            # 账户服务状态
            account_stats = self.account_service.get_statistics()
            logger.info(f"  💰 账户服务: {account_stats['status']}")
            logger.info(f"    可用资金: {account_stats['account_available']:,.2f}")
            logger.info(f"    持仓数量: {account_stats['positions_count']}")
            
            # CTP连接状态
            gateway_stats = self.ctp_gateway.get_status_info()
            logger.info(f"  🔗 CTP连接:")
            logger.info(f"    行情服务器: {'✓' if gateway_stats['md_connected'] else '✗'}")
            logger.info(f"    交易服务器: {'✓' if gateway_stats['td_connected'] else '✗'}")
            
        except Exception as e:
            logger.error(f"显示服务状态失败: {e}")
    
    def _on_tick(self, tick) -> None:
        """行情数据回调"""
        try:
            self.tick_count += 1
            self.last_prices[tick.symbol] = tick.last_price
            
            # 每50个Tick显示一次行情概览
            if self.tick_count % 50 == 0:
                logger.info(f"📈 行情概览 (已收到 {self.tick_count} 个Tick):")
                for symbol, price in self.last_prices.items():
                    logger.info(f"  {symbol}: {price:.2f}")
            
        except Exception as e:
            logger.error(f"处理Tick数据失败: {e}")
    
    def _on_account(self, account) -> None:
        """账户信息回调"""
        try:
            self.account_updates += 1
            logger.info(f"💰 账户更新: 可用资金 {account.available:,.2f}")
            
        except Exception as e:
            logger.error(f"处理账户信息失败: {e}")
    
    def _on_position(self, position) -> None:
        """持仓信息回调"""
        try:
            self.position_updates += 1
            direction_icon = "🟢" if position.direction.value == "LONG" else "🔴"
            logger.info(f"📊 持仓更新: {direction_icon} {position.symbol} "
                       f"{position.direction.value} {position.volume} 手")
            
        except Exception as e:
            logger.error(f"处理持仓信息失败: {e}")
    
    def monitor_services(self) -> None:
        """监控服务运行"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("开始监控ARBIG服务")
            logger.info("-"*40)
            logger.info("按 Ctrl+C 退出程序")
            
            self.start_time = datetime.now()
            last_stats_time = self.start_time
            
            while self.running:
                time.sleep(1)
                current_time = datetime.now()
                
                # 每60秒显示一次详细统计
                if (current_time - last_stats_time).total_seconds() >= 60:
                    self._display_detailed_statistics()
                    last_stats_time = current_time
                
                # 检查服务状态
                market_status = self.market_data_service.get_status()
                account_status = self.account_service.get_status()
                
                if market_status.value != "RUNNING":
                    logger.error(f"⚠ 行情服务状态异常: {market_status.value}")
                
                if account_status.value != "RUNNING":
                    logger.error(f"⚠ 账户服务状态异常: {account_status.value}")
            
        except KeyboardInterrupt:
            logger.info("收到退出信号")
        except Exception as e:
            logger.error(f"监控过程出错: {e}")
    
    def _display_detailed_statistics(self) -> None:
        """显示详细统计信息"""
        try:
            current_time = datetime.now()
            elapsed = (current_time - self.start_time).total_seconds()
            
            logger.info("\n" + "="*60)
            logger.info("📊 ARBIG系统运行统计")
            logger.info("="*60)
            
            # 基本统计
            logger.info(f"运行时间: {elapsed:.0f} 秒")
            logger.info(f"Tick接收数: {self.tick_count}")
            logger.info(f"账户更新数: {self.account_updates}")
            logger.info(f"持仓更新数: {self.position_updates}")
            
            # 行情统计
            market_stats = self.market_data_service.get_statistics()
            logger.info(f"\n📈 行情服务统计:")
            logger.info(f"  状态: {market_stats['status']}")
            logger.info(f"  订阅合约数: {market_stats['subscribed_symbols']}")
            logger.info(f"  缓存Tick数: {market_stats['cached_ticks']}")
            logger.info(f"  Tick速率: {self.tick_count/elapsed:.1f} tick/秒" if elapsed > 0 else "计算中...")
            
            # 账户统计
            account_stats = self.account_service.get_statistics()
            logger.info(f"\n💰 账户服务统计:")
            logger.info(f"  状态: {account_stats['status']}")
            logger.info(f"  可用资金: {account_stats['account_available']:,.2f}")
            logger.info(f"  持仓数量: {account_stats['positions_count']}")
            logger.info(f"  活跃订单: {account_stats['active_orders_count']}")
            logger.info(f"  查询间隔: {account_stats['query_interval']} 秒")
            
            # 当前行情快照
            if self.last_prices:
                logger.info(f"\n📊 当前行情快照:")
                for symbol, price in self.last_prices.items():
                    tick = self.market_data_service.get_latest_tick(symbol)
                    if tick:
                        logger.info(f"  {symbol}: {price:.2f} "
                                   f"(买一: {tick.bid_price_1:.2f}, "
                                   f"卖一: {tick.ask_price_1:.2f})")
            
            # 当前持仓快照
            positions = self.account_service.get_positions()
            if positions:
                logger.info(f"\n📋 当前持仓快照:")
                for pos in positions:
                    direction_icon = "🟢" if pos.direction.value == "LONG" else "🔴"
                    logger.info(f"  {direction_icon} {pos.symbol} {pos.direction.value}: "
                               f"{pos.volume} 手 @ {pos.price:.2f} "
                               f"(盈亏: {pos.pnl:,.2f})")
            else:
                logger.info(f"\n📋 当前无持仓")
            
            # 网关状态
            gateway_stats = self.ctp_gateway.get_status_info()
            logger.info(f"\n🔗 CTP网关状态:")
            logger.info(f"  行情连接: {'✓ 正常' if gateway_stats['md_connected'] else '✗ 断开'}")
            logger.info(f"  交易连接: {'✓ 正常' if gateway_stats['td_connected'] else '✗ 断开'}")
            logger.info(f"  合约数量: {gateway_stats['contracts_count']}")
            logger.info(f"  订单数量: {gateway_stats['orders_count']}")
            logger.info(f"  成交数量: {gateway_stats['trades_count']}")
            
        except Exception as e:
            logger.error(f"显示详细统计失败: {e}")
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("正在清理资源...")
            logger.info("-"*40)
            
            # 显示最终统计
            if self.start_time:
                self._display_detailed_statistics()
            
            # 停止服务
            if self.market_data_service:
                self.market_data_service.stop()
                logger.info("✓ 行情服务已停止")
            
            if self.account_service:
                self.account_service.stop()
                logger.info("✓ 账户服务已停止")
            
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
            
            # 启动服务
            if not self.start_services():
                return False
            
            # 监控服务
            self.monitor_services()
            
            return True
            
        except Exception as e:
            logger.error(f"演示程序运行失败: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """主函数"""
    demo = IntegratedDemo()
    success = demo.run()
    
    if success:
        logger.info("🎉 综合演示程序正常结束")
        return 0
    else:
        logger.error("❌ 综合演示程序异常结束")
        return 1

if __name__ == "__main__":
    exit(main())
