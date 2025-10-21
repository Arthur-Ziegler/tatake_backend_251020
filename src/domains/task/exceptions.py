"""
Task领域异常类定义

定义任务管理相关的自定义异常类，提供详细的错误信息和适当的HTTP状态码。

异常设计原则：
1. 明确的错误信息：每个异常都有详细的描述
2. 合适的HTTP状态码：映射到标准的HTTP状态码
3. 结构化错误响应：统一的错误响应格式
4. 可扩展性：便于后续添加新的异常类型

异常类型：
- TaskNotFoundException: 任务不存在（404）
- TaskPermissionDeniedException: 无权限访问（403）
- CircularReferenceException: 循环引用（400）
- InvalidTimeRangeException: 时间范围无效（400）

使用示例：
    raise TaskNotFoundException(task_id="123", user_id="456")

    错误响应格式：
    {
        "code": 404,
        "data": null,
        "message": "任务不存在或已被删除：task_id=123, user_id=456"
    }

作者：TaKeKe团队
版本：1.0.0
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class TaskException(HTTPException):
    """
    Task领域基础异常类

    所有Task领域异常的基类，提供统一的异常处理机制。
    继承自FastAPI的HTTPException，自动处理HTTP状态码和响应格式。

    Attributes:
        status_code (int): HTTP状态码
        detail (str): 错误详情
        error_code (str): 内部错误代码
        context (Dict[str, Any]): 错误上下文信息
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常

        Args:
            status_code (int): HTTP状态码
            detail (str): 错误详情
            error_code (str, optional): 内部错误代码
            context (Dict[str, Any], optional): 错误上下文信息
        """
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于日志记录"""
        return {
            "exception_type": self.__class__.__name__,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "detail": self.detail,
            "context": self.context
        }


class TaskNotFoundException(TaskException):
    """
    任务不存在异常

    当请求的任务不存在或已被删除时抛出此异常。
    通常发生在以下场景：
    1. 根据ID查找任务时任务不存在
    2. 任务已被软删除
    3. 用户试图访问其他用户的任务

    HTTP状态码：404 Not Found
    """

    def __init__(self, task_id: str, user_id: str = None, include_deleted: bool = False):
        """
        初始化任务不存在异常

        Args:
            task_id (str): 任务ID
            user_id (str, optional): 用户ID
            include_deleted (bool): 是否包含已删除的任务
        """
        detail = f"任务不存在或已被删除：task_id={task_id}"
        if user_id:
            detail += f", user_id={user_id}"
        if include_deleted:
            detail += "（包含已删除任务）"

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="TASK_NOT_FOUND",
            context={
                "task_id": task_id,
                "user_id": user_id,
                "include_deleted": include_deleted
            }
        )


class TaskPermissionDeniedException(TaskException):
    """
    任务权限拒绝异常

    当用户试图访问或操作无权限的任务时抛出此异常。
    通常发生在以下场景：
    1. 用户试图查看其他用户的任务
    2. 用户试图修改或删除其他用户的任务
    3. 用户试图操作没有权限的任务类型

    HTTP状态码：403 Forbidden
    """

    def __init__(self, task_id: str, user_id: str, action: str = "access"):
        """
        初始化权限拒绝异常

        Args:
            task_id (str): 任务ID
            user_id (str): 用户ID
            action (str): 试图执行的操作
        """
        detail = f"无权限{action}任务：task_id={task_id}, user_id={user_id}"

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="TASK_PERMISSION_DENIED",
            context={
                "task_id": task_id,
                "user_id": user_id,
                "action": action
            }
        )


class CircularReferenceException(TaskException):
    """
    循环引用异常

    当设置任务的父子关系时会形成循环引用时抛出此异常。
    通常发生在以下场景：
    1. 试图将任务设置为自己的子任务
    2. 试图将任务设置为自己的后代任务
    3. 在任务树中形成闭环

    HTTP状态码：400 Bad Request
    """

    def __init__(self, task_id: str, parent_id: str, cycle_path: list = None):
        """
        初始化循环引用异常

        Args:
            task_id (str): 任务ID
            parent_id (str): 父任务ID
            cycle_path (list, optional): 循环路径
        """
        detail = f"检测到循环引用：task_id={task_id}, parent_id={parent_id}"
        if cycle_path:
            detail += f", 循环路径：{' -> '.join(cycle_path)}"

        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="CIRCULAR_REFERENCE",
            context={
                "task_id": task_id,
                "parent_id": parent_id,
                "cycle_path": cycle_path or []
            }
        )


class InvalidTimeRangeException(TaskException):
    """
    无效时间范围异常

    当设置的时间范围不符合逻辑时抛出此异常。
    通常发生在以下场景：
    1. 计划结束时间早于计划开始时间
    2. 截止日期早于当前时间
    3. 时间格式无效

    HTTP状态码：400 Bad Request
    """

    def __init__(
        self,
        start_time: str = None,
        end_time: str = None,
        due_date: str = None,
        reason: str = None
    ):
        """
        初始化无效时间范围异常

        Args:
            start_time (str, optional): 开始时间
            end_time (str, optional): 结束时间
            due_date (str, optional): 截止日期
            reason (str, optional): 具体原因
        """
        if reason:
            detail = f"时间范围无效：{reason}"
        else:
            detail = "时间范围无效"
            if start_time and end_time:
                detail += f"，开始时间={start_time}, 结束时间={end_time}"
            if due_date:
                detail += f"，截止日期={due_date}"

        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="INVALID_TIME_RANGE",
            context={
                "start_time": start_time,
                "end_time": end_time,
                "due_date": due_date,
                "reason": reason
            }
        )


class TaskValidationException(TaskException):
    """
    任务验证异常

    当任务数据不符合验证规则时抛出此异常。
    通常发生在以下场景：
    1. 标题长度不符合要求
    2. 状态值无效
    3. 优先级值无效
    4. 其他业务规则验证失败

    HTTP状态码：422 Unprocessable Entity
    """

    def __init__(self, field: str, value: Any, reason: str):
        """
        初始化任务验证异常

        Args:
            field (str): 验证失败的字段名
            value (Any): 验证失败的值
            reason (str): 失败原因
        """
        detail = f"任务验证失败：{field}={value}，{reason}"

        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="TASK_VALIDATION_ERROR",
            context={
                "field": field,
                "value": value,
                "reason": reason
            }
        )


class TaskDatabaseException(TaskException):
    """
    任务数据库异常

    当数据库操作失败时抛出此异常。
    通常发生在以下场景：
    1. 数据库连接失败
    2. 事务回滚
    3. 数据库约束冲突
    4. 其他数据库相关错误

    HTTP状态码：500 Internal Server Error
    """

    def __init__(self, operation: str, reason: str, original_error: Exception = None):
        """
        初始化数据库异常

        Args:
            operation (str): 执行的操作
            reason (str): 失败原因
            original_error (Exception, optional): 原始异常
        """
        detail = f"数据库操作失败：{operation}，{reason}"

        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="TASK_DATABASE_ERROR",
            context={
                "operation": operation,
                "reason": reason,
                "original_error": str(original_error) if original_error else None
            }
        )


# 异常映射表，便于统一处理
TASK_EXCEPTION_MAP = {
    "TASK_NOT_FOUND": TaskNotFoundException,
    "TASK_PERMISSION_DENIED": TaskPermissionDeniedException,
    "CIRCULAR_REFERENCE": CircularReferenceException,
    "INVALID_TIME_RANGE": InvalidTimeRangeException,
    "TASK_VALIDATION_ERROR": TaskValidationException,
    "TASK_DATABASE_ERROR": TaskDatabaseException
}


def create_task_exception(error_code: str, **kwargs) -> TaskException:
    """
    创建Task异常的工厂函数

    根据错误代码创建对应的异常实例。

    Args:
        error_code (str): 错误代码
        **kwargs: 异常参数

    Returns:
        TaskException: 异常实例

    Raises:
        ValueError: 当错误代码不存在时
    """
    exception_class = TASK_EXCEPTION_MAP.get(error_code)
    if not exception_class:
        raise ValueError(f"未知的Task异常代码：{error_code}")

    return exception_class(**kwargs)