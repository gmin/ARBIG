#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ARBIG系统非交易时间功能测试脚本 (简化版)
测试所有不依赖CTP连接的功能，使用requests替代aiohttp
"""

import json
import sys
import os
import requests
from datetime import datetime
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

class ARBIGTester:
    def __init__(self):
        self.services = {
            "trading_service": "http://localhost:8001",
            "strategy_service": "http://localhost:8002", 
            "web_admin_service": "http://localhost:8000"
        }
        self.test_results = {}
        
    def test_service_health(self, service_name: str, base_url: str) -> Dict[str, Any]:
        """测试服务健康状态"""
        result = {
            "service": service_name,
            "base_url": base_url,
            "status": "unknown",
            "response_time": 0,
            "endpoints": {}
        }
        
        try:
            start_time = datetime.now()
            
            # 测试根端点
            response = requests.get(f"{base_url}/", timeout=5)
            end_time = datetime.now()
            result["response_time"] = (end_time - start_time).total_seconds()
            result["status"] = "running" if response.status_code == 200 else "error"
            result["endpoints"]["/"] = {
                "status": response.status_code,
                "data": response.text[:200]  # 只取前200字符
            }
            
            # 测试健康检查端点
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                result["endpoints"]["/health"] = {
                    "status": response.status_code,
                    "data": response.text[:200]
                }
            except:
                result["endpoints"]["/health"] = {"status": "not_found"}
                
        except Exception as e:
            result["status"] = "offline"
            result["error"] = str(e)
            
        return result
    
    def test_trading_service_apis(self) -> Dict[str, Any]:
        """测试交易服务API接口"""
        base_url = self.services["trading_service"]
        results = {}
        
        test_endpoints = [
            "/real_trading/positions",
            "/real_trading/orders", 
            "/real_trading/trades",
            "/real_trading/account",
            "/real_trading/status",
            "/docs"
        ]
        
        try:
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    results[endpoint] = {
                        "status": response.status_code,
                        "content_type": response.headers.get('content-type', 'unknown')
                    }
                    
                    # 对于JSON响应，尝试解析
                    if 'application/json' in results[endpoint]["content_type"]:
                        try:
                            data = response.json()
                            results[endpoint]["data_keys"] = list(data.keys()) if isinstance(data, dict) else "array"
                        except:
                            results[endpoint]["data_keys"] = "parse_error"
                            
                except Exception as e:
                    results[endpoint] = {"status": "error", "error": str(e)}
                        
        except Exception as e:
            results["connection_error"] = str(e)
            
        return results
    
    def test_strategy_service_apis(self) -> Dict[str, Any]:
        """测试策略服务API接口"""
        base_url = self.services["strategy_service"]
        results = {}
        
        test_endpoints = [
            "/strategies",
            "/strategies/types",
            "/trading/status",
            "/trading/positions"
        ]
        
        try:
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    results[endpoint] = {
                        "status": response.status_code,
                        "content_type": response.headers.get('content-type', 'unknown')
                    }
                    
                    if 'application/json' in results[endpoint]["content_type"]:
                        try:
                            data = response.json()
                            results[endpoint]["data_keys"] = list(data.keys()) if isinstance(data, dict) else "array"
                            
                            # 特殊处理策略类型数据
                            if endpoint == "/strategies/types" and isinstance(data, dict) and "data" in data:
                                results[endpoint]["strategy_count"] = len(data["data"])
                                results[endpoint]["strategy_names"] = list(data["data"].keys())
                                
                        except:
                            results[endpoint]["data_keys"] = "parse_error"
                            
                except Exception as e:
                    results[endpoint] = {"status": "error", "error": str(e)}
                        
        except Exception as e:
            results["connection_error"] = str(e)
            
        return results
    
    def test_web_admin_service(self) -> Dict[str, Any]:
        """测试Web管理服务"""
        base_url = self.services["web_admin_service"] 
        results = {}
        
        test_endpoints = [
            "/",
            "/api/v1/trading/status",
            "/api/v1/trading/positions",
            "/api/v1/trading/strategies"
        ]
        
        try:
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    results[endpoint] = {
                        "status": response.status_code,
                        "content_type": response.headers.get('content-type', 'unknown')
                    }
                    
                    if 'application/json' in results[endpoint]["content_type"]:
                        try:
                            data = response.json()
                            results[endpoint]["data_keys"] = list(data.keys()) if isinstance(data, dict) else "array"
                        except:
                            results[endpoint]["data_keys"] = "parse_error"
                            
                except Exception as e:
                    results[endpoint] = {"status": "error", "error": str(e)}
                        
        except Exception as e:
            results["connection_error"] = str(e)
            
        return results
    
    def test_config_files(self) -> Dict[str, Any]:
        """测试配置文件"""
        config_files = [
            "config/config.yaml",
            "requirements.txt"
        ]
        
        results = {}
        for config_file in config_files:
            file_path = os.path.join(os.path.dirname(__file__), '..', '..', config_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        results[config_file] = {
                            "status": "exists",
                            "size": len(content),
                            "lines": len(content.split('\n'))
                        }
                except Exception as e:
                    results[config_file] = {"status": "read_error", "error": str(e)}
            else:
                results[config_file] = {"status": "not_found"}
                
        return results
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始ARBIG系统非交易时间功能测试")
        print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. 服务健康检查
        print("\n📊 1. 服务健康状态检查")
        for service_name, base_url in self.services.items():
            result = self.test_service_health(service_name, base_url)
            self.test_results[f"{service_name}_health"] = result
            
            status_emoji = "✅" if result["status"] == "running" else "❌" if result["status"] == "offline" else "⚠️"
            print(f"{status_emoji} {service_name}: {result['status']} ({result.get('response_time', 0):.3f}s)")
        
        # 2. 交易服务API测试
        print("\n🔄 2. 交易服务API测试")
        trading_results = self.test_trading_service_apis()
        self.test_results["trading_apis"] = trading_results
        
        for endpoint, result in trading_results.items():
            if isinstance(result, dict) and "status" in result:
                status_emoji = "✅" if result["status"] == 200 else "❌"
                print(f"{status_emoji} {endpoint}: HTTP {result['status']}")
        
        # 3. 策略服务API测试  
        print("\n🧠 3. 策略服务API测试")
        strategy_results = self.test_strategy_service_apis()
        self.test_results["strategy_apis"] = strategy_results
        
        if "connection_error" in strategy_results:
            print("❌ 策略服务连接失败:", strategy_results["connection_error"])
        else:
            for endpoint, result in strategy_results.items():
                if isinstance(result, dict) and "status" in result:
                    status_emoji = "✅" if result["status"] == 200 else "❌"
                    print(f"{status_emoji} {endpoint}: HTTP {result['status']}")
                    
                    if endpoint == "/strategies/types" and "strategy_count" in result:
                        print(f"   📋 发现 {result['strategy_count']} 个策略类型: {', '.join(result['strategy_names'])}")
        
        # 4. Web管理服务测试
        print("\n🌐 4. Web管理服务测试")
        web_results = self.test_web_admin_service()
        self.test_results["web_apis"] = web_results
        
        if "connection_error" in web_results:
            print("❌ Web管理服务连接失败:", web_results["connection_error"])
        else:
            for endpoint, result in web_results.items():
                if isinstance(result, dict) and "status" in result:
                    status_emoji = "✅" if result["status"] == 200 else "❌"
                    print(f"{status_emoji} {endpoint}: HTTP {result['status']}")
        
        # 5. 配置文件检查
        print("\n⚙️  5. 配置文件检查")
        config_results = self.test_config_files()
        self.test_results["config_files"] = config_results
        
        for config_file, result in config_results.items():
            status_emoji = "✅" if result["status"] == "exists" else "❌"
            print(f"{status_emoji} {config_file}: {result['status']}")
        
        # 测试总结
        print("\n" + "=" * 60)
        print("📋 测试总结")
        
        total_tests = 0
        passed_tests = 0
        
        # 统计服务状态
        for service_name in self.services.keys():
            total_tests += 1
            if self.test_results[f"{service_name}_health"]["status"] == "running":
                passed_tests += 1
        
        # 统计API测试
        for api_group in ["trading_apis", "strategy_apis", "web_apis"]:
            if api_group in self.test_results:
                for endpoint, result in self.test_results[api_group].items():
                    if isinstance(result, dict) and "status" in result:
                        total_tests += 1
                        if result["status"] == 200:
                            passed_tests += 1
        
        # 配置文件
        for result in self.test_results["config_files"].values():
            total_tests += 1
            if result["status"] == "exists":
                passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"✅ 通过: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 系统基础功能正常，可以进行交易时间测试！")
        elif success_rate >= 60:
            print("⚠️  系统部分功能异常，建议修复后再进行交易时间测试")
        else:
            print("❌ 系统存在较多问题，需要优先修复基础功能")
        
        return self.test_results

def main():
    """主函数"""
    tester = ARBIGTester()
    results = tester.run_all_tests()
    
    # 保存测试结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    results_file = os.path.join(log_dir, f"test_results_{timestamp}.json")
    
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 测试结果已保存到: {results_file}")
    except Exception as e:
        print(f"\n❌ 保存测试结果失败: {e}")

if __name__ == "__main__":
    main()
