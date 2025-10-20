"""
认证系统API路由

处理用户认证相关请求，包括游客账号初始化、升级、登录、令牌刷新等功能。
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..dependencies import get_current_user, get_optional_current_user, get_auth_service, get_async_auth_service, get_jwt_service
from src.services import AuthService, JWTService
from src.services.async_auth_service import AsyncAuthService
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
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """
    游客账号初始化

    为新设备创建游客账号，允许用户无需注册即可使用基础功能。

    Args:
        request: 游客初始化请求，包含设备ID和设备信息
        auth_service: 认证服务实例
        jwt_service: JWT服务实例

    Returns:
        AuthResponse: 包含用户信息和认证令牌

    Raises:
        HTTPException: 当设备已存在活跃游客账号时
    """
    try:
        # 使用AuthService创建游客账号
        guest_data = auth_service.init_guest_account(
            device_id=request.device_id,
            platform=request.platform
        )

        # 使用JWT服务生成令牌
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=guest_data["user_id"],
            user_type="guest",
            additional_claims={
                "is_guest": True,
                "device_id": request.device_id,
                "platform": request.platform
            }
        )

        return create_success_response(
            data=AuthResponse(
                user_id=guest_data["user_id"],
                user_type="guest",
                is_guest=True,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=config.jwt_access_token_expire_minutes * 60,
                token_type="bearer"
            ),
            message="游客账号创建成功"
        )

    except Exception as e:
        # 记录详细错误信息
        print(f"[GuestInit] 游客账号初始化失败: {str(e)}")

        # 根据异常类型返回不同的HTTP状态码
        if "已存在" in str(e) or "exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该设备已存在活跃游客账号"
            )
        elif "限制" in str(e) or "limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"游客账号创建失败: {str(e)}"
            )


@router.post("/guest/upgrade", response_model=AuthResponse)
async def guest_upgrade(
    request: GuestUpgradeRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """
    游客账号升级

    将游客账号升级为正式账号，支持手机号、邮箱、微信等多种升级方式。

    Args:
        request: 游客升级请求，包含升级信息和验证码
        current_user: 当前用户信息（必须是游客）
        auth_service: 认证服务实例
        jwt_service: JWT服务实例

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

        # 使用AuthService进行账号升级
        upgrade_data = {
            "user_id": current_user["user_id"],
            "upgrade_type": request.upgrade_type.value,
            "phone": request.phone,
            "email": request.email,
            "wechat_code": request.wechat_code,
            "verification_code": request.verification_code,
            "device_id": request.device_id
        }

        upgraded_user = auth_service.upgrade_guest_account(**upgrade_data)

        # 使用JWT服务生成新的令牌对
        access_token, refresh_token = jwt_service.generate_token_pair(
            user_id=upgraded_user["user_id"],
            user_type="registered",
            additional_claims={
                "is_guest": False,
                "device_id": request.device_id,
                "upgrade_type": request.upgrade_type.value
            }
        )

        return create_success_response(
            data=AuthResponse(
                user_id=upgraded_user["user_id"],
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
        # 记录详细错误信息
        print(f"[GuestUpgrade] 游客账号升级失败: {str(e)}")

        # 根据异常类型返回不同的HTTP状态码
        if "验证码" in str(e) or "verification" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        elif "已存在" in str(e) or "exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该账号已被注册"
            )
        elif "不是游客" in str(e) or "not guest" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有游客账号可以升级"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"账号升级失败: {str(e)}"
            )


@router.post("/sms/send", response_model=BaseResponse)
async def send_sms_code(
    request: SMSCodeRequest,
    auth_service: AsyncAuthService = Depends(get_async_auth_service),
    client_ip: str = Depends(lambda: None)  # 获取客户端IP
):
    """
    发送短信验证码

    向指定手机号发送验证码，支持登录、注册、找回密码等场景。

    Args:
        request: 短信验证码请求，包含手机号和验证码类型
        auth_service: 异步认证服务实例
        client_ip: 客户端IP地址

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当手机号格式错误、发送频率限制或发送失败时
    """
    try:
        # 验证请求参数
        if not request.phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号不能为空"
            )

        if not request.type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码类型不能为空"
            )

        # 验证验证码类型
        valid_types = ["login", "register", "reset_password"]
        if request.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的验证码类型，支持的类型: {', '.join(valid_types)}"
            )

        # 使用异步AuthService发送验证码
        result = await auth_service.send_sms_verification(
            phone=request.phone,
            verification_type=request.type,
            ip_address=client_ip
        )

        return create_success_response(
            message=result.get("message", "验证码发送成功"),
            data={
                "cooldown_seconds": result.get("cooldown_seconds", 60),
                "type": request.type,
                "success": result.get("success", True)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[SMS] 短信发送异常: {str(e)}")

        # 根据异常类型返回不同的HTTP状态码
        error_message = str(e).lower()
        if "手机号格式" in error_message or "phone" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号格式不正确"
            )
        elif "频率" in error_message or "rate" in error_message or "限制" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="发送过于频繁，请稍后再试"
            )
        elif "验证码" in error_message or "verification" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码发送失败，请检查手机号"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="短信发送失败，请稍后重试"
            )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    auth_service: AsyncAuthService = Depends(get_async_auth_service)
):
    """
    用户登录

    支持多种登录方式：手机号+验证码、邮箱+验证码、微信授权等。

    Args:
        request: 登录请求，包含登录类型、凭证和验证码
        auth_service: 异步认证服务实例

    Returns:
        AuthResponse: 包含用户信息和认证令牌

    Raises:
        HTTPException: 当登录凭证错误、验证码失效或登录失败时
    """
    try:
        # 根据登录类型选择不同的登录方式
        if request.login_type == "phone":
            if not request.phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="手机号不能为空"
                )

            # 手机号验证码登录
            login_result = await auth_service.login_with_phone(
                phone=request.phone,
                code=request.verification_code,
                device_id=request.device_id
            )

        elif request.login_type == "email":
            if not request.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱不能为空"
                )

            # 邮箱验证码登录（暂时使用验证码，后续可能改为密码）
            login_result = await auth_service.login_with_phone(
                phone=request.email,  # 临时使用phone字段存储邮箱
                code=request.verification_code,
                device_id=request.device_id
            )

        elif request.login_type == "wechat":
            # 微信登录（暂时不支持，返回错误）
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="微信登录暂未实现"
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的登录类型: {request.login_type}"
            )

        # 转换为AuthResponse格式
        auth_response = AuthResponse(
            user_id=login_result["user"]["id"],
            user_type=login_result["user"].get("user_type", "registered"),
            is_guest=login_result["user"].get("is_guest", False),
            access_token=login_result["access_token"],
            refresh_token=login_result["refresh_token"],
            expires_in=login_result["expires_in"],
            token_type="bearer"
        )

        return create_success_response(
            data=auth_response,
            message="登录成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 根据异常类型返回不同的HTTP状态码和错误信息
        error_message = str(e).lower()

        if "验证码" in error_message or "verification" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期"
            )
        elif "用户不存在" in error_message or "not found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        elif "频率" in error_message or "rate" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登录过于频繁，请稍后再试"
            )
        else:
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
    current_user: Optional[dict] = Depends(get_current_user),
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """
    用户登出

    使访问令牌失效，清理用户会话数据。
    支持令牌黑名单机制，确保登出后的令牌无法继续使用。

    Args:
        credentials: HTTP认证凭证（可选）
        current_user: 当前用户信息（可选）
        jwt_service: JWT服务实例，用于令牌黑名单管理

    Returns:
        BaseResponse: 操作结果

    Raises:
        HTTPException: 当登出失败时
    """
    try:
        # 如果没有用户信息，返回成功但不做任何操作
        if not current_user:
            return create_success_response(
                message="已退出登录"
            )

        # 获取访问令牌JTI
        access_token_jti = current_user.get("token_jti")
        user_id = current_user.get("user_id")

        if access_token_jti and user_id:
            # 将访问令牌加入黑名单
            await jwt_service.blacklist_token(
                jti=access_token_jti,
                user_id=user_id,
                reason="用户主动登出",
                ip_address=None,  # 可以从请求中获取
                user_agent=None   # 可以从请求头中获取
            )

        return create_success_response(
            message="登出成功"
        )

    except Exception as e:
        # 记录详细错误信息
        print(f"[Logout] 用户登出失败: {str(e)}")
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