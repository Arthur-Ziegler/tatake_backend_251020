"""
聊天数据仓储层

该模块提供聊天相关的数据访问操作，包括会话管理和消息存储。
采用Repository模式，封装数据访问逻辑，提供统一的数据操作接口。

核心组件：
- ChatRepository: 聊天数据仓储主类
- ChatQuery: 聊天查询工具类

设计原则：
- 仓储模式：抽象数据访问逻辑
- 异步操作：所有数据库操作都是异步的
- 错误处理：统一的异常处理和错误传播
- 性能优化：合理的查询优化和分页支持
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from src.models.chat import ChatSession, ChatMessage
from src.models.user import User
from src.models.enums import ChatMode, MessageRole, SessionStatus
from src.services.exceptions import (
    ResourceNotFoundException,
    BusinessException,
    ValidationException
)


class ChatRepository(BaseRepository):
    """
    聊天数据仓储类

    提供聊天会话和消息的完整数据访问功能，包括：
    - 会话的增删改查操作
    - 消息的存储和检索
    - 用户会话管理
    - 统计信息查询

    Attributes:
        _session: 数据库会话
    """

    def __init__(self, session: AsyncSession):
        """
        初始化聊天仓储

        Args:
            session: 数据库会话
        """
        # ChatRepository可以管理多个模型，不指定单一模型
        # 暂时使用ChatSession作为默认模型
        super().__init__(session, ChatSession)

    # ==================== 会话管理 ====================

    async def create_session(
        self,
        user_id: UUID,
        title: str,
        chat_mode: ChatMode,
        status: SessionStatus = SessionStatus.ACTIVE,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """
        创建新的聊天会话

        Args:
            user_id: 用户ID
            title: 会话标题
            chat_mode: 聊天模式
            status: 会话状态
            metadata: 会话元数据

        Returns:
            创建的会话对象

        Raises:
            ValidationException: 参数验证失败
            BusinessException: 会话创建失败
        """
        try:
            # 参数验证
            if not user_id:
                raise ValidationException(
                    message="用户ID不能为空",
                    field="user_id",
                    value=user_id
                )
            if not title or not title.strip():
                raise ValidationException(
                    message="会话标题不能为空",
                    field="title",
                    value=title
                )
            if len(title) > 200:
                raise ValidationException(
                    message="会话标题长度不能超过200个字符",
                    field="title",
                    value=len(title)
                )

            # 创建会话对象
            session = ChatSession(
                user_id=user_id,
                title=title.strip(),
                chat_mode=chat_mode,
                status=status,
                session_metadata=session_metadata or {}
            )

            # 保存到数据库
            self._session.add(session)
            await self._session.flush()
            await self._session.refresh(session)

            self._logger.info(
                f"聊天会话创建成功",
                extra={
                    "session_id": str(session.id),
                    "user_id": str(user_id),
                    "title": title,
                    "chat_mode": chat_mode.value
                }
            )

            return session

        except ValidationException:
            raise
        except Exception as e:
            self._logger.error(
                f"聊天会话创建失败: {str(e)}",
                extra={
                    "user_id": str(user_id),
                    "title": title,
                    "chat_mode": chat_mode.value
                }
            )
            raise BusinessException(
                error_code="CHAT_SESSION_CREATION_FAILED",
                message=f"聊天会话创建失败: {str(e)}",
                details={
                    "user_id": str(user_id),
                    "title": title,
                    "chat_mode": chat_mode.value
                }
            )

    async def get_session_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        """
        根据ID获取聊天会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象或None
        """
        try:
            if not session_id:
                return None

            statement = (
                select(ChatSession)
                .options(selectinload(ChatSession.user))
                .where(ChatSession.id == session_id)
            )

            result = await self._session.execute(statement)
            return result.scalar_one_or_none()

        except Exception as e:
            self._logger.error(
                f"获取聊天会话失败: {str(e)}",
                extra={"session_id": str(session_id)}
            )
            return None

    async def get_user_sessions(
        self,
        user_id: UUID,
        status: Optional[SessionStatus] = None,
        chat_mode: Optional[ChatMode] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ChatSession]:
        """
        获取用户的聊天会话列表

        Args:
            user_id: 用户ID
            status: 状态过滤
            chat_mode: 聊天模式过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话列表

        Raises:
            ValidationException: 参数验证失败
        """
        try:
            # 参数验证
            if not user_id:
                raise ValidationException(
                    message="用户ID不能为空",
                    field="user_id",
                    value=user_id
                )
            if limit <= 0 or limit > 100:
                raise ValidationException(
                    message="返回数量限制必须在1-100之间",
                    field="limit",
                    value=limit
                )
            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    field="offset",
                    value=offset
                )

            # 构建查询
            statement = (
                select(ChatSession)
                .options(selectinload(ChatSession.user))
                .where(ChatSession.user_id == user_id)
            )

            # 添加状态过滤
            if status:
                statement = statement.where(ChatSession.status == status)

            # 添加聊天模式过滤
            if chat_mode:
                statement = statement.where(ChatSession.chat_mode == chat_mode)

            # 排序和分页
            statement = (
                statement
                .order_by(desc(ChatSession.last_activity_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(statement)
            return result.scalars().all()

        except ValidationException:
            raise
        except Exception as e:
            self._logger.error(
                f"获取用户会话列表失败: {str(e)}",
                extra={
                    "user_id": str(user_id),
                    "status": status.value if status else None,
                    "limit": limit,
                    "offset": offset
                }
            )
            raise BusinessException(
                error_code="USER_SESSIONS_FETCH_FAILED",
                message=f"获取用户会话列表失败: {str(e)}",
                details={
                    "user_id": str(user_id),
                    "status": status.value if status else None
                }
            )

    async def update_session(
        self,
        session_id: UUID,
        title: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatSession]:
        """
        更新聊天会话

        Args:
            session_id: 会话ID
            title: 新标题
            status: 新状态
            metadata: 新元数据

        Returns:
            更新后的会话对象或None

        Raises:
            ResourceNotFoundException: 会话不存在
            BusinessException: 更新失败
        """
        try:
            # 获取会话
            session = await self.get_session_by_id(session_id)
            if not session:
                raise ResourceNotFoundException(
                    resource_type="ChatSession",
                    resource_id=str(session_id)
                )

            # 更新字段
            if title is not None:
                if not title or not title.strip():
                    raise ValidationException(
                        message="会话标题不能为空",
                        field="title",
                        value=title
                    )
                if len(title) > 200:
                    raise ValidationException(
                        message="会话标题长度不能超过200个字符",
                        field="title",
                        value=len(title)
                    )
                session.title = title.strip()

            if status is not None:
                session.update_status(status)

            if session_metadata is not None:
                session.session_metadata.update(session_metadata)
                session.updated_at = datetime.now(timezone.utc)

            # 保存更改
            await self._session.flush()
            await self._session.refresh(session)

            self._logger.info(
                f"聊天会话更新成功",
                extra={
                    "session_id": str(session_id),
                    "title": session.title,
                    "status": session.status.value
                }
            )

            return session

        except (ValidationException, ResourceNotFoundException):
            raise
        except Exception as e:
            self._logger.error(
                f"聊天会话更新失败: {str(e)}",
                extra={"session_id": str(session_id)}
            )
            raise BusinessException(
                error_code="CHAT_SESSION_UPDATE_FAILED",
                message=f"聊天会话更新失败: {str(e)}",
                details={"session_id": str(session_id)}
            )

    async def update_session_activity(self, session_id: UUID, last_activity_at: datetime) -> bool:
        """
        更新会话活动时间

        Args:
            session_id: 会话ID
            last_activity_at: 最后活动时间

        Returns:
            是否更新成功
        """
        try:
            if not session_id:
                return False

            # 执行更新
            statement = (
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .with_for_update()
            )
            result = await self._session.execute(statement)
            session = result.scalar_one_or_none()

            if session:
                session.last_activity_at = last_activity_at
                session.updated_at = datetime.now(timezone.utc)
                await self._session.flush()
                return True

            return False

        except Exception as e:
            self._logger.error(
                f"更新会话活动时间失败: {str(e)}",
                extra={"session_id": str(session_id)}
            )
            return False

    async def delete_session(self, session_id: UUID) -> bool:
        """
        删除聊天会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功

        Raises:
            ResourceNotFoundException: 会话不存在
            BusinessException: 删除失败
        """
        try:
            # 获取会话
            session = await self.get_session_by_id(session_id)
            if not session:
                raise ResourceNotFoundException(
                    resource_type="ChatSession",
                    resource_id=str(session_id)
                )

            # 删除会话（级联删除消息）
            await self._session.delete(session)
            await self._session.flush()

            self._logger.info(
                f"聊天会话删除成功",
                extra={"session_id": str(session_id)}
            )

            return True

        except ResourceNotFoundException:
            raise
        except Exception as e:
            self._logger.error(
                f"聊天会话删除失败: {str(e)}",
                extra={"session_id": str(session_id)}
            )
            raise BusinessException(
                error_code="CHAT_SESSION_DELETION_FAILED",
                message=f"聊天会话删除失败: {str(e)}",
                details={"session_id": str(session_id)}
            )

    async def count_user_sessions(
        self,
        user_id: UUID,
        status: Optional[SessionStatus] = None
    ) -> int:
        """
        统计用户会话数量

        Args:
            user_id: 用户ID
            status: 状态过滤

        Returns:
            会话数量
        """
        try:
            if not user_id:
                return 0

            statement = select(func.count(ChatSession.id)).where(ChatSession.user_id == user_id)

            if status:
                statement = statement.where(ChatSession.status == status)

            result = await self._session.execute(statement)
            return result.scalar() or 0

        except Exception as e:
            self._logger.error(
                f"统计用户会话数量失败: {str(e)}",
                extra={"user_id": str(user_id)}
            )
            return 0

    # ==================== 消息管理 ====================

    async def create_message(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        message_metadata: Optional[Dict[str, Any]] = None,
        token_count: Optional[int] = None,
        processing_time_ms: Optional[int] = None
    ) -> ChatMessage:
        """
        创建聊天消息

        Args:
            session_id: 会话ID
            role: 消息角色
            content: 消息内容
            metadata: 消息元数据
            token_count: Token数量
            processing_time_ms: 处理时间

        Returns:
            创建的消息对象

        Raises:
            ValidationException: 参数验证失败
            BusinessException: 消息创建失败
        """
        try:
            # 参数验证
            if not session_id:
                raise ValidationException(
                    message="会话ID不能为空",
                    field="session_id",
                    value=session_id
                )
            if not content or not content.strip():
                raise ValidationException(
                    message="消息内容不能为空",
                    field="content",
                    value=content
                )
            if len(content) > 10000:
                raise ValidationException(
                    message="消息内容长度不能超过10000个字符",
                    field="content",
                    value=len(content)
                )

            # 创建消息对象
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content.strip(),
                message_metadata=message_metadata or {},
                token_count=token_count or max(1, len(content) // 4),
                processing_time_ms=processing_time_ms or 0
            )

            # 保存到数据库
            self._session.add(message)
            await self._session.flush()
            await self._session.refresh(message)

            # 更新会话的消息计数和活动时间
            await self.update_session_activity(
                session_id,
                message.created_at
            )

            self._logger.info(
                f"聊天消息创建成功",
                extra={
                    "message_id": str(message.id),
                    "session_id": str(session_id),
                    "role": role.value,
                    "content_length": len(content)
                }
            )

            return message

        except ValidationException:
            raise
        except Exception as e:
            self._logger.error(
                f"聊天消息创建失败: {str(e)}",
                extra={
                    "session_id": str(session_id),
                    "role": role.value,
                    "content_length": len(content) if content else 0
                }
            )
            raise BusinessException(
                error_code="CHAT_MESSAGE_CREATION_FAILED",
                message=f"聊天消息创建失败: {str(e)}",
                details={
                    "session_id": str(session_id),
                    "role": role.value
                }
            )

    async def get_session_messages(
        self,
        session_id: UUID,
        role: Optional[MessageRole] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """
        获取会话消息列表

        Args:
            session_id: 会话ID
            role: 角色过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            消息列表

        Raises:
            ValidationException: 参数验证失败
        """
        try:
            # 参数验证
            if not session_id:
                raise ValidationException(
                    message="会话ID不能为空",
                    field="session_id",
                    value=session_id
                )
            if limit <= 0 or limit > 200:
                raise ValidationException(
                    message="返回数量限制必须在1-200之间",
                    field="limit",
                    value=limit
                )
            if offset < 0:
                raise ValidationException(
                    message="偏移量不能为负数",
                    field="offset",
                    value=offset
                )

            # 构建查询
            statement = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
            )

            # 添加角色过滤
            if role:
                statement = statement.where(ChatMessage.role == role)

            # 排序和分页
            statement = (
                statement
                .order_by(ChatMessage.created_at)
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(statement)
            return result.scalars().all()

        except ValidationException:
            raise
        except Exception as e:
            self._logger.error(
                f"获取会话消息列表失败: {str(e)}",
                extra={
                    "session_id": str(session_id),
                    "role": role.value if role else None,
                    "limit": limit,
                    "offset": offset
                }
            )
            raise BusinessException(
                error_code="SESSION_MESSAGES_FETCH_FAILED",
                message=f"获取会话消息列表失败: {str(e)}",
                details={
                    "session_id": str(session_id),
                    "role": role.value if role else None
                }
            )

    async def count_session_messages(
        self,
        session_id: UUID,
        role: Optional[MessageRole] = None
    ) -> int:
        """
        统计会话消息数量

        Args:
            session_id: 会话ID
            role: 角色过滤

        Returns:
            消息数量
        """
        try:
            if not session_id:
                return 0

            statement = (
                select(func.count(ChatMessage.id))
                .where(ChatMessage.session_id == session_id)
            )

            if role:
                statement = statement.where(ChatMessage.role == role)

            result = await self._session.execute(statement)
            return result.scalar() or 0

        except Exception as e:
            self._logger.error(
                f"统计会话消息数量失败: {str(e)}",
                extra={"session_id": str(session_id)}
            )
            return 0

    async def get_message_by_id(self, message_id: UUID) -> Optional[ChatMessage]:
        """
        根据ID获取消息

        Args:
            message_id: 消息ID

        Returns:
            消息对象或None
        """
        try:
            if not message_id:
                return None

            statement = (
                select(ChatMessage)
                .options(selectinload(ChatMessage.session))
                .where(ChatMessage.id == message_id)
            )

            result = await self._session.execute(statement)
            return result.scalar_one_or_none()

        except Exception as e:
            self._logger.error(
                f"获取消息失败: {str(e)}",
                extra={"message_id": str(message_id)}
            )
            return None

    # ==================== 用户管理 ====================

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户对象或None
        """
        try:
            if not user_id:
                return None

            statement = select(User).where(User.id == user_id)
            result = await self._session.execute(statement)
            return result.scalar_one_or_none()

        except Exception as e:
            self._logger.error(
                f"获取用户失败: {str(e)}",
                extra={"user_id": str(user_id)}
            )
            return None

    # ==================== 统计信息 ====================

    async def get_chat_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """
        获取用户聊天统计信息

        Args:
            user_id: 用户ID

        Returns:
            统计信息字典
        """
        try:
            if not user_id:
                return {}

            # 基础统计
            total_sessions = await self.count_user_sessions(user_id)
            active_sessions = await self.count_user_sessions(user_id, SessionStatus.ACTIVE)

            # 消息统计
            session_statement = (
                select(func.count(ChatMessage.id))
                .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                .where(ChatSession.user_id == user_id)
            )
            message_result = await self._session.execute(session_statement)
            total_messages = message_result.scalar() or 0

            # 按模式统计会话
            mode_stats = {}
            for mode in ChatMode:
                count = await self.count_user_sessions(user_id, chat_mode=mode)
                mode_stats[mode.value] = count

            return {
                "user_id": str(user_id),
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "sessions_by_mode": mode_stats,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            self._logger.error(
                f"获取聊天统计信息失败: {str(e)}",
                extra={"user_id": str(user_id)}
            )
            return {}