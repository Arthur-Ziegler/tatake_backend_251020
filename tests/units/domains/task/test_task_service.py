"""
Task领域Service层测试套件

测试TaskService的业务逻辑功能，包括：
1. 任务完成与积分发放
2. 任务列表查询与筛选
3. 任务更新操作
4. 错误处理与边界条件
5. 事务管理

遵循TDD原则，专注于业务逻辑验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, date, timedelta
from uuid import uuid4, UUID

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.points.service import PointsService
from src.domains.task.exceptions import TaskNotFoundException, TaskPermissionDeniedException


@pytest.mark.unit
class TestTaskService:
    """TaskService测试类"""

    def test_complete_task_basic(self, task_service, task_repository):
        """测试基本任务完成功能"""
        user_id = str(uuid4())

        # 创建任务（使用Repository）
        task_data = {
            "user_id": user_id,
            "title": "要完成的任务",
            "description": "完成这个测试任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 完成任务（使用Service）
        result = task_service.complete_task(user_id, task.id)

        assert result["success"] is True
        assert "points_awarded" in result

        # 验证任务状态更新
        updated_task = task_repository.get_by_id(task.id, user_id)
        assert updated_task.status == TaskStatusConst.COMPLETED

    def test_complete_task_with_points(self, task_service, task_repository):
        """测试任务完成时发放积分"""
        user_id = str(uuid4())

        # 创建任务（使用Repository）
        task_data = {
            "user_id": user_id,
            "title": "积分测试任务",
            "description": "完成获得积分",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 获取完成前积分
        initial_points = task_service.points_service.get_balance(user_id)

        # 完成任务（使用Service）
        result = task_service.complete_task(user_id, task.id)

        # 验证积分增加
        final_points = task_service.points_service.get_balance(user_id)
        assert final_points > initial_points
        assert result["success"] is True

    def test_complete_task_already_completed(self, task_service, task_repository):
        """测试重复完成任务应该返回防刷结果而不是抛出异常"""
        user_id = str(uuid4())

        # 创建并完成任务（使用Repository）
        task_data = {
            "user_id": user_id,
            "title": "已完成任务",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM
        }
        task = task_repository.create(task_data)

        # 首次完成任务
        first_result = task_service.complete_task(user_id, task.id)
        assert first_result["success"] is True
        assert first_result["points_awarded"] > 0
        assert first_result["reward_type"] == "task_complete"

        # 验证任务状态
        updated_task = task_repository.get_by_id(task.id, user_id)
        assert updated_task.status == TaskStatusConst.COMPLETED

        # 再次完成应该返回防刷结果（不再抛出异常）
        second_result = task_service.complete_task(user_id, task.id)
        assert second_result["success"] is True  # 修复：仍然返回成功
        assert second_result["points_awarded"] == 0  # 防刷生效
        assert second_result["reward_type"] == "task_already_completed_once"
        assert "任务完成，获得0积分" == second_result["message"]

    def test_complete_task_not_found(self, task_service):
        """测试完成不存在的任务"""
        user_id = str(uuid4())
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundException):
            task_service.complete_task(fake_id, user_id)

    def test_complete_task_permission_denied(self, task_service):
        """测试无权限完成任务"""
        user_id = str(uuid4())
        other_user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="其他用户的任务"
        )

        # 其他用户尝试完成
        with pytest.raises(TaskPermissionDeniedException):
            task_service.complete_task(task.id, other_user_id)

    def test_get_task_list_empty(self, task_service):
        """测试获取空任务列表"""
        user_id = str(uuid4())

        result = task_service.get_task_list(user_id)

        assert result['tasks'] == []
        assert result['pagination']['total_count'] == 0
        assert result['pagination']['current_page'] == 1

    def test_get_task_list_with_tasks(self, task_service):
        """测试获取包含任务的列表"""
        user_id = str(uuid4())

        # 创建多个任务
        tasks = []
        for i in range(5):
            task = task_service.create_task(
                user_id=user_id,
                title=f"任务 {i+1}",
                description=f"任务描述 {i+1}"
            )
            tasks.append(task)

        result = task_service.get_task_list(user_id)

        assert len(result['tasks']) == 5
        assert result['pagination']['total_count'] == 5
        assert result['pagination']['current_page'] == 1
        assert result['pagination']['page_size'] == 20

    def test_get_task_list_with_pagination(self, task_service):
        """测试分页获取任务列表"""
        user_id = str(uuid4())

        # 创建25个任务
        for i in range(25):
            task_service.create_task(
                user_id=user_id,
                title=f"分页任务 {i+1}"
            )

        # 获取第一页
        page1 = task_service.get_task_list(user_id, page=1, page_size=10)
        assert len(page1['tasks']) == 10
        assert page1['pagination']['current_page'] == 1
        assert page1['pagination']['has_next'] is True
        assert page1['pagination']['has_prev'] is False

        # 获取第二页
        page2 = task_service.get_task_list(user_id, page=2, page_size=10)
        assert len(page2['tasks']) == 10
        assert page2['pagination']['current_page'] == 2
        assert page2['pagination']['has_next'] is True
        assert page2['pagination']['has_prev'] is True

        # 获取第三页
        page3 = task_service.get_task_list(user_id, page=3, page_size=10)
        assert len(page3['tasks']) == 5
        assert page3['pagination']['current_page'] == 3
        assert page3['pagination']['has_next'] is False
        assert page3['pagination']['has_prev'] is True

    def test_get_task_list_with_filters(self, task_service):
        """测试带筛选条件的任务列表"""
        user_id = str(uuid4())

        # 创建不同状态的任务
        task_service.create_task(
            user_id=user_id,
            title="待办任务",
            status=TaskStatusConst.PENDING
        )
        task_service.create_task(
            user_id=user_id,
            title="进行中任务",
            status=TaskStatusConst.IN_PROGRESS
        )
        task_service.create_task(
            user_id=user_id,
            title="已完成任务",
            status=TaskStatusConst.COMPLETED
        )

        # 筛选待办任务
        pending_tasks = task_service.get_task_list(
            user_id,
            filters={'status': TaskStatusConst.PENDING}
        )
        assert len(pending_tasks['tasks']) == 1
        assert pending_tasks['tasks'][0].title == "待办任务"

        # 筛选已完成任务
        completed_tasks = task_service.get_task_list(
            user_id,
            filters={'status': TaskStatusConst.COMPLETED}
        )
        assert len(completed_tasks['tasks']) == 1
        assert completed_tasks['tasks'][0].title == "已完成任务"

    def test_update_task_basic(self, task_service):
        """测试基本任务更新"""
        user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="原始标题",
            description="原始描述"
        )

        # 更新任务
        updated_task = task_service.update_task(
            task.id,
            user_id,
            {
                "title": "更新后的标题",
                "description": "更新后的描述",
                "status": TaskStatusConst.IN_PROGRESS,
                "completion_percentage": 50.0
            }
        )

        assert updated_task.id == task.id
        assert updated_task.title == "更新后的标题"
        assert updated_task.description == "更新后的描述"
        assert updated_task.status == TaskStatusConst.IN_PROGRESS
        assert updated_task.completion_percentage == 50.0

    def test_update_task_not_found(self, task_service):
        """测试更新不存在的任务"""
        user_id = str(uuid4())
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundException):
            task_service.update_task(fake_id, user_id, {"title": "新标题"})

    def test_update_task_permission_denied(self, task_service):
        """测试无权限更新任务"""
        user_id = str(uuid4())
        other_user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="原始标题"
        )

        # 其他用户尝试更新
        with pytest.raises(TaskPermissionDeniedException):
            task_service.update_task(task.id, other_user_id, {"title": "恶意修改"})

    def test_delete_task_basic(self, task_service):
        """测试基本任务删除"""
        user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="要删除的任务"
        )

        # 确认任务存在
        retrieved_task = task_service.get_task_by_id(task.id, user_id)
        assert retrieved_task is not None

        # 删除任务
        success = task_service.delete_task(task.id, user_id)
        assert success is True

        # 确认任务已删除
        deleted_task = task_service.get_task_by_id(task.id, user_id)
        assert deleted_task is None

    def test_delete_task_not_found(self, task_service):
        """测试删除不存在的任务"""
        user_id = str(uuid4())
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundException):
            task_service.delete_task(fake_id, user_id)

    def test_delete_task_permission_denied(self, task_service):
        """测试无权限删除任务"""
        user_id = str(uuid4())
        other_user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="受保护的任务"
        )

        # 其他用户尝试删除
        with pytest.raises(TaskPermissionDeniedException):
            task_service.delete_task(task.id, other_user_id)

    def test_get_task_statistics(self, task_service):
        """测试任务统计功能"""
        user_id = str(uuid4())

        # 创建不同状态的任务
        task_service.create_task(user_id=user_id, title="任务1", status=TaskStatusConst.PENDING)
        task_service.create_task(user_id=user_id, title="任务2", status=TaskStatusConst.PENDING)
        task_service.create_task(user_id=user_id, title="任务3", status=TaskStatusConst.IN_PROGRESS)
        task_service.create_task(user_id=user_id, title="任务4", status=TaskStatusConst.COMPLETED)

        # 获取统计信息
        stats = task_service.get_task_statistics(user_id)

        assert stats['pending'] == 2
        assert stats['in_progress'] == 1
        assert stats['completed'] == 1
        assert stats['total'] == 4

    def test_task_with_tags_and_services(self, task_service):
        """测试带标签和服务的任务"""
        user_id = str(uuid4())
        tags = ["开发", "Python", "测试"]
        service_ids = ["service-001", "service-002"]

        task = task_service.create_task(
            user_id=user_id,
            title="带标签的任务",
            description="测试JSON字段",
            tags=tags,
            service_ids=service_ids
        )

        # 验证JSON字段
        retrieved_task = task_service.get_task_by_id(task.id, user_id)
        assert retrieved_task.tags == tags
        assert retrieved_task.service_ids == service_ids

    def test_task_completion_with_date_validation(self, task_service):
        """测试任务完成时的日期验证"""
        user_id = str(uuid4())

        # 创建任务
        task = task_service.create_task(
            user_id=user_id,
            title="日期测试任务"
        )

        # 完成任务
        completed_task = task_service.complete_task(task.id, user_id)

        # 验证完成时间
        assert completed_task.completed_at is not None
        assert completed_task.completed_at.date() == datetime.now(timezone.utc).date()

    def test_bulk_complete_tasks(self, task_service):
        """测试批量完成任务"""
        user_id = str(uuid4())

        # 创建多个任务
        task_ids = []
        for i in range(3):
            task = task_service.create_task(
                user_id=user_id,
                title=f"批量任务 {i+1}"
            )
            task_ids.append(task.id)

        # 批量完成
        results = task_service.bulk_complete_tasks(task_ids, user_id)

        # 验证所有任务都已完成
        assert len(results) == 3
        for task in results:
            assert task.status == TaskStatusConst.COMPLETED

    def test_search_tasks_by_title(self, task_service):
        """测试按标题搜索任务"""
        user_id = str(uuid4())

        # 创建任务
        task_service.create_task(user_id=user_id, title="Python开发任务")
        task_service.create_task(user_id=user_id, title="JavaScript开发任务")
        task_service.create_task(user_id=user_id, title="系统管理")

        # 搜索包含"开发"的任务
        dev_tasks = task_service.search_tasks(user_id, "开发")
        assert len(dev_tasks) == 2

        # 搜索包含"Python"的任务
        python_tasks = task_service.search_tasks(user_id, "Python")
        assert len(python_tasks) == 1
        assert python_tasks[0].title == "Python开发任务"

    def test_task_priority_filtering(self, task_service):
        """测试按优先级筛选任务"""
        user_id = str(uuid4())

        # 创建不同优先级的任务
        task_service.create_task(
            user_id=user_id,
            title="高优先级任务",
            priority=TaskPriorityConst.HIGH
        )
        task_service.create_task(
            user_id=user_id,
            title="中优先级任务",
            priority=TaskPriorityConst.MEDIUM
        )
        task_service.create_task(
            user_id=user_id,
            title="低优先级任务",
            priority=TaskPriorityConst.LOW
        )

        # 筛选高优先级任务
        high_priority_tasks = task_service.get_task_list(
            user_id,
            filters={'priority': TaskPriorityConst.HIGH}
        )
        assert len(high_priority_tasks['tasks']) == 1
        assert high_priority_tasks['tasks'][0].priority == TaskPriorityConst.HIGH