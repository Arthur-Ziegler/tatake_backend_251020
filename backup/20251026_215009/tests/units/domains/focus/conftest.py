"""
Focus领域测试配置

提供focus领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from uuid import uuid4

from src.domains.focus.models import FocusSession
from src.domains.focus.service import FocusService


@pytest.fixture(scope="function")
async def focus_service(focus_db_session):
    """提供FocusService实例的fixture"""
    return FocusService(focus_db_session)


@pytest.fixture(scope="function")
async def sample_focus_session(focus_service):
    """创建测试用的专注会话"""
    user_id = str(uuid4())
    task_id = str(uuid4())

    return await focus_service.create_focus_session(
        user_id=user_id,
        task_id=task_id,
        duration_minutes=25
    )


@pytest.fixture(scope="function")
async def active_focus_session(focus_service):
    """创建已开始的专注会话"""
    user_id = str(uuid4())
    task_id = str(uuid4())

    session = await focus_service.create_focus_session(
        user_id=user_id,
        task_id=task_id,
        duration_minutes=25
    )

    return await focus_service.start_focus_session(session.id)


@pytest.fixture(scope="function")
async def completed_focus_session(focus_service):
    """创建已完成的专注会话"""
    user_id = str(uuid4())
    task_id = str(uuid4())

    session = await focus_service.create_focus_session(
        user_id=user_id,
        task_id=task_id,
        duration_minutes=25
    )

    await focus_service.start_focus_session(session.id)
    return await focus_service.complete_focus_session(
        session.id,
        notes="测试完成的专注会话"
    )