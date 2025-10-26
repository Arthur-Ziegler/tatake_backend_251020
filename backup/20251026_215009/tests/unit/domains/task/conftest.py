"""
Task域测试配置和Fixtures

提供task域专用的测试环境配置。

作者：TaKeKe团队
版本：2.0.0
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timezone, date
from typing import Dict, Any, List

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst


@pytest.fixture(scope="function")
def sample_user_id() -> str:
    """示例用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_task_id() -> str:
    """示例任务ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def base_task_data() -> Dict[str, Any]:
    """基础任务数据"""
    return {
        "title": "测试任务",
        "description": "这是一个测试任务",
        "status": TaskStatusConst.PENDING,
        "priority": TaskPriorityConst.MEDIUM,
        "tags": ["测试", "单元测试"],
        "estimated_minutes": 30,
        "due_date": None,
        "parent_id": None
    }


@pytest.fixture(scope="function")
def sample_task(base_task_data: Dict[str, Any], sample_user_id: str) -> Task:
    """示例任务对象"""
    task_data = {
        **base_task_data,
        "id": str(uuid4()),
        "user_id": sample_user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completion_percentage": 0.0,
        "is_deleted": False,
        "last_claimed_date": None
    }
    return Task(**task_data)


@pytest.fixture(scope="function")
def completed_task(sample_task: Task) -> Task:
    """已完成的任务对象"""
    sample_task.status = TaskStatusConst.COMPLETED
    sample_task.completion_percentage = 100.0
    sample_task.last_claimed_date = date.today()
    return sample_task


@pytest.fixture(scope="function")
def parent_task(base_task_data: Dict[str, Any], sample_user_id: str) -> Task:
    """父任务对象"""
    task_data = {
        **base_task_data,
        "id": str(uuid4()),
        "user_id": sample_user_id,
        "title": "父任务",
        "parent_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completion_percentage": 0.0,
        "is_deleted": False,
        "last_claimed_date": None
    }
    return Task(**task_data)


@pytest.fixture(scope="function")
def child_task(parent_task: Task, base_task_data: Dict[str, Any]) -> Task:
    """子任务对象"""
    task_data = {
        **base_task_data,
        "id": str(uuid4()),
        "user_id": parent_task.user_id,
        "title": "子任务",
        "parent_id": parent_task.id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completion_percentage": 0.0,
        "is_deleted": False,
        "last_claimed_date": None
    }
    return Task(**task_data)


# Task测试数据工厂
class TaskTestDataFactory:
    """Task域测试数据工厂"""

    @staticmethod
    def create_task(**overrides) -> Task:
        """创建任务数据"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "title": "测试任务",
            "description": "测试任务描述",
            "status": TaskStatusConst.PENDING,
            "priority": TaskPriorityConst.MEDIUM,
            "tags": ["测试"],
            "completion_percentage": 0.0,
            "is_deleted": False,
            "parent_id": None,
            "last_claimed_date": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        data.update(overrides)
        return Task(**data)

    @staticmethod
    def create_user_tasks(user_id: str, count: int = 5) -> List[Task]:
        """创建用户任务列表"""
        tasks = []
        for i in range(count):
            task = TaskTestDataFactory.create_task(
                title=f"任务{i+1}",
                user_id=user_id,
                status=TaskStatusConst.PENDING if i < count-1 else TaskStatusConst.COMPLETED
            )
            tasks.append(task)
        return tasks

    @staticmethod
    def create_task_hierarchy(user_id: str, levels: int = 3, children_per_level: int = 2) -> List[Task]:
        """创建任务层级结构"""
        tasks = []

        # 创建根任务
        root_task = TaskTestDataFactory.create_task(
            user_id=user_id,
            title="根任务",
            parent_id=None
        )
        tasks.append(root_task)

        # 创建子任务层级
        current_level_tasks = [root_task]
        for level in range(1, levels):
            next_level_tasks = []
            for parent in current_level_tasks:
                for i in range(children_per_level):
                    child_task = TaskTestDataFactory.create_task(
                        user_id=user_id,
                        title=f"任务L{level}C{i+1}",
                        parent_id=parent.id
                    )
                    tasks.append(child_task)
                    next_level_tasks.append(child_task)
            current_level_tasks = next_level_tasks

        return tasks

    @staticmethod
    def create_task_with_tags(user_id: str, tags: List[str]) -> Task:
        """创建带标签的任务"""
        return TaskTestDataFactory.create_task(
            user_id=user_id,
            title=f"带标签任务: {', '.join(tags)}",
            tags=tags
        )

    @staticmethod
    def create_due_task(user_id: str, days_until_due: int) -> Task:
        """创建带截止日期的任务"""
        due_date = datetime.now(timezone.utc).replace(hour=23, minute=59)
        if days_until_due >= 0:
            due_date = due_date.replace(day=due_date.day + days_until_due)

        return TaskTestDataFactory.create_task(
            user_id=user_id,
            title=f"截止任务: {days_until_due}天后",
            due_date=due_date
        )


@pytest.fixture(scope="function")
def task_test_data_factory() -> TaskTestDataFactory:
    """Task测试数据工厂实例"""
    return TaskTestDataFactory()


@pytest.fixture(scope="function")
def mock_session() -> Mock:
    """模拟数据库会话"""
    session = Mock()
    session.add = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.exec = Mock()
    session.query = Mock()
    session.refresh = Mock()
    session.delete = Mock()
    return session


# 时间相关Fixtures
@pytest.fixture(scope="function")
def current_datetime() -> datetime:
    """当前时间"""
    return datetime.now(timezone.utc)


@pytest.fixture(scope="function")
def current_date() -> date:
    """当前日期"""
    return date.today()


@pytest.fixture(scope="function")
def future_datetime(days: int = 7) -> datetime:
    """未来时间"""
    return datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day + days)


@pytest.fixture(scope="function")
def past_datetime(days: int = 1) -> datetime:
    """过去时间"""
    return datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - days)