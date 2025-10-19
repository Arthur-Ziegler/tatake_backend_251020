"""
安全中间件

实现各种安全增强功能，包括安全头设置、CSRF保护等。
"""

import secrets
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import config


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.csrf_tokens = {}

    async def dispatch(self, request: Request, call_next):
        """添加安全头和CSRF保护"""
        # 生成CSRF令牌
        if config.csrf_protection:
            csrf_token = self._generate_or_get_csrf_token(request)
            request.state.csrf_token = csrf_token

        # 处理请求
        response = await call_next(request)

        # 添加安全头
        self._add_security_headers(response, request)

        # 设置CSRF令牌
        if config.csrf_protection:
            self._set_csrf_token(response, request)

        return response

    def _generate_or_get_csrf_token(self, request: Request) -> str:
        """生成或获取CSRF令牌"""
        # 从Cookie获取现有令牌
        existing_token = request.cookies.get("csrf_token")
        if existing_token and self._is_valid_csrf_token(existing_token):
            return existing_token

        # 生成新令牌
        return secrets.token_urlsafe(32)

    def _is_valid_csrf_token(self, token: str) -> bool:
        """验证CSRF令牌格式"""
        # 简单的格式验证
        return len(token) >= 32 and token.isalnum()

    def _add_security_headers(self, response: Response, request: Request):
        """添加安全头"""
        # 防止MIME类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 启用XSS保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 限制引用来源
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 内容安全策略
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS（仅在HTTPS下）
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 权限策略
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy

    def _set_csrf_token(self, response: Response, request: Request):
        """设置CSRF令牌"""
        if hasattr(request.state, "csrf_token"):
            csrf_token = request.state.csrf_token
            # 设置CSRF令牌Cookie
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                max_age=3600,  # 1小时
                secure=config.secure_cookies,
                httponly=True,
                samesite="strict"
            )
            # 在响应头中添加令牌（方便前端获取）
            response.headers["X-CSRF-Token"] = csrf_token


class InputValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件"""

    def __init__(self, app):
        super().__init__(app)
        # 危险字符串模式
        self.dangerous_patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"javascript:",  # JavaScript协议
            r"vbscript:",  # VBScript协议
            r"onload\s*=",  # 事件处理器
            r"onerror\s*=",  # 错误处理器
            r"onclick\s*=",  # 点击处理器
            r"union\s+select",  # SQL注入
            r"drop\s+table",  # SQL删除
            r"insert\s+into",  # SQL插入
            r"update\s+set",  # SQL更新
            r"delete\s+from",  # SQL删除
        ]

    async def dispatch(self, request: Request, call_next):
        """验证输入数据"""
        # 检查查询参数
        if request.query_params:
            if self._contains_dangerous_content(dict(request.query_params)):
                from ..responses import create_error_response
                return create_error_response(
                    message="请求参数包含非法内容",
                    status_code=400,
                    error_code="INVALID_INPUT"
                )

        # 检查请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                try:
                    body = await request.json()
                    if self._contains_dangerous_content(body):
                        from ..responses import create_error_response
                        return create_error_response(
                            message="请求体包含非法内容",
                            status_code=400,
                            error_code="INVALID_INPUT"
                        )
                except:
                    # JSON解析失败，让其他中间件处理
                    pass

        # 处理请求
        return await call_next(request)

    def _contains_dangerous_content(self, data: dict) -> bool:
        """检查是否包含危险内容"""
        import re

        def check_value(value):
            if isinstance(value, str):
                # 检查危险模式
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
            elif isinstance(value, dict):
                for v in value.values():
                    if check_value(v):
                        return True
            elif isinstance(value, list):
                for item in value:
                    if check_value(item):
                        return True
            return False

        return check_value(data)