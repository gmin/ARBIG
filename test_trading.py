#!/usr/bin/env python3
"""
ARBIG交易测试脚本
测试下单功能，包括限价单、市价单等
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.event_engine import EventEngine
from core.config_manager import ConfigManager
from core.services.market_data_service import MarketDataService
from core.services.account_service import AccountService
from core.services.trading_service import TradingService
from core.services.risk_service import RiskService
from core.types import ServiceConfig, OrderRequest, Direction, OrderType, Offset
from gateways.ctp_gateway import CtpGatewayWrapper
from utils.logger import get_logger

logger = get_logger(__name__)

class TradingTester:
    """交易测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.running = False
        self.event_engine = None
        self.config_manager = None
        self.ctp_gateway = None
        self.market_data_service = None
        self.account_service = None
        self.risk_service = None
        self.trading_service = None
        
        # 测试订单记录
        self.test_orders = []
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("交易测试器初始化完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始停止测试...")
        self.stop()
        sys.exit(0)
    
    def setup(self) -> bool:
        """设置测试环境"""
        try:
            logger.info("=" * 60)
            logger.info("🧪 ARBIG交易功能测试")
            logger.info("=" * 60)
            
            # 1. 初始化事件引擎
            self.event_engine = EventEngine()
            self.event_engine.start()
            logger.info("✓ 事件引擎启动成功")
            
            # 2. 初始化配置管理器
            self.config_manager = ConfigManager()
            logger.info("✓ 配置管理器初始化成功")
            
            # 3. 初始化CTP网关
            self.ctp_gateway = CtpGatewayWrapper(self.config_manager)
            logger.info("✓ CTP网关初始化成功")
            
            return True
            
        except Exception as e:
            logger.error(f"设置测试环境失败: {e}")
            return False
    
    def connect_ctp(self) -> bool:
        """连接CTP"""
        try:
            logger.info("\n📡 连接CTP服务器...")
            
            if not self.ctp_gateway.connect():
                logger.error("CTP连接失败")
                return False
            
            logger.info("✓ CTP连接成功")
            
            # 等待连接稳定
            time.sleep(3)
            
            # 检查连接状态
            if not (self.ctp_gateway.is_md_connected() and self.ctp_gateway.is_td_connected()):
                logger.error("CTP连接状态异常")
                return False
            
            logger.info("✓ CTP连接状态正常")
            return True
            
        except Exception as e:
            logger.error(f"连接CTP失败: {e}")
            return False
    
    def start_services(self) -> bool:
        """启动服务"""
        try:
            logger.info("\n🔧 启动核心服务...")
            
            # 1. 启动行情服务
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
            
            if not self.market_data_service.start():
                logger.error("行情服务启动失败")
                return False
            
            logger.info("✓ 行情服务启动成功")
            time.sleep(2)
            
            # 2. 启动账户服务
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
                self.event_engine, account_config, self.ctp_gateway
            )
            
            if not self.account_service.start():
                logger.error("账户服务启动失败")
                return False
            
            logger.info("✓ 账户服务启动成功")
            time.sleep(2)
            
            # 3. 启动风控服务
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
            
            if not self.risk_service.start():
                logger.error("风控服务启动失败")
                return False
            
            logger.info("✓ 风控服务启动成功")
            time.sleep(2)
            
            # 4. 启动交易服务
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
            
            if not self.trading_service.start():
                logger.error("交易服务启动失败")
                return False
            
            logger.info("✓ 交易服务启动成功")
            
            # 等待服务稳定
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            return False
    
    def check_account_status(self) -> bool:
        """检查账户状态"""
        try:
            logger.info("\n💰 检查账户状态...")
            
            # 查询账户信息
            if not self.account_service.query_account_info():
                logger.error("查询账户信息失败")
                return False
            
            time.sleep(2)
            
            # 获取账户信息
            account = self.account_service.get_account_info()
            if not account:
                logger.error("无法获取账户信息")
                return False
            
            logger.info(f"✓ 账户ID: {account.accountid}")
            logger.info(f"✓ 总资金: {account.balance:,.2f}")
            logger.info(f"✓ 可用资金: {account.available:,.2f}")
            logger.info(f"✓ 冻结资金: {account.frozen:,.2f}")
            
            if account.available <= 0:
                logger.error("可用资金不足，无法进行交易测试")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查账户状态失败: {e}")
            return False
    
    def check_market_data(self) -> bool:
        """检查行情数据"""
        try:
            logger.info("\n📊 检查行情数据...")
            
            # 检查主力合约行情
            symbols = ['au2509', 'au2512']
            
            for symbol in symbols:
                tick = self.market_data_service.get_latest_tick(symbol)
                if tick:
                    logger.info(f"✓ {symbol}: {tick.last_price} (买:{tick.bid_price_1} 卖:{tick.ask_price_1})")
                else:
                    logger.warning(f"⚠ {symbol}: 无行情数据")
            
            return True
            
        except Exception as e:
            logger.error(f"检查行情数据失败: {e}")
            return False
    
    def test_limit_order(self) -> bool:
        """测试限价单"""
        try:
            logger.info("\n📋 测试限价单...")
            
            # 获取当前行情
            symbol = "au2509"
            tick = self.market_data_service.get_latest_tick(symbol)
            
            if not tick:
                logger.error(f"无法获取{symbol}行情，跳过限价单测试")
                return False
            
            current_price = tick.last_price
            logger.info(f"当前价格: {current_price}")
            
            # 创建买入限价单（价格设置得较低，不会立即成交）
            buy_price = current_price - 10.0
            
            order_req = OrderRequest(
                symbol=symbol,
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.LIMIT,
                volume=1.0,
                price=buy_price,
                offset=Offset.OPEN,
                reference="test_limit_buy"
            )
            
            logger.info(f"发送买入限价单: {symbol} {order_req.volume}手 @ {buy_price}")
            
            order_id = self.trading_service.send_order(order_req)
            if order_id:
                logger.info(f"✓ 限价单发送成功: {order_id}")
                self.test_orders.append(order_id)
                return True
            else:
                logger.error("✗ 限价单发送失败")
                return False
                
        except Exception as e:
            logger.error(f"测试限价单失败: {e}")
            return False
    
    def test_market_order(self) -> bool:
        """测试市价单（谨慎使用）"""
        try:
            logger.info("\n⚡ 测试市价单...")
            logger.warning("注意: 市价单会立即成交，请确认是否继续")
            
            # 为了安全，暂时跳过市价单测试
            logger.info("为了安全，跳过市价单测试")
            return True
            
            # 如果要测试市价单，取消下面的注释
            """
            symbol = "au2509"
            
            order_req = OrderRequest(
                symbol=symbol,
                exchange="SHFE",
                direction=Direction.LONG,
                type=OrderType.MARKET,
                volume=1.0,
                price=0.0,  # 市价单价格为0
                offset=Offset.OPEN,
                reference="test_market_buy"
            )
            
            logger.info(f"发送买入市价单: {symbol} {order_req.volume}手")
            
            order_id = self.trading_service.send_order(order_req)
            if order_id:
                logger.info(f"✓ 市价单发送成功: {order_id}")
                self.test_orders.append(order_id)
                return True
            else:
                logger.error("✗ 市价单发送失败")
                return False
            """
                
        except Exception as e:
            logger.error(f"测试市价单失败: {e}")
            return False
    
    def check_orders(self) -> None:
        """检查订单状态"""
        try:
            logger.info("\n📋 检查订单状态...")
            
            if not self.test_orders:
                logger.info("没有测试订单")
                return
            
            for order_id in self.test_orders:
                order = self.trading_service.get_order(order_id)
                if order:
                    logger.info(f"订单 {order_id[:8]}...: {order.symbol} {order.direction.value} "
                              f"{order.volume}@{order.price} 状态:{order.status.value}")
                else:
                    logger.warning(f"无法获取订单 {order_id} 信息")
            
        except Exception as e:
            logger.error(f"检查订单状态失败: {e}")
    
    def cancel_test_orders(self) -> None:
        """撤销测试订单"""
        try:
            logger.info("\n❌ 撤销测试订单...")
            
            if not self.test_orders:
                logger.info("没有需要撤销的订单")
                return
            
            for order_id in self.test_orders:
                success = self.trading_service.cancel_order(order_id)
                if success:
                    logger.info(f"✓ 订单 {order_id[:8]}... 撤销成功")
                else:
                    logger.warning(f"⚠ 订单 {order_id[:8]}... 撤销失败")
            
        except Exception as e:
            logger.error(f"撤销测试订单失败: {e}")
    
    def run_tests(self) -> bool:
        """运行交易测试"""
        try:
            self.running = True
            
            # 1. 检查账户状态
            if not self.check_account_status():
                return False
            
            # 2. 检查行情数据
            if not self.check_market_data():
                return False
            
            # 3. 测试限价单
            if not self.test_limit_order():
                return False
            
            # 等待订单处理
            time.sleep(3)
            
            # 4. 检查订单状态
            self.check_orders()
            
            # 5. 测试市价单（可选）
            # self.test_market_order()
            
            # 6. 等待一段时间观察
            logger.info("\n⏰ 等待30秒观察订单状态...")
            for i in range(30):
                if not self.running:
                    break
                time.sleep(1)
                if i % 10 == 9:
                    logger.info(f"等待中... {i+1}/30秒")
            
            # 7. 最终检查订单状态
            self.check_orders()
            
            # 8. 撤销测试订单
            self.cancel_test_orders()
            
            return True
            
        except Exception as e:
            logger.error(f"运行交易测试失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止测试"""
        try:
            self.running = False
            logger.info("\n🛑 停止交易测试...")
            
            # 撤销所有测试订单
            self.cancel_test_orders()
            
            # 停止服务
            services = [
                ("交易服务", self.trading_service),
                ("风控服务", self.risk_service),
                ("账户服务", self.account_service),
                ("行情服务", self.market_data_service)
            ]
            
            for service_name, service in services:
                if service:
                    try:
                        service.stop()
                        logger.info(f"✓ {service_name}已停止")
                    except Exception as e:
                        logger.error(f"✗ {service_name}停止失败: {e}")
            
            # 断开CTP连接
            if self.ctp_gateway:
                try:
                    self.ctp_gateway.disconnect()
                    logger.info("✓ CTP连接已断开")
                except Exception as e:
                    logger.error(f"✗ CTP断开失败: {e}")
            
            # 停止事件引擎
            if self.event_engine:
                try:
                    self.event_engine.stop()
                    logger.info("✓ 事件引擎已停止")
                except Exception as e:
                    logger.error(f"✗ 事件引擎停止失败: {e}")
            
            logger.info("✓ 交易测试停止完成")
            
        except Exception as e:
            logger.error(f"停止测试失败: {e}")

def main():
    """主函数"""
    tester = TradingTester()
    
    try:
        # 设置环境
        if not tester.setup():
            logger.error("❌ 测试环境设置失败")
            return 1
        
        # 连接CTP
        if not tester.connect_ctp():
            logger.error("❌ CTP连接失败")
            return 1
        
        # 启动服务
        if not tester.start_services():
            logger.error("❌ 服务启动失败")
            return 1
        
        # 运行测试
        if not tester.run_tests():
            logger.error("❌ 交易测试失败")
            return 1
        
        logger.info("🎉 交易测试完成")
        return 0
        
    except KeyboardInterrupt:
        logger.info("收到中断信号")
        return 0
    except Exception as e:
        logger.error(f"测试异常: {e}")
        return 1
    finally:
        tester.stop()

if __name__ == "__main__":
    exit(main())
