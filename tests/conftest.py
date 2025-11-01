"""
测试框架主配置文件

提供全局测试配置和通用fixtures。
"""

import pytest
import sys
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# 全局配置
def pytest_configure(config):
    """配置pytest全局设置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "functional: 功能测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "smoke: 冒烟测试")

    # 按域标记
    config.addinivalue_line("markers", "auth: 认证域测试")
    config.addinivalue_line("markers", "task: 任务域测试")
    config.addinivalue_line("markers", "top3: Top3域测试")
    config.addinivalue_line("markers", "reward: 奖励域测试")
    config.addinivalue_line("markers", "points: 积分域测试")
    config.addinivalue_line("markers", "chat: 聊天域测试")
    config.addinivalue_line("markers", "user: 用户域测试")
    config.addinivalue_line("markers", "focus: 专注域测试")

@pytest.fixture(scope="session")
def test_config():
    """测试配置fixture"""
    return {
        "database_url": "sqlite:///:memory:",
        "test_user_id": "test-user-123",
        "timeout": 30,
        "retry_attempts": 3
    }


@pytest.fixture(scope="function")
def db_session():
    """数据库测试会话fixture"""
    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # 创建所有表
    SQLModel.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user_id():
    """示例用户ID fixture"""
    return uuid4()