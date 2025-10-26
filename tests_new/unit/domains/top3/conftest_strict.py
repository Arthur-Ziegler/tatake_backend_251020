"""
Top3域单元测试配置和Fixtures

提供全面的top3域测试环境配置，包含数据工厂和模拟对象。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试专用配置
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4
from typing import Generator, Dict, Any, List
from datetime import datetime, timezone, date
from sqlmodel import Session

from src.domains.top3.models import TaskTop3
from src.domains.top3.service import Top3Service
from src.domains.top3.repository import Top3Repository
from src.domains.task.models import Task, TaskStatusConst


@pytest.fixture(scope="function")
def mock_session() -> Mock:
    """模拟数据库会话"""
    session = Mock(spec=Session)
    session.add = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.exec = Mock()
    session.query = Mock()
    session.refresh = Mock()
    session.delete = Mock()
    return session


@pytest.fixture(scope="function")
def mock_top3_repository() -> Mock:
    """模拟Top3仓储"""
    repo = Mock(spec=Top3Repository)

    # 配置基础方法
    repo.create = Mock(return_value=Mock(spec=TaskTop3))
    repo.get_by_id = Mock(return_value=None)
    repo.get_user_top3 = Mock(return_value=None)
    repo.get_user_top3_by_date = Mock(return_value=None)
    repo.update = Mock(return_value=Mock(spec=TaskTop3))
    repo.delete = Mock(return_value=True)
    repo.get_user_top3_history = Mock(return_value=[])

    # 配置Mock以允许动态属性设置
    repo.configure_mock(**{
        'exists_user_top3_today.return_value': False,
        'count_user_top3_today.return_value': 0,
        'get_recent_top3_records.return_value': [],
        'get_top3_statistics.return_value': {
            'total_top3': 0,
            'this_month': 0,
            'success_rate': 0.0
        }
    })
    return repo


@pytest.fixture(scope="function")
def mock_top3_service() -> Mock:
    """模拟Top3服务"""
    service = Mock(spec=Top3Service)
    service.create_top3 = Mock(return_value=Mock(spec=TaskTop3))
    service.get_top3 = Mock(return_value=None)
    service.get_user_top3_today = Mock(return_value=None)
    service.update_top3 = Mock(return_value=Mock(spec=TaskTop3))
    service.delete_top3 = Mock(return_value=True)
    service.add_task_to_top3 = Mock(return_value=True)
    service.remove_task_from_top3 = Mock(return_value=True)
    service.get_top3_statistics = Mock(return_value={
        'total_top3': 0,
        'this_month': 0,
        'success_rate': 0.0
    })
    return service


@pytest.fixture(scope="function")
def top3_service(mock_session: Mock) -> Top3Service:
    """Top3服务实例（使用真实Session Mock）"""
    return Top3Service(mock_session)


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


@pytest.fixture(scope="function")
def sample_tasks_for_top3(sample_user_id: str, sample_task_ids: List[str]) -> List[Task]:
    """用于Top3的示例任务列表"""
    tasks = []
    for i, task_id in enumerate(sample_task_ids):
        task = Task(
            id=task_id,
            user_id=sample_user_id,
            title=f"Top3任务{i+1}",
            description=f"这是第{i+1}个重要的任务",
            status=TaskStatusConst.PENDING,
            priority="high" if i < 2 else "medium",
            tags=["重要", f"任务{i+1}"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completion_percentage=0.0,
            is_deleted=False
        )
        tasks.append(task)
    return tasks


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

    @staticmethod
    def create_top3_with_tasks(user_id: str, task_count: int = 3) -> TaskTop3:
        """创建带任务的Top3"""
        task_ids = [
            {"task_id": str(uuid4()), "added_at": datetime.now(timezone.utc).isoformat()}
            for _ in range(task_count)
        ]

        return Top3TestDataFactory.create_top3(
            user_id=user_id,
            task_ids=task_ids,
            points_consumed=task_count * 2,
            remaining_balance=100 - (task_count * 2)
        )

    @staticmethod
    def create_multiple_user_top3(user_id: str, count: int = 5) -> List[TaskTop3]:
        """创建用户的多个Top3记录"""
        top3_list = []
        for i in range(count):
            top_date = date.today().replace(day=date.today().day - i)
            top3 = Top3TestDataFactory.create_top3(
                user_id=user_id,
                top_date=top_date
            )
            top3_list.append(top3)
        return top3_list

    @staticmethod
    def create_top3_with_balance(user_id: str, balance: int) -> TaskTop3:
        """创建指定余额的Top3"""
        return Top3TestDataFactory.create_top3(
            user_id=user_id,
            points_consumed=max(0, 100 - balance),
            remaining_balance=balance
        )


@pytest.fixture(scope="function")
def top3_test_data_factory() -> Top3TestDataFactory:
    """Top3测试数据工厂实例"""
    return Top3TestDataFactory()


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


# 错误模拟
@pytest.fixture(scope="function")
def mock_insufficient_balance_error() -> Exception:
    """余额不足错误模拟"""
    return Exception("积分余额不足，无法设置Top3")


@pytest.fixture(scope="function")
def mock_top3_already_exists_error() -> Exception:
    """Top3已存在错误模拟"""
    return Exception("今日Top3已存在，无法重复创建")


@pytest.fixture(scope="function")
def mock_task_not_found_error() -> Exception:
    """任务不存在错误模拟"""
    return Exception("指定的任务不存在")


@pytest.fixture(scope="function")
def mock_invalid_task_count_error() -> Exception:
    """无效任务数量错误模拟"""
    return Exception("Top3任务数量必须在1-3个之间")


# Mock工具函数
@pytest.fixture(scope="function")
def mock_points_service() -> Mock:
    """模拟积分服务"""
    service = Mock()
    service.get_balance.return_value = 100
    service.consume_points.return_value = True
    service.add_points.return_value = Mock(id=str(uuid4()))
    return service


@pytest.fixture(scope="function")
def mock_task_service() -> Mock:
    """模拟任务服务"""
    service = Mock()
    service.get_task.return_value = Mock(spec=Task)
    service.get_tasks.return_value = []
    service.list_tasks.return_value = []
    return service


# 枚举参数化
@pytest.fixture(scope="function", params=[
    1, 2, 3
])
def valid_task_count_param(request) -> int:
    """有效任务数量参数化"""
    return request.param


@pytest.fixture(scope="function", params=[
    0, 4, 5
])
def invalid_task_count_param(request) -> int:
    """无效任务数量参数化"""
    return request.param


# 性能测试辅助
@pytest.fixture(scope="function")
def performance_tracker():
    """性能跟踪器"""
    import time

    class Tracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time

        def get_duration(self) -> float:
            return self.duration or 0

    tracker = Tracker()
    yield tracker
    # 性能结果可以在测试中访问tracker.get_duration()


# 验证工具
@pytest.fixture(scope="function")
def top3_validator():
    """Top3验证工具"""
    def _validate_task_count(count: int) -> bool:
        return 1 <= count <= 3

    def _validate_task_ids(task_ids: List[dict]) -> bool:
        return all(isinstance(item, dict) and "task_id" in item for item in task_ids)

    def _validate_points_consumed(points: int, balance: int) -> bool:
        return points <= balance

    return {
        'validate_task_count': _validate_task_count,
        'validate_task_ids': _validate_task_ids,
        'validate_points_consumed': _validate_points_consumed
    }


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "top3: Top3域测试")
    config.addinivalue_line("markers", "model: 模型测试")
    config.addinivalue_line("markers", "service: 服务测试")
    config.addinivalue_line("markers", "repository: 仓储测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "integration: 集成测试")


# 清理辅助
@pytest.fixture(autouse=True)
def top3_test_cleanup():
    """Top3域测试自动清理"""
    yield
    # 测试后清理工作
    pass


# 数据库查询Mock辅助
@pytest.fixture(scope="function")
def mock_query_builder():
    """查询构建器模拟"""
    query = Mock()
    query.where.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.offset.return_value = query
    query.all.return_value = []
    query.first.return_value = None
    query.count.return_value = 0
    query.exists.return_value = False
    return query