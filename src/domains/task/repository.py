"""
Task领域Repository层

提供Task实体的数据访问操作，封装所有数据库相关的逻辑。

Repository职责：
1. 封装数据库操作细节
2. 提供类型安全的数据访问方法
3. 处理查询逻辑和数据转换
4. 管理事务边界

设计原则：
1. 单一职责：只负责数据访问，不包含业务逻辑
2. 接口隔离：提供清晰的方法接口
3. 依赖注入：接受Session对象，支持测试
4. 异步支持：所有数据库操作都是异步的

核心方法：
- create(): 创建任务
- get_by_id(): 根据ID获取任务
- get_children(): 获取子任务列表
- update(): 更新任务
- soft_delete(): 软删除任务
- get_list(): 获取任务列表
- find_by_title(): 根据标题搜索任务

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlmodel import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy import text
from sqlmodel import Session

from .models import Task, TaskStatusConst, TaskPriorityConst
from .exceptions import TaskDatabaseException

# 配置日志
logger = logging.getLogger(__name__)


class TaskRepository:
    """
    任务数据访问Repository

    提供任务实体的完整CRUD操作和复杂查询功能。
    所有方法都是同步的，调用方需要管理数据库会话。
    """

    def __init__(self, session: Session):
        """
        初始化Repository

        Args:
            session (Session): 数据库会话
        """
        self.session = session

    def create(self, task_data: Dict[str, Any]) -> Task:
        """
        创建新任务

        Args:
            task_data (Dict[str, Any]): 任务数据字典

        Returns:
            Task: 创建的任务实体

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 创建任务实例
            task = Task(**task_data)

            # 设置时间戳
            now = datetime.now(timezone.utc)
            task.created_at = now
            task.updated_at = now

            # 保存到数据库
            self.session.add(task)
            self.session.flush()  # 获取ID但不提交

            logger.debug(f"创建任务成功: {task.id}")
            return task

        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            raise TaskDatabaseException(
                operation="create_task",
                reason=f"数据库创建操作失败: {str(e)}",
                original_error=e
            )

    def get_by_id(
        self,
        task_id: UUID,
        user_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Task]:
        """
        根据ID获取任务

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID（用于权限验证）
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            Optional[Task]: 任务实体，如果不存在则返回None

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [Task.id == task_id, Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = select(Task).where(and_(*conditions))
            result = self.session.execute(statement).first()

            if result:
                task = result[0]  # 获取实际的实体对象
            else:
                task = None

            logger.debug(f"查询任务: {task_id}, 结果: {task is not None}")
            return task

        except Exception as e:
            logger.error(f"查询任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_task_by_id",
                reason=f"数据库查询操作失败: {str(e)}",
                original_error=e
            )

    def get_children(
        self,
        parent_id: UUID,
        user_id: UUID,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        获取直接子任务列表

        Args:
            parent_id (UUID): 父任务ID
            user_id (UUID): 用户ID（用于权限验证）
            include_deleted (bool): 是否包含已删除的子任务

        Returns:
            List[Task]: 子任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [
                Task.parent_id == parent_id,
                Task.user_id == user_id
            ]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.created_at)
            )
            result = self.session.execute(statement).all()
            tasks = [row[0] for row in result]  # 提取实体对象

            logger.debug(f"查询子任务: parent_id={parent_id}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"查询子任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_children",
                reason=f"数据库查询操作失败: {str(e)}",
                original_error=e
            )

    def get_all_descendants(
        self,
        parent_id: UUID,
        user_id: UUID,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        递归获取所有后代任务

        Args:
            parent_id (UUID): 父任务ID
            user_id (UUID): 用户ID（用于权限验证）
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 所有后代任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 使用递归CTE查询所有后代
            conditions = [Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 构建递归查询
            recursive_query = text("""
                WITH RECURSIVE task_tree AS (
                    -- 基础查询：直接子任务
                    SELECT id, user_id, title, description, status, priority,
                           parent_id, tags, due_date, planned_start_time,
                           planned_end_time, is_deleted, created_at, updated_at,
                           1 as level
                    FROM tasks
                    WHERE parent_id = :parent_id AND user_id = :user_id
                    AND (:include_deleted OR is_deleted = false)

                    UNION ALL

                    -- 递归查询：子任务的子任务
                    SELECT t.id, t.user_id, t.title, t.description, t.status,
                           t.priority, t.parent_id, t.tags, t.due_date,
                           t.planned_start_time, t.planned_end_time,
                           t.is_deleted, t.created_at, t.updated_at,
                           tt.level + 1
                    FROM tasks t
                    INNER JOIN task_tree tt ON t.parent_id = tt.id
                    WHERE t.user_id = :user_id
                    AND (:include_deleted OR t.is_deleted = false)
                )
                SELECT * FROM task_tree ORDER BY level, created_at
            """)

            result = self.session.execute(
                recursive_query,
                {
                    "parent_id": str(parent_id),
                    "user_id": str(user_id),
                    "include_deleted": include_deleted
                }
            ).all()

            # 转换为Task对象列表
            tasks = []
            for row in result:
                task = Task(
                    id=UUID(row.id),
                    user_id=UUID(row.user_id),
                    title=row.title,
                    description=row.description,
                    status=row.status,
                    priority=row.priority,
                    parent_id=UUID(row.parent_id) if row.parent_id else None,
                    tags=row.tags,
                    due_date=row.due_date,
                    planned_start_time=row.planned_start_time,
                    planned_end_time=row.planned_end_time,
                    is_deleted=row.is_deleted,
                    created_at=row.created_at,
                    updated_at=row.updated_at
                )
                tasks.append(task)

            logger.debug(f"查询所有后代任务: parent_id={parent_id}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"查询所有后代任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_all_descendants",
                reason=f"数据库递归查询失败: {str(e)}",
                original_error=e
            )

    def update(
        self,
        task_id: UUID,
        user_id: UUID,
        update_data: Dict[str, Any]
    ) -> Optional[Task]:
        """
        更新任务

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID（用于权限验证）
            update_data (Dict[str, Any]): 更新数据

        Returns:
            Optional[Task]: 更新后的任务实体，如果不存在则返回None

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 首先检查任务是否存在
            existing_task = self.get_by_id(task_id, user_id)
            if not existing_task:
                return None

            # 添加更新时间
            update_data['updated_at'] = datetime.now(timezone.utc)

            # 执行更新
            statement = (
                update(Task)
                .where(and_(
                    Task.id == task_id,
                    Task.user_id == user_id,
                    Task.is_deleted == False
                ))
                .values(**update_data)
                .returning(Task)
            )

            result = self.session.execute(statement).first()
            self.session.flush()

            if result:
                task = result[0]  # 获取实际的实体对象
            else:
                task = None

            logger.debug(f"更新任务成功: {task_id}")
            return task

        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            raise TaskDatabaseException(
                operation="update_task",
                reason=f"数据库更新操作失败: {str(e)}",
                original_error=e
            )

    def soft_delete(self, task_id: UUID, user_id: UUID) -> bool:
        """
        软删除任务

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID（用于权限验证）

        Returns:
            bool: 删除成功返回True，任务不存在返回False

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 执行软删除
            statement = (
                update(Task)
                .where(and_(
                    Task.id == task_id,
                    Task.user_id == user_id,
                    Task.is_deleted == False
                ))
                .values(
                    is_deleted=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = self.session.execute(statement)
            self.session.flush()

            success = result.rowcount > 0
            logger.debug(f"软删除任务: {task_id}, 成功: {success}")
            return success

        except Exception as e:
            logger.error(f"软删除任务失败: {e}")
            raise TaskDatabaseException(
                operation="soft_delete_task",
                reason=f"数据库软删除操作失败: {str(e)}",
                original_error=e
            )

    def soft_delete_cascade(self, task_id: UUID, user_id: UUID) -> int:
        """
        级联软删除任务及其所有子任务

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID（用于权限验证）

        Returns:
            int: 删除的任务总数

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 获取所有后代任务ID
            descendants = self.get_all_descendants(task_id, user_id, include_deleted=False)
            descendant_ids = [desc.id for desc in descendants]

            # 包含父任务本身
            all_ids = [task_id] + descendant_ids

            # 批量软删除
            statement = (
                update(Task)
                .where(and_(
                    Task.id.in_(all_ids),
                    Task.user_id == user_id,
                    Task.is_deleted == False
                ))
                .values(
                    is_deleted=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = self.session.execute(statement)
            self.session.flush()

            deleted_count = result.rowcount
            logger.debug(f"级联软删除任务: task_id={task_id}, 数量: {deleted_count}")
            return deleted_count

        except Exception as e:
            logger.error(f"级联软删除任务失败: {e}")
            raise TaskDatabaseException(
                operation="soft_delete_cascade",
                reason=f"数据库级联删除操作失败: {str(e)}",
                original_error=e
            )

    def get_list(
        self,
        user_id: UUID,
        filters: Dict[str, Any] = None,
        pagination: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        获取任务列表

        Args:
            user_id (UUID): 用户ID
            filters (Dict[str, Any]): 筛选条件
            pagination (Dict[str, Any]): 分页参数

        Returns:
            Dict[str, Any]: 包含任务列表和分页信息的字典

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 默认参数
            filters = filters or {}
            pagination = pagination or {}

            # 构建查询条件
            conditions = [Task.user_id == user_id]

            # 处理筛选条件
            if not filters.get('include_deleted', False):
                conditions.append(Task.is_deleted == False)

            # 状态筛选
            if filters.get('status'):
                if isinstance(filters['status'], list):
                    conditions.append(Task.status.in_(filters['status']))
                else:
                    conditions.append(Task.status == filters['status'])

            # 优先级筛选
            if filters.get('priority'):
                if isinstance(filters['priority'], list):
                    conditions.append(Task.priority.in_(filters['priority']))
                else:
                    conditions.append(Task.priority == filters['priority'])

            # 父任务筛选
            if filters.get('parent_id') is not None:
                if filters['parent_id']:
                    conditions.append(Task.parent_id == filters['parent_id'])
                else:
                    conditions.append(Task.parent_id.is_(None))

            # 截止日期筛选
            if filters.get('due_before'):
                conditions.append(Task.due_date <= filters['due_before'])

            if filters.get('due_after'):
                conditions.append(Task.due_date >= filters['due_after'])

            # 搜索关键词
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                conditions.append(
                    or_(
                        Task.title.ilike(search_term),
                        Task.description.ilike(search_term)
                    )
                )

            # 构建基础查询
            base_query = select(Task).where(and_(*conditions))

            # 获取总数
            count_query = select(func.count(Task.id)).where(and_(*conditions))
            total_count = self.session.execute(count_query).scalar()

            # 处理排序
            sort_by = pagination.get('sort_by', 'created_at')
            sort_order = pagination.get('sort_order', 'desc')

            if hasattr(Task, sort_by):
                sort_column = getattr(Task, sort_by)
                if sort_order == 'desc':
                    base_query = base_query.order_by(desc(sort_column))
                else:
                    base_query = base_query.order_by(asc(sort_column))

            # 处理分页
            page = pagination.get('page', 1)
            page_size = pagination.get('page_size', 20)

            offset = (page - 1) * page_size
            base_query = base_query.offset(offset).limit(page_size)

            # 执行查询
            result = self.session.execute(base_query).all()
            tasks = [row[0] for row in result]  # 提取实体对象

            # 计算分页信息
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            pagination_info = {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }

            logger.debug(f"查询任务列表: user_id={user_id}, 数量: {len(tasks)}, 总数: {total_count}")

            return {
                'tasks': tasks,
                'pagination': pagination_info
            }

        except Exception as e:
            logger.error(f"查询任务列表失败: {e}")
            raise TaskDatabaseException(
                operation="get_task_list",
                reason=f"数据库列表查询失败: {str(e)}",
                original_error=e
            )

    def find_by_title(
        self,
        user_id: UUID,
        title: str,
        exact_match: bool = False,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        根据标题搜索任务

        Args:
            user_id (UUID): 用户ID
            title (str): 搜索标题
            exact_match (bool): 是否精确匹配
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 匹配的任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 标题匹配条件
            if exact_match:
                conditions.append(Task.title == title)
            else:
                conditions.append(Task.title.ilike(f"%{title}%"))

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.created_at)
            )
            result = self.session.execute(statement).all()
            tasks = [row[0] for row in result]  # 提取实体对象

            logger.debug(f"标题搜索任务: title={title}, 精确匹配={exact_match}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"标题搜索任务失败: {e}")
            raise TaskDatabaseException(
                operation="find_by_title",
                reason=f"数据库搜索操作失败: {str(e)}",
                original_error=e
            )

    def count_by_status(self, user_id: UUID, include_deleted: bool = False) -> Dict[str, int]:
        """
        按状态统计任务数量

        Args:
            user_id (UUID): 用户ID
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            Dict[str, int]: 各状态的任务数量

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行统计查询
            statement = (
                select(
                    Task.status,
                    func.count(Task.id).label('count')
                )
                .where(and_(*conditions))
                .group_by(Task.status)
            )
            result = self.session.execute(statement).all()

            # 构建结果字典
            status_count = {
                'pending': 0,
                'in_progress': 0,
                'completed': 0
            }

            for row in result:
                status_count[row.status] = row.count

            logger.debug(f"状态统计任务: user_id={user_id}, 结果: {status_count}")
            return status_count

        except Exception as e:
            logger.error(f"状态统计任务失败: {e}")
            raise TaskDatabaseException(
                operation="count_by_status",
                reason=f"数据库统计操作失败: {str(e)}",
                original_error=e
            )