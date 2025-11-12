"""User领域Schema定义 - 简化版本

只包含增强的用户信息Schema，删除重复和不需要的Schema。
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EnhancedUserProfileResponse(BaseModel):
    """增强用户信息响应"""

    # 基础字段
    id: str = Field(..., description="用户ID")
    nickname: str = Field(..., description="用户昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="用户简介")
    wechat_openid: Optional[str] = Field(None, description="微信OpenID")
    is_guest: bool = Field(False, description="是否为游客")
    is_active: bool = Field(True, description="是否激活")
    created_at: str = Field(..., description="创建时间")
    last_login_at: Optional[str] = Field(None, description="最后登录时间")

    # 新增个人信息字段
    gender: Optional[str] = Field(None, description="性别: male, female, other")
    birthday: Optional[str] = Field(None, description="生日 (ISO格式)")

    # 偏好设置字段
    theme: str = Field("light", description="主题: light, dark, auto, system")
    language: str = Field("zh-CN", description="语言: zh-CN, en-US等")

    # 业务相关字段
    points_balance: int = Field(0, description="积分余额")
    stats: Optional[Dict[str, Any]] = Field(None, description="用户统计信息")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "nickname": "张三",
                "avatar": "https://example.com/avatar.jpg",
                "bio": "这是用户简介",
                "wechat_openid": None,
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
                    "total_points": 3000,
                    "login_count": 50,
                    "last_active_at": "2025-01-20T15:45:00Z"
                }
            }
        }
    )


class EnhancedUpdateProfileRequest(BaseModel):
    """增强的更新用户信息请求模型"""

    # 基础信息字段
    nickname: Optional[str] = Field(None, description="用户昵称", min_length=1, max_length=50, example="张小明")
    avatar_url: Optional[str] = Field(None, description="头像URL", example="https://example.com/avatar.jpg")
    bio: Optional[str] = Field(None, description="用户简介", max_length=500, example="这是我的个人简介")

    # 个人信息字段
    gender: Optional[str] = Field(None, description="性别: male, female, other", example="male")
    birthday: Optional[str] = Field(None, description="生日 (ISO格式: YYYY-MM-DD)", example="1990-05-15")

    # 偏好设置字段
    theme: Optional[str] = Field(None, description="主题: light, dark, auto, system", example="dark")
    language: Optional[str] = Field(None, description="语言: zh-CN, en-US等", example="zh-CN")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "nickname": "新昵称",
                "avatar_url": "https://example.com/new-avatar.jpg",
                "bio": "这是我的新简介",
                "gender": "female",
                "birthday": "1985-08-20",
                "theme": "dark",
                "language": "en-US"
            }
        }
    )