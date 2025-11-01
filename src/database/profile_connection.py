"""
独立Profile数据库连接配置模块

本模块提供Profile数据库的独立连接功能，包括：
- 专用的Profile数据库引擎创建和管理
- Profile数据库会话的获取和控制
- 独立的连接池配置和优化
- 与主数据库的事务隔离

设计原则：
1. 数据库隔离：Profile数据与主业务数据完全分离
2. 性能优化：针对Profile查询优化的连接池配置
3. 事务隔离：确保Profile操作不影响主数据库事务
4. 配置灵活：支持环境变量和参数配置

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


class ProfileDatabaseConnection:
    """
    Profile数据库连接管理类

    负责管理Profile专用数据库引擎和会话的创建、配置和生命周期。
    与主数据库完全独立，确保数据隔离和性能优化。

    Attributes:
        database_url (str): Profile数据库连接URL
        echo (bool): 是否开启SQL语句日志输出
        _engine (Optional[Engine]): 缓存的数据库引擎实例
    """

    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        初始化Profile数据库连接管理器

        Args:
            database_url (Optional[str]): Profile数据库连接URL，如果为None则使用默认值
            echo (bool): 是否开启SQL语句日志输出，默认为False

        Environment Variables:
            PROFILE_DATABASE_URL: 环境变量中的Profile数据库连接URL，会覆盖传入参数
        """
        # 优先使用环境变量，其次使用传入参数，最后使用默认值
        self.database_url = (
            os.getenv('PROFILE_DATABASE_URL') or
            database_url or
            "sqlite:///./profiles.db"
        )
        self.echo = echo
        self._engine: Optional[Engine] = None

    def get_engine(self) -> Engine:
        """
        获取Profile数据库引擎实例

        采用单例模式，确保多次调用返回同一个引擎实例。
        针对Profile数据查询进行优化配置。

        Returns:
            Engine: SQLAlchemy数据库引擎实例

        Note:
            - SQLite: 配置check_same_thread=False以支持多线程
            - 连接池: 针对Profile查询优化的连接池设置
        """
        if self._engine is None:
            # 根据数据库类型应用不同的配置
            if self.database_url.startswith('sqlite'):
                # SQLite特定配置，优化Profile查询性能
                engine_kwargs = {
                    'connect_args': {"check_same_thread": False},
                    'poolclass': StaticPool,
                    'echo': self.echo,
                    # Profile数据库优化设置
                    'pool_pre_ping': True,
                }
            else:
                # PostgreSQL, MySQL等数据库的通用配置
                engine_kwargs = {
                    'echo': self.echo,
                    'pool_pre_ping': True,  # 连接前检查连接是否有效
                    'pool_recycle': 3600,   # 1小时后回收连接
                    'pool_size': 5,         # Profile查询适中的连接池大小
                    'max_overflow': 10,     # 最大溢出连接数
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
        获取Profile数据库会话的上下文管理器

        创建一个Profile数据库会话，并在上下文结束时自动关闭，
        确保资源正确释放，避免连接泄漏。

        Yields:
            Session: SQLAlchemy数据库会话实例

        Example:
            >>> profile_db = ProfileDatabaseConnection()
            >>> with profile_db.get_session() as session:
            ...     # 使用session进行Profile数据库操作
            ...     profile = session.get(ProfileUser, user_id)
            ...     # 退出上下文时session自动关闭
        """
        engine = self.get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def create_tables(self):
        """
        创建所有Profile数据库表

        根据已定义的Profile模型创建数据库表。
        用于数据库初始化。
        """
        try:
            from .profile_migration import get_profile_migration
            migration = get_profile_migration()
            return migration.create_profile_tables()
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"创建Profile数据库表失败: {e}")
            raise

    def check_connection(self) -> bool:
        """
        检查Profile数据库连接是否正常

        Returns:
            bool: 连接是否正常
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception:
            return False


# 全局Profile数据库连接实例
_global_profile_db_connection: Optional[ProfileDatabaseConnection] = None


def get_profile_database_connection() -> ProfileDatabaseConnection:
    """
    获取全局Profile数据库连接实例

    创建并返回一个全局的Profile数据库连接实例，确保整个应用中
    使用相同的Profile数据库配置和引擎实例。

    Returns:
        ProfileDatabaseConnection: 全局Profile数据库连接实例
    """
    global _global_profile_db_connection
    if _global_profile_db_connection is None:
        _global_profile_db_connection = ProfileDatabaseConnection(
            echo=os.getenv('DEBUG', 'false').lower() == 'true'
        )
    return _global_profile_db_connection


def reset_profile_database_connection():
    """
    重置全局Profile数据库连接实例（用于测试和配置更改）
    """
    global _global_profile_db_connection
    _global_profile_db_connection = None


def get_profile_engine() -> Engine:
    """
    获取全局Profile数据库引擎

    便捷函数，直接返回全局Profile数据库连接的引擎实例。

    Returns:
        Engine: 全局Profile数据库引擎实例
    """
    return get_profile_database_connection().get_engine()


@contextmanager
def get_profile_session() -> Generator[Session, None, None]:
    """
    获取全局Profile数据库会话

    便捷函数，直接返回全局Profile数据库连接的会话上下文管理器。

    Yields:
        Session: Profile数据库会话实例

    Example:
        >>> with get_profile_session() as session:
        ...     # 执行Profile数据库操作
        ...     pass
    """
    with get_profile_database_connection().get_session() as session:
        yield session