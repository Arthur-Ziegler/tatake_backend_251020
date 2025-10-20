"""
API限流中间件

实现基于用户和IP的API访问频率限制，防止API滥用。
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import config
from ..responses import create_rate_limit_response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.requests_per_minute = config.rate_limit_requests_per_minute
        self.burst_size = config.rate_limit_burst_size

        # 存储请求计数器
        self.ip_counters: Dict[str, Deque[float]] = defaultdict(deque)
        self.user_counters: Dict[str, Deque[float]] = defaultdict(deque)

        # 最后清理时间
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        """检查限流"""
        if not config.rate_limit_enabled:
            return await call_next(request)

        # 清理过期计数器
        self._cleanup_counters()

        # 获取限制键
        limit_key, limit_type = self._get_limit_key(request)

        # 检查是否超出限制
        if self._is_rate_limited(limit_key, limit_type):
            return create_rate_limit_response()

        # 记录请求
        self._record_request(limit_key, limit_type)

        # 添加限流头信息
        response = await call_next(request)
        self._add_rate_limit_headers(response, limit_key, limit_type)

        return response

    def _get_limit_key(self, request: Request) -> Tuple[str, str]:
        """获取限制键"""
        # 优先使用用户ID
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}", "user"

        # 使用IP地址
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}", "ip"

    def _is_rate_limited(self, limit_key: str, limit_type: str) -> bool:
        """检查是否超出限制"""
        if limit_type == "user":
            counters = self.user_counters
        else:
            counters = self.ip_counters

        requests = counters[limit_key]
        now = time.time()

        # 清理1分钟前的请求
        while requests and requests[0] <= now - 60:
            requests.popleft()

        # 检查请求数量
        return len(requests) >= self.requests_per_minute

    def _record_request(self, limit_key: str, limit_type: str):
        """记录请求"""
        if limit_type == "user":
            counters = self.user_counters
        else:
            counters = self.ip_counters

        counters[limit_key].append(time.time())

    def _add_rate_limit_headers(self, response: Response, limit_key: str, limit_type: str):
        """添加限流头信息"""
        if limit_type == "user":
            counters = self.user_counters
        else:
            counters = self.ip_counters

        # 确保计数器存在
        if limit_key not in counters:
            counters[limit_key] = deque()

        requests = counters[limit_key]
        now = time.time()

        # 清理1分钟前的请求
        while requests and requests[0] <= now - 60:
            requests.popleft()

        # 添加头信息
        response.headers["x-rate-limit-limit"] = str(self.requests_per_minute)
        response.headers["x-rate-limit-remaining"] = str(max(0, self.requests_per_minute - len(requests)))
        response.headers["x-rate-limit-reset"] = str(int(now + 60))

    def _cleanup_counters(self):
        """清理过期计数器"""
        now = time.time()

        # 每分钟清理一次
        if now - self.last_cleanup < 60:
            return

        # 清理IP计数器
        for key in list(self.ip_counters.keys()):
            requests = self.ip_counters[key]
            while requests and requests[0] <= now - 60:
                requests.popleft()
            if not requests:
                del self.ip_counters[key]

        # 清理用户计数器
        for key in list(self.user_counters.keys()):
            requests = self.user_counters[key]
            while requests and requests[0] <= now - 60:
                requests.popleft()
            if not requests:
                del self.user_counters[key]

        self.last_cleanup = now

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


class AdvancedRateLimitMiddleware(RateLimitMiddleware):
    """高级限流中间件（支持分级限制）"""

    def __init__(self, app):
        super().__init__(app)
        # 不同端点的限制配置
        self.endpoint_limits = {
            "/auth/login": {"requests_per_minute": 5, "burst_size": 2},
            "/auth/sms/send": {"requests_per_minute": 3, "burst_size": 1},
            "/auth/guest/init": {"requests_per_minute": 10, "burst_size": 3},
            # 默认限制
            "default": {"requests_per_minute": 60, "burst_size": 10}
        }

    async def dispatch(self, request: Request, call_next):
        """检查分级限流"""
        if not config.rate_limit_enabled:
            return await call_next(request)

        # 获取端点限制配置
        endpoint_config = self._get_endpoint_config(request)

        # 临时更新限制配置
        original_requests_per_minute = self.requests_per_minute
        original_burst_size = self.burst_size

        self.requests_per_minute = endpoint_config["requests_per_minute"]
        self.burst_size = endpoint_config["burst_size"]

        try:
            # 执行限流检查
            return await super().dispatch(request, call_next)
        finally:
            # 恢复原始配置
            self.requests_per_minute = original_requests_per_minute
            self.burst_size = original_burst_size

    def _get_endpoint_config(self, request: Request) -> Dict[str, int]:
        """获取端点限制配置"""
        path = request.url.path

        # 匹配具体路径
        for pattern, config in self.endpoint_limits.items():
            if pattern != "default" and path.startswith(pattern):
                return config

        # 返回默认配置
        return self.endpoint_limits["default"]