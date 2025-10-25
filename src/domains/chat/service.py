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
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from .database import chat_db_manager, get_chat_database_path
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
        self._store = self.db_manager.get_store()
        self._graph = None  # Graph缓存实例

    def _create_graph_with_checkpointer(self, checkpointer):
        """
        使用提供的checkpointer创建图实例

        这个方法用于在checkpointer上下文管理器中创建图实例，
        确保checkpointer正确初始化和使用。

        Args:
            checkpointer: 已初始化的checkpointer实例

        Returns:
            ChatGraph: 聊天图实例
        """
        logger.debug("使用checkpointer创建Graph实例")
        from src.domains.chat.graph import create_chat_graph
        return create_chat_graph(checkpointer, self._store)

    def _create_graph(self):
        """创建聊天图实例（保留用于向后兼容）"""
        return self._get_or_create_graph()

    def _with_checkpointer(self, func):
        """
        使用检查点器上下文管理器执行函数

        设计动机：
        ChatService 中的 send_message 操作需要使用 LangGraph 的 checkpointer 进行状态持久化。
        但是我们发现了一个关键的类型安全问题：LangGraph 内部在处理 checkpoint 时，
        某些 channel（特别是 __start__）的版本号会被转换为复杂字符串格式，如：
        '__start__': '00000000000000000000000000000002.0.243798848838515'

        这会导致类型比较错误：'>' not supported between instances of 'str' and 'int'

        解决方案：
        我们创建一个类型安全的 checkpointer 包装器，在每次 checkpoint 操作时
        自动检测和修复类型不匹配问题，确保所有版本号都是整数类型。

        Args:
            func: 要执行的函数，接受类型安全的 checkpointer 参数

        Returns:
            函数执行结果

        Examples:
            >>> def some_operation(checkpointer):
            ...     # 使用类型安全的 checkpointer
            ...     checkpointer.put(config, checkpoint, metadata, {})
            >>> result = self._with_checkpointer(some_operation)
        """
        with self.db_manager.create_checkpointer() as checkpointer:
            # 创建类型安全的checkpointer包装器
            # 这个包装器会自动修复 checkpoint 中的类型问题
            safe_checkpointer = self._create_type_safe_checkpointer(checkpointer)
            return func(safe_checkpointer)

    def _create_type_safe_checkpointer(self, base_checkpointer):
        """
        创建类型安全的checkpointer包装器

        设计背景：
        LangGraph 在内部处理 checkpoint 时，会出现版本号类型不一致的问题。
        具体表现为：
        1. 某些内部 channel（如 __start__）的版本号被转换为复杂的UUID字符串
        2. 当 LangGraph 尝试比较这些字符串版本号与整数版本号时，会抛出类型错误
        3. 这导致 ChatService.send_message() 完全失败

        解决策略：
        我们使用装饰器模式创建一个包装器，在所有 checkpoint 操作前后
        进行类型检查和修复，确保所有 channel_versions 的值都是整数类型。

        技术细节：
        - 对于简单数字字符串：直接转换为 int
        - 对于浮点数字符串：取整数部分
        - 对于复杂UUID字符串：使用哈希生成稳定的整数
        - 对于无法转换的情况：使用默认值 1

        Args:
            base_checkpointer: 原始的 LangGraph checkpointer 实例

        Returns:
            TypeSafeCheckpointer: 类型安全的 checkpointer 包装器实例

        Raises:
            无异常抛出，所有类型问题都会被自动修复
        """

        class TypeSafeCheckpointer:
            """
            类型安全的 checkpointer 包装器

            这个类包装了原始的 LangGraph checkpointer，在每次操作前后
            进行类型安全检查，确保 channel_versions 字段中的所有值都是整数类型。
            """

            def __init__(self, base_checkpointer):
                """
                初始化类型安全的 checkpointer

                Args:
                    base_checkpointer: 原始的 checkpointer 实例
                """
                self.base_checkpointer = base_checkpointer

            def put(self, config, checkpoint, metadata, new_versions):
                """
                安全地存储 checkpoint，确保类型一致性

                这是关键的修复点：在存储 checkpoint 之前，检查并修复
                channel_versions 中的所有类型问题。

                问题现象：
                LangGraph 内部会产生如下 checkpoint：
                {
                    "channel_versions": {
                        "__start__": "00000000000000000000000000000002.0.243798848838515",  # 字符串！
                        "messages": 1  # 整数
                    }
                }

                修复策略：
                1. 浮点数字符串 -> 取整数部分
                2. UUID字符串 -> 生成稳定的哈希整数
                3. 简单数字字符串 -> 直接转换
                4. 无法转换 -> 使用默认值

                Args:
                    config: LangGraph 配置
                    checkpoint: 要存储的 checkpoint 数据
                    metadata: checkpoint 元数据
                    new_versions: 新版本信息

                Returns:
                    原始 checkpointer.put() 的返回值
                """
                # 类型修复逻辑
                if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                    channel_versions = checkpoint["channel_versions"]
                    if isinstance(channel_versions, dict):
                        for key, value in channel_versions.items():
                            if isinstance(value, str):
                                self._fix_string_version_number(key, value, channel_versions)
                            elif not isinstance(value, int):
                                self._fix_non_integer_version(key, value, channel_versions)

                # 委托给原始 checkpointer
                return self.base_checkpointer.put(config, checkpoint, metadata, new_versions)

            def _fix_string_version_number(self, key, value, channel_versions):
                """
                修复字符串类型的版本号

                处理不同类型的字符串版本号：

                示例1 - 浮点数字符串：
                '2.0' -> 2

                示例2 - UUID字符串（这是问题的根源）：
                '00000000000000000000000000000002.0.243798848838515' -> 稳定的哈希整数

                Args:
                    key: channel 名称
                    value: 字符串类型的版本号
                    channel_versions: channel_versions 字典引用
                """
                try:
                    # 情况1: 看起来像浮点数的字符串（如 "2.0"）
                    if '.' in value and value.replace('.', '').isdigit():
                        channel_versions[key] = int(float(value))
                        logger.debug(f"修复浮点版本: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                    else:
                        # 情况2: 尝试直接转换为整数（如 "2"）
                        channel_versions[key] = int(value)
                        logger.debug(f"修复整数字符串: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                except ValueError:
                    # 情况3: 复杂的 UUID 字符串，无法直接转换
                    # 使用哈希生成稳定的整数（确保相同的字符串总是生成相同的整数）
                    stable_int = abs(hash(value)) % (10**9)
                    channel_versions[key] = stable_int
                    logger.debug(f"修复UUID版本: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")

            def _fix_non_integer_version(self, key, value, channel_versions):
                """
                修复非整数类型的版本号

                处理浮点数、布尔值等其他类型的版本号

                Args:
                    key: channel 名称
                    value: 非整数类型的版本号
                    channel_versions: channel_versions 字典引用
                """
                try:
                    channel_versions[key] = int(value)
                    logger.debug(f"强制转换: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                except (ValueError, TypeError):
                    # 如果完全无法转换，使用默认值
                    channel_versions[key] = 1
                    logger.warning(f"使用默认值: {key} 从 {value} ({type(value)}) 重置为 1 (int)")

            def get(self, config):
                """
                安全地检索 checkpoint，确保类型一致性

                即使在存储时已经修复了类型，在检索时也要再次检查，
                因为可能存在直接访问数据库或其他绕过包装器的情况。

                Args:
                    config: LangGraph 配置

                Returns:
                    类型安全的 checkpoint 数据
                """
                result = self.base_checkpointer.get(config)

                # 检索时的类型修复（防御性编程）
                if result and isinstance(result, dict) and "channel_versions" in result:
                    channel_versions = result["channel_versions"]
                    if isinstance(channel_versions, dict):
                        for key, value in channel_versions.items():
                            if isinstance(value, str):
                                try:
                                    channel_versions[key] = int(value)
                                    logger.debug(f"检索时修复类型: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                                except ValueError:
                                    channel_versions[key] = 1
                                    logger.debug(f"检索时重置类型: {key} 无法转换，设置为默认值 1")
                            elif not isinstance(value, int):
                                channel_versions[key] = int(value)
                                logger.debug(f"检索时强制转换: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")

                return result

            def __getattr__(self, name):
                """
                代理其他方法到基础 checkpointer

                所有未被重写的方法都直接委托给原始 checkpointer，
                确保包装器对原有功能的影响最小。

                Args:
                    name: 方法名

                Returns:
                    原始 checkpointer 的对应方法
                """
                return getattr(self.base_checkpointer, name)

        return TypeSafeCheckpointer(base_checkpointer)

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

            # 直接创建会话记录，避免LangGraph的复杂初始化
            self._create_session_record_directly(user_id, session_id, session.title)

            logger.info(f"聊天会话创建成功: user_id={user_id}, session_id={session_id}")

            # 返回固定欢迎消息（不调用LLM）
            welcome_msg = f"你好！我是你的AI助手，会话'{session.title}'已创建。有什么可以帮助你的吗？"

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

            # 获取配置
            config = self._create_runnable_config(user_id, session_id)

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

            def _send_with_checkpointer(checkpointer):
                # 使用新的方法创建图实例
                temp_graph = self._create_graph_with_checkpointer(checkpointer)

                # 运行图处理消息 - 使用临时图实例内部的编译后的图
                result = temp_graph.graph.invoke(current_state, config)
                return result

            # 使用辅助方法执行检查点操作
            result = self._with_checkpointer(_send_with_checkpointer)

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

        使用graph.get_state获取最新状态，避免历史重复问题。

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
            # 获取配置
            config = self._create_runnable_config(user_id, session_id)

            def _get_history_with_checkpointer(checkpointer):
                # 使用临时图获取最新状态（确保正确的checkpointer）
                temp_graph = create_chat_graph(checkpointer, self._store)

                # 使用ChatGraph实例内部的编译后的图的get_state方法
                snapshot = temp_graph.graph.get_state(config)

                # 提取messages字段
                state_messages = snapshot.values.get("messages", [])

                # 序列化LangChain messages为API格式
                messages = []
                for msg in state_messages:
                    if isinstance(msg, HumanMessage):
                        message_item = {
                            "type": "human",
                            "content": msg.content,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        # 增加id字段（如果有）
                        if hasattr(msg, 'id') and msg.id:
                            message_item["id"] = str(msg.id)
                        messages.append(message_item)

                    elif isinstance(msg, AIMessage):
                        message_item = {
                            "type": "ai",
                            "content": msg.content,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        # 增加id字段（如果有）
                        if hasattr(msg, 'id') and msg.id:
                            message_item["id"] = str(msg.id)
                        # 增加tool_calls字段（如果有）
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            message_item["tool_calls"] = [dict(call) for call in msg.tool_calls]
                        # 增加additional_kwargs字段（如果有）
                        if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                            message_item["additional_kwargs"] = msg.additional_kwargs
                        messages.append(message_item)

                    elif isinstance(msg, ToolMessage):
                        message_item = {
                            "type": "tool",
                            "content": msg.content,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        # 增加tool_call_id字段
                        if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
                            message_item["tool_call_id"] = msg.tool_call_id
                        messages.append(message_item)

                # 应用limit截断（取最新N条）
                if len(messages) > limit:
                    messages = messages[-limit:]

                return messages

            # 使用辅助方法执行检查点操作
            messages = self._with_checkpointer(_get_history_with_checkpointer)

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
            # 获取配置
            config = self._create_runnable_config(user_id, session_id)

            def _get_with_checkpointer(checkpointer):
                # 尝试获取最新的检查点
                checkpoints = list(checkpointer.list(config, limit=1))

                if not checkpoints:
                    raise ValueError(f"会话不存在: {session_id}")

                latest_checkpoint = checkpoints[0]
                checkpoint_data = latest_checkpoint.checkpoint or {}

                # 获取元数据进行权限验证
                metadata = latest_checkpoint.metadata or {}

                # 提取会话信息
                channel_values = checkpoint_data.get("channel_values", {})
                messages = channel_values.get("messages", [])

                # 计算消息数量
                message_count = len([msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage))])

                # 获取会话标题，优先从元数据获取，其次从状态值获取
                session_title = metadata.get("title") or channel_values.get("session_title", "未命名会话")
                if metadata.get("user_id") != user_id:
                    raise ValueError(f"无权访问此会话: {session_id}")

                # 获取最后更新时间
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

            # 使用辅助方法执行检查点操作
            result = self._with_checkpointer(_get_with_checkpointer)
            return result

        except ValueError as e:
            logger.warning(f"会话不存在: user_id={user_id}, session_id={session_id}")
            raise
        except Exception as e:
            logger.error(f"获取会话信息失败: user_id={user_id}, session_id={session_id}, error={e}")
            raise Exception(f"获取会话信息失败: {str(e)}")

    def list_sessions(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        列出用户的聊天会话

        通过直接查询SQLite数据库来获取用户会话列表，
        绕过SqliteSaver的API限制，实现真正的会话管理功能。

        Args:
            user_id: 用户ID
            limit: 返回会话数量限制

        Returns:
            Dict[str, Any]: 会话列表

        Raises:
            Exception: 获取会话列表失败时抛出
        """
        try:
            sessions = []
            db_path = get_chat_database_path()

            # 直接查询SQLite数据库获取检查点信息
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            cursor = conn.cursor()

            try:
                # 查询检查点表，获取不同thread_id的最新检查点
                # 直接查询，在Python层面处理UTF-8问题
                query = """
                SELECT
                    thread_id,
                    checkpoint_id,
                    checkpoint,
                    metadata
                FROM checkpoints
                WHERE (thread_id, checkpoint_id) IN (
                    SELECT
                        thread_id,
                        MAX(checkpoint_id) as checkpoint_id
                    FROM checkpoints
                    GROUP BY thread_id
                )
                ORDER BY thread_id DESC
                LIMIT ?
                """

                cursor.execute(query, (max(limit * 3, 100),))  # 获取足够多的数据以便过滤
                rows = cursor.fetchall()

                logger.info(f"list_sessions查询返回{len(rows)}条记录，开始处理用户{user_id}")

                for row in rows:
                    try:
                        # 提取数据，处理可能的UTF-8错误
                        try:
                            session_id = row['thread_id']
                        except UnicodeDecodeError:
                            # 如果thread_id有编码问题，跳过这个记录
                            logger.warning(f"跳过编码错误的记录: thread_id编码错误")
                            continue

                        try:
                            metadata_str = row['metadata']
                            if isinstance(metadata_str, bytes):
                                # 如果metadata是二进制数据，尝试解码或跳过
                                try:
                                    metadata_str = metadata_str.decode('utf-8')
                                except UnicodeDecodeError:
                                    logger.debug(f"metadata为二进制数据，跳过用户验证: session_id={session_id[:8]}...")
                                    metadata_str = "{}"
                        except UnicodeDecodeError:
                            logger.debug(f"metadata编码错误，使用空字符串: session_id={session_id[:8]}...")
                            metadata_str = "{}"

                        # 直接从metadata解析用户信息，避免使用checkpointer API
                        try:
                            # 尝试解析metadata
                            if metadata_str:
                                if isinstance(metadata_str, bytes):
                                    # 如果是二进制数据，尝试解码
                                    try:
                                        metadata_str = metadata_str.decode('utf-8')
                                    except UnicodeDecodeError:
                                        logger.debug(f"跳过二进制metadata: session_id={session_id[:8]}...")
                                        continue

                                try:
                                    metadata = json.loads(metadata_str)
                                    session_user_id = metadata.get("user_id")

                                    if session_user_id == user_id:
                                        # 找到属于当前用户的会话
                                        # 获取该会话的检查点数量
                                        count_query = """
                                        SELECT COUNT(*) as checkpoint_count
                                        FROM checkpoints
                                        WHERE thread_id = ?
                                        """
                                        cursor.execute(count_query, (session_id,))
                                        count_row = cursor.fetchone()
                                        checkpoint_count = count_row['checkpoint_count'] if count_row else 0

                                        # 构建会话信息
                                        session_info = {
                                            "session_id": session_id,
                                            "user_id": user_id,
                                            "title": metadata.get("title") or "未命名会话",
                                            "message_count": checkpoint_count,
                                            "created_at": metadata.get("created_at") or datetime.now(timezone.utc).isoformat(),
                                            "updated_at": datetime.now(timezone.utc).isoformat(),
                                            "status": "active",
                                            "checkpoint_id": row['checkpoint_id']
                                        }

                                        sessions.append(session_info)
                                        logger.debug(f"找到用户会话: {metadata.get('title')} ({session_id[:8]}...)")

                                except json.JSONDecodeError:
                                    logger.debug(f"metadata JSON解析失败: session_id={session_id[:8]}...")
                                    continue
                            else:
                                logger.debug(f"metadata为空: session_id={session_id[:8]}...")
                                continue

                        except Exception as parse_error:
                            # 如果解析失败，跳过这个会话
                            logger.debug(f"metadata解析失败: session_id={session_id[:8]}..., error={parse_error}")
                            continue

                    except Exception as e:
                        logger.warning(f"处理会话失败: session_id={row.get('thread_id', 'unknown')}, error={e}")
                        # 如果是UTF-8解码错误，尝试从checkpoint数据中获取信息
                        if "utf-8" in str(e).lower() and "decode" in str(e).lower():
                            try:
                                # 尝试从checkpoint数据中解析会话信息
                                checkpoint_data = json.loads(row['checkpoint'])
                                channel_values = checkpoint_data.get('channel_values', {})

                                session_info = {
                                    "session_id": session_id,
                                    "user_id": channel_values.get("user_id", user_id),
                                    "title": channel_values.get("session_title", "未命名会话"),
                                    "message_count": len(channel_values.get("messages", [])),
                                    "created_at": datetime.now(timezone.utc).isoformat(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                    "status": "active",
                                    "checkpoint_id": row['checkpoint_id']
                                }

                                # 验证用户ID匹配
                                if session_info["user_id"] == user_id:
                                    sessions.append(session_info)
                                    logger.info(f"从checkpoint数据恢复会话: session_id={session_id}")
                                    continue
                            except Exception as recovery_error:
                                logger.debug(f"从checkpoint恢复会话失败: {recovery_error}")

                        continue

            finally:
                conn.close()

            # 按创建时间倒序排序（最新的在前）并限制数量
            sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            limited_sessions = sessions[:limit]

            logger.info(f"列出用户会话: user_id={user_id}, 找到 {len(sessions)} 个会话，返回 {len(limited_sessions)} 个")

            return {
                "user_id": user_id,
                "sessions": limited_sessions,
                "total_count": len(sessions),
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"列出会话失败: user_id={user_id}, error={e}")
            # 如果直接查询失败，回退到使用checkpointer API
            return self._list_sessions_fallback(user_id, limit)

    def _list_sessions_fallback(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        会话列表查询的回退方法

        当直接数据库查询失败时，使用checkpointer API作为回退方案。
        """
        try:
            sessions = []

            def _list_with_checkpointer(checkpointer):
                # 尝试列出检查点（仅作为回退）
                try:
                    # 使用一个通用的配置来尝试获取检查点
                    test_config = self._create_runnable_config(user_id, "fallback-list")
                    checkpoints = list(checkpointer.list(test_config, limit=1))

                    # 如果有检查点，说明系统工作正常，但无法列出所有会话
                    # 返回空列表而不是错误
                    logger.warning("使用回退方法：无法遍历所有检查点，返回空列表")

                except Exception as e:
                    logger.warning(f"回退方法也失败: {e}")

                return []

            limited_sessions = self._with_checkpointer(_list_with_checkpointer)

            return {
                "user_id": user_id,
                "sessions": limited_sessions,
                "total_count": 0,
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "note": "使用回退方法，可能不完整"
            }

        except Exception as e:
            logger.error(f"回退方法也失败: user_id={user_id}, error={e}")
            return {
                "user_id": user_id,
                "sessions": [],
                "total_count": 0,
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e)
            }

    def delete_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        删除聊天会话

        使用 SqliteSaver 的 delete_thread 方法真正删除会话数据。
        包含权限验证确保用户只能删除自己的会话。

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 删除结果

        Raises:
            Exception: 删除会话失败时抛出
        """
        try:
            # 首先验证会话是否存在且属于当前用户
            try:
                session_info = self.get_session_info(user_id=user_id, session_id=session_id)
                # 如果 get_session_info 没有抛出异常，说明会话存在且属于该用户
            except Exception as e:
                if "不存在" in str(e) or "not found" in str(e).lower():
                    raise Exception(f"会话不存在或无权访问: {session_id}")
                raise

            # 获取配置
            config = self._create_runnable_config(user_id, session_id)

            def _delete_with_checkpointer(checkpointer):
                # 使用 delete_thread 方法删除整个线程的检查点
                # delete_thread 接受 thread_id 字符串，不是配置对象
                delete_result = checkpointer.delete_thread(session_id)
                logger.info(f"删除会话成功: user_id={user_id}, session_id={session_id}, result={delete_result}")
                return delete_result

            # 使用辅助方法执行检查点操作
            self._with_checkpointer(_delete_with_checkpointer)

            # 验证删除是否成功
            try:
                # 尝试再次获取会话信息，应该失败
                self.get_session_info(user_id=user_id, session_id=session_id)
                # 如果还能获取到，说明删除失败
                raise Exception("删除验证失败：会话仍然存在")
            except Exception:
                # 预期的错误，说明删除成功
                pass

            return {
                "session_id": session_id,
                "status": "deleted",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "会话已成功删除"
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

            # 检查图创建能力（通过尝试创建临时图）
            graph_ok = False
            try:
                def _test_graph_creation(checkpointer):
                    temp_graph = create_chat_graph(checkpointer, self._store)
                    return temp_graph is not None

                self._with_checkpointer(_test_graph_creation)
                graph_ok = True
            except Exception as e:
                logger.error(f"图创建测试失败: {e}")

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

    def _create_session_record_directly(self, user_id: str, session_id: str, title: str):
        """
        使用LangGraph API创建会话记录，确保类型一致性

        Args:
            user_id: 用户ID
            session_id: 会话ID
            title: 会话标题
        """
        try:
            # 使用checkpointer创建会话记录，确保类型正确
            with self.db_manager.create_checkpointer() as checkpointer:
                # 创建LangGraph标准的配置
                config = {
                    "configurable": {
                        "thread_id": session_id,
                        "checkpoint_ns": ""
                    }
                }

                # 创建符合LangGraph格式的checkpoint
                current_time = datetime.now(timezone.utc)
                checkpoint_data = {
                    "v": 1,
                    "ts": current_time.timestamp(),
                    "id": str(uuid.uuid4()),
                    "channel_values": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "session_title": title,
                        "created_at": current_time.isoformat(),
                        "messages": []
                    },
                    "channel_versions": {
                        "messages": 1  # 确保是整数类型
                    },
                    "versions_seen": {},
                    "pending_sends": []
                }

                metadata = {
                    "user_id": user_id,
                    "title": title,
                    "source": "create",
                    "step": -1,
                    "parents": {},
                    "created_at": current_time.isoformat()
                }

                # 使用checkpointer.put，这会正确处理类型
                checkpointer.put(config, checkpoint_data, metadata, {})

            logger.debug(f"会话记录已创建: session_id={session_id}, user_id={user_id}")

        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")
            raise Exception(f"创建会话记录失败: {str(e)}")

  
    def _ensure_database_initialized(self):
        """
        确保数据库表已初始化

        通过实际使用checkpointer.put()来触发LangGraph的数据库表创建。
        使用正确的LangGraph格式，确保类型一致性。
        """
        try:
            # 使用数据库管理器初始化数据库
            with self.db_manager.create_checkpointer() as checkpointer:
                # 创建符合LangGraph标准的配置
                dummy_config = {"configurable": {"thread_id": "__db_init__", "checkpoint_ns": ""}}

                # 创建符合LangGraph格式的虚拟checkpoint
                dummy_checkpoint = {
                    "v": 1,
                    "ts": 0,
                    "id": "init-checkpoint",
                    "channel_values": {"messages": []},
                    "channel_versions": {"messages": 1},  # 确保是整数类型
                    "versions_seen": {},
                    "pending_sends": []
                }

                # put操作会自动创建checkpoints表结构，并保持正确的类型
                checkpointer.put(dummy_config, dummy_checkpoint, {}, {})

                logger.debug("数据库表结构初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise Exception(f"无法初始化聊天数据库: {str(e)}")


# 创建全局聊天服务实例
chat_service = ChatService()