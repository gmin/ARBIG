"""
CTP仿真环境配置
"""

import json
import os
from typing import Dict, Any
from pathlib import Path

class CtpConfig:
    """
    CTP仿真环境配置类
    管理CTP仿真环境的连接参数和配置
    """
    
    def __init__(self, config_file: str = None):
        """
        初始化CTP仿真配置
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        self.config_file = config_file or "config/ctp.json"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"CTP仿真配置文件不存在: {self.config_file}")
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            return config
            
        except Exception as e:
            raise RuntimeError(f"加载CTP仿真配置失败: {str(e)}")
            
    def get_trading_config(self) -> Dict[str, Any]:
        """
        获取交易配置
        
        Returns:
            Dict: 交易配置字典
        """
        return {
            "用户名": self.config.get("用户名"),
            "密码": self.config.get("密码"),
            "经纪商代码": self.config.get("BROKEID"),
            "交易服务器": self.config.get("td_server"),
            "产品名称": self.config.get("APPID"),
            "授权编码": self.config.get("AuthCode")
        }
        
    def get_market_config(self) -> Dict[str, Any]:
        """
        获取行情配置
        
        Returns:
            Dict: 行情配置字典
        """
        return {
            "用户名": self.config.get("用户名"),
            "密码": self.config.get("密码"),
            "经纪商代码": self.config.get("BROKEID"),
            "行情服务器": self.config.get("md_server"),
            "产品名称": self.config.get("APPID"),
            "授权编码": self.config.get("AuthCode")
        }
        
    def get_server_info(self) -> Dict[str, str]:
        """
        获取服务器信息
        
        Returns:
            Dict: 服务器信息字典
        """
        trading_server = self.config.get("td_server", "")
        market_server = self.config.get("md_server", "")
        
        trading_host, trading_port = trading_server.split(":") if ":" in trading_server else ("", "")
        market_host, market_port = market_server.split(":") if ":" in market_server else ("", "")
        
        return {
            "trading_host": trading_host,
            "trading_port": int(trading_port) if trading_port.isdigit() else 0,
            "market_host": market_host,
            "market_port": int(market_port) if market_port.isdigit() else 0
        }
        
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        # 支持多种字段名格式
        required_fields_mapping = {
            "用户名": ["用户名", "user", "username"],
            "密码": ["密码", "password", "passwd"],
            "经纪商代码": ["经纪商代码", "BROKEID", "broker_id", "brokerid"],
            "交易服务器": ["交易服务器", "trading_server", "td_server"],
            "行情服务器": ["行情服务器", "market_server", "md_server"]
        }
        
        for field_name, possible_names in required_fields_mapping.items():
            found = False
            for name in possible_names:
                if self.config.get(name):
                    found = True
                    break
            if not found:
                raise ValueError(f"缺少必需的配置字段: {field_name} (可能的名称: {possible_names})")
                
        return True 