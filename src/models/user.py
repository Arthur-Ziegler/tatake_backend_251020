"""
用户相关数据模型

本模块定义了用户系统相关的数据模型，包括：
- User: 用户基本信息模型
- UserSettings: 用户设置模型（与User一对一关系）

设计原则：
1. 用户唯一性：通过phone、email、wechat_openid确保用户唯一标识
2. 灵活登录：支持游客模式和多种登录方式
3. 数据完整：提供完整的用户信息字段，支持渐进式完善
4. 隐私保护：敏感信息字段设计为可选，支持匿名使用

使用示例：
    >>> user = User(nickname="张三", email="zhangsan@example.com")
    >>> session.add(user)
    >>> session.commit()
    >>> print(f"用户ID: {user.id}")
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

# 导入基础模型类
from src.models.base_model import BaseSQLModel

# 避免循环导入的类型检查
if TYPE_CHECKING:
    pass


class User(BaseSQLModel, table=True):
    """
    用户基本信息模型

    存储用户的基本信息，支持多种登录方式和用户类型。
    每个用户通过phone、email或wechat_openid进行唯一标识。

    Attributes:
        nickname (str): 用户昵称，必填字段，用于显示
        avatar (Optional[str]): 头像URL，可选字段
        phone (Optional[str]): 手机号，可选字段，唯一约束
        email (Optional[str]): 邮箱地址，可选字段，唯一约束
        wechat_openid (Optional[str]): 微信OpenID，可选字段，唯一约束
        is_guest (bool): 是否为游客用户，默认为False
        last_login_at (Optional[datetime]): 最后登录时间，可选字段
        settings (Optional[UserSettings]): 用户设置，一对一关系
        tasks (List[Task]): 用户任务列表，一对多关系
        focus_sessions (List[FocusSession]): 专注会话列表，一对多关系
        chat_sessions (List[ChatSession]): 聊天会话列表，一对多关系
    """

    __tablename__ = "users"

    # 基本信息
    nickname: str = Field(
        max_length=50,
        description="用户昵称，用于显示和识别"
    )

    avatar: Optional[str] = Field(
        default=None,
        max_length=255,
        description="用户头像URL，支持HTTP/HTTPS协议"
    )

    # 唯一标识字段（用于登录和用户识别）
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        unique=True,
        index=True,
        description="手机号码，用于登录和用户识别，全局唯一"
    )

    email: Optional[str] = Field(
        default=None,
        max_length=100,
        unique=True,
        index=True,
        description="邮箱地址，用于登录和用户识别，全局唯一"
    )

    wechat_openid: Optional[str] = Field(
        default=None,
        max_length=100,
        unique=True,
        index=True,
        description="微信OpenID，用于微信登录，全局唯一"
    )

    # 用户类型和状态
    is_guest: bool = Field(
        default=False,
        description="是否为游客用户，游客用户功能受限"
    )

    # 时间相关字段
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="最后登录时间，用于用户活跃度统计"
    )

    # 关系定义
    settings: Optional["UserSettings"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete-orphan"
        }
    )

    # 任务关系
    tasks: list["Task"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan"
        }
    )

    # focus_sessions: list["FocusSession"] = Relationship(
    #     back_populates="user",
    #     sa_relationship_kwargs={
    #         "cascade": "all, delete-orphan"
    #     }
    # )

    chat_sessions: list["ChatSession"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan"
        }
    )

    def __repr__(self) -> str:
        """
        返回用户的字符串表示

        Returns:
            str: 用户的基本信息表示

        Example:
            >>> user = User(nickname="张三")
            >>> print(repr(user))
            User(id=uuid-string)
        """
        return f"User(id={self.id})"

    def __str__(self) -> str:
        """
        返回用户友好的字符串表示

        Returns:
            str: 用户的昵称表示

        Example:
            >>> user = User(nickname="张三")
            >>> print(str(user))
            张三
        """
        return self.nickname

    
    def is_active_user(self) -> bool:
        """
        判断用户是否为活跃用户

        基于最后登录时间判断用户活跃度。
        如果用户从未登录或者超过30天未登录，则认为不活跃。

        Returns:
            bool: 如果用户活跃返回True，否则返回False

        Example:
            >>> user = User(nickname="张三")
            >>> user.last_login_at = datetime.now(timezone.utc)
            >>> print(user.is_active_user())
            True
        """
        if self.last_login_at is None:
            return False

        now = datetime.now(timezone.utc)
        # 确保时间对象都有时区信息
        if self.last_login_at.tzinfo is None:
            last_login = self.last_login_at.replace(tzinfo=timezone.utc)
        else:
            last_login = self.last_login_at

        days_since_login = (now - last_login).days
        return days_since_login <= 30

    def update_last_login(self) -> None:
        """
        更新用户最后登录时间为当前时间

        这个方法应该在用户成功登录时调用，
        用于记录用户活跃度和统计分析。

        Example:
            >>> user = User(nickname="张三")
            >>> user.update_last_login()
            >>> print(user.last_login_at)
            2023-12-01 10:30:00+00:00
        """
        self.last_login_at = datetime.now(timezone.utc)

    def has_valid_contact(self) -> bool:
        """
        判断用户是否有有效的联系方式

        检查用户是否提供了至少一种联系方式（手机、邮箱或微信）。

        Returns:
            bool: 如果用户有有效联系方式返回True，否则返回False

        Example:
            >>> user = User(nickname="张三", email="zhangsan@example.com")
            >>> print(user.has_valid_contact())
            True
        """
        return bool(self.phone or self.email or self.wechat_openid)

    def get_primary_identifier(self) -> str:
        """
        获取用户的主要标识符

        按优先级返回用户的标识符：邮箱 > 手机号 > 微信OpenID > 昵称

        Returns:
            str: 用户的主要标识符

        Example:
            >>> user = User(nickname="张三", email="zhangsan@example.com")
            >>> print(user.get_primary_identifier())
            zhangsan@example.com
        """
        if self.email:
            return self.email
        elif self.phone:
            return self.phone
        elif self.wechat_openid:
            return self.wechat_openid
        else:
            return self.nickname

    def can_upgrade_to_regular_user(self) -> bool:
        """
        判断游客用户是否可以升级为普通用户

        游客用户需要提供至少一种有效联系方式才能升级。

        Returns:
            bool: 如果可以升级返回True，否则返回False

        Example:
            >>> user = User(nickname="游客", is_guest=True)
            >>> print(user.can_upgrade_to_regular_user())
            False
            >>> user.email = "guest@example.com"
            >>> print(user.can_upgrade_to_regular_user())
            True
        """
        return self.is_guest and self.has_valid_contact()

    def upgrade_to_regular_user(self) -> bool:
        """
        将游客用户升级为普通用户

        如果用户有有效联系方式，则将is_guest设置为False。

        Returns:
            bool: 如果升级成功返回True，否则返回False

        Example:
            >>> user = User(nickname="游客", is_guest=True, email="guest@example.com")
            >>> success = user.upgrade_to_regular_user()
            >>> print(success, user.is_guest)
            True False
        """
        if self.can_upgrade_to_regular_user():
            self.is_guest = False
            return True
        return False


class UserSettings(BaseSQLModel, table=True):
    """
    用户设置模型

    存储用户的个人偏好设置和应用配置，
    与User模型建立一对一关系。

    Attributes:
        user_id (str): 用户ID，外键关联到User表，唯一约束
        focus_duration (int): 专注时长（分钟），默认25分钟
        break_duration (int): 休息时长（分钟），默认5分钟
        long_break_duration (int): 长休息时长（分钟），默认15分钟
        auto_start_breaks (bool): 自动开始休息，默认False
        auto_start_focus (bool): 自动开始专注，默认False
        notification_enabled (bool): 通知开关，默认True
        sound_enabled (bool): 声音开关，默认True
        theme (str): 主题设置，默认"light"
        language (str): 语言设置，默认"zh-CN"
        timezone (str): 时区设置，默认"Asia/Shanghai"
        user (User): 关联的用户，一对一关系
    """

    __tablename__ = "user_settings"

    # 外键关联
    user_id: str = Field(
        foreign_key="users.id",
        unique=True,
        index=True,
        description="用户ID，与User表建立一对一关系"
    )

    # 专注时间设置
    focus_duration: int = Field(
        default=25,
        ge=1,
        le=120,
        description="专注时长（分钟），范围1-120分钟"
    )

    break_duration: int = Field(
        default=5,
        ge=1,
        le=30,
        description="休息时长（分钟），范围1-30分钟"
    )

    long_break_duration: int = Field(
        default=15,
        ge=1,
        le=60,
        description="长休息时长（分钟），范围1-60分钟"
    )

    # 自动化设置
    auto_start_breaks: bool = Field(
        default=False,
        description="专注结束后自动开始休息"
    )

    auto_start_focus: bool = Field(
        default=False,
        description="休息结束后自动开始专注"
    )

    # 通知设置
    notification_enabled: bool = Field(
        default=True,
        description="是否启用通知提醒"
    )

    sound_enabled: bool = Field(
        default=True,
        description="是否启用声音提醒"
    )

    # 界面设置
    theme: str = Field(
        default="light",
        max_length=20,
        description="界面主题，如light、dark等"
    )

    language: str = Field(
        default="zh-CN",
        max_length=10,
        description="界面语言设置"
    )

    timezone: str = Field(
        default="Asia/Shanghai",
        max_length=50,
        description="用户时区设置"
    )

    # 关系定义
    user: User = Relationship(
        back_populates="settings",
        sa_relationship_kwargs={
            "uselist": False
        }
    )

    def __repr__(self) -> str:
        """
        返回用户设置的字符串表示

        Returns:
            str: 用户设置的基本信息表示

        Example:
            >>> settings = UserSettings(user_id="user123")
            >>> print(repr(settings))
            UserSettings(id=uuid-string)
        """
        return f"UserSettings(id={self.id})"

    def is_pomodoro_configuration(self) -> bool:
        """
        判断是否为标准番茄钟配置

        检查当前设置是否符合标准的番茄钟时间配置（25-5-15）。

        Returns:
            bool: 如果是标准配置返回True，否则返回False

        Example:
            >>> settings = UserSettings(user_id="user123")
            >>> print(settings.is_pomodoro_configuration())
            True
        """
        return (
            self.focus_duration == 25 and
            self.break_duration == 5 and
            self.long_break_duration == 15
        )

    def get_total_cycle_time(self) -> int:
        """
        获取完整番茄钟周期的总时间

        计算一个完整番茄钟周期（专注+休息）的总时间。

        Returns:
            int: 总时间（分钟）

        Example:
            >>> settings = UserSettings(user_id="user123")
            >>> print(settings.get_total_cycle_time())
            30  # 25分钟专注 + 5分钟休息
        """
        return self.focus_duration + self.break_duration

    def reset_to_defaults(self) -> None:
        """
        重置设置为默认值

        将所有设置重置为系统默认值。

        Example:
            >>> settings = UserSettings(user_id="user123", focus_duration=30)
            >>> settings.reset_to_defaults()
            >>> print(settings.focus_duration)
            25
        """
        self.focus_duration = 25
        self.break_duration = 5
        self.long_break_duration = 15
        self.auto_start_breaks = False
        self.auto_start_focus = False
        self.notification_enabled = True
        self.sound_enabled = True
        self.theme = "light"
        self.language = "zh-CN"
        self.timezone = "Asia/Shanghai"


# 导出所有用户相关模型
__all__ = [
    "User",
    "UserSettings"
]