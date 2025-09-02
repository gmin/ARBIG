#!/usr/bin/env python3
"""
其他策略专门测试脚本
专注测试除SystemIntegrationTestStrategy之外的其他策略
找出它们与成功策略的差异和问题
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from tests.strategy.test_strategy_offline import StrategyTester, load_available_strategies
from utils.logger import get_logger

logger = get_logger(__name__)


def test_individual_strategy(strategy_name: str, strategy_class) -> Dict[str, Any]:
    """测试单个策略"""
    print(f"\n🔍 详细测试策略: {strategy_name}")
    print("=" * 50)
    
    tester = StrategyTester()
    
    # 加载策略
    if not tester.load_strategy(strategy_class, strategy_name):
        return {"success": False, "error": "策略加载失败"}
    
    results = {
        "strategy_name": strategy_name,
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # 1. 初始化测试
    print("1️⃣ 测试策略初始化...")
    init_result = tester.test_strategy_initialization(strategy_name)
    results["tests"]["initialization"] = init_result
    
    if init_result["success"]:
        print("✅ 初始化成功")
        
        # 显示策略参数
        params = init_result.get("parameters", {})
        print("📋 策略参数:")
        for key, value in params.items():
            if not key.startswith('_') and not callable(value):
                print(f"  - {key}: {value}")
    else:
        print(f"❌ 初始化失败: {init_result.get('error')}")
        return results
    
    # 2. 数据处理测试 - 更多数据
    print("\n2️⃣ 测试数据处理能力...")
    data_result = tester.test_strategy_data_processing(strategy_name, 100, 50)  # 更多数据
    results["tests"]["data_processing"] = data_result
    
    if data_result["success"]:
        signals = data_result.get("signals_generated", 0)
        print(f"✅ 数据处理成功，生成 {signals} 个信号")
        
        # 显示信号详情
        if signals > 0:
            signals_data = data_result.get("signals", [])
            print("📊 信号详情:")
            for i, signal in enumerate(signals_data[:3]):  # 只显示前3个
                print(f"  信号 {i+1}: {signal}")
    else:
        print(f"❌ 数据处理失败: {data_result.get('error')}")
    
    # 3. 参数测试
    print("\n3️⃣ 测试参数敏感性...")
    strategy = tester.strategies[strategy_name]['strategy']
    
    # 检查常见参数
    testable_params = {}
    common_params = ['trade_volume', 'max_position', 'ma_short', 'ma_long', 'rsi_period']
    
    for param in common_params:
        if hasattr(strategy, param):
            current_value = getattr(strategy, param)
            if isinstance(current_value, (int, float)):
                if param == 'trade_volume':
                    testable_params[param] = [1, 2]
                elif param == 'max_position':
                    testable_params[param] = [3, 5]
                elif param in ['ma_short', 'ma_long', 'rsi_period']:
                    testable_params[param] = [current_value, current_value + 5]
    
    if testable_params:
        param_result = tester.test_strategy_parameters(strategy_name, testable_params)
        results["tests"]["parameter_sensitivity"] = param_result
        
        if param_result["success"]:
            param_tests = param_result.get("parameter_tests", [])
            print(f"✅ 参数测试完成，测试了 {len(param_tests)} 个参数组合")
        else:
            print(f"❌ 参数测试失败: {param_result.get('error')}")
    else:
        print("⚠️ 未发现可测试参数")
    
    return results


def analyze_strategy_differences(results: Dict[str, Any]) -> Dict[str, Any]:
    """分析策略差异"""
    analysis = {
        "successful_strategies": [],
        "failed_strategies": [],
        "common_issues": [],
        "recommendations": []
    }
    
    for strategy_name, result in results.items():
        if result.get("tests", {}).get("initialization", {}).get("success", False):
            analysis["successful_strategies"].append(strategy_name)
        else:
            analysis["failed_strategies"].append(strategy_name)
    
    # 分析常见问题
    initialization_failures = []
    data_processing_failures = []
    
    for strategy_name, result in results.items():
        tests = result.get("tests", {})
        
        init_test = tests.get("initialization", {})
        if not init_test.get("success", False):
            initialization_failures.append({
                "strategy": strategy_name,
                "error": init_test.get("error", "未知错误")
            })
        
        data_test = tests.get("data_processing", {})
        if not data_test.get("success", False):
            data_processing_failures.append({
                "strategy": strategy_name,
                "error": data_test.get("error", "未知错误")
            })
    
    if initialization_failures:
        analysis["common_issues"].append({
            "type": "初始化失败",
            "count": len(initialization_failures),
            "details": initialization_failures
        })
    
    if data_processing_failures:
        analysis["common_issues"].append({
            "type": "数据处理失败", 
            "count": len(data_processing_failures),
            "details": data_processing_failures
        })
    
    # 生成建议
    if len(analysis["successful_strategies"]) > 0:
        analysis["recommendations"].append(
            f"✅ {len(analysis['successful_strategies'])} 个策略工作正常，可以作为参考"
        )
    
    if len(analysis["failed_strategies"]) > 0:
        analysis["recommendations"].append(
            f"⚠️ {len(analysis['failed_strategies'])} 个策略需要修复"
        )
    
    return analysis


def main():
    """主函数"""
    print("🧪 其他策略专门测试")
    print("=" * 60)
    print("目标：测试除SystemIntegrationTestStrategy外的其他策略")
    print("重点：找出问题和差异，为交易时间测试做准备")
    
    # 加载所有策略
    available_strategies = load_available_strategies()
    
    # 排除参考策略
    reference_strategy = "SystemIntegrationTestStrategy"
    other_strategies = {
        name: cls for name, cls in available_strategies.items() 
        if name != reference_strategy
    }
    
    print(f"\n📋 待测试策略 ({len(other_strategies)} 个):")
    for i, name in enumerate(other_strategies.keys(), 1):
        print(f"  {i}. {name}")
    
    if not other_strategies:
        print("❌ 没有找到其他策略进行测试")
        return
    
    print(f"\n🔍 参考策略: {reference_strategy}")
    print("🎯 开始测试其他策略...")
    
    # 测试每个策略
    all_results = {}
    
    for strategy_name, strategy_class in other_strategies.items():
        try:
            result = test_individual_strategy(strategy_name, strategy_class)
            all_results[strategy_name] = result
        except Exception as e:
            print(f"❌ 策略 {strategy_name} 测试异常: {e}")
            all_results[strategy_name] = {
                "success": False,
                "error": f"测试异常: {str(e)}"
            }
    
    # 分析结果
    print("\n📊 测试结果分析")
    print("=" * 60)
    
    analysis = analyze_strategy_differences(all_results)
    
    # 显示成功策略
    successful = analysis["successful_strategies"]
    failed = analysis["failed_strategies"]
    
    print(f"✅ 成功策略 ({len(successful)} 个):")
    for strategy in successful:
        result = all_results[strategy]
        data_test = result.get("tests", {}).get("data_processing", {})
        signals = data_test.get("signals_generated", 0) if data_test.get("success") else 0
        print(f"  ✓ {strategy}: {signals} 个信号")
    
    print(f"\n❌ 失败策略 ({len(failed)} 个):")
    for strategy in failed:
        result = all_results[strategy]
        error = result.get("error", "未知错误")
        print(f"  ✗ {strategy}: {error}")
    
    # 显示常见问题
    if analysis["common_issues"]:
        print(f"\n⚠️ 常见问题:")
        for issue in analysis["common_issues"]:
            print(f"  🔍 {issue['type']} ({issue['count']} 个策略)")
            for detail in issue["details"][:2]:  # 只显示前2个
                print(f"    - {detail['strategy']}: {detail['error']}")
    
    # 显示建议
    print(f"\n💡 建议:")
    for rec in analysis["recommendations"]:
        print(f"  {rec}")
    
    # 与参考策略对比
    print(f"\n🎯 与 {reference_strategy} 对比:")
    print("  SystemIntegrationTestStrategy 的优势:")
    print("    ✓ 专为测试设计，稳定可靠")
    print("    ✓ 完整的持仓管理和风控机制") 
    print("    ✓ 详细的日志和调试信息")
    print("    ✓ 随机信号生成，适合系统验证")
    
    print("\n  其他策略的特点:")
    for strategy_name in successful:
        print(f"    ✓ {strategy_name}: 基于技术指标，适合实际交易")
    
    # 保存结果
    import json
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f"other_strategies_test_results_{timestamp}.json"
    
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "results": all_results,
                "analysis": analysis,
                "timestamp": timestamp
            }, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 详细结果已保存: {result_file}")
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")
    
    print(f"\n🎉 测试完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 总结
    total = len(other_strategies)
    success_rate = len(successful) / total * 100 if total > 0 else 0
    print(f"\n📈 总结: {len(successful)}/{total} 策略正常 ({success_rate:.1f}%)")


if __name__ == "__main__":
    main()
