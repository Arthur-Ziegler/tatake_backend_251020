"""
Task领域模块 - 微服务代理模式

TaKeKe项目的任务管理功能已迁移到微服务架构。
本模块提供代理层，将任务管理请求转发到Task微服务(localhost:20252)。

功能特性：
1. 微服务代理：HTTP调用转发到Task微服务
2. 响应格式转换：统一微服务和本地API格式
3. 错误处理：完整的异常处理和状态码映射
4. 字段适配：处理微服务缺失字段
5. 事务支持：Top3积分扣除失败时自动回滚

架构设计：
- 代理模式：保持API路径完全不变
- HTTP客户端：与Task微服务通信
- 格式转换：微服务格式 ↔ 本地格式
- 错误映射：HTTP状态码 → 业务错误码

API端点（代理）：
- POST /tasks - 代理创建任务
- GET /tasks/{id} - 代理获取任务详情
- PUT /tasks/{id} - 代理更新任务
- DELETE /tasks/{id} - 代理删除任务
- GET /tasks - 代理获取任务列表
- GET /tasks/statistics - 代理获取任务统计
- POST /tasks/special/top3 - 积分扣除+代理设置
- GET /tasks/special/top3/{date} - 代理获取Top3

保留功能（本地实现）：
- POST /tasks/{id}/complete - 任务完成和奖励分发
- POST /tasks/{id}/uncomplete - 取消任务完成

作者：TaKeKe团队
版本：2.0.0（微服务代理）
"""

# 导入主要模块
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    TaskDeleteResponse,
    CompleteTaskRequest,
    CompleteTaskResponse,
    UncompleteTaskRequest,
    UncompleteTaskResponse,
    PaginationInfo
)
from .exceptions import (
    TaskException,
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException,
    TaskValidationException,
    TaskDatabaseException
)

# 定义类型别名以保持兼容性
TaskStatus = str
TaskPriority = str

# 为了向后兼容，定义一个空的Task类
class Task:
    """占位Task类，保持向后兼容性"""
    pass

__version__ = "2.0.0"
__all__ = [
    # 占位类（保持兼容性）
    "Task",
    "TaskStatus",
    "TaskPriority",

    # Schemas
    "CreateTaskRequest",
    "UpdateTaskRequest",
    "TaskListQuery",
    "TaskResponse",
    "TaskListResponse",
    "TaskDeleteResponse",
    "CompleteTaskRequest",
    "CompleteTaskResponse",
    "UncompleteTaskRequest",
    "UncompleteTaskResponse",
    "PaginationInfo",

    # Exceptions
    "TaskException",
    "TaskNotFoundException",
    "TaskPermissionDeniedException",
    "CircularReferenceException",
    "InvalidTimeRangeException",
    "TaskValidationException",
    "TaskDatabaseException"
]