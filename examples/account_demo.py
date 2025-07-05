"""
账户信息服务演示
展示如何使用AccountService管理账户资金、持仓信息
"""

import time
import signal
import sys
from datetime import datetime

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.account_service import AccountService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class AccountDemo:
    """账户信息演示类"""
    
    def __init__(self):
        """初始化演示程序"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.account_service = None
        self.running = True
        
        # 统计信息
        self.account_updates = 0
        self.position_updates = 0
        self.order_updates = 0
        self.trade_updates = 0
        self.start_time = None
        
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
            logger.info("ARBIG账户信息服务演示")
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
            
            # 等待交易服务器连接
            logger.info("等待交易服务器连接...")
            max_wait = 15
            for i in range(max_wait):
                if self.ctp_gateway.is_td_connected():
                    break
                time.sleep(1)
                if i % 3 == 0:
                    logger.info(f"等待交易服务器... {i+1}/{max_wait}")
            
            if not self.ctp_gateway.is_td_connected():
                logger.error("✗ 交易服务器连接失败")
                return False
            
            logger.info("✓ 交易服务器连接成功")
            
            # 创建账户服务
            service_config = ServiceConfig(
                name="account",
                enabled=True,
                config={
                    'update_interval': 30,  # 30秒查询间隔
                    'position_sync': True,
                    'auto_query_after_trade': True
                }
            )
            
            self.account_service = AccountService(
                self.event_engine,
                service_config,
                self.ctp_gateway
            )
            
            # 添加回调
            self.account_service.add_account_callback(self._on_account)
            self.account_service.add_position_callback(self._on_position)
            self.account_service.add_order_callback(self._on_order)
            self.account_service.add_trade_callback(self._on_trade)
            
            logger.info("✓ 账户服务创建成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def start_account_service(self) -> bool:
        """启动账户服务"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("启动账户信息服务")
            logger.info("-"*40)
            
            # 启动服务
            if not self.account_service.start():
                logger.error("✗ 账户服务启动失败")
                return False
            
            logger.info("✓ 账户服务启动成功")
            
            # 等待初始数据
            logger.info("等待初始账户数据...")
            time.sleep(5)
            
            # 显示初始账户信息
            self._display_account_info()
            self._display_position_info()
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 启动账户服务失败: {e}")
            return False
    
    def _display_account_info(self) -> None:
        """显示账户信息"""
        try:
            account = self.account_service.get_account_info()
            if account:
                logger.info("\n💰 账户资金信息:")
                logger.info(f"  账户ID: {account.accountid}")
                logger.info(f"  总资金: {account.balance:,.2f}")
                logger.info(f"  可用资金: {account.available:,.2f}")
                logger.info(f"  冻结资金: {account.frozen:,.2f}")
                logger.info(f"  更新时间: {account.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                logger.warning("⚠ 暂无账户信息")
        except Exception as e:
            logger.error(f"显示账户信息失败: {e}")
    
    def _display_position_info(self) -> None:
        """显示持仓信息"""
        try:
            positions = self.account_service.get_positions()
            
            logger.info(f"\n📊 持仓信息 (共 {len(positions)} 个持仓):")
            
            if positions:
                # 按合约分组显示
                symbol_positions = {}
                for pos in positions:
                    if pos.symbol not in symbol_positions:
                        symbol_positions[pos.symbol] = []
                    symbol_positions[pos.symbol].append(pos)
                
                for symbol, pos_list in symbol_positions.items():
                    logger.info(f"  📈 {symbol}:")
                    for pos in pos_list:
                        direction_icon = "🟢" if pos.direction.value == "LONG" else "🔴"
                        logger.info(f"    {direction_icon} {pos.direction.value}: "
                                   f"{pos.volume} 手, "
                                   f"均价: {pos.price:.2f}, "
                                   f"盈亏: {pos.pnl:,.2f}")
            else:
                logger.info("  当前无持仓")
                
        except Exception as e:
            logger.error(f"显示持仓信息失败: {e}")
    
    def _on_account(self, account) -> None:
        """账户信息回调"""
        try:
            self.account_updates += 1
            logger.info(f"💰 账户更新 #{self.account_updates}: 可用资金 {account.available:,.2f}")
            
        except Exception as e:
            logger.error(f"处理账户信息失败: {e}")
    
    def _on_position(self, position) -> None:
        """持仓信息回调"""
        try:
            self.position_updates += 1
            direction_icon = "🟢" if position.direction.value == "LONG" else "🔴"
            logger.info(f"📊 持仓更新 #{self.position_updates}: "
                       f"{direction_icon} {position.symbol} {position.direction.value} "
                       f"{position.volume} 手 @ {position.price:.2f}")
            
        except Exception as e:
            logger.error(f"处理持仓信息失败: {e}")
    
    def _on_order(self, order) -> None:
        """订单状态回调"""
        try:
            self.order_updates += 1
            status_icon = {
                'SUBMITTING': '⏳',
                'NOTTRADED': '⏸️',
                'PARTTRADED': '🔄',
                'ALLTRADED': '✅',
                'CANCELLED': '❌',
                'REJECTED': '🚫'
            }.get(order.status.value, '❓')
            
            logger.info(f"📋 订单更新 #{self.order_updates}: "
                       f"{status_icon} {order.orderid} {order.status.value}")
            
        except Exception as e:
            logger.error(f"处理订单信息失败: {e}")
    
    def _on_trade(self, trade) -> None:
        """成交信息回调"""
        try:
            self.trade_updates += 1
            direction_icon = "🟢" if trade.direction.value == "LONG" else "🔴"
            logger.info(f"🎯 成交通知 #{self.trade_updates}: "
                       f"{direction_icon} {trade.symbol} {trade.direction.value} "
                       f"{trade.volume} 手 @ {trade.price:.2f}")
            
            # 成交后显示最新账户信息
            time.sleep(1)  # 等待账户更新
            self._display_account_info()
            
        except Exception as e:
            logger.error(f"处理成交信息失败: {e}")
    
    def monitor_service(self) -> None:
        """监控服务状态"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("开始监控账户信息")
            logger.info("-"*40)
            logger.info("按 Ctrl+C 退出程序")
            
            self.start_time = datetime.now()
            last_stats_time = self.start_time
            last_display_time = self.start_time
            
            while self.running:
                time.sleep(1)
                current_time = datetime.now()
                
                # 每60秒显示一次详细信息
                if (current_time - last_display_time).total_seconds() >= 60:
                    self._display_account_info()
                    self._display_position_info()
                    last_display_time = current_time
                
                # 每30秒显示一次统计信息
                if (current_time - last_stats_time).total_seconds() >= 30:
                    self._display_statistics()
                    last_stats_time = current_time
                
                # 检查服务状态
                if self.account_service.get_status().value != "RUNNING":
                    logger.error("⚠ 账户服务状态异常")
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
            logger.info("📊 账户服务统计信息")
            logger.info("="*50)
            
            # 基本统计
            logger.info(f"运行时间: {elapsed:.0f} 秒")
            logger.info(f"账户更新次数: {self.account_updates}")
            logger.info(f"持仓更新次数: {self.position_updates}")
            logger.info(f"订单更新次数: {self.order_updates}")
            logger.info(f"成交更新次数: {self.trade_updates}")
            
            # 服务统计
            service_stats = self.account_service.get_statistics()
            logger.info(f"\n服务状态: {service_stats['status']}")
            logger.info(f"查询间隔: {service_stats['query_interval']} 秒")
            logger.info(f"持仓数量: {service_stats['positions_count']}")
            logger.info(f"活跃订单: {service_stats['active_orders_count']}")
            logger.info(f"总成交数: {service_stats['total_trades_count']}")
            
            # 网关状态
            gateway_stats = self.ctp_gateway.get_status_info()
            logger.info(f"\nCTP连接状态:")
            logger.info(f"  行情服务器: {'✓ 已连接' if gateway_stats['md_connected'] else '✗ 未连接'}")
            logger.info(f"  交易服务器: {'✓ 已连接' if gateway_stats['td_connected'] else '✗ 未连接'}")
            logger.info(f"  账户可用资金: {gateway_stats['account_available']:,.2f}")
            
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
            
            # 停止账户服务
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
            
            # 启动账户服务
            if not self.start_account_service():
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
    demo = AccountDemo()
    success = demo.run()
    
    if success:
        logger.info("🎉 演示程序正常结束")
        return 0
    else:
        logger.error("❌ 演示程序异常结束")
        return 1

if __name__ == "__main__":
    exit(main())
