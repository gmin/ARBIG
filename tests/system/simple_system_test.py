#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ARBIG系统简单功能测试脚本 (不依赖额外包)
"""

import subprocess
import json
import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

def run_curl_command(url, timeout=5):
    """执行curl命令并返回结果"""
    try:
        cmd = f"curl -s --connect-timeout {timeout} {url}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout+2)
        return {
            "success": result.returncode == 0,
            "status_code": result.returncode,
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_service_status(service_name, url):
    """测试服务状态"""
    print(f"\n🔍 测试 {service_name}")
    print(f"   URL: {url}")
    
    result = run_curl_command(url)
    
    if result["success"]:
        print(f"   ✅ 服务响应正常")
        try:
            # 尝试解析JSON响应
            data = json.loads(result["output"])
            if isinstance(data, dict):
                print(f"   📊 响应数据: {', '.join(data.keys())}")
                if "status" in data:
                    print(f"   🚦 服务状态: {data['status']}")
        except json.JSONDecodeError:
            print(f"   📄 响应类型: HTML/文本 ({len(result['output'])} 字符)")
    else:
        print(f"   ❌ 服务无响应: {result.get('error', '未知错误')}")
    
    return result["success"]

def test_api_endpoints(service_name, base_url, endpoints):
    """测试API端点"""
    print(f"\n🔗 测试 {service_name} API端点")
    
    success_count = 0
    total_count = len(endpoints)
    
    for endpoint in endpoints:
        full_url = f"{base_url}{endpoint}"
        result = run_curl_command(full_url)
        
        if result["success"]:
            print(f"   ✅ {endpoint}")
            success_count += 1
        else:
            print(f"   ❌ {endpoint}: {result.get('error', '失败')}")
    
    print(f"   📊 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    return success_count, total_count

def check_processes():
    """检查相关进程"""
    print(f"\n🔄 检查运行中的服务进程")
    
    processes_to_check = [
        ("trading_service", "trading_service/main.py"),
        ("strategy_service", "strategy_service/main.py"), 
        ("web_admin_service", "web_admin_service/main.py")
    ]
    
    running_services = []
    
    for service_name, process_pattern in processes_to_check:
        try:
            cmd = f"ps aux | grep '{process_pattern}' | grep -v grep"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"   ✅ {service_name}: 运行中")
                running_services.append(service_name)
            else:
                print(f"   ❌ {service_name}: 未运行")
        except Exception as e:
            print(f"   ⚠️  {service_name}: 检查失败 ({e})")
    
    return running_services

def check_ports():
    """检查端口占用"""
    print(f"\n🌐 检查服务端口")
    
    ports_to_check = [
        ("交易服务", 8001),
        ("策略服务", 8002),
        ("Web管理服务", 80)
    ]
    
    open_ports = []
    
    for service_name, port in ports_to_check:
        try:
            cmd = f"netstat -tlnp | grep ':{port}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"   ✅ {service_name} (端口 {port}): 监听中")
                open_ports.append(port)
            else:
                print(f"   ❌ {service_name} (端口 {port}): 未监听")
        except Exception as e:
            print(f"   ⚠️  {service_name} (端口 {port}): 检查失败 ({e})")
    
    return open_ports

def check_config_files():
    """检查配置文件"""
    print(f"\n⚙️  检查配置文件")
    
    config_files = [
        "config/config.yaml",
        "requirements.txt", 
        "setup.py"
    ]
    
    existing_files = []
    
    for config_file in config_files:
        file_path = os.path.join("/root/ARBIG", config_file)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"   ✅ {config_file}: 存在 ({file_size} 字节)")
            existing_files.append(config_file)
        else:
            print(f"   ❌ {config_file}: 不存在")
    
    return existing_files

def main():
    """主测试函数"""
    print("🚀 ARBIG系统基础功能测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 检查进程
    running_services = check_processes()
    
    # 2. 检查端口
    open_ports = check_ports()
    
    # 3. 检查配置文件
    existing_configs = check_config_files()
    
    # 4. 测试服务状态
    services = {
        "交易服务": "http://localhost:8001/",
        "策略服务": "http://localhost:8002/",
        "Web管理服务": "http://localhost:80/"
    }
    
    responsive_services = []
    for service_name, url in services.items():
        if test_service_status(service_name, url):
            responsive_services.append(service_name)
    
    # 5. 测试API端点 (仅对响应的服务)
    total_api_tests = 0
    passed_api_tests = 0
    
    if "交易服务" in responsive_services:
        endpoints = ["/real_trading/status", "/real_trading/positions", "/docs"]
        passed, total = test_api_endpoints("交易服务", "http://localhost:8001", endpoints)
        passed_api_tests += passed
        total_api_tests += total
    
    if "策略服务" in responsive_services:
        endpoints = ["/strategies", "/strategies/types"]
        passed, total = test_api_endpoints("策略服务", "http://localhost:8002", endpoints)
        passed_api_tests += passed
        total_api_tests += total
    
    if "Web管理服务" in responsive_services:
        endpoints = ["/api/v1/trading/status"]
        passed, total = test_api_endpoints("Web管理服务", "http://localhost:80", endpoints)
        passed_api_tests += passed
        total_api_tests += total
    
    # 6. 生成测试报告
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print(f"🔄 运行中的服务: {len(running_services)}/3")
    print(f"🌐 开放的端口: {len(open_ports)}/3") 
    print(f"📄 存在的配置文件: {len(existing_configs)}/3")
    print(f"🌍 响应的服务: {len(responsive_services)}/3")
    if total_api_tests > 0:
        print(f"🔗 API测试通过: {passed_api_tests}/{total_api_tests} ({passed_api_tests/total_api_tests*100:.1f}%)")
    
    # 计算总体健康度
    total_checks = 4  # 进程、端口、配置、服务响应
    if total_api_tests > 0:
        total_checks = 5
    
    health_score = (
        (len(running_services)/3) + 
        (len(open_ports)/3) + 
        (len(existing_configs)/3) + 
        (len(responsive_services)/3) +
        (passed_api_tests/total_api_tests if total_api_tests > 0 else 0)
    ) / total_checks * 100
    
    print(f"\n🎯 系统健康度: {health_score:.1f}%")
    
    if health_score >= 80:
        print("🎉 系统状态良好，可以进行进一步测试！")
        print("💡 建议：在交易时间测试CTP连接和实时交易功能")
    elif health_score >= 60:
        print("⚠️  系统部分功能异常，建议检查未运行的服务")
        print("💡 建议：启动所有服务后再进行测试")
    else:
        print("❌ 系统存在较多问题，需要检查服务配置")
        print("💡 建议：检查日志文件，修复配置问题")
    
    # 保存简单的测试结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = {
        "timestamp": timestamp,
        "running_services": running_services,
        "open_ports": open_ports,
        "responsive_services": responsive_services,
        "health_score": health_score
    }
    
    try:
        results_file = f"/root/ARBIG/logs/simple_test_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 测试结果已保存到: {results_file}")
    except Exception as e:
        print(f"\n⚠️  保存测试结果失败: {e}")

if __name__ == "__main__":
    main()
