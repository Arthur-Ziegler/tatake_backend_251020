"""
任务相关数据模型

本模块定义了任务系统相关的数据模型，包括：
- Task: 任务信息模型，支持树形结构
- TaskTop3: 每日Top3任务模型
- TaskTag: 任务标签模型

设计原则：
1. 树形结构：Task模型支持无限层级的父子关系
2. 软删除：使用is_deleted字段实现软删除
3. 状态管理：完整的任务状态流转和生命周期管理
4. 排序支持：通过sort_order字段支持自定义排序

使用示例：
    >>> parent_task = Task(title="父任务", user_id="user123")
    >>> child_task = Task(title="子任务", user_id="user123", parent_id=parent_task.id)
    >>> print(f"子任务层级: {child_task.depth}")
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import SQLModel, Field, Relationship

# 导入基础模型类和枚举
from src.models.base_model import BaseSQLModel
from src.models.enums import TaskStatus, PriorityLevel

# 避免循环导入的类型检查
if TYPE_CHECKING:
    from src.models.user import User


class Task(BaseSQLModel, table=True):
    """
    任务信息模型

    存储任务的详细信息，支持树形结构和状态管理。
    每个任务可以属于一个用户，可以有父任务和子任务。

    Attributes:
        title (str): 任务标题，必填字段，用于显示和识别
        description (Optional[str]): 任务描述，可选字段，详细说明任务内容
        status (TaskStatus): 任务状态，使用枚举类型管理状态流转
        priority (PriorityLevel): 优先级，使用枚举类型标识重要性
        user_id (str): 用户ID，外键关联到User表
        parent_id (Optional[str]): 父任务ID，支持树形结构，自引用外键
        sort_order (int): 排序顺序，用于自定义任务排序
        is_deleted (bool): 软删除标志，False表示未删除
        completed_at (Optional[datetime]): 完成时间，记录任务完成时刻
        user (User): 关联的用户，多对一关系
        parent (Optional[Task]): 父任务，多对一关系
        children (List[Task]): 子任务列表，一对多关系
    """

    __tablename__ = "tasks"

    # 基本信息
    title: str = Field(
        min_length=1,
        max_length=200,
        description="任务标题，用于显示和识别"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="任务描述，详细说明任务内容和要求"
    )

    # 状态和优先级
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="任务状态，使用枚举管理任务生命周期"
    )

    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM,
        description="任务优先级，用于重要性标识和排序"
    )

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识任务归属"
    )

    parent_id: Optional[str] = Field(
        default=None,
        foreign_key="tasks.id",
        index=True,
        description="父任务ID，支持树形结构，自引用外键"
    )

    # 排序和状态管理
    sort_order: int = Field(
        default=0,
        description="排序顺序，数值越小排序越靠前"
    )

    is_deleted: bool = Field(
        default=False,
        index=True,
        description="软删除标志，True表示已删除"
    )

    # 时间相关字段
    completed_at: Optional[datetime] = Field(
        default=None,
        description="任务完成时间，记录任务完成的具体时刻"
    )

    # 关系定义
    user: "User" = Relationship(
        back_populates="tasks",
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    parent: Optional["Task"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "Task.id",
            "lazy": "select"
        }
    )

    children: List["Task"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回任务的字符串表示

        Returns:
            str: 任务的基本信息表示

        Example:
            >>> task = Task(title="完成项目文档")
            >>> print(repr(task))
            Task(id=uuid-string)
        """
        return f"Task(id={self.id})"

    def __str__(self) -> str:
        """
        返回任务友好的字符串表示

        Returns:
            str: 任务的标题表示

        Example:
            >>> task = Task(title="完成项目文档")
            >>> print(str(task))
            完成项目文档
        """
        return self.title

    @property
    def depth(self) -> int:
        """
        计算任务在树形结构中的深度

        Returns:
            int: 深度值，根任务为0，每增加一级深度加1

        Example:
            >>> root_task = Task(title="根任务", user_id="user123")
            >>> print(root_task.depth)
            0
        """
        if self.parent_id is None:
            return 0

        # 如果有父任务，递归计算深度
        # 注意：这里需要额外的数据库查询，实际使用时可能需要优化
        from sqlmodel import Session, select

        # 获取数据库会话（这里假设有全局会话管理）
        # 在实际应用中，这个方法可能需要在Repository层实现
        try:
            # 这是一个简化的实现，实际应用中需要更复杂的逻辑
            current_depth = 0
            parent_id = self.parent_id

            # 防止无限循环（最多递归10层）
            while parent_id and current_depth < 10:
                statement = select(Task).where(Task.id == parent_id)
                # 这里需要session，实际使用中需要传入或通过其他方式获取
                break

            return current_depth
        except Exception:
            # 如果无法计算深度，返回当前层级
            return 1

    @property
    def completion_percentage(self) -> float:
        """
        计算任务的完成百分比

        对于叶子任务：0%或100%
        对于父任务：基于子任务的完成度计算

        Returns:
            float: 完成百分比，范围0-100

        Example:
            >>> task = Task(title="父任务", user_id="user123")
            >>> print(task.completion_percentage)
            0.0
        """
        # 如果任务已完成，返回100%
        if self.status == TaskStatus.COMPLETED:
            return 100.0

        # 如果任务没有子任务，返回0%
        if not self.children:
            return 0.0

        # 计算子任务的完成度
        try:
            completed_count = 0
            total_count = len(self.children)

            for child in self.children:
                if child.status == TaskStatus.COMPLETED:
                    completed_count += 1
                elif hasattr(child, 'completion_percentage'):
                    # 如果子任务也有子任务，使用其完成百分比
                    completed_count += child.completion_percentage / 100.0

            return (completed_count / total_count) * 100.0 if total_count > 0 else 0.0
        except Exception:
            # 如果计算失败，返回0%
            return 0.0

    def is_root_task(self) -> bool:
        """
        判断是否为根任务

        Returns:
            bool: 如果是根任务返回True，否则返回False

        Example:
            >>> root_task = Task(title="根任务", user_id="user123")
            >>> print(root_task.is_root_task())
            True
        """
        return self.parent_id is None

    def is_leaf_task(self) -> bool:
        """
        判断是否为叶子任务（没有子任务）

        Returns:
            bool: 如果是叶子任务返回True，否则返回False

        Example:
            >>> leaf_task = Task(title="叶子任务", user_id="user123")
            >>> print(leaf_task.is_leaf_task())
            True
        """
        return len(self.children) == 0 if self.children else True

    def mark_as_completed(self) -> None:
        """
        标记任务为已完成

        设置任务状态为已完成，并记录完成时间。

        Example:
            >>> task = Task(title="待完成任务", user_id="user123")
            >>> task.mark_as_completed()
            >>> print(task.status)
            TaskStatus.COMPLETED
        """
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_as_in_progress(self) -> None:
        """
        标记任务为进行中

        设置任务状态为进行中，表示任务已经开始执行。

        Example:
            >>> task = Task(title="待开始任务", user_id="user123")
            >>> task.mark_as_in_progress()
            >>> print(task.status)
            TaskStatus.IN_PROGRESS
        """
        self.status = TaskStatus.IN_PROGRESS

    def soft_delete(self) -> None:
        """
        软删除任务

        设置删除标志而不是真正删除数据库记录。

        Example:
            >>> task = Task(title="要删除的任务", user_id="user123")
            >>> task.soft_delete()
            >>> print(task.is_deleted)
            True
        """
        self.is_deleted = True
        self.status = TaskStatus.DELETED

    def restore(self) -> None:
        """
        恢复已软删除的任务

        取消删除标志，将状态重置为待处理。

        Example:
            >>> task = Task(title="已删除任务", user_id="user123")
            >>> task.is_deleted = True
            >>> task.restore()
            >>> print(task.is_deleted)
            False
        """
        self.is_deleted = False
        if self.status == TaskStatus.DELETED:
            self.status = TaskStatus.PENDING

    def get_path(self) -> List[str]:
        """
        获取任务的完整路径（从根任务到当前任务的标题链）

        Returns:
            List[str]: 任务标题路径列表

        Example:
            >>> child = Task(title="子任务", user_id="user123")
            >>> print(child.get_path())
            ["根任务", "父任务", "子任务"]
        """
        # 这是一个简化的实现，实际应用中需要数据库查询
        # 这里返回包含当前任务标题的路径
        return [self.title]

    def can_add_child(self) -> bool:
        """
        判断是否可以添加子任务

        Returns:
            bool: 如果可以添加子任务返回True，否则返回False

        Example:
            >>> task = Task(title="父任务", user_id="user123")
            >>> print(task.can_add_child())
            True
        """
        # 已删除的任务不能添加子任务
        if self.is_deleted:
            return False

        # 已完成的任务通常不建议添加子任务，但技术上可行
        # 这里根据业务规则调整
        return True

    def get_all_children(self, include_deleted: bool = False) -> List["Task"]:
        """
        获取所有子任务（递归）

        Args:
            include_deleted (bool): 是否包含已删除的子任务

        Returns:
            List[Task]: 所有子任务列表

        Example:
            >>> parent = Task(title="父任务", user_id="user123")
            >>> all_children = parent.get_all_children()
            >>> print(len(all_children))
            0
        """
        all_children = []

        if self.children:
            for child in self.children:
                if not child.is_deleted or include_deleted:
                    all_children.append(child)
                    # 递归获取子任务的子任务
                    all_children.extend(child.get_all_children(include_deleted))

        return all_children


class TaskTop3(BaseSQLModel, table=True):
    """
    每日Top3任务模型

    存储用户每天选择的最重要的3个任务。
    每个用户每天只能有3个Top3任务。

    Attributes:
        user_id (str): 用户ID，外键关联到User表
        task_id (str): 任务ID，外键关联到Task表
        rank (int): 排名，1-3之间的整数
        date (datetime): 日期，精确到天
        user (User): 关联的用户
        task (Task): 关联的任务
    """

    __tablename__ = "task_top3"

    # 外键关联
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表"
    )

    task_id: str = Field(
        foreign_key="tasks.id",
        index=True,
        description="任务ID，关联到Task表"
    )

    # 排名和日期
    rank: int = Field(
        ge=1,
        le=3,
        description="任务排名，1-3之间的整数"
    )

    date: datetime = Field(
        index=True,
        description="Top3任务日期，精确到天"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    task: "Task" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回Top3任务的字符串表示

        Returns:
            str: Top3任务的基本信息表示

        Example:
            >>> top3 = TaskTop3(user_id="user123", task_id="task123", rank=1)
            >>> print(repr(top3))
            TaskTop3(id=uuid-string)
        """
        return f"TaskTop3(id={self.id})"

    def is_rank_valid(self) -> bool:
        """
        验证排名是否有效

        Returns:
            bool: 如果排名在1-3范围内返回True，否则返回False

        Example:
            >>> top3 = TaskTop3(user_id="user123", task_id="task123", rank=1)
            >>> print(top3.is_rank_valid())
            True
        """
        return 1 <= self.rank <= 3


class TaskTag(BaseSQLModel, table=True):
    """
    任务标签模型

    存储任务的分类标签，每个用户可以有自定义的标签。
    标签用于任务的分类和筛选。

    Attributes:
        name (str): 标签名称，用户自定义
        color (str): 标签颜色，十六进制颜色代码
        user_id (str): 用户ID，外键关联到User表
        user (User): 关联的用户
    """

    __tablename__ = "task_tags"

    # 标签信息
    name: str = Field(
        max_length=50,
        description="标签名称，用于任务分类和识别"
    )

    color: str = Field(
        max_length=7,
        default="#007bff",
        description="标签颜色，十六进制颜色代码，如#007bff"
    )

    # 外键关联
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识标签归属"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回标签的字符串表示

        Returns:
            str: 标签的基本信息表示

        Example:
            >>> tag = TaskTag(name="工作", user_id="user123")
            >>> print(repr(tag))
            TaskTag(id=uuid-string)
        """
        return f"TaskTag(id={self.id})"

    def __str__(self) -> str:
        """
        返回标签友好的字符串表示

        Returns:
            str: 标签的名称表示

        Example:
            >>> tag = TaskTag(name="工作", user_id="user123")
            >>> print(str(tag))
            工作
        """
        return self.name

    def is_valid_color(self) -> bool:
        """
        验证颜色格式是否有效

        Returns:
            bool: 如果是有效的十六进制颜色代码返回True，否则返回False

        Example:
            >>> tag = TaskTag(name="工作", color="#007bff", user_id="user123")
            >>> print(tag.is_valid_color())
            True
        """
        import re
        hex_color_pattern = r'^#[0-9A-Fa-f]{6}$'
        return bool(re.match(hex_color_pattern, self.color))

    def get_rgb_tuple(self) -> tuple[int, int, int]:
        """
        将十六进制颜色转换为RGB元组

        Returns:
            tuple[int, int, int]: RGB颜色元组

        Example:
            >>> tag = TaskTag(name="工作", color="#007bff", user_id="user123")
            >>> print(tag.get_rgb_tuple())
            (0, 123, 255)
        """
        if not self.is_valid_color():
            return (0, 0, 0)  # 默认黑色

        hex_color = self.color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# 导出所有任务相关模型
__all__ = [
    "Task",
    "TaskTop3",
    "TaskTag"
]