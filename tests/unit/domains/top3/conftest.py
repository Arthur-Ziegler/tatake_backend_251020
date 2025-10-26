"""
Top3领域测试配置

提供top3领域测试所需的特定fixtures和工具函数。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from sqlmodel import Session

from src.domains.top3.models import TaskTop3
from src.domains.top3.service import Top3Service
from src.domains.top3.repository import Top3Repository
from src.domains.points.service import PointsService
from src.domains.task.service import TaskService
from src.domains.reward.service import RewardService


@pytest.fixture(scope="function")
def top3_service(test_db_session: Session):
    """提供Top3Service实例的fixture"""
    # 创建依赖的服务实例
    points_service = PointsService(test_db_session)
    reward_service = RewardService(test_db_session, points_service)

    # 注意：Top3Service的构造函数需要根据实际情况调整
    # 这里暂时按照原始代码创建，如果出错再调整
    try:
        return Top3Service(test_db_session)
    except TypeError:
        # 如果Top3Service也需要依赖注入，则需要手动创建
        from src.domains.top3.repository import Top3Repository
        from src.domains.task.repository import TaskRepository

        top3_repo = Top3Repository(test_db_session)
        task_repo = TaskRepository(test_db_session)

        # 手动创建Top3Service实例
        service = Top3Service.__new__(Top3Service)
        service.session = test_db_session
        service.top3_repo = top3_repo
        service.reward_service = reward_service
        service.points_service = points_service
        service.task_repo = task_repo

        return service


@pytest.fixture(scope="function")
def sample_user_with_points(top3_service: Top3Service):
    """创建有足够积分的测试用户"""
    user_id = uuid4()

    # 通过PointsService给用户添加积分
    top3_service.points_service.add_points(
        user_id=user_id,
        amount=1000,  # 给用户1000积分
        source_type="test_initial"
    )

    return user_id


@pytest.fixture(scope="function")
def sample_tasks_for_top3(top3_service: Top3Service, sample_user_with_points):
    """创建用于Top3测试的示例任务"""
    user_id = sample_user_with_points
    task_ids = []

    # 创建3个测试任务
    task_titles = ["重要任务1", "重要任务2", "重要任务3"]
    for title in task_titles:
        task_data = {
                "user_id": str(user_id),
                "title": title,
                "description": "用于Top3测试的任务",
                "status": "pending",
                "priority": "medium"
            }
        task = top3_service.task_repo.create(task_data)
        task_ids.append(str(task.id))

    return user_id, task_ids


@pytest.fixture(scope="function")
def created_top3_entry(top3_service: Top3Service, sample_tasks_for_top3):
    """创建已设置的Top3条目"""
    user_id, task_ids = sample_tasks_for_top3
    today = date.today()

    from src.domains.top3.schemas import SetTop3Request

    request = SetTop3Request(
        date=today.isoformat(),
        task_ids=task_ids
    )

    top3_response = top3_service.set_top3(user_id, request)
    return user_id, top3_response, today


@pytest.fixture(scope="function")
def multiple_top3_entries(top3_service: Top3Service, sample_user_with_points):
    """创建多个Top3条目用于测试"""
    user_id = sample_user_with_points
    today = date.today()
    entries = []

    # 首先给用户充足的积分
    top3_service.points_service.add_points(
        user_id=user_id,
        amount=2000,  # 额外积分用于多个Top3
        source_type="test_multiple"
    )

    # 为不同日期创建任务和Top3
    for i in range(3):
        entry_date = today - timedelta(days=i)

        # 为每天创建3个任务
        daily_task_ids = []
        for j in range(3):
            task_data = {
                "user_id": str(user_id),
                "title": f"第{i+1}天任务{j+1}",
                "description": f"第{i+1}天的第{j+1}个任务",
                "status": "pending",
                "priority": "medium"
            }
            task = top3_service.task_repo.create(task_data)
            daily_task_ids.append(str(task.id))

        # 创建Top3
        from src.domains.top3.schemas import SetTop3Request
        request = SetTop3Request(
            date=entry_date.isoformat(),
            task_ids=daily_task_ids
        )

        try:
            top3_response = top3_service.set_top3(user_id, request)
            entries.append((user_id, top3_response, entry_date))
        except Exception as e:
            # 如果创建失败，记录错误但继续
            print(f"创建第{i+1}天Top3失败: {e}")

    return entries