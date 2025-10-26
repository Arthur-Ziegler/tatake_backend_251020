"""
Task域服务严格单元测试

对TaskService进行全面测试，包括业务逻辑、异常处理、边界条件等。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试
"""

import pytest
from unittest.mock import Mock, patch, call
from uuid import uuid4
from datetime import datetime, timezone, date
from typing import Dict, Any, List

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.task.exceptions import TaskNotFoundException, TaskPermissionDeniedException
from tests.unit.domains.task.conftest_strict import TaskTestDataFactory


@pytest.mark.unit
@pytest.mark.service
@pytest.mark.task
class TestTaskService:
    """TaskService测试类"""

    def test_task_service_initialization(self, mock_session: Mock):
        """测试TaskService初始化"""
        service = TaskService(mock_session)
        assert service.session is mock_session

    def test_create_task_success(self, task_service: TaskService, base_task_data: Dict[str, Any], sample_user_id: str):
        """测试成功创建任务"""
        # 配置Mock
        task_service.session.add = Mock()
        task_service.session.flush = Mock()
        task_service.session.commit = Mock()
        task_service.session.refresh = Mock()

        # 创建任务
        task_data = {**base_task_data, "user_id": sample_user_id}
        result = task_service.create_task(sample_user_id, task_data)

        # 验证结果
        assert isinstance(result, Task)
        assert result.user_id == sample_user_id
        assert result.title == task_data["title"]
        assert result.description == task_data["description"]
        assert result.status == task_data["status"]
        assert result.priority == task_data["priority"]

        # 验证数据库操作被调用
        task_service.session.add.assert_called_once()
        task_service.session.flush.assert_called_once()
        task_service.session.commit.assert_called_once()
        task_service.session.refresh.assert_called_once_with(result)

    def test_create_task_with_defaults(self, task_service: TaskService, sample_user_id: str):
        """测试使用默认值创建任务"""
        task_service.session.add = Mock()
        task_service.session.flush = Mock()
        task_service.session.commit = Mock()
        task_service.session.refresh = Mock()

        minimal_data = {"title": "最小任务"}
        result = task_service.create_task(sample_user_id, minimal_data)

        assert result.user_id == sample_user_id
        assert result.title == "最小任务"
        assert result.status == TaskStatusConst.PENDING
        assert result.priority == TaskPriorityConst.MEDIUM
        assert result.completion_percentage == 0.0
        assert result.is_deleted is False

    def test_create_task_with_invalid_data(self, task_service: TaskService, sample_user_id: str):
        """测试使用无效数据创建任务"""
        invalid_data = {"title": ""}  # 空标题

        with pytest.raises(Exception):
            task_service.create_task(sample_user_id, invalid_data)

        task_service.session.add.assert_not_called()
        task_service.session.commit.assert_not_called()

    def test_get_task_success(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试成功获取任务"""
        # 配置Mock查询
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        result = task_service.get_task(sample_task.id, sample_user_id)

        assert result is not None
        assert result.id == sample_task.id
        assert result.user_id == sample_user_id

    def test_get_task_not_found(self, task_service: TaskService, sample_task_id: str, sample_user_id: str):
        """测试获取不存在的任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = None
        task_service.session.query.return_value = mock_query

        result = task_service.get_task(sample_task_id, sample_user_id)

        assert result is None

    def test_get_task_permission_denied(self, task_service: TaskService, sample_task: Task):
        """测试获取无权限的任务"""
        other_user_id = str(uuid4())

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        result = task_service.get_task(sample_task.id, other_user_id)

        assert result is None

    def test_list_tasks_success(self, task_service: TaskService, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试成功列出任务"""
        # 创建测试数据
        tasks = task_test_data_factory.create_user_tasks(sample_user_id, 5)

        # 配置Mock查询
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = tasks
        task_service.session.query.return_value = mock_query

        result = task_service.list_tasks(sample_user_id)

        assert len(result) == 5
        assert all(task.user_id == sample_user_id for task in result)

    def test_list_tasks_with_filters(self, task_service: TaskService, sample_user_id: str):
        """测试带过滤条件的任务列表"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        task_service.session.query.return_value = mock_query

        # 测试状态过滤
        task_service.list_tasks(
            sample_user_id,
            status=TaskStatusConst.COMPLETED
        )
        mock_query.filter.assert_called()

        # 测试优先级过滤
        task_service.list_tasks(
            sample_user_id,
            priority=TaskPriorityConst.HIGH
        )
        mock_query.filter.assert_called()

        # 测试分页
        task_service.list_tasks(
            sample_user_id,
            limit=10,
            offset=20
        )
        mock_query.limit.assert_called_with(10)
        mock_query.offset.assert_called_with(20)

    def test_update_task_success(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试成功更新任务"""
        update_data = {
            "title": "更新后的标题",
            "description": "更新后的描述",
            "status": TaskStatusConst.IN_PROGRESS,
            "priority": TaskPriorityConst.HIGH
        }

        # 配置Mock
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()
        task_service.session.refresh = Mock()

        result = task_service.update_task(sample_task.id, sample_user_id, update_data)

        assert result is not None
        assert result.title == "更新后的标题"
        assert result.description == "更新后的描述"
        assert result.status == TaskStatusConst.IN_PROGRESS
        assert result.priority == TaskPriorityConst.HIGH
        assert result.updated_at > sample_task.updated_at

        task_service.session.flush.assert_called_once()
        task_service.session.commit.assert_called_once()

    def test_update_task_not_found(self, task_service: TaskService, sample_task_id: str, sample_user_id: str):
        """测试更新不存在的任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = None
        task_service.session.query.return_value = mock_query

        update_data = {"title": "更新标题"}

        with pytest.raises(TaskNotFoundException):
            task_service.update_task(sample_task_id, sample_user_id, update_data)

    def test_update_task_permission_denied(self, task_service: TaskService, sample_task: Task):
        """测试更新无权限的任务"""
        other_user_id = str(uuid4())
        update_data = {"title": "更新标题"}

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        with pytest.raises(TaskPermissionDeniedException):
            task_service.update_task(sample_task.id, other_user_id, update_data)

    def test_delete_task_success(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试成功删除任务（软删除）"""
        # 配置Mock
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()

        result = task_service.delete_task(sample_task.id, sample_user_id)

        assert result is True
        assert sample_task.is_deleted is True
        assert sample_task.updated_at > sample_task.updated_at

        task_service.session.flush.assert_called_once()
        task_service.session.commit.assert_called_once()

    def test_delete_task_not_found(self, task_service: TaskService, sample_task_id: str, sample_user_id: str):
        """测试删除不存在的任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = None
        task_service.session.query.return_value = mock_query

        with pytest.raises(TaskNotFoundException):
            task_service.delete_task(sample_task_id, sample_user_id)

    def test_complete_task_success(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试成功完成任务"""
        # 配置Mock
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()

        result = task_service.complete_task(sample_task.id, sample_user_id)

        assert result is True
        assert sample_task.status == TaskStatusConst.COMPLETED
        assert sample_task.completion_percentage == 100.0
        assert sample_task.last_claimed_date == date.today()
        assert sample_task.updated_at > sample_task.updated_at

    def test_complete_task_already_completed(self, task_service: TaskService, completed_task: Task, sample_user_id: str):
        """测试完成已完成的任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = completed_task
        task_service.session.query.return_value = mock_query

        result = task_service.complete_task(completed_task.id, sample_user_id)

        assert result is True  # 仍然返回成功，但不重复奖励

    def test_get_task_statistics(self, task_service: TaskService, sample_user_id: str):
        """测试获取任务统计"""
        # 配置Mock统计查询
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        task_service.session.query.return_value = mock_query

        stats = task_service.get_task_statistics(sample_user_id)

        assert "total" in stats
        assert "completed" in stats
        assert "pending" in stats
        assert "in_progress" in stats
        assert all(isinstance(v, int) for v in stats.values())

    def test_search_tasks_by_title(self, task_service: TaskService, sample_user_id: str):
        """测试按标题搜索任务"""
        keyword = "测试"

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        task_service.session.query.return_value = mock_query

        result = task_service.search_tasks_by_title(sample_user_id, keyword)

        assert isinstance(result, list)
        mock_query.filter.assert_called()  # 验证搜索条件被应用

    def test_get_tasks_due_soon(self, task_service: TaskService, sample_user_id: str):
        """测试获取即将到期的任务"""
        days = 7

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        task_service.session.query.return_value = mock_query

        result = task_service.get_tasks_due_soon(sample_user_id, days)

        assert isinstance(result, list)
        mock_query.where.assert_called()  # 验证时间条件被应用

    def test_get_parent_tasks(self, task_service: TaskService, sample_user_id: str):
        """测试获取父任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        task_service.session.query.return_value = mock_query

        result = task_service.get_parent_tasks(sample_user_id)

        assert isinstance(result, list)
        mock_query.where.assert_called()  # 验证parent_id条件被应用

    def test_get_child_tasks(self, task_service: TaskService, parent_task: Task):
        """测试获取子任务"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        task_service.session.query.return_value = mock_query

        result = task_service.get_child_tasks(parent_task.id)

        assert isinstance(result, list)
        mock_query.where.assert_called()  # 验证parent_id条件被应用

    def test_update_task_completion_percentage(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试更新任务完成百分比"""
        new_percentage = 75.5

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()

        result = task_service.update_task_completion_percentage(sample_task.id, sample_user_id, new_percentage)

        assert result is True
        assert sample_task.completion_percentage == new_percentage

    def test_database_error_handling(self, task_service: TaskService, sample_user_id: str):
        """测试数据库错误处理"""
        task_service.session.commit.side_effect = Exception("数据库连接失败")

        task_data = {"title": "测试任务"}

        with pytest.raises(Exception):
            task_service.create_task(sample_user_id, task_data)

        task_service.session.rollback.assert_called()

    @pytest.mark.parametrize("status", [
        TaskStatusConst.PENDING,
        TaskStatusConst.IN_PROGRESS,
        TaskStatusConst.COMPLETED
    ])
    def test_task_status_transitions(self, task_service: TaskService, sample_task: Task, sample_user_id: str, status: str):
        """测试任务状态转换"""
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()

        update_data = {"status": status}
        result = task_service.update_task(sample_task.id, sample_user_id, update_data)

        assert result.status == status

    @pytest.mark.slow
    def test_bulk_task_operations_performance(self, task_service: TaskService, task_test_data_factory: TaskTestDataFactory, performance_tracker):
        """测试批量任务操作性能"""
        sample_user_id = str(uuid4())
        tasks = task_test_data_factory.create_user_tasks(sample_user_id, 100)

        # 配置Mock
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = tasks
        task_service.session.query.return_value = mock_query

        performance_tracker.start()
        result = task_service.list_tasks(sample_user_id, limit=100)
        performance_tracker.stop()

        assert len(result) == 100
        assert performance_tracker.get_duration() < 0.5  # 应该在0.5秒内完成

    def test_task_validation_edge_cases(self, task_service: TaskService, sample_user_id: str):
        """测试任务验证边界情况"""
        # 测试无效的完成百分比
        with pytest.raises(Exception):
            task_service.create_task(sample_user_id, {
                "title": "测试任务",
                "completion_percentage": -1.0
            })

        with pytest.raises(Exception):
            task_service.create_task(sample_user_id, {
                "title": "测试任务",
                "completion_percentage": 101.0
            })

    def test_concurrent_task_modification(self, task_service: TaskService, sample_task: Task, sample_user_id: str):
        """测试并发任务修改"""
        # 模拟并发修改
        original_updated_at = sample_task.updated_at

        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.first.return_value = sample_task
        task_service.session.query.return_value = mock_query

        task_service.session.flush = Mock()
        task_service.session.commit = Mock()

        # 第一次更新
        task_service.update_task(sample_task.id, sample_user_id, {"title": "更新1"})

        # 第二次更新（应该有不同的时间戳）
        task_service.update_task(sample_task.id, sample_user_id, {"title": "更新2"})

        # 验证更新时间戳不同
        assert sample_task.updated_at > original_updated_at

    def test_task_service_error_propagation(self, task_service: TaskService, sample_user_id: str):
        """测试任务服务错误传播"""
        task_service.session.query.side_effect = Exception("数据库错误")

        with pytest.raises(Exception) as exc_info:
            task_service.get_task("invalid-id", sample_user_id)

        assert "数据库错误" in str(exc_info.value)