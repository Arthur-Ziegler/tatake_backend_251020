"""
异步任务Repository实现

提供任务相关的异步数据访问层操作，封装任务业务逻辑查询。
继承自AsyncBaseRepository，专注于任务特有的业务场景。

功能特性：
1. 异步任务查询（按用户、状态、优先级、层级查询）
2. 异步任务状态管理（完成、重新打开、取消、软删除）
3. 异步任务层级管理（父子任务关系处理）
4. 异步任务统计和分析（完成率、优先级分布等）
5. 异步业务逻辑封装（级联操作、状态验证等）

设计原则：
1. 单一责任：专注于任务相关的数据访问
2. 异步优先：所有数据库操作都是异步的
3. 查询封装：复杂业务查询封装在Repository方法中
4. 异常统一：使用统一的异常处理机制
5. 类型安全：强类型参数和返回值
6. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建异步任务Repository
    >>> task_repo = AsyncTaskRepository(async_session)
    >>>
    >>> # 异步查找用户的所有任务
    >>> tasks = await task_repo.find_by_user("user123")
    >>>
    >>> # 异步完成任务
    >>> completed_task = await task_repo.complete_task("task123")
    >>>
    >>> # 异步查找待完成的子任务
    >>> subtasks = await task_repo.find_by_parent("parent_task123")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

# 导入异步基础Repository和异常类
from src.repositories.async_base import (
    AsyncBaseRepository,
    AsyncRepositoryError,
    AsyncRepositoryValidationError,
    AsyncRepositoryNotFoundError
)
from src.models.task import Task
from src.models.enums import TaskStatus, PriorityLevel


class AsyncTaskRepository(AsyncBaseRepository[Task]):
    """
    异步任务Repository类

    提供任务相关的异步数据库操作，封装任务业务逻辑查询。
    继承自AsyncBaseRepository，专注于任务特有的业务场景。

    Attributes:
        session: SQLAlchemy异步会话对象
        model: Task模型类
    """

    def __init__(self, session: AsyncSession):
        """
        初始化异步任务Repository

        Args:
            session: SQLAlchemy异步会话对象
        """
        super().__init__(session, Task)

    async def find_by_user(
        self,
        user_id: str,
        status: Optional[TaskStatus] = None,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        查找用户的所有任务

        Args:
            user_id: 用户ID
            status: 任务状态过滤
            include_deleted: 是否包含已删除的任务

        Returns:
            任务列表

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 构建查询
            statement = select(Task).where(Task.user_id == user_id)

            # 状态过滤
            if status:
                statement = statement.where(Task.status == status)

            # 软删除过滤
            if not include_deleted:
                statement = statement.where(Task.deleted_at.is_(None))

            # 按创建时间倒序排列
            statement = statement.order_by(desc(Task.created_at))

            # 执行查询
            result = await self.session.exec(statement)
            tasks = list(result.all())

            return tasks

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询用户任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询用户任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def find_by_parent(self, parent_id: str) -> List[Task]:
        """
        查找指定任务的子任务

        Args:
            parent_id: 父任务ID

        Returns:
            子任务列表

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not parent_id:
                raise AsyncRepositoryValidationError("父任务ID不能为空")

            # 构建查询
            statement = select(Task).where(
                and_(
                    Task.parent_id == parent_id,
                    Task.deleted_at.is_(None)
                )
            ).order_by(Task.priority.desc(), Task.created_at.asc())

            # 执行查询
            result = await self.session.exec(statement)
            tasks = list(result.all())

            return tasks

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询子任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询子任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def complete_task(self, task_id: str) -> Optional[Task]:
        """
        完成任务

        Args:
            task_id: 任务ID

        Returns:
            完成后的任务对象，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id:
                raise AsyncRepositoryValidationError("任务ID不能为空")

            # 查找任务
            task = await self.get_by_id(task_id)
            if not task:
                return None

            if task.deleted_at:
                raise AsyncRepositoryValidationError("已删除的任务无法完成")

            if task.status == TaskStatus.COMPLETED:
                return task  # 已经是完成状态

            # 更新任务状态
            now = datetime.now(timezone.utc)
            update_data = {
                "status": TaskStatus.COMPLETED,
                "completed_at": now,
                "updated_at": now
            }

            return await self.update(task_id, update_data)

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"完成任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"完成任务时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Optional[Task]:
        """
        取消任务

        Args:
            task_id: 任务ID
            reason: 取消原因

        Returns:
            取消后的任务对象，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id:
                raise AsyncRepositoryValidationError("任务ID不能为空")

            # 查找任务
            task = await self.get_by_id(task_id)
            if not task:
                return None

            if task.deleted_at:
                raise AsyncRepositoryValidationError("已删除的任务无法取消")

            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return task  # 已经是终态

            # 更新任务状态
            now = datetime.now(timezone.utc)
            update_data = {
                "status": TaskStatus.CANCELLED,
                "cancelled_at": now,
                "cancel_reason": reason,
                "updated_at": now
            }

            return await self.update(task_id, update_data)

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"取消任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"取消任务时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def soft_delete_task(self, task_id: str) -> bool:
        """
        软删除任务

        Args:
            task_id: 任务ID

        Returns:
            删除成功返回True，任务不存在返回False

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id:
                raise AsyncRepositoryValidationError("任务ID不能为空")

            # 查找任务
            task = await self.get_by_id(task_id)
            if not task or task.deleted_at:
                return False

            # 软删除
            now = datetime.now(timezone.utc)
            update_data = {
                "deleted_at": now,
                "updated_at": now
            }

            await self.update(task_id, update_data)
            return True

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"软删除任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"软删除任务时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def get_task_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户任务统计信息

        Args:
            user_id: 用户ID

        Returns:
            包含统计信息的字典

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 基础统计查询
            base_filter = and_(
                Task.user_id == user_id,
                Task.deleted_at.is_(None)
            )

            # 总任务数
            total_result = await self.session.exec(
                select(func.count()).select_from(Task).where(base_filter)
            )
            total_count = total_result.scalar() or 0

            # 按状态统计
            status_result = await self.session.exec(
                select(Task.status, func.count()).select_from(Task)
                .where(base_filter).group_by(Task.status)
            )
            status_counts = dict(status_result.all())

            # 按优先级统计
            priority_result = await self.session.exec(
                select(Task.priority, func.count()).select_from(Task)
                .where(base_filter).group_by(Task.priority)
            )
            priority_counts = dict(priority_result.all())

            # 今日完成的任务数
            today = datetime.now(timezone.utc).date()
            today_completed_result = await self.session.exec(
                select(func.count()).select_from(Task).where(
                    and_(
                        base_filter,
                        Task.status == TaskStatus.COMPLETED,
                        func.date(Task.completed_at) == today
                    )
                )
            )
            today_completed = today_completed_result.scalar() or 0

            # 本周完成的任务数
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_completed_result = await self.session.exec(
                select(func.count()).select_from(Task).where(
                    and_(
                        base_filter,
                        Task.status == TaskStatus.COMPLETED,
                        Task.completed_at >= week_ago
                    )
                )
            )
            week_completed = week_completed_result.scalar() or 0

            return {
                "total": total_count,
                "by_status": status_counts,
                "by_priority": priority_counts,
                "today_completed": today_completed,
                "week_completed": week_completed,
                "completion_rate": (
                    (status_counts.get(TaskStatus.COMPLETED, 0) / total_count * 100)
                    if total_count > 0 else 0
                )
            }

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取任务统计失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取任务统计时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def __repr__(self) -> str:
        """
        返回Repository的字符串表示

        Returns:
            Repository的描述信息
        """
        return f"{self.__class__.__name__}(model={self.model_name})"


# 导出相关类
__all__ = [
    "AsyncTaskRepository"
]