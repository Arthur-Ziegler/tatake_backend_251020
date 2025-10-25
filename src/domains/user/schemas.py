"""User领域Schema定义"""

from typing import Optional
from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    is_guest: bool = Field(..., description="是否为游客")
    created_at: str = Field(..., description="创建时间")
    last_login_at: str = Field(..., description="最后登录时间")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "avatar": "https://example.com/avatar.jpg",
                "wechat_openid": "ox1234567890abcdef",
                "is_guest": False,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login_at": "2025-01-20T15:45:00Z"
            }
        }


class UpdateProfileRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, description="用户昵称")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "nickname": "新昵称"
            }
        }


# ===== 响应模型 =====

class UpdateProfileResponse(BaseModel):
    """更新用户信息响应"""
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    updated_fields: list[str] = Field(..., description="已更新的字段列表")

    class Config:
        """Pydantic配置 - 使用json_schema_extra提供示例"""
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "updated_fields": ["nickname"]
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
