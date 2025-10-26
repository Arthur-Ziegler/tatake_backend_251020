"""
Task模型测试套件

测试Task模型的字段变化和基本功能，包括：
1. Task模型字段验证
2. last_claimed_date字段测试
3. 简化字段验证
4. JSON字段类型测试

遵循TDD原则，每个测试用例都有明确的预期结果和断言。
"""

import pytest
import uuid
from datetime import datetime, timezone, date
from uuid import UUID

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst


class TestTaskModel:
    """Task模型测试类"""

    def test_task_model_creation(self):
        """测试Task模型基本创建"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task(
            id=task_id,
            user_id=user_id,
            title="测试任务",
            description="这是一个测试任务",
            status=TaskStatusConst.PENDING,
            priority=TaskPriorityConst.MEDIUM
        )

        # 验证基本字段
        assert task.id == task_id
        assert task.user_id == user_id
        assert task.title == "测试任务"
        assert task.description == "这是一个测试任务"
        assert task.status == TaskStatusConst.PENDING
        assert task.priority == TaskPriorityConst.MEDIUM
        assert task.is_deleted is False
        assert task.completion_percentage == 0.0

    def test_task_model_last_claimed_date(self):
        """测试last_claimed_date字段"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()
        claimed_date = date(2023, 12, 25)

        task = Task(
            id=task_id,
            user_id=user_id,
            title="测试任务",
            last_claimed_date=claimed_date
        )

        # 验证防刷日期字段
        assert task.last_claimed_date == claimed_date

    def test_task_model_optional_fields(self):
        """测试可选字段默认值"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task(
            id=task_id,
            user_id=user_id,
            title="最简任务"
        )

        # 验证默认值
        assert task.description is None
        assert task.completion_percentage == 0.0
        assert task.last_claimed_date is None

    def test_task_model_json_fields(self):
        """测试JSON字段类型"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()
        tags = ["工作", "重要", "测试"]
        service_ids = ["service-001", "service-002"]

        task = Task(
            id=task_id,
            user_id=user_id,
            title="JSON字段测试",
            tags=tags,
            service_ids=service_ids
        )

        # 验证JSON字段
        assert task.tags == tags
        assert task.service_ids == service_ids

    def test_task_model_to_dict(self):
        """测试to_dict方法"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()
        tags = ["测试"]

        task = Task(
            id=task_id,
            user_id=user_id,
            title="字典转换测试",
            description="测试描述",
            status=TaskStatusConst.IN_PROGRESS,
            priority=TaskPriorityConst.HIGH,
            completion_percentage=50.0,
            tags=tags,
            service_ids=["service-001"]
        )

        result = task.to_dict()

        # 验证字典包含所有字段
        assert result["id"] == task_id
        assert result["user_id"] == user_id
        assert result["title"] == "字典转换测试"
        assert result["description"] == "测试描述"
        assert result["status"] == TaskStatusConst.IN_PROGRESS
        assert result["priority"] == TaskPriorityConst.HIGH
        assert result["completion_percentage"] == 50.0
        assert result["tags"] == tags
        assert result["service_ids"] == ["service-001"]

        # 验证不包含已删除的字段
        assert "parent_id" not in result
        assert "level" not in result
        assert "path" not in result
        assert "estimated_pomodoros" not in result
        assert "actual_pomodoros" not in result
        assert "last_claimed_date" not in result  # 该字段已在to_dict中移除

    def test_task_model_removed_fields(self):
        """验证已删除字段不存在"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task(
            id=task_id,
            user_id=user_id,
            title="删除字段验证"
        )

        # 验证删除的字段不存在
        assert not hasattr(task, 'estimated_pomodoros')
        assert not hasattr(task, 'actual_pomodoros')
        assert not hasattr(task, 'level')
        assert not hasattr(task, 'path')

    def test_task_model_validation(self):
        """测试字段值范围"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # 测试创建时字段值在允许范围内（这些值会在数据库插入时验证）
        # Pydantic 的 Field 约束主要通过验证器验证，这里只测试基本创建
        task = Task(
                id=task_id,
                user_id=user_id,
                title="字段验证测试",
                completion_percentage=50.0  # 有效范围内的值
            )

        assert task.completion_percentage == 50.0

        # 测试边界值
        task_min = Task(
                id=uuid.uuid4(),
                user_id=user_id,
                title="最小值测试",
                completion_percentage=0.0  # 最小值
            )
        assert task_min.completion_percentage == 0.0

        task_max = Task(
                id=uuid.uuid4(),
                user_id=user_id,
                title="最大值测试",
                completion_percentage=100.0  # 最大值
            )
        assert task_max.completion_percentage == 100.0

    def test_task_model_string_representation(self):
        """测试字符串表示"""
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task(
            id=task_id,
            user_id=user_id,
            title="字符串测试",
            status=TaskStatusConst.COMPLETED
        )

        repr_str = repr(task)

        # 验证字符串包含关键信息
        assert "Task" in repr_str
        assert str(task_id) in repr_str
        assert "字符串测试" in repr_str
        assert TaskStatusConst.COMPLETED in repr_str
        assert str(user_id) in repr_str