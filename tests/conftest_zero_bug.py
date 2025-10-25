"""
零Bug测试体系 - 核心配置和Fixtures

提供标准化的测试环境配置、数据生成和测试工具。

设计原则：
1. 环境隔离：每个测试独立运行
2. 数据一致：使用工厂模式生成测试数据
3. 资源管理：自动创建和清理测试资源
4. 性能优化：合理使用fixtures作用域
"""

import pytest
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Generator
from pathlib import Path

from httpx import AsyncClient, Client
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# 导入工厂
from tests.factories import (
    UserFactory, TaskFactory, RewardFactory, FocusSessionFactory,
    Top3TaskFactory, PointsTransactionFactory
)

# 项目导入
from src.api.main import app
from src.database import get_db
from src.domains.auth.models import Auth
from src.domains.task.models import Task
from src.domains.reward.models import Reward, UserReward
from src.domains.focus.models import FocusSession
from src.domains.top3.models import Top3Task


class ZeroBugTestConfig:
    """零Bug测试配置类"""

    # 测试数据库配置
    TEST_DATABASE_URL = "sqlite:///:memory:"

    # 测试用户配置
    TEST_USER = {
        "wechat_openid": "test_zero_bug_user",
        "username": "zero_bug_tester",
        "email": "zerobug@test.com",
        "is_guest": False,
        "is_active": True,
    }

    # API配置
    API_BASE_URL = "http://testserver"

    # 质量标准
    REQUIRED_COVERAGE = 95.0
    MAX_TEST_TIME = 1.0  # 单元测试最大时间(秒)
    MAX_INTEGRATION_TIME = 10.0  # 集成测试最大时间(秒)


@pytest.fixture(scope="session")
def test_config():
    """测试配置fixture"""
    return ZeroBugTestConfig()


@pytest.fixture(scope="function")
def temp_dir():
    """临时目录fixture"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture(scope="function")
def test_database():
    """测试数据库fixture

    为每个测试函数创建独立的内存数据库。
    确保测试之间的完全隔离。
    """
    # 创建内存数据库
    engine = create_engine(
        ZeroBugTestConfig.TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
        echo=False  # 测试时不打印SQL日志
    )

    # 创建所有表
    from src.database import Base
    Base.metadata.create_all(bind=engine)

    # 创建会话
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 提供数据库会话
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # 清理数据库
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(test_database):
    """测试客户端fixture

    提供配置了测试数据库的FastAPI测试客户端。
    """
    # 覆盖数据库依赖
    def override_get_db():
        try:
            yield test_database
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with Client(app=app, base_url=ZeroBugTestConfig.API_BASE_URL) as client:
        yield client

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_test_client(test_database):
    """异步测试客户端fixture"""
    def override_get_db():
        try:
            yield test_database
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url=ZeroBugTestConfig.API_BASE_URL) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_user(test_database):
    """认证用户fixture

    在数据库中创建一个测试用户并返回用户数据。
    """
    # 创建测试用户
    user_data = UserFactory.create(
        wechat_openid=ZeroBugTestConfig.TEST_USER["wechat_openid"],
        username=ZeroBugTestConfig.TEST_USER["username"],
        email=ZeroBugTestConfig.TEST_USER["email"],
        is_guest=ZeroBugTestConfig.TEST_USER["is_guest"],
        is_active=ZeroBugTestConfig.TEST_USER["is_active"],
    )

    # 保存到数据库
    db_user = Auth(**user_data)
    test_database.add(db_user)
    test_database.commit()
    test_database.refresh(db_user)

    return {
        "id": str(db_user.id),
        "wechat_openid": db_user.wechat_openid,
        "username": db_user.username,
        "email": db_user.email,
        "is_guest": db_user.is_guest,
        "is_active": db_user.is_active,
    }


@pytest.fixture(scope="function")
def authenticated_client(test_client, authenticated_user):
    """已认证的测试客户端fixture

    提供带有认证信息的测试客户端。
    """
    # 生成测试Token
    import jwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": authenticated_user["wechat_openid"],
        "user_id": authenticated_user["id"],
        "is_guest": authenticated_user["is_guest"],
        "jwt_version": 1,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "token_type": "access"
    }

    # 使用测试密钥
    secret_key = "test_secret_key_zero_bug"
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    # 设置认证头
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    yield test_client

    # 清理认证头
    test_client.headers.pop("Authorization", None)


@pytest.fixture(scope="function")
def sample_tasks(test_database, authenticated_user):
    """示例任务fixture

    为测试用户创建一组示例任务。
    """
    tasks_data = TaskFactory.create_batch_with_statuses(
        count=5,
        user_id=authenticated_user["wechat_openid"]
    )

    # 保存到数据库
    db_tasks = []
    for task_data in tasks_data:
        db_task = Task(**task_data)
        test_database.add(db_task)
        test_database.commit()
        test_database.refresh(db_task)
        db_tasks.append(db_task)

    return db_tasks


@pytest.fixture(scope="function")
def sample_rewards(test_database):
    """示例奖励fixture

    创建一组示例奖励。
    """
    rewards_data = RewardFactory.create_batch(3)

    # 保存到数据库
    db_rewards = []
    for reward_data in rewards_data:
        db_reward = Reward(**reward_data)
        test_database.add(db_reward)
        test_database.commit()
        test_database.refresh(db_reward)
        db_rewards.append(db_reward)

    return db_rewards


@pytest.fixture(scope="function")
def mock_external_services():
    """模拟外部服务fixture

    模拟SMS、微信、支付等外部服务。
    """
    # 这里可以配置各种外部服务的模拟
    # 例如使用responses库模拟HTTP请求
    yield


# 零Bug测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试 - 快速隔离测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试 - 模块协作测试"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试 - 完整用户场景测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试 - 基准测试"
    )
    config.addinivalue_line(
        "markers", "security: 安全测试 - 漏洞扫描"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试 - 执行时间超过30秒"
    )
    config.addinivalue_line(
        "markers", "database: 需要数据库的测试"
    )
    config.addinivalue_line(
        "markers", "external: 需要外部服务的测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集，自动添加标记"""
    for item in items:
        # 根据测试文件路径自动添加标记
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # 根据测试名称自动添加标记
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        if "security" in item.name.lower():
            item.add_marker(pytest.mark.security)
        if "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.concurrent)


# 零Bug测试钩子
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """生成详细的测试报告"""
    outcome = yield
    rep = outcome.get_result()

    # 记录测试开始时间
    if call.when == "setup":
        rep.start_time = datetime.now(timezone.utc)

    # 计算测试执行时间
    if call.when == "teardown" and hasattr(rep, "start_time"):
        duration = (datetime.now(timezone.utc) - rep.start_time).total_seconds()

        # 检查性能标准
        if item.get_closest_marker("unit") and duration > ZeroBugTestConfig.MAX_TEST_TIME:
            pytest.fail(f"单元测试执行时间 {duration:.2f}s 超过标准 {ZeroBugTestConfig.MAX_TEST_TIME}s")

        if item.get_closest_marker("integration") and duration > ZeroBugTestConfig.MAX_INTEGRATION_TIME:
            pytest.fail(f"集成测试执行时间 {duration:.2f}s 超过标准 {ZeroBugTestConfig.MAX_INTEGRATION_TIME}s")


# 零Bug测试辅助函数
class ZeroBugTestHelper:
    """零Bug测试辅助类"""

    @staticmethod
    def assert_valid_response(response, expected_status: int = 200):
        """断言API响应有效"""
        assert response.status_code == expected_status, f"期望状态码 {expected_status}, 实际 {response.status_code}"

        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert "code" in data, "响应应包含code字段"
            assert data["code"] == 200, f"API返回错误: {data}"
            return data

        return response

    @staticmethod
    def assert_performance(start_time, max_duration: float):
        """断言性能标准"""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        assert duration <= max_duration, f"执行时间 {duration:.2f}s 超过标准 {max_duration}s"

    @staticmethod
    def create_test_user_data(**overrides):
        """创建测试用户数据"""
        return UserFactory.create(**overrides)

    @staticmethod
    def create_test_task_data(user_id: str, **overrides):
        """创建测试任务数据"""
        return TaskFactory.create(user_id=user_id, **overrides)


# 在测试中可用的全局辅助函数
@pytest.fixture(scope="session")
def test_helper():
    """测试辅助函数fixture"""
    return ZeroBugTestHelper()