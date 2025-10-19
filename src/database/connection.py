"""
数据库连接配置模块

本模块提供数据库连接的核心功能，包括：
- 数据库引擎的创建和管理
- 数据库会话的获取和控制
- 连接池的配置和优化
- 环境变量的处理和覆盖

设计原则：
1. 单例模式：确保每个应用只有一个数据库引擎实例
2. 资源管理：使用上下文管理器确保会话正确关闭
3. 配置灵活：支持环境变量和参数配置
4. 线程安全：确保多线程环境下的安全性
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


class DatabaseConnection:
    """
    数据库连接管理类

    负责管理数据库引擎和会话的创建、配置和生命周期。
    采用单例模式确保整个应用中只有一个引擎实例。

    Attributes:
        database_url (str): 数据库连接URL
        echo (bool): 是否开启SQL语句日志输出
        _engine (Optional[Engine]): 缓存的数据库引擎实例
    """

    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        初始化数据库连接管理器

        Args:
            database_url (Optional[str]): 数据库连接URL，如果为None则使用默认值或环境变量
            echo (bool): 是否开启SQL语句日志输出，默认为False

        Environment Variables:
            DATABASE_URL: 环境变量中的数据库连接URL，会覆盖传入的database_url参数
        """
        # 优先使用环境变量，其次使用传入参数，最后使用默认值
        self.database_url = (
            os.getenv('DATABASE_URL') or
            database_url or
            "sqlite:///./tatake.db"
        )
        self.echo = echo
        self._engine: Optional[Engine] = None

    def get_engine(self) -> Engine:
        """
        获取数据库引擎实例

        采用单例模式，确保多次调用返回同一个引擎实例。
        根据数据库类型的不同，应用相应的配置优化。

        Returns:
            Engine: SQLAlchemy数据库引擎实例

        Note:
            - SQLite: 配置check_same_thread=False以支持多线程
            - PostgreSQL/MySQL: 使用默认连接池配置
        """
        if self._engine is None:
            # 根据数据库类型应用不同的配置
            if self.database_url.startswith('sqlite'):
                # SQLite特定配置
                engine_kwargs = {
                    'connect_args': {"check_same_thread": False},
                    'poolclass': StaticPool,
                    'echo': self.echo
                }
            else:
                # PostgreSQL, MySQL等数据库的通用配置
                engine_kwargs = {
                    'echo': self.echo,
                    'pool_pre_ping': True,  # 连接前检查连接是否有效
                    'pool_recycle': 3600,   # 1小时后回收连接
                }

            try:
                self._engine = create_engine(self.database_url, **engine_kwargs)
            except Exception as e:
                # 如果驱动不存在，抛出明确的错误信息
                if "No module named" in str(e):
                    driver_name = self.database_url.split('://')[0].split('+')[0]
                    raise ImportError(
                        f"数据库驱动 '{driver_name}' 未安装。"
                        f"请安装相应的驱动包，例如："
                        f"PostgreSQL: pip install psycopg2-binary, "
                        f"MySQL: pip install PyMySQL"
                    ) from e
                raise

        return self._engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话的上下文管理器

        创建一个数据库会话，并在上下文结束时自动关闭，
        确保资源正确释放，避免连接泄漏。

        Yields:
            Session: SQLAlchemy数据库会话实例

        Example:
            >>> db = DatabaseConnection()
            >>> with db.get_session() as session:
            ...     # 使用session进行数据库操作
            ...     user = session.get(User, user_id)
            ...     # 退出上下文时session自动关闭
        """
        engine = self.get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()


# 全局数据库连接实例
_global_db_connection: Optional[DatabaseConnection] = None


def get_database_connection() -> DatabaseConnection:
    """
    获取全局数据库连接实例

    创建并返回一个全局的数据库连接实例，确保整个应用中
    使用相同的数据库配置和引擎实例。

    Returns:
        DatabaseConnection: 全局数据库连接实例
    """
    global _global_db_connection
    if _global_db_connection is None:
        # 从环境变量读取配置
        _global_db_connection = DatabaseConnection(
            database_url=os.getenv('DATABASE_URL'),
            echo=os.getenv('DEBUG', 'false').lower() == 'true'
        )
    return _global_db_connection


def get_engine() -> Engine:
    """
    获取全局数据库引擎

    便捷函数，直接返回全局数据库连接的引擎实例。

    Returns:
        Engine: 全局数据库引擎实例
    """
    return get_database_connection().get_engine()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取全局数据库会话

    便捷函数，直接返回全局数据库连接的会话上下文管理器。

    Yields:
        Session: 数据库会话实例

    Example:
        >>> with get_session() as session:
        ...     # 执行数据库操作
        ...     pass
    """
    with get_database_connection().get_session() as session:
        yield session