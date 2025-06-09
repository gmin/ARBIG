"""
上海黄金期货工具函数模块
"""

import os
from typing import Dict
from vnpy.trader.utility import load_json

def load_config() -> Dict:
    """
    加载CTP配置文件
    
    Returns:
        Dict: CTP配置信息
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "shfe_sim.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"CTP配置文件不存在: {config_path}")
    return load_json(config_path)
