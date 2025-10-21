"""
Task领域模块

TaKeKe项目的任务管理核心功能，提供完整的任务CRUD操作。

功能特性：
1. 基础任务CRUD（创建、读取、更新、删除）
2. 父子任务关系管理
3. 任务状态和优先级管理
4. 任务标签分类
5. 任务列表查询和筛选
6. 级联软删除
7. 循环引用检测

架构设计：
- 遵循DDD（领域驱动设计）架构模式
- 分层设计：models → schemas → repository → service → router
- 统一响应格式，与auth领域保持一致
- 完整的错误处理和异常管理

API端点：
- POST /tasks - 创建任务
- GET /tasks/{id} - 获取任务详情
- PUT /tasks/{id} - 更新任务
- DELETE /tasks/{id} - 删除任务
- GET /tasks - 获取任务列表

作者：TaKeKe团队
版本：1.0.0
"""

# 导入主要模块
from .models import Task
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    PaginationInfo
)
from .exceptions import (
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException
)

# 定义类型别名以保持兼容性
TaskStatus = str
TaskPriority = str

__version__ = "1.0.0"
__all__ = [
    # Models
    "Task",
    "TaskStatus",
    "TaskPriority",

    # Schemas
    "CreateTaskRequest",
    "UpdateTaskRequest",
    "TaskListQuery",
    "TaskResponse",
    "TaskListResponse",
    "PaginationInfo",

    # Exceptions
    "TaskNotFoundException",
    "TaskPermissionDeniedException",
    "CircularReferenceException",
    "InvalidTimeRangeException"
]