#!/usr/bin/env python3
"""
ARBIG Web API交易测试脚本
通过Web API测试下单功能
"""

import sys
import time
import requests
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class WebTradingTester:
    """Web API交易测试器"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.test_orders = []
    
    def check_api_health(self) -> bool:
        """检查API健康状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✓ API服务正常")
                return True
            else:
                logger.error(f"API健康检查失败: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到API服务，请确保服务已启动")
            return False
        except Exception as e:
            logger.error(f"API健康检查异常: {e}")
            return False
    
    def start_system(self) -> bool:
        """启动系统"""
        try:
            logger.info("启动系统...")
            response = requests.post(f"{self.api_base}/system/start", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info("✓ 系统启动成功")
                    return True
                else:
                    logger.error(f"系统启动失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"系统启动请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"启动系统异常: {e}")
            return False
    
    def start_services(self) -> bool:
        """启动必要的服务"""
        try:
            services = [
                'MarketDataService',
                'AccountService',
                'RiskService', 
                'TradingService'
            ]
            
            for service_name in services:
                logger.info(f"启动{service_name}...")
                
                payload = {
                    "service_name": service_name,
                    "action": "start"
                }
                
                response = requests.post(
                    f"{self.api_base}/services/start",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        logger.info(f"✓ {service_name}启动成功")
                    else:
                        logger.error(f"{service_name}启动失败: {data.get('message')}")
                        return False
                else:
                    logger.error(f"{service_name}启动请求失败: {response.status_code}")
                    return False
                
                time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"启动服务异常: {e}")
            return False
    
    def check_system_status(self) -> dict:
        """检查系统状态"""
        try:
            response = requests.get(f"{self.api_base}/system/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    system_info = data.get('data', {})
                    logger.info(f"✓ 系统状态: {system_info.get('system_status')}")
                    logger.info(f"✓ 运行模式: {system_info.get('running_mode')}")
                    
                    # 显示服务状态
                    services_summary = system_info.get('services_summary', {})
                    logger.info(f"✓ 服务状态: 运行{services_summary.get('running', 0)}/总计{services_summary.get('total', 0)}")
                    
                    return system_info
                else:
                    logger.error(f"获取系统状态失败: {data.get('message')}")
                    return {}
            else:
                logger.error(f"系统状态请求失败: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"检查系统状态异常: {e}")
            return {}
    
    def get_account_info(self) -> dict:
        """获取账户信息"""
        try:
            response = requests.get(f"{self.api_base}/data/account/info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    account_info = data.get('data', {})
                    logger.info(f"✓ 账户资金: 总资金={account_info.get('total_assets', 0):,.2f}")
                    logger.info(f"✓ 可用资金: {account_info.get('available', 0):,.2f}")
                    return account_info
                else:
                    logger.warning(f"获取账户信息失败: {data.get('message')}")
                    return {}
            else:
                logger.warning(f"账户信息请求失败: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.warning(f"获取账户信息异常: {e}")
            return {}
    
    def get_market_data(self) -> dict:
        """获取行情数据"""
        try:
            response = requests.get(
                f"{self.api_base}/data/market/ticks?symbols=au2509&limit=1",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    ticks = data.get('data', {}).get('ticks', [])
                    if ticks:
                        tick = ticks[0]
                        logger.info(f"✓ 当前行情: {tick.get('symbol')} @ {tick.get('last_price')}")
                        return tick
                    else:
                        logger.warning("无行情数据")
                        return {}
                else:
                    logger.warning(f"获取行情失败: {data.get('message')}")
                    return {}
            else:
                logger.warning(f"行情请求失败: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.warning(f"获取行情异常: {e}")
            return {}
    
    def send_test_order(self) -> bool:
        """发送测试订单"""
        try:
            logger.info("\n📋 发送测试订单...")

            # 获取当前行情
            tick = self.get_market_data()
            current_price = tick.get('last_price', 500.0)

            # 创建限价买单（价格设置得较低，不会立即成交）
            test_price = current_price - 20.0

            logger.info(f"计划发送订单: au2509 买入 1手 @ {test_price}")
            logger.info(f"当前价格: {current_price}")

            # 发送订单请求
            order_payload = {
                "symbol": "au2509",
                "exchange": "SHFE",
                "direction": "LONG",
                "type": "LIMIT",
                "volume": 1.0,
                "price": test_price,
                "offset": "OPEN",
                "reference": "web_api_test"
            }

            response = requests.post(
                f"{self.api_base}/data/orders/send",
                json=order_payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    order_info = data.get('data', {})
                    order_id = order_info.get('order_id')
                    logger.info(f"✓ 订单发送成功: {order_id}")
                    logger.info(f"✓ 订单状态: {order_info.get('status')}")

                    # 保存订单ID用于后续撤销
                    self.test_orders.append(order_id)

                    # 等待一下然后撤销订单
                    time.sleep(3)
                    return self.cancel_test_order(order_id)
                else:
                    logger.error(f"订单发送失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"订单发送请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送测试订单异常: {e}")
            return False

    def cancel_test_order(self, order_id: str) -> bool:
        """撤销测试订单"""
        try:
            logger.info(f"\n❌ 撤销测试订单: {order_id}")

            response = requests.post(
                f"{self.api_base}/data/orders/cancel?order_id={order_id}",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info("✓ 订单撤销成功")
                    return True
                else:
                    logger.error(f"订单撤销失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"订单撤销请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"撤销订单异常: {e}")
            return False

    def get_orders(self) -> bool:
        """获取订单列表"""
        try:
            logger.info("\n📋 获取订单列表...")

            response = requests.get(f"{self.api_base}/data/orders", timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    orders = data.get('data', {}).get('orders', [])
                    logger.info(f"✓ 获取到 {len(orders)} 个订单")

                    for order in orders:
                        logger.info(f"  订单: {order.get('symbol')} {order.get('direction')} "
                                  f"{order.get('volume')}@{order.get('price')} 状态:{order.get('status')}")

                    return True
                else:
                    logger.warning(f"获取订单列表失败: {data.get('message')}")
                    return False
            else:
                logger.warning(f"订单列表请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.warning(f"获取订单列表异常: {e}")
            return False
    
    def run_test(self) -> bool:
        """运行完整测试"""
        try:
            logger.info("🧪 Web API交易测试")
            logger.info("=" * 40)
            
            # 1. 检查API健康状态
            if not self.check_api_health():
                return False
            
            # 2. 启动系统
            if not self.start_system():
                return False
            
            time.sleep(3)
            
            # 3. 启动服务
            if not self.start_services():
                return False
            
            time.sleep(5)
            
            # 4. 检查系统状态
            system_info = self.check_system_status()
            if not system_info:
                return False
            
            # 5. 获取账户信息
            self.get_account_info()
            
            # 6. 获取行情数据
            self.get_market_data()
            
            # 7. 获取订单列表
            self.get_orders()

            # 8. 发送测试订单
            if not self.send_test_order():
                return False

            # 9. 再次获取订单列表
            self.get_orders()

            logger.info("\n🎉 Web API测试完成!")
            return True
            
        except Exception as e:
            logger.error(f"测试异常: {e}")
            return False

def main():
    """主函数"""
    try:
        logger.info("开始Web API交易测试...")
        
        tester = WebTradingTester()
        success = tester.run_test()
        
        if success:
            logger.info("✅ 测试成功完成")
            logger.info("\n📝 测试总结:")
            logger.info("1. ✓ API服务连接正常")
            logger.info("2. ✓ 系统启动成功")
            logger.info("3. ✓ 服务启动成功")
            logger.info("4. ✓ 系统状态正常")
            logger.info("5. ⚠ 订单API需要进一步实现")
            
            logger.info("\n🎯 下一步建议:")
            logger.info("1. 使用 quick_order_test.py 进行直接下单测试")
            logger.info("2. 在Web API中添加订单管理接口")
            logger.info("3. 完善前端的交易功能")
            
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
