# ctp_connection_test.py
import time
import logging
import socket
import os
from datetime import datetime
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway
from vnpy.trader.object import SubscribeRequest
from vnpy.trader.constant import Exchange
from vnpy.trader.event import EVENT_CONTRACT, EVENT_TICK, EVENT_LOG

def setup_logging():
    """配置日志记录"""
    logger = logging.getLogger("ctp_test")
    logger.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # 创建文件处理器
    fh = logging.FileHandler("ctp_test.log")
    fh.setLevel(logging.DEBUG)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(ch)
    logger.addHandler(fh)
    
    return logger

def check_network_connection(host, port, timeout=5):
    """检查网络连接"""
    try:
        start = datetime.now()
        with socket.create_connection((host, port), timeout=timeout):
            latency = (datetime.now() - start).total_seconds() * 1000
            return True, f"连接成功! 延迟: {latency:.2f}ms"
    except Exception as e:
        return False, f"连接失败: {str(e)}"

def test_ctp_connection(logger):
    """测试CTP连接"""
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加CTP网关
    main_engine.add_gateway(CtpGateway, "CTP")
    ctp_gateway = main_engine.get_gateway("CTP")
    
    # 配置信息 - 使用SimNow 7x24测试环境
    setting = {
        "用户名": "242407",
        "密码": "Crh1234567!",
        "经纪商代码": "9999",
        "交易服务器": "tcp://182.254.243.31:30001",  # 7x24测试环境：#182.254.243.31：40011
        "行情服务器": "tcp://182.254.243.31:30011",  # 7x24测试环境：#182.254.243.31：40001
        "产品名称": "simnow_client_test",
        "授权编码": "0000000000000000"
    }
    
    
    #setting = {
    #    "用户名": "000002",
    #    "密码": "fnqh123456",
    #    "经纪商代码": "8888",
    #    "交易服务器": "tcp://117.25.161.29:61205",
    #    "行情服务器": "tcp://117.25.161.29:61213",
    #    "产品名称": "client_ARBIG_1.0.0",
    #    "授权编码": "8NTZL54IEGNEB6CP"
    #}
    
    # ========== 网络连接测试 ==========
    logger.info("="*50)
    logger.info("网络连接测试")
    logger.info("="*50)
    
    servers = [
        ("交易服务器", "117.25.161.29", 61205),
        ("行情服务器", "117.25.161.29", 61213)
    ]
    
    for name, host, port in servers:
        success, msg = check_network_connection(host, port)
        status = "✓" if success else "✗"
        logger.info(f"{status} {name} {host}:{port} - {msg}")
    
    # ========== 账户信息验证 ==========
    logger.info("\n" + "="*50)
    logger.info("账户信息验证")
    logger.info("="*50)
    logger.info(f"经纪商代码: {setting['经纪商代码']}")
    logger.info(f"用户名: {setting['用户名']}")
    logger.info(f"密码: {'*' * len(setting['密码'])}")
    logger.info(f"产品名称: {setting['产品名称']}")
    logger.info(f"授权编码: {setting['授权编码']}")
    
    # 注册事件处理函数
    def handle_event(event):
        if event.type == EVENT_LOG:
            logger.info(f"[日志] {event.data}")
        elif event.type == EVENT_CONTRACT:
            contract = event.data
            if contract.symbol.startswith("au"):
                logger.info(f"发现黄金合约: {contract.symbol} - {contract.name}")
        elif event.type == EVENT_TICK:
            tick = event.data
            logger.info(f"行情更新: {tick.symbol} 最新价={tick.last_price} 量={tick.volume}")
    
    event_engine.register(EVENT_LOG, handle_event)
    event_engine.register(EVENT_CONTRACT, handle_event)
    event_engine.register(EVENT_TICK, handle_event)
    
    # ========== 连接CTP ==========
    logger.info("\n" + "="*50)
    logger.info("开始连接CTP服务器...")
    logger.info("="*50)
    ctp_gateway.connect(setting)
    
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
    # 查询合约列表
    if td_connected and td_login_status:
        logger.info("查询合约列表...")
        main_engine.query_contract()
        time.sleep(5)  # 延长等待时间
    
    # 订阅黄金合约
    if md_connected and md_login_status:
        logger.info("尝试订阅黄金合约...")
        
        # 使用有效的黄金合约
        gold_symbols = [
            "au2508", "au2512",  # 2025年8月和12月合约
            "au2612"             # 2026年12月合约
        ]
        
        for symbol in gold_symbols:
            try:
                req = SubscribeRequest(
                    symbol=symbol,
                    exchange=Exchange.SHFE
                )
                ctp_gateway.subscribe(req)
                logger.info(f"已订阅: {symbol}")
            except Exception as e:
                logger.error(f"订阅{symbol}失败: {e}")
    
    # 备用订阅方案：使用主引擎订阅
    logger.info("使用主引擎订阅合约...")
    for symbol in gold_symbols:
        vt_symbol = f"{symbol}.SHFE"
        main_engine.subscribe(vt_symbol, "CTP")
        logger.info(f"主引擎订阅: {vt_symbol}")
    
    # ========== 等待行情数据 ==========
    logger.info("等待行情数据(120秒)...")
    received_ticks = False
    for i in range(120):
        time.sleep(1)
        ticks = main_engine.get_all_ticks()
        
        if ticks:
            received_ticks = True
            logger.info(f"收到 {len(ticks)} 个合约行情")
            for symbol, tick in list(ticks.items())[:3]:  # 只显示前3个
                logger.info(f"  {symbol}: 最新价={tick.last_price}")
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
    
    # 断开连接
    ctp_gateway.close()
    time.sleep(1)
    main_engine.close()
    
    logger.info("测试完成，结果已保存到 ctp_test.log")
    
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