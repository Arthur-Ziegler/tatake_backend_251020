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
from src.utils.uuid_helpers import uuid_converter
from src.utils.enum_helpers import enum_converter

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
            # 使用UUID转换器处理UUID字段
            processed_data = task_data.copy()

            # 转换UUID字段为字符串格式（数据库存储）
            if 'user_id' in processed_data:
                processed_data['user_id'] = uuid_converter.to_db_format(processed_data['user_id'])
            if 'parent_id' in processed_data and processed_data['parent_id']:
                processed_data['parent_id'] = uuid_converter.to_db_format(processed_data['parent_id'])

            # 转换枚举字段为字符串格式（数据库存储）
            if 'status' in processed_data:
                processed_data['status'] = enum_converter.to_db_format(processed_data['status'], TaskStatusConst)
            if 'priority' in processed_data:
                processed_data['priority'] = enum_converter.to_db_format(processed_data['priority'], TaskPriorityConst)

            # 创建任务实例
            task = Task(**processed_data)

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
        task_id: str,
        user_id: str,
        include_deleted: bool = False
    ) -> Optional[Task]:
        """
        根据ID获取任务

        注意：Repository层只处理字符串类型的UUID，Service层负责UUID转换。

        Args:
            task_id (str): 任务ID（字符串格式的UUID）
            user_id (str): 用户ID（字符串格式的UUID，用于权限验证）
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            Optional[Task]: 任务实体，如果不存在则返回None

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 确保UUID参数为字符串格式（虽然应该是，但为了安全）
            task_id_str = uuid_converter.to_db_format(task_id)
            user_id_str = uuid_converter.to_db_format(user_id)

            # 构建查询条件
            conditions = [Task.id == task_id_str, Task.user_id == user_id_str]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = select(Task).where(and_(*conditions))
            result = self.session.execute(statement).first()

            task = result[0] if result else None

            logger.debug(f"查询任务: {task_id_str}, 结果: {task is not None}")
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
        parent_id: str,
        user_id: str,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        获取直接子任务列表

        注意：Repository层只处理字符串类型的UUID，Service层负责UUID转换。

        Args:
            parent_id (str): 父任务ID（字符串格式的UUID）
            user_id (str): 用户ID（字符串格式的UUID，用于权限验证）
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
            tasks = list(self.session.execute(statement).scalars().all())  # 直接获取模型对象列表

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
        parent_id: str,
        user_id: str,
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
                    id=row.id,  # 保持字符串格式
                    user_id=row.user_id,  # 保持字符串格式
                    title=row.title,
                    description=row.description,
                    status=row.status,
                    priority=row.priority,
                    parent_id=row.parent_id,  # 保持字符串格式
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
        task_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Task]:
        """
        更新任务

        注意：Repository层只处理字符串类型的UUID，Service层负责UUID转换。

        Args:
            task_id (str): 任务ID（字符串格式的UUID）
            user_id (str): 用户ID（字符串格式的UUID，用于权限验证）
            update_data (Dict[str, Any]): 更新数据

        Returns:
            Optional[Task]: 更新后的任务实体，如果不存在则返回None

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 确保UUID参数为字符串格式
            task_id_str = uuid_converter.to_db_format(task_id)
            user_id_str = uuid_converter.to_db_format(user_id)

            # 首先检查任务是否存在
            existing_task = self.get_by_id(task_id_str, user_id_str)
            if not existing_task:
                return None

            # 处理更新数据中的枚举字段
            processed_update_data = update_data.copy()
            if 'status' in processed_update_data:
                processed_update_data['status'] = enum_converter.to_db_format(
                    processed_update_data['status'], TaskStatusConst
                )
            if 'priority' in processed_update_data:
                processed_update_data['priority'] = enum_converter.to_db_format(
                    processed_update_data['priority'], TaskPriorityConst
                )

            # 添加更新时间
            processed_update_data['updated_at'] = datetime.now(timezone.utc)

            # 执行更新
            statement = (
                update(Task)
                .where(and_(
                    Task.id == task_id_str,
                    Task.user_id == user_id_str,
                    Task.is_deleted == False
                ))
                .values(**processed_update_data)
                .returning(Task)
            )

            result = self.session.execute(statement).first()
            self.session.flush()
            self.session.commit()  # 确保事务提交到数据库

            task = result[0] if result else None

            logger.debug(f"更新任务成功: {task_id_str}")
            return task

        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            raise TaskDatabaseException(
                operation="update_task",
                reason=f"数据库更新操作失败: {str(e)}",
                original_error=e
            )

    def soft_delete(self, task_id: str, user_id: str) -> bool:
        """
        软删除任务

        注意：Repository层只处理字符串类型的UUID，Service层负责UUID转换。

        Args:
            task_id (str): 任务ID（字符串格式的UUID）
            user_id (str): 用户ID（字符串格式的UUID，用于权限验证）

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

    def soft_delete_cascade(self, task_id: str, user_id: str) -> int:
        """
        级联软删除任务及其所有子任务

        Args:
            task_id (Union[UUID, str]): 任务ID
            user_id (Union[UUID, str]): 用户ID（用于权限验证）

        Returns:
            int: 删除的任务总数

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 转换UUID为字符串进行数据库查询
            task_id_str = uuid_converter.to_db_format(task_id)
            user_id_str = uuid_converter.to_db_format(user_id)

            # 获取所有后代任务ID
            descendants = self.get_all_descendants(task_id_str, user_id_str, include_deleted=False)
            descendant_ids = [uuid_converter.to_db_format(desc.id) for desc in descendants]

            # 包含父任务本身 - 使用字符串UUID
            all_ids = [task_id_str] + descendant_ids

            # 批量软删除 - 所有ID都转换为字符串
            statement = (
                update(Task)
                .where(and_(
                    Task.id.in_(all_ids),
                    Task.user_id == user_id_str,
                    Task.is_deleted == False
                ))
                .values(
                    is_deleted=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            result = self.session.execute(statement)
            self.session.flush()

            # 提交事务 - 确保删除操作持久化
            self.session.commit()

            deleted_count = result.rowcount
            logger.debug(f"级联软删除任务: task_id={task_id_str}, 数量: {deleted_count}")
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

            # 处理筛选条件 - 简化版本
            if not filters.get('include_deleted', False):
                conditions.append(Task.is_deleted == False)

            # 构建基础查询
            base_query = select(Task).where(and_(*conditions))

            # 获取总数
            count_query = select(func.count(Task.id)).where(and_(*conditions))
            total_count = self.session.execute(count_query).scalar() or 0

            # 固定排序：按创建时间倒序（最新在前）
            base_query = base_query.order_by(desc(Task.created_at))

            # 处理分页
            page = pagination.get('page', 1)
            page_size = pagination.get('page_size', 20)

            offset = (page - 1) * page_size
            base_query = base_query.offset(offset).limit(page_size)

            # 执行查询
            result = self.session.execute(base_query)
            tasks = [row[0] for row in result.all()]  # 从Result对象中提取模型对象

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
            tasks = list(self.session.execute(statement).scalars().all())  # 直接获取模型对象列表

            logger.debug(f"标题搜索任务: title={title}, 精确匹配={exact_match}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"标题搜索任务失败: {e}")
            raise TaskDatabaseException(
                operation="find_by_title",
                reason=f"数据库搜索操作失败: {str(e)}",
                original_error=e
            )

    def count_by_status(self, user_id: str, include_deleted: bool = False) -> Dict[str, int]:
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
            result = self.session.execute(statement).scalars().all()

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

    # === 树结构专用方法 ===

    def get_tasks_by_level(
        self,
        user_id: UUID,
        level: int,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        按层级查询任务

        Args:
            user_id (UUID): 用户ID
            level (int): 任务层级
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 指定层级的任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [
                Task.user_id == user_id,
                Task.level == level
            ]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.created_at)
            )
            result = self.session.execute(statement).scalars().all()
            tasks = [row[0] for row in result]

            logger.debug(f"按层级查询任务: user_id={user_id}, level={level}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"按层级查询任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_tasks_by_level",
                reason=f"数据库层级查询失败: {str(e)}",
                original_error=e
            )

    def get_subtree_tasks(
        self,
        parent_id: UUID,
        user_id: UUID,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        使用路径前缀查询子树任务（高效方式）

        Args:
            parent_id (UUID): 父任务ID
            user_id (UUID): 用户ID
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 子树中的所有任务

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 首先获取父任务的路径
            parent_task = self.get_by_id(parent_id, user_id, include_deleted)
            if not parent_task:
                return []

            # 构建路径前缀
            parent_path = parent_task.path
            if parent_path:
                path_prefix = f"{parent_path}/{parent_id}"
            else:
                path_prefix = f"/{parent_id}"

            # 构建查询条件
            conditions = [
                Task.user_id == user_id,
                Task.path.like(f"{path_prefix}%")
            ]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.level, Task.created_at)
            )
            result = self.session.execute(statement).scalars().all()
            tasks = [row[0] for row in result]

            logger.debug(f"路径前缀查询子树: parent_id={parent_id}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"路径前缀查询子树失败: {e}")
            raise TaskDatabaseException(
                operation="get_subtree_tasks",
                reason=f"数据库路径前缀查询失败: {str(e)}",
                original_error=e
            )

    def get_leaf_nodes(
        self,
        user_id: UUID,
        parent_id: Optional[UUID] = None,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        获取叶子节点任务（没有子任务的节点）

        Args:
            user_id (UUID): 用户ID
            parent_id (Optional[UUID]): 可选的父任务ID，限定查询范围
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 叶子节点任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建基础查询条件
            conditions = [Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            if parent_id:
                # 使用路径前缀限定范围
                parent_task = self.get_by_id(parent_id, user_id, include_deleted)
                if parent_task:
                    path_prefix = f"{parent_task.path}/{parent_id}" if parent_task.path else f"/{parent_id}"
                    conditions.append(Task.path.like(f"{path_prefix}%"))

            # 使用LEFT JOIN查找没有子任务的节点
            subquery = (
                select(Task.parent_id)
                .where(and_(
                    Task.parent_id.isnot(None),
                    Task.user_id == user_id,
                    Task.is_deleted == include_deleted  # 保持一致性
                ))
                .distinct()
            )

            # 叶子节点条件：ID不在任何其他任务的parent_id中
            conditions.append(~Task.id.in_(subquery))

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.level, Task.created_at)
            )
            result = self.session.execute(statement).scalars().all()
            tasks = [row[0] for row in result]

            logger.debug(f"查询叶子节点: user_id={user_id}, parent_id={parent_id}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"查询叶子节点失败: {e}")
            raise TaskDatabaseException(
                operation="get_leaf_nodes",
                reason=f"数据库叶子节点查询失败: {str(e)}",
                original_error=e
            )

    def get_tasks_by_path_prefix(
        self,
        user_id: UUID,
        path_prefix: str,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        根据路径前缀查询任务

        Args:
            user_id (UUID): 用户ID
            path_prefix (str): 路径前缀
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 匹配路径前缀的任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [
                Task.user_id == user_id,
                Task.path.like(f"{path_prefix}%")
            ]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.level, Task.created_at)
            )
            result = self.session.execute(statement).scalars().all()
            tasks = [row[0] for row in result]

            logger.debug(f"路径前缀查询: user_id={user_id}, prefix={path_prefix}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"路径前缀查询失败: {e}")
            raise TaskDatabaseException(
                operation="get_tasks_by_path_prefix",
                reason=f"数据库路径前缀查询失败: {str(e)}",
                original_error=e
            )

    def get_root_tasks(
        self,
        user_id: UUID,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        获取根任务（parent_id为None的任务）

        Args:
            user_id (UUID): 用户ID
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 根任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [
                Task.user_id == user_id,
                Task.parent_id.is_(None)
            ]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 执行查询
            statement = (
                select(Task)
                .where(and_(*conditions))
                .order_by(Task.created_at)
            )
            result = self.session.execute(statement).scalars().all()
            tasks = [row[0] for row in result]

            logger.debug(f"查询根任务: user_id={user_id}, 数量: {len(tasks)}")
            return tasks

        except Exception as e:
            logger.error(f"查询根任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_root_tasks",
                reason=f"数据库根任务查询失败: {str(e)}",
                original_error=e
            )

    def get_task_tree_depth(
        self,
        user_id: UUID,
        include_deleted: bool = False
    ) -> int:
        """
        获取用户任务树的最大深度

        Args:
            user_id (UUID): 用户ID
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            int: 最大层级深度

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建查询条件
            conditions = [Task.user_id == user_id]

            if not include_deleted:
                conditions.append(Task.is_deleted == False)

            # 查询最大层级
            statement = select(func.max(Task.level)).where(and_(*conditions))
            max_level = self.session.execute(statement).scalar()

            result = max_level if max_level is not None else 0
            logger.debug(f"查询任务树深度: user_id={user_id}, 深度: {result}")
            return result

        except Exception as e:
            logger.error(f"查询任务树深度失败: {e}")
            raise TaskDatabaseException(
                operation="get_task_tree_depth",
                reason=f"数据库深度查询失败: {str(e)}",
                original_error=e
            )

    def get_all_leaf_tasks(
        self,
        user_id: str,
        include_deleted: bool = False
    ) -> List[Task]:
        """
        获取用户所有叶子任务（没有子任务的任务）

        叶子任务定义：没有其他任务将其作为父任务的任务
        这是计算父任务完成百分比的基础

        Args:
            user_id (str): 用户ID
            include_deleted (bool): 是否包含已删除的任务

        Returns:
            List[Task]: 叶子任务列表

        Raises:
            TaskDatabaseException: 数据库操作失败
        """
        try:
            # 构建基础查询条件
            base_conditions = [Task.user_id == user_id]

            if not include_deleted:
                base_conditions.append(Task.is_deleted == False)

            # 使用子查询找到所有有子任务的父任务ID
            parent_subquery = (
                select(Task.parent_id)
                .where(
                    and_(
                        Task.parent_id.is_not(None),
                        Task.user_id == user_id,
                        *([Task.is_deleted == False] if not include_deleted else [])
                    )
                )
                .distinct()
            )

            # 查询叶子任务：不在父任务ID列表中的任务
            statement = (
                select(Task)
                .where(
                    and_(
                        *base_conditions,
                        ~Task.id.in_(parent_subquery)  # 不在有子任务的父任务ID列表中
                    )
                )
                .order_by(Task.created_at.desc())
            )

            results = self.session.execute(statement).all()
            leaf_tasks = [result[0] for result in results]

            logger.debug(f"查询用户叶子任务: user_id={user_id}, 数量: {len(leaf_tasks)}")
            return leaf_tasks

        except Exception as e:
            logger.error(f"查询叶子任务失败: {e}")
            raise TaskDatabaseException(
                operation="get_all_leaf_tasks",
                reason=f"数据库叶子任务查询失败: {str(e)}",
                original_error=e
            )