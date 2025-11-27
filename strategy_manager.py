#!/usr/bin/env python3
"""
ARBIG策略管理脚本
提供便捷的策略注册、启动、停止功能
"""

import requests
import json
import sys
import time
from typing import Dict, Any

# 策略服务配置
STRATEGY_SERVICE_URL = "http://localhost:8002"

# 策略配置表
STRATEGIES = {
    1: {
        "name": "TestSystem",
        "type": "SystemIntegrationTestStrategy",
        "symbol": "au2602",
        "display_name": "系统集成测试策略",
        "description": "随机信号生成，用于系统功能验证",
        "params": {
            "signal_interval": 10,
            "trade_volume": 1,
            "max_position": 2
        }
    },
    2: {
        "name": "GoldMaRsi",
        "type": "MaRsiComboStrategy",
        "symbol": "au2602",
        "display_name": "MA-RSI组合策略",
        "description": "基于双均线交叉和RSI指标的技术分析策略",
        "params": {
            "ma_short": 5,
            "ma_long": 20,
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.03,
            "max_position": 3,
            "trade_volume": 1
        }
    },
    3: {
        "name": "GoldMaCross",
        "type": "MaCrossoverTrendStrategy",
        "symbol": "au2602",
        "display_name": "均线交叉趋势策略",
        "description": "基于移动平均线交叉的趋势跟踪策略",
        "params": {
            "ma_short": 10,
            "ma_long": 30,
            "trade_volume": 1,
            "max_position": 2
        }
    },
    4: {
        "name": "GoldVWAP",
        "type": "VWAPDeviationReversionStrategy",
        "symbol": "au2602",
        "display_name": "VWAP偏离回归策略",
        "description": "基于VWAP偏离度的均值回归策略",
        "params": {
            "vwap_period": 20,
            "deviation_threshold": 0.5,
            "trade_volume": 1,
            "max_position": 2
        }
    },
    5: {
        "name": "GoldLargeOrder",
        "type": "LargeOrderFollowingStrategy",
        "symbol": "au2602",
        "display_name": "大单跟踪策略",
        "description": "跟踪大额订单流向的策略",
        "params": {
            "large_order_threshold": 10,
            "follow_ratio": 0.3,
            "trade_volume": 1,
            "max_position": 2
        }
    },
    6: {
        "name": "GoldComponent",
        "type": "ComponentFrameworkStrategy",
        "symbol": "au2602",
        "display_name": "组件框架策略",
        "description": "基于组件化框架的综合策略",
        "params": {
            "trade_volume": 1,
            "max_position": 3
        }
    },
    7: {
        "name": "GoldMultiMode",
        "type": "MultiModeAdaptiveStrategy",
        "symbol": "au2602",
        "display_name": "多模式自适应策略",
        "description": "根据市场条件自适应切换的多模式策略",
        "params": {
            "trade_volume": 1,
            "max_position": 3,
            "mode_switch_threshold": 0.6
        }
    }
}

def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("🚀 ARBIG量化交易系统 - 策略管理器")
    print("=" * 60)

def print_strategies():
    """显示所有可用策略"""
    print("\n📊 可用策略列表:")
    print("-" * 60)
    for num, config in STRATEGIES.items():
        status = get_strategy_status(config["name"])
        status_icon = "🟢" if status == "running" else "⚪"
        print(f"{status_icon} {num}. {config['display_name']} ({config['name']})")
        print(f"   类型: {config['type']}")
        print(f"   描述: {config['description']}")
        print(f"   状态: {status}")
        print()

def get_strategy_status(strategy_name: str) -> str:
    """获取策略状态"""
    try:
        response = requests.get(f"{STRATEGY_SERVICE_URL}/strategies", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and strategy_name in data.get("data", {}):
                return data["data"][strategy_name].get("status", "unknown")
        return "not_registered"
    except:
        return "service_error"

def register_strategy(strategy_num: int) -> bool:
    """注册策略"""
    if strategy_num not in STRATEGIES:
        print(f"❌ 无效的策略编号: {strategy_num}")
        return False
    
    config = STRATEGIES[strategy_num]
    payload = {
        "strategy_name": config["name"],
        "strategy_type": config["type"], 
        "symbol": config["symbol"],
        "params": config["params"]
    }
    
    try:
        print(f"📝 正在注册策略: {config['display_name']}")
        response = requests.post(
            f"{STRATEGY_SERVICE_URL}/strategies/register",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 策略注册成功: {config['name']}")
                return True
            else:
                print(f"❌ 策略注册失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 注册异常: {e}")
    
    return False

def start_strategy(strategy_num: int) -> bool:
    """启动策略"""
    if strategy_num not in STRATEGIES:
        print(f"❌ 无效的策略编号: {strategy_num}")
        return False
    
    config = STRATEGIES[strategy_num]
    strategy_name = config["name"]
    
    try:
        print(f"🚀 正在启动策略: {config['display_name']}")
        response = requests.post(
            f"{STRATEGY_SERVICE_URL}/strategies/{strategy_name}/start",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 策略启动成功: {strategy_name}")
                return True
            else:
                print(f"❌ 策略启动失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 启动异常: {e}")
    
    return False

def stop_strategy(strategy_num: int) -> bool:
    """停止策略"""
    if strategy_num not in STRATEGIES:
        print(f"❌ 无效的策略编号: {strategy_num}")
        return False
    
    config = STRATEGIES[strategy_num]
    strategy_name = config["name"]
    
    try:
        print(f"⏹️ 正在停止策略: {config['display_name']}")
        response = requests.post(
            f"{STRATEGY_SERVICE_URL}/strategies/{strategy_name}/stop",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 策略停止成功: {strategy_name}")
                return True
            else:
                print(f"❌ 策略停止失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 停止异常: {e}")
    
    return False

def register_and_start(strategy_num: int) -> bool:
    """注册并启动策略"""
    if register_strategy(strategy_num):
        time.sleep(1)  # 等待注册完成
        return start_strategy(strategy_num)
    return False

def show_menu():
    """显示主菜单"""
    print("\n🎯 操作菜单:")
    print("1. 显示策略列表")
    print("2. 注册策略")
    print("3. 启动策略") 
    print("4. 停止策略")
    print("5. 注册并启动策略")
    print("6. 查看策略状态")
    print("0. 退出")
    print("-" * 30)

def main():
    """主函数"""
    print_banner()
    
    while True:
        show_menu()
        try:
            choice = input("请选择操作 (0-6): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                print_strategies()
            elif choice in ["2", "3", "4", "5"]:
                print_strategies()
                strategy_num = int(input("请输入策略编号 (1-7): "))
                
                if choice == "2":
                    register_strategy(strategy_num)
                elif choice == "3":
                    start_strategy(strategy_num)
                elif choice == "4":
                    stop_strategy(strategy_num)
                elif choice == "5":
                    register_and_start(strategy_num)
            elif choice == "6":
                print_strategies()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n👋 用户中断，退出程序")
            break
        except ValueError:
            print("❌ 请输入有效的数字")
        except Exception as e:
            print(f"❌ 操作异常: {e}")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    main()
