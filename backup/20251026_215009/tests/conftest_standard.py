"""
标准测试配置和Fixtures

提供统一的测试环境配置、数据库会话、测试数据工厂等。

作者：TaKeKe团队
版本：1.0.0 - 标准化测试基础设施
"""

import pytest
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Dict, Any, List, Generator, Optional
from unittest.mock import Mock, MagicMock

from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.pool import StaticPool

from src.database import get_db_engine
from src.domains.points.models import PointsTransaction
from src.domains.reward.models import Reward, RewardTransaction, RewardRecipe
from src.domains.task.models import Task, TaskStatus, TaskPriority
from src.domains.top3.models import Top3Entry
from src.domains.user.models import User, UserSettings, UserStats
from src.domains.points.service import PointsService
from src.domains.reward.service import RewardService
from src.domains.task.service import TaskService
from src.domains.top3.service import Top3Service
from src.domains.user.repository import UserRepository
from src.core.uuid_converter import UUIDConverter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def test_db_engine():
    """测试数据库引擎"""
    # 使用内存SQLite数据库进行测试
    engine = sa_create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        echo=False  # 设置为True可以看到SQL语句
    )
    return engine


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """测试数据库会话"""
    # 创建所有表
    SQLModel.metadata.create_all(test_db_engine)

    # 创建会话
    session = Session(test_db_engine)

    try:
        yield session
    finally:
        session.close()
        # 清理所有表
        SQLModel.metadata.drop_all(test_db_engine)


@pytest.fixture(scope="function")
def test_db_session_with_data(test_db_session) -> Generator[Session, None, None]:
    """带预置数据的测试数据库会话"""
    # 创建基础测试数据
    _create_test_data(test_db_session)

    yield test_db_session


def _create_test_data(session: Session) -> None:
    """创建基础测试数据"""
    # 创建基础奖品
    basic_reward = Reward(
        id=str(uuid4()),
        name="小金币",
        description="基础奖品，可通过完成任务获得",
        points_value=10,
        category="basic",
        cost_type="points",
        cost_value=10,
        stock_quantity=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(basic_reward)

    premium_reward = Reward(
        id=str(uuid4()),
        name="钻石",
        description="珍贵奖品，可通过小金币合成",
        points_value=100,
        category="premium",
        cost_type="points",
        cost_value=100,
        stock_quantity=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(premium_reward)

    # 创建欢迎礼包奖品
    bonus_card = Reward(
        id="points-bonus-card-001",
        name="积分加成卡",
        description="+50%积分加成，有效期1小时",
        points_value=0,
        category="道具",
        cost_type="points",
        cost_value=0,
        stock_quantity=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(bonus_card)

    focus_item = Reward(
        id="focus-item-001",
        name="专注道具",
        description="立即完成专注会话",
        points_value=0,
        category="道具",
        cost_type="points",
        cost_value=0,
        stock_quantity=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(focus_item)

    time_coupon = Reward(
        id="time-management-coupon-001",
        name="时间管理券",
        description="延长任务截止时间1天",
        points_value=0,
        category="道具",
        cost_type="points",
        cost_value=0,
        stock_quantity=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(time_coupon)

    # 提交基础数据
    session.commit()


# Domain Services Fixtures
@pytest.fixture(scope="function")
def points_service(test_db_session) -> PointsService:
    """积分服务实例"""
    return PointsService(test_db_session)


@pytest.fixture(scope="function")
def reward_service(test_db_session) -> RewardService:
    """奖励服务实例"""
    points_service = PointsService(test_db_session)
    return RewardService(test_db_session, points_service)


@pytest.fixture(scope="function")
def reward_service_with_points(test_db_session) -> RewardService:
    """带积分服务的奖励服务实例"""
    points_service = PointsService(test_db_session)
    return RewardService(test_db_session, points_service)


@pytest.fixture(scope="function")
def task_service(test_db_session) -> TaskService:
    """任务服务实例"""
    return TaskService(test_db_session)


@pytest.fixture(scope="function")
def top3_service(test_db_session) -> Top3Service:
    """Top3服务实例"""
    return Top3Service(test_db_session)


@pytest.fixture(scope="function")
def user_repository(test_db_session) -> UserRepository:
    """用户仓储实例"""
    return UserRepository(test_db_session)


# Test Data Fixtures
@pytest.fixture(scope="function")
def sample_user_id() -> str:
    """示例用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_user_uuid() -> UUID:
    """示例用户UUID"""
    return uuid4()


@pytest.fixture(scope="function")
def sample_reward() -> Dict[str, Any]:
    """示例奖品数据"""
    return {
        "id": str(uuid4()),
        "name": "测试奖品",
        "description": "这是一个测试奖品",
        "points_value": 50,
        "category": "test",
        "cost_type": "points",
        "cost_value": 50,
        "stock_quantity": 0,
        "is_active": True,
        "image_url": "https://example.com/reward.jpg",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture(scope="function")
def sample_task() -> Dict[str, Any]:
    """示例任务数据"""
    return {
        "id": str(uuid4()),
        "title": "测试任务",
        "description": "这是一个测试任务描述",
        "status": TaskStatus.ACTIVE,
        "priority": TaskPriority.MEDIUM,
        "parent_id": None,
        "user_id": str(uuid4()),
        "tags": ["测试", "示例"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture(scope="function")
def sample_points_transaction() -> Dict[str, Any]:
    """示例积分交易数据"""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "amount": 100,
        "source_type": "test_reward",
        "source_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc)
    }


@pytest.fixture(scope="function")
def multiple_rewards() -> List[Dict[str, Any]]:
    """多个示例奖品数据"""
    rewards = []
    categories = ["basic", "premium", "test"]

    for i, category in enumerate(categories):
        reward = {
            "id": str(uuid4()),
            "name": f"测试奖品{i+1}",
            "description": f"这是第{i+1}个测试奖品",
            "points_value": (i+1) * 50,
            "category": category,
            "cost_type": "points",
            "cost_value": (i+1) * 50,
            "stock_quantity": 0,
            "is_active": True,
            "image_url": f"https://example.com/reward{i+1}.jpg",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        rewards.append(reward)

    return rewards


@pytest.fixture(scope="function")
def sample_user_data() -> Dict[str, Any]:
    """示例用户数据"""
    return {
        "nickname": "测试用户",
        "avatar_url": "https://example.com/avatar.jpg",
        "bio": "这是测试用户的简介",
        "created_at": datetime.now(timezone.utc),
        "last_login_at": datetime.now(timezone.utc)
    }


# Mock Fixtures
@pytest.fixture(scope="function")
def mock_session() -> Mock:
    """模拟数据库会话"""
    return Mock(spec=Session)


@pytest.fixture(scope="function")
def mock_points_service() -> Mock:
    """模拟积分服务"""
    mock_service = Mock(spec=PointsService)
    mock_service.calculate_balance.return_value = 0
    mock_service.add_points.return_value = Mock(id=uuid4())
    mock_service.get_transactions.return_value = []
    return mock_service


@pytest.fixture(scope="function")
def mock_reward_service() -> Mock:
    """模拟奖励服务"""
    mock_service = Mock(spec=RewardService)
    mock_service.get_reward_catalog.return_value = {
        "rewards": [],
        "total_count": 0
    }
    mock_service.get_my_rewards.return_value = {
        "rewards": [],
        "total_types": 0
    }
    return mock_service


# Utility Functions
@pytest.fixture(scope="function")
def uuid_string_generator() -> Generator[str, None, None]:
    """UUID字符串生成器"""
    def _generate_uuid() -> str:
        return str(uuid4())
    yield _generate_uuid


@pytest.fixture(scope="function")
def uuid_object_generator() -> Generator[UUID, None, None]:
    """UUID对象生成器"""
    def _generate_uuid() -> UUID:
        return uuid4()
    yield _generate_uuid


@pytest.fixture(scope="function")
def timestamp_generator() -> Generator[datetime, None, None]:
    """时间戳生成器"""
    def _generate_timestamp() -> datetime:
        return datetime.now(timezone.utc)
    yield _generate_timestamp


# Markers
def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )


# Test Data Factory
class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_reward(**overrides) -> Dict[str, Any]:
        """创建奖品数据"""
        data = {
            "id": str(uuid4()),
            "name": "工厂创建的奖品",
            "description": "通过测试数据工厂创建",
            "points_value": 100,
            "category": "factory",
            "cost_type": "points",
            "cost_value": 100,
            "stock_quantity": 0,
            "is_active": True,
            "image_url": "https://example.com/factory-reward.jpg",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_task(**overrides) -> Dict[str, Any]:
        """创建任务数据"""
        data = {
            "id": str(uuid4()),
            "title": "工厂创建的任务",
            "description": "通过测试数据工厂创建",
            "status": TaskStatus.ACTIVE,
            "priority": TaskPriority.MEDIUM,
            "parent_id": None,
            "user_id": str(uuid4()),
            "tags": ["factory", "test"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_user(**overrides) -> Dict[str, Any]:
        """创建用户数据"""
        data = {
            "nickname": "工厂用户",
            "avatar_url": "https://example.com/factory-avatar.jpg",
            "bio": "通过测试数据工厂创建的用户",
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc)
        }
        data.update(overrides)
        return data


@pytest.fixture(scope="function")
def test_data_factory() -> TestDataFactory:
    """测试数据工厂实例"""
    return TestDataFactory()


# Coverage configuration
def pytest_collection_modifyitems(config, items):
    """配置测试收集"""
    # 跳过慢速测试，除非明确指定
    if not config.getoption("-m") or "slow" not in config.getoption("-m"):
        skip_slow = pytest.mark.skip(reason="使用 -m slow 运行慢速测试")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# Cleanup helpers
@pytest.fixture(autouse=True)
def cleanup_test_data(test_db_session):
    """自动清理测试数据"""
    yield
    # 测试后清理
    test_db_session.execute(
        text("DELETE FROM points_transactions")
    )
    test_db_session.execute(
        text("DELETE FROM reward_transactions")
    )
    test_db_session.execute(
        text("DELETE FROM top3_entries")
    )
    test_db_session.commit()