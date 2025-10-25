"""
任务领域模型 - PostgreSQL Schema分离版本

基于PostgreSQL Schema分离的任务模型设计。
每个模型都关联到task_domain schema，支持多租户。

设计特点：
1. Schema绑定：所有表都属于task_domain schema
2. 多租户支持：通过schema_translate_map动态切换
3. 类型安全：充分利用SQLModel和Pydantic类型系统
4. 索引优化：针对schema分离场景的索引策略

作者：TaKeKe团队
版本：v2.0（Schema分离版）
"""

from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, DateTime, Text, JSON, Date, String
from sqlalchemy import Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData

# 导入Schema数据库管理器
from src.core.schema_database import db_manager

# 定义Schema特定的MetaData
task_metadata = MetaData(schema="task_domain")

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
    任务实体模型 - Schema分离版本

    表结构：task_domain.tasks
    支持多租户：通过schema_translate_map动态映射到租户schema
    """

    __tablename__ = "tasks"
    __table_args__ = (
        # Schema特定配置
        {"schema": "task_domain"},
        # 索引配置（在Schema内唯一）
        Index('idx_task_user_id', 'user_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_is_deleted', 'is_deleted'),
        Index('idx_task_parent_id', 'parent_id'),
        Index('idx_task_completion', 'completion_percentage'),
        Index('idx_task_user_status_deleted', 'user_id', 'status', 'is_deleted'),
        Index('idx_task_last_claimed', 'last_claimed_date'),
        # PostgreSQL优化配置
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )

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

    # === 完成度管理 ===
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
        description="关联服务ID列表，JSON格式存储。占位字段，后续通过AI匹配任务与服务。"
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

            # 完成度字段
            "completion_percentage": self.completion_percentage,

            # 防刷字段
            "last_claimed_date": self.last_claimed_date.isoformat() if self.last_claimed_date else None,

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
        """
        # 这里需要通过数据库查询来判断，模型方法只提供接口
        return False  # 默认返回False，实际使用时查询数据库

    def is_root_node(self) -> bool:
        """
        判断是否为根节点
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
        defaults["user_id"] = str(user_id)
        return cls(**defaults)


# Schema特定的查询构建器
class TaskQueryBuilder:
    """任务查询构建器 - Schema版本"""

    def __init__(self, domain: str = "task", tenant_id: Optional[str] = None):
        self.domain = domain
        self.tenant_id = tenant_id
        self.session = db_manager.get_schema_session(domain, tenant_id)

    def get_user_tasks(self, user_id: str, include_deleted: bool = False) -> List[Task]:
        """获取用户的所有任务"""
        query = self.session.query(Task).where(Task.user_id == user_id)

        if not include_deleted:
            query = query.where(Task.is_deleted == False)

        return query.all()

    def get_tasks_by_status(self, user_id: str, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return self.session.query(Task).where(
            Task.user_id == user_id,
            Task.status == status,
            Task.is_deleted == False
        ).all()

    def get_parent_tasks(self, user_id: str) -> List[Task]:
        """获取父任务（没有parent_id的任务）"""
        return self.session.query(Task).where(
            Task.user_id == user_id,
            Task.parent_id.is_(None),
            Task.is_deleted == False
        ).all()

    def get_child_tasks(self, parent_id: str) -> List[Task]:
        """获取子任务"""
        return self.session.query(Task).where(
            Task.parent_id == parent_id,
            Task.is_deleted == False
        ).all()

    def search_tasks_by_title(self, user_id: str, keyword: str) -> List[Task]:
        """按标题搜索任务"""
        return self.session.query(Task).where(
            Task.user_id == user_id,
            Task.title.ilike(f"%{keyword}%"),
            Task.is_deleted == False
        ).all()

    def get_tasks_due_soon(self, user_id: str, days: int = 7) -> List[Task]:
        """获取即将到期的任务"""
        from datetime import timedelta

        due_date_limit = datetime.now(timezone.utc) + timedelta(days=days)
        return self.session.query(Task).where(
            Task.user_id == user_id,
            Task.due_date <= due_date_limit,
            Task.due_date >= datetime.now(timezone.utc),
            Task.is_deleted == False
        ).all()


# Schema迁移辅助类
class TaskSchemaMigration:
    """任务Schema迁移辅助类"""

    @staticmethod
    def create_tables(drop_existing: bool = False):
        """创建任务领域的表"""
        from src.core.schema_database import db_manager

        with db_manager.main_engine.connect() as conn:
            if drop_existing:
                Task.metadata.drop_all(conn)

            Task.metadata.create_all(conn)
            conn.commit()

    @staticmethod
    def verify_schema():
        """验证Schema是否正确创建"""
        from src.core.schema_database import db_manager

        schema_info = db_manager.inspect_schema("task")
        return schema_info

    @staticmethod
    def seed_sample_data(user_id: str):
        """插入示例数据"""
        from src.core.schema_database import domain_session

        with domain_session("task") as session:
            # 创建示例任务
            tasks = [
                Task(
                    user_id=user_id,
                    title="完成项目设计文档",
                    description="编写详细的项目设计文档，包括架构设计、API设计等",
                    priority=TaskPriorityConst.HIGH,
                    tags=["文档", "设计", "重要"]
                ),
                Task(
                    user_id=user_id,
                    title="实现用户认证功能",
                    description="实现基于微信OpenID的用户认证系统",
                    priority=TaskPriorityConst.HIGH,
                    tags=["开发", "认证", "微信"]
                ),
                Task(
                    user_id=user_id,
                    title="编写单元测试",
                    description="为核心业务逻辑编写单元测试用例",
                    priority=TaskPriorityConst.MEDIUM,
                    tags=["测试", "质量"]
                )
            ]

            for task in tasks:
                session.add(task)

            session.commit()


# 导出模型和工具类
__all__ = [
    "Task",
    "TaskQueryBuilder",
    "TaskSchemaMigration",
    "TaskStatus",
    "TaskPriority",
    "TaskStatusConst",
    "TaskPriorityConst"
]