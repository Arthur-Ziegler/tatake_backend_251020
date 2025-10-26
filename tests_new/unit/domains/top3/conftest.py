"""
Top3域测试配置和Fixtures

提供top3域专用的测试环境配置。

作者：TaKeKe团队
版本：2.0.0
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timezone, date
from typing import Dict, Any, List

from src.domains.top3.models import TaskTop3
from src.domains.task.models import Task, TaskStatusConst


@pytest.fixture(scope="function")
def sample_user_id() -> str:
    """示例用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_top3_id() -> str:
    """示例Top3 ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_task_ids() -> List[str]:
    """示例任务ID列表"""
    return [str(uuid4()) for _ in range(3)]


@pytest.fixture(scope="function")
def base_top3_data() -> Dict[str, Any]:
    """基础Top3数据"""
    return {
        "user_id": str(uuid4()),
        "top_date": date.today().isoformat(),
        "task_ids": [
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()},
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()},
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
        ],
        "points_consumed": 5,
        "remaining_balance": 100
    }


@pytest.fixture(scope="function")
def sample_top3(base_top3_data: Dict[str, Any]) -> TaskTop3:
    """示例Top3对象"""
    top3_data = {
        **base_top3_data,
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    return TaskTop3(**top3_data)


@pytest.fixture(scope="function")
def today_top3(sample_user_id: str, sample_task_ids: List[str]) -> TaskTop3:
    """今日Top3对象"""
    task_id_objects = [
        {"task_id": task_id, "added_at": datetime.now(timezone.utc).isoformat()}
        for task_id in sample_task_ids[:3]
    ]

    return TaskTop3(
        id=str(uuid4()),
        user_id=sample_user_id,
        top_date=date.today(),
        task_ids=task_id_objects,
        points_consumed=5,
        remaining_balance=95,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


# Top3测试数据工厂
class Top3TestDataFactory:
    """Top3域测试数据工厂"""

    @staticmethod
    def create_top3(**overrides) -> TaskTop3:
        """创建Top3数据"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "top_date": date.today(),
            "task_ids": [
                {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
            ],
            "points_consumed": 5,
            "remaining_balance": 95,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        data.update(overrides)
        return TaskTop3(**data)

    @staticmethod
    def create_user_top3_history(user_id: str, days: int = 30) -> List[TaskTop3]:
        """创建用户Top3历史记录"""
        top3_list = []
        for i in range(days):
            top_date = date.today().replace(day=date.today().day - i)
            task_ids = [
                {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
                for _ in range(3)
            ]

            top3 = Top3TestDataFactory.create_top3(
                user_id=user_id,
                top_date=top_date,
                task_ids=task_ids,
                points_consumed=5,
                remaining_balance=100 - (i * 5)
            )
            top3_list.append(top3)
        return top3_list


@pytest.fixture(scope="function")
def top3_test_data_factory() -> Top3TestDataFactory:
    """Top3测试数据工厂实例"""
    return Top3TestDataFactory()


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
def past_date(days: int = 1) -> date:
    """过去的日期"""
    return date.today().replace(day=date.today().day - days)


@pytest.fixture(scope="function")
def future_date(days: int = 1) -> date:
    """未来的日期"""
    return date.today().replace(day=date.today().day + days)