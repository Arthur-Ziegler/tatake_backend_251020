"""
Task领域Repository简化测试

测试TaskRepository的基本功能，采用TDD方法。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from uuid import uuid4

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.repository import TaskRepository


@pytest.mark.unit
class TestTaskRepository:
    """TaskRepository测试类"""

    def test_create_task(self, task_repository):
        """测试创建任务"""
        user_id = str(uuid4())

        task = task_repository.create({
            "user_id": user_id,
            "title": "新建测试任务",
            "description": "这是一个新创建的测试任务",
            "priority": TaskPriorityConst.HIGH
        })

        assert task.id is not None
        assert task.user_id == user_id
        assert task.title == "新建测试任务"
        assert task.description == "这是一个新创建的测试任务"
        assert task.priority == TaskPriorityConst.HIGH
        assert task.status == TaskStatusConst.PENDING
        assert task.is_deleted is False
        assert task.created_at is not None

    def test_get_task_by_id(self, task_repository):
        """测试根据ID获取任务"""
        user_id = str(uuid4())

        # 创建任务
        created_task = task_repository.create({
            "user_id": user_id,
            "title": "获取测试任务"
        })

        # 获取任务
        retrieved_task = task_repository.get_by_id(created_task.id, user_id)

        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == "获取测试任务"

    def test_get_task_by_id_not_found(self, task_repository):
        """测试获取不存在的任务"""
        fake_id = str(uuid4())
        user_id = str(uuid4())
        task = task_repository.get_by_id(fake_id, user_id)
        assert task is None

    def test_update_task(self, task_repository):
        """测试更新任务"""
        user_id = str(uuid4())

        # 创建任务
        task = task_repository.create({
            "user_id": user_id,
            "title": "原始标题",
            "status": TaskStatusConst.PENDING
        })

        # 更新任务
        updated_task = task_repository.update(task.id, user_id, {
            "title": "更新后的标题",
            "description": "添加描述",
            "status": TaskStatusConst.IN_PROGRESS,
            "completion_percentage": 50.0
        })

        assert updated_task.id == task.id
        assert updated_task.title == "更新后的标题"
        assert updated_task.description == "添加描述"
        assert updated_task.status == TaskStatusConst.IN_PROGRESS
        assert updated_task.completion_percentage == 50.0

    def test_soft_delete_task(self, task_repository):
        """测试软删除任务"""
        user_id = str(uuid4())

        # 创建任务
        task = task_repository.create({
            "user_id": user_id,
            "title": "要删除的任务"
        })

        # 确认任务存在
        assert task_repository.get_by_id(task.id, user_id) is not None

        # 软删除任务
        task_repository.soft_delete(task.id, user_id)

        # 确认任务已删除
        deleted_task = task_repository.get_by_id(task.id, user_id)
        assert deleted_task is None or deleted_task.is_deleted is True

    def test_task_with_tags_and_services(self, task_repository):
        """测试带有标签和服务的任务"""
        user_id = str(uuid4())
        tags = ["开发", "Python"]
        service_ids = ["service-001", "service-002"]

        task = task_repository.create({
            "user_id": user_id,
            "title": "带标签的任务",
            "tags": tags,
            "service_ids": service_ids
        })

        # 验证JSON字段
        assert task.tags == tags
        assert task.service_ids == service_ids