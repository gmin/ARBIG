#!/usr/bin/env python3
"""
策略引擎诊断脚本
检查策略引擎加载策略的问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_strategy_engine_loading():
    """测试策略引擎加载"""
    print("🔍 策略引擎加载诊断")
    print("=" * 50)
    
    try:
        from services.strategy_service.core.strategy_engine import StrategyEngine
        from services.strategy_service.core.cta_template import ARBIGCtaTemplate
        
        print("✅ 策略引擎和模板导入成功")
        
        # 创建策略引擎实例
        engine = StrategyEngine()
        
        print(f"✅ 策略引擎创建成功")
        print(f"📊 加载的策略类数量: {len(engine.strategy_classes)}")
        
        if engine.strategy_classes:
            print("📋 加载的策略类:")
            for name, cls in engine.strategy_classes.items():
                print(f"  - {name}: {cls}")
        else:
            print("❌ 没有加载任何策略类")
            
        return engine
        
    except Exception as e:
        print(f"❌ 策略引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_strategy_imports():
    """测试单个策略文件导入"""
    print("\n🧪 单个策略文件导入测试")
    print("=" * 50)
    
    strategies_dir = Path("services/strategy_service/strategies")
    strategy_files = [f for f in strategies_dir.glob("*.py") if not f.name.startswith("__")]
    
    # 添加策略目录到路径
    sys.path.insert(0, str(strategies_dir))
    
    successful_imports = []
    failed_imports = []
    
    for strategy_file in strategy_files:
        module_name = strategy_file.stem
        print(f"\n📋 测试: {strategy_file.name}")
        
        try:
            # 动态导入模块
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            if spec is None or spec.loader is None:
                print(f"  ❌ 无法创建模块规格")
                failed_imports.append((strategy_file.name, "无法创建模块规格"))
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            print(f"  ✅ 模块导入成功")
            
            # 查找策略类
            from services.strategy_service.core.cta_template import ARBIGCtaTemplate
            
            strategy_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                if (isinstance(attr, type) and 
                    issubclass(attr, ARBIGCtaTemplate) and 
                    attr != ARBIGCtaTemplate):
                    strategy_classes.append(attr_name)
            
            if strategy_classes:
                print(f"  ✅ 找到策略类: {strategy_classes}")
                successful_imports.append((strategy_file.name, strategy_classes))
            else:
                print(f"  ⚠️ 未找到继承ARBIGCtaTemplate的策略类")
                
                # 检查所有类
                all_classes = []
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and not attr_name.startswith('_'):
                        all_classes.append(attr_name)
                
                print(f"  📝 模块中的所有类: {all_classes}")
                failed_imports.append((strategy_file.name, "未找到有效策略类"))
                
        except Exception as e:
            print(f"  ❌ 导入失败: {e}")
            failed_imports.append((strategy_file.name, str(e)))
    
    print(f"\n📊 导入结果:")
    print(f"✅ 成功: {len(successful_imports)} 个")
    print(f"❌ 失败: {len(failed_imports)} 个")
    
    if failed_imports:
        print(f"\n❌ 失败的策略:")
        for filename, error in failed_imports:
            print(f"  - {filename}: {error}")
    
    return successful_imports, failed_imports

def test_arbig_template_inheritance():
    """测试ARBIGCtaTemplate继承"""
    print("\n🔧 测试ARBIGCtaTemplate继承")
    print("=" * 50)
    
    try:
        from services.strategy_service.core.cta_template import ARBIGCtaTemplate
        print(f"✅ ARBIGCtaTemplate导入成功: {ARBIGCtaTemplate}")
        print(f"📝 基类: {ARBIGCtaTemplate.__bases__}")
        
        # 测试一个具体的策略类
        try:
            from services.strategy_service.strategies.double_ma_strategy import DoubleMaStrategy
            print(f"✅ DoubleMaStrategy导入成功: {DoubleMaStrategy}")
            print(f"📝 基类: {DoubleMaStrategy.__bases__}")
            print(f"🔗 是否继承ARBIGCtaTemplate: {issubclass(DoubleMaStrategy, ARBIGCtaTemplate)}")
            
            return True
        except Exception as e:
            print(f"❌ DoubleMaStrategy导入失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ ARBIGCtaTemplate导入失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 策略引擎诊断工具")
    print("=" * 60)
    
    # 1. 测试ARBIGCtaTemplate继承
    template_ok = test_arbig_template_inheritance()
    
    # 2. 测试单个策略导入
    successful_imports, failed_imports = test_individual_strategy_imports()
    
    # 3. 测试策略引擎加载
    engine = test_strategy_engine_loading()
    
    # 4. 总结和建议
    print("\n" + "=" * 60)
    print("🎯 诊断总结")
    print("=" * 60)
    
    if not template_ok:
        print("❌ ARBIGCtaTemplate导入有问题")
        print("建议: 检查core.cta_template模块")
    
    if failed_imports:
        print(f"❌ {len(failed_imports)} 个策略文件有问题")
        print("建议: 检查这些文件的导入路径和类定义")
    
    if engine and len(engine.strategy_classes) == 0:
        print("❌ 策略引擎没有加载任何策略")
        print("建议: 检查策略引擎的加载逻辑")
    elif engine:
        print(f"✅ 策略引擎成功加载 {len(engine.strategy_classes)} 个策略")
    
    expected_count = len([f for f in Path("services/strategy_service/strategies").glob("*.py") if not f.name.startswith("__")])
    actual_count = len(engine.strategy_classes) if engine else 0
    
    print(f"\n📊 最终结果:")
    print(f"期望策略数: {expected_count}")
    print(f"实际加载数: {actual_count}")
    
    if actual_count == expected_count:
        print("🎉 所有策略都成功加载!")
    else:
        print("⚠️ 策略加载不完整，需要修复")

if __name__ == "__main__":
    main()
