#!/usr/bin/env python3
"""
测试文件导入路径验证脚本
检查迁移后的测试文件是否能正确导入项目模块
"""

import os
import sys
import ast
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple

class ImportValidator:
    """导入路径验证器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_root = Path(__file__).parent
        self.validation_results = {}
        
    def find_test_files(self) -> List[Path]:
        """查找所有测试文件"""
        test_files = []
        for root, dirs, files in os.walk(self.tests_root):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    test_files.append(Path(root) / file)
                elif file in ['simple_system_test.py', 'test_strategy_management.py', 'test_non_trading_functions.py']:
                    test_files.append(Path(root) / file)
        
        return sorted(test_files)
    
    def extract_imports(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """提取文件中的导入语句"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            from_imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        from_imports.append(f"{module}.{alias.name}" if module else alias.name)
            
            return imports, from_imports
            
        except Exception as e:
            return [], []
    
    def check_sys_path_modifications(self, file_path: Path) -> List[str]:
        """检查文件中的sys.path修改"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            path_modifications = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                if 'sys.path' in line and ('append' in line or 'insert' in line):
                    path_modifications.append(f"Line {i}: {line.strip()}")
            
            return path_modifications
            
        except Exception as e:
            return [f"Error reading file: {e}"]
    
    def validate_project_imports(self, file_path: Path) -> Dict[str, bool]:
        """验证项目内部模块的导入"""
        imports, from_imports = self.extract_imports(file_path)
        all_imports = imports + from_imports
        
        # 项目内部模块
        project_modules = [
            'core', 'utils', 'shared', 'services',
            'core.types', 'utils.logger', 'shared.database'
        ]
        
        validation_results = {}
        
        for imp in all_imports:
            for proj_mod in project_modules:
                if imp.startswith(proj_mod):
                    # 尝试导入验证
                    try:
                        # 临时添加项目根目录到路径
                        old_path = sys.path[:]
                        sys.path.insert(0, str(self.project_root))
                        
                        module_parts = imp.split('.')
                        module_path = self.project_root
                        
                        for part in module_parts:
                            module_path = module_path / part
                            if module_path.with_suffix('.py').exists():
                                validation_results[imp] = True
                                break
                            elif module_path.is_dir() and (module_path / '__init__.py').exists():
                                continue
                            else:
                                validation_results[imp] = False
                                break
                        else:
                            validation_results[imp] = False
                        
                        # 恢复路径
                        sys.path[:] = old_path
                        
                    except Exception as e:
                        validation_results[imp] = False
        
        return validation_results
    
    def test_file_execution(self, file_path: Path) -> Dict[str, any]:
        """测试文件是否能正常导入执行"""
        result = {
            'can_import': False,
            'import_error': None,
            'syntax_valid': False,
            'syntax_error': None
        }
        
        try:
            # 检查语法
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast.parse(content)
            result['syntax_valid'] = True
            
            # 尝试导入模块
            spec = importlib.util.spec_from_file_location("test_module", file_path)
            if spec and spec.loader:
                # 临时添加项目根目录到路径
                old_path = sys.path[:]
                sys.path.insert(0, str(self.project_root))
                
                try:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    result['can_import'] = True
                except Exception as e:
                    result['import_error'] = str(e)
                finally:
                    sys.path[:] = old_path
            
        except SyntaxError as e:
            result['syntax_error'] = str(e)
        except Exception as e:
            result['import_error'] = str(e)
        
        return result
    
    def validate_file(self, file_path: Path) -> Dict[str, any]:
        """验证单个测试文件"""
        relative_path = file_path.relative_to(self.tests_root)
        
        print(f"\n🔍 验证文件: {relative_path}")
        
        result = {
            'file_path': str(relative_path),
            'exists': file_path.exists(),
            'sys_path_mods': [],
            'project_imports': {},
            'execution_test': {}
        }
        
        if not file_path.exists():
            print(f"   ❌ 文件不存在")
            return result
        
        # 检查sys.path修改
        path_mods = self.check_sys_path_modifications(file_path)
        result['sys_path_mods'] = path_mods
        
        if path_mods:
            print(f"   📝 发现sys.path修改:")
            for mod in path_mods:
                print(f"      {mod}")
        else:
            print(f"   ⚠️  未发现sys.path修改")
        
        # 验证项目导入
        project_imports = self.validate_project_imports(file_path)
        result['project_imports'] = project_imports
        
        if project_imports:
            print(f"   📦 项目模块导入:")
            for imp, valid in project_imports.items():
                status = "✅" if valid else "❌"
                print(f"      {status} {imp}")
        else:
            print(f"   ℹ️  无项目模块导入")
        
        # 测试执行
        exec_result = self.test_file_execution(file_path)
        result['execution_test'] = exec_result
        
        if exec_result['syntax_valid']:
            if exec_result['can_import']:
                print(f"   ✅ 文件可正常导入执行")
            else:
                print(f"   ❌ 导入执行失败: {exec_result['import_error']}")
        else:
            print(f"   ❌ 语法错误: {exec_result['syntax_error']}")
        
        return result
    
    def run_validation(self):
        """运行完整验证"""
        print("🚀 开始验证测试文件导入路径")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"📁 测试根目录: {self.tests_root}")
        print("=" * 60)
        
        test_files = self.find_test_files()
        print(f"📋 发现 {len(test_files)} 个测试文件")
        
        all_results = []
        success_count = 0
        
        for test_file in test_files:
            result = self.validate_file(test_file)
            all_results.append(result)
            
            # 判断是否成功
            has_syntax_error = not result['execution_test'].get('syntax_valid', False)
            has_import_error = not result['execution_test'].get('can_import', False)
            has_failed_imports = any(not v for v in result['project_imports'].values())
            
            if not (has_syntax_error or has_import_error or has_failed_imports):
                success_count += 1
        
        # 生成总结报告
        print("\n" + "=" * 60)
        print("📊 验证总结")
        
        success_rate = (success_count / len(test_files) * 100) if test_files else 0
        print(f"✅ 成功: {success_count}/{len(test_files)} ({success_rate:.1f}%)")
        
        # 详细问题报告
        problem_files = []
        for result in all_results:
            has_problems = False
            problems = []
            
            if not result['execution_test'].get('syntax_valid', False):
                problems.append("语法错误")
                has_problems = True
            
            if not result['execution_test'].get('can_import', False):
                problems.append("导入失败")
                has_problems = True
            
            if any(not v for v in result['project_imports'].values()):
                problems.append("项目模块导入失败")
                has_problems = True
            
            if not result['sys_path_mods']:
                problems.append("缺少sys.path设置")
                has_problems = True
            
            if has_problems:
                problem_files.append((result['file_path'], problems))
        
        if problem_files:
            print(f"\n⚠️  发现问题的文件:")
            for file_path, problems in problem_files:
                print(f"   ❌ {file_path}: {', '.join(problems)}")
        
        # 建议修复方案
        if problem_files:
            print(f"\n💡 修复建议:")
            print(f"   1. 确保每个测试文件都有正确的sys.path设置")
            print(f"   2. 检查项目模块的导入路径")
            print(f"   3. 验证文件语法正确性")
            print(f"   4. 测试文件能否在新位置正常运行")
        
        # 保存详细结果
        self.save_validation_results(all_results)
        
        return success_rate >= 80
    
    def save_validation_results(self, results: List[Dict]):
        """保存验证结果"""
        try:
            import json
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = self.project_root / "logs" / f"import_validation_{timestamp}.json"
            
            # 确保logs目录存在
            results_file.parent.mkdir(exist_ok=True)
            
            validation_data = {
                "timestamp": timestamp,
                "project_root": str(self.project_root),
                "tests_root": str(self.tests_root),
                "total_files": len(results),
                "results": results
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(validation_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 详细验证结果已保存到: {results_file}")
            
        except Exception as e:
            print(f"\n❌ 保存验证结果失败: {e}")

def main():
    """主函数"""
    validator = ImportValidator()
    success = validator.run_validation()
    
    if success:
        print(f"\n🎉 导入路径验证通过！")
        return 0
    else:
        print(f"\n❌ 导入路径验证失败，请修复相关问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())
