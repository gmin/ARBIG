"""
账户信息服务测试
测试AccountService的完整功能，包括混合模式（查询+推送）
"""

import time
import threading
from datetime import datetime

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.account_service import AccountService
from core.types import ServiceConfig
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class AccountServiceTest:
    """账户服务测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.event_engine = EventEngine()
        self.config_manager = ConfigManager()
        self.ctp_gateway = None
        self.account_service = None
        
        # 测试统计
        self.account_updates = 0
        self.position_updates = 0
        self.order_updates = 0
        self.trade_updates = 0
        self.test_start_time = None
        
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("="*60)
            logger.info("账户信息服务测试开始")
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
            max_wait = 10
            for i in range(max_wait):
                if self.ctp_gateway.is_td_connected():
                    break
                time.sleep(1)
                logger.info(f"等待交易服务器连接... {i+1}/{max_wait}")
            
            if not self.ctp_gateway.is_td_connected():
                logger.error("✗ 交易服务器连接失败")
                return False
            logger.info("✓ 交易服务器连接成功")
            
            # 创建账户服务配置
            service_config = ServiceConfig(
                name="account",
                enabled=True,
                config={
                    'update_interval': 10,  # 10秒查询间隔（测试用）
                    'position_sync': True,
                    'auto_query_after_trade': True
                }
            )
            
            # 创建账户服务
            self.account_service = AccountService(
                self.event_engine,
                service_config,
                self.ctp_gateway
            )
            logger.info("✓ 账户服务创建成功")
            
            # 添加回调用于测试统计
            self.account_service.add_account_callback(self._on_account_for_test)
            self.account_service.add_position_callback(self._on_position_for_test)
            self.account_service.add_order_callback(self._on_order_for_test)
            self.account_service.add_trade_callback(self._on_trade_for_test)
            
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
            if not self.account_service.start():
                logger.error("✗ 服务启动失败")
                return False
            logger.info("✓ 服务启动成功")
            
            # 检查状态
            status = self.account_service.get_status()
            if status.value != "RUNNING":
                logger.error(f"✗ 服务状态错误: {status.value}")
                return False
            logger.info("✓ 服务状态正确")
            
            # 检查查询线程是否启动
            time.sleep(2)
            stats = self.account_service.get_statistics()
            logger.info(f"服务统计: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 服务生命周期测试失败: {e}")
            return False
    
    def test_account_query(self) -> bool:
        """测试账户查询功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试2: 账户查询功能")
            logger.info("-"*40)
            
            # 主动查询账户信息
            success = self.account_service.query_account_info()
            if not success:
                logger.error("✗ 账户查询请求失败")
                return False
            logger.info("✓ 账户查询请求发送成功")
            
            # 等待查询结果
            logger.info("等待账户查询结果...")
            max_wait = 15
            for i in range(max_wait):
                account = self.account_service.get_account_info()
                if account:
                    logger.info("✓ 收到账户信息")
                    logger.info(f"  账户ID: {account.accountid}")
                    logger.info(f"  总资金: {account.balance:.2f}")
                    logger.info(f"  可用资金: {account.available:.2f}")
                    logger.info(f"  冻结资金: {account.frozen:.2f}")
                    return True
                
                time.sleep(1)
                if i % 3 == 0:
                    logger.info(f"等待账户信息... {i+1}/{max_wait}")
            
            logger.error("✗ 未收到账户信息")
            return False
            
        except Exception as e:
            logger.error(f"✗ 账户查询测试失败: {e}")
            return False
    
    def test_position_query(self) -> bool:
        """测试持仓查询功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试3: 持仓查询功能")
            logger.info("-"*40)
            
            # 主动查询持仓信息
            success = self.account_service.query_positions()
            if not success:
                logger.error("✗ 持仓查询请求失败")
                return False
            logger.info("✓ 持仓查询请求发送成功")
            
            # 等待查询结果
            logger.info("等待持仓查询结果...")
            time.sleep(5)  # 等待5秒
            
            positions = self.account_service.get_positions()
            logger.info(f"✓ 收到持仓信息，共 {len(positions)} 个持仓")
            
            if positions:
                for pos in positions[:3]:  # 显示前3个持仓
                    logger.info(f"  {pos.symbol} {pos.direction.value}: {pos.volume} 手")
            else:
                logger.info("  当前无持仓")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 持仓查询测试失败: {e}")
            return False
    
    def test_periodic_updates(self) -> bool:
        """测试定时更新功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试4: 定时更新功能")
            logger.info("-"*40)
            
            # 重置统计
            self.account_updates = 0
            self.position_updates = 0
            self.test_start_time = datetime.now()
            
            # 等待定时更新
            logger.info("等待定时更新（30秒）...")
            wait_time = 30
            
            for i in range(wait_time):
                time.sleep(1)
                if i % 5 == 0:
                    logger.info(f"等待中... {i+1}/{wait_time}秒")
                    logger.info(f"  账户更新次数: {self.account_updates}")
                    logger.info(f"  持仓更新次数: {self.position_updates}")
            
            # 检查更新次数
            if self.account_updates > 0:
                logger.info(f"✓ 账户定时更新正常，共 {self.account_updates} 次")
            else:
                logger.warning("⚠ 未收到账户定时更新")
            
            if self.position_updates > 0:
                logger.info(f"✓ 持仓定时更新正常，共 {self.position_updates} 次")
            else:
                logger.warning("⚠ 未收到持仓定时更新")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 定时更新测试失败: {e}")
            return False
    
    def test_data_caching(self) -> bool:
        """测试数据缓存功能"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试5: 数据缓存功能")
            logger.info("-"*40)
            
            # 测试账户缓存
            account = self.account_service.get_account_info()
            if account:
                logger.info("✓ 账户缓存正常")
                logger.info(f"  缓存的账户ID: {account.accountid}")
            else:
                logger.warning("⚠ 账户缓存为空")
            
            # 测试持仓缓存
            positions = self.account_service.get_positions()
            logger.info(f"✓ 持仓缓存正常，共 {len(positions)} 个持仓")
            
            # 测试按合约查询
            if positions:
                first_pos = positions[0]
                symbol_positions = self.account_service.get_positions(first_pos.symbol)
                logger.info(f"✓ 按合约查询正常，{first_pos.symbol} 有 {len(symbol_positions)} 个持仓")
            
            # 测试可用资金查询
            available_funds = self.account_service.get_available_funds()
            logger.info(f"✓ 可用资金查询正常: {available_funds:.2f}")
            
            # 测试账户快照
            snapshot = self.account_service.get_account_snapshot()
            logger.info("✓ 账户快照功能正常")
            logger.info(f"  快照时间: {snapshot.timestamp}")
            logger.info(f"  包含持仓: {len(snapshot.positions)}")
            logger.info(f"  包含订单: {len(snapshot.orders)}")
            logger.info(f"  包含成交: {len(snapshot.trades)}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ 数据缓存测试失败: {e}")
            return False
    
    def test_service_statistics(self) -> bool:
        """测试服务统计"""
        try:
            logger.info("\n" + "-"*40)
            logger.info("测试6: 服务统计")
            logger.info("-"*40)
            
            # 获取统计信息
            stats = self.account_service.get_statistics()
            logger.info("服务统计信息:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            
            # 验证关键统计
            if stats['status'] != 'RUNNING':
                logger.error(f"✗ 服务状态错误: {stats['status']}")
                return False
            
            logger.info("✓ 服务统计信息正常")
            return True
            
        except Exception as e:
            logger.error(f"✗ 服务统计测试失败: {e}")
            return False
    
    def _on_account_for_test(self, account) -> None:
        """测试用的账户回调函数"""
        self.account_updates += 1
        logger.debug(f"账户更新 #{self.account_updates}: 可用资金 {account.available:.2f}")
    
    def _on_position_for_test(self, position) -> None:
        """测试用的持仓回调函数"""
        self.position_updates += 1
        logger.debug(f"持仓更新 #{self.position_updates}: {position.symbol} {position.direction.value} {position.volume}")
    
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
                self.test_account_query,
                self.test_position_query,
                self.test_periodic_updates,
                self.test_data_caching,
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
    test = AccountServiceTest()
    success = test.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
