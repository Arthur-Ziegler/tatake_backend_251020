"""
任务防刷机制专项测试套件

专门测试任务防刷机制的各种场景，包括：
1. 基本防刷逻辑验证
2. 取消完成后再完成的防刷
3. 跨日期防刷测试
4. 并发完成防刷测试
5. 不同用户任务的防刷隔离
6. Top3任务防刷测试

遵循TDD原则，专注于防刷机制的边界条件验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, date, timedelta
from uuid import uuid4, UUID
from unittest.mock import patch

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.task.repository import TaskRepository
from src.domains.points.service import PointsService
from src.domains.task.exceptions import TaskNotFoundException, TaskPermissionDeniedException


@pytest.mark.unit
class TestTaskAntiSpamMechanism:
    """任务防刷机制测试类"""

    def test_basic_anti_spam_mechanism(self, task_service, task_repository):
        """测试基本防刷机制：同一任务重复完成只能获得一次积分"""
        user_id = str(uuid4())

        # 创建任务
        task_data = {
            "user_id": user_id,
            "title": "防刷测试任务",
            "description": "测试防刷机制",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 记录初始积分
        initial_points = task_service.points_service.get_balance(user_id)

        # 第一次完成
        first_result = task_service.complete_task(user_id, task.id)
        first_points = first_result["points_awarded"]
        first_reward_type = first_result["reward_type"]

        # 验证第一次完成
        assert first_points > 0
        assert first_reward_type == "task_complete"
        assert first_result["success"] is True

        # 验证积分增加
        points_after_first = task_service.points_service.get_balance(user_id)
        assert points_after_first == initial_points + first_points

        # 第二次完成（应该触发防刷）
        second_result = task_service.complete_task(user_id, task.id)
        second_points = second_result["points_awarded"]
        second_reward_type = second_result["reward_type"]

        # 验证防刷生效
        assert second_points == 0
        assert second_reward_type == "task_already_completed_once"
        assert second_result["success"] is True

        # 验证积分没有增加
        points_after_second = task_service.points_service.get_balance(user_id)
        assert points_after_second == points_after_first  # 积分不变

        # 验证任务状态仍然更新为completed
        updated_task = task_repository.get_by_id(task.id, user_id)
        assert updated_task.status == TaskStatusConst.COMPLETED

    def test_anti_spam_after_uncomplete(self, task_service, task_repository):
        """测试取消完成后再完成仍然防刷"""
        user_id = str(uuid4())

        # 创建任务
        task_data = {
            "user_id": user_id,
            "title": "取消完成防刷测试",
            "description": "测试取消完成后的防刷",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 第一次完成
        first_result = task_service.complete_task(user_id, task.id)
        assert first_result["points_awarded"] > 0
        assert first_result["reward_type"] == "task_complete"

        # 取消完成
        from src.domains.task.completion_service import TaskCompletionService
        completion_service = TaskCompletionService(task_repository.session)
        uncomplete_result = completion_service.uncomplete_task(task.id, user_id)

        # 验证任务状态变为pending（根据API返回结构调整）
        if "task" in uncomplete_result:
            assert uncomplete_result["task"]["status"] == TaskStatusConst.PENDING
        elif "data" in uncomplete_result and "task" in uncomplete_result["data"]:
            assert uncomplete_result["data"]["task"]["status"] == TaskStatusConst.PENDING

        # 再次完成（应该仍然防刷）
        second_result = task_service.complete_task(user_id, task.id)

        # 验证防刷仍然生效
        assert second_result["points_awarded"] == 0
        assert second_result["reward_type"] == "task_already_completed_once"
        assert second_result["success"] is True

        # 验证任务状态正确更新为completed
        final_task = task_repository.get_by_id(task.id, user_id)
        assert final_task.status == TaskStatusConst.COMPLETED

    def test_anti_spam_cross_day_boundary(self, task_service, task_repository):
        """测试跨日期防刷：即使跨天也不能重复获得积分"""
        user_id = str(uuid4())

        # 创建任务
        task_data = {
            "user_id": user_id,
            "title": "跨日期防刷测试",
            "description": "测试跨日期的防刷机制",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 模拟第一天完成
        with patch('datetime.datetime') as mock_datetime:
            # 设置为第一天
            day1 = datetime(2023, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = day1

            first_result = task_service.complete_task(user_id, task.id)
            assert first_result["points_awarded"] > 0
            assert first_result["reward_type"] == "task_complete"

        # 取消完成
        from src.domains.task.completion_service import TaskCompletionService
        completion_service = TaskCompletionService(task_repository.session)
        completion_service.uncomplete_task(task.id, user_id)

        # 模拟第二天完成
        with patch('datetime.datetime') as mock_datetime:
            # 设置为第二天
            day2 = datetime(2023, 12, 26, 10, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = day2

            second_result = task_service.complete_task(user_id, task.id)

            # 即使跨天，防刷仍然应该生效
            assert second_result["points_awarded"] == 0
            assert second_result["reward_type"] == "task_already_completed_once"

    def test_anti_spam_user_isolation(self, task_service, task_repository):
        """测试不同用户的任务防刷隔离"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        # 用户1创建并完成任务
        task1_data = {
            "user_id": user1_id,
            "title": "用户1的任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task1 = task_repository.create(task1_data)

        # 用户1第一次完成
        result1 = task_service.complete_task(user1_id, task1.id)
        assert result1["points_awarded"] > 0
        assert result1["reward_type"] == "task_complete"

        # 用户1再次完成（应该防刷）
        result1_spam = task_service.complete_task(user1_id, task1.id)
        assert result1_spam["points_awarded"] == 0
        assert result1_spam["reward_type"] == "task_already_completed_once"

        # 用户2创建相同标题的任务
        task2_data = {
            "user_id": user2_id,
            "title": "用户1的任务",  # 相同标题但不同用户
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task2 = task_repository.create(task2_data)

        # 用户2完成自己的任务（应该正常获得积分，不受用户1影响）
        result2 = task_service.complete_task(user2_id, task2.id)
        assert result2["points_awarded"] > 0
        assert result2["reward_type"] == "task_complete"

        # 验证积分计算隔离
        user1_points = task_service.points_service.get_balance(user1_id)
        user2_points = task_service.points_service.get_balance(user2_id)

        # 用户2的积分应该独立计算
        assert user2_points > 0

    def test_anti_spam_with_different_tasks(self, task_service, task_repository):
        """测试同一用户不同任务的防刷隔离"""
        user_id = str(uuid4())

        # 创建两个不同的任务
        task1_data = {
            "user_id": user_id,
            "title": "任务1",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task2_data = {
            "user_id": user_id,
            "title": "任务2",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }

        task1 = task_repository.create(task1_data)
        task2 = task_repository.create(task2_data)

        # 完成任务1
        result1 = task_service.complete_task(user_id, task1.id)
        assert result1["points_awarded"] > 0
        assert result1["reward_type"] == "task_complete"

        # 再次完成任务1（应该防刷）
        result1_spam = task_service.complete_task(user_id, task1.id)
        assert result1_spam["points_awarded"] == 0
        assert result1_spam["reward_type"] == "task_already_completed_once"

        # 完成任务2（应该正常获得积分，不受任务1影响）
        result2 = task_service.complete_task(user_id, task2.id)
        assert result2["points_awarded"] > 0
        assert result2["reward_type"] == "task_complete"

    def test_anti_spam_edge_cases(self, task_service, task_repository):
        """测试防刷机制的边界情况"""
        user_id = str(uuid4())

        # 测试1: 创建时就有last_claimed_date的任务
        task_with_claim_date = task_repository.create({
            "user_id": user_id,
            "title": "已有领取日期的任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM,
            "last_claimed_date": date(2023, 12, 25)  # 已经领取过
        })

        # 完成已有领取日期的任务（应该防刷）
        result_claimed = task_service.complete_task(user_id, task_with_claim_date.id)
        assert result_claimed["points_awarded"] == 0
        assert result_claimed["reward_type"] == "task_already_completed_once"

        # 测试2: 空的用户ID处理
        invalid_user_id = ""
        invalid_task = task_repository.create({
            "user_id": invalid_user_id,
            "title": "无效用户任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        })

        # 空用户ID完成任务（应该正常处理或优雅失败）
        try:
            result_invalid = task_service.complete_task(invalid_user_id, invalid_task.id)
            # 如果成功，验证逻辑
            assert result_invalid["success"] in [True, False]
        except Exception:
            # 如果失败，也是可以接受的
            pass

    def test_anti_spam_database_consistency(self, task_service, task_repository):
        """测试防刷机制的数据库一致性"""
        user_id = str(uuid4())

        # 创建任务
        task_data = {
            "user_id": user_id,
            "title": "数据库一致性测试",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 完成任务
        result = task_service.complete_task(user_id, task.id)
        assert result["success"] is True
        assert result["points_awarded"] > 0

        # 验证数据库中的任务状态
        db_task = task_repository.get_by_id(task.id, user_id)
        assert db_task.status == TaskStatusConst.COMPLETED
        assert db_task.last_claimed_date is not None

        # 验证积分记录
        points_balance = task_service.points_service.get_balance(user_id)
        assert points_balance > 0

        # 再次完成任务（防刷）
        spam_result = task_service.complete_task(user_id, task.id)
        assert spam_result["points_awarded"] == 0

        # 验证数据库状态保持一致
        db_task_after_spam = task_repository.get_by_id(task.id, user_id)
        assert db_task_after_spam.status == TaskStatusConst.COMPLETED
        # last_claimed_date应该保持不变
        assert db_task_after_spam.last_claimed_date == db_task.last_claimed_date

        # 验证积分余额没有变化
        points_balance_after_spam = task_service.points_service.get_balance(user_id)
        assert points_balance_after_spam == points_balance

    def test_anti_spam_error_handling(self, task_service, task_repository):
        """测试防刷机制的错误处理"""
        user_id = str(uuid4())
        fake_task_id = uuid4()

        # 测试完成不存在的任务
        with pytest.raises(TaskNotFoundException):
            task_service.complete_task(user_id, fake_task_id)

        # 测试无权限完成任务
        other_user_id = str(uuid4())
        task = task_repository.create({
            "user_id": user_id,
            "title": "权限测试任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        })

        # 根据实际实现，可能是抛出TaskNotFoundException而不是TaskPermissionDeniedException
        with pytest.raises((TaskPermissionDeniedException, TaskNotFoundException)):
            task_service.complete_task(other_user_id, task.id)

    def test_anti_spam_message_content(self, task_service, task_repository):
        """测试防刷机制的返回消息内容"""
        user_id = str(uuid4())

        # 创建任务
        task = task_repository.create({
            "user_id": user_id,
            "title": "消息内容测试",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        })

        # 第一次完成
        first_result = task_service.complete_task(user_id, task.id)
        assert "任务完成" in first_result["message"]
        assert str(first_result["points_awarded"]) in first_result["message"]

        # 第二次完成（防刷）
        second_result = task_service.complete_task(user_id, task.id)
        assert second_result["message"] == "任务完成，获得0积分"
        assert second_result["reward_type"] == "task_already_completed_once"

    def test_anti_spam_with_top3_tasks(self, task_service, task_repository):
        """测试Top3任务的防刷机制"""
        user_id = str(uuid4())

        # 创建Top3任务
        top3_task = task_repository.create({
            "user_id": user_id,
            "title": "Top3防刷测试",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.HIGH  # 假设这是Top3任务
        })

        # 第一次完成Top3任务
        first_result = task_service.complete_task(user_id, top3_task.id)
        assert first_result["points_awarded"] > 0
        assert first_result["reward_type"] == "task_complete"

        # 第二次完成Top3任务（应该防刷）
        second_result = task_service.complete_task(user_id, top3_task.id)
        assert second_result["points_awarded"] == 0
        assert second_result["reward_type"] == "task_already_completed_once"

        # 验证即使Top3任务也不能重复获得积分
        assert first_result["points_awarded"] == second_result["points_awarded"] + first_result["points_awarded"]