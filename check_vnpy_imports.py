#!/usr/bin/env python3
"""
检查vnpy导入路径
找到正确的BacktestingEngine导入方式
"""

import sys
import importlib

def check_vnpy_structure():
    """检查vnpy的包结构"""
    print("🔍 检查vnpy包结构...")
    
    # 检查vnpy主包
    try:
        import vnpy
        print(f"✅ vnpy 版本: {vnpy.__version__ if hasattr(vnpy, '__version__') else '未知'}")
        print(f"   路径: {vnpy.__file__}")
    except ImportError:
        print("❌ vnpy 未安装")
        return False
    
    # 检查vnpy_ctastrategy包
    try:
        import vnpy_ctastrategy
        print(f"✅ vnpy_ctastrategy 已安装")
        print(f"   路径: {vnpy_ctastrategy.__file__}")
        print(f"   包内容: {dir(vnpy_ctastrategy)}")
    except ImportError:
        print("❌ vnpy_ctastrategy 未安装")
        return False
    
    return True

def test_backtesting_imports():
    """测试各种BacktestingEngine导入方式"""
    print("\n🧪 测试BacktestingEngine导入...")
    
    import_paths = [
        "vnpy_ctastrategy.backtesting.BacktestingEngine",
        "vnpy_ctastrategy.engine.BacktestingEngine", 
        "vnpy_ctastrategy.BacktestingEngine",
        "vnpy.app.cta_strategy.backtesting.BacktestingEngine",
        "vnpy.app.cta_strategy.engine.BacktestingEngine",
    ]
    
    successful_imports = []
    
    for import_path in import_paths:
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            BacktestingEngine = getattr(module, class_name)
            print(f"✅ 成功: {import_path}")
            successful_imports.append(import_path)
        except (ImportError, AttributeError) as e:
            print(f"❌ 失败: {import_path} - {e}")
    
    return successful_imports

def test_template_imports():
    """测试CtaTemplate导入方式"""
    print("\n🧪 测试CtaTemplate导入...")
    
    import_paths = [
        "vnpy_ctastrategy.template.CtaTemplate",
        "vnpy_ctastrategy.CtaTemplate",
        "vnpy.app.cta_strategy.template.CtaTemplate",
    ]
    
    successful_imports = []
    
    for import_path in import_paths:
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            CtaTemplate = getattr(module, class_name)
            print(f"✅ 成功: {import_path}")
            successful_imports.append(import_path)
        except (ImportError, AttributeError) as e:
            print(f"❌ 失败: {import_path} - {e}")
    
    return successful_imports

def generate_working_imports(backtesting_imports, template_imports):
    """生成可用的导入代码"""
    print("\n📝 生成可用的导入代码...")
    
    if not backtesting_imports or not template_imports:
        print("❌ 无法找到可用的导入路径")
        return None
    
    backtesting_path = backtesting_imports[0]
    template_path = template_imports[0]
    
    # 生成导入代码
    backtesting_module, backtesting_class = backtesting_path.rsplit('.', 1)
    template_module, template_class = template_path.rsplit('.', 1)
    
    import_code = f"""
# 可用的vnpy导入代码
try:
    from {backtesting_module} import {backtesting_class}
    from {template_module} import {template_class}
    from vnpy.trader.constant import Interval, Exchange
    from vnpy.trader.object import TickData, BarData, OrderData, TradeData
    print("✅ vnpy模块导入成功")
except ImportError as e:
    print(f"❌ vnpy模块导入失败: {{e}}")
    {backtesting_class} = None
    {template_class} = None
"""
    
    print(import_code)
    return import_code

def test_simple_backtest():
    """测试简单回测功能"""
    print("\n🚀 测试简单回测功能...")
    
    try:
        # 尝试导入
        from vnpy_ctastrategy.backtesting import BacktestingEngine
        from vnpy_ctastrategy.template import CtaTemplate
        from vnpy.trader.constant import Interval
        from datetime import datetime
        
        print("✅ 导入成功，创建回测引擎...")
        
        # 创建回测引擎
        engine = BacktestingEngine()
        print("✅ 回测引擎创建成功")
        
        # 设置基本参数
        engine.set_parameters(
            vt_symbol="au2312.SHFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            rate=0.0002,
            slippage=0.2,
            size=1000,
            pricetick=0.02,
            capital=1000000
        )
        print("✅ 回测参数设置成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 回测测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 vnpy导入路径检测工具")
    print("=" * 50)
    
    # 检查包结构
    if not check_vnpy_structure():
        print("\n❌ vnpy包结构检查失败")
        return
    
    # 测试导入
    backtesting_imports = test_backtesting_imports()
    template_imports = test_template_imports()
    
    # 生成可用代码
    working_code = generate_working_imports(backtesting_imports, template_imports)
    
    # 测试回测功能
    if working_code:
        test_simple_backtest()
    
    print("\n" + "=" * 50)
    print("🎯 检测完成")
    
    if backtesting_imports and template_imports:
        print("✅ 找到可用的导入路径")
        print("💡 现在可以运行回测系统了")
    else:
        print("❌ 未找到可用的导入路径")
        print("🔧 建议:")
        print("1. 重新安装: pip uninstall vnpy_ctastrategy && pip install vnpy_ctastrategy")
        print("2. 或者安装vnpy核心: pip install vnpy[cta]")

if __name__ == "__main__":
    main()
