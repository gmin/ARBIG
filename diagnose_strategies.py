#!/usr/bin/env python3
"""
策略加载诊断脚本
检查所有策略文件的导入和类名问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def diagnose_strategy_files():
    """诊断策略文件"""
    print("🔍 策略文件诊断")
    print("=" * 60)
    
    # 策略目录
    strategies_dir = Path("services/strategy_service/strategies")
    
    if not strategies_dir.exists():
        print(f"❌ 策略目录不存在: {strategies_dir}")
        return
    
    # 获取所有Python文件
    strategy_files = list(strategies_dir.glob("*.py"))
    strategy_files = [f for f in strategy_files if not f.name.startswith("__")]
    
    print(f"📁 找到 {len(strategy_files)} 个策略文件:")
    for f in strategy_files:
        print(f"  - {f.name}")
    
    print("\n🧪 逐个测试策略文件导入:")
    print("-" * 60)
    
    # 添加策略目录到路径
    sys.path.insert(0, str(strategies_dir))
    
    successful_imports = []
    failed_imports = []
    
    for strategy_file in strategy_files:
        module_name = strategy_file.stem  # 文件名不含扩展名
        print(f"\n📋 测试: {strategy_file.name}")
        
        try:
            # 尝试导入模块
            module = __import__(module_name)
            print(f"  ✅ 模块导入成功")
            
            # 查找策略类
            strategy_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    attr_name.endswith('Strategy') and 
                    attr_name != 'ARBIGCtaTemplate'):
                    strategy_classes.append(attr_name)
            
            if strategy_classes:
                print(f"  ✅ 找到策略类: {strategy_classes}")
                successful_imports.append({
                    "file": strategy_file.name,
                    "module": module_name,
                    "classes": strategy_classes
                })
            else:
                print(f"  ⚠️ 未找到策略类")
                failed_imports.append({
                    "file": strategy_file.name,
                    "module": module_name,
                    "error": "未找到策略类"
                })
                
        except ImportError as e:
            print(f"  ❌ 导入失败: {e}")
            failed_imports.append({
                "file": strategy_file.name,
                "module": module_name,
                "error": str(e)
            })
        except Exception as e:
            print(f"  ❌ 其他错误: {e}")
            failed_imports.append({
                "file": strategy_file.name,
                "module": module_name,
                "error": str(e)
            })
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 诊断结果总结")
    print("=" * 60)
    
    print(f"✅ 成功导入: {len(successful_imports)} 个")
    for item in successful_imports:
        print(f"  - {item['file']}: {item['classes']}")
    
    print(f"\n❌ 导入失败: {len(failed_imports)} 个")
    for item in failed_imports:
        print(f"  - {item['file']}: {item['error']}")
    
    return successful_imports, failed_imports

def test_strategy_adapter():
    """测试策略适配器"""
    print("\n🔧 测试策略适配器")
    print("=" * 60)
    
    try:
        from services.strategy_service.backtesting.strategy_adapter import get_adapted_strategies
        
        print("📋 调用get_adapted_strategies()...")
        adapted_strategies = get_adapted_strategies()
        
        print(f"✅ 适配器返回 {len(adapted_strategies)} 个策略:")
        for name, strategy_class in adapted_strategies.items():
            print(f"  - {name}: {strategy_class.__name__}")
        
        return adapted_strategies
        
    except Exception as e:
        print(f"❌ 策略适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_correct_mapping(successful_imports):
    """生成正确的策略映射"""
    print("\n📝 生成正确的策略映射")
    print("=" * 60)
    
    mapping_code = """
        strategy_mappings = {"""
    
    for item in successful_imports:
        file_name = item['file']
        classes = item['classes']
        
        if classes:
            class_name = classes[0]  # 取第一个策略类
            display_name = class_name.replace('Strategy', '').replace('SHFE', 'SHFE')
            
            mapping_code += f"""
            "{file_name}": {{
                "class_name": "{class_name}",
                "display_name": "{display_name}",
                "description": "{class_name}策略"
            }},"""
    
    mapping_code += """
        }"""
    
    print("建议的策略映射代码:")
    print(mapping_code)
    
    return mapping_code

def main():
    """主函数"""
    print("🎯 ARBIG策略加载诊断工具")
    print("=" * 60)
    
    # 1. 诊断策略文件
    successful_imports, failed_imports = diagnose_strategy_files()
    
    # 2. 测试策略适配器
    adapted_strategies = test_strategy_adapter()
    
    # 3. 生成正确映射
    if successful_imports:
        generate_correct_mapping(successful_imports)
    
    # 4. 给出修复建议
    print("\n🔧 修复建议")
    print("=" * 60)
    
    if len(successful_imports) > len(adapted_strategies):
        print("⚠️ 有策略文件可以导入但未被适配器加载")
        print("建议:")
        print("1. 检查strategy_adapter.py中的strategy_mappings")
        print("2. 确保文件名和类名匹配")
        print("3. 使用上面生成的映射代码")
    
    if failed_imports:
        print("⚠️ 有策略文件导入失败")
        print("建议:")
        print("1. 检查导入路径问题")
        print("2. 检查依赖模块是否存在")
        print("3. 修复语法错误")
    
    print(f"\n🎯 期望结果: 应该加载 {len(successful_imports)} 个策略")
    print(f"🎯 实际结果: 当前加载 {len(adapted_strategies)} 个策略")

if __name__ == "__main__":
    main()
