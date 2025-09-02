#!/usr/bin/env python3
"""
信号生成调试工具
专门调试为什么策略不生成交易信号
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from tests.strategy.test_strategy_offline import MockSignalSender, MockDataGenerator
from core.types import Exchange
from utils.logger import get_logger

logger = get_logger(__name__)


def debug_strategy_signals(strategy_class, strategy_name: str):
    """调试策略信号生成"""
    print(f"\n🔍 调试策略信号生成: {strategy_name}")
    print("=" * 50)
    
    try:
        # 创建策略实例
        signal_sender = MockSignalSender()
        strategy = strategy_class(
            strategy_name=strategy_name,
            symbol="au2510",
            setting={},
            signal_sender=signal_sender
        )
        
        # 启动策略
        strategy.on_init()
        strategy.on_start()
        strategy.trading = True  # 确保交易开启
        
        print(f"✅ 策略已启动，trading={strategy.trading}")
        
        # 创建数据生成器
        data_gen = MockDataGenerator("au2510", 500.0)
        
        # 发送更多样化的数据
        print("\n📊 发送模拟数据...")
        
        # 1. 发送一些bar数据来初始化指标
        print("1️⃣ 发送bar数据初始化指标...")
        for i in range(30):  # 发送30个bar
            bar = data_gen.generate_bar()
            print(f"  Bar {i+1}: 价格={bar.close_price:.2f}")
            strategy.on_bar(bar)
            
            # 检查ArrayManager状态
            if hasattr(strategy, 'am') and strategy.am.inited:
                print(f"    ArrayManager已初始化 (count={strategy.am.count})")
                break
        
        # 2. 检查ArrayManager状态
        if hasattr(strategy, 'am'):
            print(f"📊 ArrayManager状态: inited={strategy.am.inited}, count={strategy.am.count}")
        
        # 3. 发送tick数据，模拟价格大幅波动
        print("\n2️⃣ 发送大幅波动的tick数据...")
        base_price = 500.0
        
        # 模拟价格大幅上涨
        for i in range(10):
            price = base_price + i * 2.0  # 每次上涨2元
            tick = data_gen.generate_tick()
            tick.last_price = price
            
            print(f"  Tick {i+1}: 价格={price:.2f}")
            strategy.on_tick(tick)
            
            # 检查是否生成信号
            signals = signal_sender.get_signals()
            if signals:
                print(f"    🎯 生成信号: {len(signals)} 个")
                for signal in signals[-2:]:  # 显示最新的2个信号
                    print(f"      {signal}")
        
        # 4. 发送更多bar数据
        print("\n3️⃣ 发送更多bar数据...")
        for i in range(20):
            bar = data_gen.generate_bar()
            # 模拟趋势数据
            if i < 10:
                bar.close_price = base_price + i * 1.0  # 上升趋势
            else:
                bar.close_price = base_price + (20-i) * 1.0  # 下降趋势
            
            print(f"  Bar {i+1}: 价格={bar.close_price:.2f}")
            strategy.on_bar(bar)
            
            # 检查信号
            signals = signal_sender.get_signals()
            if len(signals) > 0:
                print(f"    🎯 累计信号: {len(signals)} 个")
        
        # 最终结果
        final_signals = signal_sender.get_signals()
        print(f"\n📊 最终结果:")
        print(f"  总信号数: {len(final_signals)}")
        print(f"  策略状态: trading={strategy.trading}, pos={getattr(strategy, 'pos', 'N/A')}")
        
        if hasattr(strategy, 'am'):
            print(f"  数据状态: inited={strategy.am.inited}, count={strategy.am.count}")
        
        # 分析为什么没有信号
        if len(final_signals) == 0:
            print(f"\n⚠️ 分析：为什么没有信号？")
            
            # 检查常见原因
            reasons = []
            
            if not strategy.trading:
                reasons.append("策略trading=False")
            
            if hasattr(strategy, 'am') and not strategy.am.inited:
                reasons.append("ArrayManager未初始化")
            
            if hasattr(strategy, 'last_signal_time'):
                time_diff = time.time() - strategy.last_signal_time
                if hasattr(strategy, 'signal_interval') and time_diff < strategy.signal_interval:
                    reasons.append(f"信号间隔限制 ({time_diff:.1f}s < {strategy.signal_interval}s)")
                elif hasattr(strategy, 'min_signal_interval') and time_diff < strategy.min_signal_interval:
                    reasons.append(f"最小信号间隔限制 ({time_diff:.1f}s < {strategy.min_signal_interval}s)")
            
            if hasattr(strategy, 'pos') and hasattr(strategy, 'max_position'):
                if abs(strategy.pos) >= strategy.max_position:
                    reasons.append(f"持仓已达上限 ({strategy.pos}/{strategy.max_position})")
            
            if reasons:
                print(f"  可能原因:")
                for reason in reasons:
                    print(f"    - {reason}")
            else:
                print(f"  可能原因: 策略逻辑条件未满足（技术指标条件、市场条件等）")
        
        return {
            "success": True,
            "signals_generated": len(final_signals),
            "signals": final_signals,
            "strategy_state": {
                "trading": strategy.trading,
                "pos": getattr(strategy, 'pos', None),
                "am_inited": getattr(strategy, 'am', {}).inited if hasattr(strategy, 'am') else None
            }
        }
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        return {"success": False, "error": str(e)}


def main():
    """主函数"""
    print("🔍 策略信号生成调试工具")
    print("=" * 60)
    
    # 测试几个主要策略
    strategies_to_debug = [
        ("MaRsiComboStrategy", "services.strategy_service.strategies.MaRsiComboStrategy"),
        ("MultiModeAdaptiveStrategy", "services.strategy_service.strategies.MultiModeAdaptiveStrategy"),
        ("LargeOrderFollowingStrategy", "services.strategy_service.strategies.LargeOrderFollowingStrategy"),
    ]
    
    results = {}
    
    for strategy_name, module_path in strategies_to_debug:
        try:
            # 导入策略
            import importlib
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, strategy_name)
            
            # 调试信号生成
            result = debug_strategy_signals(strategy_class, strategy_name)
            results[strategy_name] = result
            
        except Exception as e:
            print(f"❌ 无法调试策略 {strategy_name}: {e}")
            results[strategy_name] = {"success": False, "error": str(e)}
    
    # 总结
    print(f"\n📊 调试总结")
    print("=" * 60)
    
    for strategy_name, result in results.items():
        if result.get("success"):
            signals = result.get("signals_generated", 0)
            status = "🎯 有信号" if signals > 0 else "⚠️ 无信号"
            print(f"  {status} {strategy_name}: {signals} 个信号")
        else:
            print(f"  ❌ {strategy_name}: {result.get('error', '未知错误')}")
    
    print(f"\n🎉 调试完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
