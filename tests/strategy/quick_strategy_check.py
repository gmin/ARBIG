#!/usr/bin/env python3
"""
快速策略检查工具
用于快速验证策略的基本结构和接口兼容性
不需要运行复杂的测试，只检查关键方法和属性
"""

import sys
import os
import inspect
from typing import Dict, Any, List, Type
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from services.strategy_service.core.cta_template import ARBIGCtaTemplate
from utils.logger import get_logger

logger = get_logger(__name__)


class StrategyChecker:
    """策略检查器"""
    
    def __init__(self):
        self.required_methods = [
            'on_init', 'on_start', 'on_stop', 
            'on_tick', 'on_bar'
        ]
        self.recommended_attributes = [
            'trading', 'pos', 'symbol'
        ]
        
    def check_strategy_class(self, strategy_class: Type[ARBIGCtaTemplate], 
                           strategy_name: str) -> Dict[str, Any]:
        """检查策略类的基本结构"""
        result = {
            'strategy_name': strategy_name,
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'issues': [],
            'warnings': [],
            'score': 0,
            'max_score': 0
        }
        
        try:
            # 检查1: 继承关系
            result['max_score'] += 10
            if issubclass(strategy_class, ARBIGCtaTemplate):
                result['checks']['inheritance'] = True
                result['score'] += 10
                print(f"✅ 继承检查: 正确继承 ARBIGCtaTemplate")
            else:
                result['checks']['inheritance'] = False
                result['issues'].append("策略未正确继承 ARBIGCtaTemplate")
                print(f"❌ 继承检查: 未继承 ARBIGCtaTemplate")
            
            # 检查2: 构造函数
            result['max_score'] += 10
            try:
                init_signature = inspect.signature(strategy_class.__init__)
                params = list(init_signature.parameters.keys())
                
                required_params = ['self', 'strategy_name', 'symbol', 'setting']
                missing_params = [p for p in required_params if p not in params]
                
                if not missing_params:
                    result['checks']['constructor'] = True
                    result['score'] += 10
                    print(f"✅ 构造函数检查: 参数完整")
                else:
                    result['checks']['constructor'] = False
                    result['issues'].append(f"构造函数缺少参数: {missing_params}")
                    print(f"❌ 构造函数检查: 缺少参数 {missing_params}")
                    
            except Exception as e:
                result['checks']['constructor'] = False
                result['issues'].append(f"构造函数检查失败: {e}")
                print(f"❌ 构造函数检查: 失败 - {e}")
            
            # 检查3: 必需方法
            result['max_score'] += len(self.required_methods) * 5
            missing_methods = []
            
            for method_name in self.required_methods:
                if hasattr(strategy_class, method_name):
                    method = getattr(strategy_class, method_name)
                    if callable(method):
                        result['checks'][f'method_{method_name}'] = True
                        result['score'] += 5
                        print(f"✅ 方法检查: {method_name} 存在")
                    else:
                        result['checks'][f'method_{method_name}'] = False
                        missing_methods.append(f"{method_name} (不可调用)")
                        print(f"❌ 方法检查: {method_name} 不可调用")
                else:
                    result['checks'][f'method_{method_name}'] = False
                    missing_methods.append(method_name)
                    print(f"❌ 方法检查: {method_name} 不存在")
            
            if missing_methods:
                result['issues'].append(f"缺少必需方法: {missing_methods}")
            
            # 检查4: 推荐属性
            result['max_score'] += len(self.recommended_attributes) * 2
            missing_attributes = []
            
            for attr_name in self.recommended_attributes:
                # 检查类级别属性或实例属性
                if (hasattr(strategy_class, attr_name) or 
                    attr_name in strategy_class.__dict__ or
                    any(attr_name in getattr(cls, '__dict__', {}) for cls in strategy_class.__mro__)):
                    result['checks'][f'attr_{attr_name}'] = True
                    result['score'] += 2
                    print(f"✅ 属性检查: {attr_name} 存在")
                else:
                    result['checks'][f'attr_{attr_name}'] = False
                    missing_attributes.append(attr_name)
                    print(f"⚠️ 属性检查: {attr_name} 不存在")
            
            if missing_attributes:
                result['warnings'].append(f"建议添加属性: {missing_attributes}")
            
            # 检查5: 实例化测试
            result['max_score'] += 15
            try:
                # 尝试创建实例
                test_instance = strategy_class(
                    strategy_name="test_strategy",
                    symbol="test_symbol",
                    setting={},
                    signal_sender=None
                )
                result['checks']['instantiation'] = True
                result['score'] += 15
                print(f"✅ 实例化检查: 成功创建实例")
                
                # 额外检查实例属性
                if hasattr(test_instance, 'trading'):
                    print(f"  📊 trading 属性: {getattr(test_instance, 'trading', 'undefined')}")
                if hasattr(test_instance, 'pos'):
                    print(f"  📊 pos 属性: {getattr(test_instance, 'pos', 'undefined')}")
                    
            except Exception as e:
                result['checks']['instantiation'] = False
                result['issues'].append(f"实例化失败: {e}")
                print(f"❌ 实例化检查: 失败 - {e}")
            
            # 计算总分
            percentage = (result['score'] / result['max_score']) * 100 if result['max_score'] > 0 else 0
            result['percentage'] = round(percentage, 1)
            
        except Exception as e:
            result['issues'].append(f"检查过程异常: {e}")
            logger.error(f"策略检查异常 {strategy_name}: {e}")
        
        return result
    
    def generate_recommendation(self, check_result: Dict[str, Any]) -> List[str]:
        """根据检查结果生成建议"""
        recommendations = []
        
        percentage = check_result.get('percentage', 0)
        issues = check_result.get('issues', [])
        warnings = check_result.get('warnings', [])
        
        if percentage >= 90:
            recommendations.append("✅ 策略结构优秀，可以进行实盘测试")
        elif percentage >= 70:
            recommendations.append("⚠️ 策略结构良好，建议修复警告后测试")
        elif percentage >= 50:
            recommendations.append("🔧 策略结构需要改进，建议修复问题后测试")
        else:
            recommendations.append("❌ 策略结构存在严重问题，不建议测试")
        
        # 具体建议
        if issues:
            recommendations.append(f"🚨 严重问题需要修复: {len(issues)} 个")
            for issue in issues[:3]:  # 只显示前3个
                recommendations.append(f"  - {issue}")
        
        if warnings:
            recommendations.append(f"⚠️ 建议改进: {len(warnings)} 个")
            for warning in warnings[:2]:  # 只显示前2个
                recommendations.append(f"  - {warning}")
        
        return recommendations


def load_and_check_all_strategies():
    """加载并检查所有策略"""
    print("🔍 快速策略检查工具")
    print("=" * 50)
    
    checker = StrategyChecker()
    results = {}
    
    # 尝试加载各种策略
    strategies_to_check = [
        ('SystemIntegrationTestStrategy', 'SystemIntegrationTestStrategy'),
        ('MaRsiComboStrategy', 'MaRsiComboStrategy'),
        ('LargeOrderFollowingStrategy', 'LargeOrderFollowingStrategy'),
        ('VWAPDeviationReversionStrategy', 'VWAPDeviationReversionStrategy'),
        ('MaCrossoverTrendStrategy', 'MaCrossoverTrendStrategy'),
        # 可以添加更多策略...
    ]
    
    for strategy_name, module_path in strategies_to_check:
        print(f"\n📊 检查策略: {strategy_name}")
        print("-" * 30)
        
        try:
            # 动态导入策略
            import importlib
            module = importlib.import_module(f'services.strategy_service.strategies.{strategy_name}')
            strategy_class = getattr(module, strategy_name)
            
            # 检查策略
            check_result = checker.check_strategy_class(strategy_class, strategy_name)
            results[strategy_name] = check_result
            
            # 显示结果
            score = check_result['score']
            max_score = check_result['max_score']
            percentage = check_result.get('percentage', 0)
            
            print(f"\n📊 检查结果: {score}/{max_score} ({percentage}%)")
            
            # 生成建议
            recommendations = checker.generate_recommendation(check_result)
            print("\n💡 建议:")
            for rec in recommendations:
                print(f"  {rec}")
                
        except ImportError as e:
            print(f"❌ 无法导入策略: {e}")
            results[strategy_name] = {'error': f'导入失败: {e}'}
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            results[strategy_name] = {'error': f'检查失败: {e}'}
    
    # 生成总结
    print("\n📊 检查总结")
    print("=" * 50)
    
    total_strategies = len(strategies_to_check)
    successful_checks = len([r for r in results.values() if 'error' not in r])
    
    print(f"总策略数: {total_strategies}")
    print(f"成功检查: {successful_checks}")
    print(f"检查失败: {total_strategies - successful_checks}")
    
    if successful_checks > 0:
        print("\n📋 策略评分:")
        for strategy_name, result in results.items():
            if 'error' not in result:
                percentage = result.get('percentage', 0)
                if percentage >= 90:
                    status = "🟢 优秀"
                elif percentage >= 70:
                    status = "🟡 良好"
                elif percentage >= 50:
                    status = "🟠 需改进"
                else:
                    status = "🔴 有问题"
                
                print(f"  {status} {strategy_name}: {percentage}%")
            else:
                print(f"  ❌ {strategy_name}: {result['error']}")
    
    print(f"\n🎉 检查完成！时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results


def main():
    """主函数"""
    return load_and_check_all_strategies()


if __name__ == "__main__":
    main()
