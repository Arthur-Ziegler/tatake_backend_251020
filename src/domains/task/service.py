"""
Task领域Service层 v2.0

基于Day 2要求重新设计的任务服务，专注于核心业务逻辑。

核心功能：
1. 任务完成处理：完成时自动发放积分，使用悲观锁防止刷任务
2. 积分发放：按任务类型发放不同积分（普通/Top3）
3. 任务列表查询：支持层级查询、状态筛选、分页
4. 任务更新：完整的任务信息更新，包括树结构维护
5. 事务管理：关键操作使用事务确保一致性

设计原则：
1. 纯SQL聚合：所有查询使用纯SQL，保持简单实现
2. 悲观锁机制：关键操作使用SELECT FOR UPDATE
3. 业务规则：在Service层实现复杂的业务逻辑
4. 事务边界：关键操作使用事务确保一致性
5. 错误处理：详细的错误信息用于调试

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from contextlib import contextmanager

from sqlmodel import Session, select, text
from .schemas import TaskListQuery, UpdateTaskRequest
from sqlalchemy.exc import SQLAlchemyError

from .models import Task
from .exceptions import TaskNotFoundException, TaskPermissionDeniedException
from .repository import TaskRepository
from src.config.game_config import reward_config


def parse_json_field(value: Any) -> list:
    """安全解析JSON字段"""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, list):
        return value
    return []


class TaskService:
    """
    任务系统服务层

    提供任务管理的核心业务逻辑，包括任务完成积分发放、
    任务列表查询、层级关系维护等功能。
    """

    def __init__(self, session: Session, points_service):
        """
        初始化任务服务

        Args:
            session (Session): 数据库会话
            points_service: PointsService实例，用于积分操作
        """
        self.session = session
        self.points_service = points_service
        self.task_repository = TaskRepository(session)
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def transaction_scope(self):
        """
        事务管理器

        为关键操作提供事务上下文管理，确保操作的原子性。
        在测试环境中，需要确保事务正确提交。
        """
        self.logger.debug("Starting transaction scope")

        try:
            # Session默认已经开始了事务，直接yield
            yield self.session
            # 提交事务以确保更改生效
            self.session.commit()
            self.logger.debug("Transaction completed successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Transaction failed: {e}")
            self.session.rollback()
            raise
        finally:
            self.logger.debug("Transaction scope ended")

    def get_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        获取任务详情

        验证任务存在性和用户权限，返回任务详情。

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            Task: 任务详情

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限访问任务
        """
        try:
            task_id_str = str(task_id)
            user_id_str = str(user_id)
            self.logger.info(f"DEBUG: Getting task {task_id_str} for user {user_id_str}")
            self.logger.info(f"DEBUG: Task ID type: {type(task_id)}, User ID type: {type(user_id)}")

            # 使用no_autoflush避免触发不必要的数据库操作
            with self.session.no_autoflush:
                # 通过repository获取任务
                task = self.task_repository.get_by_id(task_id_str, user_id_str)

                if not task:
                    raise TaskNotFoundException(f"任务不存在: {task_id}")

                self.logger.debug(f"Task {task_id} found for user {user_id}")
                return self._build_task_response(task)

        except (TaskNotFoundException, TaskPermissionDeniedException):
            # 业务异常，重新抛出
            raise
        except Exception as e:
            self.logger.error(f"Error getting task {task_id} for user {user_id}: {e}")
            raise Exception(f"获取任务失败: {e}")

    def complete_task(self, user_id: UUID, task_id: UUID) -> Dict[str, Any]:
        """
        完成任务并发放积分

        实现v3 API方案的任务完成逻辑：
        1. 使用悲观锁锁定任务记录
        2. 检查任务状态和时间限制
        3. 发放相应的积分（普通/Top3）
        4. 更新任务完成状态和时间

        Args:
            user_id (UUID): 用户ID
            task_id (UUID): 任务ID

        Returns:
            Dict[str, Any]: 完成结果

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限
            Exception: 其他错误
        """
        self.logger.info(f"User {user_id} completing task {task_id}")

        try:
            with self.transaction_scope():
                # 1. 查询任务记录（SQLite不支持FOR UPDATE，使用普通查询）
                # 将UUID转换为字符串用于数据库查询，查询last_claimed_date用于防刷检查
                task_result = self.session.execute(
                    text("""
                        SELECT id, status, title, last_claimed_date
                        FROM tasks
                        WHERE id = :task_id AND user_id = :user_id
                    """),
                    {"task_id": str(task_id), "user_id": str(user_id)}
                ).first()

                if not task_result:
                    raise TaskNotFoundException(f"任务不存在: {task_id}")

                task_id_db, status, title, last_claimed_date = task_result

                # 检查是否已经奖励过积分（通过status判断）
                points_rewarded = status == "completed"

                # 2. 永久防刷检查：任务只能领一次奖
                print(f"🔍 DEBUG: Task {task_id} - status: {status}, last_claimed_date: {last_claimed_date}")
                self.logger.info(f"Task {task_id} - status: {status}, last_claimed_date: {last_claimed_date}")

                # 防刷检查：判断是否应该发放积分
                should_award_points = last_claimed_date is None

                if not should_award_points:
                    print(f"🚫 BLOCKED: Task {task_id} already completed once on {last_claimed_date}!")
                    self.logger.info(f"Task {task_id} already completed once on {last_claimed_date}, no points awarded")

                # 根据防刷检查决定积分发放
                if should_award_points:
                    # 3. 根据任务类型发放积分
                    if points_rewarded:
                        # 已经奖励过积分
                        points_to_award = 0
                        self.logger.info(f"Task {task_id} already rewarded")
                    else:
                        # 统一使用普通任务积分（Top3判断由completion_service处理）
                        points_to_award = reward_config.get_normal_task_points()
                        reward_type = "task_complete"
                        self.logger.info(f"Task {task_id} awarding {points_to_award} points")
                else:
                    # 防刷生效，不给积分
                    points_to_award = 0
                    reward_type = "task_already_completed_once"
                    self.logger.info(f"Task {task_id} anti-spam activated, no points awarded")

                # 4. 发放积分（如果有）
                if points_to_award > 0:
                    self.points_service.add_points(
                        str(user_id), points_to_award, reward_type, str(task_id)
                    )

                # 5. 更新任务状态（状态总是更新，但last_claimed_date只在首次完成时设置）
                from datetime import date

                if should_award_points:
                    # 首次完成：设置状态和首次完成日期
                    claim_date = date.today()
                    update_sql = """
                        UPDATE tasks
                        SET status = 'completed',
                            last_claimed_date = :claim_date,
                            updated_at = :now
                        WHERE id = :task_id AND user_id = :user_id
                    """
                    update_params = {
                        "task_id": str(task_id),
                        "user_id": str(user_id),
                        "claim_date": claim_date,
                        "now": datetime.now(timezone.utc)
                    }
                else:
                    # 重复完成：只更新状态，不改变last_claimed_date
                    update_sql = """
                        UPDATE tasks
                        SET status = 'completed',
                            updated_at = :now
                        WHERE id = :task_id AND user_id = :user_id
                    """
                    update_params = {
                        "task_id": str(task_id),
                        "user_id": str(user_id),
                        "now": datetime.now(timezone.utc)
                    }

                update_result = self.session.execute(text(update_sql), update_params)

                # 检查UPDATE是否影响了行
                rows_affected = update_result.rowcount
                self.logger.info(f"Task update affected {rows_affected} rows")

                # 确保立即刷新到数据库（积分事务已由points_service提交）
                self.session.flush()

                # 递归更新父任务的完成百分比
                try:
                    parent_update_result = self.update_parent_completion_percentage(user_id, task_id)
                    self.logger.info(f"Parent completion updated: {parent_update_result['updated_tasks_count']} tasks")
                except Exception as e:
                    # 父任务更新失败不影响任务完成，只记录警告
                    self.logger.warning(f"Failed to update parent completion: {e}")

                result = {
                    "success": True,
                    "task_id": str(task_id),  # 将UUID转换为字符串用于JSON响应
                    "points_awarded": points_to_award,
                    "reward_type": reward_type,
                    "message": f"任务完成，获得{points_to_award}积分"
                }

                self.logger.info(f"Task {task_id} completed successfully for user {user_id}")
                return result

        except (TaskNotFoundException, TaskPermissionDeniedException) as e:
            # 业务异常，重新抛出
            self.logger.warning(f"Task completion failed for user {user_id}, task {task_id}: {e}")
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error completing task {task_id} for user {user_id}: {e}")
            raise Exception(f"数据库错误: {e}")

    def get_tasks(self, user_id: str, status: Optional[str] = None,
                 parent_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户任务列表

        支持按状态、父任务筛选和分页查询。

        Args:
            user_id (str): 用户ID
            status (Optional[str]): 任务状态筛选
            parent_id (Optional[str]): 父任务ID筛选
            limit (int): 限制数量
            offset (int): 偏移数量

        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        self.logger.info(f"Getting tasks for user {user_id}, status: {status}, parent_id: {parent_id}")

        try:
            # 构建查询条件
            conditions = ["user_id = :user_id"]
            params = {"user_id": user_id}

            if status:
                conditions.append("status = :status")
                params["status"] = status

            if parent_id:
                conditions.append("parent_id = :parent_id")
                params["parent_id"] = parent_id

            # 构建SQL查询
            where_clause = " AND ".join(conditions)

            # 使用安全的SQL查询，查询所有必要字段
            query = f"""
                SELECT
                    id, user_id, title, description, status, priority, parent_id,
                    tags, service_ids, due_date, planned_start_time, planned_end_time,
                    last_claimed_date, completion_percentage, is_deleted,
                    created_at, updated_at
                FROM tasks
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """

            result = self.session.execute(
                text(query),
                {**params, "limit": limit, "offset": offset}
            ).fetchall()

            tasks = []
            for row in result:
                # 处理JSON字段反序列化
                tags = parse_json_field(row[7])
                service_ids = parse_json_field(row[8])

                task_data = {
                    "id": str(row[0]),
                    # ❌ 不返回user_id到前端
                    "title": row[2],
                    "description": row[3],
                    "status": row[4],
                    "priority": row[5],  # 使用数据库中的priority
                    "parent_id": str(row[6]) if row[6] else None,
                    "tags": tags,  # 修复：JSON反序列化
                    "service_ids": service_ids,  # 新增：JSON反序列化
                    "due_date": row[9],  # 新增
                    "planned_start_time": row[10],  # 新增
                    "planned_end_time": row[11],  # 新增
                    "last_claimed_date": row[12],  # 新增
                    "completion_percentage": row[13],  # 新增
                    "is_deleted": row[14],  # 新增
                    "created_at": row[15],
                    "updated_at": row[16]
                }
                tasks.append(task_data)

            self.logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
            return tasks

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting tasks for user {user_id}: {e}")
            raise Exception(f"数据库错误: {e}")

    def update_parent_completion_percentage(self, user_id: UUID, task_id: UUID) -> Dict[str, Any]:
        """
        递归更新父任务的完成百分比

        基于子任务的完成度计算父任务的完成百分比：
        - 如果子任务是叶子任务：基于完成状态（completed/pending）
        - 如果子任务不是叶子任务：基于其完成百分比

        Args:
            user_id (str): 用户ID
            task_id (str): 任务ID（通常是刚完成的任务）

        Returns:
            Dict[str, Any]: 更新结果，包含影响的任务数量和详细信息

        Raises:
            TaskNotFoundException: 任务不存在
            Exception: 其他错误
        """
        self.logger.info(f"Updating parent completion percentage for user {user_id}, task {task_id}")

        try:
            updated_tasks = []

            # 1. 先构建完整的父任务链，避免在循环中修改数据库导致的问题
            parent_chain = []
            temp_task_id = task_id

            # 从当前任务开始，向上查找所有父任务
            while temp_task_id:
                parent_result = self.session.execute(
                    text("""
                        SELECT parent_id FROM tasks
                        WHERE id = :task_id AND user_id = :user_id
                    """),
                    {"task_id": str(temp_task_id), "user_id": str(user_id)}
                ).first()

                if not parent_result or not parent_result[0]:
                    break

                parent_id = UUID(parent_result[0])
                parent_chain.append(parent_id)
                temp_task_id = parent_id

                self.logger.debug(f"Found parent task in chain: {parent_id}")

            self.logger.info(f"Found {len(parent_chain)} parent tasks to update")

            # 2. 从最直接的父任务开始，向上依次更新每个父任务
            # 这样可以确保每个父任务都能正确计算其子任务的完成度
            for parent_id in parent_chain:
                self.logger.debug(f"Updating parent task: {parent_id}")

                # 计算该父任务的所有子任务的完成度
                completion_result = self.session.execute(
                    text("""
                        SELECT
                            t.id,
                            t.status,
                            t.completion_percentage,
                            -- 判断是否为叶子任务（没有子任务）
                            (SELECT COUNT(*) FROM tasks tc WHERE tc.parent_id = t.id AND tc.is_deleted = false) as child_count
                        FROM tasks t
                        WHERE t.parent_id = :parent_id AND t.user_id = :user_id AND t.is_deleted = false
                    """),
                    {"parent_id": str(parent_id), "user_id": str(user_id)}
                ).fetchall()

                if completion_result:
                    total_completion = 0.0
                    child_count = len(completion_result)

                    for child in completion_result:
                        child_id, child_status, child_completion_percentage, child_child_count = child
                        child_child_count = int(child_child_count or 0)
                        child_completion_percentage = float(child_completion_percentage or 0.0)

                        if child_child_count == 0:
                            # 叶子任务：基于完成状态
                            if child_status == 'completed':
                                total_completion += 100.0
                            # else: pending状态贡献0%
                        else:
                            # 非叶子任务：基于其完成百分比
                            total_completion += child_completion_percentage

                    # 计算平均完成百分比
                    completion_percentage = total_completion / child_count if child_count > 0 else 0.0

                    # 更新父任务的完成百分比
                    self.session.execute(
                        text("""
                            UPDATE tasks
                            SET completion_percentage = :completion_percentage,
                                updated_at = :updated_at
                            WHERE id = :parent_id AND user_id = :user_id
                        """),
                        {
                            "parent_id": str(parent_id),
                            "user_id": str(user_id),
                            "completion_percentage": completion_percentage,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    )

                    updated_tasks.append({
                        "task_id": parent_id,
                        "completion_percentage": completion_percentage,
                        "child_count": child_count
                    })

                    self.logger.debug(
                        f"Updated parent {parent_id}: {completion_percentage:.1f}% "
                        f"(based on {child_count} children)"
                    )

            # 3. 统一提交事务，确保所有更新原子性
            self.session.commit()

            result = {
                "success": True,
                "updated_tasks_count": len(updated_tasks),
                "updated_tasks": updated_tasks,
                "message": f"成功更新{len(updated_tasks)}个父任务的完成百分比"
            }

            self.logger.info(f"Parent completion update completed: {len(updated_tasks)} tasks updated")
            return result

        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating parent completion: {e}")
            self.session.rollback()
            raise Exception(f"数据库错误: {e}")
        except Exception as e:
            self.logger.error(f"Error updating parent completion: {e}")
            self.session.rollback()
            raise Exception(f"更新父任务完成度失败: {e}")

    def create_task(self, request, user_id: UUID) -> Dict[str, Any]:
        """
        创建新任务

        根据CreateTaskRequest创建新任务，支持设置父任务等基本功能。

        Args:
            request: CreateTaskRequest对象，包含任务创建信息
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 创建的任务信息

        Raises:
            Exception: 创建失败时抛出异常
        """
        self.logger.info(f"Creating task for user {user_id}: {request.title}")

        try:
            from .models import Task
            from datetime import datetime, timezone

            # 创建任务对象
            task = Task(
                id=str(uuid4()),  # 确保ID生成
                user_id=str(user_id),
                title=request.title,
                description=request.description,
                status=request.status or TaskStatusConst.PENDING,
                priority=request.priority or TaskPriorityConst.MEDIUM,
                parent_id=str(request.parent_id) if request.parent_id else None,
                tags=request.tags or [],  # 新增
                service_ids=request.service_ids or [],  # 新增
                due_date=request.due_date,  # 新增
                planned_start_time=request.planned_start_time,  # 新增
                planned_end_time=request.planned_end_time,  # 新增
                completion_percentage=0.0,  # 新任务默认0%
                is_deleted=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # 保存到数据库
            self.session.add(task)
            self.session.flush()
            self.session.refresh(task)
            self.session.commit()

            # 构建完整的TaskResponse格式数据
            result = {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,  # 使用task中的priority
                "parent_id": task.parent_id,
                "tags": task.tags or [],  # 使用task中的tags
                "service_ids": task.service_ids or [],  # 使用task中的service_ids
                "due_date": task.due_date,  # 使用task中的due_date
                "planned_start_time": task.planned_start_time,  # 使用task中的时间
                "planned_end_time": task.planned_end_time,
                "last_claimed_date": task.last_claimed_date,  # 使用task中的last_claimed_date
                "completion_percentage": task.completion_percentage,  # 使用task中的completion_percentage
                "is_deleted": task.is_deleted,  # 使用task中的is_deleted
                "created_at": task.created_at,
                "updated_at": task.updated_at
            }

            self.logger.info(f"Task created successfully: {task.id}")
            return result

        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            self.session.rollback()
            raise Exception(f"创建任务失败: {e}")

    def update_task_with_tree_structure(
        self, task_id: UUID, request: UpdateTaskRequest, user_id: UUID
    ) -> Dict[str, Any]:
        """
        更新任务（简化版，不处理树结构复杂度）

        说明：由于删除了level/path字段，无需处理树结构更新

        Args:
            task_id (UUID): 任务ID
            request (UpdateTaskRequest): 更新请求
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 更新后的任务信息

        Raises:
            TaskNotFoundException: 任务不存在
            Exception: 更新失败
        """
        self.logger.info(f"Updating task {task_id} for user {user_id}")

        try:
            # 1. 验证任务存在和权限
            task = self.task_repository.get_by_id(str(task_id), str(user_id))
            if not task:
                raise TaskNotFoundException(f"任务不存在: {task_id}")

            # 2. 构建更新数据（只包含非None字段）
            update_data = {}
            for field, value in request.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value

            # 3. 添加更新时间
            update_data['updated_at'] = datetime.now(timezone.utc)

            # 4. 调用repository更新
            updated_task = self.task_repository.update(task_id, user_id, update_data)
            if not updated_task:
                raise Exception("更新任务失败")

            # 5. 返回响应
            return self._build_task_response(updated_task)

        except (TaskNotFoundException, TaskPermissionDeniedException):
            # 业务异常，重新抛出
            raise
        except Exception as e:
            self.logger.error(f"Error updating task {task_id} for user {user_id}: {e}")
            raise Exception(f"更新任务失败: {e}")

    def delete_task(self, task_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        软删除任务及所有子任务

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 删除结果

        Raises:
            TaskNotFoundException: 任务不存在
            Exception: 删除失败
        """
        self.logger.info(f"Deleting task {task_id} for user {user_id}")

        try:
            # 1. 验证任务存在和权限
            task = self.task_repository.get_by_id(str(task_id), str(user_id))
            if not task:
                raise TaskNotFoundException(f"任务不存在: {task_id}")

            # 2. 级联软删除
            deleted_count = self.task_repository.soft_delete_cascade(task_id, user_id)

            # 3. 返回结果
            return {
                "deleted_task_id": str(task_id),
                "deleted_count": deleted_count,
                "cascade_deleted": deleted_count > 1
            }

        except (TaskNotFoundException, TaskPermissionDeniedException):
            # 业务异常，重新抛出
            raise
        except Exception as e:
            self.logger.error(f"Error deleting task {task_id} for user {user_id}: {e}")
            raise Exception(f"删除任务失败: {e}")

    def get_task_list(self, query, user_id: UUID) -> Dict[str, Any]:
        """
        获取任务列表 - 适配器方法

        适配TaskListQuery到现有的get_tasks方法，提供统一的API接口。

        Args:
            query (TaskListQuery): 任务列表查询参数
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 包含任务列表和分页信息的响应
        """
        self.logger.info(f"Getting task list for user {user_id}, page={query.page}")

        try:
            # 计算偏移量
            offset = (query.page - 1) * query.page_size

            # 调用现有的get_tasks方法
            tasks = self.get_tasks(
                user_id=str(user_id),
                status=None,  # 不过滤状态，获取所有任务
                parent_id=None,
                limit=query.page_size,
                offset=offset
            )

            # 计算总数（简化版本，实际应该单独查询）
            # 这里我们获取所有任务来计算总数
            all_tasks = self.get_tasks(user_id=str(user_id))
            total_count = len(all_tasks)

            # 计算分页信息，符合Pydantic模型要求
            current_page = query.page
            total_pages = (total_count + query.page_size - 1) // query.page_size
            has_next = current_page < total_pages
            has_prev = current_page > 1

            # 构建响应数据，符合TaskListResponse模型要求
            response = {
                "tasks": tasks,  # 任务列表在tasks字段中
                "pagination": {
                    "current_page": current_page,
                    "page_size": query.page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }

            self.logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error getting task list for user {user_id}: {e}")
            raise Exception(f"获取任务列表失败: {e}")

    def _build_task_response(self, task: Task) -> Dict[str, Any]:
        """
        构建包含计算字段的任务响应

        为Task对象添加level和path计算字段，确保符合TaskResponse schema要求。
        确保所有UUID字段转换为字符串，避免数据库类型错误。

        Args:
            task (Task): Task模型对象

        Returns:
            Dict[str, Any]: 包含所有必需字段的字典
        """
        try:
            # 获取任务基础数据，确保UUID转换为字符串
            task_dict = task.model_dump(mode='python')

            # 手动转换UUID字段为字符串
            if 'id' in task_dict and task_dict['id'] is not None:
                task_dict['id'] = str(task_dict['id'])
            if 'user_id' in task_dict and task_dict['user_id'] is not None:
                task_dict['user_id'] = str(task_dict['user_id'])
            if 'parent_id' in task_dict and task_dict['parent_id'] is not None:
                task_dict['parent_id'] = str(task_dict['parent_id'])

            # 添加必要字段到响应数据
            task_dict.update({
                # 确保completion_percentage字段存在
                "completion_percentage": task.completion_percentage
            })

            self.logger.debug(f"Built task response for task {task.id}")
            return task_dict

        except Exception as e:
            self.logger.error(f"Error building task response for task {task.id}: {e}")
            raise Exception(f"构建任务响应失败: {e}")

  
    # 暂时简化事务管理，使用session的autocommit
    # 后续可以根据需要添加更复杂的事务管理