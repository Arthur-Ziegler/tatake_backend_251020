"""
数据库模块

提供数据库连接和会话管理的核心功能，遵循FastAPI最佳实践。
"""

from typing import Annotated

from .connection import get_database_connection
from sqlmodel import Session
from fastapi import Depends


def get_db_session():
    """
    FastAPI数据库session依赖（使用yield模式）

    这个函数提供了一个统一的数据库session获取方式，
    确保session在请求结束后正确关闭。

    遵循FastAPI最佳实践：
    1. 使用try/finally块确保资源清理
    2. 支持异常处理和回滚
    3. 单session per request原则

    使用方式：
    @app.get("/some-endpoint")
    def some_endpoint(session: SessionDep):
        # 使用session进行数据库操作
        pass
    """
    engine = get_database_connection().get_engine()
    session = Session(engine)
    try:
        yield session
    except Exception:
        # 发生异常时回滚事务
        session.rollback()
        raise
    finally:
        # 确保session总是关闭
        session.close()


def get_session():
    """向后兼容的session获取函数"""
    return get_db_session()


# 使用Annotated类型提示，提供更好的类型安全和开发体验
SessionDep = Annotated[Session, Depends(get_db_session)]


# 导出数据库连接和引擎
from .connection import get_engine

__all__ = ["get_db_session", "get_session", "get_engine", "get_database_connection", "SessionDep"]