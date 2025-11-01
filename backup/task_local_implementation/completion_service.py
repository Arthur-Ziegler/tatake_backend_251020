"""
任务完成集成服务 - 微服务架构版本

集成任务完成、Top3检测、奖励分发和积分管理的综合服务。
实现v3文档中定义的任务完成奖励机制。

核心功能：
1. 任务完成状态管理（通过微服务）
2. Top3任务检测和验证（通过微服务）
3. 积分奖励分发（普通任务2分，Top3任务抽奖）
4. 奖品发放（50%概率获得奖品）
5. 流水记录和事务一致性

设计原则：
1. 事务一致性：确保所有操作要么全部成功，要么全部回滚
2. 业务逻辑封装：复杂的奖励逻辑封装在服务层
3. 可测试性：依赖注入，便于单元测试
4. 错误处理：详细的错误信息和日志记录

作者：TaTakeKe团队
版本：v2.0（微服务架构版）
"""

import logging
from datetime import date, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from sqlmodel import Session, text

from src.services.task_microservice_client import call_task_service, TaskMicroserviceError

# 导入其他领域服务
# Top3已迁移到微服务，使用微服务客户端
from ..points.service import PointsService
from ..reward.service import RewardService
from ..points.models import PointsTransaction
from ..reward.models import RewardTransaction
from src.config.game_config import RewardConfig, TransactionSource

logger = logging.getLogger(__name__)

# 任务状态常量
class TaskStatusConst:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCompletionService:
    """
    任务完成集成服务 - 微服务架构版本

    协调任务完成、Top3检测、奖励分发等业务逻辑。
    现在通过微服务客户端与Task微服务通信。
    """

    def __init__(self, session: Session):
        """
        初始化任务完成集成服务

        Args:
            session (Session): 数据库会话
        """
        self.session = session
        self.points_service = PointsService(session)
        # Top3已迁移到微服务，使用微服务客户端
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
        1. 通过微服务验证任务存在性和权限
        2. 通过微服务检测是否是Top3任务
        3. 通过微服务完成任务（包含状态更新、防刷检查、积分发放和父任务递归更新）
        4. 如果需要，触发奖励分发（只有Top3任务才触发抽奖）
        5. 记录所有流水
        6. 返回完成结果和奖励信息

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
            logger.info(f"DEBUG: TaskCompletionService.complete_task called (微服务版本)")
            logger.info(f"DEBUG: task_id={task_id_str}, type={type(task_id)}")
            logger.info(f"DEBUG: user_id={user_id_str}, type={type(user_id)}")

            # 1. 通过微服务获取任务信息
            try:
                task_data = call_task_service(
                    method="GET",
                    endpoint=f"tasks/{task_id_str}",
                    user_id=user_id_str
                )
                task = task_data.get("data", {})
                logger.info(f"  ✅ 通过微服务获取任务成功: {task.get('title')}")
            except TaskMicroserviceError as e:
                logger.error(f"通过微服务获取任务失败: {e}")
                raise

            # 2. 检测是否是Top3任务（通过微服务）
            try:
                today = date.today().isoformat()
                top3_data = call_task_service(
                    method="GET",
                    endpoint=f"tasks/special/top3/{today}",
                    user_id=user_id_str
                )
                top3_task_ids = top3_data.get("data", {}).get("task_ids", [])
                is_top3 = task_id_str in top3_task_ids
                logger.info(f"  🏆 Top3检测结果: {'是Top3任务' if is_top3 else '普通任务'}")
            except TaskMicroserviceError:
                # 如果无法获取Top3信息，默认为普通任务
                is_top3 = False
                logger.info(f"  🏆 Top3检测失败，默认为普通任务")

            # 3. 通过微服务完成任务
            try:
                complete_result = call_task_service(
                    method="POST",
                    endpoint=f"tasks/{task_id_str}/complete",
                    user_id=user_id_str,
                    data={}
                )
                logger.info(f"  ✅ 通过微服务完成任务成功")
            except TaskMicroserviceError as e:
                logger.error(f"通过微服务完成任务失败: {e}")
                raise

            # 4. 如果需要，触发奖励分发（只有Top3任务才触发抽奖）
            lottery_result = None
            reward_earned = None

            # 构建reward_earned结构（v3规范）
            if complete_result.get("success"):
                if is_top3:
                    # Top3任务：触发抽奖
                    lottery_result = self.reward_service.top3_lottery(str(user_id))
                    if lottery_result:
                        if lottery_result["type"] == "reward":
                            # 中奖获得奖品
                            reward_earned = {
                                "type": "reward",
                                "transaction_id": lottery_result.get("transaction_group"),
                                "reward_id": lottery_result["reward"]["id"],
                                "amount": 1  # 获得1个奖品
                            }
                        else:
                            # 获得积分安慰奖
                            reward_earned = {
                                "type": "points",
                                "transaction_id": lottery_result.get("transaction_group"),
                                "reward_id": None,
                                "amount": lottery_result["amount"]
                            }
                else:
                    # 普通任务：获得积分
                    reward_earned = {
                        "type": "points",
                        "transaction_id": None,  # 普通任务积分没有transaction_group
                        "reward_id": None,
                        "amount": complete_result.get("data", {}).get("points_awarded", 2)  # 默认2积分
                    }

            # 5. 重新获取更新后的任务对象
            try:
                updated_task_data = call_task_service(
                    method="GET",
                    endpoint=f"tasks/{task_id_str}",
                    user_id=user_id_str
                )
                updated_task = updated_task_data.get("data", {})
            except TaskMicroserviceError:
                updated_task = task  # 如果获取失败，使用原来的任务信息

            return {
                "code": 200,
                "data": {
                    "task": updated_task,
                    "reward_earned": reward_earned,
                    "lottery_result": lottery_result if lottery_result else None,  # 保留向后兼容
                    "message": "任务完成成功"
                },
                "message": "success"
            }

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
        1. 通过微服务验证任务存在性和权限
        2. 通过微服务检查任务是否处于完成状态
        3. 通过微服务更新任务状态为pending
        4. 记录操作日志
        5. 返回操作结果

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
            task_id_str = str(task_id)
            user_id_str = str(user_id)
            logger.info(f"取消任务完成API调用(微服务版本): task_id={task_id_str}, user_id={user_id_str}")

            # 1. 通过微服务获取任务信息
            try:
                task_data = call_task_service(
                    method="GET",
                    endpoint=f"tasks/{task_id_str}",
                    user_id=user_id_str
                )
                task = task_data.get("data", {})
            except TaskMicroserviceError as e:
                logger.error(f"通过微服务获取任务失败: {e}")
                raise

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

            # 3. 通过微服务取消完成任务
            try:
                uncomplete_result = call_task_service(
                    method="POST",
                    endpoint=f"tasks/{task_id_str}/uncomplete",
                    user_id=user_id_str,
                    data={}
                )
                logger.info(f"  ✅ 通过微服务取消完成任务成功")
            except TaskMicroserviceError as e:
                logger.error(f"通过微服务取消完成任务失败: {e}")
                raise

            # 4. 重新获取更新后的任务对象
            try:
                updated_task_data = call_task_service(
                    method="GET",
                    endpoint=f"tasks/{task_id_str}",
                    user_id=user_id_str
                )
                updated_task = updated_task_data.get("data", {})
            except TaskMicroserviceError:
                updated_task = task  # 如果获取失败，使用原来的任务信息

            # 5. 返回操作结果
            return {
                "code": 200,
                "data": {
                    "task": updated_task,
                    "parent_update": uncomplete_result.get("data", {}).get("parent_update"),
                    "message": "取消完成成功（注意：已发放的积分和奖励不会回收）"
                },
                "message": "success"
            }

        except Exception as e:
            logger.error(f"取消任务完成异常: {e}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常详情: {repr(e)}")
            # 添加堆栈跟踪以便调试
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            raise