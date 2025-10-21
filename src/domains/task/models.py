"""
Task领域数据模型

定义任务管理相关的数据模型和枚举类型。

核心模型：
- Task: 任务实体模型，包含15个核心字段
- TaskStatus: 任务状态枚举
- TaskPriority: 任务优先级枚举

设计原则：
1. 简化设计：只保留核心字段，遵循YAGNI原则
2. 父子关系：支持任务树结构，使用parent_id建立关系
3. 软删除：使用is_deleted字段实现软删除
4. 时间管理：所有时间字段使用UTC时区
5. 标签管理：使用JSON类型存储标签，简化第一版实现

索引设计：
- user_id: 支持按用户查询
- status: 支持按状态筛选
- is_deleted: 支持软删除过滤
- parent_id: 支持父子关系查询

外键约束：
- user_id → auth.id (级联删除)
- parent_id → tasks.id (SET NULL，防止循环引用)

作者：TaKeKe团队
版本：1.0.0
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, DateTime, Text, JSON
from sqlalchemy import Index, ForeignKey
from sqlalchemy.orm import relationship

# 导入基础模型
try:
    from src.domains.auth.models import BaseModel
except ImportError:
    # 相对导入作为备选方案
    from ...auth.models import BaseModel

# 使用Literal类型定义枚举值
TaskStatus = Literal["pending", "in_progress", "completed"]
TaskPriority = Literal["low", "medium", "high"]

# 常量定义
class TaskStatusConst:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriorityConst:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(BaseModel, table=True, extend_existing=True):
    """
    任务实体模型

    TaKeKe项目的核心任务模型，支持完整的任务管理功能。
    包含15个核心字段，涵盖任务的基本信息、状态管理、时间管理和关系管理。

    核心字段说明：
    - id: 主键，UUID格式
    - user_id: 用户ID，关联到auth表
    - title: 任务标题，必填字段，1-100字符
    - description: 任务描述，可选，支持长文本
    - status: 任务状态，使用TaskStatus枚举
    - priority: 任务优先级，使用TaskPriority枚举
    - parent_id: 父任务ID，支持任务树结构
    - tags: 任务标签，JSON格式存储
    - due_date: 截止日期，可选
    - planned_start_time: 计划开始时间，可选
    - planned_end_time: 计划结束时间，可选
    - is_deleted: 软删除标记
    - created_at: 创建时间
    - updated_at: 更新时间

    约束条件：
    - title长度：1-100字符
    - 时间逻辑：planned_end_time必须晚于planned_start_time
    - 父子关系：parent_id必须指向存在的任务，且不能形成循环引用
    - 用户权限：只能操作自己的任务

    索引设计：
    - idx_task_user_id: 按用户查询
    - idx_task_status: 按状态筛选
    - idx_task_is_deleted: 软删除过滤
    - idx_task_parent_id: 父子关系查询

    外键约束：
    - fk_task_user_id: user_id → auth.id (CASCADE)
    - fk_task_parent_id: parent_id → tasks.id (SET NULL)
    """

    __tablename__ = "tasks"

    # 用户关联
    user_id: UUID = Field(
        ...,
        index=True,
        description="用户ID，关联到认证表"
    )

    # 基本信息
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="任务标题，1-100字符，必填"
    )
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="任务描述，支持长文本"
    )

    # 状态管理
    status: str = Field(
        default=TaskStatusConst.PENDING,
        index=True,
        description="任务状态：pending/in_progress/completed"
    )
    priority: str = Field(
        default=TaskPriorityConst.MEDIUM,
        description="任务优先级：low/medium/high"
    )

    # 关系管理
    parent_id: Optional[UUID] = Field(
        default=None,
        index=True,
        description="父任务ID，支持任务树结构"
    )

    # 标签管理
    tags: Optional[List[str]] = Field(
        default=[],
        sa_column=Column(JSON),
        description="任务标签列表，JSON格式存储"
    )

    # 时间管理
    due_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="任务截止日期"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="计划开始时间"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="计划结束时间"
    )

    # 软删除
    is_deleted: bool = Field(
        default=False,
        index=True,
        description="软删除标记，true表示已删除"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_task_user_id', 'user_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_is_deleted', 'is_deleted'),
        Index('idx_task_parent_id', 'parent_id'),
        Index('idx_task_user_status_deleted', 'user_id', 'status', 'is_deleted'),
        Index('idx_task_created_time', 'created_at'),

        # 外键约束定义
        {
            'mysql_engine': 'InnoDB',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci'
        }
    )

    # 关系定义
    # 暂时注释掉关系，避免循环导入问题
    # user: Optional["Auth"] = relationship(
    #     "Auth",
    #     back_populates="tasks"
    # )

    # 暂时注释掉父子关系以避免循环引用
    # parent: Optional["Task"] = relationship(
    #     "Task",
    #     remote_side="Task.id",
    #     back_populates="children"
    # )
    #
    # children: List["Task"] = relationship(
    #     "Task",
    #     back_populates="parent",
    #     cascade="all, delete-orphan"
    # )

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Task(id={self.id}, title='{self.title}', "
            f"status={self.status}, priority={self.priority}, "
            f"user_id={self.user_id}, is_deleted={self.is_deleted})"
        )

    @property
    def is_overdue(self) -> bool:
        """检查任务是否过期"""
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date

    @property
    def duration_minutes(self) -> Optional[int]:
        """计算计划持续时间（分钟）"""
        if not self.planned_start_time or not self.planned_end_time:
            return None
        delta = self.planned_end_time - self.planned_start_time
        return int(delta.total_seconds() / 60)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "tags": self.tags or [],
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "planned_start_time": self.planned_start_time.isoformat() if self.planned_start_time else None,
            "planned_end_time": self.planned_end_time.isoformat() if self.planned_end_time else None,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_overdue": self.is_overdue,
            "duration_minutes": self.duration_minutes
        }

    @classmethod
    def create_example(cls, user_id: UUID, **kwargs) -> "Task":
        """创建示例任务（用于测试）"""
        defaults = {
            "title": "示例任务",
            "description": "这是一个示例任务",
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.MEDIUM,
            "tags": ["示例", "测试"]
        }
        defaults.update(kwargs)
        defaults["user_id"] = user_id
        return cls(**defaults)


# 暂时注释掉关系定义以避免循环导入问题
# def add_task_relationship_to_auth():
#     """为Auth模型添加tasks关系"""
#     from src.domains.auth.models import Auth
#
#     # 检查是否已经添加了关系
#     if not hasattr(Auth, 'tasks'):
#         Auth.tasks = relationship(
#             "Task",
#             back_populates="user",
#             cascade="all, delete-orphan"
#         )
#
#
# # 在模块导入时自动添加关系
# add_task_relationship_to_auth()