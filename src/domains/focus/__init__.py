"""
Focus领域模块 - 番茄钟系统

简化版的番茄钟系统，仅记录核心会话数据：
- 6个核心字段：id, user_id, task_id, session_type, start_time, end_time
- 4种会话类型：focus, break, long_break, pause
- 4个核心API：start, pause, resume, complete
- 自动关闭逻辑：新会话开始时自动关闭未完成的会话

设计原则：
1. 极简化：只保留时间段记录，不计算duration/管理status
2. 无状态：数据库不负责复杂的会话状态管理
3. 自动化：通过自动关闭机制简化状态管理
4. 扩展性：支持多种会话类型，为统计服务提供原始数据
"""

from .models import FocusSession, SessionType
from .schemas import (
    StartFocusRequest,
    FocusSessionResponse,
    FocusSessionListResponse
)
from .service import FocusService
from .repository import FocusRepository
from .database import get_focus_session
from .router import router

__all__ = [
    "FocusSession",
    "SessionType",
    "StartFocusRequest",
    "FocusSessionResponse",
    "FocusSessionListResponse",
    "FocusService",
    "FocusRepository",
    "get_focus_session",
    "router"
]