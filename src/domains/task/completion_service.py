"""
任务完成集成服务

集成任务完成、Top3检测、奖励分发和积分管理的综合服务。
实现v3文档中定义的任务完成奖励机制。

核心功能：
1. 任务完成状态管理
2. Top3任务检测和验证
3. 积分奖励分发（普通任务2分，Top3任务抽奖）
4. 奖品发放（50%概率获得奖品）
5. 流水记录和事务一致性

设计原则：
1. 事务一致性：确保所有操作要么全部成功，要么全部回滚
2. 业务逻辑封装：复杂的奖励逻辑封装在服务层
3. 可测试性：依赖注入，便于单元测试
4. 错误处理：详细的错误信息和日志记录

作者：TaTakeKe团队
版本：v1.0（Day3实施）
"""

import logging
from datetime import date, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from sqlmodel import Session, text

from .models import Task, TaskStatusConst
from .service import TaskService
from .repository import TaskRepository
from .exceptions import (
    TaskNotFoundException,
    TaskPermissionDeniedException,
    TaskDatabaseException
)

from ..top3.models import TaskTop3
from ..top3.service import Top3Service
from ..points.service import PointsService
from ..reward.service import RewardService
from ..points.models import PointsTransaction
from ..reward.models import RewardTransaction
from src.config.game_config import RewardConfig, TransactionSource

logger = logging.getLogger(__name__)


class TaskCompletionService:
    """
    任务完成集成服务

    协调任务完成、Top3检测、奖励分发等业务逻辑。
    确保事务一致性和业务规则的正确执行。
    """

    def __init__(self, session: Session):
        """
        初始化任务完成集成服务

        Args:
            session (Session): 数据库会话
        """
        self.session = session
        self.points_service = PointsService(session)
        self.task_service = TaskService(session, self.points_service)
        self.task_repository = TaskRepository(session)
        self.top3_service = Top3Service(session)
        self.reward_service = RewardService(session, self.points_service)
        self.game_config = RewardConfig()

    def complete_task(
        self,
        task_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        完成任务并触发奖励分发

        业务流程：
        1. 验证任务存在性和权限
        2. 检查任务是否已完成
        3. 更新任务状态为完成（包含父任务完成度递归更新）
        4. 检测是否是Top3任务
        5. 分发积分奖励（普通任务2分，Top3任务抽奖）
        6. 记录所有流水
        7. 返回完成结果和奖励信息

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 包含任务信息和奖励结果的字典

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限访问任务
        """
        try:
            task_id_str = str(task_id)
            user_id_str = str(user_id)
            logger.info(f"DEBUG: TaskCompletionService.complete_task called")
            logger.info(f"DEBUG: task_id={task_id_str}, type={type(task_id)}")
            logger.info(f"DEBUG: user_id={user_id_str}, type={type(user_id)}")

            # 1. 验证任务存在性和权限
            task = self.task_service.get_task(task_id, user_id)

            # 2. 检测是否是Top3任务
            is_top3 = self.top3_service.is_task_in_today_top3(str(user_id), str(task_id))

            # 3. 完成任务（包含状态更新、防刷检查、积分发放和父任务递归更新）
            result = self.task_service.complete_task(user_id, task_id)

            # 4. 如果需要，触发奖励分发（只有Top3任务才触发抽奖）
            lottery_result = None
            # 只有当任务是新完成的情况下才触发抽奖，排除重复完成的情况
            if (result.get("success") and
                is_top3 and
                result.get("reward_type") != "task_already_completed"):
                lottery_result = self.reward_service.top3_lottery(str(user_id))

            # 5. 重新获取更新后的任务对象
            updated_task = self.task_service.get_task(task_id, user_id)

            return {
                "code": 200,
                "data": {
                    "task": updated_task,
                    "completion_result": {
                        "success": result.get("success", True),
                        "task_id": result.get("task_id", str(task_id)),
                        "points_awarded": result.get("points_awarded", 0),
                        "reward_type": result.get("reward_type", "unknown"),
                        "message": result.get("message", "任务完成")
                    },
                    "lottery_result": lottery_result if lottery_result else None,
                    "message": "任务完成成功"
                },
                "message": "success"
            }

        except TaskNotFoundException as e:
            logger.error(f"完成任务失败: {e}")
            raise
        except TaskPermissionDeniedException as e:
            logger.error(f"完成任务失败: {e}")
            raise
        except Exception as e:
            logger.error(f"完成任务异常: {e}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常详情: {repr(e)}")
            # 添加堆栈跟踪以便调试
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            raise

    def uncomplete_task(
        self,
        task_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        取消任务完成状态

        业务流程：
        1. 验证任务存在性和权限
        2. 检查任务是否处于完成状态
        3. 更新任务状态为pending
        4. 递归更新父任务完成度
        5. 记录操作日志
        6. 返回操作结果

        注意：取消完成不会回收已发放的积分或奖励，这是业务规则决定。

        Args:
            task_id (UUID): 任务ID
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 包含任务信息和操作结果的字典

        Raises:
            TaskNotFoundException: 任务不存在
            TaskPermissionDeniedException: 无权限访问任务
        """
        try:
            logger.info(f"取消任务完成API调用: task_id={task_id}, user_id={user_id}")

            # 1. 验证任务存在性和权限
            task = self.task_service.get_task(task_id, user_id)

            # 2. 检查任务是否处于完成状态
            if task.get("status") != TaskStatusConst.COMPLETED:
                return {
                    "code": 200,
                    "data": {
                        "task": task,
                        "message": "任务未完成，无需取消"
                    },
                    "message": "success"
                }

            # 3. 更新任务状态为pending
            from datetime import datetime, timezone
            self.session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'pending', updated_at = :updated_at
                    WHERE id = :task_id AND user_id = :user_id
                """),
                {
                    "task_id": str(task_id),
                    "user_id": str(user_id),
                    "updated_at": datetime.now(timezone.utc)
                }
            )
            self.session.flush()

            # 4. 递归更新父任务完成度
            parent_update_result = self.task_service.update_parent_completion_percentage(user_id, task_id)

            # 5. 提交事务 - 确保所有数据库操作都持久化
            self.session.commit()

            # 6. 重新获取更新后的任务对象，确保返回最新状态
            updated_task = self.task_service.get_task(task_id, user_id)

            # 7. 返回操作结果
            return {
                "code": 200,
                "data": {
                    "task": updated_task,  # 使用更新后的任务对象
                    "parent_update": parent_update_result,
                    "message": "取消完成成功（注意：已发放的积分和奖励不会回收）"
                },
                "message": "success"
            }

        except TaskNotFoundException as e:
            logger.error(f"取消任务完成失败: {e}")
            self.session.rollback()
            raise
        except TaskPermissionDeniedException as e:
            logger.error(f"取消任务完成失败: {e}")
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"取消任务完成异常: {e}")
            self.session.rollback()
            raise