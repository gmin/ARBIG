#!/usr/bin/env python3
"""
ARBIG系统部署脚本
自动化部署和配置ARBIG量化交易系统
"""

import os
import sys
import subprocess
import shutil
import json
import yaml
from pathlib import Path
from typing import Dict, List
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class ARBIGDeployer:
    """ARBIG系统部署器"""
    
    def __init__(self, deployment_config: Dict):
        """
        初始化部署器
        
        Args:
            deployment_config: 部署配置
        """
        self.config = deployment_config
        self.project_root = project_root
        self.deployment_dir = Path(self.config.get('deployment_dir', '/opt/arbig'))
        self.venv_dir = self.deployment_dir / 'venv'
        self.config_dir = self.deployment_dir / 'config'
        self.logs_dir = self.deployment_dir / 'logs'
        self.data_dir = self.deployment_dir / 'data'
        
    def deploy(self) -> bool:
        """执行完整部署"""
        try:
            logger.info("="*60)
            logger.info("🚀 开始部署ARBIG量化交易系统")
            logger.info("="*60)
            
            # 部署步骤
            steps = [
                ("检查系统环境", self._check_system_requirements),
                ("创建部署目录", self._create_directories),
                ("复制项目文件", self._copy_project_files),
                ("创建Python虚拟环境", self._create_virtual_environment),
                ("安装依赖包", self._install_dependencies),
                ("生成配置文件", self._generate_config_files),
                ("设置权限", self._set_permissions),
                ("创建系统服务", self._create_system_services),
                ("验证部署", self._verify_deployment)
            ]
            
            for step_name, step_func in steps:
                logger.info(f"\n📋 {step_name}...")
                if not step_func():
                    logger.error(f"✗ {step_name}失败")
                    return False
                logger.info(f"✓ {step_name}完成")
            
            logger.info("\n🎉 ARBIG系统部署成功！")
            self._print_deployment_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"部署失败: {e}")
            return False
    
    def _check_system_requirements(self) -> bool:
        """检查系统环境要求"""
        try:
            # 检查Python版本
            python_version = sys.version_info
            if python_version < (3, 8):
                logger.error(f"Python版本过低: {python_version}, 需要3.8+")
                return False
            logger.info(f"  Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
            
            # 检查操作系统
            import platform
            os_name = platform.system()
            logger.info(f"  操作系统: {os_name}")
            
            # 检查必要的系统命令
            required_commands = ['pip', 'systemctl'] if os_name == 'Linux' else ['pip']
            for cmd in required_commands:
                if not shutil.which(cmd):
                    logger.error(f"缺少必要命令: {cmd}")
                    return False
            
            # 检查磁盘空间
            disk_usage = shutil.disk_usage(self.deployment_dir.parent)
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1.0:
                logger.error(f"磁盘空间不足: {free_gb:.1f}GB，需要至少1GB")
                return False
            logger.info(f"  可用磁盘空间: {free_gb:.1f}GB")
            
            return True
            
        except Exception as e:
            logger.error(f"系统环境检查失败: {e}")
            return False
    
    def _create_directories(self) -> bool:
        """创建部署目录结构"""
        try:
            directories = [
                self.deployment_dir,
                self.config_dir,
                self.logs_dir,
                self.data_dir,
                self.deployment_dir / 'scripts',
                self.deployment_dir / 'backup'
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"  创建目录: {directory}")
            
            return True
            
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False
    
    def _copy_project_files(self) -> bool:
        """复制项目文件"""
        try:
            # 要复制的目录和文件
            items_to_copy = [
                'core',
                'gateways', 
                'utils',
                'web_monitor',
                'examples',
                'tests',
                'requirements.txt',
                'README.md'
            ]
            
            for item in items_to_copy:
                src = self.project_root / item
                dst = self.deployment_dir / item
                
                if src.is_file():
                    shutil.copy2(src, dst)
                    logger.info(f"  复制文件: {item}")
                elif src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    logger.info(f"  复制目录: {item}")
                else:
                    logger.warning(f"  跳过不存在的项目: {item}")
            
            return True
            
        except Exception as e:
            logger.error(f"复制项目文件失败: {e}")
            return False
    
    def _create_virtual_environment(self) -> bool:
        """创建Python虚拟环境"""
        try:
            # 创建虚拟环境
            cmd = [sys.executable, '-m', 'venv', str(self.venv_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"创建虚拟环境失败: {result.stderr}")
                return False
            
            logger.info(f"  虚拟环境创建于: {self.venv_dir}")
            return True
            
        except Exception as e:
            logger.error(f"创建虚拟环境失败: {e}")
            return False
    
    def _install_dependencies(self) -> bool:
        """安装依赖包"""
        try:
            # 获取pip路径
            pip_path = self.venv_dir / 'bin' / 'pip'
            if not pip_path.exists():
                pip_path = self.venv_dir / 'Scripts' / 'pip.exe'  # Windows
            
            # 升级pip
            cmd = [str(pip_path), 'install', '--upgrade', 'pip']
            subprocess.run(cmd, check=True, capture_output=True)
            
            # 安装项目依赖
            requirements_file = self.deployment_dir / 'requirements.txt'
            if requirements_file.exists():
                cmd = [str(pip_path), 'install', '-r', str(requirements_file)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"安装依赖失败: {result.stderr}")
                    return False
                
                logger.info("  项目依赖安装完成")
            
            # 安装额外的生产环境依赖
            production_packages = [
                'gunicorn',
                'psutil',
                'supervisor'
            ]
            
            for package in production_packages:
                cmd = [str(pip_path), 'install', package]
                subprocess.run(cmd, capture_output=True)
                logger.info(f"  安装生产环境包: {package}")
            
            return True
            
        except Exception as e:
            logger.error(f"安装依赖失败: {e}")
            return False
    
    def _generate_config_files(self) -> bool:
        """生成配置文件"""
        try:
            # 生成主配置文件
            main_config = {
                'system': {
                    'name': 'ARBIG',
                    'version': '1.0.0',
                    'environment': self.config.get('environment', 'production'),
                    'debug': self.config.get('debug', False)
                },
                'logging': {
                    'level': self.config.get('log_level', 'INFO'),
                    'file': str(self.logs_dir / 'arbig.log'),
                    'max_size': '100MB',
                    'backup_count': 10
                },
                'services': {
                    'market_data': {
                        'enabled': True,
                        'symbols': self.config.get('symbols', ['au2509', 'au2512']),
                        'cache_size': 1000
                    },
                    'account': {
                        'enabled': True,
                        'update_interval': 30,
                        'position_sync': True
                    },
                    'trading': {
                        'enabled': True,
                        'order_timeout': 30,
                        'max_orders_per_second': 5
                    },
                    'risk': {
                        'enabled': True,
                        'max_position_ratio': 0.8,
                        'max_daily_loss': 50000,
                        'max_single_order_volume': 10
                    }
                },
                'web_monitor': {
                    'enabled': True,
                    'host': self.config.get('web_host', '0.0.0.0'),
                    'port': self.config.get('web_port', 8000)
                }
            }
            
            config_file = self.config_dir / 'config.yaml'
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(main_config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"  生成主配置文件: {config_file}")
            
            # 生成CTP配置文件模板
            ctp_config_template = {
                "用户名": "YOUR_CTP_USERNAME",
                "密码": "YOUR_CTP_PASSWORD", 
                "经纪商代码": "9999",
                "交易服务器": "180.168.146.187:10130",
                "行情服务器": "180.168.146.187:10131",
                "产品名称": "simnow_client_test",
                "授权编码": "0000000000000000"
            }
            
            ctp_config_file = self.config_dir / 'ctp_config.json'
            with open(ctp_config_file, 'w', encoding='utf-8') as f:
                json.dump(ctp_config_template, f, indent=2, ensure_ascii=False)
            logger.info(f"  生成CTP配置模板: {ctp_config_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"生成配置文件失败: {e}")
            return False
    
    def _set_permissions(self) -> bool:
        """设置文件权限"""
        try:
            import stat
            
            # 设置执行权限
            executable_files = [
                self.deployment_dir / 'web_monitor' / 'run_web_monitor.py',
                self.venv_dir / 'bin' / 'python',
                self.venv_dir / 'bin' / 'pip'
            ]
            
            for file_path in executable_files:
                if file_path.exists():
                    file_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                    logger.info(f"  设置执行权限: {file_path}")
            
            # 设置目录权限
            for directory in [self.logs_dir, self.data_dir, self.config_dir]:
                directory.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            
            return True
            
        except Exception as e:
            logger.error(f"设置权限失败: {e}")
            return False
    
    def _create_system_services(self) -> bool:
        """创建系统服务"""
        try:
            # 创建启动脚本
            start_script = self.deployment_dir / 'scripts' / 'start_arbig.sh'
            start_script_content = f"""#!/bin/bash
# ARBIG系统启动脚本

export ARBIG_HOME={self.deployment_dir}
export PYTHONPATH=$ARBIG_HOME:$PYTHONPATH

cd $ARBIG_HOME

# 启动Web监控服务
{self.venv_dir}/bin/python web_monitor/run_web_monitor.py --mode integrated &

echo "ARBIG系统启动完成"
"""
            
            with open(start_script, 'w') as f:
                f.write(start_script_content)
            start_script.chmod(0o755)
            logger.info(f"  创建启动脚本: {start_script}")
            
            # 创建停止脚本
            stop_script = self.deployment_dir / 'scripts' / 'stop_arbig.sh'
            stop_script_content = """#!/bin/bash
# ARBIG系统停止脚本

pkill -f "run_web_monitor.py"
echo "ARBIG系统已停止"
"""
            
            with open(stop_script, 'w') as f:
                f.write(stop_script_content)
            stop_script.chmod(0o755)
            logger.info(f"  创建停止脚本: {stop_script}")
            
            # 在Linux系统上创建systemd服务
            if sys.platform.startswith('linux'):
                self._create_systemd_service()
            
            return True
            
        except Exception as e:
            logger.error(f"创建系统服务失败: {e}")
            return False
    
    def _create_systemd_service(self):
        """创建systemd服务"""
        try:
            service_content = f"""[Unit]
Description=ARBIG Quantitative Trading System
After=network.target

[Service]
Type=forking
User=arbig
Group=arbig
WorkingDirectory={self.deployment_dir}
ExecStart={self.deployment_dir}/scripts/start_arbig.sh
ExecStop={self.deployment_dir}/scripts/stop_arbig.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            service_file = Path('/etc/systemd/system/arbig.service')
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # 重新加载systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            logger.info("  创建systemd服务: arbig.service")
            
        except Exception as e:
            logger.warning(f"创建systemd服务失败: {e}")
    
    def _verify_deployment(self) -> bool:
        """验证部署"""
        try:
            # 检查关键文件
            critical_files = [
                self.deployment_dir / 'core' / '__init__.py',
                self.deployment_dir / 'web_monitor' / 'app.py',
                self.config_dir / 'config.yaml',
                self.venv_dir / 'bin' / 'python'
            ]
            
            for file_path in critical_files:
                if not file_path.exists():
                    logger.error(f"  关键文件缺失: {file_path}")
                    return False
            
            # 测试Python环境
            python_path = self.venv_dir / 'bin' / 'python'
            cmd = [str(python_path), '-c', 'import core; print("Core module imported successfully")']
            result = subprocess.run(cmd, cwd=self.deployment_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"  Python环境测试失败: {result.stderr}")
                return False
            
            logger.info("  部署验证通过")
            return True
            
        except Exception as e:
            logger.error(f"部署验证失败: {e}")
            return False
    
    def _print_deployment_summary(self):
        """打印部署摘要"""
        logger.info("\n" + "="*60)
        logger.info("📋 部署摘要")
        logger.info("="*60)
        logger.info(f"部署目录: {self.deployment_dir}")
        logger.info(f"配置目录: {self.config_dir}")
        logger.info(f"日志目录: {self.logs_dir}")
        logger.info(f"数据目录: {self.data_dir}")
        logger.info(f"虚拟环境: {self.venv_dir}")
        
        logger.info("\n📝 下一步操作:")
        logger.info("1. 编辑CTP配置文件:")
        logger.info(f"   vi {self.config_dir}/ctp_config.json")
        logger.info("2. 启动系统:")
        logger.info(f"   {self.deployment_dir}/scripts/start_arbig.sh")
        logger.info("3. 访问Web监控:")
        web_port = self.config.get('web_port', 8000)
        logger.info(f"   http://localhost:{web_port}")
        
        if sys.platform.startswith('linux'):
            logger.info("4. 设置开机自启:")
            logger.info("   sudo systemctl enable arbig")
            logger.info("   sudo systemctl start arbig")

def load_deployment_config(config_file: str) -> Dict:
    """加载部署配置"""
    try:
        if Path(config_file).exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        else:
            # 默认配置
            return {
                'deployment_dir': '/opt/arbig',
                'environment': 'production',
                'debug': False,
                'log_level': 'INFO',
                'web_host': '0.0.0.0',
                'web_port': 8000,
                'symbols': ['au2509', 'au2512', 'au2601']
            }
    except Exception as e:
        logger.error(f"加载部署配置失败: {e}")
        return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ARBIG系统部署脚本")
    parser.add_argument(
        '--config',
        default='deploy_config.yaml',
        help='部署配置文件路径'
    )
    parser.add_argument(
        '--deployment-dir',
        help='部署目录（覆盖配置文件设置）'
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_deployment_config(args.config)
    if args.deployment_dir:
        config['deployment_dir'] = args.deployment_dir
    
    # 执行部署
    deployer = ARBIGDeployer(config)
    success = deployer.deploy()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
