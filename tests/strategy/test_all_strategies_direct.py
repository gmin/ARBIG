#!/usr/bin/env python3
"""
直接测试所有策略
绕过导入问题，直接测试每个策略文件
"""

import sys
import os
import importlib
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from tests.strategy.test_strategy_offline import StrategyTester
from utils.logger import get_logger

logger = get_logger(__name__)


def discover_strategies():
    """发现所有策略文件"""
    strategy_dir = "services/strategy_service/strategies"
    strategies = {}
    
    # 获取所有.py文件
    strategy_files = []
    for file in os.listdir(strategy_dir):
        if file.endswith('.py') and file != '__init__.py' and not file.startswith('.'):
            strategy_files.append(file)
    
    print(f"📁 发现策略文件 ({len(strategy_files)} 个):")
    for file in strategy_files:
        print(f"  - {file}")
    
    # 尝试加载每个策略
    for file in strategy_files:
        module_name = file[:-3]  # 移除.py后缀
        print(f"\n🔍 尝试加载: {module_name}")
        
        try:
            # 动态导入模块
            module = importlib.import_module(f'services.strategy_service.strategies.{module_name}')
            
            # 查找策略类（通常以Strategy结尾）
            strategy_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.endswith('Strategy') and 
                    attr_name != 'ARBIGCtaTemplate' and
                    hasattr(attr, '__init__')):
                    strategy_classes.append(attr)
            
            if strategy_classes:
                for strategy_class in strategy_classes:
                    strategies[strategy_class.__name__] = strategy_class
                    print(f"  ✅ 找到策略类: {strategy_class.__name__}")
            else:
                print(f"  ⚠️ 未找到策略类")
                
        except Exception as e:
            print(f"  ❌ 导入失败: {e}")
    
    return strategies


def test_strategy_quick(strategy_name: str, strategy_class) -> Dict[str, Any]:
    """快速测试单个策略"""
    print(f"\n🧪 测试策略: {strategy_name}")
    print("-" * 40)
    
    result = {
        "strategy_name": strategy_name,
        "tests": {},
        "issues": [],
        "summary": "unknown"
    }
    
    try:
        # 1. 尝试实例化
        print("1️⃣ 测试实例化...")
        try:
            # 使用最小参数创建实例
            instance = strategy_class(
                strategy_name="test",
                symbol="au2510", 
                setting={},
                signal_sender=None
            )
            result["tests"]["instantiation"] = True
            print("  ✅ 实例化成功")
            
            # 检查关键属性
            key_attrs = ['trading', 'pos', 'symbol', 'strategy_name']
            missing_attrs = []
            for attr in key_attrs:
                if not hasattr(instance, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                result["issues"].append(f"缺少关键属性: {missing_attrs}")
                print(f"  ⚠️ 缺少属性: {missing_attrs}")
            
        except Exception as e:
            result["tests"]["instantiation"] = False
            result["issues"].append(f"实例化失败: {str(e)}")
            print(f"  ❌ 实例化失败: {e}")
            return result
        
        # 2. 测试方法存在性
        print("2️⃣ 测试必要方法...")
        required_methods = ['on_init', 'on_start', 'on_stop', 'on_tick', 'on_bar']
        missing_methods = []
        
        for method in required_methods:
            if not hasattr(instance, method) or not callable(getattr(instance, method)):
                missing_methods.append(method)
        
        if missing_methods:
            result["issues"].append(f"缺少方法: {missing_methods}")
            print(f"  ⚠️ 缺少方法: {missing_methods}")
        else:
            result["tests"]["methods"] = True
            print("  ✅ 必要方法完整")
        
        # 3. 测试初始化调用
        print("3️⃣ 测试方法调用...")
        try:
            instance.on_init()
            instance.on_start()
            result["tests"]["method_calls"] = True
            print("  ✅ 方法调用成功")
        except Exception as e:
            result["issues"].append(f"方法调用失败: {str(e)}")
            print(f"  ❌ 方法调用失败: {e}")
        
        # 4. 检查策略类型
        print("4️⃣ 分析策略特征...")
        strategy_features = []
        
        # 检查参数
        if hasattr(instance, 'ma_short') or hasattr(instance, 'ma_long'):
            strategy_features.append("双均线")
        if hasattr(instance, 'rsi_period'):
            strategy_features.append("RSI")
        if hasattr(instance, 'signal_interval'):
            strategy_features.append("定时信号")
        if hasattr(instance, 'stop_loss_pct'):
            strategy_features.append("止损")
        if hasattr(instance, 'max_position'):
            strategy_features.append("持仓限制")
        
        result["features"] = strategy_features
        print(f"  📊 策略特征: {', '.join(strategy_features) if strategy_features else '无明显特征'}")
        
        # 综合评价
        issue_count = len(result["issues"])
        if issue_count == 0:
            result["summary"] = "excellent"
            print("  🟢 综合评价: 优秀")
        elif issue_count <= 2:
            result["summary"] = "good"
            print("  🟡 综合评价: 良好")
        else:
            result["summary"] = "needs_work"
            print("  🔴 综合评价: 需要改进")
            
    except Exception as e:
        result["issues"].append(f"测试异常: {str(e)}")
        result["summary"] = "failed"
        print(f"  ❌ 测试异常: {e}")
    
    return result


def compare_with_reference(results: Dict[str, Any]) -> Dict[str, Any]:
    """与参考策略对比"""
    reference = "SystemIntegrationTestStrategy"
    
    comparison = {
        "reference_strategy": reference,
        "other_strategies": [],
        "issues_summary": {},
        "recommendations": []
    }
    
    # 分析其他策略
    for strategy_name, result in results.items():
        if strategy_name == reference:
            continue
            
        strategy_analysis = {
            "name": strategy_name,
            "summary": result.get("summary", "unknown"),
            "features": result.get("features", []),
            "issues": result.get("issues", []),
            "issue_count": len(result.get("issues", []))
        }
        
        comparison["other_strategies"].append(strategy_analysis)
    
    # 统计问题类型
    issue_types = {}
    for strategy_name, result in results.items():
        if strategy_name == reference:
            continue
        for issue in result.get("issues", []):
            issue_type = issue.split(':')[0] if ':' in issue else issue.split('失败')[0] + "问题"
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
    
    comparison["issues_summary"] = issue_types
    
    # 生成建议
    total_strategies = len([s for s in results.keys() if s != reference])
    excellent_count = len([s for s in comparison["other_strategies"] if s["summary"] == "excellent"])
    
    if excellent_count == total_strategies:
        comparison["recommendations"].append("🎉 所有策略都工作正常！")
    elif excellent_count > total_strategies / 2:
        comparison["recommendations"].append(f"✅ 大部分策略({excellent_count}/{total_strategies})工作正常")
    else:
        comparison["recommendations"].append(f"⚠️ 多数策略需要修复({total_strategies - excellent_count}/{total_strategies})")
    
    if issue_types:
        most_common = max(issue_types.items(), key=lambda x: x[1])
        comparison["recommendations"].append(f"🔧 最常见问题: {most_common[0]} ({most_common[1]}个策略)")
    
    return comparison


def main():
    """主函数"""
    print("🔍 策略全面测试 - 直接加载模式")
    print("=" * 60)
    print("目标: 绕过导入问题，直接测试每个策略文件")
    
    # 发现所有策略
    strategies = discover_strategies()
    
    if not strategies:
        print("❌ 未发现任何策略")
        return
    
    print(f"\n📊 策略总览 ({len(strategies)} 个):")
    for name in strategies.keys():
        print(f"  • {name}")
    
    # 识别参考策略
    reference_strategy = "SystemIntegrationTestStrategy"
    has_reference = reference_strategy in strategies
    
    print(f"\n🎯 参考策略: {reference_strategy} {'✅' if has_reference else '❌ 未找到'}")
    
    # 测试所有策略
    print(f"\n🧪 开始测试所有策略...")
    print("=" * 60)
    
    all_results = {}
    
    for strategy_name, strategy_class in strategies.items():
        result = test_strategy_quick(strategy_name, strategy_class)
        all_results[strategy_name] = result
    
    # 生成对比分析
    print(f"\n📊 对比分析")
    print("=" * 60)
    
    comparison = compare_with_reference(all_results)
    
    # 显示结果统计
    summary_stats = {}
    for result in all_results.values():
        summary = result.get("summary", "unknown")
        summary_stats[summary] = summary_stats.get(summary, 0) + 1
    
    print("📈 策略质量分布:")
    for status, count in summary_stats.items():
        icon = {"excellent": "🟢", "good": "🟡", "needs_work": "🟠", "failed": "🔴"}.get(status, "⚪")
        print(f"  {icon} {status}: {count} 个策略")
    
    # 显示问题统计
    if comparison["issues_summary"]:
        print(f"\n⚠️ 常见问题:")
        for issue_type, count in sorted(comparison["issues_summary"].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {issue_type}: {count} 个策略")
    
    # 显示建议
    print(f"\n💡 建议:")
    for rec in comparison["recommendations"]:
        print(f"  {rec}")
    
    # 详细策略分析
    print(f"\n📋 详细分析:")
    for strategy in comparison["other_strategies"]:
        icon = {"excellent": "🟢", "good": "🟡", "needs_work": "🟠", "failed": "🔴"}.get(strategy["summary"], "⚪")
        print(f"  {icon} {strategy['name']}")
        if strategy["features"]:
            print(f"    特征: {', '.join(strategy['features'])}")
        if strategy["issues"]:
            print(f"    问题: {strategy['issues'][0]}")  # 只显示第一个问题
    
    # 与参考策略对比
    if has_reference:
        ref_result = all_results[reference_strategy]
        print(f"\n🎯 与 {reference_strategy} 对比:")
        print(f"  参考策略状态: {ref_result.get('summary', 'unknown')}")
        print(f"  参考策略特征: {', '.join(ref_result.get('features', []))}")
        
        better_strategies = [s for s in comparison["other_strategies"] if s["summary"] == "excellent"]
        if better_strategies:
            print(f"  同等质量策略: {len(better_strategies)} 个")
            for s in better_strategies[:3]:  # 只显示前3个
                print(f"    ✓ {s['name']}")
    
    # 保存结果
    import json
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f"all_strategies_direct_test_{timestamp}.json"
    
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "discovered_strategies": list(strategies.keys()),
                "test_results": all_results,
                "comparison": comparison,
                "timestamp": timestamp
            }, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 详细结果已保存: {result_file}")
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")
    
    print(f"\n🎉 测试完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 最终总结
    total = len(strategies)
    excellent = summary_stats.get("excellent", 0)
    good = summary_stats.get("good", 0)
    success_rate = (excellent + good) / total * 100 if total > 0 else 0
    
    print(f"\n📈 最终总结:")
    print(f"  发现策略: {total} 个")
    print(f"  优秀策略: {excellent} 个")
    print(f"  良好策略: {good} 个")
    print(f"  成功率: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
