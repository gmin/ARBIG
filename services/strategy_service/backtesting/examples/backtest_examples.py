"""
回测使用示例
演示如何使用ARBIG回测系统进行策略测试
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))

from services.strategy_service.backtesting.backtest_manager import BacktestManager, quick_backtest


async def example_1_single_strategy_backtest():
    """示例1: 单个策略回测"""
    print("=" * 60)
    print("示例1: 单个策略回测")
    print("=" * 60)
    
    manager = BacktestManager()
    
    # 检查可用策略
    strategies = manager.get_available_strategies()
    print(f"可用策略: {strategies}")
    
    if not strategies:
        print("❌ 没有可用的策略")
        return
    
    # 选择第一个策略进行回测
    strategy_name = strategies[0]
    print(f"📊 回测策略: {strategy_name}")
    
    # 策略参数
    strategy_setting = {
        "max_position": 10,
        "large_order_threshold": 3.0,
        "jump_threshold": 0.0008
    }
    
    # 回测设置
    backtest_setting = {
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 3, 31),
        "capital": 1000000,
        "rate": 0.0002,
        "slippage": 0.2
    }
    
    try:
        # 运行回测
        result = await manager.run_single_backtest(
            strategy_name=strategy_name,
            strategy_setting=strategy_setting,
            backtest_setting=backtest_setting
        )
        
        if "error" in result:
            print(f"❌ 回测失败: {result['error']}")
            return
        
        # 显示结果
        print("\n📈 回测结果:")
        basic_result = result.get("basic_result", {})
        print(f"  总收益率: {basic_result.get('total_return', 0):.2%}")
        print(f"  年化收益率: {basic_result.get('annual_return', 0):.2%}")
        print(f"  最大回撤: {basic_result.get('max_drawdown', 0):.2%}")
        print(f"  夏普比率: {basic_result.get('sharpe_ratio', 0):.2f}")
        print(f"  胜率: {basic_result.get('win_rate', 0):.2%}")
        
        # 生成详细报告
        print("\n📋 详细报告:")
        report = manager.engine.generate_report(result)
        print(report)
        
    except Exception as e:
        print(f"❌ 回测异常: {e}")


async def example_2_quick_backtest():
    """示例2: 快速回测"""
    print("\n" + "=" * 60)
    print("示例2: 快速回测 (最近30天)")
    print("=" * 60)
    
    manager = BacktestManager()
    strategies = manager.get_available_strategies()
    
    if not strategies:
        print("❌ 没有可用的策略")
        return
    
    strategy_name = strategies[0]
    print(f"⚡ 快速回测策略: {strategy_name}")
    
    try:
        # 快速回测 - 最近30天
        result = await quick_backtest(
            strategy_name=strategy_name,
            strategy_setting={"max_position": 5},
            days=30
        )
        
        if "error" in result:
            print(f"❌ 快速回测失败: {result['error']}")
            return
        
        # 显示关键指标
        basic_result = result.get("basic_result", {})
        print(f"\n📊 30天回测结果:")
        print(f"  总收益率: {basic_result.get('total_return', 0):.2%}")
        print(f"  最大回撤: {basic_result.get('max_drawdown', 0):.2%}")
        print(f"  交易次数: {basic_result.get('total_trade_count', 0)}")
        print(f"  胜率: {basic_result.get('win_rate', 0):.2%}")
        
    except Exception as e:
        print(f"❌ 快速回测异常: {e}")


async def example_3_batch_backtest():
    """示例3: 批量回测对比"""
    print("\n" + "=" * 60)
    print("示例3: 批量回测对比")
    print("=" * 60)
    
    manager = BacktestManager()
    strategies = manager.get_available_strategies()
    
    if len(strategies) < 2:
        print("❌ 需要至少2个策略进行对比")
        return
    
    # 准备批量回测配置
    strategies_config = []
    for i, strategy_name in enumerate(strategies[:3]):  # 最多测试3个策略
        strategies_config.append({
            "strategy_name": strategy_name,
            "strategy_setting": {
                "max_position": 5 + i * 2,  # 不同的仓位设置
            }
        })
    
    print(f"🔄 批量回测 {len(strategies_config)} 个策略")
    
    # 回测设置
    backtest_setting = {
        "start_date": datetime(2024, 2, 1),
        "end_date": datetime(2024, 4, 30),
        "capital": 1000000
    }
    
    try:
        # 运行批量回测
        result = await manager.run_batch_backtest(
            strategies_config=strategies_config,
            backtest_setting=backtest_setting
        )
        
        if "error" in result:
            print(f"❌ 批量回测失败: {result['error']}")
            return
        
        # 显示对比结果
        print("\n📊 策略对比结果:")
        comparison = result.get("comparison", {})
        
        # 显示综合评分
        summary = comparison.get("summary", {})
        if "ranking" in summary:
            print("\n🏆 综合评分排名:")
            for i, (strategy_name, score) in enumerate(summary["ranking"], 1):
                print(f"  {i}. {strategy_name}: {score:.4f}")
        
        # 显示各项指标排名
        rankings = comparison.get("rankings", {})
        for metric, ranking in rankings.items():
            print(f"\n📈 {metric} 排名:")
            for i, (strategy_name, value) in enumerate(ranking[:3], 1):
                if metric == "max_drawdown":
                    print(f"  {i}. {strategy_name}: {value:.2%}")
                elif "rate" in metric or "return" in metric:
                    print(f"  {i}. {strategy_name}: {value:.2%}")
                else:
                    print(f"  {i}. {strategy_name}: {value:.2f}")
        
    except Exception as e:
        print(f"❌ 批量回测异常: {e}")


async def example_4_parameter_optimization():
    """示例4: 参数优化"""
    print("\n" + "=" * 60)
    print("示例4: 参数优化")
    print("=" * 60)
    
    manager = BacktestManager()
    strategies = manager.get_available_strategies()
    
    if not strategies:
        print("❌ 没有可用的策略")
        return
    
    strategy_name = strategies[0]
    print(f"🔧 优化策略参数: {strategy_name}")
    
    # 参数优化配置
    optimization_config = {
        "optimization_setting": {
            # 这里需要根据具体策略的参数来设置
            "max_position": [3, 5, 8, 10],
            # 如果是大单跟踪策略，可以优化这些参数
            # "large_order_threshold": [2.0, 3.0, 4.0],
            # "jump_threshold": [0.0005, 0.0008, 0.001]
        },
        "target_name": "sharpe_ratio"  # 优化目标：夏普比率
    }
    
    try:
        print("⏳ 正在进行参数优化...")
        result = await manager.optimize_strategy_parameters(
            strategy_name=strategy_name,
            optimization_config=optimization_config
        )
        
        if "error" in result:
            print(f"❌ 参数优化失败: {result['error']}")
            return
        
        print("✅ 参数优化完成")
        print(f"📊 优化结果: {result}")
        
    except Exception as e:
        print(f"❌ 参数优化异常: {e}")


async def example_5_save_and_load_results():
    """示例5: 保存和加载结果"""
    print("\n" + "=" * 60)
    print("示例5: 保存和加载回测结果")
    print("=" * 60)
    
    manager = BacktestManager()
    
    # 检查是否有回测结果
    results = manager.get_backtest_results()
    print(f"📁 当前有 {len(results)} 个回测结果")
    
    if results:
        # 保存结果
        filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        manager.save_results(filename)
        print(f"💾 结果已保存到: {filename}")
        
        # 显示结果列表
        print("\n📋 回测结果列表:")
        for key, result in list(results.items())[:5]:  # 只显示前5个
            timestamp = result.get("timestamp", "未知时间")
            strategies = result.get("strategies", {})
            strategy_names = list(strategies.keys())
            print(f"  {key}: {strategy_names} - {timestamp}")
    else:
        print("📭 暂无回测结果")


async def main():
    """主函数 - 运行所有示例"""
    print("🚀 ARBIG回测系统示例")
    print("基于vnpy专业回测引擎")
    
    try:
        # 运行各个示例
        await example_1_single_strategy_backtest()
        await example_2_quick_backtest()
        await example_3_batch_backtest()
        # await example_4_parameter_optimization()  # 参数优化可能需要较长时间
        await example_5_save_and_load_results()
        
        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 示例运行异常: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
