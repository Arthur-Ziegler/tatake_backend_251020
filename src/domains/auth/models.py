"""
认证领域数据模型

定义了认证系统中使用的所有数据模型，采用SQLModel框架。
这些模型对应认证数据库中的表结构。

数据模型:
- User: 用户基本信息表
- UserSettings: 用户设置表
- SMSVerification: 短信验证码表
- TokenBlacklist: 令牌黑名单表
- UserSession: 用户会话表
- AuthLog: 认证审计日志表

设计原则:
1. 使用UUID作为主键，确保全局唯一性
2. 添加创建时间、更新时间等审计字段
3. 使用软删除策略，避免数据丢失
4. 合理的索引设计，提升查询性能
5. 字段验证和约束，确保数据完整性
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, DateTime, text
from sqlalchemy import Index


class BaseModel(SQLModel):
    """基础模型类，提供通用字段"""

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        description="主键ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间"
    )


class User(BaseModel, table=True):
    """用户基本信息表"""

    __tablename__ = "auth_users"

    username: Optional[str] = Field(
        default=None,
        max_length=50,
        unique=True,
        index=True,
        description="用户名"
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        unique=True,
        index=True,
        description="邮箱"
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        unique=True,
        index=True,
        description="手机号"
    )
    password_hash: Optional[str] = Field(
        default=None,
        max_length=255,
        description="密码哈希"
    )
    nickname: Optional[str] = Field(
        default=None,
        max_length=100,
        description="昵称"
    )
    avatar: Optional[str] = Field(
        default=None,
        max_length=500,
        description="头像URL"
    )
    is_guest: bool = Field(
        default=False,
        description="是否为游客账号"
    )
    is_active: bool = Field(
        default=True,
        description="是否激活"
    )
    is_verified: bool = Field(
        default=False,
        description="是否已验证"
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="最后登录时间"
    )
    login_count: int = Field(
        default=0,
        description="登录次数"
    )
    jwt_version: int = Field(
        default=1,
        description="JWT版本号，用于强制令牌失效"
    )

    # 积分和等级系统
    total_points: int = Field(
        default=0,
        description="总积分"
    )
    available_points: int = Field(
        default=0,
        description="可用积分"
    )
    level: int = Field(
        default=1,
        description="用户等级"
    )
    experience_points: int = Field(
        default=0,
        description="经验值"
    )

    # 第三方登录
    wechat_openid: Optional[str] = Field(
        default=None,
        max_length=100,
        unique=True,
        index=True,
        description="微信OpenID"
    )
    wechat_unionid: Optional[str] = Field(
        default=None,
        max_length=100,
        index=True,
        description="微信UnionID"
    )

    # 设备信息（用于游客账号）
    device_id: Optional[str] = Field(
        default=None,
        max_length=255,
        index=True,
        description="设备ID"
    )
    device_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="设备类型"
    )

    # 软删除
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="删除时间"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_users_phone_active', 'phone', 'is_active'),
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_device_guest', 'device_id', 'is_guest'),
        Index('idx_users_created_at', 'created_at'),
    )


class UserSettings(BaseModel, table=True):
    """用户设置表"""

    __tablename__ = "auth_user_settings"

    user_id: UUID = Field(
        foreign_key="auth_users.id",
        index=True,
        unique=True,
        description="用户ID"
    )

    # 通知设置
    email_notifications: bool = Field(
        default=True,
        description="邮件通知开关"
    )
    sms_notifications: bool = Field(
        default=True,
        description="短信通知开关"
    )
    push_notifications: bool = Field(
        default=True,
        description="推送通知开关"
    )

    # 隐私设置
    profile_public: bool = Field(
        default=False,
        description="个人资料公开"
    )
    show_online_status: bool = Field(
        default=True,
        description="显示在线状态"
    )

    # 应用设置
    language: str = Field(
        default="zh-CN",
        max_length=10,
        description="语言设置"
    )
    timezone: str = Field(
        default="Asia/Shanghai",
        max_length=50,
        description="时区设置"
    )
    theme: str = Field(
        default="light",
        max_length=20,
        description="主题设置"
    )

    # 功能设置
    auto_start_focus: bool = Field(
        default=False,
        description="自动开始专注"
    )
    focus_reminder: bool = Field(
        default=True,
        description="专注提醒"
    )
    task_reminder: bool = Field(
        default=True,
        description="任务提醒"
    )


class SMSVerification(BaseModel, table=True):
    """短信验证码表"""

    __tablename__ = "auth_sms_verification"

    phone: str = Field(
        max_length=20,
        index=True,
        description="手机号"
    )
    code: str = Field(
        max_length=10,
        description="验证码"
    )
    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="auth_users.id",
        index=True,
        description="关联用户ID"
    )
    verification_type: str = Field(
        max_length=50,
        index=True,
        description="验证类型: login, register, reset_password"
    )
    attempts: int = Field(
        default=0,
        description="尝试次数"
    )
    max_attempts: int = Field(
        default=5,
        description="最大尝试次数"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="过期时间"
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="验证时间"
    )
    is_used: bool = Field(
        default=False,
        description="是否已使用"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_sms_phone_code', 'phone', 'code'),
        Index('idx_sms_phone_type', 'phone', 'verification_type'),
        Index('idx_sms_expires_at', 'expires_at'),
    )


class TokenBlacklist(BaseModel, table=True):
    """令牌黑名单表"""

    __tablename__ = "auth_token_blacklist"

    token_id: str = Field(
        max_length=255,
        unique=True,
        index=True,
        description="令牌唯一标识"
    )
    user_id: UUID = Field(
        foreign_key="auth_users.id",
        index=True,
        description="用户ID"
    )
    token_type: str = Field(
        max_length=50,
        description="令牌类型: access, refresh"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="令牌过期时间"
    )
    blacklisted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="加入黑名单时间"
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description="加入黑名单原因"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_token_user_type', 'user_id', 'token_type'),
        Index('idx_token_expires', 'expires_at'),
    )


class UserSession(BaseModel, table=True):
    """用户会话表"""

    __tablename__ = "auth_user_sessions"

    user_id: UUID = Field(
        foreign_key="auth_users.id",
        index=True,
        description="用户ID"
    )
    session_id: str = Field(
        max_length=255,
        unique=True,
        index=True,
        description="会话ID"
    )
    device_info: Optional[str] = Field(
        default=None,
        max_length=500,
        description="设备信息"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP地址"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="用户代理"
    )
    is_active: bool = Field(
        default=True,
        description="会话是否活跃"
    )
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="最后活动时间"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="会话过期时间"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )


class AuthLog(BaseModel, table=True):
    """认证审计日志表"""

    __tablename__ = "auth_audit_logs"

    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="auth_users.id",
        index=True,
        description="用户ID（可为空，用于游客操作）"
    )
    action: str = Field(
        max_length=50,
        index=True,
        description="操作类型: login, logout, register, etc."
    )
    result: str = Field(
        max_length=20,
        index=True,
        description="操作结果: success, failure, error"
    )
    details: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="详细信息"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP地址"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="用户代理"
    )
    device_id: Optional[str] = Field(
        default=None,
        max_length=255,
        index=True,
        description="设备ID"
    )
    error_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="错误代码"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_auth_user_action', 'user_id', 'action'),
        Index('idx_auth_result_time', 'result', 'created_at'),
        Index('idx_auth_device_action', 'device_id', 'action'),
    )