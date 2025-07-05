#!/usr/bin/env python3
"""
ARBIG前端测试脚本
测试前端界面和API集成
"""

import sys
import time
import subprocess
import threading
import requests
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_backend():
    """启动后端服务"""
    print("🔧 启动后端服务...")
    try:
        # 启动main.py服务容器
        subprocess.Popen([
            sys.executable, "main.py", "--auto-start"
        ], cwd=project_root)
        
        # 等待后端启动
        time.sleep(5)
        
        # 检查后端是否启动成功
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✓ 后端服务启动成功")
                return True
            else:
                print(f"✗ 后端服务启动失败: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("✗ 无法连接到后端服务")
            return False
            
    except Exception as e:
        print(f"✗ 启动后端服务失败: {e}")
        return False

def test_api_endpoints():
    """测试API端点"""
    print("\n🧪 测试API端点...")
    
    endpoints = [
        ("GET", "/health", "健康检查"),
        ("GET", "/api/v1/system/status", "系统状态"),
        ("GET", "/api/v1/services/list", "服务列表"),
        ("GET", "/api/v1/strategies/list", "策略列表"),
        ("GET", "/api/v1/data/symbols", "合约列表"),
    ]
    
    success_count = 0
    
    for method, endpoint, description in endpoints:
        try:
            url = f"http://localhost:8000{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✓ {description}: {response.status_code}")
                success_count += 1
            else:
                print(f"✗ {description}: {response.status_code}")
                
        except Exception as e:
            print(f"✗ {description}: {e}")
    
    print(f"\nAPI测试结果: {success_count}/{len(endpoints)} 成功")
    return success_count == len(endpoints)

def check_frontend_files():
    """检查前端文件"""
    print("\n📁 检查前端文件...")
    
    frontend_dir = project_root / "web_monitor" / "frontend"
    required_files = [
        "package.json",
        "vite.config.ts",
        "tsconfig.json",
        "index.html",
        "src/main.ts",
        "src/App.vue",
        "src/views/Layout.vue",
        "src/views/Dashboard.vue",
        "src/router/index.ts",
        "src/stores/system.ts",
        "src/api/client.ts",
        "src/api/services.ts",
        "src/types/api.ts",
        "src/styles/global.scss"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = frontend_dir / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ 缺少 {len(missing_files)} 个文件")
        return False
    else:
        print(f"\n✅ 所有前端文件都存在")
        return True

def start_frontend():
    """启动前端开发服务器"""
    print("\n🎨 启动前端开发服务器...")
    
    frontend_dir = project_root / "web_monitor" / "frontend"
    
    try:
        # 检查Node.js
        subprocess.run(["node", "--version"], check=True, capture_output=True)
        print("✓ Node.js已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js未安装，请先安装Node.js")
        return False
    
    try:
        # 检查npm
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
        print("✓ npm已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm未安装，请先安装npm")
        return False
    
    print("\n📦 安装前端依赖...")
    print("这可能需要几分钟时间...")
    
    try:
        # 安装依赖
        result = subprocess.run(
            ["npm", "install"], 
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print("✓ 前端依赖安装成功")
        else:
            print(f"✗ 前端依赖安装失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 前端依赖安装超时")
        return False
    except Exception as e:
        print(f"✗ 前端依赖安装异常: {e}")
        return False
    
    print("\n🚀 启动前端开发服务器...")
    print("前端地址: http://localhost:3000")
    print("按 Ctrl+C 停止服务器")
    
    try:
        # 启动开发服务器
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)
        return True
    except KeyboardInterrupt:
        print("\n👋 前端开发服务器已停止")
        return True
    except Exception as e:
        print(f"✗ 启动前端开发服务器失败: {e}")
        return False

def main():
    """主函数"""
    print("🎨 ARBIG前端完整测试")
    print("=" * 60)
    
    # 检查前端文件
    if not check_frontend_files():
        print("\n❌ 前端文件检查失败，请检查文件完整性")
        return
    
    # 启动后端服务
    if not start_backend():
        print("\n❌ 后端服务启动失败")
        return
    
    # 测试API端点
    if not test_api_endpoints():
        print("\n⚠️ 部分API测试失败，但可以继续测试前端")
    
    print("\n" + "=" * 60)
    print("🎯 前端测试准备完成！")
    print("\n📋 测试步骤:")
    print("1. 后端服务已启动: http://localhost:8000")
    print("2. API端点已测试")
    print("3. 前端文件已检查")
    print("4. 即将启动前端开发服务器")
    print("\n🌐 访问地址:")
    print("- 前端界面: http://localhost:3000")
    print("- API文档: http://localhost:8000/api/docs")
    print("- 系统状态: http://localhost:8000/api/v1/system/status")
    
    input("\n按回车键启动前端开发服务器...")
    
    # 启动前端
    start_frontend()

if __name__ == "__main__":
    main()
