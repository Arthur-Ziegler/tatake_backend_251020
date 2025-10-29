"""
微服务认证中间件

实现基于微服务的JWT令牌认证，使用微服务公钥进行本地验证。
这个中间件替代原有的本地认证中间件，支持微服务架构。

设计原则：
- 使用微服务JWT验证器
- 保持现有中间件接口兼容性
- 支持降级机制
- 详细的错误处理和日志
"""

from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ...services.auth.jwt_validator import get_jwt_validator


class MicroserviceAuthMiddleware(BaseHTTPMiddleware):
    """
    微服务认证中间件

    提供基于微服务的JWT令牌认证功能，包括：
    - 使用微服务公钥验证JWT令牌
    - 支持公钥缓存机制
    - 自动降级到本地验证
    - 完善的错误处理

    设计思路：
    - 优先使用微服务JWT验证器
    - 缓存公钥，减少网络调用
    - 支持多种JWT算法
    - 保持与原中间件相同的接口
    """

    def __init__(self, app):
        """
        初始化微服务认证中间件

        Args:
            app: FastAPI应用实例
        """
        super().__init__(app)

        # JWT验证器实例（延迟初始化）
        self._jwt_validator = None

        # 公开路径（不需要认证的路径）
        self.public_paths = {
            "/auth/guest/init",
            "/auth/wechat/register",
            "/auth/wechat/login",
            "/auth/email/send-code",
            "/auth/email/register",
            "/auth/email/login",
            "/auth/phone/send-code",
            "/auth/phone/verify",
            "/auth/token/refresh",
            "/auth/system/public-key",
            "/info",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/"
        }

        print("[MicroserviceAuthMiddleware] 初始化微服务认证中间件")

    def _get_jwt_validator(self):
        """
        获取JWT验证器实例（延迟初始化）

        Returns:
            JWT验证器实例
        """
        if self._jwt_validator is None:
            self._jwt_validator = get_jwt_validator()
        return self._jwt_validator

    def _is_public_path(self, path: str) -> bool:
        """
        检查是否为公开路径

        Args:
            path: 请求路径

        Returns:
            True如果是公开路径，False否则
        """
        # 精确匹配
        if path in self.public_paths:
            return True

        # 前缀匹配
        prefix_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        }

        for prefix_path in prefix_paths:
            if path.startswith(prefix_path):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        提取认证令牌

        支持从多个来源提取令牌：
        1. Authorization头部（推荐方式）
        2. 查询参数（临时用途）
        3. Cookie（备用方式）

        Args:
            request: HTTP请求对象

        Returns:
            JWT令牌字符串或None
        """
        # 从Authorization头提取（推荐方式）
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            print(f"[MicroserviceAuthMiddleware] 从Authorization头提取令牌: {token[:20]}...")
            return token

        # 从查询参数提取（临时用途）
        token = request.query_params.get("token")
        if token:
            print(f"[MicroserviceAuthMiddleware] 从查询参数提取令牌: {token[:20]}...")
            return token

        # 从Cookie提取（备用方式）
        token = request.cookies.get("access_token")
        if token:
            print(f"[MicroserviceAuthMiddleware] 从Cookie提取令牌: {token[:20]}...")
            return token

        print(f"[MicroserviceAuthMiddleware] 未提取到令牌")
        return None

    async def dispatch(self, request: Request, call_next):
        """
        验证认证请求

        Args:
            request: HTTP请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            HTTP响应对象

        Raises:
            HTTPException: 认证失败时抛出HTTP异常
        """
        # 检查是否为公开路径
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # 提取令牌
        token = self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        try:
            # 使用微服务JWT验证器验证令牌
            jwt_validator = self._get_jwt_validator()
            payload = await jwt_validator.validate_token(token)

            # 设置用户信息到请求状态
            self._set_user_state(request, payload)

            print(f"[MicroserviceAuthMiddleware] 令牌验证成功: user_id={payload.get('sub')}")

        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录未知错误但不暴露详细信息
            print(f"[MicroserviceAuthMiddleware] 认证验证异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证验证失败",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return await call_next(request)

    def _set_user_state(self, request: Request, payload: Dict[str, Any]) -> None:
        """
        设置用户信息到请求状态

        Args:
            request: HTTP请求对象
            payload: 令牌声明字典
        """
        # 设置用户基本信息
        request.state.user_id = payload.get("sub")
        request.state.is_guest = payload.get("is_guest", False)
        request.state.token_exp = payload.get("exp")
        request.state.token_iat = payload.get("iat")
        request.state.token_jti = payload.get("jti")
        request.state.jwt_version = payload.get("jwt_version", 1)
        request.state.token_type = payload.get("token_type", "access")


# 兼容性别名，保持与原代码的兼容性
AuthMiddleware = MicroserviceAuthMiddleware