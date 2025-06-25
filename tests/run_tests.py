#!/usr/bin/env python3
"""
测试运行脚本
统一运行所有测试或指定测试
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_test(test_file):
    """
    运行单个测试文件
    
    Args:
        test_file: 测试文件路径
    """
    print(f"\n{'='*60}")
    print(f"运行测试: {test_file}")
    print(f"{'='*60}")
    
    try:
        # 在项目根目录下运行测试
        project_root = Path(__file__).parent.parent
        test_path = project_root / "tests" / test_file
        
        if not test_path.exists():
            print(f"❌ 测试文件不存在: {test_path}")
            return False
            
        # 切换到项目根目录运行测试
        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=project_root,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ 测试通过: {test_file}")
            return True
        else:
            print(f"❌ 测试失败: {test_file}")
            return False
            
    except Exception as e:
        print(f"❌ 运行测试时发生错误: {e}")
        return False

def list_tests():
    """
    列出所有可用的测试
    """
    tests_dir = Path(__file__).parent
    test_files = [f.name for f in tests_dir.glob("test_*.py") if f.name != "run_tests.py"]
    
    print("可用的测试文件:")
    for i, test_file in enumerate(test_files, 1):
        print(f"  {i}. {test_file}")
    
    return test_files

def run_all_tests():
    """
    运行所有测试
    """
    test_files = list_tests()
    
    print(f"\n开始运行所有测试...")
    print(f"共找到 {len(test_files)} 个测试文件")
    
    passed = 0
    failed = 0
    
    for test_file in test_files:
        if run_test(test_file):
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"测试结果汇总:")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  总计: {len(test_files)}")
    print(f"{'='*60}")
    
    return failed == 0

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="运行ARBIG项目测试")
    parser.add_argument(
        "--test", "-t",
        help="运行指定的测试文件 (例如: test_ctp_sim.py)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有可用的测试"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="运行所有测试"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
        return
    
    if args.test:
        success = run_test(args.test)
        sys.exit(0 if success else 1)
    
    if args.all:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    
    # 默认运行所有测试
    print("未指定测试选项，运行所有测试...")
    success = run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 