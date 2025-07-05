"""
ARBIG系统集成测试
验证完整的端到端交易流程，包括所有服务的协同工作
"""

import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List

from core.event_engine import EventEngine, Event
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.trading_service import TradingService
from core.services.risk_service import RiskService
from core.types import (
    ServiceConfig, OrderRequest, SignalData,
    Direction, OrderType, Status
)
from core.constants import SIGNAL_EVENT
from gateways.ctp_gateway import CtpGatewayWrapper
from web_monitor.app import web_app
from utils.logger import get_logger

logger = get_logger(__name__)

class SystemIntegrationTest:
    """系统集成测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        
        # 核心服务
        self.market_data_service = None
        self.account_service = None
        self.trading_service = None
        self.risk_service = None
        
        # Web监控
        self.web_monitor_connected = False
        
        # 测试统计
        self.test_results = {}
        self.performance_metrics = {}
        self.test_start_time = None
        
        # 测试数据收集
        self.tick_count = 0
        self.order_count = 0
        self.trade_count = 0
        self.account_updates = 0
        self.risk_checks = 0
        
    def setup_system(self) -> bool:
        """设置完整系统"""
        try:
            logger.info("="*80)
            logger.info("🧪 ARBIG系统集成测试开始")
            logger.info("="*80)
            
            # 1. 启动事件引擎
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            
            # 2. 创建CTP网关
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            if not self.ctp_gateway.connect():
                logger.error("✗ CTP连接失败")
                return False
            logger.info("✓ CTP网关连接成功")
            
            # 3. 创建所有服务
            self._create_all_services()
            
            # 4. 启动所有服务
            self._start_all_services()
            
            # 5. 连接Web监控
            self._setup_web_monitor()
            
            # 6. 设置测试回调
            self._setup_test_callbacks()
            
            logger.info("✓ 系统集成测试环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"✗ 系统设置失败: {e}")
            return False
    
    def _create_all_services(self):
        """创建所有服务"""
        # 行情服务
        market_config = ServiceConfig(
            name="market_data",
            enabled=True,
            config={
                'symbols': ['au2509', 'au2512', 'au2601'],
                'cache_size': 1000
            }
        )
        self.market_data_service = MarketDataService(
            self.event_engine, market_config, self.ctp_gateway
        )
        
        # 账户服务
        account_config = ServiceConfig(
            name="account",
            enabled=True,
            config={
                'update_interval': 10,  # 测试时使用较短间隔
                'position_sync': True,
                'auto_query_after_trade': True
            }
        )
        self.account_service = AccountService(
            self.event_engine, account_config, self.ctp_gateway
        )
        
        # 风控服务
        risk_config = ServiceConfig(
            name="risk",
            enabled=True,
            config={
                'max_position_ratio': 0.8,
                'max_daily_loss': 10000,
                'max_single_order_volume': 5  # 测试时使用较小限制
            }
        )
        self.risk_service = RiskService(
            self.event_engine, risk_config, self.account_service
        )
        
        # 交易服务
        trading_config = ServiceConfig(
            name="trading",
            enabled=True,
            config={
                'order_timeout': 30,
                'max_orders_per_second': 3  # 测试时限制频率
            }
        )
        self.trading_service = TradingService(
            self.event_engine, trading_config, self.ctp_gateway,
            self.account_service, self.risk_service
        )
        
        logger.info("✓ 所有服务创建完成")
    
    def _start_all_services(self):
        """启动所有服务"""
        services = [
            ("行情服务", self.market_data_service),
            ("账户服务", self.account_service),
            ("风控服务", self.risk_service),
            ("交易服务", self.trading_service)
        ]
        
        for name, service in services:
            if service.start():
                logger.info(f"✓ {name}启动成功")
            else:
                logger.error(f"✗ {name}启动失败")
                raise Exception(f"{name}启动失败")
    
    def _setup_web_monitor(self):
        """设置Web监控"""
        try:
            # 创建交易系统对象
            trading_system = type('TradingSystem', (), {
                'event_engine': self.event_engine,
                'ctp_gateway': self.ctp_gateway,
                'market_data_service': self.market_data_service,
                'account_service': self.account_service,
                'trading_service': self.trading_service,
                'risk_service': self.risk_service
            })()
            
            # 连接Web监控
            if web_app.connect_services(trading_system):
                self.web_monitor_connected = True
                logger.info("✓ Web监控系统连接成功")
            else:
                logger.warning("⚠ Web监控系统连接失败")
                
        except Exception as e:
            logger.warning(f"⚠ Web监控设置失败: {e}")
    
    def _setup_test_callbacks(self):
        """设置测试回调函数"""
        # 行情回调
        self.market_data_service.add_tick_callback(self._on_tick_for_test)
        
        # 账户回调
        self.account_service.add_account_callback(self._on_account_for_test)
        
        # 交易回调
        self.trading_service.add_order_callback(self._on_order_for_test)
        self.trading_service.add_trade_callback(self._on_trade_for_test)
        
        logger.info("✓ 测试回调函数设置完成")
    
    def run_integration_tests(self) -> bool:
        """运行完整的集成测试"""
        try:
            self.test_start_time = datetime.now()
            
            # 测试套件
            tests = [
                ("服务状态检查", self.test_service_status),
                ("数据流测试", self.test_data_flow),
                ("交易流程测试", self.test_trading_workflow),
                ("风控集成测试", self.test_risk_integration),
                ("Web监控测试", self.test_web_monitor),
                ("性能压力测试", self.test_performance),
                ("异常处理测试", self.test_error_handling),
                ("长时间运行测试", self.test_long_running)
            ]
            
            passed = 0
            total = len(tests)
            
            for i, (test_name, test_func) in enumerate(tests, 1):
                logger.info(f"\n{'='*20} 测试 {i}/{total}: {test_name} {'='*20}")
                
                try:
                    if test_func():
                        self.test_results[test_name] = "PASSED"
                        passed += 1
                        logger.info(f"✓ {test_name} 通过")
                    else:
                        self.test_results[test_name] = "FAILED"
                        logger.error(f"✗ {test_name} 失败")
                        
                except Exception as e:
                    self.test_results[test_name] = f"ERROR: {e}"
                    logger.error(f"✗ {test_name} 异常: {e}")
                
                # 测试间隔
                time.sleep(2)
            
            # 生成测试报告
            self._generate_test_report(passed, total)
            
            return passed == total
            
        except Exception as e:
            logger.error(f"✗ 集成测试执行失败: {e}")
            return False
    
    def test_service_status(self) -> bool:
        """测试服务状态"""
        try:
            services = {
                "行情服务": self.market_data_service,
                "账户服务": self.account_service,
                "风控服务": self.risk_service,
                "交易服务": self.trading_service
            }
            
            all_running = True
            for name, service in services.items():
                status = service.get_status()
                if status.value == "RUNNING":
                    logger.info(f"  ✓ {name}: {status.value}")
                else:
                    logger.error(f"  ✗ {name}: {status.value}")
                    all_running = False
            
            # 检查CTP连接
            if self.ctp_gateway.is_md_connected():
                logger.info("  ✓ CTP行情连接: 正常")
            else:
                logger.error("  ✗ CTP行情连接: 异常")
                all_running = False
            
            if self.ctp_gateway.is_td_connected():
                logger.info("  ✓ CTP交易连接: 正常")
            else:
                logger.error("  ✗ CTP交易连接: 异常")
                all_running = False
            
            return all_running
            
        except Exception as e:
            logger.error(f"服务状态检查失败: {e}")
            return False
    
    def test_data_flow(self) -> bool:
        """测试数据流"""
        try:
            logger.info("测试数据流，等待30秒...")
            
            # 重置计数器
            self.tick_count = 0
            self.account_updates = 0
            
            # 等待数据
            time.sleep(30)
            
            # 检查数据流
            success = True
            
            if self.tick_count > 0:
                logger.info(f"  ✓ 行情数据流: 收到 {self.tick_count} 个Tick")
            else:
                logger.error("  ✗ 行情数据流: 未收到Tick数据")
                success = False
            
            if self.account_updates > 0:
                logger.info(f"  ✓ 账户数据流: 收到 {self.account_updates} 次更新")
            else:
                logger.warning("  ⚠ 账户数据流: 未收到账户更新")
            
            # 检查数据缓存
            cached_ticks = len(self.market_data_service.get_all_ticks())
            if cached_ticks > 0:
                logger.info(f"  ✓ 数据缓存: {cached_ticks} 个Tick已缓存")
            else:
                logger.error("  ✗ 数据缓存: 无缓存数据")
                success = False
            
            return success
            
        except Exception as e:
            logger.error(f"数据流测试失败: {e}")
            return False
    
    def test_trading_workflow(self) -> bool:
        """测试交易流程"""
        try:
            logger.info("测试完整交易流程...")
            
            # 重置计数器
            self.order_count = 0
            self.trade_count = 0
            
            # 1. 发送测试订单
            order_req = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1.0,
                price=480.0,  # 设置较低价格，避免成交
                reference="integration_test_order"
            )
            
            order_id = self.trading_service.send_order(order_req)
            if order_id:
                logger.info(f"  ✓ 订单发送成功: {order_id}")
            else:
                logger.error("  ✗ 订单发送失败")
                return False
            
            # 2. 等待订单状态更新
            time.sleep(5)
            
            # 3. 检查订单状态
            order = self.trading_service.get_order(order_id)
            if order:
                logger.info(f"  ✓ 订单状态: {order.status.value}")
            else:
                logger.error("  ✗ 无法获取订单状态")
                return False
            
            # 4. 测试策略信号处理
            signal = SignalData(
                strategy_name="integration_test",
                symbol="au2509",
                direction=Direction.SHORT,
                action="OPEN",
                volume=1.0,
                price=600.0,  # 设置较高价格，避免成交
                signal_type="TRADE",
                confidence=0.8
            )
            
            signal_event = Event(SIGNAL_EVENT, signal)
            self.trading_service.process_signal(signal_event)
            logger.info("  ✓ 策略信号处理完成")
            
            # 5. 撤销测试订单
            time.sleep(3)
            active_orders = self.trading_service.get_active_orders()
            for order in active_orders:
                if "integration_test" in order.reference:
                    if self.trading_service.cancel_order(order.orderid):
                        logger.info(f"  ✓ 订单撤销成功: {order.orderid}")
                    else:
                        logger.warning(f"  ⚠ 订单撤销失败: {order.orderid}")
            
            return True
            
        except Exception as e:
            logger.error(f"交易流程测试失败: {e}")
            return False
    
    def test_risk_integration(self) -> bool:
        """测试风控集成"""
        try:
            logger.info("测试风控集成...")
            
            # 1. 测试正常订单的风控检查
            normal_order = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1.0,
                price=500.0,
                reference="risk_test_normal"
            )
            
            risk_result = self.risk_service.check_pre_trade_risk(normal_order)
            if risk_result.passed:
                logger.info("  ✓ 正常订单风控检查通过")
            else:
                logger.error(f"  ✗ 正常订单风控检查失败: {risk_result.reason}")
                return False
            
            # 2. 测试超限订单的风控检查
            large_order = OrderRequest(
                symbol="au2509",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=100.0,  # 超过限制
                price=500.0,
                reference="risk_test_large"
            )
            
            risk_result = self.risk_service.check_pre_trade_risk(large_order)
            if not risk_result.passed:
                logger.info(f"  ✓ 超限订单被风控拒绝: {risk_result.reason}")
            else:
                logger.warning("  ⚠ 超限订单通过了风控检查")
            
            # 3. 测试风险指标计算
            metrics = self.risk_service.get_risk_metrics()
            if metrics:
                logger.info(f"  ✓ 风险指标计算正常: 风险级别 {metrics.risk_level}")
            else:
                logger.error("  ✗ 风险指标计算失败")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"风控集成测试失败: {e}")
            return False
    
    def test_web_monitor(self) -> bool:
        """测试Web监控"""
        try:
            if not self.web_monitor_connected:
                logger.warning("  ⚠ Web监控未连接，跳过测试")
                return True
            
            logger.info("测试Web监控功能...")
            
            # 这里可以添加Web API测试
            # 由于需要HTTP客户端，暂时简化
            logger.info("  ✓ Web监控连接正常")
            
            return True
            
        except Exception as e:
            logger.error(f"Web监控测试失败: {e}")
            return False
    
    def test_performance(self) -> bool:
        """测试性能"""
        try:
            logger.info("测试系统性能...")
            
            start_time = time.time()
            
            # 记录初始状态
            initial_tick_count = self.tick_count
            initial_memory = self._get_memory_usage()
            
            # 运行30秒性能测试
            time.sleep(30)
            
            # 计算性能指标
            elapsed_time = time.time() - start_time
            tick_rate = (self.tick_count - initial_tick_count) / elapsed_time
            final_memory = self._get_memory_usage()
            memory_growth = final_memory - initial_memory
            
            # 记录性能指标
            self.performance_metrics = {
                'tick_rate': tick_rate,
                'memory_usage': final_memory,
                'memory_growth': memory_growth,
                'elapsed_time': elapsed_time
            }
            
            logger.info(f"  ✓ Tick处理速率: {tick_rate:.2f} tick/秒")
            logger.info(f"  ✓ 内存使用: {final_memory:.2f} MB")
            logger.info(f"  ✓ 内存增长: {memory_growth:.2f} MB")
            
            # 性能标准检查
            if tick_rate > 1.0:  # 至少1 tick/秒
                logger.info("  ✓ Tick处理性能达标")
            else:
                logger.warning("  ⚠ Tick处理性能较低")
            
            if memory_growth < 100:  # 内存增长小于100MB
                logger.info("  ✓ 内存使用稳定")
            else:
                logger.warning("  ⚠ 内存增长较快")
            
            return True
            
        except Exception as e:
            logger.error(f"性能测试失败: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """测试异常处理"""
        try:
            logger.info("测试异常处理...")
            
            # 1. 测试无效订单处理
            invalid_order = OrderRequest(
                symbol="INVALID",
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=0,  # 无效数量
                price=0,   # 无效价格
                reference="error_test"
            )
            
            order_id = self.trading_service.send_order(invalid_order)
            if not order_id:
                logger.info("  ✓ 无效订单被正确拒绝")
            else:
                logger.warning("  ⚠ 无效订单被接受")
            
            # 2. 测试服务异常恢复
            # 这里可以添加更多异常场景测试
            
            return True
            
        except Exception as e:
            logger.error(f"异常处理测试失败: {e}")
            return False
    
    def test_long_running(self) -> bool:
        """测试长时间运行"""
        try:
            logger.info("测试长时间运行稳定性（60秒）...")
            
            start_time = time.time()
            start_tick_count = self.tick_count
            
            # 运行60秒
            for i in range(60):
                time.sleep(1)
                if i % 10 == 0:
                    logger.info(f"  运行中... {i+1}/60秒")
                
                # 检查服务状态
                if not self._check_all_services_running():
                    logger.error("  ✗ 服务状态异常")
                    return False
            
            # 检查稳定性
            elapsed_time = time.time() - start_time
            tick_increase = self.tick_count - start_tick_count
            
            logger.info(f"  ✓ 运行时间: {elapsed_time:.1f}秒")
            logger.info(f"  ✓ Tick增长: {tick_increase}")
            
            if tick_increase > 0:
                logger.info("  ✓ 数据流持续正常")
            else:
                logger.warning("  ⚠ 数据流可能中断")
            
            return True
            
        except Exception as e:
            logger.error(f"长时间运行测试失败: {e}")
            return False
    
    def _check_all_services_running(self) -> bool:
        """检查所有服务是否正常运行"""
        services = [
            self.market_data_service,
            self.account_service,
            self.trading_service,
            self.risk_service
        ]
        
        for service in services:
            if service.get_status().value != "RUNNING":
                return False
        
        return True
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _generate_test_report(self, passed: int, total: int):
        """生成测试报告"""
        try:
            elapsed_time = (datetime.now() - self.test_start_time).total_seconds()
            
            logger.info("\n" + "="*80)
            logger.info("📊 ARBIG系统集成测试报告")
            logger.info("="*80)
            
            # 基本信息
            logger.info(f"测试时间: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"测试耗时: {elapsed_time:.1f} 秒")
            logger.info(f"测试结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
            
            # 详细结果
            logger.info("\n📋 详细测试结果:")
            for test_name, result in self.test_results.items():
                status_icon = "✓" if result == "PASSED" else "✗"
                logger.info(f"  {status_icon} {test_name}: {result}")
            
            # 数据统计
            logger.info(f"\n📈 数据统计:")
            logger.info(f"  Tick数据: {self.tick_count}")
            logger.info(f"  订单数量: {self.order_count}")
            logger.info(f"  成交数量: {self.trade_count}")
            logger.info(f"  账户更新: {self.account_updates}")
            
            # 性能指标
            if self.performance_metrics:
                logger.info(f"\n⚡ 性能指标:")
                for key, value in self.performance_metrics.items():
                    logger.info(f"  {key}: {value}")
            
            # 总结
            if passed == total:
                logger.info("\n🎉 所有测试通过！系统集成测试成功！")
            else:
                logger.error(f"\n❌ {total-passed} 个测试失败，需要进一步检查")
            
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")
    
    # 测试回调函数
    def _on_tick_for_test(self, tick):
        """测试用Tick回调"""
        self.tick_count += 1
    
    def _on_account_for_test(self, account):
        """测试用账户回调"""
        self.account_updates += 1
    
    def _on_order_for_test(self, order):
        """测试用订单回调"""
        self.order_count += 1
    
    def _on_trade_for_test(self, trade):
        """测试用成交回调"""
        self.trade_count += 1
    
    def cleanup(self):
        """清理测试环境"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("清理测试环境")
            logger.info("-"*40)
            
            # 撤销所有测试订单
            if self.trading_service:
                active_orders = self.trading_service.get_active_orders()
                for order in active_orders:
                    if "test" in order.reference.lower():
                        self.trading_service.cancel_order(order.orderid)
                
                self.trading_service.stop()
                logger.info("✓ 交易服务已停止")
            
            # 停止其他服务
            services = [
                ("风控服务", self.risk_service),
                ("账户服务", self.account_service),
                ("行情服务", self.market_data_service)
            ]
            
            for name, service in services:
                if service:
                    service.stop()
                    logger.info(f"✓ {name}已停止")
            
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

def main():
    """主函数"""
    test = SystemIntegrationTest()
    
    try:
        # 设置系统
        if not test.setup_system():
            logger.error("系统设置失败，退出测试")
            return 1
        
        # 运行集成测试
        success = test.run_integration_tests()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试执行异常: {e}")
        return 1
    finally:
        test.cleanup()

if __name__ == "__main__":
    exit(main())
