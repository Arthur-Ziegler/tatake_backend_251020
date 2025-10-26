"""
用户域数据模型

定义用户领域的业务数据模型，与认证域分离。
用户域负责存储用户的业务数据、配置信息、偏好设置等。

设计原则：
1. 域分离：与认证域完全分离
2. 业务导向：关注用户业务逻辑
3. 扩展性：支持用户业务数据扩展
4. 一致性：与认证域通过user_id关联

作者：TaKeKe团队
版本：1.0.0 - 域分离架构
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from uuid import UUID


class UserBase(SQLModel):
    """用户基础模型"""
    user_id: UUID = Field(..., description="用户ID（关联认证表）")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


class User(UserBase, table=True):
    """用户表 - 用户域核心数据模型"""
    id: Optional[int] = Field(default=None, primary_key=True, description="主键ID")
    is_active: bool = Field(default=True, description="是否激活")

    class Config:
        table_name = "user"


class UserSettings(SQLModel, table=True):
    """用户设置表"""
    id: Optional[int] = Field(default=None, primary_key=True, description="主键ID")
    user_id: UUID = Field(..., description="用户ID")
    theme: str = Field(default="light", description="主题设置")
    language: str = Field(default="zh-CN", description="语言设置")
    notifications_enabled: bool = Field(default=True, description="通知开关")
    privacy_level: str = Field(default="public", description="隐私级别")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Config:
        table_name = "user_settings"


class UserPreferences(SQLModel, table=True):
    """用户偏好表"""
    id: Optional[int] = Field(default=None, primary_key=True, description="主键ID")
    user_id: UUID = Field(..., description="用户ID")
    category: str = Field(..., description="偏好类别")
    key: str = Field(..., description="偏好键")
    value: str = Field(..., description="偏好值")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Config:
        table_name = "user_preferences"


class UserStats(SQLModel, table=True):
    """用户统计表"""
    id: Optional[int] = Field(default=None, primary_key=True, description="主键ID")
    user_id: UUID = Field(..., description="用户ID")
    tasks_completed: int = Field(default=0, description="完成任务数")
    total_points: int = Field(default=0, description="总积分")
    login_count: int = Field(default=0, description="登录次数")
    last_active_at: Optional[datetime] = Field(None, description="最后活跃时间")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Config:
        table_name = "user_stats"


# 响应模型
class UserProfileResponse(SQLModel):
    """用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID（来自认证域）")
    is_guest: bool = Field(..., description="是否为游客（来自认证域）")
    is_active: bool = Field(..., description="是否激活")
    created_at: str = Field(..., description="创建时间")
    last_login_at: Optional[str] = Field(None, description="最后登录时间（来自认证域）")
    stats: Optional[dict] = Field(None, description="用户统计信息")

    class Config:
        """Pydantic配置"""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "avatar": "https://example.com/avatar.jpg",
                "bio": "这是用户简介",
                "wechat_openid": "ox1234567890abcdef",
                "is_guest": False,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login_at": "2025-01-20T15:45:00Z",
                "stats": {
                    "tasks_completed": 25,
                    "total_points": 150,
                    "login_count": 10
                }
            }
        }


class UpdateProfileRequest(SQLModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")

    class Config:
        """Pydantic配置"""
        json_schema_extra = {
            "example": {
                "nickname": "新昵称",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介"
            }
        }


class UpdateProfileResponse(SQLModel):
    """更新用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        """Pydantic配置"""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "新昵称",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介",
                "updated_at": "2025-01-20T15:45:00Z"
            }
        }