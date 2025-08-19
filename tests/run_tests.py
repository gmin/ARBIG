#!/usr/bin/env python3
"""
ARBIG测试运行器
支持运行不同类别的测试
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ARBIGTestRunner:
    """ARBIG测试运行器"""
    
    def __init__(self):
        self.project_root = project_root
        self.tests_root = Path(__file__).parent
        self.test_categories = {
            'system': {
                'description': '系统级测试',
                'tests': [
                    'system/simple_system_test.py',
                    'system/test_non_trading_functions.py'
                ]
            },
            'strategy': {
                'description': '策略相关测试',
                'tests': [
                    'strategy/test_strategy_management.py'
                ]
            },
            'integration': {
                'description': '集成测试',
                'tests': [
                    # 待添加
                ]
            },
            'legacy': {
                'description': '遗留测试',
                'tests': [
                    'legacy/ctp_connection_test.py',
                    'legacy/test_account_query.py',
                    'legacy/test_frontend.py',
                    'legacy/test_history_query.py',
                    'legacy/test_order_placement.py',
                    'legacy/test_web_trading.py'
                ]
            }
        }
        
    def list_tests(self):
        """列出所有可用的测试"""
        print("📋 ARBIG可用测试列表")
        print("=" * 50)
        
        for category, info in self.test_categories.items():
            print(f"\n🔸 {category.upper()}: {info['description']}")
            for test in info['tests']:
                test_path = self.tests_root / test
                status = "✅" if test_path.exists() else "❌"
                print(f"   {status} {test}")
    
    def run_test(self, test_path, timeout=300):
        """运行单个测试"""
        full_path = self.tests_root / test_path
        if not full_path.exists():
            return False, f"测试文件不存在: {test_path}"
        
        try:
            # 切换到项目根目录运行测试
            result = subprocess.run(
                [sys.executable, str(full_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, f"测试超时 (>{timeout}秒)"
        except Exception as e:
            return False, f"运行测试失败: {e}"
    
    def run_category(self, category):
        """运行指定类别的所有测试"""
        if category not in self.test_categories:
            print(f"❌ 未知的测试类别: {category}")
            return False
        
        category_info = self.test_categories[category]
        tests = category_info['tests']
        
        if not tests:
            print(f"⚠️  {category.upper()} 类别暂无测试")
            return True
        
        print(f"\n🚀 运行 {category.upper()} 测试: {category_info['description']}")
        print("-" * 50)
        
        results = []
        for test in tests:
            print(f"\n🔄 运行测试: {test}")
            success, output = self.run_test(test)
            
            if success:
                print(f"✅ {test} - 通过")
            else:
                print(f"❌ {test} - 失败")
                print(f"错误信息: {output[:200]}...")
            
            results.append((test, success, output))
        
        # 统计结果
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 {category.upper()} 测试结果: {passed}/{total} ({success_rate:.1f}%)")
        
        return success_rate >= 80  # 80%以上算成功
    
    def run_all(self):
        """运行所有测试"""
        print("🚀 运行ARBIG完整测试套件")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        overall_results = {}
        
        # 按顺序运行各类别测试
        test_order = ['system', 'strategy', 'integration']
        
        for category in test_order:
            if category in self.test_categories:
                success = self.run_category(category)
                overall_results[category] = success
        
        # 生成总结报告
        print("\n" + "=" * 60)
        print("📋 测试总结")
        
        for category, success in overall_results.items():
            status = "✅ 通过" if success else "❌ 失败"
            print(f"   {status} {category.upper()}")
        
        total_success = all(overall_results.values())
        overall_rate = (sum(overall_results.values()) / len(overall_results) * 100) if overall_results else 0
        
        print(f"\n🎯 总体结果: {overall_rate:.1f}% ({sum(overall_results.values())}/{len(overall_results)})")
        
        if total_success:
            print("🎉 所有测试通过！系统状态良好")
        else:
            print("⚠️  部分测试失败，请检查相关功能")
        
        # 保存测试结果
        self.save_results(overall_results)
        
        return total_success
    
    def save_results(self, results):
        """保存测试结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = self.project_root / "logs" / f"test_results_{timestamp}.json"
        
        try:
            # 确保logs目录存在
            results_file.parent.mkdir(exist_ok=True)
            
            test_data = {
                "timestamp": timestamp,
                "results": results,
                "success": all(results.values()),
                "summary": f"{sum(results.values())}/{len(results)} categories passed"
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 测试结果已保存到: {results_file}")
            
        except Exception as e:
            print(f"\n❌ 保存测试结果失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ARBIG测试运行器')
    parser.add_argument('--list', action='store_true', help='列出所有可用测试')
    parser.add_argument('--category', choices=['system', 'strategy', 'integration', 'legacy'], 
                       help='运行指定类别的测试')
    parser.add_argument('--test', help='运行指定的测试文件')
    parser.add_argument('--all', action='store_true', help='运行所有主要测试')
    
    args = parser.parse_args()
    
    runner = ARBIGTestRunner()
    
    if args.list:
        runner.list_tests()
        return 0
    
    if args.test:
        print(f"🔄 运行单个测试: {args.test}")
        success, output = runner.run_test(args.test)
        if success:
            print("✅ 测试通过")
            print(output)
            return 0
        else:
            print("❌ 测试失败")
            print(output)
            return 1
    
    if args.category:
        success = runner.run_category(args.category)
        return 0 if success else 1
    
    if args.all:
        success = runner.run_all()
        return 0 if success else 1
    
    # 默认运行系统测试
    print("ℹ️  未指定测试类别，运行系统测试")
    print("💡 使用 --help 查看更多选项")
    success = runner.run_category('system')
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
