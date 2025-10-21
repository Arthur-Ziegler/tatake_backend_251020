"""
认证相关的数据模型

该模块定义了认证系统所需的数据模型，包括JWT令牌黑名单、
短信验证码存储等功能。使用SQLModel进行ORM映射。

核心功能：
1. JWT令牌黑名单管理
2. 短信验证码存储和验证
3. 用户登录会话管理
4. 认证相关的审计日志

设计原则：
- 安全存储：敏感信息加密存储
- 过期管理：自动清理过期数据
- 审计追踪：记录关键操作
- 性能优化：合理索引设计
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column, DateTime, String, Text, Integer, Boolean, Index
from sqlalchemy import func
from sqlalchemy.sql import expression
from src.models.base_model import BaseSQLModel


class SMSRecord(BaseSQLModel, table=True):
    """简化的短信记录表，用于异步认证Repository"""

    __tablename__ = "sms_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(max_length=20, description="手机号码")
    verification_type: str = Field(max_length=20, description="验证类型")
    code: str = Field(max_length=10, description="验证码")
    ip_address: Optional[str] = Field(max_length=45, description="请求IP地址")
    user_id: Optional[UUID] = Field(foreign_key="users.id", description="用户ID")
    status: str = Field(max_length=20, default="sent", description="状态")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    verified_at: Optional[datetime] = Field(description="验证时间")

    # 索引定义
    __table_args__ = (
        Index("idx_sms_record_phone_type", "phone", "verification_type", "created_at"),
        Index("idx_sms_record_created_at", "created_at"),
        Index("idx_sms_record_status", "status"),
    )


class TokenBlacklistBase(BaseSQLModel):
    """JWT令牌黑名单基础模型"""

    jti: str = Field(default=None, max_length=255, description="JWT令牌的唯一标识符")
    token: str = Field(max_length=2048, description="被加入黑名单的令牌（可选，用于审计）")
    user_id: UUID = Field(foreign_key="users.id", description="用户ID")
    reason: str = Field(max_length=255, description="加入黑名单的原因")
    revoked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="撤销时间")
    expires_at: datetime = Field(description="令牌过期时间")
    revoked_by: Optional[UUID] = Field(foreign_key="users.id", description="执行撤销操作的用户ID")
    ip_address: Optional[str] = Field(max_length=45, description="操作时的IP地址")
    user_agent: Optional[str] = Field(max_length=500, description="用户代理信息")


class TokenBlacklist(TokenBlacklistBase, table=True):
    """JWT令牌黑名单表"""

    __tablename__ = "token_blacklist"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 索引定义
    __table_args__ = (
        Index("idx_token_jti", "jti", unique=True),
        Index("idx_token_user_id", "user_id"),
        Index("idx_token_expires_at", "expires_at"),
        Index("idx_token_revoked_at", "revoked_at"),
    )


class SmsVerificationBase(BaseSQLModel):
    """短信验证码基础模型"""

    phone_number: str = Field(max_length=20, description="手机号码")
    code: str = Field(max_length=10, description="验证码")
    country_code: str = Field(max_length=5, default="+86", description="国家代码")
    verification_type: str = Field(max_length=20, description="验证类型：login/register/reset_password")
    attempt_count: int = Field(default=0, description="验证尝试次数")
    max_attempts: int = Field(default=5, description="最大尝试次数")
    is_used: bool = Field(default=False, description="是否已使用")
    used_at: Optional[datetime] = Field(description="使用时间")
    send_count: int = Field(default=1, description="发送次数")
    ip_address: Optional[str] = Field(max_length=45, description="请求IP地址")
    user_agent: Optional[str] = Field(max_length=500, description="用户代理信息")


class SmsVerification(SmsVerificationBase, table=True):
    """短信验证码表"""

    __tablename__ = "sms_verification"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    expires_at: datetime = Field(description="过期时间")

    # 索引定义
    __table_args__ = (
        Index("idx_phone_code", "phone_number", "verification_type", "created_at"),
        Index("idx_phone_type", "phone_number", "verification_type"),
        Index("idx_sms_expires_at", "expires_at"),
        Index("idx_is_used", "is_used"),
    )


class UserSessionBase(BaseSQLModel):
    """用户会话基础模型"""

    user_id: UUID = Field(foreign_key="users.id", description="用户ID")
    session_token: str = Field(max_length=255, unique=True, description="会话令牌")
    refresh_token: Optional[str] = Field(max_length=500, description="刷新令牌")
    device_info: Optional[str] = Field(max_length=500, description="设备信息")
    ip_address: str = Field(max_length=45, description="登录IP地址")
    user_agent: Optional[str] = Field(max_length=500, description="用户代理信息")
    is_active: bool = Field(default=True, description="会话是否活跃")
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="最后活跃时间")


class UserSession(UserSessionBase, table=True):
    """用户会话表"""

    __tablename__ = "user_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")
    expires_at: datetime = Field(description="过期时间")

    # 索引定义
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_session_token", "session_token", unique=True),
        Index("idx_refresh_token", "refresh_token"),
        Index("idx_sms_expires_at", "expires_at"),
        Index("idx_is_active", "is_active"),
    )


class AuthLogBase(BaseSQLModel):
    """认证日志基础模型"""

    user_id: Optional[UUID] = Field(foreign_key="users.id", description="用户ID（可选）")
    action: str = Field(max_length=50, description="操作类型：login/logout/token_refresh/verify_code")
    identifier: str = Field(max_length=255, description="操作标识（手机号/邮箱/用户ID等）")
    success: bool = Field(description="操作是否成功")
    failure_reason: Optional[str] = Field(max_length=255, description="失败原因")
    ip_address: Optional[str] = Field(max_length=45, description="IP地址")
    user_agent: Optional[str] = Field(max_length=500, description="用户代理")
    device_info: Optional[str] = Field(max_length=500, description="设备信息")
    location: Optional[str] = Field(max_length=100, description="地理位置")


class AuthLog(AuthLogBase, table=True):
    """认证日志表"""

    __tablename__ = "auth_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="创建时间")

    # 索引定义
    __table_args__ = (
        Index("idx_user_id_action", "user_id", "action"),
        Index("idx_identifier_action", "identifier", "action"),
        Index("idx_created_at", "created_at"),
        Index("idx_success", "success"),
        Index("idx_ip_address", "ip_address"),
    )


# 用于创建和读取的模型
class TokenBlacklistCreate(TokenBlacklistBase):
    """创建JWT黑名单记录的请求模型"""
    pass


class TokenBlacklistRead(TokenBlacklistBase):
    """读取JWT黑名单记录的响应模型"""

    id: int


class SmsVerificationCreate(SmsVerificationBase):
    """创建短信验证码的请求模型"""
    pass


class SmsVerificationRead(SmsVerificationBase):
    """读取短信验证码的响应模型"""

    id: int
    created_at: datetime
    expires_at: datetime


class UserSessionCreate(UserSessionBase):
    """创建用户会话的请求模型"""
    pass


class UserSessionRead(UserSessionBase):
    """读取用户会话的响应模型"""

    id: int
    created_at: datetime
    expires_at: datetime


class AuthLogCreate(AuthLogBase):
    """创建认证日志的请求模型"""
    pass


class AuthLogRead(AuthLogBase):
    """读取认证日志的响应模型"""

    id: int
    created_at: datetime