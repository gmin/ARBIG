#!/usr/bin/env python3
"""
完整的策略诊断脚本
一键检测所有策略加载问题
"""

import sys
import os
import subprocess
import json
import requests
from pathlib import Path

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"🔍 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"❌ 错误: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "❌ 超时"
    except Exception as e:
        return f"❌ 异常: {str(e)}"

def test_api_endpoint(url, description):
    """测试API端点"""
    print(f"🌐 {description}: {url}")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            try:
                data = response.json()
                return f"✅ 成功", data
            except:
                return f"✅ 成功 (非JSON响应)", response.text[:200]
        else:
            return f"❌ HTTP {response.status_code}", response.text[:200]
    except requests.exceptions.ConnectionError:
        return "❌ 连接失败", None
    except requests.exceptions.Timeout:
        return "❌ 超时", None
    except Exception as e:
        return f"❌ 异常: {str(e)}", None

def test_strategy_adapter():
    """测试策略适配器"""
    print("🧪 测试策略适配器")
    print("-" * 40)
    
    try:
        # 添加项目根目录到路径
        sys.path.append('.')
        
        from services.strategy_service.backtesting.strategy_adapter import get_adapted_strategies
        
        strategies = get_adapted_strategies()
        
        print(f"✅ 策略适配器成功: {len(strategies)} 个策略")
        for name in strategies.keys():
            print(f"  - {name}")
        
        return strategies
        
    except Exception as e:
        print(f"❌ 策略适配器失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_strategy_files():
    """检查策略文件"""
    print("\n📁 检查策略文件")
    print("-" * 40)
    
    strategies_dir = Path("services/strategy_service/strategies")
    
    if not strategies_dir.exists():
        print(f"❌ 策略目录不存在: {strategies_dir}")
        return []
    
    strategy_files = list(strategies_dir.glob("*.py"))
    strategy_files = [f for f in strategy_files if not f.name.startswith("__")]
    
    print(f"📋 找到 {len(strategy_files)} 个策略文件:")
    for f in strategy_files:
        print(f"  - {f.name}")
    
    return strategy_files

def check_services_status():
    """检查服务状态"""
    print("\n🚀 检查服务状态")
    print("-" * 40)
    
    # 检查端口占用
    ports_info = run_command("netstat -tlnp | grep -E '(8001|8002|8003|8004|8080|80)'", "端口占用情况")
    print(ports_info)
    
    print()
    
    # 检查Python进程
    processes_info = run_command("ps aux | grep python | grep -E '(main.py|start_with_logs|trading_service|strategy_service|web_admin_service)' | grep -v grep", "Python进程")
    print(processes_info)

def test_all_apis():
    """测试所有API"""
    print("\n🌐 测试所有API")
    print("-" * 40)
    
    apis_to_test = [
        ("http://localhost:8002/", "策略服务根路径"),
        ("http://localhost:8002/backtest/strategies", "策略服务-回测策略列表"),
        ("http://localhost:8002/backtest/health", "策略服务-回测健康检查"),
        ("http://localhost:8003/", "专业回测服务根路径"),
        ("http://localhost:8003/backtest/strategies", "专业回测服务-策略列表"),
        ("http://localhost:8003/health", "专业回测服务-健康检查"),
        ("http://localhost:8004/", "交易服务根路径"),
        ("http://localhost:8004/api/v1/trading/strategy/status", "交易服务-策略状态"),
        ("http://localhost:8080/", "Web服务根路径"),
    ]
    
    results = {}
    for url, description in apis_to_test:
        status, data = test_api_endpoint(url, description)
        results[url] = {"status": status, "data": data}
        print(f"  {status}")
        if data and isinstance(data, dict) and "strategies" in str(data):
            print(f"    策略数据: {data}")
        print()
    
    return results

def analyze_web_service_issue():
    """分析Web服务问题"""
    print("\n🔧 分析Web服务策略加载问题")
    print("-" * 40)
    
    print("Web服务调用的API路径:")
    print("  - /api/v1/trading/strategy/status (交易服务)")
    print("  - 但策略数据在回测服务: /backtest/strategies")
    print()
    
    # 检查交易服务是否有策略状态API
    status, data = test_api_endpoint("http://localhost:8004/api/v1/trading/strategy/status", "交易服务策略状态API")
    if "连接失败" in status or "404" in status:
        print("❌ 问题确认: 交易服务没有策略状态API")
        print("💡 解决方案: Web服务应该调用回测服务的API")
    
    return status, data

def generate_fix_suggestions(strategy_adapter_result, api_results):
    """生成修复建议"""
    print("\n🔧 修复建议")
    print("=" * 50)
    
    # 策略适配器问题
    if len(strategy_adapter_result) == 0:
        print("❌ 策略适配器没有加载任何策略")
        print("建议:")
        print("  1. 检查策略文件的导入路径")
        print("  2. 检查ARBIGCtaTemplate的导入")
        print("  3. 运行: python diagnose_strategies.py")
    elif len(strategy_adapter_result) < 7:
        print(f"⚠️ 策略适配器只加载了 {len(strategy_adapter_result)}/7 个策略")
        print("建议:")
        print("  1. 检查失败策略的导入错误")
        print("  2. 修复导入路径问题")
    else:
        print(f"✅ 策略适配器正常: {len(strategy_adapter_result)} 个策略")
    
    print()
    
    # API问题
    strategy_api_working = False
    for url, result in api_results.items():
        if "backtest/strategies" in url and "✅" in result["status"]:
            strategy_api_working = True
            break
    
    if not strategy_api_working:
        print("❌ 回测服务的策略API不可用")
        print("建议:")
        print("  1. 检查回测服务是否正常启动")
        print("  2. 检查8002和8003端口是否正常监听")
        print("  3. 重启策略服务和专业回测服务")
    else:
        print("✅ 回测服务的策略API正常")
    
    print()
    
    # Web服务问题
    web_api_issue = True
    for url, result in api_results.items():
        if "trading/strategy/status" in url and "✅" in result["status"]:
            web_api_issue = False
            break
    
    if web_api_issue:
        print("❌ Web服务调用错误的API")
        print("问题: Web服务调用 /api/v1/trading/strategy/status")
        print("解决: 应该调用 /backtest/strategies")
        print("建议:")
        print("  1. 修改Web服务的策略加载逻辑")
        print("  2. 或者在交易服务中添加策略状态API")

def main():
    """主函数"""
    print("🎯 ARBIG策略完整诊断工具")
    print("=" * 60)
    print(f"诊断时间: {datetime.now()}")
    print("=" * 60)
    
    # 1. 检查策略文件
    strategy_files = check_strategy_files()
    
    # 2. 检查服务状态
    check_services_status()
    
    # 3. 测试策略适配器
    strategy_adapter_result = test_strategy_adapter()
    
    # 4. 测试所有API
    api_results = test_all_apis()
    
    # 5. 分析Web服务问题
    web_status, web_data = analyze_web_service_issue()
    
    # 6. 生成修复建议
    generate_fix_suggestions(strategy_adapter_result, api_results)
    
    print("\n" + "=" * 60)
    print("🎯 诊断完成")
    print("=" * 60)
    
    print(f"策略文件: {len(strategy_files)} 个")
    print(f"适配策略: {len(strategy_adapter_result)} 个")
    print(f"API测试: {len([r for r in api_results.values() if '✅' in r['status']])}/{len(api_results)} 个成功")

if __name__ == "__main__":
    from datetime import datetime
    main()
