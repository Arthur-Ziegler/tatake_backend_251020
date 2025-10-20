"""
核心异常类模块

该模块定义了系统中使用的所有核心异常类，避免循环导入问题。
这些异常类可以被服务层、仓储层和API层共同使用。

核心异常类：
- BusinessException: 业务逻辑异常
- ValidationException: 验证异常
- ResourceNotFoundException: 资源未找到异常
- AuthenticationException: 认证异常
- AuthorizationException: 授权异常
- DuplicateResourceException: 重复资源异常
- InsufficientBalanceException: 余额不足异常
"""

from typing import Optional, Dict, Any


class BaseException(Exception):
    """基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化基础异常

        Args:
            message: 异常消息（内部使用）
            error_code: 错误代码
            user_message: 用户友好的错误消息
            details: 错误详情
            cause: 原始异常
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.user_message = user_message or message
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.user_message,
            "details": self.details
        }


class BusinessException(BaseException):
    """业务逻辑异常"""

    def __init__(
        self,
        message: str = "业务逻辑错误",
        error_code: Optional[str] = "BUSINESS_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, user_message, details, cause)


class ValidationException(BaseException):
    """验证异常"""

    def __init__(
        self,
        message: str = "数据验证失败",
        error_code: Optional[str] = "VALIDATION_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_code, user_message, details, cause)


class ResourceNotFoundException(BaseException):
    """资源未找到异常"""

    def __init__(
        self,
        resource_type: str = "资源",
        error_code: Optional[str] = "RESOURCE_NOT_FOUND",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        message = f"{resource_type}未找到"
        user_message = user_message or message
        super().__init__(message, error_code, user_message, details, cause)
        self.resource_type = resource_type


class AuthenticationException(BaseException):
    """认证异常"""

    def __init__(
        self,
        reason: str = "认证失败",
        error_code: Optional[str] = "AUTHENTICATION_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_identifier: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        message = f"认证失败: {reason}"
        user_message = user_message or "身份验证失败，请重新登录"
        details = details or {}
        if user_identifier:
            details["user_identifier"] = user_identifier

        super().__init__(message, error_code, user_message, details, cause)
        self.reason = reason
        self.user_identifier = user_identifier


class AuthorizationException(BaseException):
    """授权异常"""

    def __init__(
        self,
        message: str = "权限不足",
        error_code: Optional[str] = "AUTHORIZATION_ERROR",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        required_permission: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        user_message = user_message or "您没有权限执行此操作"
        details = details or {}
        if required_permission:
            details["required_permission"] = required_permission

        super().__init__(message, error_code, user_message, details, cause)
        self.required_permission = required_permission


class DuplicateResourceException(BaseException):
    """重复资源异常"""

    def __init__(
        self,
        resource_type: str = "资源",
        conflict_field: Optional[str] = None,
        conflict_value: Optional[str] = None,
        error_code: Optional[str] = "DUPLICATE_RESOURCE",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        message = f"{resource_type}已存在"
        if conflict_field and conflict_value:
            message += f"，{conflict_field}: {conflict_value}"

        user_message = user_message or message
        details = details or {}
        if conflict_field:
            details["conflict_field"] = conflict_field
        if conflict_value:
            details["conflict_value"] = conflict_value

        super().__init__(message, error_code, user_message, details, cause)
        self.resource_type = resource_type
        self.conflict_field = conflict_field
        self.conflict_value = conflict_value


class InsufficientBalanceException(BaseException):
    """余额不足异常"""

    def __init__(
        self,
        required_amount: Optional[float] = None,
        current_balance: Optional[float] = None,
        error_code: Optional[str] = "INSUFFICIENT_BALANCE",
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        message = "余额不足"
        if required_amount is not None:
            message += f"，需要: {required_amount}"

        user_message = user_message or "账户余额不足，请充值后重试"
        details = details or {}
        if required_amount is not None:
            details["required_amount"] = required_amount
        if current_balance is not None:
            details["current_balance"] = current_balance

        super().__init__(message, error_code, user_message, details, cause)
        self.required_amount = required_amount
        self.current_balance = current_balance