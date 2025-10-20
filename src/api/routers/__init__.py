"""
API路由模块

包含所有API路由的模块化组织。
"""

from .auth import router as auth_router

# 其他路由模块将在后续任务中实现
# from .tasks import router as tasks_router
# from .chat import router as chat_router
# from .focus import router as focus_router
# from .rewards import router as rewards_router
# from .statistics import router as statistics_router
# from .user import router as user_router

__all__ = [
    "auth_router",
    # 其他路由将在后续任务中添加
]