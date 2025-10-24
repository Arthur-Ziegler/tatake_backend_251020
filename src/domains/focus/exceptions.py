"""
Focus领域异常处理

定义Focus领域相关的异常类，提供清晰的错误信息和状态码。

异常设计原则：
1. 明确分类：不同类型的错误使用不同的异常类
2. 详细信息：提供足够的错误上下文
3. 状态码规范：使用合适的HTTP状态码
4. 日志友好：便于日志记录和调试

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""


class FocusException(Exception):
    """
    Focus系统基础异常类

    所有Focus相关的异常都继承自这个类，提供统一的错误处理机制。
    """

    def __init__(self, detail: str, status_code: int = 400):
        """
        初始化异常

        Args:
            detail: 错误详情
            status_code: HTTP状态码
        """
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)

    def __str__(self) -> str:
        """字符串表示"""
        return f"FocusException ({self.status_code}): {self.detail}"


class SessionNotFoundException(FocusException):
    """会话不存在异常"""

    def __init__(self, session_id: str = ""):
        message = f"会话不存在: {session_id}" if session_id else "会话不存在"
        super().__init__(message, status_code=404)


class SessionNotActiveException(FocusException):
    """会话未激活异常"""

    def __init__(self, session_id: str = ""):
        message = f"会话未激活或已完成: {session_id}" if session_id else "会话未激活或已完成"
        super().__init__(message, status_code=400)


class TaskNotFoundException(FocusException):
    """任务不存在异常"""

    def __init__(self, task_id: str = ""):
        message = f"任务不存在: {task_id}" if task_id else "任务不存在"
        super().__init__(message, status_code=404)


class PermissionDeniedException(FocusException):
    """权限不足异常"""

    def __init__(self, resource: str = "资源"):
        message = f"无权限访问{resource}"
        super().__init__(message, status_code=403)


class DatabaseOperationException(FocusException):
    """数据库操作异常"""

    def __init__(self, operation: str = "操作"):
        message = f"数据库{operation}失败"
        super().__init__(message, status_code=500)