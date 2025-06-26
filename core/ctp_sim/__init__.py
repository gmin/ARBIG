"""
CTP仿真环境模块
提供CTP仿真交易环境的配置和初始化功能
"""

from .gateway import CtpSimGateway
from .config import CtpSimConfig

__all__ = ['CtpSimGateway', 'CtpSimConfig'] 