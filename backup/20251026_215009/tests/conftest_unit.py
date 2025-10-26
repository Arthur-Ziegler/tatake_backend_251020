"""
单元测试配置和Fixtures

提供轻量级的测试环境配置，专注于单一组件的测试。

作者：TaKeKe团队
版本：1.0.0 - 单元测试专用配置
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from typing import Generator, Dict, Any
from sqlmodel import Session

from src.domains.points.service import PointsService
from src.domains.reward.service import RewardService
from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.domains.task.service import TaskService
from src.domains.top3.service import Top3Service


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
    return session


@pytest.fixture(scope="function")
def mock_points_service() -> Mock:
    """模拟积分服务"""
    service = Mock(spec=PointsService)
    service.calculate_balance.return_value = 0
    service.add_points.return_value = Mock(id=str(uuid4()))
    service.get_transactions.return_value = []
    # 配置Mock以允许动态属性设置
    service.configure_mock(**{
        'get_user_points_summary.return_value': {
            "balance": 0,
            "total_earned": 0,
            "total_spent": 0,
            "transaction_count": 0
        }
    })
    return service


@pytest.fixture(scope="function")
def mock_reward_service() -> Mock:
    """模拟奖励服务"""
    service = Mock(spec=RewardService)
    service.get_reward_catalog.return_value = {
        "rewards": [],
        "total_count": 0
    }
    service.get_my_rewards.return_value = {
        "rewards": [],
        "total_types": 0
    }
    service.redeem_reward.return_value = Mock(success=True)
    return service


@pytest.fixture(scope="function")
def mock_task_service() -> Mock:
    """模拟任务服务"""
    service = Mock(spec=TaskService)
    service.create_task.return_value = Mock(id=str(uuid4()))
    service.get_task.return_value = Mock()
    service.list_tasks.return_value = []
    service.update_task.return_value = Mock()
    service.delete_task.return_value = Mock(success=True)
    return service


@pytest.fixture(scope="function")
def mock_top3_service() -> Mock:
    """模拟Top3服务"""
    service = Mock(spec=Top3Service)
    service.get_top3.return_value = []
    service.add_to_top3.return_value = Mock(id=str(uuid4()))
    service.remove_from_top3.return_value = Mock(success=True)
    return service


@pytest.fixture(scope="function")
def welcome_gift_service(mock_session: Mock, mock_points_service: Mock) -> WelcomeGiftService:
    """欢迎礼包服务实例（使用模拟依赖）"""
    return WelcomeGiftService(mock_session, mock_points_service)


@pytest.fixture(scope="function")
def sample_user_id() -> str:
    """示例用户ID"""
    return str(uuid4())


@pytest.fixture(scope="function")
def sample_reward_data() -> Dict[str, Any]:
    """示例奖品数据"""
    return {
        "id": str(uuid4()),
        "name": "测试奖品",
        "description": "这是一个测试奖品",
        "points_value": 100,
        "category": "test",
        "cost_type": "points",
        "cost_value": 100,
        "stock_quantity": 100,
        "is_active": True
    }


@pytest.fixture(scope="function")
def sample_task_data() -> Dict[str, Any]:
    """示例任务数据"""
    return {
        "id": str(uuid4()),
        "title": "测试任务",
        "description": "这是一个测试任务",
        "status": "active",
        "priority": "medium",
        "estimated_minutes": 30
    }


# 测试标记配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


# 测试数据工厂
class UnitTestDataFactory:
    """单元测试数据工厂"""

    @staticmethod
    def create_user(**overrides) -> Dict[str, Any]:
        """创建用户数据"""
        data = {
            "id": str(uuid4()),
            "nickname": "测试用户",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "单元测试用户"
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_points_transaction(**overrides) -> Dict[str, Any]:
        """创建积分交易数据"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "amount": 100,
            "source_type": "test",
            "source_id": str(uuid4())
        }
        data.update(overrides)
        return data

    @staticmethod
    def create_reward_transaction(**overrides) -> Dict[str, Any]:
        """创建奖励交易数据"""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "reward_id": str(uuid4()),
            "quantity": 1,
            "source_type": "test"
        }
        data.update(overrides)
        return data


@pytest.fixture(scope="function")
def unit_test_data_factory() -> UnitTestDataFactory:
    """单元测试数据工厂实例"""
    return UnitTestDataFactory()


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


# 通用模拟对象
@pytest.fixture(scope="function")
def mock_repository() -> Mock:
    """通用仓储模拟"""
    repo = Mock()
    repo.create = Mock(return_value=Mock(id=str(uuid4())))
    repo.get_by_id = Mock(return_value=Mock())
    repo.get_all = Mock(return_value=[])
    repo.update = Mock(return_value=Mock())
    repo.delete = Mock(return_value=True)
    repo.count = Mock(return_value=0)
    return repo


# 异步测试支持
@pytest.fixture(scope="function")
def mock_async_session() -> Mock:
    """异步数据库会话模拟"""
    session = Mock()
    session.add = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.exec = Mock()
    session.query = Mock()
    session.close = Mock()
    return session


# 错误模拟
@pytest.fixture(scope="function")
def mock_database_error() -> Exception:
    """数据库错误模拟"""
    return Exception("数据库连接失败")


@pytest.fixture(scope="function")
def mock_validation_error() -> Exception:
    """验证错误模拟"""
    return ValueError("输入数据无效")


# 清理辅助
@pytest.fixture(autouse=True)
def unit_test_cleanup():
    """单元测试自动清理"""
    yield
    # 测试后清理工作
    pass