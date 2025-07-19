#!/usr/bin/env python3
"""
测试CTP历史订单和成交查询功能
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_history_query():
    """测试历史数据查询"""
    print("🧪 测试CTP历史订单和成交查询...")
    print("=" * 50)
    
    try:
        # 导入vnpy相关模块
        from vnpy.event import EventEngine
        from vnpy_ctp import CtpGateway
        from vnpy.trader.setting import SETTINGS
        from vnpy.trader.object import OrderRequest, CancelRequest
        from vnpy.trader.constant import Direction, OrderType, Exchange
        
        print("✓ vnpy模块导入成功")
        
        # 读取CTP配置
        import json
        with open('config/ctp_sim.json', 'r', encoding='utf-8') as f:
            ctp_config = json.load(f)
        
        print("✓ CTP配置加载成功")
        print(f"  用户名: {ctp_config['用户名']}")
        print(f"  交易服务器: {ctp_config['交易服务器']}")
        print(f"  行情服务器: {ctp_config['行情服务器']}")

        # 转换为vnpy需要的格式
        vnpy_config = {
            "用户名": ctp_config["用户名"],
            "密码": ctp_config["密码"],
            "经纪商代码": ctp_config["经纪商代码"],
            "交易服务器": ctp_config["交易服务器"],
            "行情服务器": ctp_config["行情服务器"],
            "产品名称": ctp_config["产品名称"],
            "授权编码": ctp_config["授权编码"],
            "产品信息": ctp_config["产品信息"]
        }
        
        # 创建事件引擎
        event_engine = EventEngine()
        print("✓ 事件引擎创建成功")

        # 数据存储
        orders_received = {}
        trades_received = {}
        accounts_received = {}
        positions_received = {}

        # 事件处理函数
        def handle_order(event):
            order = event.data
            orders_received[order.vt_orderid] = order
            print(f"📋 收到订单: {order.symbol} {order.direction.value} {order.volume}@{order.price} [{order.status.value}] {order.datetime}")

        def handle_trade(event):
            trade = event.data
            trades_received[trade.vt_tradeid] = trade
            print(f"💰 收到成交: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price} {trade.datetime}")

        def handle_account(event):
            account = event.data
            accounts_received[account.accountid] = account
            print(f"💳 收到账户: {account.accountid} 余额={account.balance:,.2f}")

        def handle_position(event):
            position = event.data
            positions_received[position.vt_positionid] = position
            if position.volume > 0:
                print(f"📊 收到持仓: {position.symbol} {position.direction.value} {position.volume}手")

        # 注册事件处理器
        from vnpy.trader.event import EVENT_ORDER, EVENT_TRADE, EVENT_ACCOUNT, EVENT_POSITION
        event_engine.register(EVENT_ORDER, handle_order)
        event_engine.register(EVENT_TRADE, handle_trade)
        event_engine.register(EVENT_ACCOUNT, handle_account)
        event_engine.register(EVENT_POSITION, handle_position)

        # 创建CTP网关
        ctp_gateway = CtpGateway(event_engine, "CTP")
        print("✓ CTP网关创建成功")
        
        # 连接CTP
        print("\n📡 开始连接CTP...")
        ctp_gateway.connect(vnpy_config)
        
        # 等待连接成功
        print("⏳ 等待连接建立...")
        for i in range(30):  # 等待30秒
            time.sleep(1)
            if hasattr(ctp_gateway, 'td_api') and ctp_gateway.td_api and hasattr(ctp_gateway.td_api, 'login_status'):
                if ctp_gateway.td_api.login_status:
                    print("✓ 交易连接成功")
                    break
            print(f"  等待中... ({i+1}/30)")
        else:
            print("❌ 连接超时")
            return None
        
        # 等待初始数据加载
        print("\n⏳ 等待初始数据加载...")
        time.sleep(5)
        
        # 检查当前数据状态
        print(f"\n📊 当前数据状态:")

        # 检查vnpy网关的属性
        print("  检查vnpy网关属性...")
        gateway_attrs = [attr for attr in dir(ctp_gateway) if not attr.startswith('_')]
        data_attrs = [attr for attr in gateway_attrs if attr in ['orders', 'trades', 'positions', 'accounts']]
        print(f"  数据相关属性: {data_attrs}")

        # 尝试不同的方式获取数据
        orders_count = 0
        trades_count = 0
        positions_count = 0
        accounts_count = 0

        # 方法1: 直接属性
        if hasattr(ctp_gateway, 'orders'):
            orders_count = len(ctp_gateway.orders)
            print(f"  订单数 (直接): {orders_count}")

        if hasattr(ctp_gateway, 'trades'):
            trades_count = len(ctp_gateway.trades)
            print(f"  成交数 (直接): {trades_count}")

        if hasattr(ctp_gateway, 'positions'):
            positions_count = len(ctp_gateway.positions)
            print(f"  持仓数 (直接): {positions_count}")

        if hasattr(ctp_gateway, 'accounts'):
            accounts_count = len(ctp_gateway.accounts)
            print(f"  账户数 (直接): {accounts_count}")

        # 方法2: 通过main_engine
        if hasattr(ctp_gateway, 'main_engine'):
            main_engine = ctp_gateway.main_engine
            print(f"  找到main_engine: {type(main_engine)}")

            if hasattr(main_engine, 'get_all_orders'):
                all_orders = main_engine.get_all_orders()
                print(f"  订单数 (main_engine): {len(all_orders)}")
                orders_count = len(all_orders)

            if hasattr(main_engine, 'get_all_trades'):
                all_trades = main_engine.get_all_trades()
                print(f"  成交数 (main_engine): {len(all_trades)}")
                trades_count = len(all_trades)

        print(f"\n📊 数据统计:")
        print(f"  订单数: {orders_count}")
        print(f"  成交数: {trades_count}")
        print(f"  持仓数: {positions_count}")
        print(f"  账户数: {accounts_count}")
        
        # 尝试使用vnpy标准方法查询历史数据
        print(f"\n🔍 尝试使用vnpy标准方法查询历史数据...")

        # 使用vnpy的query_history方法
        if hasattr(ctp_gateway, 'query_history'):
            print("✓ 找到vnpy的query_history方法")
            try:
                print("📋 调用query_history查询历史订单和成交...")
                ctp_gateway.query_history()

                # 等待数据返回
                print("⏳ 等待历史数据返回...")
                for i in range(15):
                    time.sleep(1)
                    if orders_received or trades_received:
                        print(f"✓ 收到数据: 订单={len(orders_received)}, 成交={len(trades_received)}")
                        break
                    if i % 3 == 2:
                        print(f"    等待中... ({i+1}/15)")

            except Exception as e:
                print(f"❌ query_history调用失败: {e}")

        # 备用方法：直接使用CTP API
        if hasattr(ctp_gateway, 'td_api') and ctp_gateway.td_api:
            td_api = ctp_gateway.td_api
            print("✓ 找到交易API")
            
            # 检查查询方法
            query_methods = [method for method in dir(td_api) if method.startswith('req') and 'Qry' in method]
            print(f"  可用查询方法: {query_methods}")
            
            # 尝试查询订单
            if hasattr(td_api, 'reqQryOrder'):
                print("\n📋 尝试查询历史订单...")
                try:
                    # 创建查询请求（空请求获取所有订单）
                    req = {}
                    request_id = int(time.time() * 1000) % 1000000  # 生成请求ID
                    
                    result = td_api.reqQryOrder(req, request_id)
                    print(f"  查询请求发送结果: {result}")
                    
                    if result == 0:
                        print("  ✓ 订单查询请求发送成功，等待响应...")

                        # 等待更长时间，并显示进度
                        for i in range(10):
                            time.sleep(1)
                            if orders_received:
                                print(f"  ✓ 收到 {len(orders_received)} 个订单")
                                break
                            if i % 2 == 1:
                                print(f"    等待订单数据... ({i+1}/10)")

                        # 检查是否有新数据
                        print(f"  通过事件收到订单数: {len(orders_received)}")

                        new_orders_count = 0
                        if hasattr(ctp_gateway, 'orders'):
                            new_orders_count = len(ctp_gateway.orders)
                        elif hasattr(ctp_gateway, 'main_engine') and hasattr(ctp_gateway.main_engine, 'get_all_orders'):
                            new_orders_count = len(ctp_gateway.main_engine.get_all_orders())
                        print(f"  vnpy内部订单数: {new_orders_count}")
                        
                    else:
                        print(f"  ❌ 订单查询请求发送失败: {result}")
                        
                except Exception as e:
                    print(f"  ❌ 订单查询异常: {e}")
            
            # 尝试查询成交
            if hasattr(td_api, 'reqQryTrade'):
                print("\n💰 尝试查询历史成交...")
                try:
                    req = {}
                    request_id = int(time.time() * 1000) % 1000000
                    
                    result = td_api.reqQryTrade(req, request_id)
                    print(f"  查询请求发送结果: {result}")
                    
                    if result == 0:
                        print("  ✓ 成交查询请求发送成功，等待响应...")

                        # 等待更长时间，并显示进度
                        for i in range(10):
                            time.sleep(1)
                            if trades_received:
                                print(f"  ✓ 收到 {len(trades_received)} 个成交")
                                break
                            if i % 2 == 1:
                                print(f"    等待成交数据... ({i+1}/10)")

                        print(f"  通过事件收到成交数: {len(trades_received)}")

                        new_trades_count = 0
                        if hasattr(ctp_gateway, 'trades'):
                            new_trades_count = len(ctp_gateway.trades)
                        elif hasattr(ctp_gateway, 'main_engine') and hasattr(ctp_gateway.main_engine, 'get_all_trades'):
                            new_trades_count = len(ctp_gateway.main_engine.get_all_trades())
                        print(f"  vnpy内部成交数: {new_trades_count}")
                        
                    else:
                        print(f"  ❌ 成交查询请求发送失败: {result}")
                        
                except Exception as e:
                    print(f"  ❌ 成交查询异常: {e}")
            
            # 尝试查询持仓
            if hasattr(td_api, 'reqQryInvestorPosition'):
                print("\n📊 尝试查询持仓...")
                try:
                    req = {}
                    request_id = int(time.time() * 1000) % 1000000
                    
                    result = td_api.reqQryInvestorPosition(req, request_id)
                    print(f"  查询请求发送结果: {result}")
                    
                    if result == 0:
                        print("  ✓ 持仓查询请求发送成功，等待响应...")
                        time.sleep(3)
                        
                        new_positions_count = 0
                        if hasattr(ctp_gateway, 'positions'):
                            new_positions_count = len(ctp_gateway.positions)
                        print(f"  查询后持仓数: {new_positions_count}")
                        
                    else:
                        print(f"  ❌ 持仓查询请求发送失败: {result}")
                        
                except Exception as e:
                    print(f"  ❌ 持仓查询异常: {e}")
        
        # 最终数据统计
        print(f"\n📈 最终数据统计:")

        final_orders_count = 0
        final_trades_count = 0
        final_positions_count = 0
        final_accounts_count = 0

        # 获取最终数据
        all_orders = []
        all_trades = []

        if hasattr(ctp_gateway, 'orders'):
            final_orders_count = len(ctp_gateway.orders)
            all_orders = list(ctp_gateway.orders.items())
        elif hasattr(ctp_gateway, 'main_engine') and hasattr(ctp_gateway.main_engine, 'get_all_orders'):
            all_orders_list = ctp_gateway.main_engine.get_all_orders()
            final_orders_count = len(all_orders_list)
            all_orders = [(order.vt_orderid, order) for order in all_orders_list]

        if hasattr(ctp_gateway, 'trades'):
            final_trades_count = len(ctp_gateway.trades)
            all_trades = list(ctp_gateway.trades.items())
        elif hasattr(ctp_gateway, 'main_engine') and hasattr(ctp_gateway.main_engine, 'get_all_trades'):
            all_trades_list = ctp_gateway.main_engine.get_all_trades()
            final_trades_count = len(all_trades_list)
            all_trades = [(trade.vt_tradeid, trade) for trade in all_trades_list]

        if hasattr(ctp_gateway, 'positions'):
            final_positions_count = len(ctp_gateway.positions)

        if hasattr(ctp_gateway, 'accounts'):
            final_accounts_count = len(ctp_gateway.accounts)

        print(f"  vnpy订单数: {final_orders_count}")
        print(f"  vnpy成交数: {final_trades_count}")
        print(f"  vnpy持仓数: {final_positions_count}")
        print(f"  vnpy账户数: {final_accounts_count}")

        print(f"\n📊 通过事件接收的数据:")
        print(f"  事件订单数: {len(orders_received)}")
        print(f"  事件成交数: {len(trades_received)}")
        print(f"  事件持仓数: {len(positions_received)}")
        print(f"  事件账户数: {len(accounts_received)}")

        # 显示通过事件接收的订单详情
        if orders_received:
            print("\n📋 事件接收的订单详情:")
            for i, (order_id, order) in enumerate(orders_received.items()):
                if i >= 10:
                    print(f"  ... 还有 {len(orders_received) - 10} 个订单")
                    break
                print(f"  {order_id}: {order.symbol} {order.direction.value} {order.volume}@{order.price} [{order.status.value}] {order.datetime}")

        # 显示通过事件接收的成交详情
        if trades_received:
            print("\n💰 事件接收的成交详情:")
            total_turnover = 0
            for i, (trade_id, trade) in enumerate(trades_received.items()):
                if i >= 10:
                    print(f"  ... 还有 {len(trades_received) - 10} 个成交")
                    break
                turnover = trade.volume * trade.price
                total_turnover += turnover
                print(f"  {trade_id}: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price} (金额: {turnover:,.2f}) {trade.datetime}")

            if total_turnover > 0:
                print(f"  总成交金额: {total_turnover:,.2f}")

        # 显示vnpy内部数据详情
        if all_orders:
            print("\n📋 vnpy内部订单详情:")
            for i, (order_id, order) in enumerate(all_orders):
                if i >= 5:
                    print(f"  ... 还有 {len(all_orders) - 5} 个订单")
                    break
                print(f"  {order_id}: {order.symbol} {order.direction.value} {order.volume}@{order.price} [{order.status.value}] {order.datetime}")
        
        # 断开连接
        print(f"\n🔌 断开连接...")
        ctp_gateway.close()
        event_engine.stop()
        
        return {
            "vnpy_orders": final_orders_count,
            "vnpy_trades": final_trades_count,
            "vnpy_positions": final_positions_count,
            "vnpy_accounts": final_accounts_count,
            "event_orders": len(orders_received),
            "event_trades": len(trades_received),
            "event_positions": len(positions_received),
            "event_accounts": len(accounts_received)
        }
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_history_query()
    if result:
        print("\n🎉 测试完成！")
        print(f"vnpy数据: 订单={result['vnpy_orders']}, 成交={result['vnpy_trades']}, 持仓={result['vnpy_positions']}, 账户={result['vnpy_accounts']}")
        print(f"事件数据: 订单={result['event_orders']}, 成交={result['event_trades']}, 持仓={result['event_positions']}, 账户={result['event_accounts']}")
    else:
        print("\n❌ 测试失败！")
