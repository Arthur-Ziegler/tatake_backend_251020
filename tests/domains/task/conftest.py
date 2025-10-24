"""
Task领域测试配置

提供task领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.points.service import PointsService
from src.domains.task.repository import TaskRepository


@pytest.fixture(scope="function")
def task_service(task_db_session):
    """提供TaskService实例的fixture"""
    points_service = PointsService(task_db_session)
    task_service = TaskService(task_db_session, points_service)
    return task_service


@pytest.fixture(scope="function")
def task_repository(task_db_session):
    """提供TaskRepository实例的fixture"""
    return TaskRepository(task_db_session)


@pytest.fixture(scope="function")
async def sample_task(task_repository):
    """创建测试用的任务"""
    user_id = str(uuid4())
    return await task_repository.create_task(
        user_id=user_id,
        title="测试任务",
        description="这是一个测试任务",
        priority=TaskPriorityConst.MEDIUM
    )


@pytest.fixture(scope="function")
async def sample_task_list(task_repository):
    """创建多个测试用的任务"""
    user_id = str(uuid4())
    tasks = []

    # 创建不同状态的任务
    statuses = [
        TaskStatusConst.PENDING,
        TaskStatusConst.IN_PROGRESS,
        TaskStatusConst.COMPLETED
    ]

    priorities = [
        TaskPriorityConst.LOW,
        TaskPriorityConst.MEDIUM,
        TaskPriorityConst.HIGH
    ]

    for i, (status, priority) in enumerate(zip(statuses, priorities)):
        task = await task_repository.create_task(
            user_id=user_id,
            title=f"测试任务 {i+1}",
            description=f"这是第{i+1}个测试任务",
            status=status,
            priority=priority,
            completion_percentage=100.0 if status == TaskStatusConst.COMPLETED else 0.0
        )
        tasks.append(task)

    return tasks


@pytest.fixture(scope="function")
async def task_with_dependencies(task_repository):
    """创建有依赖关系的任务"""
    user_id = str(uuid4())

    # 创建父任务
    parent_task = await task_repository.create_task(
        user_id=user_id,
        title="父任务",
        description="这是一个父任务",
        priority=TaskPriorityConst.HIGH
    )

    # 创建子任务
    child_task = await task_repository.create_task(
        user_id=user_id,
        title="子任务",
        description="这是一个子任务",
        priority=TaskPriorityConst.MEDIUM,
        parent_id=parent_task.id
    )

    return parent_task, child_task


@pytest.fixture(scope="function")
def sample_task_data():
    """提供测试用的任务数据"""
    return {
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": TaskPriorityConst.MEDIUM,
        "status": TaskStatusConst.PENDING,
        "tags": ["测试", "开发"],
        "service_ids": ["service-001"]
    }