#!/usr/bin/env python3
"""
显示ARBIG系统的启动参数和使用方法
"""

def show_startup_options():
    print("🚀 ARBIG量化交易系统启动参数")
    print("=" * 60)
    
    print("\n📋 基本用法:")
    print("python main.py [选项]")
    
    print("\n🔧 可用参数:")
    print("--daemon, -d          后台运行模式")
    print("--api-only            仅启动API服务（不启动交易系统）")
    print("--auto-start          自动启动系统")
    print("--demo-mode           演示模式（不需要CTP连接）")
    print("--help, -h            显示帮助信息")
    
    print("\n💡 常用启动命令:")
    print("1. 完整交易模式（推荐）:")
    print("   python main.py --auto-start --daemon")
    print("   - 启动完整的交易系统")
    print("   - 连接真实CTP服务器")
    print("   - 后台运行")
    
    print("\n2. 演示模式:")
    print("   python main.py --auto-start --demo-mode --daemon")
    print("   - 启动演示模式")
    print("   - 不连接CTP服务器")
    print("   - 使用模拟数据")
    print("   - 后台运行")
    
    print("\n3. 仅API服务:")
    print("   python main.py --api-only")
    print("   - 只启动Web API服务")
    print("   - 不启动交易系统")
    print("   - 前台运行")
    
    print("\n4. 交互式启动:")
    print("   python main.py --auto-start")
    print("   - 启动完整系统")
    print("   - 前台运行，可以看到日志")
    print("   - 按Ctrl+C停止")
    
    print("\n🌐 Web访问地址:")
    print("- 主页面: http://您的转发地址:8000")
    print("- 策略监控: http://您的转发地址:8000/strategy_monitor.html?strategy=shfe_quant")
    print("- API文档: http://您的转发地址:8000/api/docs")
    print("- 系统状态: http://您的转发地址:8000/api/v1/system/status")
    
    print("\n⚠️ 重要提醒:")
    print("1. 必须在vnpy环境下启动:")
    print("   source /root/anaconda3/etc/profile.d/conda.sh")
    print("   conda activate vnpy")
    print("   cd /root/ARBIG")
    print("   python main.py [参数]")
    
    print("\n2. 交易模式 vs 演示模式:")
    print("   - 交易模式: 连接真实CTP，可以进行实际交易")
    print("   - 演示模式: 使用模拟数据，安全测试功能")
    
    print("\n3. 后台模式 vs 前台模式:")
    print("   - 后台模式(--daemon): 程序在后台运行，不显示日志")
    print("   - 前台模式: 显示实时日志，便于调试")
    
    print("\n📊 当前推荐启动命令:")
    print("bash -c \"")
    print("source /root/anaconda3/etc/profile.d/conda.sh")
    print("conda activate vnpy")
    print("cd /root/ARBIG")
    print("python main.py --auto-start --daemon")
    print("\"")
    
    print("\n🔍 检查系统状态:")
    print("curl -s http://localhost:8000/api/v1/system/status | jq '.data.system_status'")
    
    print("\n🛠️ 故障排除:")
    print("1. 如果页面无法访问:")
    print("   - 检查端口8000是否被占用: netstat -tlnp | grep :8000")
    print("   - 检查防火墙设置")
    print("   - 检查网络转发配置")
    
    print("\n2. 如果CTP连接失败:")
    print("   - 检查网络连接")
    print("   - 检查CTP账户配置")
    print("   - 尝试使用演示模式测试")
    
    print("\n3. 如果环境问题:")
    print("   - 确认在vnpy环境下运行")
    print("   - 检查Python路径: which python")
    print("   - 检查conda环境: echo $CONDA_DEFAULT_ENV")

if __name__ == "__main__":
    show_startup_options()
