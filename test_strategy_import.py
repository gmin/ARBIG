#!/usr/bin/env python3
"""
测试策略导入
单独测试策略文件的导入问题
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_strategy_imports():
    """测试策略导入"""
    print("🧪 测试策略文件导入...")
    
    # 添加策略目录到路径
    strategies_dir = os.path.join(os.path.dirname(__file__), 'services', 'strategy_service', 'strategies')
    if strategies_dir not in sys.path:
        sys.path.insert(0, strategies_dir)
    
    print(f"策略目录: {strategies_dir}")
    print(f"目录存在: {os.path.exists(strategies_dir)}")
    
    # 列出策略文件
    if os.path.exists(strategies_dir):
        files = [f for f in os.listdir(strategies_dir) if f.endswith('.py') and not f.startswith('__')]
        print(f"策略文件: {files}")
    
    # 测试导入各个策略
    strategies_to_test = [
        ("microstructure_strategy", "LargeOrderFollowingStrategy"),
        ("mean_reversion_strategy", "VWAPDeviationReversionStrategy"), 
        ("double_ma_strategy", "DoubleMaStrategy"),
        ("test_strategy", "TestStrategy")
    ]
    
    successful_imports = []
    
    for module_name, class_name in strategies_to_test:
        try:
            print(f"\n📋 测试导入: {module_name}.{class_name}")
            
            # 尝试导入模块
            module = __import__(module_name)
            print(f"  ✅ 模块导入成功: {module}")
            
            # 尝试获取类
            strategy_class = getattr(module, class_name)
            print(f"  ✅ 类获取成功: {strategy_class}")
            
            # 检查基类
            base_classes = [base.__name__ for base in strategy_class.__bases__]
            print(f"  📝 基类: {base_classes}")
            
            successful_imports.append((module_name, class_name, strategy_class))
            
        except ImportError as e:
            print(f"  ❌ 模块导入失败: {e}")
        except AttributeError as e:
            print(f"  ❌ 类获取失败: {e}")
        except Exception as e:
            print(f"  ❌ 其他错误: {e}")
    
    print(f"\n📊 导入结果: {len(successful_imports)}/{len(strategies_to_test)} 成功")
    return successful_imports

def test_cta_template_import():
    """测试ARBIGCtaTemplate导入"""
    print("\n🧪 测试ARBIGCtaTemplate导入...")
    
    try:
        from services.strategy_service.core.cta_template import ARBIGCtaTemplate
        print("✅ ARBIGCtaTemplate导入成功")
        print(f"   类: {ARBIGCtaTemplate}")
        print(f"   基类: {[base.__name__ for base in ARBIGCtaTemplate.__bases__]}")
        return True
    except ImportError as e:
        print(f"❌ ARBIGCtaTemplate导入失败: {e}")
        return False

def test_vnpy_compatibility():
    """测试vnpy兼容性"""
    print("\n🧪 测试vnpy兼容性...")
    
    try:
        from vnpy_ctastrategy.template import CtaTemplate
        print("✅ vnpy CtaTemplate导入成功")
        
        from services.strategy_service.core.cta_template import ARBIGCtaTemplate
        print("✅ ARBIG CtaTemplate导入成功")
        
        # 检查是否兼容
        print(f"ARBIGCtaTemplate基类: {ARBIGCtaTemplate.__bases__}")
        
        return True
    except ImportError as e:
        print(f"❌ vnpy兼容性测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 策略导入测试工具")
    print("=" * 50)
    
    # 测试ARBIGCtaTemplate导入
    cta_template_ok = test_cta_template_import()
    
    # 测试vnpy兼容性
    vnpy_ok = test_vnpy_compatibility()
    
    # 测试策略导入
    successful_strategies = test_strategy_imports()
    
    print("\n" + "=" * 50)
    print("📊 测试总结:")
    print(f"ARBIGCtaTemplate: {'✅' if cta_template_ok else '❌'}")
    print(f"vnpy兼容性: {'✅' if vnpy_ok else '❌'}")
    print(f"策略导入: {len(successful_strategies)} 个成功")
    
    if successful_strategies:
        print("\n✅ 成功导入的策略:")
        for module_name, class_name, strategy_class in successful_strategies:
            print(f"  - {class_name} ({module_name})")
    
    if len(successful_strategies) > 0:
        print("\n🎉 策略导入基本正常，可以继续测试回测功能")
    else:
        print("\n⚠️ 策略导入有问题，需要进一步排查")

if __name__ == "__main__":
    main()
