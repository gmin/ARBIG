"""
API路由模块
组织和管理所有API路由
"""

from .system import router as system_router
from .services import router as services_router
from .strategies import router as strategies_router
from .data import router as data_router

__all__ = [
    "system_router",
    "services_router",
    "strategies_router",
    "data_router"
]
