"""
集成测试配置和Fixtures

提供真实的数据库环境和多个服务组件的集成测试。

作者：TaKeKe团队
版本：1.0.0 - 集成测试专用配置
"""

import pytest
import logging
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch

from sqlmodel import Session, create_engine, SQLModel, select
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
from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.task.service import TaskService
from src.domains.top3.service import Top3Service
from src.domains.user.repository import UserRepository
from src.core.uuid_converter import UUIDConverter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def integration_test_db_engine():
    """集成测试数据库引擎"""
    # 使用内存SQLite数据库进行集成测试
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
def integration_test_db_session(integration_test_db_engine) -> Generator[Session, None, None]:
    """集成测试数据库会话"""
    # 创建所有表
    SQLModel.metadata.create_all(integration_test_db_engine)

    # 创建会话
    session = Session(integration_test_db_engine)

    try:
        yield session
    finally:
        session.close()
        # 清理所有表
        SQLModel.metadata.drop_all(integration_test_db_engine)


@pytest.fixture(scope="function")
def integration_test_db_session_with_data(integration_test_db_session) -> Generator[Session, None, None]:
    """带预置数据的集成测试数据库会话"""
    # 创建完整的测试数据
    _create_integration_test_data(integration_test_db_session)

    yield integration_test_db_session


def _create_integration_test_data(session: Session) -> None:
    """创建集成测试数据"""
    # 创建基础奖品
    basic_reward = Reward(
        id=str(uuid4()),
        name="小金币",
        description="基础奖品，可通过完成任务获得",
        points_value=10,
        category="basic",
        cost_type="points",
        cost_value=10,
        stock_quantity=1000,
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
        stock_quantity=100,
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

    # 创建奖励配方
    recipe = RewardRecipe(
        id=str(uuid4()),
        name="小金币合成钻石",
        description="10个小金币合成1个钻石",
        result_reward_id=premium_reward.id,
        result_quantity=1,
        cost_type="rewards",
        cost_value='{"小金币": 10}',
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(recipe)

    # 提交基础数据
    session.commit()


# 服务实例Fixtures
@pytest.fixture(scope="function")
def integration_points_service(integration_test_db_session) -> PointsService:
    """集成测试积分服务实例"""
    return PointsService(integration_test_db_session)


@pytest.fixture(scope="function")
def integration_reward_service(integration_test_db_session) -> RewardService:
    """集成测试奖励服务实例"""
    points_service = PointsService(integration_test_db_session)
    return RewardService(integration_test_db_session, points_service)


@pytest.fixture(scope="function")
def integration_welcome_gift_service(integration_test_db_session) -> WelcomeGiftService:
    """集成测试欢迎礼包服务实例"""
    points_service = PointsService(integration_test_db_session)
    return WelcomeGiftService(integration_test_db_session, points_service)


@pytest.fixture(scope="function")
def integration_task_service(integration_test_db_session) -> TaskService:
    """集成测试任务服务实例"""
    return TaskService(integration_test_db_session)


@pytest.fixture(scope="function")
def integration_top3_service(integration_test_db_session) -> Top3Service:
    """集成测试Top3服务实例"""
    return Top3Service(integration_test_db_session)


@pytest.fixture(scope="function")
def integration_user_repository(integration_test_db_session) -> UserRepository:
    """集成测试用户仓储实例"""
    return UserRepository(integration_test_db_session)


# 集成测试数据工厂
class IntegrationTestDataFactory:
    """集成测试数据工厂"""

    @staticmethod
    def create_user(session: Session, **overrides) -> User:
        """创建用户数据并保存到数据库"""
        data = {
            "id": str(uuid4()),
            "nickname": "集成测试用户",
            "avatar_url": "https://example.com/integration-avatar.jpg",
            "bio": "集成测试用户",
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc)
        }
        data.update(overrides)

        user = User(**data)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def create_points_transaction(session: Session, user_id: str, **overrides) -> PointsTransaction:
        """创建积分交易数据并保存到数据库"""
        data = {
            "user_id": user_id,
            "amount": 100,
            "source_type": "integration_test",
            "source_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc)
        }
        data.update(overrides)

        transaction = PointsTransaction(**data)
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    @staticmethod
    def create_task(session: Session, user_id: str, **overrides) -> Task:
        """创建任务数据并保存到数据库"""
        data = {
            "title": "集成测试任务",
            "description": "这是一个集成测试任务",
            "status": TaskStatus.ACTIVE,
            "priority": TaskPriority.MEDIUM,
            "user_id": user_id,
            "parent_id": None,
            "tags": ["集成测试"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        data.update(overrides)

        task = Task(**data)
        session.add(task)
        session.commit()
        session.refresh(task)
        return task

    @staticmethod
    def create_reward_transaction(session: Session, user_id: str, reward_id: str, **overrides) -> RewardTransaction:
        """创建奖励交易数据并保存到数据库"""
        data = {
            "user_id": user_id,
            "reward_id": reward_id,
            "quantity": 1,
            "source_type": "integration_test",
            "source_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc)
        }
        data.update(overrides)

        transaction = RewardTransaction(**data)
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction


@pytest.fixture(scope="function")
def integration_test_data_factory() -> IntegrationTestDataFactory:
    """集成测试数据工厂实例"""
    return IntegrationTestDataFactory()


# 复杂场景数据生成
@pytest.fixture(scope="function")
def user_with_complete_data(integration_test_db_session, integration_test_data_factory) -> Dict[str, Any]:
    """创建具有完整数据的用户"""
    # 创建用户
    user = integration_test_data_factory.create_user(integration_test_db_session)

    # 创建积分交易
    for i in range(5):
        integration_test_data_factory.create_points_transaction(
            integration_test_db_session,
            user.id,
            amount=100 * (i + 1),
            source_type=f"test_source_{i}"
        )

    # 创建任务
    for i in range(3):
        integration_test_data_factory.create_task(
            integration_test_db_session,
            user.id,
            title=f"测试任务_{i + 1}",
            priority=list(TaskPriority)[i % len(TaskPriority)]
        )

    return {
        "user": user,
        "user_id": user.id,
        "points_balance": 1500,  # 100+200+300+400+500
        "task_count": 3,
        "transaction_count": 5
    }


@pytest.fixture(scope="function")
def users_with_rewards_flow(integration_test_db_session, integration_test_data_factory, integration_points_service, integration_reward_service) -> List[Dict[str, Any]]:
    """创建包含奖励流转数据的多个用户"""
    users_data = []

    for i in range(3):
        # 创建用户
        user = integration_test_data_factory.create_user(
            integration_test_db_session,
            nickname=f"奖励测试用户_{i + 1}"
        )

        # 发放积分
        integration_points_service.add_points(
            user.id,
            500,
            source_type="initial_gift"
        )

        # 创建奖励交易
        rewards = integration_test_db_session.exec(select(Reward)).all()
        for reward in rewards[:2]:  # 每个用户获得前两种奖励
            integration_test_data_factory.create_reward_transaction(
                integration_test_db_session,
                user.id,
                reward.id,
                quantity=2,
                source_type="gift"
            )

        users_data.append({
            "user": user,
            "user_id": user.id,
            "points_balance": 500,
            "rewards_count": 2
        })

    return users_data


# 数据验证辅助函数
@pytest.fixture(scope="function")
def data_validator():
    """数据验证辅助工具"""
    class DataValidator:
        @staticmethod
        def validate_user_data(session: Session, user_id: str, expected_data: Dict[str, Any]) -> bool:
            """验证用户数据"""
            user = session.get(User, user_id)
            if not user:
                return False

            for key, expected_value in expected_data.items():
                if getattr(user, key) != expected_value:
                    return False
            return True

        @staticmethod
        def validate_points_balance(session: Session, user_id: str, expected_balance: int) -> bool:
            """验证积分余额"""
            points_service = PointsService(session)
            actual_balance = points_service.calculate_balance(user_id)
            return actual_balance == expected_balance

        @staticmethod
        def validate_transaction_count(session: Session, user_id: str, expected_count: int, source_type: str = None) -> bool:
            """验证交易数量"""
            query = select(PointsTransaction).where(PointsTransaction.user_id == user_id)
            if source_type:
                query = query.where(PointsTransaction.source_type == source_type)

            transactions = session.exec(query).all()
            return len(transactions) == expected_count

    return DataValidator()


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速集成测试")
    config.addinivalue_line("markers", "database: 数据库集成测试")


# 清理辅助
@pytest.fixture(autouse=True)
def integration_test_cleanup(integration_test_db_session):
    """集成测试自动清理"""
    yield
    # 测试后清理数据库
    try:
        integration_test_db_session.execute(
            text("DELETE FROM points_transactions")
        )
        integration_test_db_session.execute(
            text("DELETE FROM reward_transactions")
        )
        integration_test_db_session.execute(
            text("DELETE FROM top3_entries")
        )
        integration_test_db_session.execute(
            text("DELETE FROM tasks")
        )
        integration_test_db_session.commit()
    except Exception as e:
        logger.error(f"集成测试清理失败: {e}")
        integration_test_db_session.rollback()