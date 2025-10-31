"""
认证中间件

重构为透传模式，统一使用 JWTValidator 进行令牌验证。
移除重复的验证逻辑，简化为轻量级的认证层。
"""

from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.auth.jwt_validator import validate_jwt_token_simple


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件类（透传模式）

    重构后的轻量级认证中间件：
    - 统一使用 JWTValidator 进行令牌验证
    - 移除重复的验证逻辑
    - 简化为透传模式
    - 保持API兼容性
    """

    def __init__(self, app):
        """
        初始化认证中间件

        Args:
            app: FastAPI应用实例
        """
        super().__init__(app)

        # 不需要认证的路径
        self.public_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/",
            "/static"
        }

    async def dispatch(self, request: Request, call_next):
        """
        验证认证请求（透传模式）

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
            # 使用统一的JWT验证器验证令牌
            payload = await validate_jwt_token_simple(token)

            # 设置用户信息到请求状态（保持向后兼容）
            self._set_user_state(request, payload)

        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录未知错误但不暴露详细信息
            print(f"[AuthMiddleware] 认证验证异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证验证失败",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return await call_next(request)

    def _set_user_state(self, request: Request, payload: dict) -> None:
        """
        设置用户信息到请求状态（保持向后兼容）

        Args:
            request: HTTP请求对象
            payload: 令牌声明字典
        """
        # 设置用户基本信息
        request.state.user_id = payload.get("sub")
        request.state.user_type = "guest" if payload.get("is_guest", True) else "user"
        request.state.token_exp = payload.get("exp")
        request.state.token_iat = payload.get("iat")
        request.state.is_guest = payload.get("is_guest", True)

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

        # 前缀匹配 - 仅对特定需要子路径的公开路径进行前缀匹配
        prefix_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/static"
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
            print(f"[AuthMiddleware] 从Authorization头提取令牌: {token[:20]}...")
            return token

        # 从查询参数提取（临时用途）
        token = request.query_params.get("token")
        if token:
            print(f"[AuthMiddleware] 从查询参数提取令牌: {token[:20]}...")
            return token

        # 从Cookie提取（备用方式）
        token = request.cookies.get("access_token")
        if token:
            print(f"[AuthMiddleware] 从Cookie提取令牌: {token[:20]}...")
            return token

        print(f"[AuthMiddleware] 未提取到令牌")
        return None


class RefreshTokenMiddleware(BaseHTTPMiddleware):
    """
    刷新令牌中间件（简化版）

    保留刷新令牌的特殊处理逻辑，但简化实现。
    """

    def __init__(self, app):
        super().__init__(app)
        self.refresh_token_paths = {
            "/auth/token/refresh"
        }

    async def dispatch(self, request: Request, call_next):
        """处理刷新令牌"""
        if request.url.path in self.refresh_token_paths:
            # 特殊处理刷新令牌逻辑
            return await self._handle_refresh_token(request, call_next)

        return await call_next(request)

    async def _handle_refresh_token(self, request: Request, call_next):
        """处理刷新令牌请求"""
        # 从请求体或Cookie获取刷新令牌
        refresh_token = None

        # 尝试从请求体获取
        if request.method == "POST":
            try:
                body = await request.json()
                refresh_token = body.get("refresh_token")
            except:
                pass

        # 尝试从Cookie获取
        if not refresh_token:
            refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少刷新令牌"
            )

        # 设置刷新令牌到请求状态，让后续处理使用
        request.state.refresh_token = refresh_token

        return await call_next(request)