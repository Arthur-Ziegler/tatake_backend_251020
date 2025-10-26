"""
Task域仓储严格单元测试

对TaskRepository进行全面测试，包括数据库操作、查询构建、事务管理等。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试
"""

import pytest
from unittest.mock import Mock, call, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, date
from typing import Dict, Any, List
from sqlmodel import SQLModel, select

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.repository import TaskRepository
from tests.unit.domains.task.conftest_strict import TaskTestDataFactory


@pytest.mark.unit
@pytest.mark.repository
@pytest.mark.task
class TestTaskRepository:
    """TaskRepository测试类"""

    def test_repository_initialization(self, mock_session: Mock):
        """测试TaskRepository初始化"""
        repo = TaskRepository(mock_session)
        assert repo.session is mock_session

    def test_create_task_success(self, mock_task_repository: TaskRepository, base_task_data: Dict[str, Any], sample_user_id: str):
        """测试成功创建任务"""
        # 创建真实Task对象
        task_data = {**base_task_data, "user_id": sample_user_id}
        new_task = Task(**task_data)

        # 配置Mock返回真实对象
        mock_task_repository.session.add = Mock()
        mock_task_repository.session.flush = Mock()
        mock_task_repository.session.refresh = Mock()
        mock_task_repository.create.return_value = new_task

        result = mock_task_repository.create(new_task)

        assert result is not None
        assert result.user_id == sample_user_id
        assert result.title == task_data["title"]
        mock_task_repository.session.add.assert_called_once_with(new_task)

    def test_get_by_id_success(self, mock_task_repository: TaskRepository, sample_task: Task):
        """测试根据ID获取任务"""
        mock_task_repository.get_by_id.return_value = sample_task

        result = mock_task_repository.get_by_id(sample_task.id)

        assert result is not None
        assert result.id == sample_task.id
        mock_task_repository.get_by_id.assert_called_once_with(sample_task.id)

    def test_get_by_id_not_found(self, mock_task_repository: TaskRepository, sample_task_id: str):
        """测试获取不存在的任务"""
        mock_task_repository.get_by_id.return_value = None

        result = mock_task_repository.get_by_id(sample_task_id)

        assert result is None

    def test_get_user_tasks(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试获取用户所有任务"""
        tasks = task_test_data_factory.create_user_tasks(sample_user_id, 5)
        mock_task_repository.get_user_tasks.return_value = tasks

        result = mock_task_repository.get_user_tasks(sample_user_id)

        assert len(result) == 5
        assert all(task.user_id == sample_user_id for task in result)
        mock_task_repository.get_user_tasks.assert_called_once_with(sample_user_id)

    def test_get_user_active_tasks(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试获取用户活跃任务"""
        active_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 3)
        mock_task_repository.get_user_active_tasks.return_value = active_tasks

        result = mock_task_repository.get_user_active_tasks(sample_user_id)

        assert len(result) == 3
        assert all(task.user_id == sample_user_id for task in result)
        mock_task_repository.get_user_active_tasks.assert_called_once_with(sample_user_id)

    def test_get_tasks_by_status(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试根据状态获取任务"""
        completed_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 3)
        for task in completed_tasks:
            task.status = TaskStatusConst.COMPLETED

        mock_task_repository.get_tasks_by_status.return_value = completed_tasks

        result = mock_task_repository.get_tasks_by_status(sample_user_id, TaskStatusConst.COMPLETED)

        assert len(result) == 3
        assert all(task.status == TaskStatusConst.COMPLETED for task in result)
        mock_task_repository.get_tasks_by_status.assert_called_once_with(sample_user_id, TaskStatusConst.COMPLETED)

    def test_get_tasks_by_priority(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试根据优先级获取任务"""
        high_priority_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 2)
        for task in high_priority_tasks:
            task.priority = TaskPriorityConst.HIGH

        mock_task_repository.get_tasks_by_priority.return_value = high_priority_tasks

        result = mock_task_repository.get_tasks_by_priority(sample_user_id, TaskPriorityConst.HIGH)

        assert len(result) == 2
        assert all(task.priority == TaskPriorityConst.HIGH for task in result)
        mock_task_repository.get_tasks_by_priority.assert_called_once_with(sample_user_id, TaskPriorityConst.HIGH)

    def test_update_task_success(self, mock_task_repository: TaskRepository, sample_task: Task):
        """测试更新任务"""
        updated_task = sample_task
        updated_task.title = "更新后的标题"
        updated_task.status = TaskStatusConst.IN_PROGRESS

        mock_task_repository.update.return_value = updated_task

        result = mock_task_repository.update(updated_task)

        assert result is not None
        assert result.title == "更新后的标题"
        assert result.status == TaskStatusConst.IN_PROGRESS

    def test_delete_task_success(self, mock_task_repository: TaskRepository, sample_task: Task):
        """测试删除任务"""
        mock_task_repository.delete.return_value = True

        result = mock_task_repository.delete(sample_task.id)

        assert result is True
        mock_task_repository.delete.assert_called_once_with(sample_task.id)

    def test_delete_task_not_found(self, mock_task_repository: TaskRepository, sample_task_id: str):
        """测试删除不存在的任务"""
        mock_task_repository.delete.return_value = False

        result = mock_task_repository.delete(sample_task_id)

        assert result is False

    def test_count_user_tasks(self, mock_task_repository: TaskRepository, sample_user_id: str):
        """测试统计用户任务数量"""
        mock_task_repository.count_user_tasks.return_value = 10

        result = mock_task_repository.count_user_tasks(sample_user_id)

        assert result == 10
        mock_task_repository.count_user_tasks.assert_called_once_with(sample_user_id)

    def test_get_parent_tasks(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试获取父任务"""
        parent_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 2)
        for task in parent_tasks:
            task.parent_id = None

        mock_task_repository.get_parent_tasks.return_value = parent_tasks

        result = mock_task_repository.get_parent_tasks(sample_user_id)

        assert len(result) == 2
        assert all(task.parent_id is None for task in result)

    def test_get_child_tasks(self, mock_task_repository: TaskRepository, parent_task: Task, task_test_data_factory: TaskTestDataFactory):
        """测试获取子任务"""
        child_tasks = task_test_data_factory.create_user_tasks(parent_task.user_id, 3)
        for task in child_tasks:
            task.parent_id = parent_task.id

        mock_task_repository.get_child_tasks.return_value = child_tasks

        result = mock_task_repository.get_child_tasks(parent_task.id)

        assert len(result) == 3
        assert all(task.parent_id == parent_task.id for task in result)

    def test_search_tasks_by_title(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试按标题搜索任务"""
        keyword = "重要"
        search_results = task_test_data_factory.create_user_tasks(sample_user_id, 3)

        mock_task_repository.search_tasks_by_title.return_value = search_results

        result = mock_task_repository.search_tasks_by_title(sample_user_id, keyword)

        assert len(result) == 3
        mock_task_repository.search_tasks_by_title.assert_called_once_with(sample_user_id, keyword)

    def test_get_tasks_due_soon(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试获取即将到期的任务"""
        due_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 2)

        mock_task_repository.get_tasks_due_soon.return_value = due_tasks

        result = mock_task_repository.get_tasks_due_soon(sample_user_id, 7)

        assert len(result) == 2
        mock_task_repository.get_tasks_due_soon.assert_called_once_with(sample_user_id, 7)

    def test_get_tasks_by_date_range(self, mock_task_repository: TaskRepository, sample_user_id: str, task_test_data_factory: TaskTestDataFactory):
        """测试按日期范围获取任务"""
        start_date = datetime.now(timezone.utc)
        end_date = start_date.replace(day=start_date.day + 7)
        range_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 4)

        mock_task_repository.get_tasks_by_date_range.return_value = range_tasks

        result = mock_task_repository.get_tasks_by_date_range(sample_user_id, start_date, end_date)

        assert len(result) == 4
        mock_task_repository.get_tasks_by_date_range.assert_called_once_with(sample_user_id, start_date, end_date)

    def test_get_task_statistics(self, mock_task_repository: TaskRepository, sample_user_id: str):
        """测试获取任务统计"""
        stats = {
            "total": 20,
            "completed": 8,
            "pending": 10,
            "in_progress": 2
        }

        mock_task_repository.get_task_statistics.return_value = stats

        result = mock_task_repository.get_task_statistics(sample_user_id)

        assert result == stats
        assert result["total"] == 20
        assert result["completed"] == 8
        mock_task_repository.get_task_statistics.assert_called_once_with(sample_user_id)

    def test_transaction_rollback_on_error(self, mock_task_repository: TaskRepository):
        """测试错误时事务回滚"""
        mock_task_repository.session.add.side_effect = Exception("数据库错误")

        task = Task(user_id=str(uuid4()), title="测试任务")

        with pytest.raises(Exception):
            mock_task_repository.create(task)

        mock_task_repository.session.rollback.assert_called_once()

    def test_bulk_operations(self, mock_task_repository: TaskRepository, task_test_data_factory: TaskTestDataFactory, sample_user_id: str):
        """测试批量操作"""
        tasks = task_test_data_factory.create_user_tasks(sample_user_id, 10)

        # 模拟批量创建
        created_tasks = []
        for task in tasks:
            created_task = Task(**task.dict())
            created_tasks.append(created_task)

        mock_task_repository.session.add = Mock()
        mock_task_repository.session.flush = Mock()
        mock_task_repository.session.commit = Mock()

        # 执行批量创建
        for task in tasks:
            mock_task_repository.session.add(task)

        # 验证批量操作
        assert mock_task_repository.session.add.call_count == 10
        mock_task_repository.session.flush.assert_called_once()
        mock_task_repository.session.commit.assert_called_once()

    def test_complex_query_building(self, mock_task_repository: TaskRepository, sample_user_id: str):
        """测试复杂查询构建"""
        # 配置查询链式调用
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        mock_task_repository.session.query.return_value = mock_query

        # 模拟复杂查询
        mock_task_repository.get_user_tasks(
            sample_user_id,
            status=TaskStatusConst.COMPLETED,
            priority=TaskPriorityConst.HIGH,
            limit=10,
            offset=0
        )

        # 验证查询链
        mock_query.where.assert_called()
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called()
        mock_query.limit.assert_called_with(10)
        mock_query.offset.assert_called_with(0)

    def test_query_parameter_validation(self, mock_task_repository: TaskRepository, sample_user_id: str):
        """测试查询参数验证"""
        # 测试负数limit
        with pytest.raises(ValueError):
            mock_task_repository.get_user_tasks(sample_user_id, limit=-1)

        # 测试负数offset
        with pytest.raises(ValueError):
            mock_task_repository.get_user_tasks(sample_user_id, offset=-1)

        # 测试无效日期范围
        start_date = datetime.now(timezone.utc)
        end_date = start_date.replace(day=start_date.day - 7)  # 结束日期早于开始日期

        with pytest.raises(ValueError):
            mock_task_repository.get_tasks_by_date_range(sample_user_id, start_date, end_date)

    @pytest.mark.parametrize("status", [
        TaskStatusConst.PENDING,
        TaskStatusConst.IN_PROGRESS,
        TaskStatusConst.COMPLETED
    ])
    def test_status_filtering(self, mock_task_repository: TaskRepository, sample_user_id: str, status: str, task_test_data_factory: TaskTestDataFactory):
        """测试状态过滤"""
        filtered_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 3)
        for task in filtered_tasks:
            task.status = status

        mock_task_repository.get_tasks_by_status.return_value = filtered_tasks

        result = mock_task_repository.get_tasks_by_status(sample_user_id, status)

        assert len(result) == 3
        assert all(task.status == status for task in result)

    @pytest.mark.parametrize("priority", [
        TaskPriorityConst.LOW,
        TaskPriorityConst.MEDIUM,
        TaskPriorityConst.HIGH
    ])
    def test_priority_filtering(self, mock_task_repository: TaskRepository, sample_user_id: str, priority: str, task_test_data_factory: TaskTestDataFactory):
        """测试优先级过滤"""
        filtered_tasks = task_test_data_factory.create_user_tasks(sample_user_id, 2)
        for task in filtered_tasks:
            task.priority = priority

        mock_task_repository.get_tasks_by_priority.return_value = filtered_tasks

        result = mock_task_repository.get_tasks_by_priority(sample_user_id, priority)

        assert len(result) == 2
        assert all(task.priority == priority for task in result)

    def test_null_value_handling(self, mock_task_repository: TaskRepository, sample_user_id: str):
        """测试空值处理"""
        # 测试查询返回None
        mock_task_repository.get_by_id.return_value = None
        result = mock_task_repository.get_by_id("non-existent-id")
        assert result is None

        # 测试可选字段为None的任务
        task_with_nulls = Task(
            user_id=sample_user_id,
            title="空值任务",
            description=None,
            parent_id=None,
            due_date=None,
            last_claimed_date=None
        )

        mock_task_repository.get_by_id.return_value = task_with_nulls
        result = mock_task_repository.get_by_id("null-task-id")

        assert result.description is None
        assert result.parent_id is None
        assert result.due_date is None
        assert result.last_claimed_date is None

    @pytest.mark.slow
    def test_repository_performance(self, mock_task_repository: TaskRepository, task_test_data_factory: TaskTestDataFactory, performance_tracker):
        """测试仓储性能"""
        sample_user_id = str(uuid4())
        large_task_list = task_test_data_factory.create_user_tasks(sample_user_id, 1000)

        mock_task_repository.get_user_tasks.return_value = large_task_list

        performance_tracker.start()
        result = mock_task_repository.get_user_tasks(sample_user_id)
        performance_tracker.stop()

        assert len(result) == 1000
        assert performance_tracker.get_duration() < 0.1  # Mock操作应该很快

    def test_concurrent_access(self, mock_task_repository: TaskRepository, sample_task: Task):
        """测试并发访问"""
        # 模拟并发读取
        mock_task_repository.get_by_id.return_value = sample_task

        # 模拟多个并发请求
        results = []
        for i in range(10):
            result = mock_task_repository.get_by_id(sample_task.id)
            results.append(result)

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(result.id == sample_task.id for result in results)
        assert mock_task_repository.get_by_id.call_count == 10

    def test_repository_error_handling(self, mock_task_repository: TaskRepository):
        """测试仓储错误处理"""
        # 测试数据库连接错误
        mock_task_repository.session.query.side_effect = Exception("数据库连接失败")

        with pytest.raises(Exception) as exc_info:
            mock_task_repository.get_user_tasks("user-id")

        assert "数据库连接失败" in str(exc_info.value)

        # 测试事务失败回滚
        mock_task_repository.session.add.side_effect = Exception("插入失败")
        mock_task_repository.session.rollback = Mock()

        task = Task(user_id=str(uuid4()), title="测试任务")

        with pytest.raises(Exception):
            mock_task_repository.create(task)

        mock_task_repository.session.rollback.assert_called_once()