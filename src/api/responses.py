"""
统一API响应格式

定义所有API响应的统一格式，包括成功响应和错误响应。
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def _convert_datetime_to_string(obj: Any) -> Any:
    """递归转换datetime对象为ISO字符串"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_to_string(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_datetime_to_string(item) for item in obj)
    else:
        return obj


class ApiResponse(BaseModel):
    """统一API响应模型"""
    code: int
    message: str
    data: Optional[Any] = None
    timestamp: str
    trace_id: str


class SuccessResponse(ApiResponse):
    """成功响应"""

    @classmethod
    def create(
        cls,
        data: Any = None,
        message: str = "操作成功",
        code: int = 200
    ) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "traceId": str(uuid.uuid4())
        }


class ErrorResponse(ApiResponse):
    """错误响应"""

    @classmethod
    def create(
        cls,
        message: str,
        code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        response_data = {
            "code": code,
            "message": message,
            "data": None,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "traceId": str(uuid.uuid4())
        }

        if details:
            response_data["details"] = details

        if error_code:
            response_data["errorCode"] = error_code

        return response_data


class ValidationErrorResponse(ErrorResponse):
    """参数验证错误响应"""

    @classmethod
    def create(cls, validation_errors: Dict[str, Any]) -> Dict[str, Any]:
        """创建验证错误响应"""
        return super().create(
            message="参数验证失败",
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=validation_errors,
            error_code="VALIDATION_ERROR"
        )


class NotFoundErrorResponse(ErrorResponse):
    """资源未找到错误响应"""

    @classmethod
    def create(cls, resource: str = "资源") -> Dict[str, Any]:
        """创建未找到错误响应"""
        return super().create(
            message=f"{resource}未找到",
            code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND"
        )


class UnauthorizedErrorResponse(ErrorResponse):
    """未授权错误响应"""

    @classmethod
    def create(cls, message: str = "未授权访问") -> Dict[str, Any]:
        """创建未授权错误响应"""
        return super().create(
            message=message,
            code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED"
        )


class ForbiddenErrorResponse(ErrorResponse):
    """禁止访问错误响应"""

    @classmethod
    def create(cls, message: str = "禁止访问") -> Dict[str, Any]:
        """创建禁止访问响应"""
        return super().create(
            message=message,
            code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN"
        )


class InternalServerErrorResponse(ErrorResponse):
    """内部服务器错误响应"""

    @classmethod
    def create(cls, message: str = "内部服务器错误") -> Dict[str, Any]:
        """创建内部错误响应"""
        return super().create(
            message=message,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR"
        )


class RateLimitErrorResponse(ErrorResponse):
    """限流错误响应"""

    @classmethod
    def create(cls) -> Dict[str, Any]:
        """创建限流错误响应"""
        return super().create(
            message="请求过于频繁，请稍后再试",
            code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED"
        )


def create_success_response(
    data: Any = None,
    message: str = "操作成功",
    status_code: int = status.HTTP_200_OK,
    trace_id: Optional[str] = None
) -> JSONResponse:
    """创建成功响应"""
    if trace_id:
        response_data = SuccessResponse.create(data=data, message=message, code=status_code)
        response_data["traceId"] = trace_id
    else:
        response_data = SuccessResponse.create(data=data, message=message, code=status_code)
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def create_error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> JSONResponse:
    """创建错误响应"""
    # 转换details中的datetime对象为字符串
    if details:
        details = _convert_datetime_to_string(details)

    response_data = ErrorResponse.create(
        message=message,
        code=status_code,
        details=details,
        error_code=error_code
    )
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )


def create_validation_error_response(
    validation_errors: Dict[str, Any]
) -> JSONResponse:
    """创建验证错误响应"""
    response_data = ValidationErrorResponse.create(validation_errors)
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def create_not_found_response(
    resource: str = "资源"
) -> JSONResponse:
    """创建未找到响应"""
    response_data = NotFoundErrorResponse.create(resource)
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_404_NOT_FOUND
    )


def create_unauthorized_response(
    message: str = "未授权访问"
) -> JSONResponse:
    """创建未授权响应"""
    response_data = UnauthorizedErrorResponse.create(message)
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def create_forbidden_response(
    message: str = "禁止访问"
) -> JSONResponse:
    """创建禁止访问响应"""
    response_data = ForbiddenErrorResponse.create(message)
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_403_FORBIDDEN
    )


def create_internal_server_error_response(
    message: str = "内部服务器错误"
) -> JSONResponse:
    """创建内部错误响应"""
    response_data = InternalServerErrorResponse.create(message)
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def create_rate_limit_response() -> JSONResponse:
    """创建限流响应"""
    response_data = RateLimitErrorResponse.create()
    return JSONResponse(
        content=response_data,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )