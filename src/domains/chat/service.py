"""
聊天服务层

基于LangGraph的聊天业务逻辑实现，提供会话管理和消息处理功能。
采用简单的架构设计，避免过度抽象，专注于核心聊天功能。

设计原则：
1. 直接使用LangGraph API，避免过度封装
2. 简单明确的会话管理
3. 清晰的错误处理逻辑
4. 保持与现有域架构的一致性

功能特性：
- 会话创建和管理
- 消息发送和接收
- 聊天历史查询
- JWT认证集成
- 用户隔离机制

作者：TaKeKe团队
版本：1.0.0
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from .database import chat_db_manager
from .graph import create_chat_graph
from .models import ChatState, ChatSession, ChatMessage
from .prompts.system import format_welcome_message, format_session_summary

# 配置日志
logger = logging.getLogger(__name__)


class ChatService:
    """
    聊天服务类

    提供基于LangGraph的聊天功能，包括会话管理、消息处理
    和历史查询等核心业务逻辑。
    """

    def __init__(self):
        """初始化聊天服务"""
        self.db_manager = chat_db_manager
        self._checkpointer = None
        self._store = None
        self._graph = None

    def _get_graph(self):
        """获取聊天图实例"""
        if self._graph is None:
            self._checkpointer = self.db_manager.get_checkpointer()
            self._store = self.db_manager.get_store()
            self._graph = create_chat_graph(self._checkpointer, self._store)
        return self._graph

    def _create_thread_id(self) -> str:
        """创建新的线程ID"""
        return str(uuid.uuid4())

    def _create_runnable_config(self, user_id: str, thread_id: str) -> RunnableConfig:
        """
        创建LangGraph运行配置

        Args:
            user_id: 用户ID
            thread_id: 线程ID

        Returns:
            RunnableConfig: LangGraph运行配置
        """
        return {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }

    def create_session(self, user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新的聊天会话

        Args:
            user_id: 用户ID
            title: 会话标题（可选）

        Returns:
            Dict[str, Any]: 会话创建结果

        Raises:
            Exception: 会话创建失败时抛出
        """
        try:
            # 生成会话ID
            session_id = self._create_thread_id()

            # 创建会话记录
            session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                title=title or "新会话",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # 获取配置并初始化图
            config = self._create_runnable_config(user_id, session_id)
            graph = self._get_graph()

            # 创建初始状态（使用字典格式）
            initial_state = {
                "user_id": user_id,
                "session_id": session_id,
                "session_title": session.title,
                "messages": []
            }

            # 运行图以初始化会话状态
            result = graph.invoke(initial_state, config)

            logger.info(f"聊天会话创建成功: user_id={user_id}, session_id={session_id}")

            # 生成欢迎消息
            welcome_msg = format_welcome_message(user_id, session_id, title)

            return {
                "session_id": session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "welcome_message": welcome_msg,
                "status": "created"
            }

        except Exception as e:
            logger.error(f"创建聊天会话失败: user_id={user_id}, error={e}")
            raise Exception(f"创建会话失败: {str(e)}")

    def send_message(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """
        发送消息到聊天会话

        基于最佳实践的简化实现：
        1. 使用标准LangChain消息格式
        2. 简化状态管理
        3. 优化AI回复提取逻辑

        Args:
            user_id: 用户ID
            session_id: 会话ID
            message: 用户消息内容

        Returns:
            Dict[str, Any]: 消息处理结果

        Raises:
            Exception: 消息发送失败时抛出
        """
        try:
            # 验证输入
            if not message or not message.strip():
                raise ValueError("消息内容不能为空")

            # 获取配置和图
            config = self._create_runnable_config(user_id, session_id)
            graph = self._get_graph()

            # 创建用户消息 - 使用标准LangChain格式
            from langchain_core.messages import HumanMessage
            user_message = HumanMessage(content=message.strip())

            # 创建当前状态 - 基于最佳实践的简洁状态
            current_state = {
                "user_id": user_id,
                "session_id": session_id,
                "session_title": "聊天会话",  # 可从数据库获取
                "messages": [user_message]
            }

            # 运行图处理消息
            result = graph.invoke(current_state, config)

            # 提取AI回复 - 使用优化逻辑
            ai_response = self._extract_ai_response(result.get("messages", []))

            logger.info(f"✅ 消息处理成功: user_id={user_id}, session_id={session_id}")

            return {
                "session_id": session_id,
                "user_message": message,
                "ai_response": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success"
            }

        except ValueError as e:
            logger.warning(f"⚠️ 消息验证失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise
        except Exception as e:
            logger.error(f"❌ 消息发送失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise Exception(f"发送消息失败: {str(e)}")

    def _extract_ai_response(self, messages: List) -> str:
        """
        从消息列表中提取最新的AI回复

        基于最佳实践的消息处理逻辑：
        1. 从最后一条消息开始查找
        2. 优先返回AIMessage内容
        3. 处理工具调用场景

        Args:
            messages: 消息列表

        Returns:
            str: AI回复内容
        """
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # 如果AI消息有工具调用，检查后续是否有工具结果
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 查找工具结果来生成更完整的回复
                    return msg.content or "工具调用已完成。"
                return msg.content
            elif isinstance(msg, HumanMessage):
                # 遇到用户消息，停止搜索
                break
            elif isinstance(msg, ToolMessage):
                # 工具消息，继续搜索前面的AI消息
                continue

        # 如果没有找到AI回复，返回默认消息
        return "抱歉，我现在无法处理您的消息，请稍后再试。"

    def get_chat_history(self, user_id: str, session_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        获取聊天历史记录

        Args:
            user_id: 用户ID
            session_id: 会话ID
            limit: 返回消息数量限制

        Returns:
            Dict[str, Any]: 聊天历史记录

        Raises:
            Exception: 获取历史记录失败时抛出
        """
        try:
            # 获取配置和图
            config = self._create_runnable_config(user_id, session_id)
            graph = self._get_graph()

            # 获取检查点历史
            checkpoints = list(self._checkpointer.list(config, limit=limit))

            # 构建消息历史
            messages = []
            for checkpoint in checkpoints:
                checkpoint_data = checkpoint.checkpoint or {}
                channel_values = checkpoint_data.get("channel_values", {})
                state_messages = channel_values.get("messages", [])
                for msg in state_messages:
                    # 处理不同类型的消息格式
                    if isinstance(msg, dict):
                        # 字典格式的消息
                        msg_type = msg.get("type", "unknown")
                        if msg_type in ["human", "ai", "tool"]:
                            messages.append({
                                "type": msg_type,
                                "content": msg.get("content", ""),
                                "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat())
                            })
                    elif hasattr(msg, 'content'):  # LangChain消息对象
                        if isinstance(msg, HumanMessage):
                            messages.append({
                                "type": "human",
                                "content": msg.content,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                        elif isinstance(msg, AIMessage):
                            messages.append({
                                "type": "ai",
                                "content": msg.content,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                        elif isinstance(msg, ToolMessage):
                            messages.append({
                                "type": "tool",
                                "content": msg.content,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

            # 按时间排序并限制数量
            messages = messages[-limit:] if len(messages) > limit else messages

            logger.info(f"获取聊天历史成功: user_id={user_id}, session_id={session_id}, messages={len(messages)}")

            return {
                "session_id": session_id,
                "messages": messages,
                "total_count": len(messages),
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"获取聊天历史失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise Exception(f"获取聊天历史失败: {str(e)}")

    def get_session_info(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        获取会话信息

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 会话信息

        Raises:
            Exception: 获取会话信息失败时抛出
        """
        try:
            # 获取配置和图
            config = self._create_runnable_config(user_id, session_id)
            graph = self._get_graph()

            # 尝试获取最新的检查点
            # 正确的配置格式
            checkpoints = list(self._checkpointer.list(config, limit=1))

            if not checkpoints:
                raise ValueError(f"会话不存在: {session_id}")

            latest_checkpoint = checkpoints[0]
            checkpoint_data = latest_checkpoint.checkpoint or {}

            # 提取会话信息
            channel_values = checkpoint_data.get("channel_values", {})
            messages = channel_values.get("messages", [])

            # 计算消息数量
            message_count = len([msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage))])

            # 获取会话标题
            session_title = channel_values.get("session_title", "未命名会话")

            # 获取最后更新时间
            metadata = latest_checkpoint.metadata or {}
            if isinstance(metadata, dict):
                source = metadata.get("source", {})
                if isinstance(source, dict):
                    updated_at = source.get("time", datetime.now(timezone.utc).isoformat())
                else:
                    updated_at = str(source) if source else datetime.now(timezone.utc).isoformat()
            else:
                updated_at = str(metadata) if metadata else datetime.now(timezone.utc).isoformat()

            logger.info(f"获取会话信息成功: user_id={user_id}, session_id={session_id}")

            return {
                "session_id": session_id,
                "title": session_title,
                "message_count": message_count,
                "created_at": updated_at,  # SQLite没有单独的创建时间，使用更新时间
                "updated_at": updated_at,
                "status": "active"
            }

        except ValueError as e:
            logger.warning(f"会话不存在: user_id={user_id}, session_id={session_id}")
            raise
        except Exception as e:
            logger.error(f"获取会话信息失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise Exception(f"获取会话信息失败: {str(e)}")

    def list_sessions(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        列出用户的聊天会话

        Args:
            user_id: 用户ID
            limit: 返回会话数量限制

        Returns:
            Dict[str, Any]: 会话列表

        Raises:
            Exception: 获取会话列表失败时抛出
        """
        try:
            # 由于SqliteSaver限制，这里返回简单的会话列表
            # 在实际应用中，可能需要额外的会话索引表
            sessions = []

            # 尝试从检查点中恢复会话信息
            # 注意：这是一个简化实现，实际项目中可能需要专门的会话管理表
            logger.info(f"列出用户会话: user_id={user_id}, limit={limit}")

            return {
                "user_id": user_id,
                "sessions": sessions,  # 暂时返回空列表，等待后续实现
                "total_count": 0,
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "note": "会话列表功能将在后续版本中实现"
            }

        except Exception as e:
            logger.error(f"列出会话失败: user_id={user_id}, error={e}")
            raise Exception(f"列出会话失败: {str(e)}")

    def delete_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        删除聊天会话

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 删除结果

        Raises:
            Exception: 删除会话失败时抛出
        """
        try:
            # 获取配置
            config = self._create_runnable_config(user_id, session_id)

            # 删除检查点数据
            # 注意：SqliteSaver可能不直接支持删除操作，这里做标记删除
            config_tuple = ("", config["configurable"])

            # 在实际实现中，这里需要调用适当的方法删除会话数据
            # 由于LangGraph的限制，这里只是记录操作
            logger.info(f"删除会话操作: user_id={user_id}, session_id={session_id}")

            return {
                "session_id": session_id,
                "status": "deleted",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "会话删除功能将在后续版本中完善"
            }

        except Exception as e:
            logger.error(f"删除会话失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise Exception(f"删除会话失败: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        """
        聊天服务健康检查

        Returns:
            Dict[str, Any]: 健康检查结果
        """
        try:
            # 检查数据库连接
            db_health = self.db_manager.health_check()

            # 检查图初始化状态
            graph_ok = self._graph is not None

            overall_status = "healthy" if (db_health.get("status") == "healthy" and graph_ok) else "unhealthy"

            return {
                "status": overall_status,
                "database": db_health,
                "graph_initialized": graph_ok,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"聊天服务健康检查失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# 创建全局聊天服务实例
chat_service = ChatService()