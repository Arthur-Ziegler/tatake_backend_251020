"""
认证中间件

实现JWT令牌认证和用户身份验证，支持真实JWT验证、数据库令牌黑名单检查、
令牌自动刷新等功能。
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import config
from src.services.jwt_service import JWTService
from src.repositories.auth import TokenBlacklistRepository
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import State


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件类

    提供JWT令牌认证和用户身份验证功能，包括：
    - 真实JWT令牌验证
    - 数据库令牌黑名单检查
    - 令牌自动刷新机制
    - 完善的错误处理
    """

    def __init__(self, app, db_session: Optional[AsyncSession] = None):
        """
        初始化认证中间件

        Args:
            app: FastAPI应用实例
            db_session: 数据库会话（可选，用于黑名单检查）
        """
        super().__init__(app)

        # 使用安全的JWT配置
        jwt_config = config.get_secure_jwt_config()
        self.jwt_service = JWTService(
            token_blacklist_repo=TokenBlacklistRepository(db_session) if db_session else None,
            **jwt_config
        )

        self.db_session = db_session

        # 不需要认证的路径
        self.public_paths = {
            "/api/v1/auth/guest/init",
            "/api/v1/auth/sms/send",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/"
        }

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

        # 提取并验证令牌
        token = self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )

        try:
            # 使用真实JWT服务验证令牌
            payload = await self._verify_token_with_blacklist(token)

            # 检查令牌是否即将过期，如果需要则触发自动刷新
            await self._check_token_refresh(request, payload)

            # 设置用户信息到请求状态
            self._set_user_state(request, payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证令牌已过期",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的认证令牌: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            # 记录未知错误但不暴露详细信息
            print(f"[AuthMiddleware] 认证验证异常: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证验证失败",
                headers={"WWW-Authenticate": "Bearer"}
            )

        return await call_next(request)

    async def _verify_token_with_blacklist(self, token: str) -> Dict[str, Any]:
        """
        验证JWT令牌并检查黑名单

        Args:
            token: JWT令牌字符串

        Returns:
            解码后的令牌声明字典

        Raises:
            jwt.InvalidTokenError: 令牌无效或被撤销时
        """
        # 使用JWT服务验证访问令牌
        if self.db_session:
            payload = await self.jwt_service.verify_access_token_async(token)
        else:
            # 如果没有数据库会话，使用同步验证（不支持黑名单检查）
            payload = self.jwt_service.verify_access_token(token)

        return payload

    async def _check_token_refresh(self, request: Request, payload: Dict[str, Any]) -> None:
        """
        检查令牌是否需要刷新

        如果令牌即将过期（比如5分钟内过期），设置刷新标志。

        Args:
            request: HTTP请求对象
            payload: 令牌声明字典
        """
        try:
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
                now = datetime.now(timezone.utc)
                time_remaining = exp_datetime - now

                # 如果令牌在5分钟内过期，设置刷新标志
                if time_remaining.total_seconds() < 300:  # 5分钟
                    request.state.token_needs_refresh = True
                    print(f"[AuthMiddleware] 令牌将在 {time_remaining.total_seconds():.0f} 秒后过期，建议刷新")

        except Exception as e:
            # 刷新检查失败不应该阻止请求继续
            print(f"[AuthMiddleware] 令牌刷新检查失败: {str(e)}")

    def _set_user_state(self, request: Request, payload: Dict[str, Any]) -> None:
        """
        设置用户信息到请求状态

        Args:
            request: HTTP请求对象
            payload: 令牌声明字典
        """
        # 设置用户基本信息
        request.state.user_id = payload.get("user_id")
        request.state.user_type = payload.get("user_type", "user")
        request.state.token_exp = payload.get("exp")
        request.state.token_iat = payload.get("iat")
        request.state.token_jti = payload.get("jti")
        request.state.iss = payload.get("iss")
        request.state.aud = payload.get("aud")

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
        # 避免错误匹配 /api/v1/auth 开头路径到 /api/v1/tasks
        prefix_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health"
        }

        for prefix_path in prefix_paths:
            if path.startswith(prefix_path):
                return True

        # 对于认证相关路径，需要更精确的匹配
        auth_public_paths = {
            "/api/v1/auth/guest/init",
            "/api/v1/auth/sms/send",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh"
        }

        # 认证路径只允许精确匹配，不允许前缀匹配
        if path in auth_public_paths:
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
            return auth_header[7:]

        # 从查询参数提取（临时用途）
        token = request.query_params.get("token")
        if token:
            return token

        # 从Cookie提取（备用方式）
        token = request.cookies.get("access_token")
        if token:
            return token

        return None


class RefreshTokenMiddleware(BaseHTTPMiddleware):
    """刷新令牌中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.refresh_token_paths = {
            "/api/v1/auth/refresh"
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

        try:
            # 验证刷新令牌
            payload = jwt.decode(
                refresh_token,
                config.jwt_secret_key,
                algorithms=[config.jwt_algorithm]
            )

            # 检查令牌类型
            if payload.get("token_type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的刷新令牌类型"
                )

            # 设置用户信息
            request.state.user_id = payload.get("user_id")
            request.state.user_type = payload.get("user_type", "user")
            request.state.refresh_token = refresh_token

            return await call_next(request)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已过期"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"无效的刷新令牌: {str(e)}"
            )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=config.jwt_access_token_expire_minutes
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "access"
    })

    return jwt.encode(
        to_encode,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )


def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        days=config.jwt_refresh_token_expire_days
    )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "token_type": "refresh"
    })

    return jwt.encode(
        to_encode,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm
    )


def verify_token(token: str) -> Dict[str, Any]:
    """
    验证JWT令牌

    注意：这个函数为了保持向后兼容性而保留。
    新代码应该使用JWTService进行令牌验证。
    """
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algorithm],
            options={
                'require': ['exp', 'iat', 'sub'],
                'verify_aud': False,  # 为了兼容性暂时不验证aud
                'verify_iss': False   # 为了兼容性暂时不验证iss
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"无效令牌: {str(e)}"
        )