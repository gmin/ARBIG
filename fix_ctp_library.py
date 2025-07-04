#!/usr/bin/env python3
"""
修复CTP库加载问题
解决locale::fac错误和库路径问题
"""

import os
import sys
import shutil
from pathlib import Path

def fix_ctp_library_issues():
    """
    修复CTP库加载问题
    """
    print("=" * 60)
    print("修复CTP库加载问题")
    print("=" * 60)
    
    # 获取项目根目录
    project_root = Path.cwd()
    print(f"项目根目录: {project_root}")
    
    # 1. 设置环境变量
    print("\n1. 设置环境变量...")
    
    # 设置LD_LIBRARY_PATH
    ctp_lib_path = project_root / "libs" / "ctp_sim"
    current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    
    if str(ctp_lib_path) not in current_ld_path:
        if current_ld_path:
            new_ld_path = f"{ctp_lib_path}:{current_ld_path}"
        else:
            new_ld_path = str(ctp_lib_path)
        
        os.environ['LD_LIBRARY_PATH'] = new_ld_path
        print(f"✓ 设置LD_LIBRARY_PATH: {new_ld_path}")
    else:
        print(f"✓ LD_LIBRARY_PATH已包含CTP库路径")
    
    # 设置PYTHONPATH
    current_python_path = os.environ.get('PYTHONPATH', '')
    if str(ctp_lib_path) not in current_python_path:
        if current_python_path:
            new_python_path = f"{ctp_lib_path}:{current_python_path}"
        else:
            new_python_path = str(ctp_lib_path)
        
        os.environ['PYTHONPATH'] = new_python_path
        print(f"✓ 设置PYTHONPATH: {new_python_path}")
    else:
        print(f"✓ PYTHONPATH已包含CTP库路径")
    
    # 2. 检查库文件
    print("\n2. 检查CTP库文件...")
    required_files = ["thosttraderapi_se.so", "thostmduserapi_se.so"]
    
    for file in required_files:
        file_path = ctp_lib_path / file
        if file_path.exists():
            # 设置执行权限
            file_path.chmod(0o755)
            print(f"✓ 找到并设置权限: {file}")
        else:
            print(f"✗ 缺少文件: {file}")
            return False
    
    # 3. 创建软链接（如果需要）
    print("\n3. 创建软链接...")
    old_ctp_path = project_root / "libs" / "ctp"
    
    if not old_ctp_path.exists():
        old_ctp_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {old_ctp_path}")
    
    # 为每个库文件创建软链接
    for file in required_files:
        source_file = ctp_lib_path / file
        link_file = old_ctp_path / file
        
        if link_file.exists():
            link_file.unlink()  # 删除现有链接
        
        try:
            link_file.symlink_to(source_file)
            print(f"✓ 创建软链接: {link_file} -> {source_file}")
        except Exception as e:
            print(f"⚠ 创建软链接失败: {e}")
            # 尝试复制文件
            try:
                shutil.copy2(source_file, link_file)
                print(f"✓ 复制文件: {source_file} -> {link_file}")
            except Exception as e2:
                print(f"✗ 复制文件也失败: {e2}")
    
    # 4. 检查系统依赖
    print("\n4. 检查系统依赖...")
    
    # 检查locale设置
    try:
        import locale
        current_locale = locale.getlocale()
        print(f"✓ 当前locale设置: {current_locale}")
        
        # 尝试设置locale
        try:
            locale.setlocale(locale.LC_ALL, 'C.utf8')
            print("✓ 设置locale为C.utf8")
        except:
            try:
                locale.setlocale(locale.LC_ALL, 'en_US.utf8')
                print("✓ 设置locale为en_US.utf8")
            except:
                print("⚠ 无法设置locale，使用系统默认")
                
    except Exception as e:
        print(f"⚠ locale检查失败: {e}")
    
    # 5. 测试库加载
    print("\n5. 测试CTP库加载...")
    
    try:
        # 添加库路径到sys.path
        if str(ctp_lib_path) not in sys.path:
            sys.path.insert(0, str(ctp_lib_path))
        
        # 尝试导入vnpy_ctp
        import vnpy_ctp
        print("✓ vnpy_ctp导入成功")
        
        # 尝试创建CtpGateway实例
        from vnpy.event import EventEngine
        event_engine = EventEngine()
        gateway = vnpy_ctp.CtpGateway(event_engine, "CTP_SIM")
        print("✓ CtpGateway创建成功")
        
        return True
        
    except Exception as e:
        print(f"✗ CTP库加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_environment_script():
    """
    创建环境设置脚本
    """
    print("\n6. 创建环境设置脚本...")
    
    script_content = '''#!/bin/bash
# CTP环境设置脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 设置CTP库路径
export LD_LIBRARY_PATH="$PROJECT_ROOT/libs/ctp_sim:$LD_LIBRARY_PATH"
export PYTHONPATH="$PROJECT_ROOT/libs/ctp_sim:$PYTHONPATH"

# 设置locale
export LC_ALL=C.UTF-8

echo "CTP环境设置完成"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo "PYTHONPATH: $PYTHONPATH"
echo "LC_ALL: $LC_ALL"
'''
    
    script_path = Path("setup_ctp_env.sh")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    script_path.chmod(0o755)
    print(f"✓ 创建环境设置脚本: {script_path}")

def main():
    """
    主函数
    """
    try:
        success = fix_ctp_library_issues()
        
        if success:
            create_environment_script()
            print("\n" + "=" * 60)
            print("修复完成！")
            print("=" * 60)
            print("\n使用方法:")
            print("1. 运行环境设置脚本:")
            print("   source setup_ctp_env.sh")
            print("2. 然后运行你的CTP程序")
            print("\n或者直接在Python中设置环境变量后运行")
        else:
            print("\n修复失败，请检查上述错误信息")
            
    except Exception as e:
        print(f"\n修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 