"""
Task域单元测试配置和Fixtures

提供全面的task域测试环境配置，包含数据工厂和模拟对象。

作者：TaKeKe团队
版本：2.0.0 - 严格单元测试专用配置
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from uuid import uuid4
from typing import Generator, Dict, Any, List
from datetime import datetime, timezone, date
from sqlmodel import Session

from src.domains.task.models import Task, TaskStatusConst, TaskPriorityConst
from src.domains.task.service import TaskService
from src.domains.task.repository import TaskRepository
from src.domains.task.completion_service import TaskCompletionService
from src.utils.enum_helpers import ensure_enum_value


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
def mock_task_repository() -> Mock:
    """模拟任务仓储"""
    repo = Mock(spec=TaskRepository)

    # 配置基础方法
    repo.create = Mock(return_value=Mock(spec=Task))
    repo.get_by_id = Mock(return_value=None)
    repo.get_user_tasks = Mock(return_value=[])
    repo.get_user_active_tasks = Mock(return_value=[])
    repo.update = Mock(return_value=Mock(spec=Task))
    repo.delete = Mock(return_value=True)
    repo.count_user_tasks = Mock(return_value=0)
    repo.get_parent_tasks = Mock(return_value=[])
    repo.get_child_tasks = Mock(return_value=[])

    # 配置Mock以允许动态属性设置
    repo.configure_mock(**{
        'get_tasks_by_status.return_value': [],
        'get_tasks_by_priority.return_value': [],
        'search_tasks_by_title.return_value': [],
        'get_tasks_due_soon.return_value': [],
        'get_tasks_by_date_range.return_value': [],
        'get_task_statistics.return_value': {
            'total': 0,
            'completed': 0,
            'pending': 0,
            'in_progress': 0
        }
    })
    return repo


@pytest.fixture(scope="function")
def mock_task_service() -> Mock:
    """模拟任务服务"""
    service = Mock(spec=TaskService)
    service.create_task = Mock(return_value=Mock(spec=Task))
    service.get_task = Mock(return_value=None)
    service.list_tasks = Mock(return_value=[])
    service.update_task = Mock(return_value=Mock(spec=Task))
    service.delete_task = Mock(return_value=True)
    service.complete_task = Mock(return_value={'success': True})
    service.get_task_statistics = Mock(return_value={
        'total': 0,
        'completed': 0,
        'pending': 0,
        'in_progress': 0
    })
    return service


@pytest.fixture(scope="function")
def task_service(mock_session: Mock) -> TaskService:
    """任务服务实例（使用真实Session Mock）"""
    return TaskService(mock_session)


@pytest.fixture(scope="function")
def completion_service(mock_session: Mock) -> TaskCompletionService:
    """任务完成服务实例"""
    return TaskCompletionService(mock_session)


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


# 测试数据工厂
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


# 枚举测试数据
@pytest.fixture(scope="function", params=[
    TaskStatusConst.PENDING,
    TaskStatusConst.IN_PROGRESS,
    TaskStatusConst.COMPLETED
])
def task_status_param(request) -> str:
    """任务状态参数化"""
    return request.param


@pytest.fixture(scope="function", params=[
    TaskPriorityConst.LOW,
    TaskPriorityConst.MEDIUM,
    TaskPriorityConst.HIGH
])
def task_priority_param(request) -> str:
    """任务优先级参数化"""
    return request.param


# 错误模拟
@pytest.fixture(scope="function")
def mock_database_error() -> Exception:
    """数据库错误模拟"""
    return Exception("数据库连接失败")


@pytest.fixture(scope="function")
def mock_validation_error() -> Exception:
    """验证错误模拟"""
    return ValueError("任务数据验证失败")


@pytest.fixture(scope="function")
def mock_permission_error() -> Exception:
    """权限错误模拟"""
    return PermissionError("无权限访问此任务")


# Mock工具函数
@pytest.fixture(scope="function")
def mock_uuid_generator() -> Generator[str, None, None]:
    """UUID生成器模拟"""
    generated_uuids = []

    def _generate_uuid() -> str:
        uuid_str = str(uuid4())
        generated_uuids.append(uuid_str)
        return uuid_str

    yield _generate_uuid


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


# 枚举验证工具
@pytest.fixture(scope="function")
def enum_validator():
    """枚举验证工具"""
    def _validate_enum(value: str, enum_class: type) -> bool:
        try:
            ensure_enum_value(value, enum_class)
            return True
        except ValueError:
            return False
    return _validate_enum


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "task: Task域测试")
    config.addinivalue_line("markers", "model: 模型测试")
    config.addinivalue_line("markers", "service: 服务测试")
    config.addinivalue_line("markers", "repository: 仓储测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "integration: 集成测试")


# 清理辅助
@pytest.fixture(autouse=True)
def task_test_cleanup():
    """Task域测试自动清理"""
    yield
    # 测试后清理工作
    pass


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


# 数据库查询Mock辅助
@pytest.fixture(scope="function")
def mock_query_builder():
    """查询构建器模拟"""
    query = Mock()
    query.where = Mock(return_value=query)
    query.filter = Mock(return_value=query)
    query.order_by = Mock(return_value=query)
    query.limit = Mock(return_value=query)
    query.offset = Mock(return_value=query)
    query.all = Mock(return_value=[])
    query.first = Mock(return_value=None)
    query.count = Mock(return_value=0)
    query.exists = Mock(return_value=False)
    return query