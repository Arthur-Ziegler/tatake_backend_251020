"""
任务服务模块

该模块实现任务管理相关的业务逻辑，包括任务CRUD操作、任务状态管理、
任务层次结构管理、Top3任务管理等功能。提供完整的任务生命周期管理。

设计原则：
1. 层次结构：支持无限层级的任务树结构
2. 状态管理：严格的任务状态流转控制
3. 业务规则：实现完整的任务业务规则验证
4. 性能优化：高效的任务查询和更新机制
5. 异常处理：详细的错误信息和处理建议

核心功能：
- 任务CRUD操作
- 任务状态转换管理
- 任务层次结构管理
- 任务完成逻辑（包含抽奖机制）
- Top3任务管理
- 任务搜索和筛选
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    InsufficientBalanceException
)
from src.models.task import Task
from src.models.enums import TaskStatus, PriorityLevel


class TaskService(BaseService):
    """
    任务服务类

    处理任务管理相关的所有业务逻辑，包括任务创建、更新、删除、
    状态管理、层次结构管理等核心功能。

    Attributes:
        _user_repo: 用户数据访问对象
        _task_repo: 任务数据访问对象
        _focus_repo: 专注数据访问对象
        _reward_repo: 奖励数据访问对象
    """

    def __init__(self, user_repo, task_repo, focus_repo=None, reward_repo=None, **kwargs):
        """
        初始化任务服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            **kwargs
        )

    # ==================== 任务CRUD操作 ====================

    def create_task(self, user_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建任务

        创建新的任务，支持设置父任务形成层次结构。
        进行数据验证和业务规则检查。

        Args:
            user_id: 用户ID
            task_data: 任务数据

        Returns:
            创建的任务信息

        Raises:
            ResourceNotFoundException: 当用户或父任务不存在时
            ValidationException: 当数据无效时
            DuplicateResourceException: 当任务重复时
        """
        try:
            self._log_info("开始创建任务", {
                "user_id": user_id,
                "task_title": task_data.get("title", "")
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证和清理任务数据
            validated_data = self._validate_task_data(task_data, is_create=True)

            # 设置任务基础信息
            validated_data.update({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "status": TaskStatus.PENDING,
                "is_top3": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })

            # 验证父任务（如果存在）
            parent_id = validated_data.get("parent_id")
            if parent_id:
                self._validate_parent_task(user_id, parent_id)

            # 创建任务
            created_task = self.get_task_repository().create(validated_data)

            # 计算并更新父任务的完成度
            if parent_id:
                self._update_parent_completion_progress(parent_id)

            # 返回任务信息
            result = self._task_to_dict(created_task)

            self._log_info("任务创建成功", {
                "task_id": created_task.id,
                "user_id": user_id,
                "title": created_task.title
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "create_task", {
                "user_id": user_id,
                "task_data": task_data
            })

    def get_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """
        获取任务详情

        获取指定任务的详细信息，包括子任务统计。

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            任务详细信息

        Raises:
            ResourceNotFoundException: 当任务不存在时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("获取任务详情", {
                "task_id": task_id,
                "user_id": user_id
            })

            # 获取任务信息
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            # 验证用户权限
            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:read",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 获取子任务统计
            children_stats = self._get_children_statistics(task_id)

            # 构建完整任务信息
            result = self._task_to_dict(task)
            result["children_statistics"] = children_stats

            self._log_info("任务详情获取成功", {
                "task_id": task_id,
                "user_id": user_id
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_task", {
                "task_id": task_id,
                "user_id": user_id
            })

    def update_task(self, task_id: str, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新任务信息

        更新任务的基本信息，如标题、描述、优先级等。
        进行数据验证和权限检查。

        Args:
            task_id: 任务ID
            user_id: 用户ID
            update_data: 更新数据

        Returns:
            更新后的任务信息

        Raises:
            ResourceNotFoundException: 当任务不存在时
            ValidationException: 当数据无效时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("更新任务信息", {
                "task_id": task_id,
                "user_id": user_id,
                "update_fields": list(update_data.keys())
            })

            # 获取任务信息
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            # 验证用户权限
            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:update",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 已完成的任务不允许修改某些字段
            if task.status == TaskStatus.COMPLETED:
                restricted_fields = {"title", "description", "parent_id"}
                update_fields = set(update_data.keys())
                if restricted_fields.intersection(update_fields):
                    raise ValidationException(
                        message="已完成的任务不允许修改基本信息",
                        details={"restricted_fields": list(restricted_fields.intersection(update_fields))}
                    )

            # 验证更新数据
            validated_data = self._validate_task_data(update_data, is_create=False)

            # 验证父任务变更（如果存在）
            new_parent_id = validated_data.get("parent_id")
            if new_parent_id and new_parent_id != task.parent_id:
                self._validate_parent_task(user_id, new_parent_id, exclude_task_id=task_id)

            # 添加更新时间
            validated_data["updated_at"] = datetime.now()

            # 更新任务
            updated_task = self.get_task_repository().update(task_id, validated_data)

            # 如果父任务发生变化，更新原父任务和新父任务的完成度
            old_parent_id = task.parent_id
            if old_parent_id and old_parent_id != new_parent_id:
                self._update_parent_completion_progress(old_parent_id)
            if new_parent_id and new_parent_id != old_parent_id:
                self._update_parent_completion_progress(new_parent_id)

            result = self._task_to_dict(updated_task)

            self._log_info("任务更新成功", {
                "task_id": task_id,
                "user_id": user_id,
                "updated_fields": list(validated_data.keys())
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "update_task", {
                "task_id": task_id,
                "user_id": user_id,
                "update_data": update_data
            })

    def delete_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """
        删除任务

        软删除任务，标记为已删除状态。
        如果任务有子任务，需要先处理子任务。

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            删除结果

        Raises:
            ResourceNotFoundException: 当任务不存在时
            ValidationException: 当任务有子任务时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("删除任务", {
                "task_id": task_id,
                "user_id": user_id
            })

            # 获取任务信息
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            # 验证用户权限
            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:delete",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 检查是否有子任务
            if self._has_children(task_id):
                raise ValidationException(
                    message="存在子任务的任务不能删除，请先删除所有子任务",
                    details={"task_id": task_id}
                )

            # 软删除任务
            update_data = {
                "status": TaskStatus.DELETED,
                "updated_at": datetime.now()
            }

            self.get_task_repository().update(task_id, update_data)

            # 更新父任务的完成度
            if task.parent_id:
                self._update_parent_completion_progress(task.parent_id)

            result = {
                "success": True,
                "message": "任务删除成功",
                "task_id": task_id
            }

            self._log_info("任务删除成功", {
                "task_id": task_id,
                "user_id": user_id
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "delete_task", {
                "task_id": task_id,
                "user_id": user_id
            })

    # ==================== 任务状态管理 ====================

    def complete_task(self, task_id: str, user_id: str, mood_feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        标记任务完成

        将任务标记为已完成状态，记录心情反馈，
        触发积分奖励和抽奖机制。

        Args:
            task_id: 任务ID
            user_id: 用户ID
            mood_feedback: 心情反馈（可选）

        Returns:
            完成结果和奖励信息

        Raises:
            ResourceNotFoundException: 当任务不存在时
            ValidationException: 当任务状态不允许完成时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("标记任务完成", {
                "task_id": task_id,
                "user_id": user_id,
                "mood_feedback": mood_feedback
            })

            # 获取任务信息
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            # 验证用户权限
            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:complete",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 验证任务状态
            if task.status != TaskStatus.PENDING and task.status != TaskStatus.IN_PROGRESS:
                raise ValidationException(
                    message="只有待处理或进行中的任务可以标记为完成",
                    details={"current_status": task.status.value}
                )

            # 检查是否有未完成的子任务
            if self._has_incomplete_children(task_id):
                raise ValidationException(
                    message="存在未完成的子任务，请先完成所有子任务",
                    details={"task_id": task_id}
                )

            # 更新任务状态为已完成
            update_data = {
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now(),
                "updated_at": datetime.now()
            }

            if mood_feedback:
                update_data["mood_feedback"] = mood_feedback

            completed_task = self.get_task_repository().update(task_id, update_data)

            # 计算任务奖励
            rewards = self._calculate_task_rewards(task)

            # 发放奖励
            if rewards["points"] > 0 or rewards["fragments"] > 0:
                self._grant_task_rewards(user_id, task_id, rewards)

            # 执行抽奖（如果有资格）
            lottery_result = None
            if self._is_eligible_for_lottery(task):
                lottery_result = self._execute_lottery(user_id, task_id)

            # 更新父任务的完成度
            if task.parent_id:
                self._update_parent_completion_progress(task.parent_id)

            # 构建结果
            result = {
                "task": self._task_to_dict(completed_task),
                "rewards": rewards,
                "lottery_result": lottery_result
            }

            self._log_info("任务完成成功", {
                "task_id": task_id,
                "user_id": user_id,
                "points_awarded": rewards["points"],
                "fragments_awarded": rewards["fragments"]
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "complete_task", {
                "task_id": task_id,
                "user_id": user_id
            })

    def uncomplete_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """
        取消任务完成状态

        将已完成的任务状态回滚到待处理或进行中状态。

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            取消完成结果

        Raises:
            ResourceNotFoundException: 当任务不存在时
            ValidationException: 当任务状态不允许取消完成时
            AuthorizationException: 当用户无权访问时
        """
        try:
            self._log_info("取消任务完成状态", {
                "task_id": task_id,
                "user_id": user_id
            })

            # 获取任务信息
            task = self._check_resource_exists(
                self.get_task_repository(),
                task_id,
                "任务"
            )

            # 验证用户权限
            if task.user_id != user_id:
                raise AuthorizationException(
                    required_permission="task:uncomplete",
                    user_id=user_id,
                    resource_id=task_id
                )

            # 验证任务状态
            if task.status != TaskStatus.COMPLETED:
                raise ValidationException(
                    message="只有已完成的任务可以取消完成状态",
                    details={"current_status": task.status.value}
                )

            # 检查时间限制（完成24小时后不允许取消）
            if task.completed_at:
                time_diff = datetime.now() - task.completed_at
                if time_diff > timedelta(hours=24):
                    raise ValidationException(
                        message="任务完成超过24小时后不允许取消完成状态",
                        details={"completed_at": task.completed_at.isoformat()}
                    )

            # 回滚任务状态
            update_data = {
                "status": TaskStatus.IN_PROGRESS,
                "completed_at": None,
                "updated_at": datetime.now()
            }

            updated_task = self.get_task_repository().update(task_id, update_data)

            # TODO: 回滚任务奖励（如果有）
            # 这里需要实现奖励回滚逻辑

            # 更新父任务的完成度
            if task.parent_id:
                self._update_parent_completion_progress(task.parent_id)

            result = {
                "task": self._task_to_dict(updated_task),
                "message": "任务完成状态已取消"
            }

            self._log_info("任务完成状态取消成功", {
                "task_id": task_id,
                "user_id": user_id
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "uncomplete_task", {
                "task_id": task_id,
                "user_id": user_id
            })

    # ==================== Top3任务管理 ====================

    def set_top3_tasks(self, user_id: str, task_ids: List[str]) -> Dict[str, Any]:
        """
        设定每日Top3任务

        设置用户当天的Top3重要任务，需要消耗积分。

        Args:
            user_id: 用户ID
            task_ids: Top3任务ID列表（最多3个）

        Returns:
            设置结果

        Raises:
            ResourceNotFoundException: 当用户或任务不存在时
            ValidationException: 当参数无效时
            InsufficientBalanceException: 当积分不足时
        """
        try:
            self._log_info("设定Top3任务", {
                "user_id": user_id,
                "task_count": len(task_ids)
            })

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证参数
            if len(task_ids) > 3:
                raise ValidationException(
                    message="Top3任务最多只能设置3个",
                    details={"task_count": len(task_ids)}
                )

            if len(task_ids) == 0:
                raise ValidationException(
                    message="Top3任务至少需要设置1个",
                    details={"task_count": len(task_ids)}
                )

            # 检查今天是否已经设置过Top3
            today = datetime.now().date()
            if self._has_top3_today(user_id, today):
                raise ValidationException(
                    message="今天已经设置过Top3任务，每天只能设置一次",
                    details={"date": today.isoformat()}
                )

            # 验证任务存在且属于该用户
            validated_tasks = []
            for task_id in task_ids:
                task = self._check_resource_exists(
                    self.get_task_repository(),
                    task_id,
                    "任务"
                )

                if task.user_id != user_id:
                    raise AuthorizationException(
                        required_permission="task:set_top3",
                        user_id=user_id,
                        resource_id=task_id
                    )

                validated_tasks.append(task)

            # 检查用户积分是否足够（需要300积分）
            current_points = getattr(user, 'points', 0)
            if current_points < 300:
                raise InsufficientBalanceException(
                    current_balance=current_points,
                    required_amount=300,
                    balance_type="积分"
                )

            # 消耗积分
            # TODO: 调用UserService的方法来消耗积分
            # self.user_service.consume_user_points(user_id, 300, "设置Top3任务", "top3_setting")

            # 设置Top3任务
            top3_date = today.isoformat()
            self._set_top3_tasks_for_date(user_id, top3_date, task_ids)

            # 构建结果
            result = {
                "success": True,
                "date": top3_date,
                "top3_tasks": [self._task_to_dict(task) for task in validated_tasks],
                "points_consumed": 300
            }

            self._log_info("Top3任务设置成功", {
                "user_id": user_id,
                "date": top3_date,
                "task_count": len(task_ids)
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "set_top3_tasks", {
                "user_id": user_id,
                "task_ids": task_ids
            })

    def get_top3_tasks(self, user_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取Top3任务

        获取指定日期的Top3任务列表。

        Args:
            user_id: 用户ID
            date: 日期（YYYY-MM-DD格式），默认为今天

        Returns:
            Top3任务列表

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当日期格式无效时
        """
        try:
            self._log_info("获取Top3任务", {
                "user_id": user_id,
                "date": date or "today"
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 处理日期参数
            if date:
                try:
                    target_date = datetime.fromisoformat(date).date()
                except ValueError:
                    raise ValidationException(
                        message="日期格式无效，请使用YYYY-MM-DD格式",
                        details={"date": date}
                    )
            else:
                target_date = datetime.now().date()

            # 获取Top3任务
            top3_tasks = self._get_top3_tasks_for_date(user_id, target_date.isoformat())

            result = {
                "date": target_date.isoformat(),
                "top3_tasks": top3_tasks
            }

            self._log_info("Top3任务获取成功", {
                "user_id": user_id,
                "date": target_date.isoformat(),
                "task_count": len(top3_tasks)
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_top3_tasks", {
                "user_id": user_id,
                "date": date
            })

    # ==================== 任务搜索和筛选 ====================

    def search_tasks(self, user_id: str, query: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        搜索任务

        根据关键词搜索用户的任务。

        Args:
            user_id: 用户ID
            query: 搜索关键词
            limit: 结果数量限制
            offset: 偏移量

        Returns:
            搜索结果

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("搜索任务", {
                "user_id": user_id,
                "query": query,
                "limit": limit,
                "offset": offset
            })

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证参数
            if not query or len(query.strip()) == 0:
                raise ValidationException(
                    message="搜索关键词不能为空",
                    details={"query": query}
                )

            if limit <= 0 or limit > 100:
                raise ValidationException(
                    message="结果数量限制必须在1-100之间",
                    details={"limit": limit}
                )

            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    details={"offset": offset}
                )

            # 执行搜索
            search_results = self.get_task_repository().search_tasks(
                user_id=user_id,
                query=query.strip(),
                limit=limit,
                offset=offset
            )

            # 构建结果
            tasks = [self._task_to_dict(task) for task in search_results]
            total_count = self.get_task_repository().count_tasks_by_user(user_id, search_query=query.strip())

            result = {
                "tasks": tasks,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_count": total_count,
                    "has_more": offset + limit < total_count
                },
                "search_info": {
                    "query": query.strip(),
                    "searched_at": datetime.now().isoformat()
                }
            }

            self._log_info("任务搜索完成", {
                "user_id": user_id,
                "query": query.strip(),
                "result_count": len(tasks)
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "search_tasks", {
                "user_id": user_id,
                "query": query
            })

    # ==================== 私有方法 ====================

    def _validate_task_data(self, task_data: Dict[str, Any], is_create: bool) -> Dict[str, Any]:
        """
        验证任务数据

        Args:
            task_data: 任务数据
            is_create: 是否为创建操作

        Returns:
            验证后的任务数据

        Raises:
            ValidationException: 当数据无效时
        """
        validated_data = {}

        # 验证标题
        if "title" in task_data:
            title = task_data["title"]
            if not title or len(title.strip()) == 0:
                raise ValidationException(
                    message="任务标题不能为空",
                    details={"title": title}
                )
            if len(title) > 200:
                raise ValidationException(
                    message="任务标题长度不能超过200个字符",
                    details={"title": title, "length": len(title)}
                )
            validated_data["title"] = title.strip()

        # 验证描述
        if "description" in task_data:
            description = task_data["description"]
            if description and len(description) > 2000:
                raise ValidationException(
                    message="任务描述长度不能超过2000个字符",
                    details={"description_length": len(description)}
                )
            validated_data["description"] = description.strip() if description else None

        # 验证优先级
        if "priority" in task_data:
            priority = task_data["priority"]
            try:
                validated_data["priority"] = PriorityLevel(priority)
            except ValueError:
                raise ValidationException(
                    message="无效的优先级",
                    details={"priority": priority, "valid_values": [p.value for p in PriorityLevel]}
                )

        # 验证父任务ID
        if "parent_id" in task_data:
            parent_id = task_data["parent_id"]
            if parent_id and not isinstance(parent_id, str):
                raise ValidationException(
                    message="父任务ID必须是字符串",
                    details={"parent_id": parent_id}
                )
            validated_data["parent_id"] = parent_id

        # 验证截止日期
        if "due_date" in task_data:
            due_date = task_data["due_date"]
            if due_date:
                try:
                    if isinstance(due_date, str):
                        validated_data["due_date"] = datetime.fromisoformat(due_date)
                    else:
                        validated_data["due_date"] = due_date
                except ValueError:
                    raise ValidationException(
                        message="截止日期格式无效",
                        details={"due_date": due_date}
                    )

        return validated_data

    def _validate_parent_task(self, user_id: str, parent_id: str, exclude_task_id: str = None) -> None:
        """
        验证父任务

        Args:
            user_id: 用户ID
            parent_id: 父任务ID
            exclude_task_id: 排除的任务ID（用于更新时避免循环引用）

        Raises:
            ResourceNotFoundException: 当父任务不存在时
            ValidationException: 当父任务无效时
        """
        # 获取父任务信息
        parent_task = self._check_resource_exists(
            self.get_task_repository(),
            parent_id,
            "父任务"
        )

        # 验证父任务属于该用户
        if parent_task.user_id != user_id:
            raise ValidationException(
                message="父任务不属于当前用户",
                details={"parent_id": parent_id, "user_id": user_id}
            )

        # 验证父任务状态
        if parent_task.status == TaskStatus.DELETED:
            raise ValidationException(
                message="不能将已删除的任务作为父任务",
                details={"parent_id": parent_id}
            )

        # 检查是否会形成循环引用（更新时）
        if exclude_task_id:
            if self._would_create_circular_reference(parent_id, exclude_task_id):
                raise ValidationException(
                    message="不能设置会形成循环引用的父子关系",
                    details={"parent_id": parent_id, "child_id": exclude_task_id}
                )

    def _would_create_circular_reference(self, parent_id: str, child_id: str) -> bool:
        """
        检查是否会创建循环引用

        Args:
            parent_id: 父任务ID
            child_id: 子任务ID

        Returns:
            是否会形成循环引用
        """
        # 从父任务开始，向上遍历任务层次结构
        current_id = parent_id
        max_depth = 50  # 防止无限循环

        while current_id and max_depth > 0:
            if current_id == child_id:
                return True

            # 获取当前任务的父任务
            current_task = self.get_task_repository().get_by_id(current_id)
            if not current_task:
                break

            current_id = current_task.parent_id
            max_depth -= 1

        return False

    def _has_children(self, task_id: str) -> bool:
        """检查任务是否有子任务"""
        children = self.get_task_repository().find_subtasks(task_id)
        return len(children) > 0

    def _has_incomplete_children(self, task_id: str) -> bool:
        """检查任务是否有未完成的子任务"""
        children = self.get_task_repository().find_subtasks(task_id)
        for child in children:
            if child.status != TaskStatus.COMPLETED:
                return True
        return False

    def _get_children_statistics(self, task_id: str) -> Dict[str, Any]:
        """获取子任务统计信息"""
        children = self.get_task_repository().find_subtasks(task_id)

        total = len(children)
        completed = sum(1 for child in children if child.status == TaskStatus.COMPLETED)
        in_progress = sum(1 for child in children if child.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for child in children if child.status == TaskStatus.PENDING)

        return {
            "total_children": total,
            "completed_children": completed,
            "in_progress_children": in_progress,
            "pending_children": pending,
            "completion_rate": completed / total if total > 0 else 0.0
        }

    def _update_parent_completion_progress(self, parent_id: str) -> None:
        """
        更新父任务的完成进度

        Args:
            parent_id: 父任务ID
        """
        # 获取子任务统计
        children_stats = self._get_children_statistics(parent_id)

        # 如果所有子任务都完成，将父任务也标记为完成
        if children_stats["total_children"] > 0 and children_stats["completed_children"] == children_stats["total_children"]:
            update_data = {
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now(),
                "updated_at": datetime.now()
            }
        else:
            # 如果有子任务在进行中，将父任务标记为进行中
            if children_stats["in_progress_children"] > 0:
                update_data = {
                    "status": TaskStatus.IN_PROGRESS,
                    "updated_at": datetime.now()
                }
            else:
                # 否则标记为待处理
                update_data = {
                    "status": TaskStatus.PENDING,
                    "updated_at": datetime.now()
                }

        self.get_task_repository().update(parent_id, update_data)

    def _calculate_task_rewards(self, task: Task) -> Dict[str, int]:
        """
        计算任务奖励

        Args:
            task: 任务对象

        Returns:
            奖励信息
        """
        # 基础奖励
        base_points = 10
        base_fragments = 1

        # 根据优先级调整奖励
        priority_multipliers = {
            PriorityLevel.LOW: 0.5,
            PriorityLevel.NORMAL: 1.0,
            PriorityLevel.HIGH: 1.5,
            PriorityLevel.URGENT: 2.0
        }

        multiplier = priority_multipliers.get(task.priority, 1.0)

        points = int(base_points * multiplier)
        fragments = max(1, int(base_fragments * multiplier))

        # 如果任务有子任务，根据子任务完成情况增加奖励
        if self._has_children(task.id):
            children_stats = self._get_children_statistics(task.id)
            if children_stats["total_children"] > 0:
                bonus_points = int(children_stats["total_children"] * 5 * children_stats["completion_rate"])
                points += bonus_points

        return {
            "points": points,
            "fragments": fragments
        }

    def _grant_task_rewards(self, user_id: str, task_id: str, rewards: Dict[str, int]) -> None:
        """
        发放任务奖励

        Args:
            user_id: 用户ID
            task_id: 任务ID
            rewards: 奖励信息
        """
        # TODO: 调用UserService的方法来发放奖励
        # if rewards["points"] > 0:
        #     self.user_service.add_user_points(user_id, rewards["points"], f"完成任务 {task_id}")
        # if rewards["fragments"] > 0:
        #     self.user_service.add_user_fragments(user_id, rewards["fragments"], f"完成任务 {task_id}")
        pass

    def _is_eligible_for_lottery(self, task: Task) -> bool:
        """
        判断任务是否有资格参与抽奖

        Args:
            task: 任务对象

        Returns:
            是否有抽奖资格
        """
        # 高优先级和紧急任务有抽奖资格
        return task.priority in [PriorityLevel.HIGH, PriorityLevel.URGENT]

    def _execute_lottery(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        执行抽奖

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            抽奖结果
        """
        # TODO: 实现抽奖逻辑
        # 这里需要调用RewardService的方法
        return None

    def _has_top3_today(self, user_id: str, date) -> bool:
        """检查今天是否已经设置过Top3"""
        # TODO: 实现Top3检查逻辑
        return False

    def _set_top3_tasks_for_date(self, user_id: str, date: str, task_ids: List[str]) -> None:
        """设置指定日期的Top3任务"""
        # TODO: 实现Top3设置逻辑
        pass

    def _get_top3_tasks_for_date(self, user_id: str, date: str) -> List[Dict[str, Any]]:
        """获取指定日期的Top3任务"""
        # TODO: 实现Top3获取逻辑
        return []

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """将任务对象转换为字典"""
        return {
            "id": task.id,
            "user_id": task.user_id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "parent_id": task.parent_id,
            "is_top3": getattr(task, 'is_top3', False),
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }