"""
Task领域数据模型

定义任务管理相关的数据模型和枚举类型，支持无限层级任务结构。

核心模型：
- Task: 任务实体模型，包含20个核心字段，支持完整的树结构管理
- TaskStatus: 任务状态枚举
- TaskPriority: 任务优先级枚举

设计原则：
1. 简化设计：保留核心字段，删除番茄钟和复杂树结构字段
2. 基础层级：支持基本的parent_id层级关系
3. 智能完成度：基于叶子节点计算任务完成百分比
4. 软删除：使用is_deleted字段实现软删除
5. 时间管理：所有时间字段使用UTC时区
6. 标签管理：使用JSON类型存储标签，简化第一版实现

索引设计：
- user_id: 支持按用户查询
- status: 支持按状态筛选
- is_deleted: 支持软删除过滤
- parent_id: 支持基本父子关系查询
- completion_percentage: 支持完成度查询

外键约束：
- user_id → auth.id (级联删除)
- parent_id → tasks.id (SET NULL，防止循环引用)

作者：TaTakeKe团队
版本：1.1.0（增强树结构支持）
"""

from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, DateTime, Text, JSON, Date, String
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


class Task(SQLModel, table=True):
    """
    任务实体模型

    TaKeKe项目的核心任务模型，支持完整的任务管理和无限层级树结构功能。
    包含18个核心字段，涵盖任务的基本信息、状态管理、时间管理和层级管理。

    核心字段说明：
    - 基础信息：id, user_id, title, description
    - 状态管理：status, priority, is_deleted
    - 层级结构：parent_id, completion_percentage
    - 时间管理：due_date, planned_start_time, planned_end_time
    - 其他：tags, created_at, updated_at

    层级功能：
    - parent_id: 父任务ID，支持基本的父子关系
    - completion_percentage: 完成百分比，基于叶子节点数量自动计算

    约束条件：
    - title长度：1-100字符
    - completion_percentage范围：0.0-100.0
    - level必须为非负整数
    - 番茄钟数量必须为非负整数
    - 时间逻辑：planned_end_time必须晚于planned_start_time
    - 父子关系：parent_id必须指向存在的任务，且不能形成循环引用

    索引设计：
    - idx_task_user_id: 按用户查询
    - idx_task_status: 按状态筛选
    - idx_task_is_deleted: 软删除过滤
    - idx_task_parent_id: 父子关系查询
    - idx_task_level: 按层级查询
    - idx_task_path: 路径前缀查询
    - idx_task_completion: 完成度查询
    - idx_task_user_level: 用户按层级查询
    - idx_task_user_status_deleted: 用户状态删除组合查询
    - idx_task_created_time: 创建时间查询

    外键约束：
    - fk_task_user_id: user_id → auth.id (CASCADE)
    - fk_task_parent_id: parent_id → tasks.id (SET NULL)
    """

    __tablename__ = "tasks"

    # === 基础字段 ===
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        primary_key=True,
        description="主键ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间"
    )

    # === 用户关联字段 ===
    user_id: str = Field(
        ...,
        index=True,
        description="用户ID，关联到认证表"
    )

    # === 基本信息 ===
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

    # === 层级结构 ===
    parent_id: Optional[str] = Field(
        default=None,
        index=True,
        description="父任务ID，支持任务树结构"
    )

    # === 状态管理 ===
    status: str = Field(
        default=TaskStatusConst.PENDING,
        index=True,
        description="任务状态：pending/in_progress/completed"
    )
    priority: str = Field(
        default=TaskPriorityConst.MEDIUM,
        description="任务优先级：low/medium/high"
    )
    is_deleted: bool = Field(
        default=False,
        index=True,
        description="软删除标记，true表示已删除"
    )

    # === 简化字段 ===
    completion_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="任务完成百分比，基于叶子节点数量计算，范围0.0-100.0"
    )

    # === 防刷机制 ===
    last_claimed_date: Optional[date] = Field(
        default=None,
        sa_column=Column(Date),
        description="最后领奖日期，用于防刷机制，YYYY-MM-DD格式"
    )

    # === 标签管理 ===
    tags: Optional[List[str]] = Field(
        default=[],
        sa_column=Column(JSON),
        description="任务标签列表，JSON格式存储"
    )

    # === 服务关联（占位字段，后续AI匹配） ===
    service_ids: Optional[List[str]] = Field(
        default=[],
        sa_column=Column(JSON),
        description="关联服务ID列表，JSON格式存储。占位字段，后续通过AI匹配任务与服务。示例: ['service-001', 'service-002']"
    )

    # === 时间管理 ===
    due_date: Optional[datetime] = Field(
        default=None,
        description="任务截止日期"
    )
    planned_start_time: Optional[datetime] = Field(
        default=None,
        description="计划开始时间"
    )
    planned_end_time: Optional[datetime] = Field(
        default=None,
        description="计划结束时间"
    )

    # === 数据库索引和约束 ===
    __table_args__ = (
        # 根据v3方案，简化索引策略，仅保留主键索引
        # 性能优化问题后续解决，当前优先保证功能正确性

        # 数据库配置
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

    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，包含所有字段信息

        Returns:
            Dict[str, Any]: 包含所有任务字段的字典，包括树结构相关字段
        """
        return {
            # 基础字段
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "tags": self.tags or [],
            "service_ids": self.service_ids or [],

            # 状态字段
            "status": self.status,
            "priority": self.priority,
            "is_deleted": self.is_deleted,

            # 简化字段
            "completion_percentage": self.completion_percentage,

            # 时间字段
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "planned_start_time": self.planned_start_time.isoformat() if self.planned_start_time else None,
            "planned_end_time": self.planned_end_time.isoformat() if self.planned_end_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

  
    def is_leaf_node(self) -> bool:
        """
        判断是否为叶子节点（没有子任务的节点）

        Returns:
            bool: True表示是叶子节点
        """
        # 这里需要通过数据库查询来判断，模型方法只提供接口
        # 实际实现需要在Repository层
        return False  # 默认返回False，实际使用时查询数据库

    def is_root_node(self) -> bool:
        """
        判断是否为根节点

        Returns:
            bool: True表示是根节点
        """
        return self.parent_id is None

    
    @classmethod
    def create_example(cls, user_id: UUID, **kwargs) -> "Task":
        """创建示例任务（用于测试）"""
        defaults = {
            "title": "示例任务",
            "description": "这是一个示例任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM,
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