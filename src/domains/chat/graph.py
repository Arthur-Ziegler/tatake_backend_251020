"""
聊天图定义

基于LangGraph构建聊天对话图，定义对话流程和节点逻辑。
实现简单的对话模式，包含agent节点和工具节点，支持工具调用。

设计原则：
1. 简单直接的对话流程
2. 清晰的节点职责分离
3. 灵活的工具集成
4. 完整的错误处理

图结构：
START → agent → [条件路由] → {tools, END}
tools → agent → [条件路由] → {tools, END}

功能特性：
- 对话状态管理
- 工具调用集成
- 条件路由逻辑
- 消息处理流程

作者：TaKeKe团队
版本：1.0.0
"""

import os
import logging
from typing import Dict, Any, Literal
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import ToolNode

from .models import ChatState
from .tools.password_opener import sesame_opener
from .tools.task_query import query_tasks, get_task_detail
from .tools.task_crud import create_task, update_task, delete_task
from .tools.task_search import search_tasks
from .tools.task_batch import batch_create_subtasks
from .prompts.system import format_system_prompt
from .context_manager import manage_conversation_context

# 配置日志
logger = logging.getLogger(__name__)


class ChatGraph:
    """
    聊天图类

    封装LangGraph图的构建和编译逻辑，提供统一的聊天对话接口。
    """

    def __init__(self, checkpointer: SqliteSaver, store: InMemoryStore):
        """
        初始化聊天图

        Args:
            checkpointer: LangGraph检查点器
            store: 内存存储实例
        """
        self.checkpointer = checkpointer
        self.store = store
        self.graph = None
        self._build_graph()

    def _build_graph(self) -> None:
        """
        构建LangGraph对话图

        基于最佳实践构建简洁的图结构：
        1. 使用标准节点命名（agent, tools）
        2. 清晰的条件路由
        3. 工具节点自动处理并行调用

        图流程: START -> agent -> [条件路由] -> {tools, END}
        tools -> agent -> [条件路由] -> {tools, END}
        """
        try:
            # 创建工具节点 - 支持并行工具调用，包含所有8个工具
            tool_node = ToolNode([
                sesame_opener,  # 基础工具
                query_tasks, get_task_detail,  # 任务查询工具
                create_task, update_task, delete_task,  # 任务CRUD工具
                search_tasks,  # 任务搜索工具
                batch_create_subtasks  # 批量操作工具
            ])

            # 创建状态图构建器
            builder = StateGraph(ChatState)

            # 添加节点
            builder.add_node("agent", self._agent_node)
            builder.add_node("tools", tool_node)

            # 添加边
            builder.add_edge(START, "agent")

            # 添加条件边：使用标准路由模式
            builder.add_conditional_edges(
                "agent",
                self._route_to_tools,
                {
                    "tools": "tools",
                    "end": END
                }
            )

            # 工具执行完成后返回agent
            builder.add_edge("tools", "agent")

            # 编译图 - 包含检查点和存储
            self.graph = builder.compile(
                checkpointer=self.checkpointer,
                store=self.store
            )

            logger.info("✅ 聊天图构建成功（基于最佳实践）")

        except Exception as e:
            logger.error(f"❌ 聊天图构建失败: {e}")
            raise

    def _agent_node(self, state: ChatState, config: RunnableConfig) -> Dict[str, Any]:
        """
        Agent节点：处理用户消息，生成AI回复

        基于LangGraph最佳实践：
        1. 直接使用状态中的消息
        2. 添加系统提示词
        3. 使用上下文管理优化历史消息
        4. 让模型决定是否调用工具
        5. 返回标准消息格式

        Args:
            state: 当前聊天状态（包含messages字段）
            config: 运行配置，包含user_id和thread_id

        Returns:
            Dict[str, Any]: 更新后的状态（仅包含messages）
        """
        try:
            # 从配置中获取用户信息
            user_id = config.get("configurable", {}).get("user_id")
            session_id = config.get("configurable", {}).get("thread_id")

            if not user_id or not session_id:
                raise ValueError("缺少user_id或thread_id配置")

            # 获取模型（已绑定工具）
            model = self._get_model()
            model_name = model.model_name if hasattr(model, 'model_name') else "gpt-3.5-turbo"

            # 构建消息列表 - 使用标准的LangChain消息格式
            messages = state["messages"]

            # 使用上下文管理器优化消息历史
            if len(messages) > 1:  # 只有多条消息时才需要优化
                original_count = len(messages)
                messages = manage_conversation_context(messages, model_name)
                optimized_count = len(messages)

                if original_count != optimized_count:
                    logger.info(f"📝 上下文优化: {original_count} -> {optimized_count} 条消息")

            # 添加系统提示词到消息开头
            system_prompt = format_system_prompt(user_id, session_id)
            from langchain_core.messages import SystemMessage
            messages_with_system = [SystemMessage(content=system_prompt)] + messages

            # 调用模型，模型会自动决定是否使用工具
            response = model.invoke(messages_with_system)

            logger.info(f"✅ Agent节点处理完成: user_id={user_id}, session_id={session_id}")
            logger.debug(f"🔧 user_id传递状态验证: {user_id} -> ChatState")

            # 检查是否有工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"🔧 模型生成工具调用: {[call['name'] for call in response.tool_calls]}")

            # 返回更新后的消息列表
            return {"messages": [response]}

        except Exception as e:
            logger.error(f"❌ Agent节点处理失败: {e}")

            # 生成错误回复
            from langchain_core.messages import AIMessage
            error_message = AIMessage(content="抱歉，我现在遇到了一些问题，请稍后再试。")
            return {"messages": [error_message]}

    
    def _route_to_tools(self, state: ChatState) -> Literal["tools", "end"]:
        """
        路由决策：判断是否需要调用工具

        使用LangGraph最佳实践：检查最后一条消息是否有tool_calls

        Args:
            state: 当前聊天状态

        Returns:
            Literal["tools", "end"]: 路由决策
        """
        try:
            logger.info("🚦 开始路由决策...")

            # 获取最后一条消息
            last_message = state["messages"][-1] if state["messages"] else None

            if not last_message:
                logger.info("🚦 无消息，路由到结束")
                return "end"

            # 检查是否有工具调用 - 使用标准LangGraph模式
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                logger.info(f"🚦 检测到工具调用: {[call['name'] for call in last_message.tool_calls]}")
                return "tools"

            logger.info("🚦 无工具调用需求，路由到结束")
            return "end"

        except Exception as e:
            logger.error(f"路由决策失败: {e}")
            return "end"

    
    def _get_model(self) -> ChatOpenAI:
        """
        获取OpenAI模型实例并绑定工具

        Returns:
            ChatOpenAI: 模型实例
        """
        try:
            # 聊天模块优先使用OpenAI配置（支持工具调用）
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
            model_name = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            temperature = float(os.getenv("OPENAI_TEMPERATURE", os.getenv("LLM_TEMPERATURE", "0.7")))

            if not api_key:
                raise ValueError("API密钥未设置，请设置LLM_API_KEY或OPENAI_API_KEY环境变量")

            # 创建模型实例
            model = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=1000
            )

            # 绑定工具 - 只对支持工具调用的模型绑定
            if "gpt" in model_name.lower() or "openai" in model_name.lower():
                try:
                    # 绑定所有8个工具
                    all_tools = [
                        sesame_opener,  # 基础工具
                        query_tasks, get_task_detail,  # 任务查询工具
                        create_task, update_task, delete_task,  # 任务CRUD工具
                        search_tasks,  # 任务搜索工具
                        batch_create_subtasks  # 批量操作工具
                    ]
                    model = model.bind_tools(all_tools)
                    logger.info(f"✅ 模型创建成功（带8个工具）: {model_name} @ {base_url}")
                except Exception as tool_error:
                    logger.warning(f"⚠️ 工具绑定失败，使用不带工具的模型: {tool_error}")
                    logger.info(f"📝 模型创建成功（不带工具）: {model_name} @ {base_url}")
            else:
                logger.info(f"📝 模型 {model_name} 可能不支持工具调用，使用基础模型")

            return model

        except Exception as e:
            logger.error(f"❌ 模型创建失败: {e}")
            raise

    def invoke(self, state: ChatState, config: RunnableConfig) -> ChatState:
        """
        调用聊天图

        Args:
            state: 聊天状态
            config: 运行配置

        Returns:
            ChatState: 处理后的状态
        """
        try:
            if not self.graph:
                raise RuntimeError("聊天图未初始化")

            result = self.graph.invoke(state, config)
            return result

        except Exception as e:
            logger.error(f"聊天图调用失败: {e}")
            raise

    def stream(self, state: ChatState, config: RunnableConfig):
        """
        流式调用聊天图

        Args:
            state: 聊天状态
            config: 运行配置

        Yields:
            ChatState: 流式状态更新
        """
        try:
            if not self.graph:
                raise RuntimeError("聊天图未初始化")

            for chunk in self.graph.stream(state, config):
                yield chunk

        except Exception as e:
            logger.error(f"聊天图流式调用失败: {e}")
            raise


def create_chat_graph(checkpointer: SqliteSaver, store: InMemoryStore) -> ChatGraph:
    """
    创建聊天图实例

    Args:
        checkpointer: 检查点器
        store: 内存存储

    Returns:
        ChatGraph: 聊天图实例
    """
    try:
        graph = ChatGraph(checkpointer, store)
        logger.info("聊天图实例创建成功")
        return graph

    except Exception as e:
        logger.error(f"聊天图实例创建失败: {e}")
        raise