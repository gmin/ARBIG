#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略管理系统增强功能测试脚本
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import requests
import time

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class StrategyManagementTester:
    def __init__(self):
        self.strategy_service_url = "http://localhost:8002"
        self.web_admin_url = "http://localhost:80"
        self.test_strategy_name = "test_performance_001"
        
    def test_service_connectivity(self):
        """测试服务连接"""
        print("🔗 测试服务连接...")
        
        services = {
            "策略服务": self.strategy_service_url,
            "Web管理服务": self.web_admin_url
        }
        
        results = {}
        for name, url in services.items():
            try:
                response = requests.get(f"{url}/", timeout=5)
                results[name] = response.status_code == 200
                print(f"   {'✅' if results[name] else '❌'} {name}: {url}")
            except Exception as e:
                results[name] = False
                print(f"   ❌ {name}: 连接失败 - {e}")
        
        return all(results.values())
    
    def test_strategy_api(self):
        """测试策略API"""
        print("\n📋 测试策略管理API...")
        
        try:
            # 测试获取策略类型
            response = requests.get(f"{self.strategy_service_url}/strategies/types")
            if response.status_code == 200:
                data = response.json()
                strategy_types = data.get("data", {})
                print(f"   ✅ 获取策略类型: 发现 {len(strategy_types)} 个策略类型")
                for strategy_type in list(strategy_types.keys())[:3]:  # 显示前3个
                    print(f"      - {strategy_type}")
            else:
                print(f"   ❌ 获取策略类型失败: HTTP {response.status_code}")
                return False
            
            # 测试获取策略列表
            response = requests.get(f"{self.strategy_service_url}/strategies")
            if response.status_code == 200:
                data = response.json()
                strategies = data.get("data", {})
                print(f"   ✅ 获取策略列表: 发现 {len(strategies)} 个策略实例")
            else:
                print(f"   ❌ 获取策略列表失败: HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 策略API测试失败: {e}")
            return False
    
    def test_performance_api(self):
        """测试性能统计API"""
        print("\n📊 测试性能统计API...")
        
        try:
            # 测试获取所有策略性能
            response = requests.get(f"{self.strategy_service_url}/strategies/performance")
            if response.status_code == 200:
                data = response.json()
                performance_data = data.get("data", {})
                print(f"   ✅ 获取所有策略性能: 发现 {len(performance_data)} 个策略的性能数据")
                
                # 显示性能数据示例
                for strategy_name, perf in list(performance_data.items())[:2]:
                    print(f"      - {strategy_name}: 盈亏={perf.get('net_pnl', 0):.2f}, 胜率={perf.get('win_rate', 0)*100:.1f}%")
            else:
                print(f"   ❌ 获取性能统计失败: HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 性能API测试失败: {e}")
            return False
    
    def test_strategy_registration(self):
        """测试策略注册"""
        print("\n➕ 测试策略注册...")
        
        try:
            # 注册测试策略
            params = {
                "strategy_name": self.test_strategy_name,
                "symbol": "au2412",
                "strategy_type": "TestStrategy",
                "params": {
                    "signal_interval": 60,
                    "trade_volume": 1,
                    "max_position": 5
                }
            }
            
            response = requests.post(
                f"{self.strategy_service_url}/strategies/register",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"   ✅ 策略注册成功: {self.test_strategy_name}")
                    return True
                else:
                    print(f"   ❌ 策略注册失败: {data.get('message', '未知错误')}")
                    return False
            else:
                print(f"   ❌ 策略注册失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 策略注册测试失败: {e}")
            return False
    
    def test_strategy_lifecycle(self):
        """测试策略生命周期"""
        print("\n🔄 测试策略生命周期...")
        
        try:
            # 启动策略
            response = requests.post(f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/start")
            if response.status_code == 200:
                print(f"   ✅ 策略启动成功")
            else:
                print(f"   ❌ 策略启动失败: HTTP {response.status_code}")
                return False
            
            # 等待一段时间
            time.sleep(2)
            
            # 检查策略状态
            response = requests.get(f"{self.strategy_service_url}/strategies/{self.test_strategy_name}")
            if response.status_code == 200:
                data = response.json()
                strategy_data = data.get("data", {})
                status = strategy_data.get("status", "unknown")
                print(f"   📊 策略状态: {status}")
            
            # 停止策略
            response = requests.post(f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/stop")
            if response.status_code == 200:
                print(f"   ✅ 策略停止成功")
            else:
                print(f"   ❌ 策略停止失败: HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 策略生命周期测试失败: {e}")
            return False
    
    def test_performance_tracking(self):
        """测试性能跟踪"""
        print("\n📈 测试性能跟踪...")
        
        try:
            # 模拟交易记录
            trade_data = {
                "symbol": "au2412",
                "direction": "buy",
                "volume": 1,
                "price": 520.50,
                "pnl": 100.0,
                "commission": 5.0,
                "order_id": "test_order_001"
            }
            
            response = requests.post(
                f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/trade",
                json=trade_data
            )
            
            if response.status_code == 200:
                print(f"   ✅ 交易记录更新成功")
            else:
                print(f"   ❌ 交易记录更新失败: HTTP {response.status_code}")
                return False
            
            # 模拟持仓更新
            position_data = {"position": 1}
            response = requests.post(
                f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/position",
                json=position_data
            )
            
            if response.status_code == 200:
                print(f"   ✅ 持仓更新成功")
            else:
                print(f"   ❌ 持仓更新失败: HTTP {response.status_code}")
                return False
            
            # 检查性能统计
            response = requests.get(f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/performance")
            if response.status_code == 200:
                data = response.json()
                performance = data.get("data", {})
                print(f"   📊 性能统计更新:")
                print(f"      - 总盈亏: {performance.get('net_pnl', 0):.2f}")
                print(f"      - 交易次数: {performance.get('total_trades', 0)}")
                print(f"      - 当前持仓: {performance.get('current_position', 0)}")
            else:
                print(f"   ❌ 获取性能统计失败: HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ 性能跟踪测试失败: {e}")
            return False
    
    def test_web_admin_proxy(self):
        """测试Web管理服务代理"""
        print("\n🌐 测试Web管理服务代理...")
        
        try:
            # 测试策略列表代理
            response = requests.get(f"{self.web_admin_url}/api/v1/trading/strategies")
            if response.status_code == 200:
                print(f"   ✅ 策略列表代理正常")
            else:
                print(f"   ❌ 策略列表代理失败: HTTP {response.status_code}")
                return False
            
            # 测试性能统计代理
            response = requests.get(f"{self.web_admin_url}/api/v1/trading/strategies/performance")
            if response.status_code == 200:
                print(f"   ✅ 性能统计代理正常")
            else:
                print(f"   ❌ 性能统计代理失败: HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ Web管理服务代理测试失败: {e}")
            return False
    
    def cleanup_test_strategy(self):
        """清理测试策略"""
        print("\n🧹 清理测试数据...")
        
        try:
            # 尝试删除测试策略（如果有删除API）
            # 目前没有删除API，所以只是停止策略
            response = requests.post(f"{self.strategy_service_url}/strategies/{self.test_strategy_name}/stop")
            if response.status_code == 200:
                print(f"   ✅ 测试策略已停止")
            
        except Exception as e:
            print(f"   ⚠️  清理测试数据失败: {e}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 策略管理系统增强功能测试")
        print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        test_results = []
        
        # 运行测试
        tests = [
            ("服务连接", self.test_service_connectivity),
            ("策略API", self.test_strategy_api),
            ("性能统计API", self.test_performance_api),
            ("策略注册", self.test_strategy_registration),
            ("策略生命周期", self.test_strategy_lifecycle),
            ("性能跟踪", self.test_performance_tracking),
            ("Web代理", self.test_web_admin_proxy),
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                test_results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")
                test_results.append((test_name, False))
        
        # 清理测试数据
        self.cleanup_test_strategy()
        
        # 测试总结
        print("\n" + "=" * 60)
        print("📋 测试总结")
        
        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        for test_name, result in test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {status} {test_name}")
        
        print(f"\n🎯 测试结果: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 策略管理系统增强功能基本正常！")
            print("💡 建议: 可以在交易时间进一步测试实际交易功能")
        elif success_rate >= 60:
            print("⚠️  策略管理系统部分功能异常")
            print("💡 建议: 检查失败的测试项，修复后重新测试")
        else:
            print("❌ 策略管理系统存在较多问题")
            print("💡 建议: 优先修复基础功能，确保服务正常运行")
        
        return success_rate >= 80

def main():
    """主函数"""
    tester = StrategyManagementTester()
    success = tester.run_all_tests()
    
    # 保存测试结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"/root/ARBIG/logs/strategy_management_test_{timestamp}.json"
    
    try:
        results = {
            "timestamp": timestamp,
            "success": success,
            "test_details": "详细结果请查看控制台输出"
        }
        
        os.makedirs("/root/ARBIG/logs", exist_ok=True)
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 测试结果已保存到: {results_file}")
    except Exception as e:
        print(f"\n❌ 保存测试结果失败: {e}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
