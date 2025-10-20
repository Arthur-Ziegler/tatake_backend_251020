# 数据模型模块

# 导入基础模型
from src.models.base_model import BaseSQLModel

# 导入枚举类型
from src.models.enums import (
    TaskStatus, PriorityLevel, SessionType,
    RewardType, RewardStatus, TransactionType
)

# 导入用户模型
from src.models.user import User, UserSettings

# 导入任务模型
from src.models.task import Task, TaskTop3, TaskTag

# 导入专注系统模型
from src.models.focus import FocusSession, FocusSessionBreak, FocusSessionTemplate

# 导入奖励系统模型
from src.models.reward import (
    Reward, RewardRule, UserFragment,
    LotteryRecord, PointsTransaction
)

# 导入认证系统模型
from src.models.auth import (
    TokenBlacklist, TokenBlacklistCreate, TokenBlacklistRead,
    SmsVerification, SmsVerificationCreate, SmsVerificationRead,
    UserSession, UserSessionCreate, UserSessionRead,
    AuthLog, AuthLogCreate, AuthLogRead
)

# 导入聊天系统模型
from src.models.chat import ChatSession, ChatMessage

# 导出所有模型
__all__ = [
    # 基础模型
    "BaseSQLModel",

    # 枚举类型
    "TaskStatus",
    "PriorityLevel",
    "SessionType",
    "RewardType",
    "RewardStatus",
    "TransactionType",

    # 用户模型
    "User",
    "UserSettings",

    # 任务模型
    "Task",
    "TaskTop3",
    "TaskTag",

    # 专注系统模型
    "FocusSession",
    "FocusSessionBreak",
    "FocusSessionTemplate",

    # 奖励系统模型
    "Reward",
    "RewardRule",
    "UserFragment",
    "LotteryRecord",
    "PointsTransaction",

    # 认证系统模型
    "TokenBlacklist",
    "TokenBlacklistCreate",
    "TokenBlacklistRead",
    "SmsVerification",
    "SmsVerificationCreate",
    "SmsVerificationRead",
    "UserSession",
    "UserSessionCreate",
    "UserSessionRead",
    "AuthLog",
    "AuthLogCreate",
    "AuthLogRead",

    # 聊天系统模型
    "ChatSession",
    "ChatMessage",
]