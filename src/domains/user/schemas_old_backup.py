"""User领域Schema定义"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserProfileResponse(BaseModel):
    """用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    is_guest: bool = Field(..., description="是否为游客")
    created_at: str = Field(..., description="创建时间")
    last_login_at: Optional[str] = Field(None, description="最后登录时间")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "avatar": "https://example.com/avatar.jpg",
                "bio": "这是用户简介",
                "wechat_openid": "ox1234567890abcdef",
                "is_guest": False,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login_at": "2025-01-20T15:45:00Z"
            }
        }
    )


class UpdateProfileRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "nickname": "新昵称",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介"
            }
        }
    )


# ===== 响应模型 =====

class UpdateProfileResponse(BaseModel):
    """更新用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    updated_fields: list[str] = Field(..., description="已更新的字段列表")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介",
                "updated_fields": ["nickname", "avatar_url", "bio"]
            }
        }


class WelcomeGiftRewardItem(BaseModel):
    """欢迎礼包奖励物品"""
    name: str = Field(..., description="奖励名称")
    quantity: int = Field(..., description="奖励数量")
    description: str = Field(..., description="奖励描述")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "name": "积分加成卡",
                "quantity": 3,
                "description": "+50%积分，有效期1小时"
            }
        }


class WelcomeGiftResponse(BaseModel):
    """欢迎礼包领取响应"""
    points_granted: int = Field(..., description="发放的积分数")
    rewards_granted: list[WelcomeGiftRewardItem] = Field(..., description="发放的奖励物品列表")
    transaction_group: str = Field(..., description="事务组ID")
    granted_at: str = Field(..., description="发放时间")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "points_granted": 1000,
                "rewards_granted": [
                    {
                        "name": "积分加成卡",
                        "quantity": 3,
                        "description": "+50%积分，有效期1小时"
                    }
                ],
                "transaction_group": "welcome_gift_user123_abc12345",
                "granted_at": "2025-01-20T15:45:00Z"
            }
        }


class WelcomeGiftHistoryItem(BaseModel):
    """欢迎礼包历史记录项"""
    transaction_group: str = Field(..., description="事务组ID")
    granted_at: str = Field(..., description="发放时间")
    points_granted: int = Field(..., description="发放的积分数")
    rewards_count: int = Field(..., description="奖励物品总数")
    reward_items: list[dict] = Field(..., description="奖励物品详情")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "transaction_group": "welcome_gift_user123_abc12345",
                "granted_at": "2025-01-20T15:45:00Z",
                "points_granted": 1000,
                "rewards_count": 18,
                "reward_items": [
                    {
                        "name": "积分加成卡",
                        "quantity": 3,
                        "description": "+50%积分，有效期1小时"
                    }
                ]
            }
        }


class WelcomeGiftHistoryResponse(BaseModel):
    """欢迎礼包历史响应"""
    history: list[WelcomeGiftHistoryItem] = Field(..., description="领取历史列表")
    total_count: int = Field(..., description="总领取次数")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "history": [
                    {
                        "transaction_group": "welcome_gift_user123_abc12345",
                        "granted_at": "2025-01-20T15:45:00Z",
                        "points_granted": 1000,
                        "rewards_count": 18,
                        "reward_items": [
                            {
                                "name": "积分加成卡",
                                "quantity": 3,
                                "description": "+50%积分，有效期1小时"
                            }
                        ]
                    }
                ],
                "total_count": 5
            }
        }


# ===== 增强的Profile功能Schema =====

class EnhancedUserProfileResponse(BaseModel):
    """增强的用户信息响应模型"""
    # 基础字段
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    is_guest: bool = Field(..., description="是否为游客")
    is_active: bool = Field(..., description="是否激活")
    created_at: str = Field(..., description="创建时间")
    last_login_at: Optional[str] = Field(None, description="最后登录时间")

    # 新增个人信息字段
    gender: Optional[str] = Field(None, description="性别 (male/female/other)")
    birthday: Optional[str] = Field(None, description="生日")

    # 偏好设置字段
    theme: Optional[str] = Field("light", description="主题设置 (light/dark/auto/system)")
    language: Optional[str] = Field("zh-CN", description="语言设置")

    # 业务相关字段
    points_balance: int = Field(0, description="积分余额")
    stats: Optional[dict] = Field(None, description="用户统计信息")

    model_config = ConfigDict(
        json_schema_extra={
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
                "gender": "male",
                "birthday": "1990-05-15",
                "theme": "dark",
                "language": "zh-CN",
                "points_balance": 1500,
                "stats": {
                    "tasks_completed": 25,
                    "total_points": 150,
                    "login_count": 10
                }
            }
        }
    )


class EnhancedUpdateProfileRequest(BaseModel):
    """增强的更新用户信息请求模型"""
    # 基础字段
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")

    # 新增个人信息字段
    gender: Optional[str] = Field(None, description="性别 (male/female/other)")
    birthday: Optional[str] = Field(None, description="生日")

    # 偏好设置字段
    theme: Optional[str] = Field(None, description="主题设置 (light/dark/auto/system)")
    language: Optional[str] = Field(None, description="语言设置")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nickname": "新昵称",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介",
                "gender": "female",
                "birthday": "1992-08-20",
                "theme": "auto",
                "language": "en-US"
            }
        }
    )
