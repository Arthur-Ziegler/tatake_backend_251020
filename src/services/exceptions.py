"""
服务层异常类定义

该模块定义了服务层使用的所有自定义异常类，提供丰富的上下文错误信息，
便于快速定位问题和进行错误处理。

设计原则：
1. 异常传播机制：保持异常信息的完整传递链
2. 丰富上下文信息：包含错误代码、技术消息、用户消息、建议等
3. 结构化错误信息：便于程序化处理和用户界面展示
4. 类型安全：明确的异常类型区分不同的业务场景

异常层次结构：
    BusinessException (基础业务异常)
    ├── ValidationException (数据验证异常)
    ├── ResourceNotFoundException (资源未找到异常)
    ├── InsufficientBalanceException (余额不足异常)
    ├── DuplicateResourceException (重复资源异常)
    └── AuthenticationException (认证异常)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import traceback


class BusinessException(Exception):
    """
    基础业务异常类

    所有服务层业务异常的基类，提供统一的错误信息结构。
    包含丰富的上下文信息，便于错误定位和用户提示。

    Attributes:
        error_code (str): 标准化错误代码，便于程序化处理
        message (str): 技术错误消息，用于开发者调试
        details (Dict[str, Any]): 详细错误上下文，包含参数、状态等信息
        user_message (str): 用户友好的错误消息
        suggestions (List[str]): 修复建议列表
        debug_info (Dict[str, Any]): 调试信息，包含时间戳、调用栈等
        cause (Optional[Exception]): 原始异常，用于异常链追踪
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化业务异常

        Args:
            error_code: 标准化错误代码，格式为 SERVICE_XXX
            message: 技术错误消息，用于开发者调试
            details: 详细错误上下文，包含相关参数、状态等信息
            user_message: 用户友好的错误消息，如果为None则使用message
            suggestions: 修复建议列表，帮助用户或开发者解决问题
            cause: 原始异常，用于异常链追踪
        """
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.user_message = user_message or message
        self.suggestions = suggestions or []
        self.cause = cause

        # 生成调试信息
        self.debug_info = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": self.__class__.__name__,
            "traceback": traceback.format_exc() if cause else None
        }

        # 调用父类构造函数
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        将异常信息转换为字典格式

        Returns:
            包含所有异常信息的字典，便于序列化和API响应
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "suggestions": self.suggestions,
            "debug_info": {
                **self.debug_info,
                "traceback": self.debug_info["traceback"]  # 在生产环境中可能需要过滤
            }
        }

    def add_detail(self, key: str, value: Any) -> None:
        """
        添加详细信息

        Args:
            key: 信息键名
            value: 信息值
        """
        self.details[key] = value

    def add_suggestion(self, suggestion: str) -> None:
        """
        添加修复建议

        Args:
            suggestion: 修复建议文本
        """
        self.suggestions.append(suggestion)

    def __str__(self) -> str:
        """返回异常的字符串表示"""
        return f"[{self.error_code}] {self.user_message}"

    def __repr__(self) -> str:
        """返回异常的详细表示"""
        return f"{self.__class__.__name__}(error_code='{self.error_code}', message='{self.message}')"


class ValidationException(BusinessException):
    """
    数据验证异常类

    当输入数据不符合业务规则或格式要求时抛出此异常。
    通常用于API层的数据验证结果处理。
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """
        初始化验证异常

        Args:
            message: 验证错误消息
            field: 验证失败的字段名
            value: 验证失败的值
            **kwargs: 传递给父类的其他参数
        """
        details = kwargs.get("details", {})

        # 添加验证相关的详细信息
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)

        kwargs["details"] = details

        super().__init__(
            error_code="SERVICE_VALIDATION_ERROR",
            message=message,
            **kwargs
        )


class ResourceNotFoundException(BusinessException):
    """
    资源未找到异常类

    当请求的资源不存在时抛出此异常。
    通常用于查询、更新或删除操作时的资源存在性检查。
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        search_criteria: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        初始化资源未找到异常

        Args:
            resource_type: 资源类型，如"User"、"Task"等
            resource_id: 资源ID
            search_criteria: 搜索条件，当使用复合条件查询时使用
            **kwargs: 传递给父类的其他参数
        """
        # 构建错误消息
        if resource_id:
            message = f"{resource_type} with ID '{resource_id}' not found"
            user_message = f"未找到ID为'{resource_id}'的{resource_type}"
        elif search_criteria:
            criteria_str = ", ".join([f"{k}={v}" for k, v in search_criteria.items()])
            message = f"{resource_type} with criteria ({criteria_str}) not found"
            user_message = f"未找到符合条件的{resource_type}"
        else:
            message = f"{resource_type} not found"
            user_message = f"未找到{resource_type}"

        # 构建详细信息
        details = {
            "resource_type": resource_type
        }
        if resource_id:
            details["resource_id"] = resource_id
        if search_criteria:
            details["search_criteria"] = search_criteria

        kwargs.setdefault("details", {}).update(details)
        kwargs.setdefault("user_message", user_message)

        super().__init__(
            error_code="SERVICE_RESOURCE_NOT_FOUND",
            message=message,
            **kwargs
        )


class InsufficientBalanceException(BusinessException):
    """
    余额不足异常类

    当用户积分、碎片或其他虚拟货币余额不足时抛出此异常。
    通常用于奖励兑换、抽奖等涉及消费的业务场景。
    """

    def __init__(
        self,
        current_balance: float,
        required_amount: float,
        balance_type: str = "积分",
        **kwargs
    ):
        """
        初始化余额不足异常

        Args:
            current_balance: 当前余额
            required_amount: 所需金额
            balance_type: 余额类型，如"积分"、"碎片"等
            **kwargs: 传递给父类的其他参数
        """
        message = f"Insufficient {balance_type}: current={current_balance}, required={required_amount}"
        user_message = f"{balance_type}不足，当前余额为{current_balance}，需要{required_amount}"

        details = {
            "current_balance": current_balance,
            "required_amount": required_amount,
            "balance_type": balance_type,
            "shortfall": required_amount - current_balance
        }

        suggestions = [
            f"通过完成任务获取更多{balance_type}",
            "参与抽奖活动赢取奖励",
            "查看其他可兑换的奖励"
        ]

        kwargs.setdefault("details", {}).update(details)
        kwargs.setdefault("user_message", user_message)
        kwargs.setdefault("suggestions", []).extend(suggestions)

        super().__init__(
            error_code="SERVICE_INSUFFICIENT_BALANCE",
            message=message,
            **kwargs
        )


class DuplicateResourceException(BusinessException):
    """
    重复资源异常类

    当尝试创建已存在的资源时抛出此异常。
    通常用于注册、创建等操作时的唯一性约束检查。
    """

    def __init__(
        self,
        resource_type: str,
        conflict_field: str,
        conflict_value: str,
        existing_resource_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化重复资源异常

        Args:
            resource_type: 资源类型，如"User"、"Task"等
            conflict_field: 冲突字段名，如"email"、"phone"等
            conflict_value: 冲突字段的值
            existing_resource_id: 已存在资源的ID
            **kwargs: 传递给父类的其他参数
        """
        message = f"{resource_type} with {conflict_field} '{conflict_value}' already exists"
        user_message = f"{conflict_field}'{conflict_value}'已被使用"

        details = {
            "resource_type": resource_type,
            "conflict_field": conflict_field,
            "conflict_value": conflict_value
        }
        if existing_resource_id:
            details["existing_resource_id"] = existing_resource_id

        suggestions = [
            f"尝试使用不同的{conflict_field}",
            "如果这是您的账户，请直接登录",
            "联系管理员处理重复问题"
        ]

        kwargs.setdefault("details", {}).update(details)
        kwargs.setdefault("user_message", user_message)
        kwargs.setdefault("suggestions", []).extend(suggestions)

        super().__init__(
            error_code="SERVICE_DUPLICATE_RESOURCE",
            message=message,
            **kwargs
        )


class AuthenticationException(BusinessException):
    """
    认证异常类

    当用户认证失败时抛出此异常。
    包括登录失败、令牌无效、权限不足等情况。
    """

    def __init__(
        self,
        reason: str,
        user_identifier: Optional[str] = None,
        **kwargs
    ):
        """
        初始化认证异常

        Args:
            reason: 认证失败的原因
            user_identifier: 用户标识符，如邮箱、用户ID等
            **kwargs: 传递给父类的其他参数
        """
        message = f"Authentication failed: {reason}"
        user_message = "认证失败"

        if "invalid credentials" in reason.lower():
            user_message = "用户名或密码错误"
        elif "token expired" in reason.lower():
            user_message = "登录已过期，请重新登录"
        elif "token invalid" in reason.lower():
            user_message = "登录状态无效，请重新登录"
        elif "permission denied" in reason.lower():
            user_message = "权限不足，无法执行此操作"

        details = {
            "reason": reason
        }
        if user_identifier:
            details["user_identifier"] = user_identifier

        suggestions = [
            "检查用户名和密码是否正确",
            "尝试重新登录",
            "联系管理员重置密码"
        ]

        kwargs.setdefault("details", {}).update(details)
        kwargs.setdefault("user_message", user_message)
        kwargs.setdefault("suggestions", []).extend(suggestions)

        super().__init__(
            error_code="SERVICE_AUTHENTICATION_ERROR",
            message=message,
            **kwargs
        )


class AuthorizationException(BusinessException):
    """
    授权异常类

    当用户权限不足时抛出此异常。
    用于访问控制，区分认证和授权的不同场景。
    """

    def __init__(
        self,
        required_permission: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化授权异常

        Args:
            required_permission: 所需权限
            user_id: 用户ID
            resource_id: 资源ID
            **kwargs: 传递给父类的其他参数
        """
        message = f"Access denied: requires permission '{required_permission}'"
        user_message = "权限不足，无法执行此操作"

        details = {
            "required_permission": required_permission
        }
        if user_id:
            details["user_id"] = user_id
        if resource_id:
            details["resource_id"] = resource_id

        suggestions = [
            "联系管理员申请相应权限",
            "确认您是否有权执行此操作",
            "如果认为这是错误，请联系技术支持"
        ]

        kwargs.setdefault("details", {}).update(details)
        kwargs.setdefault("user_message", user_message)
        kwargs.setdefault("suggestions", []).extend(suggestions)

        super().__init__(
            error_code="SERVICE_AUTHORIZATION_ERROR",
            message=message,
            **kwargs
        )


# 异常映射字典，便于根据错误代码查找异常类
EXCEPTION_MAP: Dict[str, type] = {
    "SERVICE_VALIDATION_ERROR": ValidationException,
    "SERVICE_RESOURCE_NOT_FOUND": ResourceNotFoundException,
    "SERVICE_INSUFFICIENT_BALANCE": InsufficientBalanceException,
    "SERVICE_DUPLICATE_RESOURCE": DuplicateResourceException,
    "SERVICE_AUTHENTICATION_ERROR": AuthenticationException,
    "SERVICE_AUTHORIZATION_ERROR": AuthorizationException,
}


def create_exception(error_code: str, message: str, **kwargs) -> BusinessException:
    """
    根据错误代码创建对应的异常实例

    Args:
        error_code: 错误代码
        message: 错误消息
        **kwargs: 传递给异常构造函数的其他参数

    Returns:
        对应的异常实例
    """
    exception_class = EXCEPTION_MAP.get(error_code, BusinessException)

    # 对于BusinessException基类，直接传递所有参数
    if exception_class == BusinessException:
        return exception_class(
            error_code=error_code,
            message=message,
            **kwargs
        )

    # 对于子类，使用特定的构造参数
    elif exception_class == ValidationException:
        return exception_class(
            message=message,
            **kwargs
        )

    elif exception_class == ResourceNotFoundException:
        return exception_class(
            resource_type=kwargs.get('resource_type', 'Resource'),
            resource_id=kwargs.get('resource_id'),
            search_criteria=kwargs.get('search_criteria'),
            user_message=message,
            details=kwargs.get('details', {})
        )

    elif exception_class == InsufficientBalanceException:
        return exception_class(
            current_balance=kwargs.get('current_balance', 0),
            required_amount=kwargs.get('required_amount', 0),
            balance_type=kwargs.get('balance_type', '积分'),
            user_message=message,
            details=kwargs.get('details', {})
        )

    elif exception_class == DuplicateResourceException:
        return exception_class(
            resource_type=kwargs.get('resource_type', 'Resource'),
            conflict_field=kwargs.get('conflict_field', 'field'),
            conflict_value=kwargs.get('conflict_value', 'value'),
            existing_resource_id=kwargs.get('existing_resource_id'),
            user_message=message,
            details=kwargs.get('details', {})
        )

    elif exception_class == AuthenticationException:
        return exception_class(
            reason=message,
            user_identifier=kwargs.get('user_identifier'),
            user_message=message,
            details=kwargs.get('details', {})
        )

    elif exception_class == AuthorizationException:
        return exception_class(
            required_permission=kwargs.get('required_permission', 'permission'),
            user_id=kwargs.get('user_id'),
            resource_id=kwargs.get('resource_id'),
            user_message=message,
            details=kwargs.get('details', {})
        )

    else:
        # 默认情况，使用基类
        return BusinessException(
            error_code=error_code,
            message=message,
            **kwargs
        )


def wrap_repository_error(repo_error: Exception, context: str) -> BusinessException:
    """
    将Repository层异常包装为Service层异常

    Args:
        repo_error: Repository层异常
        context: 操作上下文描述

    Returns:
        包装后的Service层异常
    """
    from src.repositories.base import (
        RepositoryNotFoundError,
        RepositoryValidationError,
        RepositoryIntegrityError
    )

    error_message = f"{context}: {str(repo_error)}"

    if isinstance(repo_error, RepositoryNotFoundError):
        return ResourceNotFoundException(
            resource_type="Resource",
            user_message=error_message,
            cause=repo_error
        )
    elif isinstance(repo_error, RepositoryValidationError):
        return ValidationException(
            message=error_message,
            cause=repo_error
        )
    elif isinstance(repo_error, RepositoryIntegrityError):
        return DuplicateResourceException(
            resource_type="Resource",
            conflict_field="unknown",
            conflict_value="unknown",
            user_message=error_message,
            cause=repo_error
        )
    else:
        return BusinessException(
            error_code="SERVICE_REPOSITORY_ERROR",
            message=error_message,
            cause=repo_error
        )