"""
API路由模块

包含所有API路由的模块化组织。
"""

from .auth import router as auth_router
from .tasks import router as tasks_router
from .chat import router as chat_router
from .focus import router as focus_router
from .rewards import router as rewards_router
from .statistics import router as statistics_router
from .user import router as user_router

__all__ = [
    "auth_router",
    "tasks_router",
    "chat_router",
    "focus_router",
    "rewards_router",
    "statistics_router",
    "user_router"
]