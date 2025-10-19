"""
pytest 配置和共享夹具
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from typing import Generator

# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """创建测试数据库引擎"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """创建数据库会话夹具"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def transaction_session(session) -> Generator[Session, None, None]:
    """事务会话夹具，测试后自动回滚"""
    transaction = session.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()