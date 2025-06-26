"""
CTP模块
提供CTP交易环境的连接和交易功能
"""

from .gateway import CtpWrapper
from .config import CtpConfig

__all__ = ['CtpWrapper', 'CtpConfig'] 