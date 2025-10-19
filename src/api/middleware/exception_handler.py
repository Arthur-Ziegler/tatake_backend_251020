"""
异常处理中间件

统一处理API中的所有异常，生成标准化的错误响应。
"""

import traceback
from typing import Dict, Any, Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..responses import (
    create_validation_error_response,
    create_error_response,
    create_internal_server_error_response
)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """异常处理中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理异常"""
        try:
            response = await call_next(request)
            return response

        except RequestValidationError as e:
            # 参数验证异常
            return self._handle_validation_error(e, request)

        except StarletteHTTPException as e:
            # HTTP异常
            return self._handle_http_exception(e, request)

        except Exception as e:
            # 其他异常
            return self._handle_general_exception(e, request)

    def _handle_validation_error(self, e: RequestValidationError, request: Request) -> Response:
        """处理参数验证错误"""
        errors = {}
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors[field] = {
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            }

        return create_validation_error_response(errors)

    def _handle_http_exception(self, e: StarletteHTTPException, request: Request) -> Response:
        """处理HTTP异常"""
        return create_error_response(
            message=e.detail,
            status_code=e.status_code,
            error_code=f"HTTP_{e.status_code}"
        )

    def _handle_general_exception(self, e: Exception, request: Request) -> Response:
        """处理一般异常"""
        # 记录异常信息
        self._log_exception(e, request)

        # 返回通用错误响应
        return create_internal_server_error_response(
            message="服务器内部错误，请稍后重试"
        )

    def _log_exception(self, e: Exception, request: Request):
        """记录异常信息"""
        request_id = getattr(request.state, "request_id", "unknown")

        error_info = {
            "request_id": request_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "url": str(request.url),
            "method": request.method,
            "client_ip": self._get_client_ip(request)
        }

        # 记录到日志
        import json
        print(json.dumps({
            "event": "exception",
            **error_info
        }, ensure_ascii=False))

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"