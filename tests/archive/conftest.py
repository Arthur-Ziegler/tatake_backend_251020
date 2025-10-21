"""
pytest配置文件

配置服务层测试所需的夹具、Mock对象和测试环境。
遵循TDD最佳实践，提供可复用的测试组件。
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Any, Dict, Optional
import uuid
from datetime import datetime, timedelta

# 导入Service层组件
from src.services import BaseService, ServiceFactory
from src.services.exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    InsufficientBalanceException,
    DuplicateResourceException,
    AuthenticationException,
    AuthorizationException
)

# 导入Repository层
from src.repositories.user import UserRepository
from src.repositories.task import TaskRepository
from src.repositories.focus import FocusRepository
from src.repositories.reward import RewardRepository

# 导入数据模型
from src.models.user import User
from src.models.task import Task
from src.models.focus import FocusSession
from src.models.reward import Reward


# ==================== Mock Repository Factory ====================

@pytest.fixture
def mock_user_repo():
    """创建模拟的UserRepository"""
    mock_repo = Mock(spec=UserRepository)

    # 配置基础方法
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.update = Mock()
    mock_repo.delete = Mock()
    mock_repo.exists = Mock()
    mock_repo.count = Mock()
    mock_repo.find_many = Mock()

    # 配置UserRepository特有方法
    mock_repo.find_by_email = Mock()
    mock_repo.find_by_phone = Mock()
    mock_repo.find_by_wechat_openid = Mock()
    mock_repo.find_registered_users = Mock()
    mock_repo.find_guest_users = Mock()
    mock_repo.find_active_users = Mock()
    mock_repo.email_exists = Mock()
    mock_repo.phone_exists = Mock()
    mock_repo.create_guest_user = Mock()
    mock_repo.upgrade_guest_to_registered = Mock()

    return mock_repo


@pytest.fixture
def mock_task_repo():
    """创建模拟的TaskRepository"""
    mock_repo = Mock(spec=TaskRepository)

    # 配置基础方法
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.update = Mock()
    mock_repo.delete = Mock()
    mock_repo.exists = Mock()
    mock_repo.count = Mock()
    mock_repo.find_many = Mock()

    # 配置TaskRepository特有方法
    mock_repo.find_by_user_id = Mock()
    mock_repo.find_by_status = Mock()
    mock_repo.find_by_priority = Mock()
    mock_repo.find_parent_tasks = Mock()
    mock_repo.find_subtasks = Mock()
    mock_repo.find_top3_tasks = Mock()
    mock_repo.update_status = Mock()
    mock_repo.complete_task = Mock()

    return mock_repo


@pytest.fixture
def mock_focus_repo():
    """创建模拟的FocusRepository"""
    mock_repo = Mock(spec=FocusRepository)

    # 配置基础方法
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.update = Mock()
    mock_repo.delete = Mock()
    mock_repo.exists = Mock()
    mock_repo.count = Mock()
    mock_repo.find_many = Mock()

    # 配置FocusRepository特有方法
    mock_repo.find_by_user_id = Mock()
    mock_repo.find_active_sessions = Mock()
    mock_repo.find_completed_sessions = Mock()
    mock_repo.find_sessions_by_date_range = Mock()
    mock_repo.start_session = Mock()
    mock_repo.complete_session = Mock()
    mock_repo.pause_session = Mock()
    mock_repo.resume_session = Mock()
    mock_repo.get_today_total_time = Mock()
    mock_repo.get_week_total_time = Mock()
    mock_repo.get_month_total_time = Mock()

    return mock_repo


@pytest.fixture
def mock_reward_repo():
    """创建模拟的RewardRepository"""
    mock_repo = Mock(spec=RewardRepository)

    # 配置基础方法
    mock_repo.create = Mock()
    mock_repo.get_by_id = Mock()
    mock_repo.update = Mock()
    mock_repo.delete = Mock()
    mock_repo.exists = Mock()
    mock_repo.count = Mock()
    mock_repo.find_many = Mock()

    # 配置RewardRepository特有方法
    mock_repo.find_by_user_id = Mock()
    mock_repo.find_available_rewards = Mock()
    mock_repo.find_user_rewards = Mock()
    mock_repo.redeem_reward = Mock()
    mock_repo.update_user_points = Mock()
    mock_repo.get_user_points = Mock()
    mock_repo.add_transaction = Mock()
    mock_repo.find_transactions = Mock()
    mock_repo.draw_lottery = Mock()

    return mock_repo


# ==================== Service Factory Fixtures ====================

@pytest.fixture
def base_service(mock_user_repo, mock_task_repo, mock_focus_repo, mock_reward_repo):
    """创建BaseService实例，注入所有Mock Repository"""
    return BaseService(
        user_repo=mock_user_repo,
        task_repo=mock_task_repo,
        focus_repo=mock_focus_repo,
        reward_repo=mock_reward_repo
    )


@pytest.fixture
def service_factory():
    """创建ServiceFactory实例"""
    return ServiceFactory()


# ==================== 测试数据工厂 ====================

@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "nickname": "测试用户",
        "password_hash": "hashed_password_123",
        "user_type": "registered",
        "is_active": True,
        "points": 100,
        "fragments": 50,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_task_data():
    """示例任务数据"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "title": "测试任务",
        "description": "这是一个测试任务",
        "status": "pending",
        "priority": "high",
        "parent_id": None,
        "is_top3": False,
        "due_date": datetime.now() + timedelta(days=1),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_focus_session_data():
    """示例专注会话数据"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "session_type": "focus",
        "duration_minutes": 25,
        "actual_duration_minutes": 25,
        "status": "completed",
        "start_time": datetime.now() - timedelta(minutes=25),
        "end_time": datetime.now(),
        "notes": "专注完成测试任务",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def sample_reward_data():
    """示例奖励数据"""
    return {
        "id": str(uuid.uuid4()),
        "name": "测试奖励",
        "description": "这是一个测试奖励",
        "reward_type": "physical",
        "required_points": 100,
        "required_fragments": 10,
        "is_available": True,
        "stock_quantity": 100,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


# ==================== Mock Model Objects ====================

@pytest.fixture
def mock_user(sample_user_data):
    """创建模拟User对象"""
    user = Mock()
    # 设置基本属性
    for key, value in sample_user_data.items():
        setattr(user, key, value)
    # 设置to_dict方法
    user.to_dict = Mock(return_value=sample_user_data)
    return user


@pytest.fixture
def mock_task(sample_task_data):
    """创建模拟Task对象"""
    task = Mock(spec=Task)
    for key, value in sample_task_data.items():
        setattr(task, key, value)
    task.to_dict.return_value = sample_task_data
    return task


@pytest.fixture
def mock_focus_session(sample_focus_session_data):
    """创建模拟FocusSession对象"""
    session = Mock(spec=FocusSession)
    for key, value in sample_focus_session_data.items():
        setattr(session, key, value)
    session.to_dict.return_value = sample_focus_session_data
    return session


@pytest.fixture
def mock_reward(sample_reward_data):
    """创建模拟Reward对象"""
    reward = Mock(spec=Reward)
    for key, value in sample_reward_data.items():
        setattr(reward, key, value)
    reward.to_dict.return_value = sample_reward_data
    return reward


# ==================== 测试工具函数 ====================

@pytest.fixture
def assert_business_exception():
    """创建业务异常断言函数"""
    def _assert_exception(exception, expected_error_code, expected_user_message=None):
        """断言业务异常的属性"""
        assert isinstance(exception, BusinessException)
        assert exception.error_code == expected_error_code

        if expected_user_message:
            assert exception.user_message == expected_user_message

        # 验证异常包含必要的结构化信息
        assert hasattr(exception, 'details')
        assert hasattr(exception, 'debug_info')
        assert hasattr(exception, 'suggestions')

        # 验证to_dict方法正常工作
        exception_dict = exception.to_dict()
        assert 'error_code' in exception_dict
        assert 'message' in exception_dict
        assert 'user_message' in exception_dict
        assert 'details' in exception_dict
        assert 'debug_info' in exception_dict
        assert 'suggestions' in exception_dict

    return _assert_exception


@pytest.fixture
def temp_db_session():
    """临时数据库会话夹具（用于集成测试）"""
    # 这里可以创建内存数据库或测试数据库会话
    # 目前返回Mock，实际集成测试时需要真实数据库连接
    mock_session = Mock()
    mock_session.begin.return_value.__enter__ = Mock()
    mock_session.begin.return_value.__exit__ = Mock()
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    return mock_session


# ==================== 测试配置 ====================

def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """自动应用于所有测试的环境设置"""
    # 设置测试环境变量
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # 配置日志记录器避免测试输出污染
    import logging
    logging.getLogger("src.services").setLevel(logging.CRITICAL)


# ==================== 性能测试工具 ====================

@pytest.fixture
def performance_monitor():
    """性能监控夹具"""
    import time
    from contextlib import contextmanager

    @contextmanager
    def monitor(operation_name: str, max_time_seconds: float = 1.0):
        """监控操作执行时间"""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            assert execution_time <= max_time_seconds, f"Operation '{operation_name}' took too long: {execution_time:.3f}s > {max_time_seconds}s"

    return monitor