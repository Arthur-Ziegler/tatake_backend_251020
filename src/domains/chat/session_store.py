"""
聊天会话元数据存储

专门存储LangGraph不支持的会话元数据，与LangGraph完全分离
避免任何类型冲突和兼容性问题

设计原则：
1. 完全分离：LangGraph只处理消息，这里处理所有元数据
2. 事务安全：所有操作都在事务中执行
3. 高性能：使用连接池和索引优化
4. 简洁设计：遵循KISS原则，控制复杂度

作者：TaKeKe团队
版本：1.0.0 - 彻底分离方案实现
"""

import sqlite3
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ChatSessionStore:
    """
    聊天会话元数据存储管理器

    功能职责：
    - 管理会话基本信息（id, user_id, title, created_at等）
    - 提供thread_id与LangGraph关联
    - 维护会话状态和统计信息
    - 提供高性能的查询接口

    设计约束：
    - 文件行数 <= 300行
    - 函数复杂度 <= 8
    - 所有函数 <= 20行
    """

    def __init__(self, db_path: str):
        """
        初始化会话存储

        Args:
            db_path: SQLite数据库路径

        Raises:
            sqlite3.Error: 数据库初始化失败
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                self._create_tables(cursor)
                conn.commit()
            logger.info(f"✅ 会话元数据表初始化完成: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise

    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        """创建数据库表"""
        # 会话元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT DEFAULT '新会话',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                metadata TEXT DEFAULT '{}',
                thread_id TEXT NOT NULL
            )
        ''')

        # 创建索引优化查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON chat_sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_thread_id ON chat_sessions(thread_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON chat_sessions(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_sessions ON chat_sessions(user_id, is_active)')

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器

        Yields:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 启用字典式访问
        try:
            yield conn
        finally:
            conn.close()

    def create_session(self, user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新的聊天会话

        Args:
            user_id: 用户ID
            title: 会话标题（可选）

        Returns:
            Dict[str, Any]: 会话信息字典

        Raises:
            sqlite3.Error: 数据库操作失败
        """
        session_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        sql = '''
            INSERT INTO chat_sessions
            (session_id, user_id, title, thread_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        '''

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (session_id, user_id, title or '新会话', thread_id, now, now))
            conn.commit()

        session_info = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or '新会话',
            "thread_id": thread_id,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "is_active": 1  # SQLite中存储为整数
        }

        logger.info(f"✅ 会话创建成功: session_id={session_id}")
        return session_info

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict]: 会话信息，如果不存在返回None
        """
        sql = 'SELECT * FROM chat_sessions WHERE session_id = ?'

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_by_thread_id(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        通过thread_id获取会话信息

        Args:
            thread_id: LangGraph thread_id

        Returns:
            Optional[Dict]: 会话信息，如果不存在返回None
        """
        sql = 'SELECT * FROM chat_sessions WHERE thread_id = ?'

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (thread_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_session(self, session_id: str, **updates) -> bool:
        """
        更新会话信息

        Args:
            session_id: 会话ID
            **updates: 要更新的字段

        Returns:
            bool: 是否更新成功

        Raises:
            ValueError: 当没有提供更新字段时
        """
        if not updates:
            raise ValueError("必须提供至少一个更新字段")

        # 自动更新updated_at
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [session_id]

        sql = f'UPDATE chat_sessions SET {set_clause} WHERE session_id = ?'

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()

            success = cursor.rowcount > 0
            if success:
                logger.debug(f"✅ 会话更新成功: session_id={session_id}")
            else:
                logger.warning(f"⚠️ 会话更新失败: session_id={session_id} 不存在")
            return success

    def increment_message_count(self, session_id: str) -> bool:
        """
        增加会话消息计数

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否更新成功
        """
        sql = '''
            UPDATE chat_sessions
            SET message_count = message_count + 1, updated_at = ?
            WHERE session_id = ?
        '''

        now = datetime.now(timezone.utc).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (now, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_user_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        列出用户的活跃会话列表

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[Dict]: 会话列表，按updated_at降序排列
        """
        sql = '''
            SELECT * FROM chat_sessions
            WHERE user_id = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        '''

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id, limit, offset))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """
        软删除会话（标记为非活跃）

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        return self.update_session(session_id, is_active=False)

    def get_thread_id(self, session_id: str) -> Optional[str]:
        """
        获取会话对应的thread_id

        Args:
            session_id: 会话ID

        Returns:
            Optional[str]: thread_id，如果会话不存在返回None
        """
        session = self.get_session(session_id)
        return session.get('thread_id') if session else None

    def cleanup_inactive_sessions(self, days: int = 30) -> int:
        """
        清理不活跃的会话

        Args:
            days: 清理多少天前的会话

        Returns:
            int: 清理的会话数量
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        sql = '''
            DELETE FROM chat_sessions
            WHERE is_active = 0 AND updated_at < ?
        '''

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (cutoff_date.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

        logger.info(f"🗑️ 清理了 {deleted_count} 个不活跃会话")
        return deleted_count


# 全局实例管理
_session_store_instance = None


def get_session_store(db_path: Optional[str] = None) -> ChatSessionStore:
    """
    获取会话存储实例（单例模式）

    Args:
        db_path: 数据库路径（可选），默认使用chat数据库路径

    Returns:
        ChatSessionStore: 会话存储实例
    """
    global _session_store_instance

    if _session_store_instance is None:
        if db_path is None:
            from .database import get_chat_database_path
            db_path = get_chat_database_path()

        _session_store_instance = ChatSessionStore(db_path)

    return _session_store_instance