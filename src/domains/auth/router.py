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
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Request, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# from fastapi.responses import JSONResponse  # 不再使用JSONResponse

from jose import JWTError, jwt

from .service import AuthService
from .dependencies import get_auth_service_with_db
from .schemas import (
    # 请求模型
    GuestInitRequest,
    WeChatRegisterRequest,
    WeChatLoginRequest,
    GuestUpgradeRequest,
    TokenRefreshRequest,
    SMSSendRequest,
    SMSVerifyRequest,
    # 响应模型
    AuthTokenData,
    UnifiedResponse,
    SMSSendResponse,
    SMSVerifyResponse,
    PhoneBindResponse,
)
from .exceptions import (
    AuthenticationException,
    UserNotFoundException,
    TokenException,
    ValidationError,
    RateLimitException,
    DailyLimitException,
    AccountLockedException,
    VerificationNotFoundException,
    VerificationExpiredException,
    InvalidVerificationCodeException,
)

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案（可选）
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """
    从JWT令牌中获取当前用户ID

    用于需要认证的端点。
    如果令牌无效，抛出HTTPException。
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="需要认证令牌"
        )

    try:
        # 解码JWT令牌
        secret_key = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here")
        payload = jwt.decode(credentials.credentials, secret_key, algorithms=["HS256"])

        # 验证令牌类型
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误"
            )

        user_id = UUID(payload.get("sub"))
        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌格式错误"
        )


# ===== 依赖注入函数 =====

# 使用新的依赖注入方式，确保每个请求都有独立的数据库session
create_auth_service = get_auth_service_with_db


# ===== API端点实现 =====


@router.post(
    "/guest/init",
    response_model=UnifiedResponse[AuthTokenData],
    summary="游客账号初始化",
    description="创建一个新的游客账号，无需任何参数。每次请求都创建全新的随机游客身份。",
)
async def guest_init(
    request: Request,
    auth_service: AuthService = Depends(create_auth_service)
) -> UnifiedResponse[AuthTokenData]:
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
        result = auth_service.init_guest_account(
            request=GuestInitRequest(), ip_address=ip_address, user_agent=user_agent
        )

        # 构造AuthTokenData
        token_data = AuthTokenData(
            user_id=result["user_id"],
            is_guest=result["is_guest"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

        return UnifiedResponse[AuthTokenData](
            code=200, data=token_data, message="success"
        )

    except AuthenticationException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))


@router.post(
    "/register",
    response_model=UnifiedResponse[AuthTokenData],
    summary="微信用户注册",
    description="通过微信OpenID注册新用户。内部实现为创建游客账号并立即升级为正式用户，包含完整的用户初始化流程。",
)
async def wechat_register(
    request: WeChatRegisterRequest,
    http_request: Request,
    auth_service: AuthService = Depends(create_auth_service)
) -> UnifiedResponse[AuthTokenData]:
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
        result = auth_service.wechat_register(
            request=request, ip_address=ip_address, user_agent=user_agent
        )

        # 构造AuthTokenData
        token_data = AuthTokenData(
            user_id=result["user_id"],
            is_guest=result["is_guest"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

        return UnifiedResponse[AuthTokenData](
            code=200, data=token_data, message="success"
        )

    except ValidationError as e:
        return UnifiedResponse[AuthTokenData](code=400, data=None, message=str(e))
    except AuthenticationException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))


@router.post(
    "/login",
    response_model=UnifiedResponse[AuthTokenData],
    summary="微信用户登录",
    description="通过微信OpenID登录已有用户账号。支持新用户自动注册和已有用户登录，返回JWT访问令牌。",
)
async def wechat_login(
    http_request: Request,
    request: WeChatLoginRequest = Body(
        ...,
        examples={
            "NormalLogin": {
                "summary": "标准微信登录",
                "description": "使用有效的微信OpenID登录系统",
                "value": {"wechat_openid": "ox1234567890abcdef1234567890abcdef"},
            },
            "NewUserLogin": {
                "summary": "新用户首次登录",
                "description": "新用户首次使用微信登录，系统会自动创建账号",
                "value": {"wechat_openid": "ox0987654321fedcba0987654321fedcba"},
            },
        },
    ),
    auth_service: AuthService = Depends(create_auth_service)
) -> UnifiedResponse[AuthTokenData]:
    """
    微信登录

    通过微信OpenID进行身份验证并返回认证令牌。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行微信登录
        result = auth_service.wechat_login(
            request=request, ip_address=ip_address, user_agent=user_agent
        )

        # 构造AuthTokenData
        token_data = AuthTokenData(
            user_id=result["user_id"],
            is_guest=result["is_guest"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

        return UnifiedResponse[AuthTokenData](
            code=200, data=token_data, message="success"
        )

    except UserNotFoundException as e:
        return UnifiedResponse[AuthTokenData](code=404, data=None, message=str(e))
    except ValidationError as e:
        return UnifiedResponse[AuthTokenData](code=400, data=None, message=str(e))
    except AuthenticationException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))


@router.post(
    "/guest/upgrade",
    response_model=UnifiedResponse[AuthTokenData],
    summary="游客账号升级",
    description="将当前游客账号升级为正式用户，需要提供微信OpenID。",
    dependencies=[Depends(get_current_user_id)],
)
async def upgrade_guest(
    request: GuestUpgradeRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    http_request: Request = None,
    auth_service: AuthService = Depends(create_auth_service)
) -> UnifiedResponse[AuthTokenData]:
    """
    游客账号升级

    需要有效的访问令牌，将当前游客账号与微信OpenID绑定。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行游客升级
        result = auth_service.upgrade_guest_account(
            request=request,
            current_user_id=current_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 构造AuthTokenData
        token_data = AuthTokenData(
            user_id=result["user_id"],
            is_guest=result["is_guest"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

        return UnifiedResponse[AuthTokenData](
            code=200, data=token_data, message="success"
        )

    except UserNotFoundException as e:
        return UnifiedResponse[AuthTokenData](code=404, data=None, message=str(e))
    except ValidationError as e:
        return UnifiedResponse[AuthTokenData](code=400, data=None, message=str(e))
    except AuthenticationException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))


@router.post(
    "/refresh",
    response_model=UnifiedResponse[AuthTokenData],
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌。",
)
async def refresh_token(
    request: TokenRefreshRequest,
    http_request: Request,
    auth_service: AuthService = Depends(create_auth_service)
) -> UnifiedResponse[AuthTokenData]:
    """
    刷新访问令牌

    使用有效的刷新令牌获取新的访问令牌和刷新令牌。
    """
    try:
        # 获取客户端信息
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "unknown")

        # 执行令牌刷新
        result = auth_service.refresh_token(
            request=request, ip_address=ip_address, user_agent=user_agent
        )

        # 构造AuthTokenData
        token_data = AuthTokenData(
            user_id=result["user_id"],
            is_guest=result["is_guest"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
        )

        return UnifiedResponse[AuthTokenData](
            code=200, data=token_data, message="success"
        )

    except TokenException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))
    except AuthenticationException as e:
        return UnifiedResponse[AuthTokenData](code=401, data=None, message=str(e))


# ===== SMS认证端点 =====


@router.post("/sms/send", response_model=UnifiedResponse[SMSSendResponse])
async def send_sms_code_endpoint(
    request: Request,
    send_request: SMSSendRequest = Body(...),
    auth_service: AuthService = Depends(create_auth_service),
):
    """
    发送短信验证码

    发送短信验证码到指定手机号，支持register、login、bind三种场景。

    Args:
        request: FastAPI请求对象，用于获取IP地址
        send_request: 发送短信验证码请求
        auth_service: 认证服务实例

    Returns:
        UnifiedResponse[SMSSendResponse]: 统一响应格式
    """
    try:
        # 获取客户端IP地址
        ip_address = request.client.host
        if "x-forwarded-for" in request.headers:
            ip_address = request.headers["x-forwarded-for"]

        # 调用服务发送短信
        result = await auth_service.send_sms_code(
            phone=send_request.phone, scene=send_request.scene, ip_address=ip_address
        )

        # 返回成功响应
        return UnifiedResponse[SMSSendResponse](
            code=200,
            data=SMSSendResponse(
                expires_in=result["expires_in"], retry_after=result["retry_after"]
            ),
            message="短信验证码发送成功",
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except RateLimitException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except DailyLimitException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except AccountLockedException as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "短信发送失败，请稍后重试",
            },
        )


@router.post(
    "/sms/verify", response_model=UnifiedResponse[SMSVerifyResponse | PhoneBindResponse]
)
async def verify_sms_code_endpoint(
    request: Request,
    verify_request: SMSVerifyRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    auth_service: AuthService = Depends(create_auth_service),
):
    """
    验证短信验证码

    验证短信验证码，支持register、login、bind三种场景。
    bind场景需要提供JWT认证。

    Args:
        request: FastAPI请求对象
        verify_request: 验证短信验证码请求
        credentials: HTTP认证凭证（bind场景需要）
        auth_service: 认证服务实例

    Returns:
        UnifiedResponse: 统一响应格式
    """
    try:
        # 对于bind场景，需要从JWT中提取微信OpenID
        user_wechat_openid = None
        if verify_request.scene == "bind" and credentials:
            # 解析JWT获取微信OpenID
            try:
                payload = jwt.decode(
                    credentials.credentials,
                    os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-here"),
                    algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
                )
                user_wechat_openid = payload.get("wechat_openid")
            except (JWTError, KeyError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "success": False,
                        "error_code": "INVALID_TOKEN",
                        "message": "无效的认证令牌",
                    },
                )

        # 调用服务验证验证码
        result = auth_service.verify_sms_code(
            phone=verify_request.phone,
            code=verify_request.code,
            scene=verify_request.scene,
            user_wechat_openid=user_wechat_openid,
        )

        # 根据场景返回不同响应
        if verify_request.scene == "bind":
            # 绑定场景返回绑定响应
            response_data = PhoneBindResponse(
                user_id=result["user_id"],
                phone=verify_request.phone,
                upgraded=result["upgraded"],
            )
        else:
            # 注册和登录场景返回验证响应
            response_data = SMSVerifyResponse(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                user_id=result["user_id"],
                is_new_user=result["is_new_user"],
            )

        return UnifiedResponse(code=200, data=response_data, message="验证码验证成功")

    except VerificationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except VerificationExpiredException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except InvalidVerificationCodeException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error_code": e.error_code, "message": str(e)},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "验证码验证失败，请稍后重试",
            },
        )


# ===== 导出 =====

# 导出路由器实例
auth_router = router

# ===== 移除的端点注释 =====
# 以下端点已被移除，原因：
# - DELETE /auth/logout: 移除登出功能
# - GET /auth/user-info: 移除用户信息查询功能
# - 所有与设备信息相关的操作端点
# - 复杂的密码登录、多平台登录端点
