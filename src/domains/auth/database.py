"""
认证数据库连接管理

管理认证专用数据库的连接、会话和表创建。
认证数据库使用独立的SQLite文件，与业务数据库分离。

数据库配置:
- 数据库文件: tatake_auth.db
- 连接池: 使用aiosqlite异步连接池
- 表结构: 自动创建所有认证相关表

使用方法:
```python
from src.domains.auth.database import get_auth_db, create_tables

# 获取数据库会话
async with get_auth_db() as session:
    # 执行数据库操作
    pass

# 创建所有表
await create_tables()
```

环境变量:
- AUTH_DATABASE_URL: 认证数据库连接URL
- AUTH_ECHO_SQL: 是否输出SQL语句（调试用）
"""

import os
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel


# 数据库配置
AUTH_DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "sqlite+aiosqlite:///./tatake_auth.db"
)

# 是否在控制台输出SQL语句（调试用）
AUTH_ECHO_SQL = os.getenv("AUTH_ECHO_SQL", "false").lower() == "true"

# 创建异步引擎
auth_engine = create_async_engine(
    AUTH_DATABASE_URL,
    echo=AUTH_ECHO_SQL,
    future=True,
    # SQLite特定的连接池配置
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    },
    # 连接池配置
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建会话工厂
AuthSessionLocal = async_sessionmaker(
    bind=auth_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def get_auth_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取认证数据库会话

    这是一个异步上下文管理器，用于获取认证数据库的会话。
    使用with语句确保会话正确关闭。

    Returns:
        AsyncGenerator[AsyncSession, None]: 数据库会话

    Example:
        ```python
        async with get_auth_db() as session:
            user = await session.get(User, user_id)
        ```
    """
    async with AuthSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """
    创建认证数据库中的所有表

    该函数会根据SQLModel定义自动创建所有必要的表。
    如果表已存在，则不会重复创建。

    注意事项:
    - 使用checkfirst=True避免重复创建
    - 仅在开发环境使用，生产环境应使用数据库迁移

    Raises:
        Exception: 数据库连接或表创建失败时抛出
    """
    try:
        # 导入所有模型以确保它们被注册
        from src.domains.auth.models import (
            User,
            UserSettings,
            SMSVerification,
            TokenBlacklist,
            UserSession,
            AuthLog,
        )

        # 创建所有表
        async with auth_engine.begin() as conn:
            await conn.run_sync(
                SQLModel.metadata.create_all,
                checkfirst=True
            )

        print("✅ 认证数据库表创建成功")

    except Exception as e:
        print(f"❌ 认证数据库表创建失败: {e}")
        raise


async def drop_tables() -> None:
    """
    删除认证数据库中的所有表

    ⚠️ 警告: 此操作会删除所有数据，仅用于测试环境

    Raises:
        Exception: 数据库连接或表删除失败时抛出
    """
    try:
        # 导入所有模型
        from src.domains.auth.models import (
            User,
            UserSettings,
            SMSVerification,
            TokenBlacklist,
            UserSession,
            AuthLog,
        )

        # 删除所有表
        async with auth_engine.begin() as conn:
            await conn.run_sync(
                SQLModel.metadata.drop_all,
                checkfirst=True
            )

        print("✅ 认证数据库表删除成功")

    except Exception as e:
        print(f"❌ 认证数据库表删除失败: {e}")
        raise


async def check_connection() -> bool:
    """
    检查认证数据库连接是否正常

    Returns:
        bool: 连接是否正常

    Example:
        ```python
        if await check_connection():
            print("数据库连接正常")
        ```
    """
    try:
        from sqlalchemy import text
        async with auth_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ 数据库连接检查失败: {e}")
        return False


async def get_database_info() -> dict:
    """
    获取认证数据库基本信息

    Returns:
        dict: 数据库信息字典

    Example:
        ```python
        info = await get_database_info()
        print(f"数据库URL: {info['url']}")
        print(f"连接池大小: {info['pool_size']}")
        ```
    """
    try:
        async with get_auth_db() as session:
            # 获取表数量
            from sqlalchemy import text
            result = await session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ))
            table_count = result.scalar()

            # 获取数据库文件大小
            db_path = AUTH_DATABASE_URL.replace("sqlite+aiosqlite:///", "")
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                file_size_mb = file_size / (1024 * 1024)
            else:
                file_size_mb = 0

            return {
                "url": AUTH_DATABASE_URL,
                "echo_sql": AUTH_ECHO_SQL,
                "pool_size": auth_engine.pool.size(),
                "table_count": table_count,
                "file_size_mb": round(file_size_mb, 2),
                "dialect": str(auth_engine.dialect),
                "driver": str(auth_engine.driver),
            }

    except Exception as e:
        print(f"❌ 获取数据库信息失败: {e}")
        return {}


class AuthDatabaseManager:
    """
    认证数据库管理器

    提供数据库连接管理、表操作、备份恢复等高级功能。
    """

    def __init__(self):
        self.engine = auth_engine
        self.session_factory = AuthSessionLocal

    async def health_check(self) -> dict:
        """
        数据库健康检查

        Returns:
            dict: 健康检查结果
        """
        try:
            # 检查连接
            is_connected = await check_connection()

            # 检查表是否存在
            tables_info = {}
            if is_connected:
                async with get_auth_db() as session:
                    from sqlalchemy import text

                    # 检查各个表是否存在
                    tables = ["users", "user_settings", "sms_verification",
                             "token_blacklist", "user_sessions", "auth_logs"]

                    for table in tables:
                        result = await session.execute(text(
                            f"SELECT count(*) FROM sqlite_master "
                            f"WHERE type='table' AND name='{table}'"
                        ))
                        tables_info[table] = result.scalar() > 0

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "tables": tables_info,
                "timestamp": str(datetime.now(timezone.utc)),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": str(datetime.now(timezone.utc)),
            }

    async def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 备份是否成功
        """
        try:
            import shutil

            # 获取当前数据库文件路径
            current_db_path = AUTH_DATABASE_URL.replace("sqlite+aiosqlite:///", "")

            # 复制数据库文件
            shutil.copy2(current_db_path, backup_path)

            print(f"✅ 数据库备份成功: {backup_path}")
            return True

        except Exception as e:
            print(f"❌ 数据库备份失败: {e}")
            return False

    async def restore_database(self, backup_path: str) -> bool:
        """
        恢复数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            import shutil

            # 获取当前数据库文件路径
            current_db_path = AUTH_DATABASE_URL.replace("sqlite+aiosqlite:///", "")

            # 停止所有连接
            await auth_engine.dispose()

            # 恢复数据库文件
            shutil.copy2(backup_path, current_db_path)

            print(f"✅ 数据库恢复成功: {backup_path}")
            return True

        except Exception as e:
            print(f"❌ 数据库恢复失败: {e}")
            return False


# 创建全局数据库管理器实例
auth_db_manager = AuthDatabaseManager()