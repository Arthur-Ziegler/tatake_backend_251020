"""
简化认证领域Schema定义

根据设计文档，Schema大幅简化：
1. 统一响应格式：{code, data, message}
2. 移除复杂设备信息、SMS验证等非核心功能
3. 只保留微信登录相关的Schema
4. 简化请求参数，降低使用复杂度

设计原则:
- 极简化：只包含5个API需要的最小Schema集合
- 统一性：所有API使用相同的响应格式
- 类型安全：完整的数据验证
- 自文档化：清晰的字段说明

API端点对应的Schema:
1. POST /auth/guest/init -> GuestInitRequest -> AuthTokenResponse
2. POST /auth/register -> WeChatRegisterRequest -> AuthTokenResponse
3. POST /auth/login -> WeChatLoginRequest -> AuthTokenResponse
4. POST /auth/guest/upgrade -> GuestUpgradeRequest -> AuthTokenResponse
5. POST /auth/refresh -> TokenRefreshRequest -> AuthTokenResponse
"""

from datetime import datetime
from typing import Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ===== 枚举类型 =====

class UserTypeEnum(str, Enum):
    """简化的用户类型枚举"""
    GUEST = "guest"      # 游客
    WECHAT = "wechat"    # 微信用户


# ===== 核心响应格式 =====

class UnifiedResponse(BaseModel):
    """
    统一响应格式

    所有API端点都使用这个统一的响应格式：
    - code: HTTP状态码（200, 400, 401, 403, 404, 409等）
    - data: 响应数据，成功时包含具体数据，失败时为null
    - message: 响应消息，成功时为"success"，失败时为具体错误描述

    Examples:
        成功响应：
        {
            "code": 200,
            "data": {"user_id": "...", "access_token": "..."},
            "message": "success"
        }

        错误响应：
        {
            "code": 404,
            "data": null,
            "message": "用户不存在"
        }
    """
    code: int = Field(..., description="HTTP状态码")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    message: str = Field(..., description="响应消息")

    model_config = ConfigDict(from_attributes=True)


# ===== 请求Schema =====

class GuestInitRequest(BaseModel):
    """
    游客账号初始化请求

    根据设计文档，游客初始化不接受任何参数。
    每次请求都会创建全新的随机游客身份。
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"  # 禁止额外字段
    )


class WeChatRegisterRequest(BaseModel):
    """
    微信注册请求

    微信注册本质上是"创建游客 + 立即升级"的组合操作。
    客户端只需要提供微信openid。
    """
    wechat_openid: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="微信OpenID"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class WeChatLoginRequest(BaseModel):
    """
    微信登录请求

    通过微信OpenID进行登录验证。
    """
    wechat_openid: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="微信OpenID"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class GuestUpgradeRequest(BaseModel):
    """
    游客账号升级请求

    将游客账号升级为正式用户，需要提供微信OpenID。
    """
    wechat_openid: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="微信OpenID"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class TokenRefreshRequest(BaseModel):
    """
    令牌刷新请求

    使用刷新令牌获取新的访问令牌。
    """
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="刷新令牌"
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


# ===== 响应Schema =====

class AuthTokenResponse(UnifiedResponse):
    """
    认证令牌响应

    所有认证相关的成功响应都使用这个Schema，
    返回统一的令牌数据结构。
    """
    data: Dict[str, Any] = Field(
        ...,
        description="令牌数据，包含user_id, access_token, refresh_token"
    )

    # 令牌数据结构示例：
    # {
    #     "user_id": "uuid",
    #     "access_token": "jwt_access_token",
    #     "refresh_token": "jwt_refresh_token"
    # }


# ===== 删除的Schema注释 =====
# 以下Schema已被删除，原因：
# - DeviceInfo: 移除设备信息依赖
# - SMSCodeRequest: 移除短信验证功能
# - LoginRequest: 简化为微信专用登录Schema
# - UserInfoResponse: 移除用户信息查询功能
# - SMSCodeResponse: 移除短信发送功能
# - BaseResponse/ErrorResponse: 合并为UnifiedResponse
# - TokenInfo, UserProfile: 移除非核心信息Schema