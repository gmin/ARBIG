"""
直接CTP仿真网关测试脚本
不依赖vnpy_ctp包，直接使用CTP仿真库
"""

import time
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.ctp_sim import DirectCtpSimGateway, CtpSimConfig
from vnpy.trader.constant import Direction, Offset, OrderType

def test_direct_ctp_sim_connection():
    """
    测试直接CTP仿真环境连接
    """
    print("=" * 50)
    print("开始测试直接CTP仿真环境连接")
    print("=" * 50)
    
    try:
        # 创建配置对象
        config = CtpSimConfig()
        print("✓ CTP仿真配置加载成功")
        
        # 验证配置
        config.validate_config()
        print("✓ CTP仿真配置验证通过")
        
        # 显示服务器信息
        server_info = config.get_server_info()
        print(f"交易服务器: {server_info['trading_host']}:{server_info['trading_port']}")
        print(f"行情服务器: {server_info['market_host']}:{server_info['market_port']}")
        
        # 创建直接网关
        gateway = DirectCtpSimGateway(config)
        print("✓ 直接CTP仿真网关创建成功")
        
        # 连接仿真环境
        print("\n正在连接CTP仿真环境...")
        if gateway.connect():
            print("✓ CTP仿真环境连接成功")
            
            # 测试订阅合约
            symbols = ["AU0"]
            print(f"\n正在订阅合约: {symbols}")
            if gateway.subscribe(symbols):
                print("✓ 合约订阅成功")
                
                # 等待行情数据
                print("\n等待行情数据...")
                for i in range(5):
                    time.sleep(1)
                    tick = gateway.get_tick("AU0")
                    if tick:
                        print(f"✓ 收到行情数据: {tick.symbol} 最新价: {tick.last_price}")
                        print(f"  买卖价: {tick.bid_price_1} / {tick.ask_price_1}")
                        print(f"  成交量: {tick.volume}, 持仓量: {tick.open_interest}")
                        print(f"  最高价: {tick.high_price}, 最低价: {tick.low_price}")
                        print(f"  开盘价: {tick.open_price}, 昨收价: {tick.pre_close}")
                        print(f"  时间: {tick.datetime}")
                        break
                    print(f"等待中... ({i+1}/5)")
                else:
                    print("⚠ 未收到行情数据")
                    
            else:
                print("✗ 合约订阅失败")
                
            # 测试获取持仓
            print("\n获取持仓信息...")
            positions = gateway.get_all_positions()
            if positions:
                print(f"✓ 当前持仓数量: {len(positions)}")
                for key, pos in positions.items():
                    print(f"  {key}: {pos.volume}手")
            else:
                print("✓ 当前无持仓")
                
            # 断开连接
            print("\n断开CTP仿真环境连接...")
            gateway.disconnect()
            print("✓ CTP仿真环境已断开")
            
        else:
            print("✗ CTP仿真环境连接失败")
            
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def test_direct_ctp_sim_trading():
    """
    测试直接CTP仿真环境交易功能
    """
    print("\n" + "=" * 50)
    print("开始测试直接CTP仿真环境交易功能")
    print("=" * 50)
    
    try:
        # 创建网关
        gateway = DirectCtpSimGateway()
        
        # 连接仿真环境
        if not gateway.connect():
            print("✗ 无法连接CTP仿真环境，跳过交易测试")
            return
            
        # 订阅合约
        symbols = ["AU2406"]
        if not gateway.subscribe(symbols):
            print("✗ 无法订阅合约，跳过交易测试")
            return
            
        # 等待行情数据
        print("等待行情数据...")
        for i in range(3):
            time.sleep(1)
            tick = gateway.get_tick("AU2406")
            if tick:
                print(f"✓ 收到行情数据: {tick.symbol} 最新价: {tick.last_price}")
                break
        else:
            print("✗ 未收到行情数据，跳过交易测试")
            return
            
        # 测试发送订单（限价单）
        print("\n测试发送限价单...")
        tick = gateway.get_tick("AU2406")
        if tick:
            # 以当前价格+1元发送限价买单
            price = tick.last_price + 1.0
            order_id = gateway.send_order(
                symbol="AU2406",
                direction=Direction.LONG,
                offset=Offset.OPEN,
                volume=1,
                price=price,
                order_type=OrderType.LIMIT
            )
            
            if order_id:
                print(f"✓ 限价单发送成功，订单ID: {order_id}")
                
                # 等待订单状态更新
                time.sleep(1)
                
                # 撤销订单
                print("撤销测试订单...")
                if gateway.cancel_order(order_id):
                    print("✓ 订单撤销成功")
                else:
                    print("✗ 订单撤销失败")
            else:
                print("✗ 限价单发送失败")
                
        # 测试发送市价单
        print("\n测试发送市价单...")
        order_id = gateway.send_order(
            symbol="AU2406",
            direction=Direction.SHORT,
            offset=Offset.OPEN,
            volume=1,
            price=0.0,  # 市价单价格为0
            order_type=OrderType.MARKET
        )
        
        if order_id:
            print(f"✓ 市价单发送成功，订单ID: {order_id}")
        else:
            print("✗ 市价单发送失败")
            
        # 断开连接
        gateway.disconnect()
        print("✓ 交易测试完成")
        
    except Exception as e:
        print(f"✗ 交易测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """
    主函数
    """
    print("直接CTP仿真环境测试程序")
    print("不依赖vnpy_ctp包，直接使用CTP仿真库")
    print()
    
    # 运行连接测试
    test_direct_ctp_sim_connection()
    
    # 询问是否进行交易测试
    print("\n是否进行交易功能测试？(y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice in ['y', 'yes', '是']:
            test_direct_ctp_sim_trading()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except:
        print("\n跳过交易测试")

if __name__ == "__main__":
    main() 