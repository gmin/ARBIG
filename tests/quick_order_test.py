#!/usr/bin/env python3
"""
ARBIG快速下单测试脚本
简化版本，专门用于测试下单功能
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import get_service_container
from core.types import OrderRequest, Direction, OrderType, Offset
from utils.logger import get_logger

logger = get_logger(__name__)

def test_order_placement():
    """测试下单功能"""
    try:
        logger.info("🧪 快速下单测试")
        logger.info("=" * 40)
        
        # 1. 获取服务容器
        container = get_service_container()
        logger.info("✓ 获取服务容器成功")
        
        # 2. 启动系统
        logger.info("启动系统...")
        result = container.start_system()
        if not result.success:
            logger.error(f"系统启动失败: {result.message}")
            return False
        
        logger.info("✓ 系统启动成功")
        time.sleep(3)
        
        # 3. 启动必要的服务
        services_to_start = [
            'MarketDataService',
            'AccountService', 
            'RiskService',
            'TradingService'
        ]
        
        for service_name in services_to_start:
            logger.info(f"启动{service_name}...")
            result = container.start_service(service_name)
            if result.success:
                logger.info(f"✓ {service_name}启动成功")
            else:
                logger.error(f"✗ {service_name}启动失败: {result.message}")
                return False
            time.sleep(2)
        
        # 4. 检查服务状态
        logger.info("\n检查服务状态...")
        for service_name in services_to_start:
            status = container.get_service_status(service_name)
            logger.info(f"{service_name}: {status.get('status', 'unknown')}")
        
        # 5. 获取交易服务实例
        trading_service = container.services.get('TradingService')
        if not trading_service:
            logger.error("无法获取交易服务实例")
            return False
        
        logger.info("✓ 获取交易服务实例成功")
        
        # 6. 获取账户服务实例检查资金
        account_service = container.services.get('AccountService')
        if account_service:
            logger.info("查询账户信息...")
            account_service.query_account_info()
            time.sleep(2)
            
            account = account_service.get_account_info()
            if account:
                logger.info(f"✓ 账户资金: 总资金={account.balance:,.2f}, 可用={account.available:,.2f}")
            else:
                logger.warning("⚠ 无法获取账户信息")
        
        # 7. 获取行情服务检查价格
        market_service = container.services.get('MarketDataService')
        current_price = 500.0  # 默认价格
        
        if market_service:
            tick = market_service.get_latest_tick('au2509')
            if tick:
                current_price = tick.last_price
                logger.info(f"✓ 当前行情: au2509 @ {current_price}")
            else:
                logger.warning("⚠ 无法获取行情，使用默认价格")
        
        # 8. 创建测试订单（使用最新价，确保能够立即成交）
        test_price = current_price  # 使用最新价下单
        
        order_req = OrderRequest(
            symbol="au2509",
            exchange="SHFE", 
            direction=Direction.LONG,
            type=OrderType.LIMIT,
            volume=1.0,
            price=test_price,
            offset=Offset.OPEN,
            reference="quick_test_order"
        )
        
        logger.info(f"\n📋 发送测试订单:")
        logger.info(f"合约: {order_req.symbol}")
        logger.info(f"方向: {order_req.direction.value}")
        logger.info(f"数量: {order_req.volume}手")
        logger.info(f"价格: {order_req.price} (当前价格: {current_price})")
        logger.info(f"类型: {order_req.type.value}")
        
        # 9. 发送订单
        order_id = trading_service.send_order(order_req)
        
        if order_id:
            logger.info(f"✓ 订单发送成功! 订单ID: {order_id}")
            
            # 10. 等待并检查订单状态
            logger.info("等待订单状态更新...")
            time.sleep(3)
            
            order = trading_service.get_order(order_id)
            if order:
                logger.info(f"✓ 订单状态: {order.status.value}")
                logger.info(f"✓ 订单详情: {order.symbol} {order.direction.value} {order.volume}@{order.price}")
            else:
                logger.warning("⚠ 无法获取订单详情")
            
            # 11. 撤销测试订单
            logger.info(f"\n❌ 撤销测试订单: {order_id}")
            cancel_success = trading_service.cancel_order(order_id)
            
            if cancel_success:
                logger.info("✓ 订单撤销成功")
            else:
                logger.warning("⚠ 订单撤销失败")
            
            # 12. 再次检查订单状态
            time.sleep(2)
            order = trading_service.get_order(order_id)
            if order:
                logger.info(f"✓ 撤销后订单状态: {order.status.value}")
            
        else:
            logger.error("✗ 订单发送失败")
            return False
        
        logger.info("\n🎉 快速下单测试完成!")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

def main():
    """主函数"""
    try:
        logger.info("开始快速下单测试...")
        
        success = test_order_placement()
        
        if success:
            logger.info("✅ 测试成功完成")
            return 0
        else:
            logger.error("❌ 测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 0
    except Exception as e:
        logger.error(f"测试异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
