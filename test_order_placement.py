#!/usr/bin/env python3
"""
基于成功CTP连接的下单测试脚本
使用与ctp_connection_test.py相同的连接方式
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
    
    def send_test_order(self):
        """发送测试订单"""
        try:
            self.logger.info("📋 发送测试订单...")
            
            # 检查账户资金
            if not self.account_info:
                self.logger.error("无账户信息，无法下单")
                return False
            
            if self.account_info.available < 50000:  # 至少5万可用资金
                self.logger.error(f"可用资金不足: {self.account_info.available:,.2f}")
                return False
            
            # 选择黄金期货合约（排除期权）
            gold_contracts = [c for c in self.contracts.values()
                            if c.symbol.startswith("au") and c.exchange == Exchange.SHFE
                            and len(c.symbol) == 6 and c.symbol[2:].isdigit()]

            if not gold_contracts:
                self.logger.error("无可用的黄金期货合约")
                return False

            contract = sorted(gold_contracts, key=lambda x: x.symbol)[0]
            self.logger.info(f"选择交易合约: {contract.symbol}")
            
            # 获取当前行情
            tick = self.ticks.get(contract.vt_symbol)
            if not tick:
                self.logger.error("无行情数据，无法下单")
                return False
            
            current_price = tick.last_price
            # 使用买一价下单，确保能够立即成交，并调整到最小变动价位
            # 黄金期货最小变动价位是0.02元
            if hasattr(tick, 'ask_price_1') and tick.ask_price_1 > 0:
                order_price = tick.ask_price_1
            else:
                order_price = current_price

            # 调整价格到最小变动价位（0.02的倍数）
            order_price = round(order_price / 0.02) * 0.02
            
            self.logger.info(f"当前价格: {current_price}")
            self.logger.info(f"买一价: {getattr(tick, 'ask_price_1', 'N/A')}")
            self.logger.info(f"卖一价: {getattr(tick, 'bid_price_1', 'N/A')}")
            self.logger.info(f"下单价格: {order_price}")
            self.logger.info(f"合约信息: {contract.symbol} 交易所: {contract.exchange}")

            # 创建订单请求 - 使用限价单，价格设置为买一价确保成交
            order_req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=Direction.LONG,
                type=OrderType.LIMIT,  # 使用限价单
                volume=1,  # 1手黄金期货
                price=order_price,  # 使用调整后的价格
                offset=Offset.OPEN,  # 开仓
                reference="test_limit_order"
            )

            self.logger.info("订单参数详情:")
            self.logger.info(f"  symbol: {order_req.symbol}")
            self.logger.info(f"  exchange: {order_req.exchange}")
            self.logger.info(f"  direction: {order_req.direction}")
            self.logger.info(f"  type: {order_req.type}")
            self.logger.info(f"  volume: {order_req.volume}")
            self.logger.info(f"  price: {order_req.price}")
            self.logger.info(f"  offset: {order_req.offset}")
            self.logger.info(f"  reference: {order_req.reference}")
            
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
                else:
                    self.logger.warning("⚠ 未收到订单状态更新")
                
                return True
            else:
                self.logger.error("✗ 订单发送失败")
                return False
                
        except Exception as e:
            self.logger.error(f"发送测试订单失败: {e}")
            return False
    
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

def main():
    """主函数"""
    logger = setup_logging()
    tester = OrderTester(logger)
    
    try:
        logger.info("🧪 开始下单测试")
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
        
        # 4. 发送测试订单
        if not tester.send_test_order():
            logger.error("❌ 测试订单失败")
            return 1
        
        # 5. 等待观察
        logger.info("⏰ 等待30秒观察订单状态...")
        time.sleep(30)
        
        # 6. 撤销测试订单
        tester.cancel_test_orders()
        
        logger.info("🎉 下单测试完成!")
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
