# ctp_connection_test.py
import time
import logging
import socket
import os
from datetime import datetime
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest, OrderRequest
from vnpy.trader.constant import Exchange, Direction, OrderType, Offset
from vnpy.trader.event import EVENT_CONTRACT, EVENT_TICK, EVENT_LOG, EVENT_ORDER, EVENT_TRADE, EVENT_ACCOUNT

def setup_logging():
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("ctp_test")

def check_network_connection(host, port, timeout=5):
    """检查网络连接"""
    try:
        start = datetime.now()
        with socket.create_connection((host, port), timeout=timeout):
            latency = (datetime.now() - start).total_seconds() * 1000
            return True, f"连接成功! 延迟: {latency:.2f}ms"
    except Exception as e:
        return False, f"连接失败: {str(e)}"

def load_config():
    """加载配置文件"""
    import json
    from pathlib import Path
    
    config_file = Path("config/ctp_sim.json")
 
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    logger.info(f"加载配置文件: config/ctp_sim.json")

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

def test_ctp_connection(logger):
    """测试CTP连接"""
    # 首先读取配置文件（在可能修改工作目录的代码之前）
    try:
        config = load_config()
        vnpy_config = convert_to_vnpy_format(config)
        logger.info(f"用户名: {config['用户名']}")
        logger.info(f"经纪商代码: {config['经纪商代码']}")
        logger.info(f"交易服务器: {config['交易服务器']}")
        logger.info(f"行情服务器: {config['行情服务器']}")
        logger.info("")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return
    # ========== 网络连接测试 ==========
    logger.info("="*50)
    logger.info("网络连接测试")
    logger.info("="*50)
    
    # 从配置中解析服务器信息
    def parse_servers_from_config(config):
        servers = []
        
        # 解析交易服务器
        if "交易服务器" in config:
            td_server = config["交易服务器"]
            host, port = td_server.split(":")
            servers.append(("交易服务器", host, int(port)))
        
        # 解析行情服务器
        if "行情服务器" in config:
            md_server = config["行情服务器"]
            host, port = md_server.split(":")
            servers.append(("行情服务器", host, int(port)))
        
        return servers
    
    servers = parse_servers_from_config(config)
    
    # 检查网络连接
    network_ok = True
    for name, host, port in servers:
        success, msg = check_network_connection(host, port)
        status = "✓" if success else "✗"
        logger.info(f"{status} {name} {host}:{port} - {msg}")
        if not success:
            network_ok = False
    
    # 如果网络连接失败，提前退出
    if not network_ok:
        logger.error("网络连接失败，无法继续测试。请检查：")
        logger.error("1. 网络连接是否正常")
        logger.error("2. 防火墙是否阻止了连接")
        logger.error("3. 服务器地址和端口是否正确")
        logger.error("4. 是否在正确的网络环境中")
        return
    
    # ========== 创建CTP网关 ==========
    logger.info("\n" + "="*50)
    logger.info("创建CTP网关")
    logger.info("="*50)
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加CTP网关
    main_engine.add_gateway(CtpGateway, "CTP")
    ctp_gateway = main_engine.get_gateway("CTP")
    
    # ========== 账户信息验证 ==========
    logger.info("\n" + "="*50)
    logger.info("账户信息验证")
    logger.info("="*50)
    logger.info(f"经纪商代码: {config['经纪商代码']}")
    logger.info(f"用户名: {config['用户名']}")
    logger.info(f"密码: {'*' * len(config['密码'])}")
    logger.info(f"产品名称: {config.get('产品名称', 'simnow_client_test')}")
    logger.info(f"授权编码: {config.get('授权编码', '0000000000000000')}")
    
    # 存储交易相关数据
    account_info = None
    test_orders = []

    # 注册事件处理函数
    def handle_event(event):
        nonlocal account_info
        if event.type == EVENT_LOG:
            logger.info(f"[日志] {event.data}")
        elif event.type == EVENT_CONTRACT:
            contract = event.data
            if contract.symbol.startswith("au"):
                logger.info(f"发现黄金合约: {contract.symbol} - {contract.name}")
        elif event.type == EVENT_TICK:
            tick = event.data
            logger.info(f"行情更新: {tick.symbol} 最新价={tick.last_price} 量={tick.volume}")
        elif event.type == EVENT_ORDER:
            order = event.data
            logger.info(f"📋 订单更新: {order.symbol} {order.direction.value} {order.volume}@{order.price} 状态:{order.status.value}")
        elif event.type == EVENT_TRADE:
            trade = event.data
            logger.info(f"💰 成交回报: {trade.symbol} {trade.direction.value} {trade.volume}@{trade.price}")
        elif event.type == EVENT_ACCOUNT:
            account = event.data
            account_info = account
            logger.info(f"💳 账户更新: 总资金={account.balance:,.2f} 可用={account.available:,.2f}")

    event_engine.register(EVENT_LOG, handle_event)
    event_engine.register(EVENT_CONTRACT, handle_event)
    event_engine.register(EVENT_TICK, handle_event)
    event_engine.register(EVENT_ORDER, handle_event)
    event_engine.register(EVENT_TRADE, handle_event)
    event_engine.register(EVENT_ACCOUNT, handle_event)
    
    # ========== 连接CTP ==========
    logger.info("\n" + "="*50)
    logger.info("开始连接CTP服务器...")
    logger.info("="*50)
    ctp_gateway.connect(vnpy_config)
    
    # 延长等待时间
    logger.info("等待连接建立(15秒)...")
    time.sleep(15)
    
    # ========== 连接状态检查 ==========
    td_connected = False
    md_connected = False
    td_login_status = False
    md_login_status = False
    
    # 交易服务器状态
    if hasattr(ctp_gateway, 'td_api'):
        td_connected = getattr(ctp_gateway.td_api, 'connect_status', False)
        logger.info(f"交易服务器连接状态: {'✓ 成功' if td_connected else '✗ 失败'}")
        
        if td_connected:
            td_login_status = getattr(ctp_gateway.td_api, 'login_status', False)
            logger.info(f"交易服务器登录状态: {'✓ 成功' if td_login_status else '✗ 失败'}")
            logger.info(f"交易日: {getattr(ctp_gateway.td_api, 'trading_day', '未知')}")
            
            # 错误信息捕获
            if hasattr(ctp_gateway.td_api, 'error_message'):
                error_msg = ctp_gateway.td_api.error_message
                logger.error(f"交易API错误信息: {error_msg}")
                
                # 常见错误解析
                if "错误代码=3" in error_msg:
                    logger.error("原因: 无效密码 - 请检查密码大小写和特殊字符")
                elif "错误代码=5" in error_msg:
                    logger.error("原因: 未登录 - 请检查用户名/经纪商代码")
                elif "错误代码=7" in error_msg:
                    logger.error("原因: 连接断开 - 网络问题或服务器限制")
                elif "错误代码=1001" in error_msg:
                    logger.error("原因: 网络连接失败 - 检查防火墙/端口")
    
    # 行情服务器状态
    if hasattr(ctp_gateway, 'md_api'):
        md_connected = getattr(ctp_gateway.md_api, 'connect_status', False)
        logger.info(f"行情服务器连接状态: {'✓ 成功' if md_connected else '✗ 失败'}")
        
        if md_connected:
            md_login_status = getattr(ctp_gateway.md_api, 'login_status', False)
            logger.info(f"行情服务器登录状态: {'✓ 成功' if md_login_status else '✗ 失败'}")
            
            if hasattr(ctp_gateway.md_api, 'error_message'):
                logger.error(f"行情API错误信息: {ctp_gateway.md_api.error_message}")
    
    # ========== 合约查询与订阅 ==========
    # 收集合约并订阅主力合约
    if md_connected and md_login_status:
        logger.info("等待合约推送(10秒)...")
        time.sleep(10)
        
        # 获取所有合约
        all_contracts = main_engine.get_all_contracts()
        if all_contracts:
            logger.info(f"收到 {len(all_contracts)} 个合约")
            
            # 筛选黄金合约
            gold_contracts = [c for c in all_contracts if c.symbol.startswith("au") and c.exchange == Exchange.SHFE]
            if gold_contracts:
                # 按持仓量排序，选择主力合约
                gold_contracts.sort(key=lambda c: getattr(c, 'open_interest', 0) or 0, reverse=True)
                main_contract = gold_contracts[0]
                
                logger.info(f"选择主力合约: {main_contract.symbol} (持仓量: {getattr(main_contract, 'open_interest', 0)})")
                
                try:
                    req = SubscribeRequest(
                        symbol=main_contract.symbol,
                        exchange=main_contract.exchange
                    )
                    ctp_gateway.subscribe(req)
                    logger.info(f"已订阅主力合约: {main_contract.symbol}")
                except Exception as e:
                    logger.error(f"订阅主力合约失败: {e}")
            else:
                logger.warning("未找到黄金合约，尝试订阅默认合约")
                # 如果没有黄金合约，订阅第一个可用的合约
                try:
                    first_contract = all_contracts[0]
                    req = SubscribeRequest(
                        symbol=first_contract.symbol,
                        exchange=first_contract.exchange
                    )
                    ctp_gateway.subscribe(req)
                    logger.info(f"已订阅默认合约: {first_contract.symbol}")
                except Exception as e:
                    logger.error(f"订阅默认合约失败: {e}")
        else:
            logger.warning("未收到任何合约信息")

    # ========== 等待行情数据 ==========
    logger.info("等待行情数据(120秒)...")
    received_ticks = False
    for i in range(120):
        time.sleep(1)
        ticks = main_engine.get_all_ticks()
        
        if ticks:
            received_ticks = True
            logger.info(f"收到 {len(ticks)} 个合约行情")
            for tick in ticks[:3]:  # 只显示前3个
                logger.info(f"  {tick.symbol}: 最新价={tick.last_price}")
            break
        
        # 每10秒输出一次进度
        if i % 10 == 0:
            logger.info(f"等待行情数据... {i+1}/120")
    
    # ========== 结果输出 ==========
    logger.info("\n" + "="*50)
    logger.info("CTP连接测试总结")
    logger.info("="*50)
    
    logger.info(f"交易服务器连接: {'✓ 成功' if td_connected else '✗ 失败'}")
    logger.info(f"交易服务器登录: {'✓ 成功' if td_login_status else '✗ 失败'}")
    logger.info(f"行情服务器连接: {'✓ 成功' if md_connected else '✗ 失败'}")
    logger.info(f"行情服务器登录: {'✓ 成功' if md_login_status else '✗ 失败'}")
    logger.info(f"收到行情数据: {'✓ 是' if received_ticks else '✗ 否'}")
    
    # ========== 清理资源 ==========
    logger.info("\n" + "="*50)
    logger.info("清理资源")
    logger.info("="*50)
    
    try:
        # 断开连接
        ctp_gateway.close()
        time.sleep(1)
        main_engine.close()
        logger.info("✓ 资源清理完成")
    except Exception as e:
        logger.error(f"资源清理时出错: {e}")
    
    logger.info("测试完成")
    
    # 最终建议
    if not received_ticks:
        logger.info("\n" + "="*50)
        logger.info("故障排除建议:")
        logger.info("="*50)
        logger.info("1. 使用SimNow官网验证账户状态")
        logger.info("2. 尝试修改密码为更简单的组合 (如 Test1234!)")
        logger.info("3. 更换服务器地址:")
        logger.info("   - tcp://218.202.237.33:10112 (交易)")
        logger.info("   - tcp://218.202.237.33:10113 (行情)")
        logger.info("4. 检查系统时间是否准确: date")
        logger.info("5. 联系SimNow技术支持: service@simnow.com.cn")

if __name__ == "__main__":
   logger = setup_logging()
   test_ctp_connection(logger)