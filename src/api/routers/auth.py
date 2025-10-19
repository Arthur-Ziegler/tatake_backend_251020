"""
认证系统API路由

处理用户认证相关请求，包括游客账号初始化、升级、登录、令牌刷新等功能。
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..dependencies import get_current_user, get_optional_current_user
from ..schemas import (
    # 请求模型
    GuestInitRequest,
    GuestUpgradeRequest,
    SMSCodeRequest,
    LoginRequest,
    TokenRefreshRequest,

    # 响应模型
    AuthResponse,
    UserInfoResponse,
    BaseResponse,
    ErrorResponse
)
from ..responses import create_success_response, create_error_response
from ..middleware.auth import create_access_token, create_refresh_token, verify_token
from ..config import config

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


@router.post("/guest/init", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def guest_init(
    request: GuestInitRequest,
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    游客账号初始化

    为新设备创建游客账号，允许用户无需注册即可使用基础功能。

    Args:
        request: 游客初始化请求，包含设备ID和设备信息
        current_user: 当前用户信息（可选）

    Returns:
        AuthResponse: 包含用户信息和认证令牌

    Raises:
        HTTPException: 当设备已存在活跃游客账号时
    """
    try:
        # TODO: 集成AuthService
        # auth_service = get_auth_service()

        # 临时模拟数据
        user_id = f"guest_{datetime.utcnow().timestamp()}"

        # 创建访问令牌
        access_token_expires = timedelta(minutes=config.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "user_id": user_id,
                "user_type": "guest",
                "is_guest": True,
                "device_id": request.device_id
            },
            expires_delta=access_token_expires
        )

        # 创建刷新令牌
        refresh_token = create_refresh_token(
            data={
                "user_id": user_id,
                "user_type": "guest",
                "is_guest": True,
                "device_id": request.device_id
            }
        )

        return create_success_response(
            data=AuthResponse(
                user_id=user_id,
                user_type="guest",
                is_guest=True,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=config.jwt_access_token_expire_minutes * 60,
                token_type="bearer"
            ),
            message="游客账号创建成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"游客账号创建失败: {str(e)}"
        )


@router.post("/guest/upgrade", response_model=AuthResponse)
async def guest_upgrade(
    request: GuestUpgradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    游客账号升级

    将游客账号升级为正式账号，支持手机号、邮箱、微信等多种升级方式。

    Args:
        request: 游客升级请求，包含升级信息和验证码
        current_user: 当前用户信息（必须是游客）

    Returns:
        AuthResponse: 包含更新后的用户信息和新的认证令牌

    Raises:
        HTTPException: 当用户不是游客、验证码错误或升级失败时
    """
    try:
        # 验证当前用户是游客
        if not current_user.get("is_guest"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只有游客账号可以升级"
            )

        # TODO: 集成AuthService进行升级
        # auth_service = get_auth_service()
        # upgraded_user = auth_service.upgrade_guest_account(
        #     current_user["user_id"],
        #     request.dict()
        # )

        # 临时模拟数据
        user_id = current_user["user_id"]

        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=config.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "user_id": user_id,
                "user_type": "registered",
                "is_guest": False,
                "device_id": request.device_id
            },
            expires_delta=access_token_expires
        )

        # 创建新的刷新令牌
        refresh_token = create_refresh_token(
            data={
                "user_id": user_id,
                "user_type": "registered",
                "is_guest": False,
                "device_id": request.device_id
            }
        )

        return create_success_response(
            data=AuthResponse(
                user_id=user_id,
                user_type="registered",
                is_guest=False,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=config.jwt_access_token_expire_minutes * 60,
                token_type="bearer"
            ),
            message="账号升级成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"账号升级失败: {str(e)}"
        )


@router.post("/sms/send", response_model=BaseResponse)
async def send_sms_code(
    request: SMSCodeRequest
):
    """
    发送短信验证码

    向指定手机号发送验证码，支持登录、注册、找回密码等场景。

    Args:
        request: 短信验证码请求，包含手机号和验证码类型

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当手机号格式错误、发送频率限制或发送失败时
    """
    try:
        # TODO: 集成AuthService发送验证码
        # auth_service = get_auth_service()
        # auth_service.send_sms_code(request.phone, request.type)

        # 临时模拟发送成功
        return create_success_response(
            message="验证码发送成功，请注意查收"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证码发送失败: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest
):
    """
    用户登录

    支持多种登录方式：手机号+验证码、邮箱+验证码、微信授权等。

    Args:
        request: 登录请求，包含登录类型、凭证和验证码

    Returns:
        AuthResponse: 包含用户信息和认证令牌

    Raises:
        HTTPException: 当登录凭证错误、验证码失效或登录失败时
    """
    try:
        # TODO: 集成AuthService进行登录验证
        # auth_service = get_auth_service()
        # user_info = auth_service.authenticate_user(request.dict())

        # 临时模拟登录成功
        user_id = f"user_{datetime.utcnow().timestamp()}"
        user_type = "registered" if request.login_type != "guest" else "guest"

        # 创建访问令牌
        access_token_expires = timedelta(minutes=config.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "user_id": user_id,
                "user_type": user_type,
                "is_guest": False,
                "device_id": request.device_id
            },
            expires_delta=access_token_expires
        )

        # 创建刷新令牌
        refresh_token = create_refresh_token(
            data={
                "user_id": user_id,
                "user_type": user_type,
                "is_guest": False,
                "device_id": request.device_id
            }
        )

        return create_success_response(
            data=AuthResponse(
                user_id=user_id,
                user_type=user_type,
                is_guest=False,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=config.jwt_access_token_expire_minutes * 60,
                token_type="bearer"
            ),
            message="登录成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: TokenRefreshRequest
):
    """
    刷新访问令牌

    使用刷新令牌获取新的访问令牌，延长用户的登录状态。

    Args:
        request: 令牌刷新请求，包含刷新令牌

    Returns:
        dict: 包含新的访问令牌和过期时间

    Raises:
        HTTPException: 当刷新令牌无效、过期或已被撤销时
    """
    try:
        # 验证刷新令牌
        payload = verify_token(request.refresh_token)

        # 检查令牌类型
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌类型"
            )

        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=config.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "user_id": payload["user_id"],
                "user_type": payload["user_type"],
                "is_guest": payload.get("is_guest", False),
                "device_id": payload.get("device_id")
            },
            expires_delta=access_token_expires
        )

        return create_success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": config.jwt_access_token_expire_minutes * 60
            },
            message="令牌刷新成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌刷新失败: {str(e)}"
        )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    用户登出

    使访问令牌失效，清理用户会话数据。

    Args:
        credentials: HTTP认证凭证（可选）
        current_user: 当前用户信息（可选）

    Returns:
        BaseResponse: 操作结果
    """
    try:
        # TODO: 集成AuthService处理登出
        # auth_service = get_auth_service()
        # if current_user:
        #     auth_service.logout_user(current_user["user_id"])

        return create_success_response(
            message="登出成功"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登出失败: {str(e)}"
        )


@router.get("/user-info", response_model=UserInfoResponse)
async def get_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户信息

    根据当前用户的认证令牌返回用户基本信息。

    Args:
        current_user: 当前用户信息

    Returns:
        UserInfoResponse: 用户详细信息

    Raises:
        HTTPException: 当用户不存在或令牌无效时
    """
    try:
        # TODO: 集成UserService获取用户信息
        # user_service = get_user_service()
        # user_info = user_service.get_user_profile(current_user["user_id"])

        # 临时模拟用户数据
        user_info = {
            "user_id": current_user["user_id"],
            "user_type": current_user.get("user_type", "guest"),
            "is_guest": current_user.get("is_guest", True),
            "phone": None,
            "email": None,
            "display_name": None,
            "avatar_url": None,
            "created_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow()
        }

        return create_success_response(
            data=UserInfoResponse(**user_info),
            message="获取用户信息成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户信息失败: {str(e)}"
        )