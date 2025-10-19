"""
服务层模块

该模块提供完整的服务层实现，作为数据层（Repository层）和API层之间的桥梁。
服务层承担完整的业务逻辑处理责任，包括复杂的事务处理、跨Repository协作和错误处理。

核心组件：
- Service基类：提供统一的服务接口和行为
- 异常类：提供丰富的上下文错误信息
- 具体服务类：实现各业务领域的业务逻辑

Services:
    AuthService: 处理用户认证相关业务逻辑
    UserService: 处理用户管理业务逻辑
    TaskService: 处理任务管理业务逻辑
    FocusService: 处理专注会话业务逻辑
    RewardService: 处理奖励系统业务逻辑
    StatisticsService: 处理统计分析业务逻辑
    ChatService: 处理AI对话业务逻辑
"""

from .base import BaseService, ServiceFactory
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    InsufficientBalanceException,
    DuplicateResourceException,
    AuthenticationException,
    AuthorizationException,
    create_exception,
    wrap_repository_error,
)
from .auth_service import AuthService
from .user_service import UserService
from .task_service import TaskService
from .focus_service import FocusService
from .reward_service import RewardService
from .statistics_service import StatisticsService
from .chat_service import ChatService

__all__ = [
    # 基础组件
    "BaseService",
    "ServiceFactory",

    # 异常类
    "BusinessException",
    "ValidationException",
    "ResourceNotFoundException",
    "InsufficientBalanceException",
    "DuplicateResourceException",
    "AuthenticationException",
    "AuthorizationException",

    # 异常工具函数
    "create_exception",
    "wrap_repository_error",

    # 服务类
    "AuthService",
    "UserService",
    "TaskService",
    "FocusService",
    "RewardService",
    "StatisticsService",
    "ChatService",
]

# 版本信息
__version__ = "1.0.0"

# 模块元数据
__author__ = "TaKeKe Backend Team"
__description__ = "TaKeKe Backend Service Layer Implementation"