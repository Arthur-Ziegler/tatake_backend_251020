"""
认证领域Schema定义

本模块定义了认证领域所需的最小化Schema集合，仅包含7个认证API的请求和响应模型。
采用Pydantic v2语法，提供完整的数据验证和序列化功能。

设计原则：
- 最小化：只包含7个API真正需要的Schema
- 无冗余：不包含其他模块的兼容性代码
- 自文档化：每个Schema都有完整的docstring和字段说明
- 类型安全：使用Pydantic完整验证
- 可测试：Schema定义清晰，易于单元测试
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator
import uuid


# ===== 枚举类型 =====

class UserTypeEnum(str, Enum):
    """用户类型枚举"""
    GUEST = "guest"  # 游客
    PHONE = "phone"  # 手机号用户
    WECHAT = "wechat"  # 微信用户
    APPLE = "apple"  # 苹果用户


class VerificationTypeEnum(str, Enum):
    """验证类型枚举"""
    REGISTER = "register"  # 注册验证
    LOGIN = "login"  # 登录验证
    RESET_PASSWORD = "reset_password"  # 重置密码验证
    UPGRADE = "upgrade"  # 游客升级验证


class UpgradeMethodEnum(str, Enum):
    """升级方式枚举"""
    SMS_CODE = "sms_code"  # 短信验证码升级
    WECHAT = "wechat"  # 微信授权升级
    APPLE = "apple"  # 苹果授权升级


class LoginMethodEnum(str, Enum):
    """登录方式枚举"""
    SMS_CODE = "sms_code"  # 短信验证码登录
    PASSWORD = "password"  # 密码登录
    WECHAT = "wechat"  # 微信授权登录
    APPLE = "apple"  # 苹果授权登录


# ===== 辅助Schema =====

class DeviceInfo(BaseModel):
    """设备信息"""
    device_id: Optional[str] = Field(None, description="设备唯一标识")
    device_type: Optional[str] = Field(None, description="设备类型：ios/android/web/desktop")
    device_name: Optional[str] = Field(None, description="设备名称")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    app_version: Optional[str] = Field(None, description="应用版本")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理字符串")

    model_config = ConfigDict(from_attributes=True)


class TokenInfo(BaseModel):
    """令牌信息"""
    token_type: str = Field(..., description="令牌类型：access/refresh")
    expires_in: int = Field(..., description="令牌有效期（秒）")
    scope: Optional[str] = Field(None, description="令牌权限范围")

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """用户资料"""
    user_id: str = Field(..., description="用户ID")
    user_type: UserTypeEnum = Field(..., description="用户类型")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    phone: Optional[str] = Field(None, description="手机号（脱敏显示）")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    apple_id: Optional[str] = Field(None, description="苹果用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    model_config = ConfigDict(from_attributes=True)


# ===== 基础响应Schema =====

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    trace_id: Optional[str] = Field(None, description="请求追踪ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = Field(False, description="请求是否成功")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_detail: Optional[Dict[str, Any]] = Field(None, description="错误详情")

    model_config = ConfigDict(from_attributes=True)


# ===== 请求Schema =====

class GuestInitRequest(BaseModel):
    """游客账号初始化请求"""
    device_info: Optional[DeviceInfo] = Field(None, description="设备信息")

    model_config = ConfigDict(from_attributes=True)


class GuestUpgradeRequest(BaseModel):
    """游客账号升级请求"""
    upgrade_method: UpgradeMethodEnum = Field(..., description="升级方式")
    phone: Optional[str] = Field(None, description="手机号（短信升级时必填）")
    sms_code: Optional[str] = Field(None, description="短信验证码（短信升级时必填）")
    wechat_code: Optional[str] = Field(None, description="微信授权码（微信升级时必填）")
    apple_id_token: Optional[str] = Field(None, description="苹果ID令牌（苹果升级时必填）")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v, info):
        if v and not v.isdigit():
            raise ValueError('手机号必须是数字')
        if v and len(v) != 11:
            raise ValueError('手机号必须是11位数字')
        return v

    @field_validator('sms_code')
    @classmethod
    def validate_sms_code(cls, v, info):
        if v and not v.isdigit():
            raise ValueError('短信验证码必须是数字')
        return v

    model_config = ConfigDict(from_attributes=True)


class SMSCodeRequest(BaseModel):
    """短信验证码发送请求"""
    phone: str = Field(..., description="手机号")
    verification_type: VerificationTypeEnum = Field(..., description="验证类型")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not v.isdigit():
            raise ValueError('手机号必须是数字')
        if len(v) != 11:
            raise ValueError('手机号必须是11位数字')
        return v

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """用户登录请求"""
    login_method: LoginMethodEnum = Field(..., description="登录方式")
    phone: Optional[str] = Field(None, description="手机号（短信登录时必填）")
    password: Optional[str] = Field(None, description="密码（密码登录时必填）")
    sms_code: Optional[str] = Field(None, description="短信验证码（短信登录时必填）")
    wechat_code: Optional[str] = Field(None, description="微信授权码（微信登录时必填）")
    apple_id_token: Optional[str] = Field(None, description="苹果ID令牌（苹果登录时必填）")
    device_info: Optional[DeviceInfo] = Field(None, description="设备信息")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v, info):
        if v and not v.isdigit():
            raise ValueError('手机号必须是数字')
        if v and len(v) != 11:
            raise ValueError('手机号必须是11位数字')
        return v

    @field_validator('sms_code')
    @classmethod
    def validate_sms_code(cls, v, info):
        if v and not v.isdigit():
            raise ValueError('短信验证码必须是数字')
        return v

    model_config = ConfigDict(from_attributes=True)


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")

    model_config = ConfigDict(from_attributes=True)


# LogoutRequest 不需要单独定义，因为没有请求体


# ===== 响应Schema =====

class AuthTokenResponse(BaseResponse):
    """认证令牌响应模型"""
    data: Dict[str, Any] = Field(..., description="令牌数据")

    # 令牌数据结构：
    # {
    #     "access_token": "访问令牌",
    #     "refresh_token": "刷新令牌",
    #     "token_type": "bearer",
    #     "expires_in": 1800,
    #     "user_info": {
    #         "user_id": "用户ID",
    #         "user_type": "用户类型",
    #         "is_new_user": false
    #     }
    # }

    model_config = ConfigDict(from_attributes=True)


class UserInfoResponse(BaseResponse):
    """用户信息响应模型"""
    data: Dict[str, Any] = Field(..., description="用户信息数据")

    # 用户信息数据结构：
    # {
    #     "user_profile": {
    #         "user_id": "用户ID",
    #         "user_type": "用户类型",
    #         "nickname": "昵称",
    #         "avatar_url": "头像URL",
    #         "phone": "138****8000",
    #         "created_at": "2024-01-01T00:00:00Z",
    #         "last_login_at": "2024-01-01T12:00:00Z"
    #     },
    #     "settings": {
    #         "notifications": true,
    #         "privacy": "public"
    #     }
    # }

    model_config = ConfigDict(from_attributes=True)


class SMSCodeResponse(BaseResponse):
    """短信验证码响应模型"""
    data: Dict[str, Any] = Field(..., description="短信发送结果数据")

    # 短信发送结果数据结构：
    # {
    #     "sms_id": "短信ID",
    #     "phone_masked": "138****8000",
    #     "expires_in": 300,
    #     "send_count": 1
    # }

    model_config = ConfigDict(from_attributes=True)