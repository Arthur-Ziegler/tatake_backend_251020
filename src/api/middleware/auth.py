"""
认证中间件

实现JWT令牌认证和用户身份验证。
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import config


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.jwt_secret_key = config.jwt_secret_key
        self.jwt_algorithm = config.jwt_algorithm

        # 不需要认证的路径
        self.public_paths = {
            "/api/v1/auth/guest/init",
            "/api/v1/auth/sms/send",
            "/api/v1/auth/login",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/"
        }

    async def dispatch(self, request: Request, call_next):
        """验证认证"""
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
            # 解码令牌
            payload = self._decode_token(token)

            # 设置用户信息到请求状态
            request.state.user_id = payload.get("user_id")
            request.state.user_type = payload.get("user_type", "user")
            request.state.token_exp = payload.get("exp")
            request.state.token_iat = payload.get("iat")

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

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径"""
        # 精确匹配
        if path in self.public_paths:
            return True

        # 前缀匹配
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True

        return False

    def _extract_token(self, request: Request) -> Optional[str]:
        """提取认证令牌"""
        # 从Authorization头提取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]

        # 从查询参数提取（临时用途）
        token = request.query_params.get("token")
        if token:
            return token

        # 从Cookie提取
        token = request.cookies.get("access_token")
        if token:
            return token

        return None

    def _decode_token(self, token: str) -> Dict[str, Any]:
        """解码JWT令牌"""
        return jwt.decode(
            token,
            self.jwt_secret_key,
            algorithms=[self.jwt_algorithm]
        )


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