"""
零Bug测试体系 - 防御式API层

提供严格的API请求/响应验证，确保API的安全性和可靠性。

设计原则：
1. 输入即验证：每个输入都经过严格验证
2. 快速失败：验证失败立即返回，不进入业务逻辑
3. 明确错误：每个错误都有明确的错误码和消息
4. 审计日志：所有操作都有完整的审计记录
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timezone
import traceback
import logging

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .types import UserId, TaskId, UTCDateTime
from .validators import ValidationError, BusinessRuleViolationError

# =============================================================================
# API响应格式
# =============================================================================

@dataclass(frozen=True)
class APIResponse:
    """标准API响应格式"""
    code: int  # 200表示成功，其他表示错误
    message: str  # 用户友好的消息
    data: Optional[Any] = None  # 响应数据
    timestamp: Optional[datetime] = None  # 时间戳
    request_id: Optional[str] = None  # 请求ID，用于追踪

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_id": self.request_id
        }

    @classmethod
    def success(cls, data: Any = None, message: str = "操作成功", request_id: str = None) -> 'APIResponse':
        """创建成功响应"""
        return cls(code=200, message=message, data=data, request_id=request_id)

    @classmethod
    def error(cls, message: str, code: int = 400, data: Any = None, request_id: str = None) -> 'APIResponse':
        """创建错误响应"""
        return cls(code=code, message=message, data=data, request_id=request_id)

# =============================================================================
# 错误码定义
# =============================================================================

class ErrorCodes:
    """API错误码常量"""

    # 通用错误 (1000-1999)
    INVALID_REQUEST: Final = 1001
    MISSING_PARAMETER: Final = 1002
    INVALID_PARAMETER: Final = 1003
    PERMISSION_DENIED: Final = 1004
    RESOURCE_NOT_FOUND: Final = 1005
    INTERNAL_ERROR: Final = 1006
    RATE_LIMITED: Final = 1007

    # 认证错误 (2000-2999)
    INVALID_TOKEN: Final = 2001
    TOKEN_EXPIRED: Final = 2002
    UNAUTHORIZED: Final = 2003
    USER_NOT_FOUND: Final = 2004
    INVALID_CREDENTIALS: Final = 2005

    # 任务错误 (3000-3999)
    TASK_NOT_FOUND: Final = 3001
    TASK_CREATION_FAILED: Final = 3002
    TASK_UPDATE_FAILED: Final = 3003
    TASK_DELETION_FAILED: Final = 3004
    INVALID_TASK_STATUS: Final = 3005
    TASK_ALREADY_COMPLETED: Final = 3006

    # 业务规则错误 (4000-4999)
    BUSINESS_RULE_VIOLATION: Final = 4001
    DATA_CONSISTENCY_ERROR: Final = 4002
    OPERATION_NOT_ALLOWED: Final = 4003
    RESOURCE_CONFLICT: Final = 4004

    @classmethod
    def get_message(cls, code: int) -> str:
        """获取错误码对应的消息"""
        error_map = {
            cls.INVALID_REQUEST: "请求格式无效",
            cls.MISSING_PARAMETER: "缺少必要参数",
            cls.INVALID_PARAMETER: "参数值无效",
            cls.PERMISSION_DENIED: "权限不足",
            cls.RESOURCE_NOT_FOUND: "资源不存在",
            cls.INTERNAL_ERROR: "服务器内部错误",
            cls.RATE_LIMITED: "请求过于频繁",

            cls.INVALID_TOKEN: "访问令牌无效",
            cls.TOKEN_EXPIRED: "访问令牌已过期",
            cls.UNAUTHORIZED: "未授权访问",
            cls.USER_NOT_FOUND: "用户不存在",
            cls.INVALID_CREDENTIALS: "凭据无效",

            cls.TASK_NOT_FOUND: "任务不存在",
            cls.TASK_CREATION_FAILED: "任务创建失败",
            cls.TASK_UPDATE_FAILED: "任务更新失败",
            cls.TASK_DELETION_FAILED: "任务删除失败",
            cls.INVALID_TASK_STATUS: "任务状态无效",
            cls.TASK_ALREADY_COMPLETED: "任务已完成",

            cls.BUSINESS_RULE_VIOLATION: "违反业务规则",
            cls.DATA_CONSISTENCY_ERROR: "数据一致性错误",
            cls.OPERATION_NOT_ALLOWED: "操作不被允许",
            cls.RESOURCE_CONFLICT: "资源冲突",
        }
        return error_map.get(code, "未知错误")

# =============================================================================
# 请求验证装饰器
# =============================================================================

def validate_request(validator_func: Callable = None, error_code: int = ErrorCodes.INVALID_PARAMETER):
    """请求验证装饰器"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                # 如果提供了验证器函数，先执行验证
                if validator_func:
                    validator_func(*args, **kwargs)

                # 执行实际的处理函数
                return await func(*args, **kwargs)

            except ValidationError as e:
                # 验证错误
                return create_error_response(
                    message=e.message,
                    code=error_code,
                    data={"field": e.field, "value": e.value}
                )
            except BusinessRuleViolationError as e:
                # 业务规则错误
                return create_error_response(
                    message=e.message,
                    code=ErrorCodes.BUSINESS_RULE_VIOLATION,
                    data={"field": e.field, "value": e.value}
                )
            except Exception as e:
                # 其他未预期的错误
                logging.error(f"API处理异常: {e}", exc_info=True)
                return create_error_response(
                    message="服务器内部错误",
                    code=ErrorCodes.INTERNAL_ERROR,
                    data={"error_type": type(e).__name__}
                )

        return wrapper
    return decorator

def require_auth(permission_check: Callable = None):
    """认证和权限检查装饰器"""
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # 从请求头中获取token
                authorization = request.headers.get("authorization")
                if not authorization or not authorization.startswith("Bearer "):
                    return create_error_response(
                        message="缺少访问令牌",
                        code=ErrorCodes.INVALID_TOKEN
                    )

                token = authorization[7:]  # 移除 "Bearer " 前缀

                # 验证token并提取用户信息
                user_id = validate_token(token)

                # 权限检查
                if permission_check and not permission_check(user_id, request):
                    return create_error_response(
                        message="权限不足",
                        code=ErrorCodes.PERMISSION_DENIED
                    )

                # 将用户信息添加到kwargs中
                kwargs['user_id'] = user_id

                # 执行实际的处理函数
                return await func(request, *args, **kwargs)

            except Exception as e:
                logging.error(f"认证检查异常: {e}", exc_info=True)
                return create_error_response(
                    message="认证失败",
                    code=ErrorCodes.INVALID_TOKEN
                )

        return wrapper
    return decorator

# =============================================================================
# 审计日志
# =============================================================================

class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self.logger = logging.getLogger("audit")

    def log_request(self, request: Request, user_id: Optional[UserId] = None) -> str:
        """记录请求日志"""
        request_id = generate_request_id()

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "user_id": user_id,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.logger.info(f"API请求: {log_data}")
        return request_id

    def log_response(self, request_id: str, response: APIResponse, duration_ms: float = None) -> None:
        """记录响应日志"""
        log_data = {
            "request_id": request_id,
            "response_code": response.code,
            "response_message": response.message,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if response.code == 200:
            self.logger.info(f"API响应: {log_data}")
        else:
            self.logger.warning(f"API错误响应: {log_data}")

    def log_error(self, request_id: str, error: Exception, context: Dict[str, Any] = None) -> None:
        """记录错误日志"""
        log_data = {
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stack_trace": traceback.format_exc()
        }

        self.logger.error(f"API错误: {log_data}")

# 全局审计日志实例
audit_logger = AuditLogger()

# =============================================================================
# 响应创建函数
# =============================================================================

def create_success_response(data: Any = None, message: str = "操作成功",
                           request_id: str = None) -> JSONResponse:
    """创建成功响应"""
    response = APIResponse.success(data=data, message=message, request_id=request_id)
    return JSONResponse(content=response.to_dict(), status_code=200)

def create_error_response(message: str, code: int = 400, data: Any = None,
                        request_id: str = None) -> JSONResponse:
    """创建错误响应"""
    # 根据错误码确定HTTP状态码
    if code >= 2000 and code < 3000:
        status_code = 401  # 认证错误
    elif code >= 3000 and code < 4000:
        status_code = 400  # 客户端错误
    elif code >= 4000 and code < 5000:
        status_code = 422  # 业务规则错误
    elif code >= 5000:
        status_code = 500  # 服务器错误
    else:
        status_code = 400  # 默认客户端错误

    response = APIResponse.error(message=message, code=code, data=data, request_id=request_id)
    return JSONResponse(content=response.to_dict(), status_code=status_code)

# =============================================================================
# 工具函数
# =============================================================================

def generate_request_id() -> str:
    """生成请求ID"""
    import uuid
    return f"req_{uuid.uuid4().hex[:16]}"

def validate_token(token: str) -> UserId:
    """验证访问令牌"""
    # 这里应该实现实际的token验证逻辑
    # 暂时返回一个示例用户ID
    try:
        # 解析JWT token
        # payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # return UserId(payload["user_id"])

        # 临时实现
        if token == "test_token":
            return UserId("test_user_123")
        else:
            raise ValueError("无效token")
    except Exception as e:
        raise ValueError(f"Token验证失败: {e}")

def extract_client_info(request: Request) -> Dict[str, str]:
    """提取客户端信息"""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "referer": request.headers.get("referer", "unknown"),
        "x_forwarded_for": request.headers.get("x-forwarded-for", "unknown"),
    }

# =============================================================================
# API中间件
# =============================================================================

class SecurityMiddleware:
    """安全中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # 添加安全头
            response = await self.app(scope, receive, send)

            # 这里可以添加响应安全头
            # response.headers["X-Content-Type-Options"] = "nosniff"
            # response.headers["X-Frame-Options"] = "DENY"
            # response.headers["X-XSS-Protection"] = "1; mode=block"

            return response
        else:
            return await self.app(scope, receive, send)

# =============================================================================
# 导出的组件
# =============================================================================

__all__ = [
    # 响应格式
    'APIResponse',

    # 错误码
    'ErrorCodes',

    # 装饰器
    'validate_request', 'require_auth',

    # 审计日志
    'AuditLogger', 'audit_logger',

    # 响应创建
    'create_success_response', 'create_error_response',

    # 工具函数
    'generate_request_id', 'validate_token', 'extract_client_info',

    # 中间件
    'SecurityMiddleware',
]