"""
Task域模型严格单元测试

对Task模型进行全面测试，包括字段验证、方法调用、边界条件等。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试
"""

import pytest
from datetime import datetime, timezone, date
from typing import Dict, Any
from uuid import uuid4

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from tests.unit.domains.task.conftest_strict import TaskTestDataFactory


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.task
class TestTaskModel:
    """Task模型测试类"""

    def test_task_creation_with_minimal_data(self, sample_user_id: str):
        """测试使用最小数据创建Task"""
        task = Task(
            user_id=sample_user_id,
            title="最小任务"
        )

        assert task.id is not None
        assert task.user_id == sample_user_id
        assert task.title == "最小任务"
        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM
        assert task.completion_percentage == 0.0
        assert task.is_deleted is False
        assert task.parent_id is None
        assert task.description is None
        assert task.tags == []
        assert task.service_ids == []
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_creation_with_full_data(self, base_task_data: Dict[str, Any], sample_user_id: str):
        """测试使用完整数据创建Task"""
        full_data = {
            **base_task_data,
            "user_id": sample_user_id,
            "id": str(uuid4()),
            "completion_percentage": 50.0,
            "service_ids": ["service1", "service2"]
        }

        task = Task(**full_data)

        assert task.id == full_data["id"]
        assert task.user_id == sample_user_id
        assert task.title == full_data["title"]
        assert task.description == full_data["description"]
        assert task.status == full_data["status"]
        assert task.priority == full_data["priority"]
        assert task.tags == full_data["tags"]
        assert task.service_ids == full_data["service_ids"]
        assert task.completion_percentage == 50.0

    def test_task_field_validation(self, sample_user_id: str):
        """测试Task字段验证"""
        # 测试必填字段
        with pytest.raises(Exception):  # SQLModel验证异常
            Task()  # 缺少user_id

        with pytest.raises(Exception):
            Task(user_id=sample_user_id)  # 缺少title

        # 测试字段长度限制
        with pytest.raises(Exception):
            Task(
                user_id=sample_user_id,
                title="a" * 101  # 超过100字符限制
            )

        # 测试completion_percentage范围
        with pytest.raises(Exception):
            Task(
                user_id=sample_user_id,
                title="测试任务",
                completion_percentage=-1.0  # 小于0
            )

        with pytest.raises(Exception):
            Task(
                user_id=sample_user_id,
                title="测试任务",
                completion_percentage=101.0  # 大于100
            )

    def test_task_default_values(self, sample_user_id: str):
        """测试Task默认值"""
        task = Task(
            user_id=sample_user_id,
            title="默认值测试"
        )

        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM
        assert task.completion_percentage == 0.0
        assert task.is_deleted is False
        assert task.tags == []
        assert task.service_ids == []
        assert task.parent_id is None
        assert task.description is None
        assert task.due_date is None
        assert task.planned_start_time is None
        assert task.planned_end_time is None
        assert task.last_claimed_date is None

    def test_task_to_dict(self, sample_task: Task):
        """测试Task.to_dict方法"""
        result = sample_task.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == sample_task.id
        assert result["user_id"] == sample_task.user_id
        assert result["title"] == sample_task.title
        assert result["status"] == sample_task.status
        assert result["priority"] == sample_task.priority
        assert result["completion_percentage"] == sample_task.completion_percentage
        assert result["is_deleted"] == sample_task.is_deleted
        assert result["tags"] == sample_task.tags
        assert result["service_ids"] == sample_task.service_ids
        assert "created_at" in result
        assert "updated_at" in result

    def test_task_to_dict_with_optional_fields(self, sample_user_id: str):
        """测试包含可选字段的Task.to_dict"""
        test_date = date.today()
        task = Task(
            user_id=sample_user_id,
            title="完整字段测试",
            description="测试描述",
            last_claimed_date=test_date,
            tags=["标签1", "标签2"],
            service_ids=["service1"]
        )

        result = task.to_dict()

        assert result["description"] == "测试描述"
        assert result["last_claimed_date"] == test_date.isoformat()
        assert result["tags"] == ["标签1", "标签2"]
        assert result["service_ids"] == ["service1"]

    def test_task_is_root_node(self, sample_task: Task, parent_task: Task, child_task: Task):
        """测试Task.is_root_node方法"""
        assert sample_task.is_root_node() is True  # 没有parent_id
        assert parent_task.is_root_node() is True  # 没有parent_id
        assert child_task.is_root_node() is False  # 有parent_id

    def test_task_is_leaf_node(self, sample_task: Task):
        """测试Task.is_leaf_node方法"""
        # 这个方法需要数据库查询，所以总是返回False
        assert sample_task.is_leaf_node() is False

    def test_task_repr(self, sample_task: Task):
        """测试Task.__repr__方法"""
        repr_str = repr(sample_task)

        assert isinstance(repr_str, str)
        assert sample_task.id in repr_str
        assert sample_task.title in repr_str
        assert sample_task.status in repr_str
        assert sample_task.priority in repr_str
        assert sample_task.user_id in repr_str

    @pytest.mark.parametrize("status,expected", [
        (TaskStatusConst.PENDING, "pending"),
        (TaskStatusConst.IN_PROGRESS, "in_progress"),
        (TaskStatusConst.COMPLETED, "completed")
    ])
    def test_task_status_values(self, sample_user_id: str, status: str, expected: str):
        """测试任务状态值"""
        task = Task(
            user_id=sample_user_id,
            title="状态测试",
            status=status
        )
        assert task.status == expected

    @pytest.mark.parametrize("priority,expected", [
        (TaskPriorityConst.LOW, "low"),
        (TaskPriorityConst.MEDIUM, "medium"),
        (TaskPriorityConst.HIGH, "high")
    ])
    def test_task_priority_values(self, sample_user_id: str, priority: str, expected: str):
        """测试任务优先级值"""
        task = Task(
            user_id=sample_user_id,
            title="优先级测试",
            priority=priority
        )
        assert task.priority == expected

    def test_task_json_fields(self, sample_user_id: str):
        """测试JSON类型字段"""
        tags = ["工作", "重要", "紧急"]
        service_ids = ["service1", "service2"]

        task = Task(
            user_id=sample_user_id,
            title="JSON字段测试",
            tags=tags,
            service_ids=service_ids
        )

        assert task.tags == tags
        assert task.service_ids == service_ids

        # 测试空列表
        task_empty = Task(
            user_id=sample_user_id,
            title="空JSON字段测试"
        )
        assert task_empty.tags == []
        assert task_empty.service_ids == []

    def test_task_time_fields(self, sample_user_id: str, current_datetime: datetime, future_datetime: datetime):
        """测试时间字段"""
        task = Task(
            user_id=sample_user_id,
            title="时间字段测试",
            due_date=future_datetime,
            planned_start_time=current_datetime,
            planned_end_time=future_datetime
        )

        assert task.due_date == future_datetime
        assert task.planned_start_time == current_datetime
        assert task.planned_end_time == future_datetime
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_last_claimed_date(self, sample_user_id: str, current_date: date):
        """测试最后领奖日期字段"""
        task = Task(
            user_id=sample_user_id,
            title="领奖日期测试",
            last_claimed_date=current_date
        )

        assert task.last_claimed_date == current_date

    def test_task_soft_delete(self, sample_user_id: str):
        """测试软删除字段"""
        task = Task(
            user_id=sample_user_id,
            title="软删除测试",
            is_deleted=True
        )

        assert task.is_deleted is True

    def test_task_hierarchy_fields(self, sample_user_id: str, sample_task_id: str):
        """测试层级字段"""
        task = Task(
            user_id=sample_user_id,
            title="层级测试",
            parent_id=sample_task_id
        )

        assert task.parent_id == sample_task_id

    def test_task_completion_percentage_boundaries(self, sample_user_id: str):
        """测试完成度边界值"""
        # 测试0%
        task_0 = Task(
            user_id=sample_user_id,
            title="0%完成",
            completion_percentage=0.0
        )
        assert task_0.completion_percentage == 0.0

        # 测试100%
        task_100 = Task(
            user_id=sample_user_id,
            title="100%完成",
            completion_percentage=100.0
        )
        assert task_100.completion_percentage == 100.0

        # 测试中间值
        task_50 = Task(
            user_id=sample_user_id,
            title="50%完成",
            completion_percentage=50.5
        )
        assert task_50.completion_percentage == 50.5

    def test_task_create_example_method(self, sample_user_id: str):
        """测试Task.create_example类方法"""
        task = Task.create_example(
            user_id=sample_user_id,
            title="示例任务",
            description="示例描述"
        )

        assert isinstance(task, Task)
        assert task.user_id == str(sample_user_id)
        assert task.title == "示例任务"
        assert task.description == "示例描述"
        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM

    def test_task_uuid_generation(self, sample_user_id: str):
        """测试UUID自动生成"""
        task1 = Task(user_id=sample_user_id, title="任务1")
        task2 = Task(user_id=sample_user_id, title="任务2")

        assert task1.id is not None
        assert task2.id is not None
        assert task1.id != task2.id
        assert isinstance(task1.id, str)
        assert isinstance(task2.id, str)

    def test_task_automatic_timestamps(self, sample_user_id: str):
        """测试自动时间戳"""
        before_creation = datetime.now(timezone.utc)

        task = Task(user_id=sample_user_id, title="时间戳测试")

        after_creation = datetime.now(timezone.utc)

        assert task.created_at >= before_creation
        assert task.created_at <= after_creation
        assert task.updated_at >= before_creation
        assert task.updated_at <= after_creation
        assert task.created_at == task.updated_at

    @pytest.mark.slow
    def test_task_bulk_creation_performance(self, task_test_data_factory: TaskTestDataFactory, performance_tracker):
        """测试批量创建Task的性能"""
        performance_tracker.start()

        tasks = []
        for i in range(1000):
            task = task_test_data_factory.create_task(title=f"性能测试任务{i}")
            tasks.append(task)

        performance_tracker.stop()

        assert len(tasks) == 1000
        assert performance_tracker.get_duration() < 1.0  # 应该在1秒内完成
        assert all(isinstance(task.id, str) for task in tasks)

    def test_task_edge_cases(self, sample_user_id: str):
        """测试Task边界情况"""
        # 测试空字符串标题
        with pytest.raises(Exception):
            Task(user_id=sample_user_id, title="")

        # 测试只有空格的标题
        with pytest.raises(Exception):
            Task(user_id=sample_user_id, title="   ")

        # 测试非常长的标题（刚好在边界）
        long_title = "a" * 100
        task = Task(user_id=sample_user_id, title=long_title)
        assert task.title == long_title

        # 测试特殊字符标题
        special_title = "测试任务！@#￥%……&*（）——+"
        task = Task(user_id=sample_user_id, title=special_title)
        assert task.title == special_title

    def test_task_field_types(self, sample_task: Task):
        """测试Task字段类型"""
        assert isinstance(sample_task.id, str)
        assert isinstance(sample_task.user_id, str)
        assert isinstance(sample_task.title, str)
        assert isinstance(sample_task.status, str)
        assert isinstance(sample_task.priority, str)
        assert isinstance(sample_task.completion_percentage, float)
        assert isinstance(sample_task.is_deleted, bool)
        assert isinstance(sample_task.tags, list)
        assert isinstance(sample_task.service_ids, list)
        assert isinstance(sample_task.created_at, datetime)
        assert isinstance(sample_task.updated_at, datetime)


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.task
class TestTaskModelRelationships:
    """Task模型关系测试类"""

    def test_task_parent_child_relationship(self, parent_task: Task, child_task: Task):
        """测试父子任务关系"""
        assert child_task.parent_id == parent_task.id
        assert parent_task.parent_id is None

    def test_task_self_reference_potential(self, sample_task: Task):
        """测试Task自引用潜在问题"""
        # 测试任务不能引用自己作为父任务
        with pytest.raises(Exception):
            Task(
                user_id=sample_task.user_id,
                title="自引用测试",
                parent_id=sample_task.id
            )


@pytest.mark.unit
@pytest.mark.model
@pytest.mark.task
class TestTaskModelConstants:
    """Task模型常量测试类"""

    def test_task_status_const_values(self):
        """测试TaskStatusConst常量值"""
        assert hasattr(TaskStatusConst, 'PENDING')
        assert hasattr(TaskStatusConst, 'IN_PROGRESS')
        assert hasattr(TaskStatusConst, 'COMPLETED')

        assert TaskStatusConst.PENDING == "pending"
        assert TaskStatusConst.IN_PROGRESS == "in_progress"
        assert TaskStatusConst.COMPLETED == "completed"

    def test_task_priority_const_values(self):
        """测试TaskPriorityConst常量值"""
        assert hasattr(TaskPriorityConst, 'LOW')
        assert hasattr(TaskPriorityConst, 'MEDIUM')
        assert hasattr(TaskPriorityConst, 'HIGH')

        assert TaskPriorityConst.LOW == "low"
        assert TaskPriorityConst.MEDIUM == "medium"
        assert TaskPriorityConst.HIGH == "high"