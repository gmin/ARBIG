"""
行情订阅服务测试
测试MarketDataService的完整功能
"""

import time
import threading
from datetime import datetime

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class MarketDataServiceTest:
    """行情服务测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.market_data_service = None
        
        # 测试统计
        self.tick_count = 0
        self.received_symbols = set()
        self.test_start_time = None
        
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("="*60)
            logger.info("行情订阅服务测试开始")
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
            
            # 创建行情服务配置
            service_config = ServiceConfig(
                name="market_data",
                enabled=True,
                config={
                    'symbols': ['au2509', 'au2512'],
                    'cache_size': 1000
                }
            )
            
            # 创建行情服务
            self.market_data_service = MarketDataService(
                self.event_engine, 
                service_config, 
                self.ctp_gateway
            )
            logger.info("✓ 行情服务创建成功")
            
            # 添加Tick回调用于测试统计
            self.market_data_service.add_tick_callback(self._on_tick_for_test)
            
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
            if not self.market_data_service.start():
                logger.error("✗ 服务启动失败")
                return False
            logger.info("✓ 服务启动成功")
            
            # 检查状态
            status = self.market_data_service.get_status()
            if status.value != "RUNNING":
                logger.error(f"✗ 服务状态错误: {status.value}")
                return False
            logger.info("✓ 服务状态正确")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 服务生命周期测试失败: {e}")
            return False
    
    def test_subscription_management(self) -> bool:
        """测试订阅管理"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试2: 订阅管理")
            logger.info("-"*40)
            
            # 测试订阅
            symbols = ['au2509', 'au2512']
            for symbol in symbols:
                success = self.market_data_service.subscribe_symbol(symbol, 'test_client')
                if success:
                    logger.info(f"✓ 订阅成功: {symbol}")
                else:
                    logger.error(f"✗ 订阅失败: {symbol}")
                    return False
            
            # 检查订阅状态
            subscription_status = self.market_data_service.get_subscription_status()
            logger.info(f"当前订阅状态: {subscription_status}")
            
            for symbol in symbols:
                if symbol not in subscription_status:
                    logger.error(f"✗ 订阅状态错误: {symbol} 未在订阅列表中")
                    return False
            
            logger.info("✓ 订阅状态检查通过")
            
            # 测试重复订阅
            success = self.market_data_service.subscribe_symbol('au2509', 'test_client2')
            if success:
                logger.info("✓ 重复订阅处理正确")
            else:
                logger.error("✗ 重复订阅处理失败")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 订阅管理测试失败: {e}")
            return False
    
    def test_market_data_reception(self) -> bool:
        """测试行情数据接收"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试3: 行情数据接收")
            logger.info("-"*40)
            
            # 重置统计
            self.tick_count = 0
            self.received_symbols.clear()
            self.test_start_time = datetime.now()
            
            # 等待行情数据
            logger.info("等待行情数据...")
            max_wait_time = 60  # 最大等待60秒
            wait_time = 0
            
            while wait_time < max_wait_time:
                time.sleep(1)
                wait_time += 1
                
                # 检查是否收到数据
                if self.tick_count > 0:
                    logger.info(f"✓ 开始接收行情数据，等待更多数据...")
                    break
                
                if wait_time % 10 == 0:
                    logger.info(f"等待行情数据... {wait_time}/{max_wait_time}秒")
            
            if self.tick_count == 0:
                logger.error("✗ 未收到任何行情数据")
                return False
            
            # 继续等待更多数据
            additional_wait = 30
            logger.info(f"继续收集数据 {additional_wait} 秒...")
            time.sleep(additional_wait)
            
            # 统计结果
            logger.info(f"✓ 总共收到 {self.tick_count} 个Tick数据")
            logger.info(f"✓ 涉及合约: {list(self.received_symbols)}")
            
            # 测试数据缓存
            for symbol in self.received_symbols:
                latest_tick = self.market_data_service.get_latest_tick(symbol)
                if latest_tick:
                    logger.info(f"✓ 缓存数据正常: {symbol} @ {latest_tick.last_price}")
                else:
                    logger.error(f"✗ 缓存数据缺失: {symbol}")
                    return False
            
            # 测试市场快照
            snapshot = self.market_data_service.get_market_snapshot()
            logger.info(f"✓ 市场快照包含 {len(snapshot.symbols)} 个合约")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 行情数据接收测试失败: {e}")
            return False
    
    def test_unsubscription(self) -> bool:
        """测试取消订阅"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试4: 取消订阅")
            logger.info("-"*40)
            
            # 取消订阅
            success = self.market_data_service.unsubscribe_symbol('au2509', 'test_client')
            if success:
                logger.info("✓ 取消订阅成功: au2509")
            else:
                logger.error("✗ 取消订阅失败: au2509")
                return False
            
            # 检查订阅状态
            subscription_status = self.market_data_service.get_subscription_status()
            logger.info(f"取消订阅后状态: {subscription_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 取消订阅测试失败: {e}")
            return False
    
    def test_service_statistics(self) -> bool:
        """测试服务统计"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试5: 服务统计")
            logger.info("-"*40)
            
            # 获取统计信息
            stats = self.market_data_service.get_statistics()
            logger.info("服务统计信息:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            
            # 验证关键统计
            if stats['status'] != 'RUNNING':
                logger.error(f"✗ 服务状态错误: {stats['status']}")
                return False
            
            if stats['cached_ticks'] == 0:
                logger.error("✗ 缓存Tick数量为0")
                return False
            
            logger.info("✓ 服务统计信息正常")
            return True
            
        except Exception as e:
            logger.error(f"✗ 服务统计测试失败: {e}")
            return False
    
    def _on_tick_for_test(self, tick) -> None:
        """测试用的Tick回调函数"""
        self.tick_count += 1
        self.received_symbols.add(tick.symbol)
        
        if self.tick_count % 10 == 0:
            logger.info(f"已收到 {self.tick_count} 个Tick数据")
    
    def cleanup(self) -> None:
        """清理测试环境"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("清理测试环境")
            logger.info("-"*40)
            
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
                self.test_subscription_management,
                self.test_market_data_reception,
                self.test_unsubscription,
                self.test_service_statistics
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
    test = MarketDataServiceTest()
    success = test.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
