"""
任务完成服务 - 跨领域业务逻辑示例

展示如何在PostgreSQL Schema分离环境下实现跨领域的复杂业务逻辑。
任务完成涉及：
1. 任务领域（Task Domain）：更新任务状态
2. 积分领域（Points Domain）：发放积分奖励
3. 奖励领域（Reward Domain）：发放奖品奖励
4. 审计领域（Auth Domain）：记录操作日志

核心特性：
1. 跨领域事务：使用cross_domain_transaction确保数据一致性
2. Schema隔离：每个领域使用独立的Schema
3. 多租户支持：动态Schema翻译
4. 防刷机制：last_claimed_date字段确保永久防刷
5. 事件驱动：完成后触发领域事件

作者：TaKeKe团队
版本：v2.0（Schema分离版）
"""

import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List
from enum import Enum

# 导入Schema数据库管理器
from src.core.schema_database import db_manager, cross_domains, domain_session
from src.domains.task.models_schema import Task, TaskStatusConst, TaskQueryBuilder
from src.domains.points.models import PointsTransaction
from src.domains.reward.models import RewardTransaction
from src.domains.auth.models import AuthLog


class TaskCompleteResult(Enum):
    """任务完成结果类型"""
    NORMAL_REWARD = "normal_reward"      # 普通任务奖励（2积分）
    TOP3_POINTS = "top3_points"          # Top3任务积分奖励（100积分）
    TOP3_REWARD = "top3_reward"          # Top3任务奖品奖励
    ALREADY_CLAIMED = "already_claimed"  # 已领取过奖励
    FAILED = "failed"                    # 操作失败


class TaskCompleteRequest:
    """任务完成请求"""

    def __init__(
        self,
        user_id: str,
        task_id: str,
        mood_feedback: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.mood_feedback = mood_feedback or {}
        self.tenant_id = tenant_id


class TaskCompleteResponse:
    """任务完成响应"""

    def __init__(
        self,
        success: bool,
        task: Optional[Task] = None,
        result_type: Optional[TaskCompleteResult] = None,
        reward_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        self.success = success
        self.task = task
        self.result_type = result_type
        self.reward_data = reward_data or {}
        self.error_message = error_message


class TaskCompleteService:
    """任务完成服务 - Schema分离版本"""

    def __init__(self):
        self.query_builder = TaskQueryBuilder("task")

    def complete_task(self, request: TaskCompleteRequest) -> TaskCompleteResponse:
        """
        完成任务并发放奖励（跨领域操作）

        Args:
            request: 任务完成请求

        Returns:
            TaskCompleteResponse: 完成结果
        """
        try:
            # 使用跨领域事务确保数据一致性
            with cross_domains(["task", "points", "reward", "auth"], request.tenant_id) as sessions:
                task_session = sessions["task"]
                points_session = sessions["points"]
                reward_session = sessions["reward"]
                auth_session = sessions["auth"]

                # 1. 获取并验证任务
                task = self._get_and_validate_task(task_session, request.task_id, request.user_id)
                if not task:
                    return TaskCompleteResponse(
                        success=False,
                        error_message="任务不存在或无权限访问"
                    )

                # 2. 检查防刷机制
                if task.last_claimed_date is not None:
                    # 已领取过奖励，但仍然可以更新任务状态
                    task = self._update_task_status_only(task_session, task)
                    return TaskCompleteResponse(
                        success=True,
                        task=task,
                        result_type=TaskCompleteResult.ALREADY_CLAIMED,
                        reward_data={"message": "任务完成，但已领取过奖励"}
                    )

                # 3. 确定奖励类型和发放奖励
                reward_result = self._issue_reward(
                    points_session,
                    reward_session,
                    request.user_id,
                    task
                )

                # 4. 更新任务状态和防刷标记
                task = self._update_task_and_claim_date(task_session, task)

                # 5. 更新父任务完成度（如果有）
                self._update_parent_completion(task_session, task)

                # 6. 记录操作日志
                self._log_operation(auth_session, request, task, reward_result)

                # 7. 构建响应
                return self._build_response(task, reward_result)

        except Exception as e:
            # 事务会自动回滚
            return TaskCompleteResponse(
                success=False,
                error_message=f"任务完成失败: {str(e)}"
            )

    def _get_and_validate_task(self, session, task_id: str, user_id: str) -> Optional[Task]:
        """获取并验证任务"""
        task = session.query(Task).where(Task.id == task_id).first()
        if not task:
            return None

        if task.user_id != user_id:
            return None

        if task.is_deleted:
            return None

        return task

    def _is_top3_task(self, task: Task) -> bool:
        """检查是否为Top3任务"""
        # 需要查询top3_domain.task_top3表
        with domain_session("top3") as top3_session:
            from src.domains.top3.models import TaskTop3

            today = date.today()
            top3_record = top3_session.query(TaskTop3).where(
                TaskTop3.user_id == task.user_id,
                TaskTop3.top_date == today
            ).first()

            if not top3_record:
                return False

            # 检查任务是否在今日Top3中
            import json
            task_ids = top3_record.task_ids or []
            for item in task_ids:
                if item.get("task_id") == task.id:
                    return True

            return False

    def _issue_reward(self, points_session, reward_session, user_id: str, task: Task) -> Dict[str, Any]:
        """发放奖励"""
        transaction_group = str(uuid.uuid4())

        if self._is_top3_task(task):
            # Top3任务奖励：50%概率100积分，50%概率奖品
            import random
            if random.random() < 0.5:
                # 发放100积分
                points_transaction = PointsTransaction(
                    user_id=user_id,
                    amount=100,
                    source_type="task_complete_top3",
                    source_id=task.id,
                    transaction_group=transaction_group
                )
                points_session.add(points_transaction)

                return {
                    "type": "points",
                    "amount": 100,
                    "transaction_id": points_transaction.id,
                    "result_type": TaskCompleteResult.TOP3_POINTS
                }
            else:
                # 发放奖品
                reward_id = self._random_reward_id()
                reward_transaction = RewardTransaction(
                    user_id=user_id,
                    reward_id=reward_id,
                    source_type="top3_lottery",
                    source_id=task.id,
                    quantity=1,
                    transaction_group=transaction_group
                )
                reward_session.add(reward_transaction)

                return {
                    "type": "reward",
                    "reward_id": reward_id,
                    "quantity": 1,
                    "transaction_id": reward_transaction.id,
                    "result_type": TaskCompleteResult.TOP3_REWARD
                }
        else:
            # 普通任务奖励：固定2积分
            points_transaction = PointsTransaction(
                user_id=user_id,
                amount=2,
                source_type="task_complete",
                source_id=task.id
            )
            points_session.add(points_transaction)

            return {
                "type": "points",
                "amount": 2,
                "transaction_id": points_transaction.id,
                "result_type": TaskCompleteResult.NORMAL_REWARD
            }

    def _random_reward_id(self) -> str:
        """随机选择奖品ID（示例实现）"""
        # 实际实现中应该从rewards表中查询活跃的奖品
        rewards = ["small_coin", "big_coin", "diamond"]
        import random
        return random.choice(rewards)

    def _update_task_status_only(self, session, task: Task) -> Task:
        """只更新任务状态（不更新防刷标记）"""
        task.status = TaskStatusConst.COMPLETED
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        session.flush()  # 立即刷新但不提交
        return task

    def _update_task_and_claim_date(self, session, task: Task) -> Task:
        """更新任务状态和防刷日期"""
        task.status = TaskStatusConst.COMPLETED
        task.last_claimed_date = date.today()
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        session.flush()
        return task

    def _update_parent_completion(self, session, task: Task):
        """更新父任务完成度"""
        if not task.parent_id:
            return

        # 递归更新父任务完成度
        parent_task = session.query(Task).where(Task.id == task.parent_id).first()
        if not parent_task:
            return

        # 计算父任务的完成度
        child_tasks = session.query(Task).where(Task.parent_id == task.parent_id).all()
        if not child_tasks:
            return

        completed_count = sum(1 for child in child_tasks if child.status == TaskStatusConst.COMPLETED)
        completion_percentage = (completed_count / len(child_tasks)) * 100

        parent_task.completion_percentage = completion_percentage
        parent_task.updated_at = datetime.now(timezone.utc)
        session.add(parent_task)

        # 递归更新更高层级的父任务
        if parent_task.parent_id:
            self._update_parent_completion(session, parent_task)

    def _log_operation(self, auth_session, request: TaskCompleteRequest, task: Task, reward_result: Dict[str, Any]):
        """记录操作日志"""
        auth_log = AuthLog(
            user_id=request.user_id,
            action="task_complete",
            result="success",
            details=f"完成任务: {task.title}, 奖励: {reward_result.get('type', 'none')}"
        )
        auth_session.add(auth_log)

    def _build_response(self, task: Task, reward_result: Dict[str, Any]) -> TaskCompleteResponse:
        """构建响应"""
        return TaskCompleteResponse(
            success=True,
            task=task,
            result_type=reward_result["result_type"],
            reward_data={
                "type": reward_result["type"],
                "amount": reward_result.get("amount", 0),
                "reward_id": reward_result.get("reward_id"),
                "quantity": reward_result.get("quantity", 0),
                "transaction_id": reward_result["transaction_id"]
            }
        )


# 业务服务工厂
class TaskServiceFactory:
    """任务服务工厂"""

    @staticmethod
    def create_complete_service() -> TaskCompleteService:
        """创建任务完成服务"""
        return TaskCompleteService()


# 便捷API函数
def complete_task(user_id: str, task_id: str, mood_feedback: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None) -> TaskCompleteResponse:
    """
    完成任务的便捷API函数

    Args:
        user_id: 用户ID
        task_id: 任务ID
        mood_feedback: 心情反馈
        tenant_id: 租户ID

    Returns:
        TaskCompleteResponse: 完成结果
    """
    service = TaskServiceFactory.create_complete_service()
    request = TaskCompleteRequest(
        user_id=user_id,
        task_id=task_id,
        mood_feedback=mood_feedback,
        tenant_id=tenant_id
    )
    return service.complete_task(request)


# 批量完成任务的服务
class BatchTaskCompleteService:
    """批量任务完成服务"""

    @staticmethod
    def complete_multiple_tasks(
        user_id: str,
        task_ids: List[str],
        tenant_id: Optional[str] = None
    ) -> List[TaskCompleteResponse]:
        """
        批量完成多个任务

        Args:
            user_id: 用户ID
            task_ids: 任务ID列表
            tenant_id: 租户ID

        Returns:
            List[TaskCompleteResponse]: 每个任务的完成结果
        """
        results = []
        service = TaskCompleteService()

        for task_id in task_ids:
            request = TaskCompleteRequest(
                user_id=user_id,
                task_id=task_id,
                tenant_id=tenant_id
            )
            result = service.complete_task(request)
            results.append(result)

        return results


# 导出服务类
__all__ = [
    "TaskCompleteService",
    "TaskCompleteRequest",
    "TaskCompleteResponse",
    "TaskCompleteResult",
    "TaskServiceFactory",
    "BatchTaskCompleteService",
    "complete_task"
]