"""
简化的聊天代理

基于Context7最佳实践实现：
1. 使用create_react_agent而不是自定义图
2. 使用MessagesState而不是复杂状态
3. 自定义数据库管理消息历史
4. 严格TDD方法
5. KISS设计原则

作者：TaKeKe团队
版本：1.0.0 - 基于Context7最佳实践的重建
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from .simple_database import ChatDatabaseManager
from .simple_state import SimpleChatState

logger = logging.getLogger(__name__)


class SimpleChatAgent:
    """
    简化的聊天代理

    遵循Context7最佳实践：
    - 使用create_react_agent简化代理创建
    - 使用MessagesState避免复杂状态管理
    - 自定义消息历史管理（最近10条）
    - 严格的错误处理和日志记录
    - 无优雅降级，详细错误信息
    """

    def __init__(self, model: BaseChatModel, db_path: Optional[str] = None):
        """
        初始化简化聊天代理

        Args:
            model: 聊天模型实例
            db_path: 数据库路径（可选，默认使用路径）

        Raises:
            Exception: 初始化失败
        """
        try:
            # 初始化数据库管理器
            self._db_manager = ChatDatabaseManager(db_path)

            # 初始化内存存储
            self._store = InMemoryStore()

            # 保存模型引用
            self._model = model

            # 初始化工具（暂时不集成，遵循渐进式集成）
            self._tools = []

            # 延迟初始化代理（遵循lazy loading原则）
            self._agent = None

            logger.info("✅ SimpleChatAgent初始化完成")

        except Exception as e:
            logger.error(f"❌ SimpleChatAgent初始化失败: {e}")
            raise Exception(f"SimpleChatAgent初始化失败: {str(e)}")

    def _create_agent(self) -> Any:
        """
        创建ReAct代理

        Returns:
            配置好的LangGraph代理实例

        Raises:
            Exception: 代理创建失败
        """
        try:
            if self._agent is not None:
                return self._agent

            # 使用create_react_agent（Context7最佳实践）
            agent = create_react_agent(
                self._model,
                tools=self._tools,  # 开始时不集成工具，保持简单
                prompt="你是一个有用的AI助手。请用简洁、友好的方式回答用户问题。"
            )

            # 缓存代理实例
            self._agent = agent

            logger.info("✅ ReAct代理创建成功")
            return agent

        except Exception as e:
            logger.error(f"❌ ReAct代理创建失败: {e}")
            raise Exception(f"ReAct代理创建失败: {str(e)}")

    def _create_config(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        创建LangGraph运行配置

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict[str, Any]: LangGraph配置

        Raises:
            ValueError: 参数验证失败
        """
        # 严格的参数验证
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id必须是非空字符串")
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id必须是非空字符串")

        # 使用thread_id确保会话隔离
        config = {
            "configurable": {
                "thread_id": session_id,
                "user_id": user_id
            }
        }

        return config

    async def send_message(
        self,
        user_id: str,
        session_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        发送消息并获取AI回复

        Args:
            user_id: 用户ID
            session_id: 会话ID
            message: 用户消息

        Returns:
            Dict[str, Any]: 包含AI回复的结果

        Raises:
            ValueError: 参数验证失败
            Exception: 消息处理失败
        """
        try:
            # 严格的参数验证
            if not message or not message.strip():
                raise ValueError("消息内容不能为空")
            if not user_id or not session_id:
                raise ValueError("用户ID和会话ID不能为空")

            # 获取历史消息（最近10条）
            history = await self._db_manager.get_recent_messages(session_id, limit=10)

            # 构建消息列表
            messages: List[BaseMessage] = []

            # 添加历史消息
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))

            # 添加当前用户消息
            messages.append(HumanMessage(content=message))

            # 创建代理
            agent = self._create_agent()

            # 创建配置
            config = self._create_config(user_id, session_id)

            # 调用代理
            result = agent.invoke({"messages": messages}, config)

            # 提取AI回复
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            if not ai_messages:
                raise Exception("代理未返回AI回复")

            ai_response = ai_messages[-1].content
            if not ai_response:
                raise Exception("AI回复内容为空")

            # 保存消息到数据库
            await self._db_manager.save_message(session_id, "user", message)
            await self._db_manager.save_message(session_id, "assistant", ai_response)

            result_data = {
                "user_id": user_id,
                "session_id": session_id,
                "user_message": message,
                "ai_response": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success"
            }

            logger.info(f"✅ 消息处理成功: user_id={user_id}, session_id={session_id}")
            return result_data

        except ValueError:
            raise
        except Exception as e:
            error_msg = f"消息处理失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    async def get_message_history(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取消息历史

        Args:
            session_id: 会话ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            Dict[str, Any]: 消息历史

        Raises:
            ValueError: 参数验证失败
            Exception: 查询失败
        """
        try:
            if not session_id:
                raise ValueError("会话ID不能为空")
            if limit <= 0 or limit > 100:
                raise ValueError("limit必须在1-100之间")
            if offset < 0:
                raise ValueError("offset不能为负数")

            messages = await self._db_manager.get_recent_messages(
                session_id,
                limit=limit,
                offset=offset
            )

            result = {
                "session_id": session_id,
                "messages": messages,
                "total": len(messages),
                "limit": limit,
                "offset": offset,
                "status": "success"
            }

            return result

        except ValueError:
            raise
        except Exception as e:
            error_msg = f"获取消息历史失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    async def clear_session(self, session_id: str) -> Dict[str, Any]:
        """
        清除会话消息

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 清除结果

        Raises:
            ValueError: 参数验证失败
            Exception: 清除失败
        """
        try:
            if not session_id:
                raise ValueError("会话ID不能为空")

            success = await self._db_manager.clear_session_messages(session_id)
            if not success:
                raise Exception("清除会话消息失败")

            result = {
                "session_id": session_id,
                "status": "success",
                "cleared_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✅ 会话清除成功: session_id={session_id}")
            return result

        except ValueError:
            raise
        except Exception as e:
            error_msg = f"清除会话失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话统计信息

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 会话统计

        Raises:
            ValueError: 参数验证失败
            Exception: 查询失败
        """
        try:
            if not session_id:
                raise ValueError("会话ID不能为空")

            stats = await self._db_manager.get_session_stats(session_id)

            result = {
                "session_id": session_id,
                "message_count": stats.get("message_count", 0),
                "last_message_at": stats.get("last_message_at"),
                "created_at": stats.get("created_at"),
                "status": "success"
            }

            return result

        except ValueError:
            raise
        except Exception as e:
            error_msg = f"获取会话统计失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    def add_tool(self, tool: Any) -> None:
        """
        添加工具（渐进式集成）

        Args:
            tool: 要添加的工具

        Raises:
            ValueError: 工具验证失败
        """
        try:
            # 验证工具
            if not hasattr(tool, 'name') or not hasattr(tool, 'description'):
                raise ValueError("工具必须具有name和description属性")

            self._tools.append(tool)

            # 重置代理以包含新工具
            self._agent = None

            logger.info(f"✅ 工具添加成功: {tool.name}")

        except ValueError:
            raise
        except Exception as e:
            error_msg = f"添加工具失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

    def get_tool_count(self) -> int:
        """获取当前工具数量"""
        return len(self._tools)

    def is_agent_ready(self) -> bool:
        """检查代理是否已准备就绪"""
        return self._agent is not None