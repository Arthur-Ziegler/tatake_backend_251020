"""
简化认证数据库连接管理

根据设计文档，认证数据库大幅简化：
1. 只保留2张表：auth（核心认证）和auth_audit_logs（审计）
2. 删除SMS、会话管理等复杂功能
3. 专注于微信登录和JWT令牌管理
4. 采用同步数据库操作，保持代码简洁

数据库配置:
- 数据库文件: tatake_auth.db
- 连接池: 使用同步SQLite连接
- 表结构: 自动创建简化的认证表

使用方法:
```python
from src.domains.auth.database import get_auth_db, create_tables

# 获取数据库会话
with get_auth_db() as session:
    # 执行数据库操作
    pass

# 创建所有表
create_tables()
```

环境变量:
- AUTH_DATABASE_URL: 认证数据库连接URL
- AUTH_ECHO_SQL: 是否输出SQL语句（调试用）
"""

import os
from datetime import datetime, timezone
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel


# 数据库配置
AUTH_DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "sqlite:///./data/auth.db"
)

# 是否在控制台输出SQL语句（调试用）
AUTH_ECHO_SQL = os.getenv("AUTH_ECHO_SQL", "false").lower() == "true"

# 创建同步引擎
auth_engine = create_engine(
    AUTH_DATABASE_URL,
    echo=AUTH_ECHO_SQL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    }
)

# 创建会话工厂
AuthSessionLocal = sessionmaker(
    bind=auth_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


@contextmanager
def get_auth_db():
    """
    获取认证数据库会话

    这是一个同步上下文管理器，用于获取认证数据库的会话。
    使用with语句确保会话正确关闭。

    Returns:
        Session: 数据库会话

    Example:
        ```python
        with get_auth_db() as session:
            user = session.get(User, user_id)
        ```
    """
    session = AuthSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """
    创建简化认证数据库中的表

    根据设计文档，只创建2张表：
    - auth: 核心认证表（7个字段）
    - auth_audit_logs: 审计日志表（保留）

    注意事项:
    - 使用checkfirst=True避免重复创建
    - 仅在开发环境使用，生产环境应使用数据库迁移

    Raises:
        Exception: 数据库连接或表创建失败时抛出
    """
    try:
        # 导入模型
        from src.domains.auth.models import Auth, AuthLog, SMSVerification

        # 创建表
        SQLModel.metadata.create_all(
            auth_engine,
            checkfirst=True
        )

        print("✅ 认证数据库表创建成功（auth + auth_audit_logs + sms_verification）")

    except Exception as e:
        print(f"❌ 认证数据库表创建失败: {e}")
        raise


def drop_tables() -> None:
    """
    删除认证数据库中的所有表

    ⚠️ 警告: 此操作会删除所有数据，仅用于测试环境

    Raises:
        Exception: 数据库连接或表删除失败时抛出
    """
    try:
        # 导入模型
        from src.domains.auth.models import Auth, AuthLog, SMSVerification

        # 删除所有表
        SQLModel.metadata.drop_all(
            auth_engine,
            checkfirst=True
        )

        print("✅ 认证数据库表删除成功")

    except Exception as e:
        print(f"❌ 认证数据库表删除失败: {e}")
        raise


def check_connection() -> bool:
    """
    检查认证数据库连接是否正常

    Returns:
        bool: 连接是否正常

    Example:
        ```python
        if check_connection():
            print("数据库连接正常")
        ```
    """
    try:
        with auth_engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ 数据库连接检查失败: {e}")
        return False


def get_database_info() -> dict:
    """
    获取认证数据库基本信息

    Returns:
        dict: 数据库信息字典

    Example:
        ```python
        info = get_database_info()
        print(f"数据库URL: {info['url']}")
        print(f"表数量: {info['table_count']}")
        ```
    """
    try:
        with get_auth_db() as session:
            from sqlalchemy import text

            # 获取表数量
            result = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ))
            table_count = result.scalar()

            # 获取数据库文件大小
            db_path = AUTH_DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                file_size_mb = file_size / (1024 * 1024)
            else:
                file_size_mb = 0

            return {
                "url": AUTH_DATABASE_URL,
                "echo_sql": AUTH_ECHO_SQL,
                "table_count": table_count,
                "file_size_mb": round(file_size_mb, 2),
                "dialect": str(auth_engine.dialect),
                "driver": str(auth_engine.driver),
                "simplified": True,  # 标识这是简化版本
            }

    except Exception as e:
        print(f"❌ 获取数据库信息失败: {e}")
        return {}


class AuthDatabaseManager:
    """
    简化认证数据库管理器

    专注于核心功能，移除复杂的备份恢复等功能。
    """

    def __init__(self):
        self.engine = auth_engine
        self.session_factory = AuthSessionLocal

    def health_check(self) -> dict:
        """
        数据库健康检查

        Returns:
            dict: 健康检查结果
        """
        try:
            # 检查连接
            is_connected = check_connection()

            # 检查简化后的表是否存在
            tables_info = {}
            if is_connected:
                with get_auth_db() as session:
                    from sqlalchemy import text

                    # 检查简化后的表
                    tables = ["auth", "auth_audit_logs"]

                    for table in tables:
                        result = session.execute(text(
                            f"SELECT count(*) FROM sqlite_master "
                            f"WHERE type='table' AND name='{table}'"
                        ))
                        tables_info[table] = result.scalar() > 0

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "tables": tables_info,
                "simplified": True,
                "timestamp": str(datetime.now(timezone.utc)),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": str(datetime.now(timezone.utc)),
            }

    def verify_simplified_structure(self) -> dict:
        """
        验证数据库结构是否符合简化设计

        Returns:
            dict: 验证结果
        """
        try:
            with get_auth_db() as session:
                from sqlalchemy import text

                # 验证auth表结构
                result = session.execute(text("PRAGMA table_info(auth)"))
                auth_columns = [row[1] for row in result.fetchall()]

                expected_auth_columns = {
                    'id', 'wechat_openid', 'phone', 'is_guest', 'created_at',
                    'updated_at', 'last_login_at', 'jwt_version'
                }

                auth_valid = set(auth_columns) == expected_auth_columns

                # 验证auth_audit_logs表结构
                result = session.execute(text("PRAGMA table_info(auth_audit_logs)"))
                log_columns = [row[1] for row in result.fetchall()]

                # 检查必要的日志字段
                required_log_fields = {'id', 'user_id', 'action', 'result', 'created_at'}
                log_valid = required_log_fields.issubset(set(log_columns))

                # 检查是否删除了旧表
                old_tables = [
                    'auth_users', 'auth_sms_verification', 'auth_token_blacklist',
                    'auth_user_sessions', 'auth_user_settings'
                ]

                old_tables_exist = []
                for table in old_tables:
                    result = session.execute(text(
                        f"SELECT count(*) FROM sqlite_master "
                        f"WHERE type='table' AND name='{table}'"
                    ))
                    exists = result.scalar() > 0
                    old_tables_exist.append(exists)

                old_tables_cleaned = not any(old_tables_exist)

                return {
                    "auth_table_valid": auth_valid,
                    "auth_log_table_valid": log_valid,
                    "old_tables_cleaned": old_tables_cleaned,
                    "overall_valid": auth_valid and log_valid and old_tables_cleaned,
                    "timestamp": str(datetime.now(timezone.utc)),
                }

        except Exception as e:
            return {
                "error": str(e),
                "overall_valid": False,
                "timestamp": str(datetime.now(timezone.utc)),
            }


# 创建全局数据库管理器实例
auth_db_manager = AuthDatabaseManager()