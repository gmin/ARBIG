"""
MT5 工具函数模块
"""

import os
from typing import Dict
from vnpy.trader.utility import load_json

def load_config() -> Dict:
    """
    加载MT5配置文件
    
    Returns:
        Dict: MT5配置信息
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "mt5_sim.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"MT5配置文件不存在: {config_path}")
    return load_json(config_path)
