"""
简化的聊天数据库管理

基于Context7最佳实践：
1. 自定义数据库管理消息历史
2. 最近10条消息限制
3. 异步操作
4. 错误处理和日志记录
5. 事务安全

作者：TaKeKe团队
版本：1.0.0 - 简化数据库管理
"""

import logging
import sqlite3
import aiosqlite
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from .simple_state import MessageMetadata, SessionInfo

logger = logging.getLogger(__name__)


class ChatDatabaseManager:
    """
    简化的聊天数据库管理器

    职责：
    - 管理消息历史存储
    - 实现最近10条消息限制
    - 提供异步数据库操作
    - 确保事务安全
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库路径（可选）

        Raises:
            Exception: 数据库初始化失败
        """
        try:
            self._db_path = db_path or "data/chat_simple.db"
            self._initialized = False

            # 确保数据目录存在
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"✅ ChatDatabaseManager初始化完成: {self._db_path}")

        except Exception as e:
            logger.error(f"❌ ChatDatabaseManager初始化失败: {e}")
            raise Exception(f"数据库初始化失败: {str(e)}")

    async def _ensure_initialized(self):
        """确保数据库已初始化"""
        if not self._initialized:
            await self._init_database()
            self._initialized = True

    async def _init_database(self) -> None:
        """初始化数据库表"""
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                # 创建会话表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL DEFAULT '新会话',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 创建消息表
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                    )
                """)

                # 创建索引
                await cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp
                    ON messages(session_id, timestamp DESC)
                """)

                await cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_user_created
                    ON sessions(user_id, created_at DESC)
                """)

                await conn.commit()
                logger.info("✅ 数据库表初始化完成")

        except Exception as e:
            logger.error(f"❌ 数据库表初始化失败: {e}")
            raise

    async def save_message(self, session_id: str, role: str, content: str) -> str:
        """
        保存消息到数据库

        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容

        Returns:
            str: 消息ID

        Raises:
            Exception: 保存失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            # 验证参数
            if not session_id or not session_id.strip():
                raise ValueError("会话ID不能为空")
            if not role or not role.strip():
                raise ValueError("角色不能为空")
            if not content or not content.strip():
                raise ValueError("消息内容不能为空")

            if role not in ['user', 'assistant']:
                raise ValueError("角色必须是user或assistant")

            message_metadata = MessageMetadata(session_id, role, content)

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                # 确保会话存在
                await cursor.execute("""
                    INSERT OR IGNORE INTO sessions (session_id, user_id, title)
                    VALUES (?, ?, ?)
                """, (session_id, "unknown", "新会话"))

                # 插入消息
                await cursor.execute("""
                    INSERT INTO messages (message_id, session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    message_metadata.message_id,
                    session_id,
                    role,
                    content,
                    message_metadata.timestamp.isoformat() if message_metadata.timestamp else None
                ))

                # 更新会话最后消息时间
                await cursor.execute("""
                    UPDATE sessions
                    SET last_message_at = ?
                    WHERE session_id = ?
                """, (message_metadata.timestamp.isoformat() if message_metadata.timestamp else None, session_id))

                await conn.commit()

                logger.debug(f"✅ 消息保存成功: {message_metadata.message_id}")
                return message_metadata.message_id

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 消息保存失败: {e}")
            raise Exception(f"消息保存失败: {str(e)}")

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取最近的消息

        Args:
            session_id: 会话ID
            limit: 限制数量（默认10条）
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 消息列表

        Raises:
            Exception: 查询失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not session_id:
                raise ValueError("会话ID不能为空")

            if limit <= 0 or limit > 100:
                limit = 10  # 默认限制

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                await cursor.execute("""
                    SELECT message_id, session_id, role, content, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ? OFFSET ?
                """, (session_id, limit, offset))

                rows = await cursor.fetchall()

                messages = []
                for row in rows:
                    messages.append({
                        "message_id": row[0],
                        "session_id": row[1],
                        "role": row[2],
                        "content": row[3],
                        "timestamp": row[4]
                    })

                logger.debug(f"✅ 获取消息成功: {len(messages)}条")
                return messages

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 获取消息失败: {e}")
            raise Exception(f"获取消息失败: {str(e)}")

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            title: 会话标题

        Returns:
            Dict[str, Any]: 会话信息

        Raises:
            Exception: 创建失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not session_id or not user_id:
                raise ValueError("会话ID和用户ID不能为空")

            session_info = SessionInfo(session_id, user_id, title)

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                await cursor.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_id, title, created_at, last_message_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_info.session_id,
                    session_info.user_id,
                    session_info.title,
                    session_info.created_at.isoformat() if session_info.created_at else None,
                    session_info.last_message_at.isoformat() if session_info.last_message_at else None
                ))

                await conn.commit()

                result = session_info.to_dict()
                logger.debug(f"✅ 会话创建成功: {session_id}")
                return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 会话创建失败: {e}")
            raise Exception(f"会话创建失败: {str(e)}")

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict[str, Any]]: 会话信息或None

        Raises:
            Exception: 查询失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not session_id:
                raise ValueError("会话ID不能为空")

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                await cursor.execute("""
                    SELECT session_id, user_id, title, created_at, last_message_at
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))

                row = await cursor.fetchone()
                if not row:
                    return None

                session_info = {
                    "session_id": row[0],
                    "user_id": row[1],
                    "title": row[2],
                    "created_at": row[3],
                    "last_message_at": row[4]
                }

                logger.debug(f"✅ 获取会话信息成功: {session_id}")
                return session_info

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: {e}")
            raise Exception(f"获取会话信息失败: {str(e)}")

    async def clear_session_messages(self, session_id: str) -> bool:
        """
        清除会话消息

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功

        Raises:
            Exception: 清除失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not session_id:
                raise ValueError("会话ID不能为空")

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                # 删除消息
                await cursor.execute("""
                    DELETE FROM messages WHERE session_id = ?
                """, (session_id,))

                # 更新会话最后消息时间
                await cursor.execute("""
                    UPDATE sessions
                    SET last_message_at = created_at
                    WHERE session_id = ?
                """, (session_id,))

                await conn.commit()

                logger.debug(f"✅ 会话消息清除成功: {session_id}")
                return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 清除会话消息失败: {e}")
            return False

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 统计信息

        Raises:
            Exception: 查询失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not session_id:
                raise ValueError("会话ID不能为空")

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                # 获取消息数量
                await cursor.execute("""
                    SELECT COUNT(*) FROM messages WHERE session_id = ?
                """, (session_id,))
                message_count = (await cursor.fetchone())[0]

                # 获取会话信息
                await cursor.execute("""
                    SELECT created_at, last_message_at
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))
                session_row = await cursor.fetchone()

                stats = {
                    "message_count": message_count,
                    "created_at": session_row[0] if session_row else None,
                    "last_message_at": session_row[1] if session_row else None
                }

                logger.debug(f"✅ 获取会话统计成功: {session_id}")
                return stats

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 获取会话统计失败: {e}")
            raise Exception(f"获取会话统计失败: {str(e)}")

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户会话列表

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 会话列表

        Raises:
            Exception: 查询失败
        """
        try:
            # 确保数据库已初始化
            await self._ensure_initialized()
            if not user_id:
                raise ValueError("用户ID不能为空")

            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.cursor()

                await cursor.execute("""
                    SELECT session_id, user_id, title, created_at, last_message_at
                    FROM sessions
                    WHERE user_id = ?
                    ORDER BY last_message_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))

                rows = await cursor.fetchall()

                sessions = []
                for row in rows:
                    sessions.append({
                        "session_id": row[0],
                        "user_id": row[1],
                        "title": row[2],
                        "created_at": row[3],
                        "last_message_at": row[4]
                    })

                logger.debug(f"✅ 获取用户会话列表成功: {len(sessions)}个会话")
                return sessions

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"❌ 获取用户会话列表失败: {e}")
            raise Exception(f"获取用户会话列表失败: {str(e)}")