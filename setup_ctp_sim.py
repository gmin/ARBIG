#!/usr/bin/env python3
"""
CTP仿真环境自动配置脚本
"""

import os
import shutil
import sys
from pathlib import Path

def setup_ctp_sim_environment():
    """
    设置CTP仿真环境
    """
    print("=" * 60)
    print("CTP仿真环境自动配置脚本")
    print("=" * 60)
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前工作目录: {current_dir}")
    
    # 创建必要的目录
    libs_dir = current_dir / "libs" / "ctp_sim"
    config_dir = current_dir / "config"
    
    print(f"\n创建目录结构...")
    libs_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(exist_ok=True)
    print(f"✓ 目录创建完成")
    
    # 检查API库文件
    print(f"\n检查CTP仿真API库文件...")
    required_files = ["thosttraderapi_se.so", "thostmduserapi_se.so"]
    missing_files = []
    
    for file in required_files:
        file_path = libs_dir / file
        if not file_path.exists():
            missing_files.append(file)
        else:
            print(f"✓ 找到文件: {file}")
    
    if missing_files:
        print(f"\n⚠ 缺少以下API库文件:")
        for file in missing_files:
            print(f"  - {file}")
        print(f"\n请将CTP仿真API库文件放到以下目录:")
        print(f"  {libs_dir}")
        print(f"\n然后重新运行此脚本")
        return False
    
    # 设置文件权限
    print(f"\n设置文件权限...")
    for file in required_files:
        file_path = libs_dir / file
        file_path.chmod(0o755)
        print(f"✓ 设置权限: {file}")
    
    # 检查配置文件
    config_file = config_dir / "ctp_sim.json"
    if not config_file.exists():
        print(f"\n创建CTP仿真配置文件...")
        create_ctp_config(config_file)
        print(f"✓ 配置文件创建完成: {config_file}")
    else:
        print(f"✓ 配置文件已存在: {config_file}")
    
    # 检查Python依赖
    print(f"\n检查Python依赖...")
    check_python_dependencies()
    
    print(f"\n" + "=" * 60)
    print("CTP仿真环境配置完成！")
    print("=" * 60)
    print(f"\n下一步操作:")
    print(f"1. 运行测试脚本验证配置:")
    print(f"   python test_ctp_sim.py")
    print(f"2. 查看配置文档:")
    print(f"   cat CTP_SIM_SETUP.md")
    print(f"3. 开始使用CTP仿真环境进行开发")
    
    return True

def create_ctp_config(config_file):
    """
    创建CTP仿真配置文件
    """
    config_content = '''{
    "用户名": "242407",
    "密码": "1234%^&*QWE",
    "经纪商代码": "9999",
    "交易服务器": "180.168.146.187:10101",
    "行情服务器": "180.168.146.187:10102",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "产品信息": "simnow_client_test"
}'''
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)

def check_python_dependencies():
    """
    检查Python依赖
    """
    required_packages = [
        'vnpy',
        'vnpy_ctp',
        'pandas',
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (未安装)")
    
    if missing_packages:
        print(f"\n⚠ 缺少以下Python包:")
        for package in missing_packages:
            print(f"  - {package}")
        print(f"\n请安装缺少的依赖:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """
    主函数
    """
    try:
        success = setup_ctp_sim_environment()
        if success:
            print(f"\n配置成功完成！")
            sys.exit(0)
        else:
            print(f"\n配置未完成，请检查上述信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n配置被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n配置过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 