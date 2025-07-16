#!/usr/bin/env python3
"""
优化版下单测试脚本
支持开仓/平仓、做多/做空、多种订单类型
基于成功CTP连接的下单测试脚本
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest, OrderRequest
from vnpy.trader.constant import Exchange, Direction, OrderType, Offset
from vnpy.trader.event import EVENT_CONTRACT, EVENT_TICK, EVENT_LOG, EVENT_ORDER, EVENT_TRADE, EVENT_ACCOUNT, EVENT_POSITION

def setup_logging():
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("order_test")

def load_config():
    """加载配置文件"""
    config_file = Path("config/ctp_sim.json")
    
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config

def convert_to_vnpy_format(config):
    """转换为vnpy需要的格式"""
    return {
        "用户名": config["用户名"],
        "密码": config["密码"],
        "经纪商代码": config["经纪商代码"],
        "交易服务器": f"tcp://{config['交易服务器']}",
        "行情服务器": f"tcp://{config['行情服务器']}",
        "产品名称": config.get("产品名称", "simnow_client_test"),
        "授权编码": config.get("授权编码", "0000000000000000")
    }

class OrderTester:
    """下单测试器"""
    
    def __init__(self, logger):
        self.logger = logger
        self.event_engine = None
        self.main_engine = None
        self.ctp_gateway = None
        
        # 连接状态
        self.td_connected = False
        self.md_connected = False
        self.td_login_status = False
        self.md_login_status = False
        
        # 交易相关
        self.account_info = None
        self.positions = {}
        self.orders = {}
        self.trades = {}
        self.contracts = {}
        self.ticks = {}
        
        # 测试订单
        self.test_orders = []
    
    def setup_event_handlers(self):
        """设置事件处理器"""
        self.event_engine.register(EVENT_LOG, self.handle_log)
        self.event_engine.register(EVENT_CONTRACT, self.handle_contract)
        self.event_engine.register(EVENT_TICK, self.handle_tick)
        self.event_engine.register(EVENT_ORDER, self.handle_order)
        self.event_engine.register(EVENT_TRADE, self.handle_trade)
        self.event_engine.register(EVENT_ACCOUNT, self.handle_account)
        self.event_engine.register(EVENT_POSITION, self.handle_position)
    
    def handle_log(self, event):
        """处理日志事件"""
        log_data = event.data
        self.logger.info(f"[CTP日志] {log_data.msg}")
        
        # 检查连接状态
        if "交易服务器连接成功" in log_data.msg or "交易前置连接成功" in log_data.msg:
            self.td_connected = True
        elif "行情服务器连接成功" in log_data.msg or "行情前置连接成功" in log_data.msg:
            self.md_connected = True
        elif "交易服务器登录成功" in log_data.msg:
            self.td_login_status = True
        elif "行情服务器登录成功" in log_data.msg:
            self.md_login_status = True
    
    def handle_contract(self, event):
        """处理合约事件"""
        contract = event.data
        self.contracts[contract.vt_symbol] = contract
        if contract.symbol.startswith("au"):
            self.logger.info(f"发现黄金合约: {contract.symbol} - {contract.name}")
    
    def handle_tick(self, event):
        """处理行情事件"""
        tick = event.data
        self.ticks[tick.vt_symbol] = tick
        if tick.symbol.startswith("au"):
            self.logger.info(f"行情更新: {tick.symbol} 最新价={tick.last_price} 买价={tick.bid_price_1} 卖价={tick.ask_price_1}")
    
    def handle_order(self, event):
        """处理订单事件"""
        order = event.data
        self.orders[order.vt_orderid] = order
        self.logger.info(f"订单更新: {order.symbol} {order.direction.value} {order.volume}@{order.price} 状态:{order.status.value}")
    
    def handle_trade(self, event):
        """处理成交事件"""
        trade = event.data
        self.trades[trade.vt_tradeid] = trade
        self.logger.info(f"成交回报: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")
    
    def handle_account(self, event):
        """处理账户事件"""
        account = event.data
        self.account_info = account
        self.logger.info(f"账户更新: 总资金={account.balance:,.2f} 可用={account.available:,.2f} 冻结={account.frozen:,.2f}")
    
    def handle_position(self, event):
        """处理持仓事件"""
        position = event.data
        self.positions[position.vt_positionid] = position
        if position.volume > 0:
            self.logger.info(f"持仓更新: {position.symbol} {position.direction.value} 数量={position.volume}")
    
    def connect_ctp(self):
        """连接CTP"""
        try:
            # 加载配置
            config = load_config()
            vnpy_config = convert_to_vnpy_format(config)
            
            self.logger.info("🔗 开始连接CTP...")
            self.logger.info(f"用户名: {config['用户名']}")
            self.logger.info(f"经纪商代码: {config['经纪商代码']}")
            
            # 创建引擎
            self.event_engine = EventEngine()
            self.main_engine = MainEngine(self.event_engine)
            
            # 设置事件处理器
            self.setup_event_handlers()
            
            # 添加CTP网关
            self.main_engine.add_gateway(CtpGateway, "CTP")
            self.ctp_gateway = self.main_engine.get_gateway("CTP")
            
            # 连接
            self.ctp_gateway.connect(vnpy_config)
            
            # 等待连接
            self.logger.info("等待连接建立...")
            for i in range(20):
                time.sleep(1)
                if self.td_connected and self.md_connected and self.td_login_status and self.md_login_status:
                    self.logger.info("✓ CTP连接成功!")
                    return True
                
                if i % 5 == 4:
                    self.logger.info(f"连接中... {i+1}/20秒")
            
            # 检查连接状态
            if not (self.td_connected and self.td_login_status):
                self.logger.error("✗ 交易服务器连接失败")
                return False
            
            if not (self.md_connected and self.md_login_status):
                self.logger.error("✗ 行情服务器连接失败")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"CTP连接失败: {e}")
            return False
    
    def query_account_info(self):
        """查询账户信息"""
        try:
            self.logger.info("📊 查询账户信息...")
            self.ctp_gateway.query_account()
            
            # 等待账户信息
            for i in range(10):
                time.sleep(1)
                if self.account_info:
                    self.logger.info("✓ 账户信息查询成功")
                    return True
            
            self.logger.warning("⚠ 未收到账户信息")
            return False
            
        except Exception as e:
            self.logger.error(f"查询账户信息失败: {e}")
            return False
    
    def subscribe_market_data(self):
        """订阅行情数据"""
        try:
            self.logger.info("📈 订阅行情数据...")
            
            # 等待合约信息
            time.sleep(5)
            
            # 查找黄金期货合约（排除期权合约）
            gold_contracts = [c for c in self.contracts.values()
                            if c.symbol.startswith("au") and c.exchange == Exchange.SHFE
                            and len(c.symbol) == 6 and c.symbol[2:].isdigit()]  # au2508格式

            if not gold_contracts:
                self.logger.warning("未找到黄金期货合约")
                return False

            # 选择主力合约（通常是最近的月份）
            main_contract = sorted(gold_contracts, key=lambda x: x.symbol)[0]
            self.logger.info(f"选择合约: {main_contract.symbol}")
            req = SubscribeRequest(
                symbol=main_contract.symbol,
                exchange=main_contract.exchange
            )
            self.ctp_gateway.subscribe(req)
            self.logger.info(f"✓ 已订阅合约: {main_contract.symbol}")
            
            # 等待行情数据
            for i in range(10):
                time.sleep(1)
                if main_contract.vt_symbol in self.ticks:
                    self.logger.info("✓ 收到行情数据")
                    return True
            
            self.logger.warning("⚠ 未收到行情数据")
            return False
            
        except Exception as e:
            self.logger.error(f"订阅行情失败: {e}")
            return False
    
    def get_available_contracts(self):
        """获取可用的黄金期货合约"""
        gold_contracts = [c for c in self.contracts.values()
                        if c.symbol.startswith("au") and c.exchange == Exchange.SHFE
                        and len(c.symbol) == 6 and c.symbol[2:].isdigit()]
        return sorted(gold_contracts, key=lambda x: x.symbol)

    def get_current_positions(self):
        """获取当前持仓"""
        positions = {}
        for pos in self.positions.values():
            if pos.volume > 0:  # 只显示有持仓的合约
                positions[pos.vt_symbol] = pos
        return positions

    def calculate_order_price(self, tick, direction, order_type):
        """计算下单价格"""
        if order_type == OrderType.MARKET:
            return 0.0  # 市价单不需要价格

        current_price = tick.last_price

        if direction == Direction.LONG:
            # 买入：使用卖一价或当前价
            if hasattr(tick, 'ask_price_1') and tick.ask_price_1 > 0:
                price = tick.ask_price_1
            else:
                price = current_price
        else:
            # 卖出：使用买一价或当前价
            if hasattr(tick, 'bid_price_1') and tick.bid_price_1 > 0:
                price = tick.bid_price_1
            else:
                price = current_price

        # 调整价格到最小变动价位（0.02的倍数）
        return round(price / 0.02) * 0.02

    def send_order(self, symbol, direction, offset, order_type=OrderType.LIMIT, volume=1, price=None):
        """发送订单的通用方法"""
        try:
            # 检查账户资金
            if not self.account_info:
                self.logger.error("无账户信息，无法下单")
                return False

            if self.account_info.available < 50000:  # 至少5万可用资金
                self.logger.error(f"可用资金不足: {self.account_info.available:,.2f}")
                return False

            # 查找合约
            contract = None
            for c in self.contracts.values():
                if c.symbol == symbol and c.exchange == Exchange.SHFE:
                    contract = c
                    break

            if not contract:
                self.logger.error(f"未找到合约: {symbol}")
                return False

            # 获取当前行情
            tick = self.ticks.get(contract.vt_symbol)
            if not tick:
                self.logger.error("无行情数据，无法下单")
                return False

            # 计算下单价格
            if price is None:
                order_price = self.calculate_order_price(tick, direction, order_type)
            else:
                order_price = round(price / 0.02) * 0.02  # 调整到最小变动价位

            # 显示市场信息
            self.logger.info(f"📊 市场信息:")
            self.logger.info(f"  当前价格: {tick.last_price}")
            self.logger.info(f"  买一价: {getattr(tick, 'bid_price_1', 'N/A')}")
            self.logger.info(f"  卖一价: {getattr(tick, 'ask_price_1', 'N/A')}")
            self.logger.info(f"  成交量: {getattr(tick, 'volume', 'N/A')}")

            # 创建订单请求
            order_req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=direction,
                type=order_type,
                volume=volume,
                price=order_price,
                offset=offset,
                reference=f"enhanced_test_{direction.value}_{offset.value}"
            )

            # 显示订单详情
            direction_str = "买入" if direction == Direction.LONG else "卖出"
            offset_str = "开仓" if offset == Offset.OPEN else "平仓"
            type_str = "限价单" if order_type == OrderType.LIMIT else "市价单"

            self.logger.info(f"📋 订单详情:")
            self.logger.info(f"  合约: {order_req.symbol}")
            self.logger.info(f"  方向: {direction_str}")
            self.logger.info(f"  开平: {offset_str}")
            self.logger.info(f"  类型: {type_str}")
            self.logger.info(f"  数量: {order_req.volume}手")
            self.logger.info(f"  价格: {order_req.price if order_type == OrderType.LIMIT else '市价'}")

            # 发送订单
            vt_orderid = self.ctp_gateway.send_order(order_req)

            if vt_orderid:
                self.logger.info(f"✓ 订单发送成功: {vt_orderid}")
                self.test_orders.append(vt_orderid)

                # 等待订单状态更新
                time.sleep(3)

                # 检查订单状态
                if vt_orderid in self.orders:
                    order = self.orders[vt_orderid]
                    self.logger.info(f"✓ 订单状态: {order.status.value}")
                    if hasattr(order, 'traded') and order.traded > 0:
                        self.logger.info(f"✓ 已成交: {order.traded}手")
                else:
                    self.logger.warning("⚠ 未收到订单状态更新")

                return True
            else:
                self.logger.error("✗ 订单发送失败")
                return False

        except Exception as e:
            self.logger.error(f"发送订单失败: {e}")
            return False

    def send_test_order(self):
        """发送测试订单 - 保持向后兼容"""
        contracts = self.get_available_contracts()
        if not contracts:
            self.logger.error("无可用的黄金期货合约")
            return False

        contract = contracts[0]  # 选择第一个合约
        return self.send_order(
            symbol=contract.symbol,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            order_type=OrderType.LIMIT,
            volume=1
        )
    
    def cancel_test_orders(self):
        """撤销测试订单"""
        try:
            self.logger.info("❌ 撤销测试订单...")
            
            for vt_orderid in self.test_orders:
                if vt_orderid in self.orders:
                    order = self.orders[vt_orderid]
                    if order.status.value in ["提交中", "未成交"]:
                        cancel_req = order.create_cancel_request()
                        self.ctp_gateway.cancel_order(cancel_req)
                        self.logger.info(f"✓ 撤销订单: {vt_orderid}")
                    else:
                        self.logger.info(f"订单 {vt_orderid} 状态为 {order.status.value}，无需撤销")
            
            # 等待撤销结果
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"撤销订单失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.ctp_gateway:
                self.ctp_gateway.close()
            if self.main_engine:
                self.main_engine.close()
            self.logger.info("✓ 资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")

def show_menu():
    """显示交互菜单"""
    print("\n" + "="*60)
    print("🎛️  ARBIG 增强版下单测试系统")
    print("="*60)
    print("1. 📊 查看账户信息")
    print("2. 📈 查看可用合约")
    print("3. 📋 查看当前持仓")
    print("4. 🟢 做多开仓 (买入开仓)")
    print("5. 🔴 做空开仓 (卖出开仓)")
    print("6. ✅ 平多仓 (卖出平仓)")
    print("7. ✅ 平空仓 (买入平仓)")
    print("8. 📤 自定义下单")
    print("9. ❌ 撤销所有测试订单")
    print("10. 📊 查看订单状态")
    print("0. 🚪 退出系统")
    print("="*60)

def get_user_choice():
    """获取用户选择"""
    try:
        choice = input("请选择操作 (0-10): ").strip()
        return int(choice) if choice.isdigit() else -1
    except:
        return -1

def interactive_trading(tester):
    """交互式交易"""
    while True:
        show_menu()
        choice = get_user_choice()

        if choice == 0:
            print("👋 退出系统")
            break
        elif choice == 1:
            show_account_info(tester)
        elif choice == 2:
            show_available_contracts(tester)
        elif choice == 3:
            show_current_positions(tester)
        elif choice == 4:
            do_long_open(tester)
        elif choice == 5:
            do_short_open(tester)
        elif choice == 6:
            do_long_close(tester)
        elif choice == 7:
            do_short_close(tester)
        elif choice == 8:
            do_custom_order(tester)
        elif choice == 9:
            tester.cancel_test_orders()
        elif choice == 10:
            show_order_status(tester)
        else:
            print("❌ 无效选择，请重新输入")

        input("\n按Enter键继续...")

def show_account_info(tester):
    """显示账户信息"""
    if tester.account_info:
        print(f"\n💰 账户信息:")
        print(f"  账户ID: {tester.account_info.accountid}")
        print(f"  总资金: {tester.account_info.balance:,.2f}")
        print(f"  可用资金: {tester.account_info.available:,.2f}")
        print(f"  冻结资金: {tester.account_info.frozen:,.2f}")
    else:
        print("❌ 无账户信息")

def show_available_contracts(tester):
    """显示可用合约"""
    contracts = tester.get_available_contracts()
    if contracts:
        print(f"\n📈 可用黄金期货合约 ({len(contracts)}个):")
        for i, contract in enumerate(contracts, 1):
            tick = tester.ticks.get(contract.vt_symbol)
            price_info = f"价格: {tick.last_price}" if tick else "无行情"
            print(f"  {i}. {contract.symbol} - {price_info}")
    else:
        print("❌ 无可用合约")

def show_current_positions(tester):
    """显示当前持仓"""
    positions = tester.get_current_positions()
    if positions:
        print(f"\n📋 当前持仓 ({len(positions)}个):")
        for vt_symbol, pos in positions.items():
            direction = "多头" if pos.direction == Direction.LONG else "空头"
            pnl_str = f"盈亏: {pos.pnl:+.2f}" if hasattr(pos, 'pnl') else ""
            print(f"  {pos.symbol}: {direction} {pos.volume}手 @{pos.price:.2f} {pnl_str}")
    else:
        print("📋 当前无持仓")

def select_contract(tester):
    """选择合约"""
    contracts = tester.get_available_contracts()
    if not contracts:
        print("❌ 无可用合约")
        return None

    print("\n📈 选择合约:")
    for i, contract in enumerate(contracts, 1):
        tick = tester.ticks.get(contract.vt_symbol)
        price_info = f"价格: {tick.last_price}" if tick else "无行情"
        print(f"  {i}. {contract.symbol} - {price_info}")

    try:
        choice = int(input(f"请选择合约 (1-{len(contracts)}): ")) - 1
        if 0 <= choice < len(contracts):
            return contracts[choice].symbol
    except:
        pass

    print("❌ 无效选择")
    return None

def get_volume():
    """获取下单数量"""
    try:
        volume = int(input("请输入下单数量 (手, 默认1): ") or "1")
        if volume > 0:
            return volume
    except:
        pass
    print("❌ 无效数量，使用默认值1手")
    return 1

def do_long_open(tester):
    """做多开仓"""
    print("\n🟢 做多开仓 (买入开仓)")
    symbol = select_contract(tester)
    if symbol:
        volume = get_volume()
        tester.send_order(symbol, Direction.LONG, Offset.OPEN, OrderType.LIMIT, volume)

def do_short_open(tester):
    """做空开仓"""
    print("\n🔴 做空开仓 (卖出开仓)")
    symbol = select_contract(tester)
    if symbol:
        volume = get_volume()
        tester.send_order(symbol, Direction.SHORT, Offset.OPEN, OrderType.LIMIT, volume)

def do_long_close(tester):
    """平多仓"""
    print("\n✅ 平多仓 (卖出平仓)")
    positions = tester.get_current_positions()
    long_positions = {k: v for k, v in positions.items() if v.direction == Direction.LONG}

    if not long_positions:
        print("❌ 当前无多头持仓")
        return

    print("选择要平仓的多头持仓:")
    pos_list = list(long_positions.items())
    for i, (vt_symbol, pos) in enumerate(pos_list, 1):
        print(f"  {i}. {pos.symbol}: {pos.volume}手 @{pos.price:.2f}")

    try:
        choice = int(input(f"请选择 (1-{len(pos_list)}): ")) - 1
        if 0 <= choice < len(pos_list):
            vt_symbol, pos = pos_list[choice]

            # 选择平仓类型
            print("\n选择平仓类型:")
            print("1. 平今仓 (平当日开仓)")
            print("2. 平昨仓 (平昨日持仓)")
            print("3. 自动平仓 (系统自动选择)")

            try:
                offset_choice = int(input("请选择 (1-3): "))
                if offset_choice == 1:
                    offset = Offset.CLOSETODAY
                    offset_desc = "平今仓"
                elif offset_choice == 2:
                    offset = Offset.CLOSEYESTERDAY
                    offset_desc = "平昨仓"
                else:
                    offset = Offset.CLOSE
                    offset_desc = "自动平仓"

                print(f"\n📋 平仓类型: {offset_desc}")
                max_volume = int(pos.volume)
                volume = min(get_volume(), max_volume)
                tester.send_order(pos.symbol, Direction.SHORT, offset, OrderType.LIMIT, volume)
            except:
                print("❌ 无效的平仓类型选择")
    except:
        print("❌ 无效选择")

def do_short_close(tester):
    """平空仓"""
    print("\n✅ 平空仓 (买入平仓)")
    positions = tester.get_current_positions()
    short_positions = {k: v for k, v in positions.items() if v.direction == Direction.SHORT}

    if not short_positions:
        print("❌ 当前无空头持仓")
        return

    print("选择要平仓的空头持仓:")
    pos_list = list(short_positions.items())
    for i, (vt_symbol, pos) in enumerate(pos_list, 1):
        print(f"  {i}. {pos.symbol}: {pos.volume}手 @{pos.price:.2f}")

    try:
        choice = int(input(f"请选择 (1-{len(pos_list)}): ")) - 1
        if 0 <= choice < len(pos_list):
            vt_symbol, pos = pos_list[choice]

            # 选择平仓类型
            print("\n选择平仓类型:")
            print("1. 平今仓 (平当日开仓)")
            print("2. 平昨仓 (平昨日持仓)")
            print("3. 自动平仓 (系统自动选择)")

            try:
                offset_choice = int(input("请选择 (1-3): "))
                if offset_choice == 1:
                    offset = Offset.CLOSETODAY
                    offset_desc = "平今仓"
                elif offset_choice == 2:
                    offset = Offset.CLOSEYESTERDAY
                    offset_desc = "平昨仓"
                else:
                    offset = Offset.CLOSE
                    offset_desc = "自动平仓"

                print(f"\n📋 平仓类型: {offset_desc}")
                max_volume = int(pos.volume)
                volume = min(get_volume(), max_volume)
                tester.send_order(pos.symbol, Direction.LONG, offset, OrderType.LIMIT, volume)
            except:
                print("❌ 无效的平仓类型选择")
    except:
        print("❌ 无效选择")

def do_custom_order(tester):
    """自定义下单"""
    print("\n📤 自定义下单")

    # 选择合约
    symbol = select_contract(tester)
    if not symbol:
        return

    # 选择方向
    print("\n选择交易方向:")
    print("1. 买入")
    print("2. 卖出")
    try:
        dir_choice = int(input("请选择 (1-2): "))
        direction = Direction.LONG if dir_choice == 1 else Direction.SHORT
    except:
        print("❌ 无效选择")
        return

    # 选择开平仓
    print("\n选择开平仓:")
    print("1. 开仓")
    print("2. 平仓")
    try:
        offset_choice = int(input("请选择 (1-2): "))
        if offset_choice == 1:
            offset = Offset.OPEN
            offset_desc = "开仓"
        else:
            # 如果选择平仓，进一步选择平仓类型
            print("\n选择平仓类型:")
            print("1. 平今仓 (平当日开仓)")
            print("2. 平昨仓 (平昨日持仓)")
            print("3. 自动平仓 (系统自动选择)")

            try:
                close_choice = int(input("请选择 (1-3): "))
                if close_choice == 1:
                    offset = Offset.CLOSETODAY
                    offset_desc = "平今仓"
                elif close_choice == 2:
                    offset = Offset.CLOSEYESTERDAY
                    offset_desc = "平昨仓"
                else:
                    offset = Offset.CLOSE
                    offset_desc = "自动平仓"
            except:
                print("❌ 无效的平仓类型选择")
                return

        print(f"\n📋 开平仓类型: {offset_desc}")
    except:
        print("❌ 无效选择")
        return

    # 选择订单类型
    print("\n选择订单类型:")
    print("1. 限价单")
    print("2. 市价单")
    try:
        type_choice = int(input("请选择 (1-2): "))
        order_type = OrderType.LIMIT if type_choice == 1 else OrderType.MARKET
    except:
        print("❌ 无效选择")
        return

    # 获取数量
    volume = get_volume()

    # 获取价格（限价单）
    price = None
    if order_type == OrderType.LIMIT:
        try:
            price_input = input("请输入价格 (留空使用市场价): ").strip()
            if price_input:
                price = float(price_input)
        except:
            print("❌ 无效价格，将使用市场价")

    # 发送订单
    tester.send_order(symbol, direction, offset, order_type, volume, price)

def show_order_status(tester):
    """显示订单状态"""
    if tester.test_orders:
        print(f"\n📊 测试订单状态 ({len(tester.test_orders)}个):")
        for vt_orderid in tester.test_orders:
            if vt_orderid in tester.orders:
                order = tester.orders[vt_orderid]
                print(f"  {vt_orderid}: {order.status.value}")
                if hasattr(order, 'traded') and order.traded > 0:
                    print(f"    已成交: {order.traded}手")
            else:
                print(f"  {vt_orderid}: 状态未知")
    else:
        print("📊 当前无测试订单")

def main():
    """主函数"""
    logger = setup_logging()
    tester = OrderTester(logger)

    try:
        logger.info("🧪 开始增强版下单测试")
        logger.info("=" * 50)

        # 1. 连接CTP
        if not tester.connect_ctp():
            logger.error("❌ CTP连接失败")
            return 1

        # 2. 查询账户信息
        if not tester.query_account_info():
            logger.error("❌ 账户信息查询失败")
            return 1

        # 3. 订阅行情
        if not tester.subscribe_market_data():
            logger.error("❌ 行情订阅失败")
            return 1

        logger.info("✅ 系统初始化完成，进入交互模式")

        # 4. 进入交互模式
        interactive_trading(tester)

        # 5. 退出前撤销所有测试订单
        if tester.test_orders:
            print("\n🧹 清理测试订单...")
            tester.cancel_test_orders()

        logger.info("🎉 测试完成!")
        return 0

    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        return 0
    except Exception as e:
        logger.error(f"测试异常: {e}")
        return 1
    finally:
        tester.cleanup()

if __name__ == "__main__":
    exit(main())
