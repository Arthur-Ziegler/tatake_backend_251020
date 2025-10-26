"""
测试配置和共享Fixtures

提供统一的测试基础设施，包括：
1. 数据库配置和清理
2. 测试数据工厂
3. Mock服务配置
4. 异步测试支持
5. 测试环境隔离

设计原则：
- 测试隔离：每个测试用例独立运行，不相互影响
- 数据清理：测试后自动清理，保持环境干净
- 配置统一：统一的测试配置和环境变量
- 异步支持：完整的异步测试框架支持

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施重构
"""

import asyncio
import os
import pytest
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import Mock, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 设置测试环境变量
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "ERROR"  # 测试时减少日志噪音
os.environ["SMS_MODE"] = "mock"  # 测试时使用Mock SMS

# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """
    提供内存数据库session用于测试

    每个测试函数都会获得一个全新的内存数据库，
    确保测试之间的完全隔离。
    """
    # 创建内存数据库引擎
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # 创建会话工厂
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    # 创建所有表
    from src.domains.auth.models import Auth, AuthLog, SMSVerification
    from src.domains.task.models import Task
    from src.domains.reward.models import Reward, RewardRecipe, RewardTransaction
    from src.domains.top3.models import TaskTop3
    from src.domains.focus.models import FocusSession

    # 创建所有需要的表
    Auth.metadata.create_all(bind=engine)
    AuthLog.metadata.create_all(bind=engine)
    SMSVerification.metadata.create_all(bind=engine)
    Task.metadata.create_all(bind=engine)
    Reward.metadata.create_all(bind=engine)
    RewardRecipe.metadata.create_all(bind=engine)
    RewardTransaction.metadata.create_all(bind=engine)
    TaskTop3.metadata.create_all(bind=engine)
    FocusSession.metadata.create_all(bind=engine)

    # 提供session
    session = SessionLocal()
    yield session

    # 清理：关闭session并删除所有表
    session.close()
    # 内存数据库会自动清理


@pytest.fixture(scope="function")
def auth_db_session(test_db_session: Session) -> Session:
    """
    提供认证数据库session（别名，为了向后兼容）
    """
    yield test_db_session


@pytest.fixture
def mock_sms_client():
    """
    提供Mock SMS客户端

    模拟SMS发送行为，避免真实网络调用。
    支持验证发送参数和模拟响应。
    """
    client = Mock()

    async def mock_send_code(phone: str, code: str):
        # 记录调用参数用于验证
        mock_send_code.calls.append({"phone": phone, "code": code})

        # 模拟不同的响应场景
        if phone in ["13800138000", "13800138001"]:
            return {"success": True, "message_id": f"mock_{len(mock_send_code.calls)}"}
        else:
            return {"success": False, "error": "Phone not supported"}

    # 初始化调用记录
    mock_send_code.calls = []
    client.send_code = mock_send_code

    yield client


@pytest.fixture
def mock_jwt_service():
    """
    提供Mock JWT服务

    模拟JWT生成和验证，避免依赖真实的密钥。
    """
    service = Mock()

    def mock_generate_tokens(user_data):
        return {
            "access_token": f"mock_access_token_{user_data['user_id']}",
            "refresh_token": f"mock_refresh_token_{user_data['user_id']}",
            "expires_in": 3600,
            "token_type": "bearer"
        }

    service.generate_tokens = mock_generate_tokens
    yield service


@asynccontextmanager
async def get_test_auth_service() -> AsyncGenerator:
    """
    异步上下文管理器：创建带测试数据库的认证服务

    专门为异步测试设计，确保session在整个异步测试期间保持活跃。
    """
    from src.domains.auth.dependencies import get_auth_service_with_db

    # 创建测试数据库
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # 创建表结构
    from src.domains.auth.models import Auth, AuthLog, SMSVerification
    Auth.metadata.create_all(bind=engine)
    AuthLog.metadata.create_all(bind=engine)
    SMSVerification.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        # 使用依赖注入创建service
        async with get_auth_service_with_db() as service:
            # 替换为测试session
            service.repository.session = session
            service.audit_repository.session = session
            yield service
    finally:
        session.close()


@pytest.fixture
async def async_auth_service():
    """
    异步测试fixture：提供认证服务实例

    适用于异步测试函数，自动管理session生命周期。
    """
    async with get_test_auth_service() as service:
        yield service


# 测试数据工厂
@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "wechat_openid": "wx_test_12345",
        "is_guest": False,
        "jwt_version": 1,
    }


@pytest.fixture
def sample_sms_data():
    """示例SMS数据"""
    return {
        "phone": "13800138000",
        "code": "123456",
        "scene": "register",
        "ip_address": "127.0.0.1",
    }


# 异步测试支持
@pytest.fixture
async def async_test_client():
    """
    提供异步测试客户端

    用于测试FastAPI的异步端点。
    """
    from httpx import AsyncClient
    from src.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# 错误注入支持
@pytest.fixture
def error_injector():
    """
    错误注入器fixture

    支持在测试中模拟各种错误场景。
    """
    class ErrorInjector:
        def __init__(self):
            self.errors = {}

        def inject_error(self, target: str, error: Exception):
            """注入错误到指定目标"""
            self.errors[target] = error

        def should_error(self, target: str) -> bool:
            """检查目标是否应该抛出错误"""
            return target in self.errors

        def get_error(self, target: str) -> Optional[Exception]:
            """获取目标对应的错误"""
            return self.errors.get(target)

        def clear(self):
            """清除所有注入的错误"""
            self.errors.clear()

    injector = ErrorInjector()
    yield injector
    injector.clear()


# 性能测试支持
@pytest.fixture
def performance_profiler():
    """
    性能分析器fixture

    用于测试代码性能，识别性能瓶颈。
    """
    import time

    class PerformanceProfiler:
        def __init__(self):
            self.timings = {}

        def start_timer(self, name: str):
            """开始计时"""
            self.timings[name] = {"start": time.time()}

        def end_timer(self, name: str) -> float:
            """结束计时，返回耗时（秒）"""
            if name in self.timings:
                duration = time.time() - self.timings[name]["start"]
                self.timings[name]["duration"] = duration
                return duration
            return 0.0

        def get_timing(self, name: str) -> Optional[float]:
            """获取指定计时"""
            return self.timings.get(name, {}).get("duration")

        def get_all_timings(self) -> dict:
            """获取所有计时结果"""
            return {
                name: data.get("duration", 0.0)
                for name, data in self.timings.items()
                if "duration" in data
            }

    profiler = PerformanceProfiler()
    yield profiler


# 测试标记定义
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "functional: 功能测试标记"
    )
    config.addinivalue_line(
        "markers", "async_test: 异步测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试标记"
    )


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集，添加默认标记"""
    for item in items:
        # 根据文件路径自动添加标记
        if "units/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "functional/" in str(item.fspath):
            item.add_marker(pytest.mark.functional)

        # 异步测试标记
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.async_test)