"""
API层数据模型

定义所有API的请求和响应数据模型，确保数据验证和序列化。
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, EmailStr


# ================================
# 基础响应模型
# ================================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Any]
    total: int
    page: int
    limit: int
    has_more: bool
    pages: int


# ================================
# 枚举类型
# ================================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FocusSessionType(str, Enum):
    """专注会话类型枚举"""
    FOCUS = "focus"
    BREAK = "break"
    LONG_BREAK = "long_break"


class UserTypeEnum(str, Enum):
    """用户类型枚举"""
    GUEST = "guest"
    REGISTERED = "registered"
    PREMIUM = "premium"


class LoginType(str, Enum):
    """登录类型枚举"""
    PHONE = "phone"
    EMAIL = "email"
    WECHAT = "wechat"


# ================================
# 认证相关模型
# ================================

class GuestInitRequest(BaseModel):
    """游客初始化请求"""
    device_id: str = Field(..., description="设备ID")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    platform: Optional[str] = Field(None, description="平台信息")


class GuestUpgradeRequest(BaseModel):
    """游客升级请求"""
    upgrade_type: LoginType = Field(..., description="升级类型")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    wechat_code: Optional[str] = Field(None, description="微信授权码")
    verification_code: str = Field(..., description="验证码")
    device_id: str = Field(..., description="设备ID")

    @validator('phone')
    def validate_phone(cls, v, values):
        if values.get('upgrade_type') == LoginType.PHONE and not v:
            raise ValueError('手机号升级时必须提供手机号')
        if v and not v.isdigit() or len(v) != 11:
            raise ValueError('手机号格式不正确')
        return v

    @validator('email')
    def validate_email(cls, v, values):
        if values.get('upgrade_type') == LoginType.EMAIL and not v:
            raise ValueError('邮箱升级时必须提供邮箱')
        return v

    @validator('wechat_code')
    def validate_wechat_code(cls, v, values):
        if values.get('upgrade_type') == LoginType.WECHAT and not v:
            raise ValueError('微信升级时必须提供微信授权码')
        return v


class SMSCodeRequest(BaseModel):
    """短信验证码请求"""
    phone: str = Field(..., description="手机号", regex=r'^1[3-9]\d{9}$')
    type: str = Field(..., description="验证码类型", regex=r'^(login|register|reset_password)$')


class LoginRequest(BaseModel):
    """登录请求"""
    login_type: LoginType = Field(..., description="登录类型")
    phone: Optional[str] = Field(None, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    wechat_code: Optional[str] = Field(None, description="微信授权码")
    verification_code: str = Field(..., description="验证码")
    device_id: str = Field(..., description="设备ID")


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class AuthResponse(BaseModel):
    """认证响应"""
    user_id: str
    user_type: UserTypeEnum
    is_guest: bool
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    user_type: UserTypeEnum
    is_guest: bool
    phone: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


# ================================
# 任务相关模型
# ================================

class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(..., min_length=0, max_length=2000, description="任务描述")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000, description="预估工时")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    parent_task_id: Optional[str] = Field(None, description="父任务ID")

    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        for tag in v:
            if len(tag) > 50:
                raise ValueError('标签长度不能超过50个字符')
        return v


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="任务标题")
    description: Optional[str] = Field(None, min_length=0, max_length=2000, description="任务描述")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000, description="预估工时")
    actual_hours: Optional[float] = Field(None, ge=0, le=1000, description="实际工时")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    parent_task_id: Optional[str] = Field(None, description="父任务ID")


class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[datetime]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    tags: List[str]
    parent_task_id: Optional[str]
    children_count: int
    completion_percentage: float
    user_id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskCompleteRequest(BaseModel):
    """任务完成请求"""
    mood_feedback: Optional[str] = Field(None, description="心情反馈")
    completion_notes: Optional[str] = Field(None, max_length=500, description="完成备注")
    actual_hours: Optional[float] = Field(None, ge=0, le=1000, description="实际工时")


class TaskSearchParams(BaseModel):
    """任务搜索参数"""
    query: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[TaskStatus] = Field(None, description="状态筛选")
    priority: Optional[TaskPriority] = Field(None, description="优先级筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    due_date_start: Optional[datetime] = Field(None, description="截止日期开始")
    due_date_end: Optional[datetime] = Field(None, description="截止日期结束")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", regex=r'^(asc|desc)$', description="排序顺序")


class Top3TaskRequest(BaseModel):
    """Top3任务设置请求"""
    task_ids: List[str] = Field(..., min_items=1, max_items=3, description="任务ID列表")
    date: Optional[datetime] = Field(None, description="日期，默认为今天")


class Top3TaskResponse(BaseModel):
    """Top3任务响应"""
    date: str
    task_ids: List[str]
    tasks: List[TaskResponse]
    points_consumed: int


# ================================
# 专注会话相关模型
# ================================

class FocusSessionCreateRequest(BaseModel):
    """专注会话创建请求"""
    task_id: str = Field(..., description="关联任务ID")
    planned_duration_minutes: int = Field(25, ge=5, le=180, description="计划时长（分钟）")
    session_type: FocusSessionType = Field(FocusSessionType.FOCUS, description="会话类型")


class FocusSessionUpdateRequest(BaseModel):
    """专注会话更新请求"""
    actual_duration_minutes: Optional[int] = Field(None, ge=0, le=300, description="实际时长（分钟）")
    notes: Optional[str] = Field(None, max_length=1000, description="备注")


class FocusSessionResponse(BaseModel):
    """专注会话响应"""
    id: str
    task_id: str
    session_type: FocusSessionType
    planned_duration_minutes: int
    actual_duration_minutes: Optional[int]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    pause_time: Optional[datetime]
    resume_time: Optional[datetime]
    interruptions_count: int
    mood_feedback: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    user_id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FocusSessionCompleteRequest(BaseModel):
    """专注会话完成请求"""
    mood_feedback: Optional[str] = Field(None, description="心情反馈")
    notes: Optional[str] = Field(None, max_length=1000, description="完成备注")
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5, description="满意度评分")


class FocusStatisticsParams(BaseModel):
    """专注统计参数"""
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    task_id: Optional[str] = Field(None, description="任务ID筛选")


class FocusStatisticsResponse(BaseModel):
    """专注统计响应"""
    total_sessions: int
    total_minutes: int
    average_session_minutes: float
    completion_rate: float
    daily_average_minutes: float
    mood_distribution: Dict[str, int]
    session_type_distribution: Dict[str, int]
    trend_data: List[Dict[str, Any]]


# ================================
# 奖励系统相关模型
# ================================

class RewardCatalogResponse(BaseModel):
    """奖励目录响应"""
    id: str
    name: str
    description: str
    category: str
    fragment_cost: int
    points_cost: Optional[int]
    image_url: Optional[str]
    is_available: bool
    stock_quantity: Optional[int]
    probability: Optional[float]


class UserCollectionResponse(BaseModel):
    """用户收集状态响应"""
    user_id: str
    fragments: Dict[str, int]  # 碎片类型 -> 数量
    completed_sets: List[str]  # 已完成的套装
    in_progress_sets: List[Dict[str, Any]]  # 进行中的套装
    total_fragments: int
    last_updated: datetime


class PrizeRedeemRequest(BaseModel):
    """奖品兑换请求"""
    prize_id: str = Field(..., description="奖品ID")
    use_fragments: bool = Field(True, description="是否使用碎片")
    use_points: bool = Field(False, description="是否使用积分")


class PrizeRedeemResponse(BaseModel):
    """奖品兑换响应"""
    redemption_id: str
    prize_id: str
    user_id: str
    status: str
    fragments_used: Dict[str, int]
    points_used: int
    redeemed_at: datetime
    estimated_delivery: Optional[datetime]


class PointsBalanceResponse(BaseModel):
    """积分余额响应"""
    user_id: str
    current_balance: int
    total_earned: int
    total_spent: int
    last_updated: datetime


class PointsTransactionResponse(BaseModel):
    """积分记录响应"""
    id: str
    user_id: str
    type: str
    amount: int
    balance_after: int
    description: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    created_at: datetime


class PointsPackageResponse(BaseModel):
    """积分套餐响应"""
    id: str
    name: str
    description: str
    points_amount: int
    price: float
    currency: str
    bonus_points: int
    is_active: bool


class PointsPurchaseRequest(BaseModel):
    """积分购买请求"""
    package_id: str = Field(..., description="套餐ID")
    payment_method: str = Field(..., description="支付方式")


class PointsPurchaseResponse(BaseModel):
    """积分购买响应"""
    purchase_id: str
    user_id: str
    package_id: str
    points_amount: int
    price: float
    payment_method: str
    status: str
    created_at: datetime


# ================================
# 统计分析相关模型
# ================================

class DashboardStatsResponse(BaseModel):
    """仪表板统计响应"""
    user_id: str
    period_start: datetime
    period_end: datetime

    # 任务统计
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    overdue_tasks: int

    # 专注统计
    total_focus_minutes: int
    focus_sessions_count: int
    average_focus_minutes: float
    focus_completion_rate: float

    # 积分统计
    points_earned: int
    points_spent: int
    current_points_balance: int

    # 趋势数据
    daily_task_completion: List[Dict[str, Any]]
    daily_focus_minutes: List[Dict[str, Any]]
    mood_trend: List[Dict[str, Any]]


class TaskStatisticsParams(BaseModel):
    """任务统计参数"""
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    group_by: str = Field("day", regex=r'^(day|week|month)$', description="分组方式")


class TaskStatisticsResponse(BaseModel):
    """任务统计响应"""
    period_start: datetime
    period_end: datetime
    group_by: str

    # 基础统计
    total_tasks: int
    completed_tasks: int
    cancelled_tasks: int
    completion_rate: float

    # 分类统计
    priority_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    tag_distribution: Dict[str, int]

    # 时间统计
    average_completion_time_hours: float
    on_time_completion_rate: float

    # 趋势数据
    time_series_data: List[Dict[str, Any]]


# ================================
# 用户管理相关模型
# ================================

class UserProfileResponse(BaseModel):
    """用户资料响应"""
    user_id: str
    user_type: UserTypeEnum
    display_name: Optional[str]
    avatar_url: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    points: int
    fragments: Dict[str, int]
    level: int
    experience_points: int
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]


class UserProfileUpdateRequest(BaseModel):
    """用户资料更新请求"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=50, description="显示名称")
    avatar_url: Optional[str] = Field(None, description="头像URL")


class UserSettingsResponse(BaseModel):
    """用户设置响应"""
    user_id: str
    settings: Dict[str, Any]
    updated_at: datetime


class UserSettingsUpdateRequest(BaseModel):
    """用户设置更新请求"""
    settings: Dict[str, Any] = Field(..., description="设置数据")


class AvatarUploadResponse(BaseModel):
    """头像上传响应"""
    avatar_url: str
    file_size: int
    file_type: str
    uploaded_at: datetime


class UserFeedbackRequest(BaseModel):
    """用户反馈请求"""
    feedback_type: str = Field(..., description="反馈类型")
    content: str = Field(..., min_length=1, max_length=2000, description="反馈内容")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分")
    contact_info: Optional[str] = Field(None, description="联系方式")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")


class UserFeedbackResponse(BaseModel):
    """用户反馈响应"""
    feedback_id: str
    user_id: str
    feedback_type: str
    content: str
    rating: Optional[int]
    status: str
    created_at: datetime
    replied_at: Optional[datetime]
    reply_content: Optional[str]


# ================================
# AI对话相关模型
# ================================

class ChatSessionCreateRequest(BaseModel):
    """对话会话创建请求"""
    title: Optional[str] = Field(None, max_length=100, description="会话标题")
    initial_message: Optional[str] = Field(None, max_length=2000, description="初始消息")


class ChatSessionResponse(BaseModel):
    """对话会话响应"""
    id: str
    user_id: str
    title: str
    status: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class MessageSendRequest(BaseModel):
    """消息发送请求"""
    content: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    message_type: str = Field("text", regex=r'^(text|image|file)$', description="消息类型")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    session_id: str
    role: str  # user, assistant, system
    content: str
    message_type: str
    attachments: Optional[List[Dict[str, Any]]]
    created_at: datetime
    metadata: Optional[Dict[str, Any]]


class ChatHistoryResponse(BaseModel):
    """对话历史响应"""
    session_id: str
    messages: List[MessageResponse]
    total_count: int
    has_more: bool


class ChatSessionListResponse(BaseModel):
    """对话会话列表响应"""
    sessions: List[ChatSessionResponse]
    total_count: int
    page: int
    limit: int
    has_more: bool


# ================================
# 通用查询参数模型
# ================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.limit


class DateRangeParams(BaseModel):
    """日期范围参数"""
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('结束日期不能早于开始日期')
        return v