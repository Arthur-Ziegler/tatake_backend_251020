"""User领域Schema定义"""

from typing import Optional
from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """用户信息响应"""
    id: str
    nickname: str
    avatar: Optional[str]
    wechat_openid: Optional[str]
    is_guest: bool
    created_at: str
    last_login_at: str


class UpdateProfileRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = None


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    type: str = Field(..., description="反馈类型: bug_report/feature_request/general_feedback/complaint")
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    contact_info: Optional[str] = None
