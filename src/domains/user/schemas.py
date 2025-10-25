"""User领域Schema定义"""

from typing import Optional, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

# ===== 统一响应格式 =====

class UnifiedResponse(BaseModel, Generic[T]):
    """
    统一响应格式

    所有API端点都使用这个统一的响应格式：
    - code: HTTP状态码（200, 400, 401, 403, 404, 409等）
    - data: 响应数据，成功时包含具体数据，失败时为null
    - message: 响应消息，成功时为"success"，失败时为具体错误描述
    """
    code: int = Field(..., description="HTTP状态码")
    data: Optional[T] = Field(None, description="响应数据，成功时包含具体数据，失败时为null")
    message: str = Field(..., description="响应消息")


class UserProfileResponse(BaseModel):
    """用户信息响应"""
    id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000", description="用户ID")
    nickname: str = Field(..., example="张三", description="用户昵称")
    avatar: Optional[str] = Field(None, example="https://example.com/avatar.jpg", description="头像URL")
    wechat_openid: Optional[str] = Field(None, example="ox1234567890abcdef", description="微信OpenID")
    is_guest: bool = Field(..., example=False, description="是否为游客")
    created_at: str = Field(..., example="2024-01-15T10:30:00Z", description="创建时间")
    last_login_at: str = Field(..., example="2025-01-20T15:45:00Z", description="最后登录时间")


class UpdateProfileRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, example="新昵称", description="用户昵称")


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    type: str = Field(...,
        example="bug_report", description="反馈类型: bug_report/feature_request/other")
    title: str = Field(..., min_length=1, max_length=100, example="登录问题", description="反馈标题")
    content: str = Field(..., min_length=1, max_length=2000, example="无法通过微信登录", description="反馈内容")
    contact_info: Optional[str] = Field(None, example="user@example.com", description="联系方式")


# ===== 响应模型 =====

class UpdateProfileResponse(BaseModel):
    """更新用户信息响应"""
    id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000", description="用户ID")
    nickname: str = Field(..., example="张三", description="用户昵称")
    updated_fields: list[str] = Field(..., example=["nickname"], description="已更新的字段列表")


class AvatarUploadResponse(BaseModel):
    """头像上传响应"""
    avatar_url: str = Field(..., example="https://example.com/avatars/550e8400-e29b-41d4-a716-446655440000.jpg", description="头像URL")
    message: str = Field(..., example="头像上传成功（占位实现）", description="处理消息")


class FeedbackSubmitResponse(BaseModel):
    """反馈提交响应"""
    feedback_id: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000", description="反馈ID")
    status: str = Field(..., example="pending", description="反馈状态")
    message: str = Field(..., example="反馈已提交，我们会尽快处理", description="处理消息")


class WelcomeGiftRewardItem(BaseModel):
    """欢迎礼包奖励物品"""
    name: str = Field(..., example="积分加成卡", description="奖励名称")
    quantity: int = Field(..., example=3, description="奖励数量")
    description: str = Field(..., example="+50%积分，有效期1小时", description="奖励描述")


class WelcomeGiftResponse(BaseModel):
    """欢迎礼包领取响应"""
    points_granted: int = Field(..., example=1000, description="发放的积分数")
    rewards_granted: list[WelcomeGiftRewardItem] = Field(..., description="发放的奖励物品列表")
    transaction_group: str = Field(..., example="welcome_gift_user123_abc12345", description="事务组ID")
    granted_at: str = Field(..., example="2025-01-20T15:45:00Z", description="发放时间")


class WelcomeGiftHistoryItem(BaseModel):
    """欢迎礼包历史记录项"""
    transaction_group: str = Field(..., example="welcome_gift_user123_abc12345", description="事务组ID")
    granted_at: str = Field(..., example="2025-01-20T15:45:00Z", description="发放时间")
    points_granted: int = Field(..., example=1000, description="发放的积分数")
    rewards_count: int = Field(..., example=18, description="奖励物品总数")
    reward_items: list[dict] = Field(..., description="奖励物品详情")


class WelcomeGiftHistoryResponse(BaseModel):
    """欢迎礼包历史响应"""
    history: list[WelcomeGiftHistoryItem] = Field(..., description="领取历史列表")
    total_count: int = Field(..., example=5, description="总领取次数")
