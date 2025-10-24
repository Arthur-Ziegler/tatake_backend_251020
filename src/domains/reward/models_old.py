"""
Reward领域数据模型

奖励系统模型，基于v3 API方案重新设计。
移除UserReward库存表，采用流水记录方式。

核心模型：
- Reward: 奖品实体（简化版）
- RewardRecipe: 奖品兑换配方（支持name字段）
- RewardTransaction: 奖品流水记录
- PointsTransaction: 积分流水记录

设计原则：
1. 流水记录：所有变动通过流水表记录，余额实时计算
2. 事务组关联：兑换操作的多个记录通过transaction_group关联
3. 类型安全：使用枚举类型定义source_type
4. JSON字段：直接使用SQLAlchemy JSON字段，无需序列化工具

作者：TaTakeKe团队
版本：v2.0（基于v3 API方案）
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, JSON, Index, Text
from sqlalchemy import DateTime

try:
    from src.domains.auth.models import BaseModel
except ImportError:
    from ...auth.models import BaseModel


class Reward(BaseModel, table=True):
    """
    奖品实体模型（简化版）

    存储所有奖品的基本信息，无等级概念。
    兑换关系通过RewardRecipe配方表定义。

    移除字段：icon, is_exchangeable（v3方案不需要）
    保留字段：name, description, points_value
    """

    __tablename__ = "rewards"

    name: str = Field(
        ...,
        max_length=100,
        description="奖品名称",
        index=True
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="奖品描述"
    )
    points_value: int = Field(
        ...,
        ge=0,
        description="奖品积分价值"
    )

    __table_args__ = (
        Index('idx_reward_name', 'name'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


class RewardRecipe(BaseModel, table=True):
    """
    奖品兑换配方模型

    定义奖品之间的兑换关系，支持灵活的组合兑换。
    支持：1个配方名称，结果奖品ID，所需材料列表（JSON格式）

    新增字段：name（配方名称，便于前端显示）
    """

    __tablename__ = "reward_recipes"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="配方ID"
    )
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="配方名称，便于前端显示"
    )
    result_reward_id: UUID = Field(
        ...,
        description="兑换结果奖品ID"
    )
    required_rewards: List[Dict[str, Any]] = Field(
        ...,
        sa_column=Column(JSON),
        description="所需奖品列表，JSON格式: [{'reward_id': 'uuid', 'quantity': 10}]"
    )

    __table_args__ = (
        Index('idx_recipe_result', 'result_reward_id'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


class RewardTransaction(BaseModel, table=True):
    """
    奖品流水记录模型

    记录所有奖品变动，包括获得、消耗、兑换等操作。
    支持事务组关联，用于追踪兑换操作的多个流水记录。

    字段设计：
    - quantity: 正数表示获得，负数表示消耗
    - source_type: 枚举类型，确保类型安全
    - transaction_group: 可选，用于关联同一兑换操作的多个记录
    """

    __tablename__ = "reward_transactions"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="流水记录ID"
    )
    user_id: UUID = Field(
        ...,
        index=True,
        description="用户ID"
    )
    reward_id: UUID = Field(
        ...,
        index=True,
        description="奖品ID"
    )
    quantity: int = Field(
        ...,
        description="奖品变动数量，正=获得，负=消耗"
    )
    source_type: str = Field(
        ...,
        max_length=50,
        description="来源类型: top3_lottery | recipe_consume | recipe_produce"
    )
    source_id: Optional[UUID] = Field(
        default=None,
        description="关联ID（如task_id, recipe_id等）"
    )
    transaction_group: Optional[str] = Field(
        default=None,
        max_length=64,
        description="事务组ID，用于关联同一兑换操作的多个流水记录"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间"
    )

    __table_args__ = (
        Index('idx_user_reward_time', 'user_id', 'created_at'),
        Index('idx_transaction_group', 'transaction_group'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


class PointsTransaction(BaseModel, table=True):
    """
    积分流水记录模型

    记录所有积分变动，余额 = SUM(amount)。
    amount为正数表示收入，负数表示支出。

    设计优化：
    - 直接SUM聚合查询，无需余额表
    - 完整的来源类型追踪
    - 支持事务组关联（虽然积分通常不需要，但保持一致性）
    """

    __tablename__ = "points_transactions"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="积分流水记录ID"
    )
    user_id: UUID = Field(
        ...,
        index=True,
        description="用户ID"
    )
    amount: int = Field(
        ...,
        description="积分变动数量，正=收入，负=支出"
    )
    source_type: str = Field(
        ...,
        max_length=50,
        description="来源类型: task_complete | task_complete_top3 | top3_cost | lottery_points"
    )
    source_id: Optional[UUID] = Field(
        default=None,
        description="关联ID（如task_id, recipe_id等）"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间"
    )

    __table_args__ = (
        Index('idx_user_points_time', 'user_id', 'created_at'),
        Index('idx_points_source', 'source_type'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


# 移除的模型（保留代码以备参考）
# class UserReward(BaseModel, table=True):
#     """
#     用户奖品模型（已删除，使用流水记录替代）
#
#     记录用户拥有的奖品及数量。
#     现在通过reward_transactions聚合计算实现。
#     """
#     __tablename__ = "user_rewards"
#
#     user_id: UUID = Field(
#         ...,
#         index=True,
#         description="用户ID"
#     )
#     reward_id: UUID = Field(
#         ...,
#         index=True,
#         description="奖品ID"
#     )
#     quantity: int = Field(
#         default=0,
#         ge=0,
#         description="拥有数量"
#     )
#     obtained_at: datetime = Field(
#         default_factory=datetime.utcnow,
#         sa_column=Column(DateTime(timezone=True)),
#         description="获得时间"
#     )
#
#     __table_args__ = (
#         Index('idx_user_reward', 'user_id', 'reward_id', unique=True),
#         {
#             'mysql_engine': 'InnoDB',
#             'mysql_charset': 'utf8mb4'
#         }
#     )