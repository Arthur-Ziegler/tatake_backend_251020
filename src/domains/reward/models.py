"""
Reward领域数据模型

奖励系统模型，基于v3 API方案重新设计。
移除UserReward库存表，采用流水记录方式。

核心模型：
- Reward: 奖品实体（简化版）
- RewardRecipe: 奖品兑换配方（支持name字段）
- RewardTransaction: 奖品流水记录

设计原则：
1. 流水记录：所有变动通过流水表记录，余额实时计算
2. 事务组关联：兑换操作的多个记录通过transaction_group关联
3. 类型安全：使用枚举类型定义source_type
4. JSON字段：直接使用SQLAlchemy JSON字段，无需序列化工具

作者：TaTakeKe团队
版本：v2.0（基于v3 API方案）
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlmodel import Field, SQLModel, Column, Index, Text
from sqlalchemy import DateTime, JSON as SQLAlchemyJSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

try:
    from src.domains.auth.models import BaseModel
except ImportError:
    from sqlmodel import SQLModel as BaseModel


class Reward(BaseModel, table=True):
    model_config = {"arbitrary_types_allowed": True}
    """
    奖品实体模型

    定义可兑换的奖品信息，支持不同类型的奖品。
    移除UserReward库存表，通过流水记录追踪用户奖品。

    字段说明：
    - cost_type: 成本类型，支持points和recipe
    - image_url: 奖品图片URL
    """

    __tablename__ = "rewards"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="奖品ID"
    )
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
    image_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="奖品图片URL"
    )
    cost_type: str = Field(
        ...,
        max_length=20,
        description="成本类型：points | recipe"
    )
    cost_value: int = Field(
        ...,
        ge=0,
        description="成本数值"
    )
    stock_quantity: int = Field(
        default=0,
        ge=0,
        description="库存数量"
    )
    category: str = Field(
        ...,
        max_length=50,
        description="奖品分类"
    )
    is_active: bool = Field(
        default=True,
        description="是否启用"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间"
    )

    __table_args__ = (
        Index('idx_reward_name', 'name'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


class RewardRecipe(BaseModel, table=True):
    class Config:
        arbitrary_types_allowed = True
    """
    奖品兑换配方模型

    定义奖品之间的兑换关系，支持灵活的组合兑换。
    支持：1个配方名称，结果奖品ID，所需材料列表（JSON格式）

    新增字段：name（配方名称，便于前端显示）
    """

    __tablename__ = "reward_recipes"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="配方ID"
    )
    name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="配方名称，便于前端显示"
    )
    result_reward_id: str = Field(
        ...,
        description="兑换结果奖品ID"
    )
    materials: Optional[List[Dict[str, Any]]] = Field(
        default=[],
        sa_column=Column(SQLiteJSON),
        description="所需材料列表，JSON格式存储reward_id和quantity"
    )
    is_active: bool = Field(
        default=True,
        description="是否启用"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间"
    )

    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4'
    }


class RewardTransaction(BaseModel, table=True):
    model_config = {"arbitrary_types_allowed": True}
    """
    奖品流水记录模型（基于v3 API方案）

    记录所有奖品变动，包括获得、消耗、兑换等操作。
    支持事务组关联，用于追踪兑换操作的多个流水记录。

    字段设计（严格匹配v3文档）：
    - user_id: 用户ID
    - reward_id: 奖品ID
    - source_type: 来源类型（task_complete_top3 | redemption | manual）
    - source_id: 来源对象ID（任务ID或配方ID）
    - quantity: 数量，正数表示获得，负数表示消耗
    - transaction_group: 事务组ID，用于关联同一操作的多个记录
    """

    __tablename__ = "reward_transactions"

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="流水记录ID"
    )
    user_id: str = Field(
        ...,
        index=True,
        description="用户ID"
    )
    reward_id: str = Field(
        ...,
        index=True,
        description="奖品ID"
    )
    source_type: str = Field(
        ...,
        max_length=50,
        description="来源类型：top3_lottery | recipe_consume | recipe_produce"
    )
    source_id: Optional[str] = Field(
        default=None,
        index=True,
        description="来源对象ID，如任务ID、配方ID等"
    )
    quantity: int = Field(
        ...,
        description="数量，正数表示获得，负数表示消耗"
    )
    transaction_group: Optional[str] = Field(
        default=None,
        max_length=50,
        index=True,
        description="事务组ID，用于关联同一操作的多个记录"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )

    __table_args__ = (
        Index('idx_user_reward_time', 'user_id', 'created_at'),
        Index('idx_reward_transaction', 'reward_id'),
        Index('idx_source_transaction', 'source_type', 'source_id'),
        Index('idx_transaction_group', 'transaction_group'),
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4'
        }
    )


# 导出所有模型，保持向后兼容
from src.domains.points.models import PointsTransaction