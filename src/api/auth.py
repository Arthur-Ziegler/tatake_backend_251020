"""
认证微服务透传路由

这个文件实现了与外部认证微服务的透传接口，提供：
- 与微服务完全一致的API路径
- 自动参数注入和响应格式转换
- 统一的错误处理
- 完整的微信、邮箱、手机认证功能

设计原则：
- 纯透传架构，无业务逻辑
- API路径与微服务完全一致
- 自动注入project参数
- 统一响应格式处理
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from ..services.auth.client import AuthMicroserviceClient
from ..services.auth.jwt_validator import validate_jwt_token


# ==================== Pydantic模型定义 ====================

class UnifiedResponse(BaseModel):
    """统一响应格式"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# 请求模型
class GuestInitRequest(BaseModel):
    """游客初始化请求"""
    # 微服务只需要project参数，但会自动注入，所以这里可以为空


class WeChatRegisterRequest(BaseModel):
    """微信注册请求"""
    wechat_openid: str = Field(..., min_length=1, max_length=100, description="微信OpenID")


class WeChatLoginRequest(BaseModel):
    """微信登录请求"""
    wechat_openid: str = Field(..., min_length=1, max_length=100, description="微信OpenID")


class GuestUpgradeRequest(BaseModel):
    """游客账号升级请求"""
    wechat_openid: str = Field(..., min_length=1, max_length=100, description="微信OpenID")


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")


class EmailSendRequest(BaseModel):
    """邮箱验证码发送请求"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="邮箱地址")
    scene: str = Field(..., pattern=r'^(register|login|bind)$', description="使用场景")


class EmailRegisterRequest(BaseModel):
    """邮箱注册请求"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码")
    verification_code: str = Field(..., pattern=r'^\d{6}$', description="邮箱验证码")


class EmailLoginRequest(BaseModel):
    """邮箱登录请求"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="邮箱地址")
    password: str = Field(..., min_length=1, description="密码")


class EmailBindRequest(BaseModel):
    """邮箱绑定请求"""
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码")
    verification_code: str = Field(..., pattern=r'^\d{6}$', description="邮箱验证码")


class SMSSendRequest(BaseModel):
    """短信验证码发送请求"""
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$', description="手机号")
    scene: str = Field(..., pattern=r'^(register|login|bind)$', description="使用场景")


class SMSVerifyRequest(BaseModel):
    """短信验证码验证请求"""
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$', description="手机号")
    code: str = Field(..., pattern=r'^\d{6}$', description="验证码")
    scene: str = Field(..., pattern=r'^(register|login|bind)$', description="使用场景")


# ==================== 路由配置 ====================

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)

# 全局认证客户端实例
_auth_client = AuthMicroserviceClient()


def get_auth_client() -> AuthMicroserviceClient:
    """获取认证客户端实例"""
    return _auth_client


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> str:
    """
    从JWT令牌中获取当前用户ID

    Args:
        credentials: HTTP认证凭证
        auth_client: 认证客户端

    Returns:
        用户ID字符串

    Raises:
        HTTPException: 认证失败时
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # 使用JWT验证器验证令牌
        payload = await validate_jwt_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中缺少用户ID"
            )
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌验证失败: {str(e)}"
        )


# ==================== API端点实现 ====================

@router.post("/guest/init", response_model=UnifiedResponse, summary="游客账号初始化")
async def guest_init(
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    创建一个新的游客账号，需要提供project参数。
    每次请求都在指定project中创建全新的随机游客身份。
    """
    try:
        response = await auth_client.guest_init()
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"游客初始化失败: {str(e)}"
        )


@router.post("/wechat/register", response_model=UnifiedResponse, summary="微信用户注册")
async def wechat_register(
    request: WeChatRegisterRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    通过微信OpenID注册新用户。如果用户已存在则直接登录，支持自动登录机制。
    """
    try:
        response = await auth_client.wechat_register(request.wechat_openid)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"微信注册失败: {str(e)}"
        )


@router.post("/wechat/login", response_model=UnifiedResponse, summary="微信用户登录")
async def wechat_login(
    request: WeChatLoginRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    通过微信OpenID登录已有用户账号。如果账号不存在可选择自动注册，提供灵活的登录体验。
    """
    try:
        response = await auth_client.wechat_login(request.wechat_openid)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"微信登录失败: {str(e)}"
        )


@router.post("/wechat/bind", response_model=UnifiedResponse, summary="微信账号绑定")
async def wechat_bind(
    request: GuestUpgradeRequest,
    current_user_id: str = Depends(get_current_user_id),
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UnifiedResponse:
    """
    将当前账号与微信OpenID绑定，支持游客账号升级为正式账号，也支持已有账号添加微信登录方式。
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要认证令牌"
            )

        response = await auth_client.wechat_bind(request.wechat_openid, credentials.credentials)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"微信绑定失败: {str(e)}"
        )


@router.post("/token/refresh", response_model=UnifiedResponse, summary="刷新访问令牌")
async def refresh_token(
    request: TokenRefreshRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    使用刷新令牌获取新的访问令牌，支持游客、微信、手机等多种认证方式的令牌刷新。
    """
    try:
        response = await auth_client.refresh_token(request.refresh_token)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"令牌刷新失败: {str(e)}"
        )


@router.post("/email/send-code", response_model=UnifiedResponse, summary="发送邮箱验证码")
async def email_send_code(
    request: EmailSendRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    发送邮箱验证码到指定邮箱地址，支持邮箱注册、邮箱登录、邮箱绑定三种业务场景。
    验证码有效期为5分钟，同一邮箱有发送频率限制。
    """
    try:
        response = await auth_client.email_send_code(request.email, request.scene)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"邮箱验证码发送失败: {str(e)}"
        )


@router.post("/email/register", response_model=UnifiedResponse, summary="邮箱用户注册")
async def email_register(
    request: EmailRegisterRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    通过邮箱和密码注册新用户。需要提供有效的邮箱验证码。
    如果用户已存在则返回错误。
    """
    try:
        response = await auth_client.email_register(
            request.email, request.password, request.verification_code
        )
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"邮箱注册失败: {str(e)}"
        )


@router.post("/email/login", response_model=UnifiedResponse, summary="邮箱密码登录")
async def email_login(
    request: EmailLoginRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    通过邮箱和密码登录已有用户账号。
    支持邮箱+密码的传统登录方式。
    """
    try:
        response = await auth_client.email_login(request.email, request.password)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"邮箱登录失败: {str(e)}"
        )


@router.post("/email/bind", response_model=UnifiedResponse, summary="邮箱账号绑定")
async def email_bind(
    request: EmailBindRequest,
    current_user_id: str = Depends(get_current_user_id),
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UnifiedResponse:
    """
    将当前登录的账号与邮箱绑定，支持多种场景：
    1. 游客账号绑定邮箱，升级为正式账号
    2. 已有微信账号添加邮箱登录方式
    3. 已有手机账号添加邮箱登录方式
    需要有效的访问令牌进行身份验证。
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要认证令牌"
            )

        response = await auth_client.email_bind(
            request.email, request.password, request.verification_code, credentials.credentials
        )
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"邮箱绑定失败: {str(e)}"
        )


@router.post("/phone/send-code", response_model=UnifiedResponse, summary="发送手机验证码")
async def phone_send_code(
    request: SMSSendRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UnifiedResponse:
    """
    发送手机验证码

    发送短信验证码到指定手机号，支持手机注册、手机登录、手机绑定三种业务场景。
    验证码有效期为5分钟，同一手机号有发送频率限制。

    安全机制：
    - register/login场景：无限制，任何人可请求
    - bind场景：需要JWT认证，只能给当前登录用户发送
    """
    try:
        token = credentials.credentials if credentials and request.scene == "bind" else None
        response = await auth_client.phone_send_code(request.phone, request.scene, token)
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手机验证码发送失败: {str(e)}"
        )


@router.post("/phone/verify", response_model=UnifiedResponse, summary="手机验证码验证")
async def phone_verify(
    request: SMSVerifyRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UnifiedResponse:
    """
    验证短信验证码

    验证短信验证码，支持手机注册、手机登录、手机绑定三种业务场景。

    认证逻辑：
    - register/login场景：无需认证
    - bind场景：需要JWT认证
    """
    try:
        # 只有bind场景需要认证
        if request.scene == "bind":
            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="绑定场景需要认证令牌"
                )
            token = credentials.credentials
        else:
            token = None

        response = await auth_client.phone_verify(
            request.phone, request.code, request.scene, token
        )
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手机验证码验证失败: {str(e)}"
        )


@router.get("/system/public-key", response_model=UnifiedResponse, summary="获取JWT公钥")
async def get_public_key(
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    获取JWT公钥

    系统端点：获取JWT公钥用于本地验证JWT签名。
    业务服务可以调用此接口获取公钥，支持RSA和HMAC算法验证。

    Returns:
        dict: 包含公钥信息的字典
    """
    try:
        response = await auth_client.get_public_key()
        return UnifiedResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取公钥失败: {str(e)}"
        )


# ==================== 导出路由器 ====================

# 导出路由器实例，供主应用使用
auth_router = router