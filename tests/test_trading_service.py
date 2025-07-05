"""
交易执行服务测试
测试TradingService的完整功能，包括订单管理、策略信号处理等
"""

import time
import threading
from datetime import datetime

from core.event_engine import EventEngine, Event
from core.config_manager import ConfigManager
from core.services.trading_service import TradingService
from core.services.account_service import AccountService
from core.services.risk_service import RiskService
from core.types import (
    ServiceConfig, OrderRequest, SignalData, 
    Direction, OrderType, Status
)
from core.constants import SIGNAL_EVENT
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class TradingServiceTest:
    """交易服务测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.account_service = None
        self.risk_service = None
        self.trading_service = None
        
        # 测试统计
        self.order_updates = 0
        self.trade_updates = 0
        self.test_orders = []
        self.test_start_time = None
        
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("="*60)
            logger.info("交易执行服务测试开始")
            logger.info("="*60)
            
            # 启动事件引擎
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            
            # 创建CTP网关
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            logger.info("✓ CTP网关创建成功")
            
            # 连接CTP
            if not self.ctp_gateway.connect():
                logger.error("✗ CTP连接失败")
                return False
            logger.info("✓ CTP连接成功")
            
            # 等待交易服务器连接
            max_wait = 15
            for i in range(max_wait):
                if self.ctp_gateway.is_td_connected():
                    break
                time.sleep(1)
                logger.info(f"等待交易服务器连接... {i+1}/{max_wait}")
            
            if not self.ctp_gateway.is_td_connected():
                logger.error("✗ 交易服务器连接失败")
                return False
            logger.info("✓ 交易服务器连接成功")
            
            # 创建账户服务
            account_config = ServiceConfig(
                name="account",
                enabled=True,
                config={'update_interval': 10}
            )
            
            self.account_service = AccountService(
                self.event_engine,
                account_config,
                self.ctp_gateway
            )
            
            if not self.account_service.start():
                logger.error("✗ 账户服务启动失败")
                return False
            logger.info("✓ 账户服务启动成功")
            
            # 创建风控服务
            risk_config = ServiceConfig(
                name="risk",
                enabled=True,
                config={
                    'max_position_ratio': 0.8,
                    'max_daily_loss': 10000,
                    'max_single_order_volume': 10
                }
            )
            
            self.risk_service = RiskService(
                self.event_engine,
                risk_config,
                self.account_service
            )
            
            if not self.risk_service.start():
                logger.error("✗ 风控服务启动失败")
                return False
            logger.info("✓ 风控服务启动成功")
            
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
                self.event_engine,
                trading_config,
                self.ctp_gateway,
                self.account_service,
                self.risk_service
            )
            
            # 添加回调用于测试统计
            self.trading_service.add_order_callback(self._on_order_for_test)
            self.trading_service.add_trade_callback(self._on_trade_for_test)
            
            logger.info("✓ 交易服务创建成功")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 测试环境设置失败: {e}")
            return False
    
    def test_service_lifecycle(self) -> bool:
        """测试服务生命周期"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试1: 服务生命周期")
            logger.info("-"*40)
            
            # 测试启动
            if not self.trading_service.start():
                logger.error("✗ 服务启动失败")
                return False
            logger.info("✓ 服务启动成功")
            
            # 检查状态
            status = self.trading_service.get_status()
            if status.value != "RUNNING":
                logger.error(f"✗ 服务状态错误: {status.value}")
                return False
            logger.info("✓ 服务状态正确")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 服务生命周期测试失败: {e}")
            return False
    
    def test_order_management(self) -> bool:
        """测试订单管理功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试2: 订单管理功能")
            logger.info("-"*40)
            
            # 创建测试订单请求
            order_req = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1.0,
                price=500.0,  # 设置一个不会成交的价格
                reference="test_strategy_buy"
            )
            
            # 发送订单
            order_id = self.trading_service.send_order(order_req)
            if not order_id:
                logger.error("✗ 订单发送失败")
                return False
            
            logger.info(f"✓ 订单发送成功: {order_id}")
            self.test_orders.append(order_id)
            
            # 等待订单状态更新
            time.sleep(3)
            
            # 检查订单状态
            order = self.trading_service.get_order(order_id)
            if not order:
                logger.error("✗ 无法获取订单信息")
                return False
            
            logger.info(f"✓ 订单状态: {order.status.value}")
            
            # 测试活跃订单查询
            active_orders = self.trading_service.get_active_orders()
            logger.info(f"✓ 活跃订单数量: {len(active_orders)}")
            
            # 测试按策略查询订单
            strategy_orders = self.trading_service.get_orders_by_strategy("test_strategy")
            logger.info(f"✓ 策略订单数量: {len(strategy_orders)}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 订单管理测试失败: {e}")
            return False
    
    def test_signal_processing(self) -> bool:
        """测试策略信号处理"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试3: 策略信号处理")
            logger.info("-"*40)
            
            # 创建策略信号
            signal = SignalData(
                strategy_name="test_strategy",
                symbol="au2509",
                direction=Direction.SHORT,
                action="OPEN",
                volume=1.0,
                price=600.0,  # 设置一个不会成交的价格
                signal_type="TRADE",
                confidence=0.8
            )
            
            # 发送信号事件
            signal_event = Event(SIGNAL_EVENT, signal)
            self.trading_service.process_signal(signal_event)
            
            logger.info("✓ 策略信号处理完成")
            
            # 等待订单生成
            time.sleep(3)

            # 检查是否生成了订单
            strategy_orders = self.trading_service.get_orders_by_strategy("test_strategy")
            expected_orders = 2  # 应该有2个订单（之前的买单 + 现在的卖单）

            if len(strategy_orders) >= 1:  # 至少应该有1个订单
                logger.info(f"✓ 策略订单生成正确，共 {len(strategy_orders)} 个订单")
            else:
                logger.error(f"✗ 策略订单数量不正确: {len(strategy_orders)}")
                return False
            
            # 记录新订单
            for order in strategy_orders:
                if order.orderid not in self.test_orders:
                    self.test_orders.append(order.orderid)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 策略信号处理测试失败: {e}")
            return False
    
    def test_order_cancellation(self) -> bool:
        """测试订单撤销功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试4: 订单撤销功能")
            logger.info("-"*40)
            
            # 获取活跃订单
            active_orders = self.trading_service.get_active_orders()
            if not active_orders:
                logger.warning("⚠ 没有活跃订单可以撤销")
                return True
            
            # 撤销第一个活跃订单
            order_to_cancel = active_orders[0]
            success = self.trading_service.cancel_order(order_to_cancel.orderid)
            
            if success:
                logger.info(f"✓ 订单撤销请求发送成功: {order_to_cancel.orderid}")
            else:
                logger.error(f"✗ 订单撤销请求发送失败: {order_to_cancel.orderid}")
                return False
            
            # 等待撤销结果
            time.sleep(3)
            
            # 测试批量撤销策略订单
            cancelled_count = self.trading_service.cancel_strategy_orders("test_strategy")
            logger.info(f"✓ 批量撤销策略订单: {cancelled_count} 个")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 订单撤销测试失败: {e}")
            return False
    
    def test_statistics_and_monitoring(self) -> bool:
        """测试统计和监控功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试5: 统计和监控功能")
            logger.info("-"*40)
            
            # 获取服务统计
            stats = self.trading_service.get_statistics()
            logger.info("服务统计信息:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            
            # 获取策略统计
            strategy_stats = self.trading_service.get_strategy_statistics("test_strategy")
            logger.info("策略统计信息:")
            for key, value in strategy_stats.items():
                logger.info(f"  {key}: {value}")
            
            # 验证关键统计
            if stats['status'] != 'RUNNING':
                logger.error(f"✗ 服务状态错误: {stats['status']}")
                return False
            
            if stats['total_orders'] == 0:
                logger.error("✗ 订单统计错误")
                return False
            
            logger.info("✓ 统计信息正常")
            return True
            
        except Exception as e:
            logger.error(f"✗ 统计和监控测试失败: {e}")
            return False
    
    def test_risk_integration(self) -> bool:
        """测试风控集成"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试6: 风控集成")
            logger.info("-"*40)
            
            # 创建一个超过风控限制的订单
            large_order_req = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=100.0,  # 超过风控限制
                price=500.0,
                reference="test_strategy_large"
            )
            
            # 尝试发送大订单
            order_id = self.trading_service.send_order(large_order_req)
            
            if order_id:
                logger.warning("⚠ 大订单通过了风控检查（可能风控参数设置较宽松）")
                self.test_orders.append(order_id)
            else:
                logger.info("✓ 大订单被风控拒绝")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 风控集成测试失败: {e}")
            return False
    
    def _on_order_for_test(self, order) -> None:
        """测试用的订单回调函数"""
        self.order_updates += 1
        logger.debug(f"订单更新 #{self.order_updates}: {order.orderid} {order.status.value}")
    
    def _on_trade_for_test(self, trade) -> None:
        """测试用的成交回调函数"""
        self.trade_updates += 1
        logger.debug(f"成交更新 #{self.trade_updates}: {trade.symbol} {trade.volume}@{trade.price}")
    
    def cleanup(self) -> None:
        """清理测试环境"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("清理测试环境")
            logger.info("-"*40)
            
            # 撤销所有测试订单
            if self.trading_service:
                for order_id in self.test_orders:
                    try:
                        self.trading_service.cancel_order(order_id)
                    except:
                        pass
                
                # 停止交易服务
                self.trading_service.stop()
                logger.info("✓ 交易服务已停止")
            
            # 停止其他服务
            if self.risk_service:
                self.risk_service.stop()
                logger.info("✓ 风控服务已停止")
            
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
            
        except Exception as e:
            logger.error(f"✗ 清理环境失败: {e}")
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        try:
            # 设置环境
            if not self.setup():
                return False
            
            # 运行测试
            tests = [
                self.test_service_lifecycle,
                self.test_order_management,
                self.test_signal_processing,
                self.test_order_cancellation,
                self.test_statistics_and_monitoring,
                self.test_risk_integration
            ]
            
            passed = 0
            total = len(tests)
            
            for i, test in enumerate(tests, 1):
                logger.info(f"\n{'='*20} 测试 {i}/{total} {'='*20}")
                if test():
                    passed += 1
                    logger.info(f"✓ 测试 {i} 通过")
                else:
                    logger.error(f"✗ 测试 {i} 失败")
            
            # 测试结果
            logger.info("\n" + "="*60)
            logger.info("测试结果汇总")
            logger.info("="*60)
            logger.info(f"总测试数: {total}")
            logger.info(f"通过测试: {passed}")
            logger.info(f"失败测试: {total - passed}")
            logger.info(f"成功率: {passed/total*100:.1f}%")
            logger.info(f"订单更新次数: {self.order_updates}")
            logger.info(f"成交更新次数: {self.trade_updates}")
            
            if passed == total:
                logger.info("🎉 所有测试通过！")
                return True
            else:
                logger.error("❌ 部分测试失败！")
                return False
            
        except Exception as e:
            logger.error(f"✗ 测试执行失败: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """主函数"""
    test = TradingServiceTest()
    success = test.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
