"""
零Bug测试体系 - 测试数据工厂

提供标准化、可重用的测试数据生成机制，确保测试数据的一致性和可靠性。

设计原则：
1. 数据隔离：每个测试使用独立的数据
2. 确定可重现：相同输入产生相同输出
3. 边界覆盖：涵盖正常、边界、异常情况
4. 性能优化：批量创建和缓存机制
"""

from .base import BaseFactory
from .users import UserFactory, AuthLogFactory
from .tasks import TaskFactory, TaskCompletionFactory
from .rewards import RewardFactory, UserRewardFactory, RecipeFactory
from .focus import FocusSessionFactory, FocusOperationFactory
from .top3 import Top3TaskFactory
from .points import PointsTransactionFactory

__all__ = [
    # 基础工厂
    "BaseFactory",

    # 用户相关工厂
    "UserFactory",
    "AuthLogFactory",

    # 任务相关工厂
    "TaskFactory",
    "TaskCompletionFactory",

    # 奖励相关工厂
    "RewardFactory",
    "UserRewardFactory",
    "RecipeFactory",

    # 专注系统工厂
    "FocusSessionFactory",
    "FocusOperationFactory",

    # Top3系统工厂
    "Top3TaskFactory",

    # 积分系统工厂
    "PointsTransactionFactory",
]