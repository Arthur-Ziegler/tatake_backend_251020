"""
简化认证领域API路由

根据设计文档，API大幅简化：
1. 统一响应格式：所有端点返回{code, data, message}
2. 只保留5个核心端点，移除复杂功能
3. 微信单一登录：只支持微信OpenID认证
4. 极简化设计：删除SMS、用户信息等非核心端点

API端点:
1. POST /auth/guest/init - 游客账号初始化
2. POST /auth/register - 微信注册
3. POST /auth/login - 微信登录
4. POST /auth/guest/upgrade - 游客账号升级
5. POST /auth/refresh - 刷新访问令牌

移除的端点:
- DELETE /auth/logout - 移除登出功能
- GET /auth/user-info - 移除用户信息查询
- POST /auth/sms/send - 移除短信验证码
- 所有基于设备信息的操作

设计原则:
- RESTful设计
- 统一错误处理
- 详细参数验证
- 完整文档说明
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Request, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from jose import JWTError, jwt

from .service import AuthService
from .schemas import (
    # 请求模型
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,

    # 响应模型
    AuthTokenResponse,
    UnifiedResponse
)
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    ValidationError
)

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案（可选）
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    从JWT令牌中获取当前用户ID

    用于需要认证的端点。
    如果令牌无效，抛出HTTPException。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证令牌"
        )

    try:
        # 解码JWT令牌
        secret_key = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here")
        payload = jwt.decode(
            credentials.credentials,
            secret_key,
            algorithms=["HS256"]
        )

        # 验证令牌类型
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌类型错误"
            )

        user_id = UUID(payload.get("sub"))
        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式错误"
        )


def create_success_response(data: Dict[str, Any]) -> JSONResponse:
    """创建统一成功响应"""
    response = UnifiedResponse(
        code=200,
        data=data,
        message="success"
    )
    return JSONResponse(content=response.model_dump(), status_code=200)


def create_error_response(status_code: int, message: str, data: Dict[str, Any] = None) -> JSONResponse:
    """创建统一错误响应"""
    response = UnifiedResponse(
        code=status_code,
        data=data,
        message=message
    )
    return JSONResponse(content=response.model_dump(), status_code=status_code)


# ===== API端点实现 =====

@router.post(
    "/guest/init",
    response_model=UnifiedResponse,
    summary="游客账号初始化",
    description="创建一个新的游客账号，无需任何参数。每次请求都创建全新的随机游客身份。"
)
async def guest_init(
    request: Request
) -> JSONResponse:
    """
    游客账号初始化

    根据设计文档，这个端点不接受任何请求体参数，
    直接创建新的游客账号并返回认证令牌。
    """
    try:
        # 获取客户端信息
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # 初始化游客账号
        auth_service = AuthService()
        result = auth_service.init_guest_account(
            request=GuestInitRequest(),
            ip_address=ip_address,
            user_agent=user_agent
        )

        return create_success_response(result)

    except AuthenticationException as e:
        return create_error_response(401, str(e))


@router.post(
    "/register",
    response_model=UnifiedResponse,
    summary="微信用户注册",
    description="通过微信OpenID注册新用户。内部实现为创建游客账号并立即升级为正式用户，包含完整的用户初始化流程。"
)
async def wechat_register(
    request: WeChatRegisterRequest,
    http_request: Request
) -> JSONResponse:
    """
    微信注册

    根据设计文档，这是"创建游客 + 立即升级"的组合操作。
    客户端只需要提供微信openid。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行微信注册
        auth_service = AuthService()
        result = auth_service.wechat_register(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return create_success_response(result)

    except ValidationError as e:
        return create_error_response(400, str(e))
    except AuthenticationException as e:
        return create_error_response(401, str(e))


@router.post(
    "/login",
    response_model=UnifiedResponse,
    summary="微信用户登录",
    description="通过微信OpenID登录已有用户账号。支持新用户自动注册和已有用户登录，返回JWT访问令牌。"
)
async def wechat_login(
    http_request: Request,
    request: WeChatLoginRequest = Body(..., examples={
        "NormalLogin": {
            "summary": "标准微信登录",
            "description": "使用有效的微信OpenID登录系统",
            "value": {
                "wechat_openid": "ox1234567890abcdef1234567890abcdef"
            }
        },
        "NewUserLogin": {
            "summary": "新用户首次登录",
            "description": "新用户首次使用微信登录，系统会自动创建账号",
            "value": {
                "wechat_openid": "ox0987654321fedcba0987654321fedcba"
            }
        }
    })
) -> JSONResponse:
    """
    微信登录

    通过微信OpenID进行身份验证并返回认证令牌。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行微信登录
        auth_service = AuthService()
        result = auth_service.wechat_login(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return create_success_response(result)

    except UserNotFoundException as e:
        return create_error_response(404, str(e))
    except ValidationError as e:
        return create_error_response(400, str(e))
    except AuthenticationException as e:
        return create_error_response(401, str(e))


@router.post(
    "/guest/upgrade",
    response_model=UnifiedResponse,
    summary="游客账号升级",
    description="将当前游客账号升级为正式用户，需要提供微信OpenID。",
    dependencies=[Depends(get_current_user_id)]
)
async def upgrade_guest(
    request: GuestUpgradeRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    http_request: Request = None
) -> JSONResponse:
    """
    游客账号升级

    需要有效的访问令牌，将当前游客账号与微信OpenID绑定。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行游客升级
        auth_service = AuthService()
        result = auth_service.upgrade_guest_account(
            request=request,
            current_user_id=current_user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return create_success_response(result)

    except UserNotFoundException as e:
        return create_error_response(404, str(e))
    except ValidationError as e:
        return create_error_response(400, str(e))
    except AuthenticationException as e:
        return create_error_response(401, str(e))


@router.post(
    "/refresh",
    response_model=UnifiedResponse,
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌。"
)
async def refresh_token(
    request: TokenRefreshRequest,
    http_request: Request
) -> JSONResponse:
    """
    刷新访问令牌

    使用有效的刷新令牌获取新的访问令牌和刷新令牌。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行令牌刷新
        auth_service = AuthService()
        result = auth_service.refresh_token(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return create_success_response(result)

    except TokenException as e:
        return create_error_response(401, str(e))
    except AuthenticationException as e:
        return create_error_response(401, str(e))


# ===== 依赖注入函数 =====

async def create_auth_service() -> AuthService:
    """创建认证服务实例（依赖注入）"""
    return AuthService()


# ===== 移除的端点注释 =====
# 以下端点已被移除，原因：
# - DELETE /auth/logout: 移除登出功能
# - GET /auth/user-info: 移除用户信息查询
# - POST /auth/sms/send: 移除短信验证码发送
# - 所有与设备信息相关的操作端点
# - 复杂的密码登录、多平台登录端点