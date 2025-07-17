#!/usr/bin/env python3
"""
测试回测结果一致性
验证相同参数的回测是否产生相同结果
"""

import sys
import os
sys.path.append('/root/ARBIG')

from core.backtest import SimpleBacktester

def test_backtest_consistency():
    """测试回测结果一致性"""
    
    # 测试参数
    strategy_params = {
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss': 0.05,
        'take_profit': 0.08,
        'position_size': 1,
        'max_position': 5,
        'risk_factor': 0.02,
        'position_mode': 'fixed',
        'position_multiplier': 1.0
    }
    
    start_date = "2024-01-01"
    end_date = "2024-03-31"
    initial_capital = 100000
    
    print("🧪 测试回测结果一致性...")
    print(f"参数: {strategy_params}")
    print(f"日期范围: {start_date} 到 {end_date}")
    print(f"初始资金: {initial_capital}")
    print("-" * 60)
    
    # 运行多次回测
    results = []
    for i in range(5):
        backtester = SimpleBacktester(initial_capital)
        result = backtester.run_backtest(strategy_params, start_date, end_date)
        results.append(result)
        
        print(f"第{i+1}次回测:")
        print(f"  总收益率: {result['total_return']:.4f}")
        print(f"  年化收益率: {result['annual_return']:.4f}")
        print(f"  最大回撤: {result['max_drawdown']:.4f}")
        print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
        print(f"  胜率: {result['win_rate']:.2f}")
        print(f"  交易次数: {result['total_trades']}")
        print()
    
    # 检查一致性
    print("🔍 一致性检查:")
    first_result = results[0]
    all_consistent = True
    
    for key in ['total_return', 'annual_return', 'max_drawdown', 'sharpe_ratio', 'win_rate', 'total_trades']:
        values = [r[key] for r in results]
        if len(set(values)) > 1:
            print(f"❌ {key}: 结果不一致 {values}")
            all_consistent = False
        else:
            print(f"✅ {key}: 结果一致 {values[0]}")
    
    if all_consistent:
        print("\n🎉 所有回测结果完全一致！")
    else:
        print("\n⚠️ 回测结果存在不一致！")
    
    return all_consistent

def test_different_position_modes():
    """测试不同开仓模式的回测结果"""
    
    base_params = {
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss': 0.05,
        'take_profit': 0.08,
        'position_size': 1,
        'max_position': 5,
        'risk_factor': 0.02,
        'position_multiplier': 1.0
    }
    
    modes = ['fixed', 'risk_based', 'kelly', 'martingale']
    start_date = "2024-01-01"
    end_date = "2024-03-31"
    initial_capital = 100000
    
    print("\n🔬 测试不同开仓模式...")
    print("-" * 60)
    
    for mode in modes:
        params = base_params.copy()
        params['position_mode'] = mode
        
        backtester = SimpleBacktester(initial_capital)
        result = backtester.run_backtest(params, start_date, end_date)
        
        print(f"📊 {mode.upper()} 模式:")
        print(f"  总收益率: {result['total_return']:.4f}")
        print(f"  年化收益率: {result['annual_return']:.4f}")
        print(f"  最大回撤: {result['max_drawdown']:.4f}")
        print(f"  夏普比率: {result['sharpe_ratio']:.2f}")
        print(f"  胜率: {result['win_rate']:.2f}")
        print(f"  交易次数: {result['total_trades']}")
        print()

def test_parameter_sensitivity():
    """测试参数敏感性"""
    
    base_params = {
        'ma_short': 5,
        'ma_long': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'stop_loss': 0.05,
        'take_profit': 0.08,
        'position_size': 1,
        'max_position': 5,
        'risk_factor': 0.02,
        'position_mode': 'fixed',
        'position_multiplier': 1.0
    }
    
    start_date = "2024-01-01"
    end_date = "2024-03-31"
    initial_capital = 100000
    
    print("\n🎛️ 测试参数敏感性...")
    print("-" * 60)
    
    # 测试不同的MA参数
    ma_configs = [
        (3, 15),
        (5, 20),
        (10, 30)
    ]
    
    for ma_short, ma_long in ma_configs:
        params = base_params.copy()
        params['ma_short'] = ma_short
        params['ma_long'] = ma_long
        
        backtester = SimpleBacktester(initial_capital)
        result = backtester.run_backtest(params, start_date, end_date)
        
        print(f"📈 MA({ma_short},{ma_long}):")
        print(f"  总收益率: {result['total_return']:.4f}")
        print(f"  交易次数: {result['total_trades']}")
        print()

if __name__ == "__main__":
    print("🚀 开始回测一致性测试...")
    
    # 测试一致性
    consistent = test_backtest_consistency()
    
    # 测试不同开仓模式
    test_different_position_modes()
    
    # 测试参数敏感性
    test_parameter_sensitivity()
    
    print("✅ 测试完成！")
    
    if consistent:
        print("🎯 回测系统工作正常，结果一致可靠。")
    else:
        print("⚠️ 回测系统存在一致性问题，需要进一步检查。")
