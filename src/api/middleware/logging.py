"""
日志中间件

记录所有API请求和响应的日志，包括请求时间、响应时间、
状态码、用户信息等。
"""

import time
import uuid
from typing import Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import config


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.start_time = time.time()

    async def dispatch(self, request: Request, call_next):
        """记录请求和响应日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录开始时间
        start_time = time.time()

        # 提取请求信息
        request_info = await self._extract_request_info(request)

        # 记录请求日志
        self._log_request(request_id, request_info)

        try:
            # 处理请求
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 提取响应信息
            response_info = self._extract_response_info(response, process_time)

            # 记录响应日志
            self._log_response(request_id, response_info)

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"

            return response

        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录错误日志
            self._log_error(request_id, request_info, e, process_time)

            # 重新抛出异常
            raise

    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """提取请求信息"""
        # 基础信息
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "content_type": request.headers.get("content-type", ""),
            "content_length": request.headers.get("content-length", "0")
        }

        # 用户信息（如果已认证）
        if hasattr(request.state, "user_id"):
            request_info["user_id"] = request.state.user_id

        # 请求参数
        try:
            if request.method in ["GET", "DELETE"]:
                request_info["query_params"] = dict(request.query_params)
            elif request.method in ["POST", "PUT", "PATCH"]:
                if request.headers.get("content-type", "").startswith("application/json"):
                    try:
                        body = await request.json()
                        request_info["body"] = self._sanitize_body(body)
                    except:
                        request_info["body"] = "[解析失败]"
                else:
                    request_info["body"] = f"[二进制数据，大小: {request.headers.get('content-length', '0')}字节]"
        except Exception:
            pass

        return request_info

    def _extract_response_info(self, response: Response, process_time: float) -> Dict[str, Any]:
        """提取响应信息"""
        return {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": response.headers.get("content-length", "0"),
            "process_time_ms": round(process_time * 1000, 2)
        }

    def _log_request(self, request_id: str, request_info: Dict[str, Any]):
        """记录请求日志"""
        message = f"API请求开始: {request_info['method']} {request_info['url']}"

        # 结构化日志
        log_data = {
            "request_id": request_id,
            "event": "request_start",
            **request_info
        }

        if config.log_format == "json":
            print(json.dumps(log_data, ensure_ascii=False))
        else:
            print(f"[{request_id}] {message}")
            print(f"  客户端IP: {request_info['client_ip']}")
            print(f"  用户代理: {request_info['user_agent']}")

    def _log_response(self, request_id: str, response_info: Dict[str, Any]):
        """记录响应日志"""
        message = f"API请求完成: 状态码 {response_info['status_code']}, 耗时 {response_info['process_time_ms']}ms"

        # 结构化日志
        log_data = {
            "request_id": request_id,
            "event": "request_end",
            **response_info
        }

        if config.log_format == "json":
            print(json.dumps(log_data, ensure_ascii=False))
        else:
            print(f"[{request_id}] {message}")

    def _log_error(self, request_id: str, request_info: Dict[str, Any], error: Exception, process_time: float):
        """记录错误日志"""
        message = f"API请求失败: {type(error).__name__}: {str(error)}"

        # 结构化日志
        log_data = {
            "request_id": request_id,
            "event": "request_error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "process_time_ms": round(process_time * 1000, 2),
            **request_info
        }

        if config.log_format == "json":
            print(json.dumps(log_data, ensure_ascii=False))
        else:
            print(f"[{request_id}] ERROR: {message}")

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 返回直连IP
        return request.client.host if request.client else "unknown"

    def _sanitize_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """清理请求体，移除敏感信息"""
        sensitive_fields = ["password", "token", "secret", "key", "auth"]

        if isinstance(body, dict):
            sanitized = {}
            for key, value in body.items():
                if any(field in key.lower() for field in sensitive_fields):
                    sanitized[key] = "***"
                else:
                    sanitized[key] = value
            return sanitized

        return body


# 导入json模块
import json