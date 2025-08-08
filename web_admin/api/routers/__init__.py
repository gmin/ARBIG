"""
API路由模块
组织和管理所有API路由
"""

from .system_new import router as system_router
from .services_new import router as services_router
from .strategies_new import router as strategies_router
from .data_new import router as data_router

__all__ = [
    "system_router",
    "services_router",
    "strategies_router",
    "data_router"
]
