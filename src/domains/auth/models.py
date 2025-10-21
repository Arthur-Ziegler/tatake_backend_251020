"""
简化认证领域数据模型

根据设计文档，认证领域大幅简化，只保留核心认证功能：
1. 统一微信登录，移除其他登录方式
2. 简化数据模型，只保留7个核心字段
3. 移除用户资料管理，聚焦认证功能
4. 删除SMS、会话管理等非核心功能

核心数据模型:
- Auth: 简化的用户认证表（重命名自auth_users）
- AuthLog: 审计日志表（保留）

设计原则:
1. 极简化：只保留认证所需的最小字段集
2. 单一职责：只负责身份认证，不管理用户资料
3. 微信单一登录：只支持微信OpenID认证
4. 游客简化：每次创建新的随机游客身份
5. 无状态：不维护复杂会话状态
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


class Auth(BaseModel, table=True):
    """
    简化的用户认证表

    根据设计文档，这是从auth_users表简化而来的核心认证表。
    只保留7个核心字段，专注于身份认证功能。

    字段说明：
    - id: 主键
    - wechat_openid: 微信OpenID（游客为null，正式用户必须有值）
    - is_guest: 是否为游客账号
    - created_at: 创建时间
    - updated_at: 最后更新时间
    - last_login_at: 最后登录时间
    - jwt_version: JWT版本号，用于强制令牌失效

    索引设计：
    - idx_auth_wechat_openid: 支持微信登录查询
    - idx_auth_is_guest: 支持游客统计
    - idx_auth_created_at: 支持按创建时间查询
    """

    __tablename__ = "auth"

    wechat_openid: Optional[str] = Field(
        default=None,
        max_length=100,
        unique=True,
        index=True,
        description="微信OpenID，游客为null，正式用户必填"
    )
    is_guest: bool = Field(
        default=True,
        index=True,
        description="是否为游客账号"
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="最后登录时间"
    )
    jwt_version: int = Field(
        default=1,
        description="JWT版本号，用于强制令牌失效"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_auth_wechat_openid', 'wechat_openid'),
        Index('idx_auth_is_guest', 'is_guest'),
        Index('idx_auth_created_at', 'created_at'),
    )


class AuthLog(BaseModel, table=True):
    """
    认证审计日志表

    保留原有的审计功能，记录所有认证相关操作。
    支持安全审计和问题排查。
    """

    __tablename__ = "auth_audit_logs"

    user_id: Optional[UUID] = Field(
        default=None,
        foreign_key="auth.id",
        index=True,
        description="用户ID（可为空，用于游客操作）"
    )
    action: str = Field(
        max_length=50,
        index=True,
        description="操作类型: guest_init, login, register, upgrade, token_refresh, etc."
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
        description="设备ID（已弃用但保留用于日志）"
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


# 删除的模型（保留注释说明删除原因）：
# - UserSettings: 用户设置移至独立的user领域
# - SMSVerification: 移除短信验证功能，只支持微信登录
# - TokenBlacklist: 移除登出功能，不维护token黑名单
# - UserSession: 移除会话管理，采用无状态JWT