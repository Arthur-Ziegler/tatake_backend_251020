"""
任务Repository实现

提供任务相关的数据访问层操作，封装任务业务逻辑查询。
继承自BaseRepository，专注于任务特有的业务场景。

功能特性：
1. 任务查询（按用户、状态、优先级、层级查询）
2. 任务状态管理（完成、重新打开、取消、软删除）
3. 任务层级管理（父子任务关系处理）
4. 任务统计和分析（完成率、优先级分布等）
5. 业务逻辑封装（级联操作、状态验证等）

设计原则：
1. 单一责任：专注于任务相关的数据访问
2. 查询封装：复杂业务查询封装在Repository方法中
3. 异常统一：使用统一的异常处理机制
4. 类型安全：强类型参数和返回值
5. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建任务Repository
    >>> task_repo = TaskRepository(session)
    >>>
    >>> # 查找用户的所有任务
    >>> tasks = task_repo.find_by_user("user123")
    >>>
    >>> # 完成任务
    >>> completed_task = task_repo.complete_task("task123")
    >>>
    >>> # 查找待完成的子任务
    >>> subtasks = task_repo.find_by_parent("parent_task123")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlmodel import Session, select, and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

# 导入基础Repository和异常类
from src.repositories.base import BaseRepository, RepositoryError, RepositoryValidationError, RepositoryNotFoundError
from src.models.task import Task
from src.models.enums import TaskStatus, PriorityLevel


class TaskRepository(BaseRepository[Task]):
    """
    任务Repository类

    提供任务相关的数据库操作，封装任务业务逻辑查询。
    继承自BaseRepository，专注于任务特有的业务场景。

    Attributes:
        session: SQLAlchemy会话对象
        model: Task模型类
    """

    def __init__(self, session: Session):
        """
        初始化TaskRepository

        Args:
            session: SQLAlchemy会话对象
        """
        super().__init__(session, Task)

    def find_by_user(self, user_id: str) -> List[Task]:
        """
        根据用户ID查找任务

        Args:
            user_id: 用户ID

        Returns:
            List[Task]: 用户的任务列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> tasks = task_repo.find_by_user("user123")
            >>> print(f"用户共有 {len(tasks)} 个任务")
            "用户共有 5 个任务"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            # 构建查询：查找用户的所有未删除任务，按排序顺序和创建时间排序
            statement = select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.is_deleted == False
                )
            ).order_by(Task.sort_order.asc(), Task.created_at.desc())

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据用户ID查找任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据用户ID查找任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态查找任务

        Args:
            status: 任务状态

        Returns:
            List[Task]: 指定状态的任务列表

        Raises:
            RepositoryValidationError: 状态参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> pending_tasks = task_repo.find_by_status(TaskStatus.PENDING)
            >>> print(f"有待完成任务 {len(pending_tasks)} 个")
            "有待完成任务 3 个"
        """
        try:
            # 参数验证
            if not isinstance(status, TaskStatus):
                raise RepositoryValidationError("状态参数必须是TaskStatus枚举类型")

            # 构建查询：查找指定状态的未删除任务
            statement = select(Task).where(
                and_(
                    Task.status == status,
                    Task.is_deleted == False
                )
            ).order_by(Task.priority.desc(), Task.created_at.desc())

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据状态查找任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据状态查找任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_priority(self, priority: PriorityLevel) -> List[Task]:
        """
        根据优先级查找任务

        Args:
            priority: 任务优先级

        Returns:
            List[Task]: 指定优先级的任务列表

        Raises:
            RepositoryValidationError: 优先级参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> high_tasks = task_repo.find_by_priority(PriorityLevel.HIGH)
            >>> print(f"高优先级任务 {len(high_tasks)} 个")
            "高优先级任务 2 个"
        """
        try:
            # 参数验证
            if not isinstance(priority, PriorityLevel):
                raise RepositoryValidationError("优先级参数必须是PriorityLevel枚举类型")

            # 构建查询：查找指定优先级的未删除任务
            statement = select(Task).where(
                and_(
                    Task.priority == priority,
                    Task.is_deleted == False
                )
            ).order_by(Task.created_at.desc())

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据优先级查找任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据优先级查找任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_parent(self, parent_id: str) -> List[Task]:
        """
        根据父任务ID查找子任务

        Args:
            parent_id: 父任务ID

        Returns:
            List[Task]: 子任务列表

        Raises:
            RepositoryValidationError: 父任务ID参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> subtasks = task_repo.find_by_parent("parent123")
            >>> print(f"父任务有 {len(subtasks)} 个子任务")
            "父任务有 3 个子任务"
        """
        try:
            # 参数验证
            if not parent_id or not isinstance(parent_id, str):
                raise RepositoryValidationError("父任务ID参数不能为空且必须是字符串类型")

            # 构建查询：查找指定父任务的未删除子任务
            statement = select(Task).where(
                and_(
                    Task.parent_id == parent_id,
                    Task.is_deleted == False
                )
            ).order_by(Task.sort_order.asc(), Task.created_at.asc())

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据父任务ID查找子任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据父任务ID查找子任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_root_tasks(self, user_id: str = None) -> List[Task]:
        """
        查找根任务（没有父任务的任务）

        Args:
            user_id: 可选的用户ID，如果提供则只查找该用户的根任务

        Returns:
            List[Task]: 根任务列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> roots = task_repo.find_root_tasks("user123")
            >>> print(f"用户有 {len(roots)} 个根任务")
            "用户有 2 个根任务"
        """
        try:
            # 参数验证
            if user_id is not None and (not user_id or not isinstance(user_id, str)):
                raise RepositoryValidationError("用户ID参数必须是字符串类型或None")

            # 构建查询条件
            conditions = [Task.parent_id.is_(None), Task.is_deleted == False]

            if user_id:
                conditions.append(Task.user_id == user_id)

            # 构建查询
            statement = select(Task).where(and_(*conditions)).order_by(
                Task.priority.desc(), Task.sort_order.asc(), Task.created_at.desc()
            )

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找根任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找根任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_leaf_tasks(self, user_id: str = None) -> List[Task]:
        """
        查找叶子任务（没有子任务的任务）

        Args:
            user_id: 可选的用户ID，如果提供则只查找该用户的叶子任务

        Returns:
            List[Task]: 叶子任务列表

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if user_id is not None and (not user_id or not isinstance(user_id, str)):
                raise RepositoryValidationError("用户ID参数必须是字符串类型或None")

            # 子查询：查找所有有子任务的任务ID
            subquery = select(Task.parent_id).where(Task.parent_id.isnot(None)).distinct()

            # 构建查询条件
            conditions = [
                Task.id.notin_(subquery),
                Task.is_deleted == False
            ]

            if user_id:
                conditions.append(Task.user_id == user_id)

            # 构建查询
            statement = select(Task).where(and_(*conditions)).order_by(
                Task.priority.desc(), Task.created_at.desc()
            )

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找叶子任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找叶子任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_pending_tasks(self, user_id: str = None) -> List[Task]:
        """
        查找待完成任务

        Args:
            user_id: 可选的用户ID，如果提供则只查找该用户的待完成任务

        Returns:
            List[Task]: 待完成任务列表
        """
        return self.find_by_status(TaskStatus.PENDING) if not user_id else \
               [task for task in self.find_by_status(TaskStatus.PENDING) if task.user_id == user_id]

    def find_completed_tasks(self, user_id: str = None, days: int = 30) -> List[Task]:
        """
        查找已完成任务

        Args:
            user_id: 可选的用户ID
            days: 查找最近多少天内的完成任务，默认30天

        Returns:
            List[Task]: 已完成任务列表
        """
        try:
            # 参数验证
            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 构建查询条件
            conditions = [
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= threshold_date,
                Task.is_deleted == False
            ]

            if user_id:
                conditions.append(Task.user_id == user_id)

            # 构建查询
            statement = select(Task).where(and_(*conditions)).order_by(
                desc(Task.completed_at)
            )

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找已完成任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找已完成任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_overdue_tasks(self, user_id: str = None) -> List[Task]:
        """
        查找逾期任务（这里简单实现，实际项目中可能需要due_date字段）

        Args:
            user_id: 可选的用户ID

        Returns:
            List[Task]: 逾期任务列表
        """
        # 简单实现：查找创建时间超过7天仍为待完成的任务
        try:
            threshold_date = datetime.now(timezone.utc) - timedelta(days=7)

            # 构建查询条件
            conditions = [
                Task.status == TaskStatus.PENDING,
                Task.created_at < threshold_date,
                Task.is_deleted == False
            ]

            if user_id:
                conditions.append(Task.user_id == user_id)

            # 构建查询
            statement = select(Task).where(and_(*conditions)).order_by(
                Task.created_at.asc()
            )

            # 执行查询
            tasks = self.session.exec(statement).all()

            return list(tasks)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找逾期任务失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找逾期任务时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def complete_task(self, task_id: str) -> Task:
        """
        完成任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 完成后的任务

        Raises:
            RepositoryValidationError: 任务ID参数无效时
            RepositoryNotFoundError: 任务不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> task_repo = TaskRepository(session)
            >>> completed_task = task_repo.complete_task("task123")
            >>> print(f"任务状态: {completed_task.status}")
            "任务状态: TaskStatus.COMPLETED"
        """
        try:
            # 参数验证
            if not task_id or not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数不能为空且必须是字符串类型")

            # 查找任务
            task = self.get_by_id(task_id)
            if task is None:
                raise RepositoryNotFoundError(f"未找到ID为 {task_id} 的任务")

            # 检查任务状态
            if task.status == TaskStatus.COMPLETED:
                raise RepositoryValidationError(f"任务 {task_id} 已经完成，无需重复操作")

            if task.status == TaskStatus.CANCELLED:
                raise RepositoryValidationError(f"任务 {task_id} 已取消，无法完成")

            # 构建更新数据
            update_data = {
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now(timezone.utc)
            }

            # 更新任务
            return self.update(task_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"完成任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    def reopen_task(self, task_id: str) -> Task:
        """
        重新打开任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 重新打开后的任务

        Raises:
            RepositoryValidationError: 任务ID参数无效时
            RepositoryNotFoundError: 任务不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id or not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数不能为空且必须是字符串类型")

            # 查找任务
            task = self.get_by_id(task_id)
            if task is None:
                raise RepositoryNotFoundError(f"未找到ID为 {task_id} 的任务")

            # 检查任务状态
            if task.status == TaskStatus.PENDING:
                raise RepositoryValidationError(f"任务 {task_id} 已经是待完成状态，无需重新打开")

            if task.status == TaskStatus.IN_PROGRESS:
                raise RepositoryValidationError(f"任务 {task_id} 正在进行中，无需重新打开")

            # 构建更新数据
            update_data = {
                "status": TaskStatus.PENDING,
                "completed_at": None
            }

            # 更新任务
            return self.update(task_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"重新打开任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    def cancel_task(self, task_id: str) -> Task:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 取消后的任务

        Raises:
            RepositoryValidationError: 任务ID参数无效时
            RepositoryNotFoundError: 任务不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id or not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数不能为空且必须是字符串类型")

            # 查找任务
            task = self.get_by_id(task_id)
            if task is None:
                raise RepositoryNotFoundError(f"未找到ID为 {task_id} 的任务")

            # 检查任务状态
            if task.status == TaskStatus.CANCELLED:
                raise RepositoryValidationError(f"任务 {task_id} 已经取消，无需重复操作")

            if task.status == TaskStatus.COMPLETED:
                raise RepositoryValidationError(f"任务 {task_id} 已完成，无法取消")

            # 构建更新数据
            update_data = {
                "status": TaskStatus.CANCELLED,
                "completed_at": None
            }

            # 更新任务
            return self.update(task_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"取消任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    def delete_task(self, task_id: str) -> Task:
        """
        软删除任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 删除后的任务

        Raises:
            RepositoryValidationError: 任务ID参数无效时
            RepositoryNotFoundError: 任务不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id or not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数不能为空且必须是字符串类型")

            # 查找任务
            task = self.get_by_id(task_id)
            if task is None:
                raise RepositoryNotFoundError(f"未找到ID为 {task_id} 的任务")

            # 检查是否已删除
            if task.is_deleted:
                raise RepositoryValidationError(f"任务 {task_id} 已经删除，无需重复操作")

            # 构建更新数据
            update_data = {
                "is_deleted": True
            }

            # 更新任务
            return self.update(task_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"删除任务失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    def get_task_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """
        获取任务统计信息

        Args:
            user_id: 可选的用户ID，如果提供则只统计该用户的任务

        Returns:
            Dict[str, Any]: 统计信息字典

        Raises:
            RepositoryValidationError: 用户ID参数无效时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if user_id is not None and (not user_id or not isinstance(user_id, str)):
                raise RepositoryValidationError("用户ID参数必须是字符串类型或None")

            # 构建基础查询条件
            base_conditions = [Task.is_deleted == False]
            if user_id:
                base_conditions.append(Task.user_id == user_id)

            # 统计各状态任务数量
            status_stats = {}
            for status in TaskStatus:
                status_count_query = select(func.count(Task.id)).where(
                    and_(*base_conditions, Task.status == status)
                )
                status_count = self.session.exec(status_count_query).one()
                status_stats[status.value] = status_count

            # 统计各优先级任务数量
            priority_stats = {}
            for priority in PriorityLevel:
                priority_count_query = select(func.count(Task.id)).where(
                    and_(*base_conditions, Task.priority == priority)
                )
                priority_count = self.session.exec(priority_count_query).one()
                priority_stats[priority.value] = priority_count

            # 统计总任务数和已完成任务数
            total_query = select(func.count(Task.id)).where(and_(*base_conditions))
            total_count = self.session.exec(total_query).one()

            completed_query = select(func.count(Task.id)).where(
                and_(*base_conditions, Task.status == TaskStatus.COMPLETED)
            )
            completed_count = self.session.exec(completed_query).one()

            # 计算完成率
            completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0

            return {
                "total_tasks": total_count,
                "completed_tasks": completed_count,
                "pending_tasks": status_stats.get(TaskStatus.PENDING.value, 0),
                "in_progress_tasks": status_stats.get(TaskStatus.IN_PROGRESS.value, 0),
                "cancelled_tasks": status_stats.get(TaskStatus.CANCELLED.value, 0),
                "completion_rate": round(completion_rate, 2),
                "status_distribution": status_stats,
                "priority_distribution": priority_stats
            }

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"获取任务统计信息失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"获取任务统计信息时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def get_task_hierarchy(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务的层级结构

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, Any]: 包含任务、父任务、子任务信息的字典

        Raises:
            RepositoryValidationError: 任务ID参数无效时
            RepositoryNotFoundError: 任务不存在时
            RepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not task_id or not isinstance(task_id, str):
                raise RepositoryValidationError("任务ID参数不能为空且必须是字符串类型")

            # 查找主任务
            task = self.get_by_id(task_id)
            if task is None:
                raise RepositoryNotFoundError(f"未找到ID为 {task_id} 的任务")

            # 查找父任务链（递归向上）
            parent_chain = []
            current_parent = task.parent_id
            depth = 0

            while current_parent and depth < 10:  # 防止无限循环
                parent_task = self.get_by_id(current_parent)
                if not parent_task or parent_task.is_deleted:
                    break
                parent_chain.append(parent_task)
                current_parent = parent_task.parent_id
                depth += 1

            # 查找直接子任务
            children = self.find_by_parent(task_id)

            # 查找所有后代任务（递归向下）
            all_descendants = []
            def collect_descendants(parent_id: str, current_depth: int = 0):
                if current_depth >= 10:  # 防止无限循环
                    return

                direct_children = self.find_by_parent(parent_id)
                for child in direct_children:
                    all_descendants.append(child)
                    collect_descendants(child.id, current_depth + 1)

            collect_descendants(task_id)

            return {
                "task": task,
                "parent_chain": list(reversed(parent_chain)),  # 从根到当前任务
                "direct_children": children,
                "all_descendants": all_descendants,
                "depth": len(parent_chain),
                "has_children": len(children) > 0,
                "has_descendants": len(all_descendants) > 0
            }

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"获取任务层级结构失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )


# 导出TaskRepository类
__all__ = ["TaskRepository"]