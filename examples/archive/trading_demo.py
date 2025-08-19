"""
交易执行服务演示
展示如何使用TradingService进行订单管理和策略信号处理
"""

import time
import signal
import sys
from datetime import datetime

from core.event_engine import EventEngine, Event
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.risk_service import RiskService
from core.services.trading_service import TradingService
from core.types import (
    ServiceConfig, OrderRequest, SignalData,
    Direction, OrderType, Status
)
from core.constants import SIGNAL_EVENT
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class TradingDemo:
    """交易执行演示类"""
    
    def __init__(self):
        """初始化演示程序"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.market_data_service = None
        self.account_service = None
        self.risk_service = None
        self.trading_service = None
        self.running = True
        
        # 统计信息
        self.order_updates = 0
        self.trade_updates = 0
        self.start_time = None
        self.demo_orders = []
        
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
            logger.info("ARBIG交易执行服务演示")
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
            
            # 创建服务组件
            self._create_services()
            
            logger.info("✓ 服务组件创建成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 初始化失败: {e}")
            return False
    
    def _create_services(self) -> None:
        """创建所有服务组件"""
        # 创建行情服务
        market_config = ServiceConfig(
            name="market_data",
            enabled=True,
            config={'symbols': ['au2509', 'au2512'], 'cache_size': 1000}
        )
        
        self.market_data_service = MarketDataService(
            self.event_engine, market_config, self.ctp_gateway
        )
        
        # 创建账户服务
        account_config = ServiceConfig(
            name="account",
            enabled=True,
            config={'update_interval': 30, 'position_sync': True}
        )
        
        self.account_service = AccountService(
            self.event_engine, account_config, self.ctp_gateway
        )
        
        # 创建风控服务
        risk_config = ServiceConfig(
            name="risk",
            enabled=True,
            config={
                'max_position_ratio': 0.8,
                'max_daily_loss': 50000,
                'max_single_order_volume': 10
            }
        )
        
        self.risk_service = RiskService(
            self.event_engine, risk_config, self.account_service
        )
        
        # 创建交易服务
        trading_config = ServiceConfig(
            name="trading",
            enabled=True,
            config={
                'order_timeout': 30,
                'max_orders_per_second': 5
            }
        )
        
        self.trading_service = TradingService(
            self.event_engine, trading_config, self.ctp_gateway,
            self.account_service, self.risk_service
        )
        
        # 添加回调
        self.trading_service.add_order_callback(self._on_order)
        self.trading_service.add_trade_callback(self._on_trade)
    
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
            
            # 启动风控服务
            if not self.risk_service.start():
                logger.error("✗ 风控服务启动失败")
                return False
            logger.info("✓ 风控服务启动成功")
            
            # 启动交易服务
            if not self.trading_service.start():
                logger.error("✗ 交易服务启动失败")
                return False
            logger.info("✓ 交易服务启动成功")
            
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
            
            # 交易服务状态
            trading_stats = self.trading_service.get_statistics()
            logger.info(f"  📋 交易服务: {trading_stats['status']}")
            logger.info(f"    总订单数: {trading_stats['total_orders']}")
            logger.info(f"    活跃订单: {trading_stats['active_orders']}")
            logger.info(f"    总成交数: {trading_stats['total_trades']}")
            
            # 账户服务状态
            account_stats = self.account_service.get_statistics()
            logger.info(f"  💰 账户服务: {account_stats['status']}")
            logger.info(f"    可用资金: {account_stats['account_available']:,.2f}")
            
            # 风控服务状态
            risk_stats = self.risk_service.get_statistics()
            logger.info(f"  🛡️ 风控服务: {risk_stats['status']}")
            logger.info(f"    风险级别: {risk_stats['risk_level']}")
            
        except Exception as e:
            logger.error(f"显示服务状态失败: {e}")
    
    def demo_trading_operations(self) -> None:
        """演示交易操作"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("开始交易操作演示")
            logger.info("-"*40)
            
            # 演示1: 发送限价订单
            self._demo_limit_order()
            time.sleep(5)
            
            # 演示2: 处理策略信号
            self._demo_strategy_signal()
            time.sleep(5)
            
            # 演示3: 订单管理操作
            self._demo_order_management()
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"交易操作演示失败: {e}")
    
    def _demo_limit_order(self) -> None:
        """演示限价订单"""
        try:
            logger.info("\n📋 演示1: 发送限价订单")
            
            # 获取当前行情
            tick = self.market_data_service.get_latest_tick('au2509')
            if not tick:
                logger.warning("⚠ 无法获取当前行情，使用默认价格")
                current_price = 500.0
            else:
                current_price = tick.last_price
                logger.info(f"当前行情: {tick.symbol} @ {current_price}")
            
            # 创建买入订单（价格设置得较低，不会立即成交）
            buy_price = current_price - 10.0
            order_req = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1.0,
                price=buy_price,
                reference="demo_buy_order"
            )
            
            order_id = self.trading_service.send_order(order_req)
            if order_id:
                logger.info(f"✓ 买入订单发送成功: {order_id} @ {buy_price}")
                self.demo_orders.append(order_id)
            else:
                logger.error("✗ 买入订单发送失败")
            
        except Exception as e:
            logger.error(f"限价订单演示失败: {e}")
    
    def _demo_strategy_signal(self) -> None:
        """演示策略信号处理"""
        try:
            logger.info("\n🎯 演示2: 策略信号处理")
            
            # 创建策略信号
            signal = SignalData(
                strategy_name="demo_strategy",
                symbol="au2509",
                direction=Direction.SHORT,
                action="OPEN",
                volume=1.0,
                price=0.0,  # 市价单
                signal_type="TRADE",
                confidence=0.8
            )
            
            # 发送信号事件
            signal_event = Event(SIGNAL_EVENT, signal)
            self.trading_service.process_signal(signal_event)
            
            logger.info("✓ 策略信号处理完成")
            
            # 等待订单生成
            time.sleep(2)
            
            # 检查策略订单
            strategy_orders = self.trading_service.get_orders_by_strategy("demo_strategy")
            logger.info(f"✓ 策略订单数量: {len(strategy_orders)}")
            
            for order in strategy_orders:
                if order.orderid not in self.demo_orders:
                    self.demo_orders.append(order.orderid)
            
        except Exception as e:
            logger.error(f"策略信号演示失败: {e}")
    
    def _demo_order_management(self) -> None:
        """演示订单管理"""
        try:
            logger.info("\n🔧 演示3: 订单管理操作")
            
            # 显示所有订单
            all_orders = self.trading_service.get_orders()
            logger.info(f"总订单数: {len(all_orders)}")
            
            # 显示活跃订单
            active_orders = self.trading_service.get_active_orders()
            logger.info(f"活跃订单数: {len(active_orders)}")
            
            if active_orders:
                for order in active_orders[:3]:  # 显示前3个
                    logger.info(f"  {order.orderid}: {order.symbol} "
                               f"{order.direction.value} {order.volume}@{order.price} "
                               f"({order.status.value})")
            
            # 演示撤销订单
            if active_orders:
                order_to_cancel = active_orders[0]
                success = self.trading_service.cancel_order(order_to_cancel.orderid)
                if success:
                    logger.info(f"✓ 订单撤销请求发送: {order_to_cancel.orderid}")
                else:
                    logger.error(f"✗ 订单撤销请求失败: {order_to_cancel.orderid}")
            
        except Exception as e:
            logger.error(f"订单管理演示失败: {e}")
    
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
            logger.error(f"处理订单回调失败: {e}")
    
    def _on_trade(self, trade) -> None:
        """成交信息回调"""
        try:
            self.trade_updates += 1
            direction_icon = "🟢" if trade.direction.value == "LONG" else "🔴"
            logger.info(f"🎯 成交通知 #{self.trade_updates}: "
                       f"{direction_icon} {trade.symbol} {trade.direction.value} "
                       f"{trade.volume} 手 @ {trade.price:.2f}")
            
        except Exception as e:
            logger.error(f"处理成交回调失败: {e}")
    
    def monitor_trading(self) -> None:
        """监控交易活动"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("开始监控交易活动")
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
                trading_status = self.trading_service.get_status()
                if trading_status.value != "RUNNING":
                    logger.error(f"⚠ 交易服务状态异常: {trading_status.value}")
            
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
            logger.info("📊 ARBIG交易系统运行统计")
            logger.info("="*60)
            
            # 基本统计
            logger.info(f"运行时间: {elapsed:.0f} 秒")
            logger.info(f"订单更新数: {self.order_updates}")
            logger.info(f"成交更新数: {self.trade_updates}")
            
            # 交易统计
            trading_stats = self.trading_service.get_statistics()
            logger.info(f"\n📋 交易服务统计:")
            logger.info(f"  状态: {trading_stats['status']}")
            logger.info(f"  总订单数: {trading_stats['total_orders']}")
            logger.info(f"  活跃订单: {trading_stats['active_orders']}")
            logger.info(f"  总成交数: {trading_stats['total_trades']}")
            logger.info(f"  总成交量: {trading_stats['total_volume']:.0f}")
            logger.info(f"  总成交额: {trading_stats['total_turnover']:,.2f}")
            logger.info(f"  平均价格: {trading_stats['avg_price']:.2f}")
            logger.info(f"  策略数量: {trading_stats['strategies_count']}")
            
            # 当前活跃订单
            active_orders = self.trading_service.get_active_orders()
            if active_orders:
                logger.info(f"\n📋 当前活跃订单:")
                for order in active_orders[:5]:  # 显示前5个
                    logger.info(f"  {order.orderid}: {order.symbol} "
                               f"{order.direction.value} {order.volume}@{order.price} "
                               f"({order.status.value})")
            else:
                logger.info(f"\n📋 当前无活跃订单")
            
        except Exception as e:
            logger.error(f"显示详细统计失败: {e}")
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("正在清理资源...")
            logger.info("-"*40)
            
            # 撤销演示订单
            if self.trading_service:
                for order_id in self.demo_orders:
                    try:
                        self.trading_service.cancel_order(order_id)
                    except:
                        pass
                
                # 显示最终统计
                if self.start_time:
                    self._display_detailed_statistics()
                
                # 停止服务
                self.trading_service.stop()
                logger.info("✓ 交易服务已停止")
            
            if self.risk_service:
                self.risk_service.stop()
                logger.info("✓ 风控服务已停止")
            
            if self.account_service:
                self.account_service.stop()
                logger.info("✓ 账户服务已停止")
            
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
            
            # 启动服务
            if not self.start_services():
                return False
            
            # 演示交易操作
            self.demo_trading_operations()
            
            # 监控交易
            self.monitor_trading()
            
            return True
            
        except Exception as e:
            logger.error(f"演示程序运行失败: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """主函数"""
    demo = TradingDemo()
    success = demo.run()
    
    if success:
        logger.info("🎉 交易演示程序正常结束")
        return 0
    else:
        logger.error("❌ 交易演示程序异常结束")
        return 1

if __name__ == "__main__":
    exit(main())
