"""
认证领域API路由

提供完整的认证API端点，包含7个核心认证功能：
1. 游客账号初始化
2. 游客账号升级
3. 短信验证码发送
4. 用户登录
5. 令牌刷新
6. 用户登出
7. 获取用户信息

API设计原则:
- RESTful设计风格
- 统一的请求/响应格式
- 完整的错误处理
- 安全的认证机制
- 详细的参数验证

端点列表:
POST /auth/guest/init          - 游客账号初始化
POST /auth/guest/upgrade       - 游客账号升级
POST /auth/sms/send           - 发送短信验证码
POST /auth/login              - 用户登录
POST /auth/refresh            - 刷新访问令牌
POST /auth/logout             - 用户登出
GET  /auth/user-info          - 获取用户信息
"""

from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .service import create_auth_service
from .schemas import (
    # 请求模型
    GuestInitRequest, GuestUpgradeRequest, LoginRequest,
    SMSCodeRequest, TokenRefreshRequest,

    # 响应模型（统一使用AuthTokenResponse）
    AuthTokenResponse, UserInfoResponse, SMSCodeResponse,

    # 通用模型
    BaseResponse, ErrorResponse
)
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    SMSException,
    ValidationError
)

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """从JWT令牌中获取当前用户ID"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证令牌"
        )

    try:
        # 这里应该验证JWT令牌并提取用户ID
        # 为了简化，这里先跳过JWT验证
        # 实际项目中应该调用JWTService.verify_token

        # 临时解析令牌（实际应该用JWTService）
        import jwt
        try:
            payload = jwt.decode(
                credentials.credentials,
                "your-super-secret-jwt-key-here",
                algorithms=["HS256"]
            )
            user_id = UUID(payload.get("sub"))
            return user_id
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )


def get_client_info(request: Request) -> Dict[str, str]:
    """获取客户端信息"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "device_id": request.headers.get("X-Device-ID")
    }


def create_error_response(error: Exception) -> ErrorResponse:
    """创建统一的错误响应"""
    if isinstance(error, AuthenticationException):
        return ErrorResponse(
            success=False,
            error_code="AUTH_ERROR",
            message=str(error),
            details=None
        )
    elif isinstance(error, UserNotFoundException):
        return ErrorResponse(
            success=False,
            error_code="USER_NOT_FOUND",
            message=str(error),
            details=None
        )
    elif isinstance(error, TokenException):
        return ErrorResponse(
            success=False,
            error_code="TOKEN_ERROR",
            message=str(error),
            details=None
        )
    elif isinstance(error, SMSException):
        return ErrorResponse(
            success=False,
            error_code="SMS_ERROR",
            message=str(error),
            details=None
        )
    elif isinstance(error, ValidationError):
        return ErrorResponse(
            success=False,
            error_code="VALIDATION_ERROR",
            message=str(error),
            details=None
        )
    else:
        return ErrorResponse(
            success=False,
            error_code="INTERNAL_ERROR",
            message="服务器内部错误",
            details=str(error) if __debug__ else None
        )


@router.post("/guest/init", response_model=AuthTokenResponse)
async def init_guest_account(
    request: GuestInitRequest,
    http_request: Request
):
    """
    游客账号初始化

    为新设备创建临时游客账号，无需用户提供任何身份信息。
    游客账号具有有限的功能，后续可以升级为正式账号。

    Args:
        request: 游客初始化请求
        http_request: HTTP请求对象

    Returns:
        AuthInitResponse: 包含用户ID和认证令牌的响应

    Raises:
        HTTPException: 当初始化失败时
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 执行游客账号初始化
        result = await auth_service.init_guest_account(
            request=request,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应
        response = AuthTokenResponse(
            success=True,
            message="游客账号初始化成功",
            data={
                "user_id": result["user_id"],
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
                "is_guest": True
            }
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[GuestInit] 游客账号初始化失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )


@router.post("/guest/upgrade", response_model=AuthTokenResponse)
async def upgrade_guest_account(
    request: GuestUpgradeRequest,
    http_request: Request,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    游客账号升级

    将游客账号升级为正式账号，需要提供手机号和短信验证码。
    升级后可以享受完整的功能。

    Args:
        request: 账号升级请求
        current_user_id: 当前用户ID（从JWT令牌获取）
        http_request: HTTP请求对象

    Returns:
        AuthTokenResponse: 包含新用户信息和令牌的响应

    Raises:
        HTTPException: 当升级失败时
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 执行账号升级
        result = await auth_service.upgrade_guest_account(
            request=request,
            current_user_id=current_user_id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应
        response = AuthTokenResponse(
            success=True,
            message="账号升级成功",
            data={
                "user_id": result["user_id"],
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
                "is_guest": False
            }
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[GuestUpgrade] 账号升级失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )


@router.post("/sms/send", response_model=SMSCodeResponse)
async def send_sms_code(
    request: SMSCodeRequest,
    http_request: Request,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    发送短信验证码

    向指定手机号发送验证码，用于登录、注册、账号升级等场景。
    实施发送频率限制，防止短信轰炸。

    Args:
        request: 短信发送请求
        current_user_id: 当前用户ID（可选）
        http_request: HTTP请求对象

    Returns:
        SMSCodeResponse: 短信发送结果

    Raises:
        HTTPException: 当发送失败时
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 发送短信验证码
        code = await auth_service.send_sms_code(
            request=request,
            user_id=current_user_id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应（不返回实际验证码，只返回成功信息）
        response = SMSCodeResponse(
            success=True,
            message="验证码发送成功",
            data={
                "phone": request.phone,
                "verification_type": request.verification_type,
                "expires_in": 300,  # 5分钟
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[SMSSend] 短信发送失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request
):
    """
    用户登录

    支持密码登录和短信验证码登录两种方式。
    成功登录后返回JWT访问令牌和刷新令牌。

    Args:
        request: 登录请求
        http_request: HTTP请求对象

    Returns:
        AuthTokenResponse: 登录成功响应

    Raises:
        HTTPException: 当登录失败时
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 执行登录
        result = await auth_service.login(
            request=request,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应
        response = AuthTokenResponse(
            success=True,
            message="登录成功",
            data={
                "user_id": result["user_id"],
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
                "is_guest": result["is_guest"]
            }
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[Login] 登录失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response.dict()
        )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    http_request: Request
):
    """
    刷新访问令牌

    使用刷新令牌获取新的访问令牌。
    当访问令牌即将过期时，客户端应使用此接口续期。

    Args:
        request: 令牌刷新请求
        http_request: HTTP请求对象

    Returns:
        AuthTokenResponse: 新的令牌信息

    Raises:
        HTTPException: 当刷新失败时
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 刷新令牌
        result = await auth_service.refresh_token(
            request=request,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应
        response = AuthTokenResponse(
            success=True,
            message="令牌刷新成功",
            data={
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"]
            }
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[TokenRefresh] 令牌刷新失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response.dict()
        )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    http_request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    用户登出

    将当前令牌加入黑名单，使其立即失效。
    客户端在登出后应删除本地存储的令牌。

    Args:
        credentials: HTTP认证凭据
        http_request: HTTP请求对象

    Returns:
        BaseResponse: 登出结果

    Raises:
        HTTPException: 当登出失败时
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要认证令牌"
            )

        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 创建认证服务
        auth_service = await create_auth_service()

        # 解析令牌获取用户信息
        import jwt
        try:
            payload = jwt.decode(
                credentials.credentials,
                "your-super-secret-jwt-key-here",
                algorithms=["HS256"]
            )
            user_id = UUID(payload.get("sub"))
            token_jti = payload.get("jti")
            expires_at = datetime.fromtimestamp(payload.get("exp"), timezone.utc)
        except jwt.JWTError:
            raise TokenException("无效的认证令牌")

        # 执行登出
        await auth_service.logout(
            token_jti=token_jti,
            user_id=user_id,
            token_type="access",
            expires_at=expires_at,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        # 构建响应
        response = BaseResponse(
            success=True,
            message="登出成功"
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[Logout] 登出失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )


@router.get("/user-info", response_model=UserInfoResponse)
async def get_user_info(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    获取用户信息

    根据JWT令牌获取当前用户的详细信息。
    包含用户基本信息、账号状态、积分等级等。

    Args:
        current_user_id: 当前用户ID（从JWT令牌获取）

    Returns:
        UserInfoResponse: 用户详细信息

    Raises:
        HTTPException: 当获取失败时
    """
    try:
        # 创建认证服务
        auth_service = await create_auth_service()

        # 获取用户信息
        user_info = await auth_service.get_user_info(current_user_id)

        # 构建响应
        response = UserInfoResponse(
            success=True,
            message="获取用户信息成功",
            data=user_info
        )

        return response

    except Exception as e:
        # 记录错误并返回统一错误响应
        print(f"[UserInfo] 获取用户信息失败: {str(e)}")
        error_response = create_error_response(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )