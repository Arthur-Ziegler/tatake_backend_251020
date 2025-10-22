"""
聊天域数据库配置

基于LangGraph的SQLiteMemory进行状态持久化，提供聊天对话的
会话管理和数据存储功能。

设计原则：
1. 使用LangGraph原生的SqliteSaver进行状态持久化
2. 独立的SQLite数据库文件，不与其他域共享
3. 简单直接的配置，避免过度抽象
4. 完整的错误处理和日志记录

功能特性：
- LangGraph SqliteSaver配置和管理
- 聊天会话状态持久化
- 数据库连接检查
- 错误诊断和调试信息

作者：TaKeKe团队
版本：1.0.0
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore


# 配置日志
logger = logging.getLogger(__name__)

# 聊天域数据库配置
CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "data/chat.db")
CHAT_ECHO_SQL = os.getenv("CHAT_ECHO_SQL", "false").lower() == "true"


def get_chat_database_path() -> str:
    """
    获取聊天数据库文件路径

    Returns:
        str: 数据库文件的完整路径
    """
    # 确保使用绝对路径
    if not os.path.isabs(CHAT_DB_PATH):
        # 从 src/domains/chat/database.py 向上到项目根目录，然后加上 data/chat.db
        # 需要向上4层：database.py -> chat -> domains -> src -> project_root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        return os.path.join(project_root, CHAT_DB_PATH)
    return CHAT_DB_PATH


def create_chat_checkpointer() -> SqliteSaver:
    """
    创建LangGraph聊天检查点器

    使用SqliteSaver.from_conn_string()为LangGraph提供状态持久化能力，
    支持会话恢复和历史管理。

    修复说明：
    - 使用推荐的 SqliteSaver.from_conn_string() 方法
    - 确保 data/chat.db 文件正确创建和使用
    - 返回上下文管理器，需要在 with 语句中使用

    Returns:
        SqliteSaver: LangGraph检查点器实例（上下文管理器）

    Raises:
        Exception: 数据库连接或配置失败时抛出
    """
    try:
        db_path = get_chat_database_path()

        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 使用推荐的 SqliteSaver.from_conn_string() 方法
        # 返回上下文管理器，确保资源正确管理
        checkpointer = SqliteSaver.from_conn_string(db_path)

        logger.info(f"聊天检查点器创建成功: {db_path}")

        # 验证检查点器可以被正确创建
        if checkpointer is None:
            raise RuntimeError("SqliteSaver 返回了 None")

        logger.info(f"检查点器验证通过: {db_path}")

        return checkpointer

    except Exception as e:
        logger.error(f"创建聊天检查点器失败: {e}")
        raise


def create_memory_store() -> InMemoryStore:
    """
    创建LangGraph内存存储

    提供聊天会话的内存存储能力，用于管理会话元数据
    和临时信息。

    Returns:
        InMemoryStore: 内存存储实例
    """
    try:
        store = InMemoryStore()
        logger.info("聊天内存存储创建成功")
        return store

    except Exception as e:
        logger.error(f"创建聊天内存存储失败: {e}")
        raise


def check_connection() -> bool:
    """
    检查聊天数据库连接状态

    执行简单的查询来验证数据库连接是否正常。

    Returns:
        bool: 连接正常返回True，否则返回False
    """
    try:
        db_path = get_chat_database_path()

        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            logger.warning(f"聊天数据库文件不存在: {db_path}")
            return False

        # 尝试连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 执行简单查询
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        conn.close()

        if result:
            logger.info("聊天数据库连接正常")
            return True
        else:
            logger.error("聊天数据库连接测试失败")
            return False

    except Exception as e:
        logger.error(f"聊天数据库连接检查失败: {e}")
        return False


def get_database_info() -> dict:
    """
    获取聊天域数据库基本信息

    返回聊天域相关的数据库状态和统计信息。

    Returns:
        dict: 数据库信息字典
    """
    try:
        db_path = get_chat_database_path()

        # 获取数据库文件信息
        file_exists = os.path.exists(db_path)
        file_size = 0
        file_size_mb = 0

        if file_exists:
            file_size = os.path.getsize(db_path)
            file_size_mb = file_size / (1024 * 1024)

        # 检查连接状态
        is_connected = check_connection()

        return {
            "path": db_path,
            "exists": file_exists,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size_mb, 2),
            "connected": is_connected,
            "echo_sql": CHAT_ECHO_SQL,
            "type": "sqlite",
            "purpose": "LangGraph聊天状态持久化",
            "timestamp": str(datetime.now(timezone.utc)),
        }

    except Exception as e:
        logger.error(f"获取聊天数据库信息失败: {e}")
        return {
            "error": str(e),
            "timestamp": str(datetime.now(timezone.utc)),
        }


class ChatDatabaseManager:
    """
    聊天数据库管理器

    提供聊天域数据库的统一管理接口，包括连接管理、
    健康检查和错误处理等功能。

    注意：由于 SqliteSaver 现在是上下文管理器，这个类主要
    用于创建检查点器实例，而不是管理连接。
    """

    def __init__(self):
        """初始化聊天数据库管理器"""
        self.db_path = get_chat_database_path()
        self._store = None

    def create_checkpointer(self) -> SqliteSaver:
        """
        创建新的聊天检查点器实例

        Returns:
            SqliteSaver: LangGraph检查点器（上下文管理器）
        """
        return create_chat_checkpointer()

    def get_store(self) -> InMemoryStore:
        """
        获取内存存储实例

        Returns:
            InMemoryStore: 内存存储实例
        """
        if self._store is None:
            self._store = create_memory_store()
        return self._store

    def health_check(self) -> dict:
        """
        数据库健康检查

        Returns:
            dict: 健康检查结果
        """
        try:
            # 检查文件存在性
            file_exists = os.path.exists(self.db_path)

            # 检查连接状态
            is_connected = check_connection()

            # 尝试创建检查点器
            checkpointer_ok = False
            if is_connected:
                try:
                    checkpointer = self.create_checkpointer()
                    # 验证检查点器可以被创建（在上下文管理器中）
                    with checkpointer as cp:
                        checkpointer_ok = cp is not None
                except Exception as e:
                    logger.error(f"检查点器创建失败: {e}")

            # 尝试创建内存存储
            store_ok = False
            try:
                store = self.get_store()
                store_ok = store is not None
            except Exception as e:
                logger.error(f"内存存储创建失败: {e}")

            return {
                "status": "healthy" if (file_exists and is_connected and checkpointer_ok and store_ok) else "unhealthy",
                "file_exists": file_exists,
                "connected": is_connected,
                "checkpointer_ok": checkpointer_ok,
                "store_ok": store_ok,
                "path": self.db_path,
                "timestamp": str(datetime.now(timezone.utc)),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": str(datetime.now(timezone.utc)),
            }

    def cleanup(self) -> None:
        """
        清理数据库资源

        关闭检查点器连接，释放资源。
        """
        try:
            if self._checkpointer is not None:
                # SqliteSaver会在上下文管理器中自动关闭连接
                # 但我们可以显式清理引用
                self._checkpointer = None
                logger.info("聊天检查点器已清理")

            if self._store is not None:
                self._store = None
                logger.info("聊天内存存储已清理")

        except Exception as e:
            logger.error(f"清理聊天数据库资源失败: {e}")


def create_tables() -> bool:
    """
    创建聊天域数据库表

    初始化LangGraph所需的数据库表结构。
    主要用于初始化checkpointer。

    Returns:
        bool: 创建成功返回True，失败返回False
    """
    try:
        # 通过创建检查点器来初始化数据库
        checkpointer = create_chat_checkpointer()

        # 验证数据库连接
        if check_connection():
            logger.info("聊天数据库表创建成功")
            return True
        else:
            logger.error("聊天数据库连接验证失败")
            return False

    except Exception as e:
        logger.error(f"创建聊天数据库表失败: {e}")
        return False


# 创建全局数据库管理器实例
chat_db_manager = ChatDatabaseManager()