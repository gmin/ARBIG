#!/usr/bin/env python3
"""
策略对比测试脚本
专门用于对比SystemIntegrationTestStrategy与其他策略的行为差异
帮助识别其他策略可能存在的问题
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List
import json

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from tests.strategy.test_strategy_offline import StrategyTester, MockDataGenerator, load_available_strategies
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyComparator:
    """策略对比器"""
    
    def __init__(self):
        self.tester = StrategyTester()
        self.reference_strategy = "SystemIntegrationTestStrategy"  # 参考策略
        
    def compare_strategies(self, strategies_to_compare: List[str]) -> Dict[str, Any]:
        """对比多个策略的行为"""
        results = {}
        
        # 加载所有策略
        available_strategies = load_available_strategies()
        
        # 确保参考策略存在
        if self.reference_strategy not in available_strategies:
            return {"error": f"参考策略 {self.reference_strategy} 不存在"}
        
        # 加载参考策略
        ref_class = available_strategies[self.reference_strategy]
        self.tester.load_strategy(ref_class, self.reference_strategy)
        
        print(f"📊 参考策略: {self.reference_strategy}")
        print("-" * 50)
        
        # 测试参考策略
        ref_results = self._test_strategy_behavior(self.reference_strategy)
        results[self.reference_strategy] = ref_results
        
        # 对比其他策略
        for strategy_name in strategies_to_compare:
            if strategy_name == self.reference_strategy:
                continue
                
            if strategy_name not in available_strategies:
                print(f"⚠️ 策略 {strategy_name} 不存在，跳过")
                continue
                
            print(f"\n📊 对比策略: {strategy_name}")
            print("-" * 50)
            
            # 加载并测试策略
            strategy_class = available_strategies[strategy_name]
            if self.tester.load_strategy(strategy_class, strategy_name):
                test_results = self._test_strategy_behavior(strategy_name)
                results[strategy_name] = test_results
                
                # 立即对比
                comparison = self._compare_with_reference(ref_results, test_results)
                results[f"{strategy_name}_vs_reference"] = comparison
                
                self._print_comparison_summary(strategy_name, comparison)
            else:
                print(f"❌ 策略 {strategy_name} 加载失败")
        
        return results
    
    def _test_strategy_behavior(self, strategy_name: str) -> Dict[str, Any]:
        """测试策略行为"""
        results = {}
        
        # 1. 初始化测试
        print("1️⃣ 测试初始化...")
        init_result = self.tester.test_strategy_initialization(strategy_name)
        results['initialization'] = init_result
        
        if not init_result['success']:
            print(f"❌ 初始化失败: {init_result.get('error')}")
            return results
        
        print("✅ 初始化成功")
        
        # 2. 数据处理测试
        print("2️⃣ 测试数据处理...")
        data_result = self.tester.test_strategy_data_processing(strategy_name, 30, 20)
        results['data_processing'] = data_result
        
        if data_result['success']:
            signals_count = data_result.get('signals_generated', 0)
            print(f"✅ 数据处理成功，生成 {signals_count} 个信号")
        else:
            print(f"❌ 数据处理失败: {data_result.get('error')}")
        
        # 3. 异常处理测试
        print("3️⃣ 测试异常处理...")
        exception_result = self._test_exception_handling(strategy_name)
        results['exception_handling'] = exception_result
        
        return results
    
    def _test_exception_handling(self, strategy_name: str) -> Dict[str, Any]:
        """测试策略异常处理能力"""
        try:
            strategy_info = self.tester.strategies[strategy_name]
            strategy = strategy_info['strategy']
            
            results = {
                'success': True,
                'tests': []
            }
            
            # 测试1: 无效tick数据
            try:
                from core.types import TickData
                invalid_tick = TickData(
                    symbol="INVALID",
                    exchange="UNKNOWN",
                    datetime=datetime.now(),
                    last_price=0.0,  # 无效价格
                    volume=0
                )
                strategy.on_tick(invalid_tick)
                results['tests'].append({'name': 'invalid_tick', 'passed': True})
            except Exception as e:
                results['tests'].append({'name': 'invalid_tick', 'passed': False, 'error': str(e)})
            
            # 测试2: 停止状态下的数据处理
            try:
                original_trading = strategy.trading
                strategy.trading = False
                
                data_generator = MockDataGenerator()
                tick = data_generator.generate_tick()
                strategy.on_tick(tick)  # 应该被忽略
                
                strategy.trading = original_trading
                results['tests'].append({'name': 'stopped_state', 'passed': True})
            except Exception as e:
                results['tests'].append({'name': 'stopped_state', 'passed': False, 'error': str(e)})
            
            return results
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _compare_with_reference(self, ref_results: Dict[str, Any], 
                              test_results: Dict[str, Any]) -> Dict[str, Any]:
        """与参考策略对比"""
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'differences': [],
            'similarities': [],
            'issues': []
        }
        
        # 对比初始化
        ref_init = ref_results.get('initialization', {})
        test_init = test_results.get('initialization', {})
        
        if ref_init.get('success') != test_init.get('success'):
            comparison['differences'].append({
                'category': 'initialization',
                'reference': ref_init.get('success'),
                'tested': test_init.get('success'),
                'severity': 'high'
            })
            
            if not test_init.get('success'):
                comparison['issues'].append({
                    'type': 'initialization_failure',
                    'message': test_init.get('error', '未知错误'),
                    'severity': 'high'
                })
        
        # 对比数据处理
        ref_data = ref_results.get('data_processing', {})
        test_data = test_results.get('data_processing', {})
        
        ref_signals = ref_data.get('signals_generated', 0)
        test_signals = test_data.get('signals_generated', 0)
        
        if ref_data.get('success') and not test_data.get('success'):
            comparison['issues'].append({
                'type': 'data_processing_failure',
                'message': test_data.get('error', '数据处理失败'),
                'severity': 'high'
            })
        
        # 信号生成对比
        if abs(ref_signals - test_signals) > 5:  # 信号数量差异较大
            comparison['differences'].append({
                'category': 'signal_generation',
                'reference': ref_signals,
                'tested': test_signals,
                'severity': 'medium'
            })
        elif ref_signals > 0 and test_signals == 0:
            comparison['issues'].append({
                'type': 'no_signals_generated',
                'message': f'参考策略生成了{ref_signals}个信号，但测试策略没有生成信号',
                'severity': 'high'
            })
        
        # 异常处理对比
        ref_exception = ref_results.get('exception_handling', {})
        test_exception = test_results.get('exception_handling', {})
        
        if ref_exception.get('success') and not test_exception.get('success'):
            comparison['issues'].append({
                'type': 'exception_handling_failure',
                'message': '异常处理能力不如参考策略',
                'severity': 'medium'
            })
        
        return comparison
    
    def _print_comparison_summary(self, strategy_name: str, comparison: Dict[str, Any]):
        """打印对比摘要"""
        print(f"\n📊 {strategy_name} vs {self.reference_strategy} 对比结果:")
        
        issues = comparison.get('issues', [])
        differences = comparison.get('differences', [])
        
        if not issues and not differences:
            print("✅ 行为基本一致，无明显问题")
        else:
            if issues:
                print(f"⚠️ 发现 {len(issues)} 个问题:")
                for issue in issues:
                    severity_icon = "🚨" if issue['severity'] == 'high' else "⚠️"
                    print(f"  {severity_icon} {issue['type']}: {issue['message']}")
            
            if differences:
                print(f"📊 发现 {len(differences)} 个差异:")
                for diff in differences:
                    print(f"  📈 {diff['category']}: 参考={diff['reference']}, 测试={diff['tested']}")


def main():
    """主函数"""
    print("🔍 策略对比测试工具")
    print("=" * 50)
    
    # 获取所有可用策略
    available_strategies = load_available_strategies()
    strategy_names = list(available_strategies.keys())
    
    print(f"📋 可用策略 ({len(strategy_names)} 个):")
    for i, name in enumerate(strategy_names, 1):
        print(f"  {i}. {name}")
    
    # 创建对比器
    comparator = StrategyComparator()
    
    # 确定要对比的策略
    reference_strategy = "SystemIntegrationTestStrategy"
    strategies_to_compare = [name for name in strategy_names if name != reference_strategy]
    
    if not strategies_to_compare:
        print("❌ 没有找到其他策略进行对比")
        return
    
    print(f"\n🎯 将以 {reference_strategy} 为参考策略")
    print(f"📊 对比策略: {', '.join(strategies_to_compare)}")
    
    print("\n🚀 开始对比测试...")
    print("=" * 50)
    
    # 执行对比
    results = comparator.compare_strategies(strategies_to_compare)
    
    # 生成最终报告
    print("\n📊 对比测试总结")
    print("=" * 50)
    
    total_compared = len(strategies_to_compare)
    problematic_strategies = []
    
    for strategy_name in strategies_to_compare:
        comparison_key = f"{strategy_name}_vs_reference"
        if comparison_key in results:
            comparison = results[comparison_key]
            issues = comparison.get('issues', [])
            high_severity_issues = [issue for issue in issues if issue['severity'] == 'high']
            
            if high_severity_issues:
                problematic_strategies.append(strategy_name)
    
    print(f"总对比策略数: {total_compared}")
    print(f"存在问题的策略: {len(problematic_strategies)}")
    print(f"正常策略: {total_compared - len(problematic_strategies)}")
    
    if problematic_strategies:
        print(f"\n⚠️ 需要关注的策略:")
        for strategy_name in problematic_strategies:
            comparison_key = f"{strategy_name}_vs_reference"
            issues = results[comparison_key].get('issues', [])
            high_issues = [issue for issue in issues if issue['severity'] == 'high']
            print(f"  ❌ {strategy_name}: {len(high_issues)} 个严重问题")
    
    # 保存详细结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_file = f"strategy_comparison_results_{timestamp}.json"
    
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 详细结果已保存: {result_file}")
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")
    
    print(f"\n🎉 对比测试完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
