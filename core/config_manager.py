"""
配置管理器
负责系统配置的加载、更新和保存
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from core.types import CtpConfig, DatabaseConfig, RedisConfig, ServiceConfig
from utils.logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._load_ctp_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"配置文件加载成功: {self.config_path}")
            else:
                logger.warning(f"配置文件不存在: {self.config_path}")
                self.config = self._get_default_config()
                self.save_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = self._get_default_config()

    def _load_ctp_config(self) -> None:
        """加载CTP配置文件"""
        try:
            ctp_config_path = Path("config/ctp_sim.json")
            if ctp_config_path.exists():
                with open(ctp_config_path, 'r', encoding='utf-8') as f:
                    ctp_config = json.load(f)

                # 将CTP配置合并到主配置中
                if 'ctp' not in self.config:
                    self.config['ctp'] = {}

                self.config['ctp']['trading'] = {
                    'userid': ctp_config.get('用户名', ''),
                    'password': ctp_config.get('密码', ''),
                    'brokerid': ctp_config.get('经纪商代码', ''),
                    'td_address': ctp_config.get('交易服务器', ''),
                    'appid': ctp_config.get('产品名称', ''),
                    'auth_code': ctp_config.get('授权编码', ''),
                    'product_info': ctp_config.get('产品信息', '')
                }

                self.config['ctp']['market'] = {
                    'userid': ctp_config.get('用户名', ''),
                    'password': ctp_config.get('密码', ''),
                    'brokerid': ctp_config.get('经纪商代码', ''),
                    'md_address': ctp_config.get('行情服务器', ''),
                    'appid': ctp_config.get('产品名称', ''),
                    'auth_code': ctp_config.get('授权编码', ''),
                    'product_info': ctp_config.get('产品信息', '')
                }

                logger.info(f"CTP配置文件加载成功: {ctp_config_path}")
            else:
                logger.warning(f"CTP配置文件不存在: {ctp_config_path}")

        except Exception as e:
            logger.error(f"加载CTP配置文件失败: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'ctp': {
                'trading': {
                    'userid': '242407',
                    'password': '1234%^&*QWE',
                    'brokerid': '9999',
                    'td_address': '180.168.146.187:10130',
                    'appid': '',
                    'auth_code': '',
                    'product_info': ''
                },
                'market': {
                    'md_address': '180.168.146.187:10131'
                }
            },
            'services': {
                'market_data': {
                    'enabled': True,
                    'symbols': ['AU2509', 'AU2512'],
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
                    'max_orders_per_second': 10
                },
                'risk': {
                    'enabled': True,
                    'max_position_ratio': 0.8,
                    'max_daily_loss': 50000,
                    'stop_loss_ratio': 0.02
                }
            },
            'strategies': {
                'shfe_quant': {
                    'enabled': True,
                    'max_position': 1000,
                    'bollinger_period': 20,
                    'rsi_period': 14
                }
            },
            'database': {
                'mongodb': {
                    'host': 'localhost',
                    'port': 27017,
                    'database': 'arbig'
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0
                }
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/arbig.log',
                'max_size': '10MB',
                'backup_count': 5
            }
        }
    
    def get_config(self, key: str = None) -> Any:
        """
        获取配置
        
        Args:
            key: 配置键，支持点分隔的嵌套键，如 'ctp.trading.userid'
            
        Returns:
            配置值
        """
        if key is None:
            return self.config
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def set_config(self, key: str, value: Any) -> None:
        """
        设置配置
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到最后一级的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        logger.info(f"配置已更新: {key} = {value}")
    
    def get_ctp_config(self) -> CtpConfig:
        """获取CTP配置"""
        trading_config = self.get_config('ctp.trading') or {}
        market_config = self.get_config('ctp.market') or {}
        
        return CtpConfig(
            userid=trading_config.get('userid', ''),
            password=trading_config.get('password', ''),
            brokerid=trading_config.get('brokerid', ''),
            td_address=trading_config.get('td_address', ''),
            md_address=market_config.get('md_address', ''),
            appid=trading_config.get('appid', ''),
            auth_code=trading_config.get('auth_code', ''),
            product_info=trading_config.get('product_info', '')
        )
    
    def get_service_config(self, service_name: str) -> ServiceConfig:
        """
        获取服务配置
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务配置
        """
        config = self.get_config(f'services.{service_name}') or {}
        
        return ServiceConfig(
            name=service_name,
            enabled=config.get('enabled', True),
            config=config
        )
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        获取策略配置
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略配置字典
        """
        return self.get_config(f'strategies.{strategy_name}') or {}
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        config = self.get_config('database.mongodb') or {}
        
        return DatabaseConfig(
            host=config.get('host', 'localhost'),
            port=config.get('port', 27017),
            database=config.get('database', 'arbig'),
            username=config.get('username', ''),
            password=config.get('password', '')
        )
    
    def get_redis_config(self) -> RedisConfig:
        """获取Redis配置"""
        config = self.get_config('database.redis') or {}
        
        return RedisConfig(
            host=config.get('host', 'localhost'),
            port=config.get('port', 6379),
            db=config.get('db', 0),
            password=config.get('password', '')
        )
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"配置文件保存成功: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def reload_config(self) -> bool:
        """
        重新加载配置文件
        
        Returns:
            是否加载成功
        """
        try:
            self._load_config()
            logger.info("配置文件重新加载成功")
            return True
        except Exception as e:
            logger.error(f"重新加载配置文件失败: {e}")
            return False
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        try:
            # 验证CTP配置
            ctp_config = self.get_ctp_config()
            if not ctp_config.userid or not ctp_config.password:
                logger.error("CTP配置不完整：缺少用户名或密码")
                return False
            
            # 验证服务配置
            required_services = ['market_data', 'account', 'trading', 'risk']
            for service in required_services:
                service_config = self.get_service_config(service)
                if not service_config.enabled:
                    logger.warning(f"服务 {service} 已禁用")
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
