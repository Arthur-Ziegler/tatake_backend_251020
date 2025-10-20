"""
CORS中间件

处理跨域资源共享配置，允许前端应用访问API。
"""

from typing import List

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from ..config import config


class CORSMiddleware(BaseHTTPMiddleware):
    """自定义CORS中间件"""

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.allowed_origins = config.allowed_origins
        self.allowed_methods = config.allowed_methods
        self.allowed_headers = config.allowed_headers

    async def dispatch(self, request: Request, call_next):
        """处理CORS请求"""
        origin = request.headers.get("origin")

        # 处理预检请求 - 直接返回响应，不需要继续传递
        if request.method == "OPTIONS":
            response = StarletteResponse()
            response.headers["Access-Control-Allow-Origin"] = self._get_allowed_origin(origin)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            response.headers["Access-Control-Max-Age"] = "86400"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # 处理普通请求
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = self._get_allowed_origin(origin)
        response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    def _get_allowed_origin(self, origin: str) -> str:
        """获取允许的源"""
        if not origin:
            return "null"

        # 检查是否在允许列表中
        if origin in self.allowed_origins:
            return origin

        # 检查通配符
        for allowed_origin in self.allowed_origins:
            if allowed_origin == "*" or self._matches_pattern(origin, allowed_origin):
                return origin

        return "null"

    def _matches_pattern(self, origin: str, pattern: str) -> bool:
        """检查源是否匹配模式"""
        if not pattern.startswith("*"):
            return False

        # 简单的通配符匹配
        suffix = pattern[1:]
        return origin.endswith(suffix)


def add_cors_middleware(app: FastAPI):
    """添加CORS中间件到FastAPI应用"""
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=config.allowed_methods,
        allow_headers=config.allowed_headers,
        expose_headers=["X-Total-Count", "X-Trace-ID"]
    )