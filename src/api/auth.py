"""
认证接口 - 简化版

提供4个核心认证接口：
- 微信登录（自动注册）
- 手机验证码登录（自动注册）
- 发送手机验证码
- 刷新访问令牌

设计原则：
- 自动处理注册/登录流程
- 统一响应格式 {code, message, data}
- 最小化接口数量
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..services.auth_microservice_client import get_auth_client, AuthMicroserviceClient
from src.database import get_db_session
from src.domains.user.models import User

logger = logging.getLogger(__name__)


# ==================== Pydantic模型定义 ====================

class UnifiedResponse(BaseModel):
    """统一响应格式"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# 请求模型
class WeChatLoginRequest(BaseModel):
    """微信登录请求"""
    wechat_openid: str = Field(..., min_length=1, max_length=100, description="微信OpenID")


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")


class SMSSendRequest(BaseModel):
    """短信验证码发送请求"""
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$', description="手机号")


class SMSVerifyRequest(BaseModel):
    """短信验证码验证请求"""
    phone: str = Field(..., pattern=r'^1[3-9]\d{9}$', description="手机号")
    code: str = Field(..., pattern=r'^\d{6}$', description="验证码")


# ==================== 路由配置 ====================

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证系统"])

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)

# 全局认证客户端已移至auth_microservice_client.py




# ==================== API端点实现 ====================





@router.post("/wechat/login", response_model=UnifiedResponse, summary="微信登录")
async def wechat_login(
    request: WeChatLoginRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    business_session: Session = Depends(get_db_session)
) -> UnifiedResponse:
    """
    微信登录（自动注册）

    自动处理注册和登录流程：
    1. 先尝试登录已有用户
    2. 如果用户不存在，自动注册新用户
    3. 在User表中创建或更新用户业务数据记录
    4. 返回Access Token和Refresh Token

    输入：微信OpenID
    输出：认证Token信息
    """
    try:
        # 第一步：尝试登录
        response = await auth_client.wechat_login(request.wechat_openid)

        # 检查响应中的code字段，如果是404（用户不存在），尝试注册
        if response.get('code') == 404:
            try:
                response = await auth_client.wechat_register(request.wechat_openid)
            except Exception as register_error:
                # 注册也失败，返回错误
                raise HTTPException(
                    status_code=400,
                    detail=f"微信注册失败: {str(register_error)}"
                )

        # 第二步：确保User表中有用户记录（无论是登录还是注册）
        if response.get('code') == 200 and response.get('data'):
            user_id = response['data'].get('user_id')
            if user_id:
                await _ensure_user_business_record(business_session, user_id)

        # 如果登录成功，返回响应
        return UnifiedResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"微信登录失败: {str(e)}"
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




@router.post("/phone/send-code", response_model=UnifiedResponse, summary="发送手机验证码")
async def phone_send_code(
    request: SMSSendRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client)
) -> UnifiedResponse:
    """
    发送手机验证码（智能检测）

    智能检测用户状态，自动选择合适的场景：
    1. 先尝试发送登录验证码
    2. 如果用户不存在，自动切换为注册验证码
    3. 返回发送结果和验证码类型

    验证码有效期为5分钟，同一手机号有发送频率限制。
    """
    try:
        # 第一步：尝试发送登录验证码
        try:
            response = await auth_client.phone_send_code(request.phone, scene="login")

            # 添加详细日志用于调试验证码null问题
            logger.info(f"Auth微服务原始响应: {response}")
            logger.info(f"响应中的data字段: {response.get('data')}")
            logger.info(f"提取的verification_code: {response.get('data', {}).get('verification_code')}")

            return UnifiedResponse(**{
                "code": 200,
                "message": "登录验证码发送成功",
                "data": {
                    "scene": "login",
                    "expires_in": response.get("data", {}).get("expires_in", 300),
                    "retry_after": response.get("data", {}).get("retry_after", 60),
                    "verification_code": response.get("data", {}).get("verification_code")  # 测试阶段返回验证码
                }
            })
        except HTTPException as login_error:
            # 对429错误（请求过于频繁）返回统一格式
            if login_error.status_code == 429:
                return UnifiedResponse(**{
                    "code": 429,
                    "message": "发送验证码过于频繁，请稍后再试",
                    "data": {
                        "retry_after": 60,
                        "suggestion": "请等待60秒后重新发送验证码"
                    }
                })
            # 如果登录验证码发送失败（用户不存在），尝试注册验证码
            if login_error.status_code in [400, 404, 500]:  # 扩展错误码范围以包含更多可能的错误情况
                try:
                    response = await auth_client.phone_send_code(request.phone, scene="register")

                    # 添加详细日志用于调试验证码null问题
                    logger.info(f"注册场景Auth微服务原始响应: {response}")
                    logger.info(f"注册场景响应中的data字段: {response.get('data')}")
                    logger.info(f"注册场景提取的verification_code: {response.get('data', {}).get('verification_code')}")

                    return UnifiedResponse(**{
                        "code": 200,
                        "message": "注册验证码发送成功（新用户）",
                        "data": {
                            "scene": "register",
                            "expires_in": response.get("data", {}).get("expires_in", 300),
                            "retry_after": response.get("data", {}).get("retry_after", 60),
                            "is_new_user": True,
                            "verification_code": response.get("data", {}).get("verification_code")  # 测试阶段返回验证码
                        }
                    })
                except Exception as register_error:
                    # 注册也失败，返回错误
                    raise HTTPException(
                        status_code=400,
                        detail=f"手机号注册失败: {str(register_error)}"
                    )
            else:
                raise login_error
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手机验证码发送失败: {str(e)}"
        )


@router.post("/phone/verify", response_model=UnifiedResponse, summary="手机验证码登录")
async def phone_verify(
    request: SMSVerifyRequest,
    auth_client: AuthMicroserviceClient = Depends(get_auth_client),
    business_session: Session = Depends(get_db_session)
) -> UnifiedResponse:
    """
    手机验证码登录（智能检测）

    智能检测用户状态，自动选择合适的验证场景：
    1. 先尝试登录验证
    2. 如果用户不存在，自动切换为注册验证
    3. 在User表中创建或更新用户业务数据记录
    4. 返回认证Token信息

    输入：手机号、验证码
    输出：认证Token信息
    """
    try:
        response = None

        # 第一步：尝试登录验证
        try:
            response = await auth_client.phone_verify(request.phone, request.code, scene="login")

            # 登录成功，返回响应并添加场景信息
            if response.get('code') == 200:
                response['data'] = response.get('data', {})
                response['data']['scene'] = 'login'
                response['data']['is_new_user'] = False

        except HTTPException as login_error:
            # 如果登录验证失败（用户不存在），尝试注册验证
            if login_error.status_code in [400, 404]:
                try:
                    response = await auth_client.phone_verify(request.phone, request.code, scene="register")

                    # 注册成功，返回响应并添加场景信息
                    if response.get('code') == 200:
                        response['data'] = response.get('data', {})
                        response['data']['scene'] = 'register'
                        response['data']['is_new_user'] = True

                except Exception as register_error:
                    # 注册也失败，返回错误
                    raise HTTPException(
                        status_code=400,
                        detail=f"手机号注册失败: {str(register_error)}"
                    )
            else:
                # 其他错误，直接抛出
                raise login_error

        # 第二步：确保User表中有用户记录
        if response and response.get('code') == 200 and response.get('data'):
            user_id = response['data'].get('user_id')
            if user_id:
                await _ensure_user_business_record(business_session, user_id)

        return UnifiedResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"手机验证码验证失败: {str(e)}"
        )




# ==================== 辅助函数 ====================

async def _ensure_user_business_record(session: Session, user_id: str) -> None:
    """
    确保User表中存在用户业务数据记录

    Args:
        session: 数据库会话
        user_id: 用户ID（UUID格式，带连字符）
    """
    try:
        # 转换UUID格式（去掉连字符）以匹配User表的格式
        user_id_str = user_id.replace('-', '')

        # 检查用户记录是否存在
        user_stmt = select(User).where(User.user_id == user_id_str)
        existing_user = session.exec(user_stmt).first()

        if not existing_user:
            # 创建新用户记录
            new_user = User(
                user_id=user_id_str,
                nickname=f"用户_{user_id_str[:8]}",  # 默认昵称
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_user)
            session.commit()
            logger.info(f"为用户创建业务数据记录: user_id={user_id_str}")
        else:
            # 更新最后活跃时间
            existing_user.updated_at = datetime.utcnow()
            session.commit()
            logger.debug(f"用户业务数据记录已存在: user_id={user_id_str}")

    except Exception as e:
        session.rollback()
        logger.error(f"创建/更新用户业务数据记录失败: user_id={user_id}, error={str(e)}")
        # 不抛出异常，避免影响登录流程


# ==================== 导出路由器 ====================

# 导出路由器实例，供主应用使用
auth_router = router