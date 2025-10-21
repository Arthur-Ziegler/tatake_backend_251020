"""
Task领域Service层

提供任务管理的核心业务逻辑，协调Repository层和外部依赖。

Service职责：
1. 实现核心业务逻辑
2. 处理复杂的业务规则
3. 协调多个Repository
4. 事务管理
5. 业务验证

核心功能：
1. 任务创建和验证
2. 任务更新和业务规则检查
3. 循环引用检测
4. 级联删除逻辑
5. 任务列表查询和筛选
6. 权限验证

设计原则：
1. 业务逻辑封装：所有业务规则都在Service层
2. 事务边界管理：确保数据一致性
3. 错误处理：提供详细的错误信息
4. 可测试性：依赖注入，便于单元测试

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from uuid import UUID

from sqlmodel import Session

from .models import Task, TaskStatusConst, TaskPriorityConst
from .schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskListQuery,
    TaskResponse,
    TaskListResponse,
    PaginationInfo,
    TaskDeleteResponse
)
from .repository import TaskRepository
from .exceptions import (
    TaskNotFoundException,
    TaskPermissionDeniedException,
    CircularReferenceException,
    InvalidTimeRangeException,
    TaskValidationException,
    TaskDatabaseException
)

# 配置日志
logger = logging.getLogger(__name__)


class TaskService:
    """
    任务管理服务

    提供完整的任务管理业务逻辑，包括创建、更新、删除、查询等功能。
    负责执行业务规则验证和确保数据一致性。
    """

    def __init__(self, session: Session):
        """
        初始化TaskService

        Args:
            session (Session): 数据库会话
        """
        self.session = session
        self.repository = TaskRepository(session)

    def create_task(self, request: CreateTaskRequest, user_id: UUID) -> TaskResponse:
        """
        创建新任务

        业务逻辑：
        1. 验证请求数据
        2. 如果设置了parent_id，验证父任务存在性和权限
        3. 验证时间范围的合理性
        4. 创建任务并返回

        Args:
            request (CreateTaskRequest): 创建任务请求
            user_id (UUID): 用户ID

        Returns:
            TaskResponse: 创建的任务响应

        Raises:
            TaskNotFoundException: 父任务不存在
            TaskPermissionDeniedException: 无权限访问父任务
            InvalidTimeRangeException: 时间范围无效
            TaskValidationException: 数据验证失败
        """
        try:
            logger.info(f"开始创建任务: user_id={user_id}, title={request.title}")

            # 验证标题唯一性（可选）
            existing_tasks = self.repository.find_by_title(
                user_id=user_id,
                title=request.title,
                exact_match=True
            )
            if existing_tasks:
                logger.warning(f"任务标题已存在: {request.title}")

            # 验证父任务
            parent_task = None
            if request.parent_id:
                parent_task = self.repository.get_by_id(request.parent_id, user_id)
                if not parent_task:
                    raise TaskNotFoundException(
                        task_id=str(request.parent_id),
                        user_id=str(user_id)
                    )

                # 检查是否会形成循环引用（将任务设为自己的子任务）
                if request.parent_id == request.parent_id:  # 这里逻辑有问题，应该是检查其他情况
                    pass  # 创建时不会形成循环，因为新任务还没有子任务

            # 验证时间范围
            self._validate_time_range(
                planned_start_time=request.planned_start_time,
                planned_end_time=request.planned_end_time,
                due_date=request.due_date
            )

            # 准备任务数据
            task_data = {
                'user_id': user_id,
                'title': request.title,
                'description': request.description,
                'status': request.status,
                'priority': request.priority,
                'parent_id': request.parent_id,
                'tags': request.tags or [],
                'due_date': request.due_date,
                'planned_start_time': request.planned_start_time,
                'planned_end_time': request.planned_end_time
            }

            # 创建任务
            task = self.repository.create(task_data)

            # 提交事务
            self.session.commit()

            logger.info(f"任务创建成功: {task.id}")

            # 转换为响应格式
            return self._convert_to_response(task)

        except Exception as e:
            # 回滚事务
            self.session.rollback()
            logger.error(f"创建任务失败: {e}")
            raise

    def get_task(self, task_id: UUID, user_id: UUID) -> TaskResponse:
        """
        获取任务详情

        业务逻辑：
        1. 验证任务存在性
        2. 验证用户权限
        3. 检查任务是否已删除
        4. 返回任务详情

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            TaskResponse: 任务响应

        Raises:
            TaskNotFoundException: 任务不存在或已删除
            TaskPermissionDeniedException: 无权限访问任务
        """
        try:
            logger.debug(f"获取任务详情: task_id={task_id}, user_id={user_id}")

            # 获取任务
            task = self.repository.get_by_id(task_id, user_id, include_deleted=False)

            if not task:
                raise TaskNotFoundException(
                    task_id=str(task_id),
                    user_id=str(user_id)
                )

            logger.debug(f"任务获取成功: {task_id}")
            return self._convert_to_response(task)

        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            raise

    def update_task(
        self,
        task_id: UUID,
        request: UpdateTaskRequest,
        user_id: UUID
    ) -> TaskResponse:
        """
        更新任务

        业务逻辑：
        1. 验证任务存在性和权限
        2. 如果更新parent_id，检查循环引用
        3. 验证时间范围
        4. 执行部分更新
        5. 返回更新后的任务

        Args:
            task_id (UUID): 任务ID
            request (UpdateTaskRequest): 更新请求
            user_id (UUID): 用户ID

        Returns:
            TaskResponse: 更新后的任务响应

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限访问任务
            CircularReferenceException: 会形成循环引用
            InvalidTimeRangeException: 时间范围无效
        """
        try:
            logger.info(f"开始更新任务: task_id={task_id}, user_id={user_id}")

            # 获取现有任务
            existing_task = self.repository.get_by_id(task_id, user_id, include_deleted=False)
            if not existing_task:
                raise TaskNotFoundException(
                    task_id=str(task_id),
                    user_id=str(user_id)
                )

            # 准备更新数据
            update_data = {}

            # 处理各个字段的更新
            if request.title is not None:
                update_data['title'] = request.title

            if request.description is not None:
                update_data['description'] = request.description

            if request.status is not None:
                update_data['status'] = request.status

            if request.priority is not None:
                update_data['priority'] = request.priority

            if request.tags is not None:
                update_data['tags'] = request.tags

            if request.due_date is not None:
                update_data['due_date'] = request.due_date

            if request.planned_start_time is not None:
                update_data['planned_start_time'] = request.planned_start_time

            if request.planned_end_time is not None:
                update_data['planned_end_time'] = request.planned_end_time

            # 处理父任务更新（需要特殊验证）
            if request.parent_id is not None:
                # 检查循环引用
                if request.parent_id != existing_task.parent_id:
                    if self._check_circular_reference(task_id, request.parent_id, user_id):
                        raise CircularReferenceException(
                            task_id=str(task_id),
                            parent_id=str(request.parent_id)
                        )

                # 验证父任务存在性（如果不为None）
                if request.parent_id:
                    parent_task = self.repository.get_by_id(request.parent_id, user_id)
                    if not parent_task:
                        raise TaskNotFoundException(
                            task_id=str(request.parent_id),
                            user_id=str(user_id)
                        )

                update_data['parent_id'] = request.parent_id

            # 验证时间范围（如果更新了时间字段）
            planned_start = update_data.get('planned_start_time', existing_task.planned_start_time)
            planned_end = update_data.get('planned_end_time', existing_task.planned_end_time)
            due_date = update_data.get('due_date', existing_task.due_date)

            if (request.planned_start_time is not None or
                request.planned_end_time is not None or
                request.due_date is not None):
                self._validate_time_range(planned_start, planned_end, due_date)

            # 如果没有更新数据，直接返回现有任务
            if not update_data:
                logger.debug(f"任务无更新数据: {task_id}")
                return self._convert_to_response(existing_task)

            # 执行更新
            updated_task = self.repository.update(task_id, user_id, update_data)
            if not updated_task:
                raise TaskNotFoundException(
                    task_id=str(task_id),
                    user_id=str(user_id)
                )

            # 提交事务
            self.session.commit()

            logger.info(f"任务更新成功: {task_id}")
            return self._convert_to_response(updated_task)

        except Exception as e:
            # 回滚事务
            self.session.rollback()
            logger.error(f"更新任务失败: {e}")
            raise

    def delete_task(self, task_id: UUID, user_id: UUID) -> TaskDeleteResponse:
        """
        删除任务

        业务逻辑：
        1. 验证任务存在性和权限
        2. 获取所有子任务
        3. 级联软删除父任务和所有子任务
        4. 返回删除结果

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            TaskDeleteResponse: 删除操作结果

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限访问任务
        """
        try:
            logger.info(f"开始删除任务: task_id={task_id}, user_id={user_id}")

            # 验证任务存在性
            task = self.repository.get_by_id(task_id, user_id, include_deleted=False)
            if not task:
                raise TaskNotFoundException(
                    task_id=str(task_id),
                    user_id=str(user_id)
                )

            # 执行级联软删除
            deleted_count = self.repository.soft_delete_cascade(task_id, user_id)

            # 提交事务
            self.session.commit()

            # 判断是否有级联删除
            cascade_deleted = deleted_count > 1

            logger.info(f"任务删除成功: task_id={task_id}, 删除数量: {deleted_count}")

            return TaskDeleteResponse(
                deleted_task_id=task_id,
                deleted_count=deleted_count,
                cascade_deleted=cascade_deleted
            )

        except Exception as e:
            # 回滚事务
            self.session.rollback()
            logger.error(f"删除任务失败: {e}")
            raise

    def get_task_list(self, query: TaskListQuery, user_id: UUID) -> TaskListResponse:
        """
        获取任务列表

        业务逻辑：
        1. 解析查询参数
        2. 构建筛选条件
        3. 执行分页查询
        4. 返回列表和分页信息

        Args:
            query (TaskListQuery): 查询参数
            user_id (UUID): 用户ID

        Returns:
            TaskListResponse: 任务列表响应
        """
        try:
            logger.debug(f"获取任务列表: user_id={user_id}, page={query.page}")

            # 构建筛选条件
            filters = {
                'status': query.status,
                'priority': query.priority,
                'parent_id': query.parent_id,
                'include_deleted': query.include_deleted,
                'due_before': query.due_before,
                'due_after': query.due_after,
                'search': query.search
            }

            # 构建分页参数
            pagination = {
                'page': query.page,
                'page_size': query.page_size,
                'sort_by': query.sort_by,
                'sort_order': query.sort_order
            }

            # 执行查询
            result = self.repository.get_list(user_id, filters, pagination)

            # 转换任务列表
            tasks = [self._convert_to_response(task) for task in result['tasks']]

            # 构建分页信息
            pagination_info = PaginationInfo(**result['pagination'])

            logger.debug(f"任务列表获取成功: 数量={len(tasks)}, 总数={result['pagination']['total_count']}")

            return TaskListResponse(
                tasks=tasks,
                pagination=pagination_info
            )

        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            raise

    def check_circular_reference(
        self,
        task_id: UUID,
        new_parent_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        检查是否会形成循环引用

        业务逻辑：
        1. 从new_parent_id开始向上遍历
        2. 检查是否会遇到task_id
        3. 如果遇到则说明会形成循环引用

        Args:
            task_id (UUID): 要移动的任务ID
            new_parent_id (UUID): 新的父任务ID
            user_id (UUID): 用户ID

        Returns:
            bool: 如果会形成循环引用返回True，否则返回False
        """
        return self._check_circular_reference(task_id, new_parent_id, user_id)

    def _check_circular_reference(
        self,
        task_id: UUID,
        new_parent_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        内部方法：检查循环引用

        使用递归算法检查将task_id设置为new_parent_id的子任务是否会形成循环引用。

        Args:
            task_id (UUID): 要移动的任务ID
            new_parent_id (UUID): 新的父任务ID
            user_id (UUID): 用户ID

        Returns:
            bool: 如果会形成循环引用返回True
        """
        try:
            visited = set()
            current_id = new_parent_id

            while current_id and current_id not in visited:
                if current_id == task_id:
                    return True  # 检测到循环引用

                visited.add(current_id)

                # 获取当前任务的父任务
                current_task = self.repository.get_by_id(current_id, user_id)
                if not current_task:
                    break  # 父任务不存在，不会形成循环

                current_id = current_task.parent_id

            return False

        except Exception as e:
            logger.error(f"检查循环引用失败: {e}")
            # 出错时为了安全，返回True（阻止操作）
            return True

    def _validate_time_range(
        self,
        planned_start_time: Optional[datetime],
        planned_end_time: Optional[datetime],
        due_date: Optional[datetime]
    ) -> None:
        """
        验证时间范围的合理性

        验证规则：
        1. 如果同时设置了开始和结束时间，结束时间必须晚于开始时间
        2. 如果设置了截止日期和结束时间，截止日期不能早于结束时间

        Args:
            planned_start_time (Optional[datetime]): 计划开始时间
            planned_end_time (Optional[datetime]): 计划结束时间
            due_date (Optional[datetime]): 截止日期

        Raises:
            InvalidTimeRangeException: 时间范围无效
        """
        # 检查计划时间范围
        if planned_start_time and planned_end_time:
            if planned_end_time <= planned_start_time:
                raise InvalidTimeRangeException(
                    start_time=planned_start_time.isoformat(),
                    end_time=planned_end_time.isoformat(),
                    reason="计划结束时间必须晚于计划开始时间"
                )

        # 检查截止日期与计划结束时间
        if due_date and planned_end_time:
            if due_date < planned_end_time:
                raise InvalidTimeRangeException(
                    end_time=planned_end_time.isoformat(),
                    due_date=due_date.isoformat(),
                    reason="截止日期不能早于计划结束时间"
                )

    def _convert_to_response(self, task: Task) -> TaskResponse:
        """
        将Task实体转换为TaskResponse

        Args:
            task (Task): 任务实体

        Returns:
            TaskResponse: 任务响应
        """
        return TaskResponse(
            id=task.id,
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            parent_id=task.parent_id,
            tags=task.tags or [],
            due_date=task.due_date,
            planned_start_time=task.planned_start_time,
            planned_end_time=task.planned_end_time,
            is_deleted=task.is_deleted,
            created_at=task.created_at,
            updated_at=task.updated_at,
            is_overdue=task.is_overdue,
            duration_minutes=task.duration_minutes
        )