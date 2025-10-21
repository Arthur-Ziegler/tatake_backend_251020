"""
异步对话Repository实现

提供对话相关的异步数据访问层操作，封装对话业务逻辑查询。
继承自AsyncBaseRepository，专注于对话特有的业务场景。

功能特性：
1. 异步对话记录查询（按用户、会话、时间范围查询）
2. 异步对话会话管理（创建、更新、删除对话会话）
3. 异步对话消息管理（添加、查询、更新消息）
4. 异步对话统计和分析（对话次数、消息数量等）
5. 异步业务逻辑封装（会话状态管理、消息验证等）

设计原则：
1. 单一责任：专注于对话相关的数据访问
2. 异步优先：所有数据库操作都是异步的
3. 查询封装：复杂业务查询封装在Repository方法中
4. 异常统一：使用统一的异常处理机制
5. 类型安全：强类型参数和返回值
6. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建异步对话Repository
    >>> chat_repo = AsyncChatRepository(async_session)
    >>>
    >>> # 异步查找用户的所有对话会话
    >>> sessions = await chat_repo.find_sessions_by_user("user123")
    >>>
    >>> # 异步创建新对话会话
    >>> new_session = await chat_repo.create_session("user123", "AI助手")
    >>>
    >>> # 异步添加消息
    >>> message = await chat_repo.add_message("session123", "user", "你好")
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError

# 导入异步基础Repository和异常类
from src.repositories.async_base import (
    AsyncBaseRepository,
    AsyncRepositoryError,
    AsyncRepositoryValidationError,
    AsyncRepositoryNotFoundError
)
from src.models.chat import ChatSession, ChatMessage
from src.models.enums import MessageRole, SessionStatus


class AsyncChatRepository(AsyncBaseRepository[ChatSession]):
    """
    异步对话Repository类

    提供对话相关的异步数据库操作，封装对话业务逻辑查询。
    继承自AsyncBaseRepository，专注于对话特有的业务场景。

    Attributes:
        session: SQLAlchemy异步会话对象
        model: ChatSession模型类
    """

    def __init__(self, session: AsyncSession):
        """
        初始化异步对话Repository

        Args:
            session: SQLAlchemy异步会话对象
        """
        super().__init__(session, ChatSession)

    async def find_sessions_by_user(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: Optional[int] = None
    ) -> List[ChatSession]:
        """
        查找用户的所有对话会话

        Args:
            user_id: 用户ID
            status: 会话状态过滤
            limit: 结果数量限制

        Returns:
            对话会话列表

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 构建查询
            statement = select(ChatSession).where(ChatSession.user_id == user_id)

            # 状态过滤
            if status:
                statement = statement.where(ChatSession.status == status)

            # 按最后消息时间倒序排列
            statement = statement.order_by(desc(ChatSession.last_message_at))

            # 限制结果数量
            if limit:
                statement = statement.limit(limit)

            # 执行查询
            result = await self.session.exec(statement)
            sessions = list(result.all())

            return sessions

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询用户对话会话失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询用户对话会话时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> ChatSession:
        """
        创建新的对话会话

        Args:
            user_id: 用户ID
            title: 会话标题
            system_prompt: 系统提示词

        Returns:
            创建的对话会话对象

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            now = datetime.now(timezone.utc)
            session_data = {
                "user_id": user_id,
                "title": title or f"对话 {now.strftime('%Y-%m-%d %H:%M')}",
                "status": SessionStatus.ACTIVE,
                "system_prompt": system_prompt,
                "created_at": now,
                "updated_at": now,
                "last_message_at": now
            }

            return await self.create(session_data)

        except AsyncRepositoryValidationError:
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"创建对话会话失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"创建对话会话时发生未知错误: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        向对话会话添加消息

        Args:
            session_id: 对话会话ID
            role: 消息角色
            content: 消息内容
            metadata: 消息元数据

        Returns:
            创建的消息对象

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryNotFoundError: 对话会话不存在时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")
            if not role:
                raise AsyncRepositoryValidationError("消息角色不能为空")
            if not content or not content.strip():
                raise AsyncRepositoryValidationError("消息内容不能为空")

            # 检查会话是否存在
            session = await self.get_by_id(session_id)
            if not session:
                raise AsyncRepositoryNotFoundError(f"对话会话不存在: {session_id}")

            # 创建消息
            now = datetime.now(timezone.utc)
            message_data = {
                "session_id": session_id,
                "role": role,
                "content": content.strip(),
                "metadata": metadata or {},
                "created_at": now
            }

            # 使用SQLModel直接创建消息
            message = ChatMessage(**message_data)
            self.session.add(message)
            await self.session.commit()
            await self.session.refresh(message)

            # 更新会话的最后消息时间
            session_update_data = {
                "last_message_at": now,
                "updated_at": now
            }

            for field, value in session_update_data.items():
                setattr(session, field, value)

            self.session.add(session)
            await self.session.commit()

            return message

        except (AsyncRepositoryValidationError, AsyncRepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"添加消息失败: {str(e)}",
                operation="create",
                model_name="ChatMessage"
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"添加消息时发生未知错误: {str(e)}",
                operation="create",
                model_name="ChatMessage"
            )

    async def get_session_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        获取对话会话的消息列表

        Args:
            session_id: 对话会话ID
            limit: 结果数量限制

        Returns:
            消息列表（按时间正序排列）

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 构建查询
            statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
            statement = statement.order_by(asc(ChatMessage.created_at))

            # 限制结果数量
            if limit:
                statement = statement.limit(limit)

            # 执行查询
            result = await self.session.exec(statement)
            messages = list(result.all())

            return messages

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取会话消息失败: {str(e)}",
                operation="read",
                model_name="ChatMessage"
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取会话消息时发生未知错误: {str(e)}",
                operation="read",
                model_name="ChatMessage"
            )

    async def close_session(self, session_id: str) -> Optional[ChatSession]:
        """
        关闭对话会话

        Args:
            session_id: 对话会话ID

        Returns:
            关闭后的会话对象，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 查找会话
            session = await self.get_by_id(session_id)
            if not session:
                return None

            if session.status == SessionStatus.CLOSED:
                return session  # 已经关闭

            now = datetime.now(timezone.utc)
            update_data = {
                "status": SessionStatus.CLOSED,
                "closed_at": now,
                "updated_at": now
            }

            return await self.update(session_id, update_data)

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"关闭会话失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"关闭会话时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def delete_session(self, session_id: str) -> bool:
        """
        删除对话会话（级联删除消息）

        Args:
            session_id: 对话会话ID

        Returns:
            删除成功返回True，会话不存在返回False

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not session_id:
                raise AsyncRepositoryValidationError("会话ID不能为空")

            # 检查会话是否存在
            session = await self.get_by_id(session_id)
            if not session:
                return False

            # 删除相关消息
            delete_messages_stmt = select(ChatMessage).where(ChatMessage.session_id == session_id)
            messages_result = await self.session.exec(delete_messages_stmt)
            messages = list(messages_result.all())

            for message in messages:
                await self.session.delete(message)

            # 删除会话
            await self.session.delete(session)
            await self.session.commit()

            return True

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"删除会话失败: {str(e)}",
                operation="delete",
                model_name=self.model_name
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"删除会话时发生未知错误: {str(e)}",
                operation="delete",
                model_name=self.model_name
            )

    async def get_chat_statistics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取用户对话统计信息

        Args:
            user_id: 用户ID
            start_date: 统计开始日期
            end_date: 统计结束日期

        Returns:
            包含对话统计信息的字典

        Raises:
            AsyncRepositoryValidationError: 参数验证失败时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not user_id:
                raise AsyncRepositoryValidationError("用户ID不能为空")

            # 基础过滤条件
            session_filter = ChatSession.user_id == user_id

            # 日期范围过滤
            if start_date:
                session_filter = and_(session_filter, ChatSession.created_at >= start_date)
            if end_date:
                session_filter = and_(session_filter, ChatSession.created_at <= end_date)

            # 总会话数
            total_sessions_result = await self.session.exec(
                select(func.count()).select_from(ChatSession).where(session_filter)
            )
            total_sessions = total_sessions_result.scalar() or 0

            # 按状态统计会话
            session_status_result = await self.session.exec(
                select(ChatSession.status, func.count()).select_from(ChatSession)
                .where(session_filter).group_by(ChatSession.status)
            )
            session_status_counts = dict(session_status_result.all())

            # 获取相关会话ID
            sessions_result = await self.session.exec(
                select(ChatSession.id).where(session_filter)
            )
            session_ids = [row[0] for row in sessions_result.all()]

            # 统计消息数量
            if session_ids:
                message_filter = ChatMessage.session_id.in_(session_ids)

                total_messages_result = await self.session.exec(
                    select(func.count()).select_from(ChatMessage).where(message_filter)
                )
                total_messages = total_messages_result.scalar() or 0

                # 按角色统计消息
                message_role_result = await self.session.exec(
                    select(ChatMessage.role, func.count()).select_from(ChatMessage)
                    .where(message_filter).group_by(ChatMessage.role)
                )
                message_role_counts = dict(message_role_result.all())
            else:
                total_messages = 0
                message_role_counts = {}

            # 今日对话统计
            today = datetime.now(timezone.utc).date()
            today_filter = and_(session_filter, func.date(ChatSession.created_at) == today)

            today_sessions_result = await self.session.exec(
                select(func.count()).select_from(ChatSession).where(today_filter)
            )
            today_sessions = today_sessions_result.scalar() or 0

            # 本周对话统计
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_filter = and_(session_filter, ChatSession.created_at >= week_ago)

            week_sessions_result = await self.session.exec(
                select(func.count()).select_from(ChatSession).where(week_filter)
            )
            week_sessions = week_sessions_result.scalar() or 0

            return {
                "total_sessions": total_sessions,
                "sessions_by_status": session_status_counts,
                "total_messages": total_messages,
                "messages_by_role": message_role_counts,
                "average_messages_per_session": (
                    total_messages / total_sessions if total_sessions > 0 else 0
                ),
                "today_sessions": today_sessions,
                "week_sessions": week_sessions
            }

        except AsyncRepositoryValidationError:
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"获取对话统计失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"获取对话统计时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def __repr__(self) -> str:
        """
        返回Repository的字符串表示

        Returns:
            Repository的描述信息
        """
        return f"{self.__class__.__name__}(model={self.model_name})"


# 导出相关类
__all__ = [
    "AsyncChatRepository"
]