"""
Pytest配置和共享fixtures

提供测试环境的配置和共享的测试工具函数，遵循FastAPI最佳实践。

测试结构:
- 单元测试 (unit): 测试单个函数或类
- 集成测试 (integration): 测试API端点和数据库交互
- 端到端测试 (e2e): 模拟完整用户流程

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from uuid import uuid4
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

# 导入FastAPI应用
from src.api.main import app

# 测试数据库配置 - 使用内存数据库以提高测试速度
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # 测试时关闭SQL日志
    pool_pre_ping=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient fixture

    提供用于测试的FastAPI客户端，支持同步测试。
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    异步HTTP客户端fixture

    提供用于异步测试的httpx AsyncClient，使用ASGITransport
    直接与FastAPI应用交互，无需运行服务器。
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """
    测试数据库会话fixture

    提供独立的测试数据库会话，确保测试之间不会相互影响。
    每个测试函数都会获得一个全新的数据库会话。
    使用内存数据库确保完全隔离。
    """
    # 创建测试数据库表
    SQLModel.metadata.create_all(test_engine)

    # 提供数据库会话
    session = TestingSessionLocal()
    try:
        yield session
        # 提交事务以确保测试完成
        session.commit()
    except Exception:
        # 发生异常时回滚
        session.rollback()
        raise
    finally:
        session.close()
        # 清理测试数据库
        SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
async def async_test_db_session() -> AsyncGenerator[Session, None]:
    """
    异步测试数据库会话fixture

    为异步测试提供独立的数据库会话。
    每个测试函数都会获得一个全新的数据库会话。
    """
    # 创建测试数据库表
    SQLModel.metadata.create_all(test_engine)

    # 提供数据库会话
    session = TestingSessionLocal()
    try:
        yield session
        # 提交事务以确保测试完成
        session.commit()
    except Exception:
        # 发生异常时回滚
        session.rollback()
        raise
    finally:
        session.close()
        # 清理测试数据库
        SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def sample_user_data():
    """示例用户数据fixture"""
    return {
        "is_guest": True,
        "device_id": "test-device-12345",
        "user_agent": "test-user-agent"
    }


@pytest.fixture
def sample_task_data():
    """示例任务数据fixture"""
    return {
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": "medium",
        "status": "pending",
        "tags": ["测试"],
        "parent_id": None,
        "due_date": None,
        "planned_start_time": None,
        "planned_end_time": None
    }


@pytest.fixture
def sample_reward_data():
    """示例奖品数据fixture"""
    return {
        "name": "测试奖品",
        "description": "这是一个测试奖品",
        "points_value": 100,
        "image_url": "https://example.com/image.jpg",
        "cost_type": "points",
        "cost_value": 100,
        "stock_quantity": 10,
        "category": "测试分类"
    }


@pytest.fixture
def auth_headers():
    """认证headers fixture"""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token"
    }


# API配置
API_BASE_URL = "http://localhost:8001"


def get_auth_headers(access_token: str) -> dict:
    """
    获取认证headers

    Args:
        access_token (str): JWT访问令牌

    Returns:
        dict: 包含认证信息的headers
    """
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }


# 领域特定数据库fixtures
@pytest.fixture(scope="function")
def auth_db_session() -> Generator[Session, None, None]:
    """Auth领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.auth.models import Auth, AuthLog

    # 创建认证数据库表
    Auth.metadata.create_all(test_engine)
    AuthLog.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # 清理所有表
        AuthLog.metadata.drop_all(test_engine)
        Auth.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def task_db_session() -> Generator[Session, None, None]:
    """Task领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.auth.models import Auth
    from src.domains.task.models import Task

    # 先创建auth表（因为task表有外键依赖）
    Auth.metadata.create_all(test_engine)
    Task.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # 清理所有表
        Task.metadata.drop_all(test_engine)
        Auth.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def reward_db_session() -> Generator[Session, None, None]:
    """Reward领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.reward.models import Reward, RewardTransaction, RewardRecipe
    from src.domains.points.models import PointsTransaction

    # 创建所有相关表
    Reward.metadata.create_all(test_engine)
    RewardTransaction.metadata.create_all(test_engine)
    RewardRecipe.metadata.create_all(test_engine)
    PointsTransaction.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # 清理所有表
        PointsTransaction.metadata.drop_all(test_engine)
        RewardRecipe.metadata.drop_all(test_engine)
        RewardTransaction.metadata.drop_all(test_engine)
        Reward.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def focus_db_session() -> Generator[Session, None, None]:
    """Focus领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.auth.models import Auth
    from src.domains.task.models import Task
    from src.domains.focus.models import FocusSession

    # 按依赖顺序创建表：Auth -> Task -> FocusSession
    Auth.metadata.create_all(test_engine)
    Task.metadata.create_all(test_engine)
    FocusSession.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # 按相反顺序清理表
        FocusSession.metadata.drop_all(test_engine)
        Task.metadata.drop_all(test_engine)
        Auth.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def chat_db_session() -> Generator[Session, None, None]:
    """Chat领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.chat.models import ChatSession, ChatMessage

    # 创建聊天数据库表
    ChatSession.metadata.create_all(test_engine)
    ChatMessage.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        ChatMessage.metadata.drop_all(test_engine)
        ChatSession.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def top3_db_session() -> Generator[Session, None, None]:
    """Top3领域专用数据库fixture"""
    # 导入模型放在fixture内部，避免初始化时的循环依赖
    from src.domains.top3.models import Top3Entry

    # 创建Top3数据库表
    Top3Entry.metadata.create_all(test_engine)

    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Top3Entry.metadata.drop_all(test_engine)


# 测试标记
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security