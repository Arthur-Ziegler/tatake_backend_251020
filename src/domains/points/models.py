"""
Points领域数据模型

定义积分相关的数据模型，支持纯SQL聚合查询的积分计算功能。

核心模型：
- PointsTransaction: 积分流水记录模型
- 支持各种source_type：task_complete, task_complete_top3, top3_cost, lottery_points, recharge

设计原则：
1. 简单设计：只包含必要的字段，避免过度设计
2. 纯SQL聚合：余额和统计通过纯SQL计算
3. UTC时间：统一使用UTC时区存储时间
4. 类型安全：使用SQLModel类型系统确保类型安全

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel

# 导入基础模型
from src.domains.auth.models import BaseModel


class PointsTransaction(BaseModel, table=True):
    """
    积分流水记录模型

    记录用户积分的变动历史，支持纯SQL聚合计算余额和统计。
    所有积分变动都通过此表记录，实现完整的积分追踪功能。
    """

    __tablename__ = "points_transactions"

    # 核心字段
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="交易ID，主键"
    )

    user_id: str = Field(
        ...,
        index=True,
        description="用户ID，关联到认证表"
    )

    amount: int = Field(
        ...,
        description="积分数量，正数表示获得，负数表示消费"
    )

    source_type: str = Field(
        ...,
        index=True,
        description="积分来源类型：task_complete | task_complete_top3 | top3_cost | lottery_points | recharge | welcome_gift"
    )

    source_id: Optional[str] = Field(
        default=None,
        description="来源对象的ID，如任务ID、配方ID等"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间，UTC时区"
    )

    # 数据库配置
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }


# 数据库索引配置
__table_index_args__ = [
    # 按用户ID优化余额查询
    ("idx_points_user_id", "user_id"),

    # 按来源类型和日期优化统计查询
    ("idx_points_source_date", "source_type", "created_at"),

    # 按来源对象查询优化
    ("idx_points_source_id", "source_id"),
]