"""
AI客户端模块

该模块提供与AI服务的集成，包括LangGraph状态机和LLM客户端。
采用面向对象设计，支持不同的AI提供商和配置。

核心组件：
- AIProviderBase: AI提供商基类
- ClaudeProvider: Claude AI提供商实现
- LangGraphOrchestrator: LangGraph对话编排器
- MessageHandler: 消息处理工具

设计原则：
- 策略模式：支持多种AI提供商
- 工厂模式：动态创建AI客户端
- 依赖注入：便于测试和扩展
- 错误隔离：AI服务异常不影响业务逻辑
"""

import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

# LangChain和LangGraph导入
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig

# 环境变量和配置
from dotenv import load_dotenv

# 导入服务层组件
from ..exceptions import BusinessException, ValidationException
from ..base import BaseService

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class AIConfig:
    """AI配置类"""
    """AI服务配置"""
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "claude-3-haiku-20240307"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.9")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1000")))
    timeout: int = 30  # 请求超时时间（秒）


@dataclass
class ChatState:
    """聊天状态类"""
    """LangGraph状态定义"""
    messages: List[Any] = field(default_factory=list)
    user_context: Dict[str, Any] = field(default_factory=dict)
    conversation_metadata: Dict[str, Any] = field(default_factory=dict)
    current_intent: Optional[str] = None
    required_actions: List[str] = field(default_factory=list)
    processing_state: str = "idle"
    error_info: Optional[Dict[str, Any]] = None


class AIProviderBase(ABC):
    """AI提供商基类"""

    def __init__(self, config: AIConfig):
        """
        初始化AI提供商

        Args:
            config: AI配置
        """
        self.config = config
        self._client = None

    @abstractmethod
    async def initialize(self) -> None:
        """初始化AI客户端"""
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        生成AI回复

        Args:
            messages: 消息历史
            context: 上下文信息

        Returns:
            AI回复内容
        """
        pass

    @abstractmethod
    async def generate_stream_response(
        self,
        messages: List[Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式AI回复

        Args:
            messages: 消息历史
            context: 上下文信息

        Yields:
            流式回复内容
        """
        pass


class ClaudeProvider(AIProviderBase):
    """Claude AI提供商实现"""

    def __init__(self, config: AIConfig):
        """
        初始化Claude提供商

        Args:
            config: AI配置
        """
        super().__init__(config)
        self._client = None
        self._model = None

    async def initialize(self) -> None:
        """初始化Claude客户端"""
        try:
            self._client = ChatAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                model=self.config.model,
                timeout=self.config.timeout
            )

            # 验证连接
            await self._test_connection()

            logger.info(f"Claude AI客户端初始化成功，模型: {self.config.model}")

        except Exception as e:
            logger.error(f"Claude AI客户端初始化失败: {str(e)}")
            raise BusinessException(
                error_code="AI_CLIENT_INIT_FAILED",
                message=f"AI客户端初始化失败: {str(e)}",
                details={"provider": "claude", "model": self.config.model}
            )

    async def _test_connection(self) -> None:
        """测试连接"""
        try:
            # 发送一个简单的测试消息
            test_message = HumanMessage(content="Hello")
            await self._client.ainvoke([test_message])
        except Exception as e:
            raise BusinessException(
                error_code="AI_CONNECTION_TEST_FAILED",
                message=f"AI连接测试失败: {str(e)}",
                details={"provider": "claude"}
            )

    async def generate_response(
        self,
        messages: List[Any],
        context: Dict[str, Any] = None
    ) -> str:
        """
        生成Claude回复

        Args:
            messages: 消息历史
            context: 上下文信息

        Returns:
            Claude回复内容
        """
        if not self._client:
            await self.initialize()

        try:
            # 构建消息列表
            langchain_messages = self._convert_messages(messages)

            # 生成回复
            response = await self._client.ainvoke(langchain_messages)

            return response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            logger.error(f"Claude回复生成失败: {str(e)}")
            raise BusinessException(
                error_code="AI_RESPONSE_GENERATION_FAILED",
                message=f"AI回复生成失败: {str(e)}",
                details={
                    "provider": "claude",
                    "model": self.config.model,
                    "message_count": len(messages)
                }
            )

    async def generate_stream_response(
        self,
        messages: List[Any],
        context: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成Claude流式回复

        Args:
            messages: 消息历史
            context: 上下文信息

        Yields:
            流式回复内容
        """
        if not self._client:
            await self.initialize()

        try:
            # 构建消息列表
            langchain_messages = self._convert_messages(messages)

            # 生成流式回复
            async for chunk in self._client.astream(langchain_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"Claude流式回复生成失败: {str(e)}")
            # 在流式模式下，我们返回错误信息而不是抛出异常
            yield f"\n\n抱歉，AI回复生成出现问题: {str(e)}"

    def _convert_messages(self, messages: List[Any]) -> List[Any]:
        """
        转换消息格式为LangChain格式

        Args:
            messages: 原始消息列表

        Returns:
            LangChain消息列表
        """
        langchain_messages = []

        for msg in messages:
            if hasattr(msg, 'message_type'):
                if msg.message_type == MessageType.USER:
                    langchain_messages.append(HumanMessage(content=msg.content))
                elif msg.message_type == MessageType.ASSISTANT:
                    langchain_messages.append(AIMessage(content=msg.content))
                elif msg.message_type == MessageType.SYSTEM:
                    langchain_messages.append(SystemMessage(content=msg.content))
            else:
                # 如果是LangChain消息，直接添加
                langchain_messages.append(msg)

        return langchain_messages


class LangGraphOrchestrator:
    """LangGraph对话编排器"""

    def __init__(self, ai_provider: AIProviderBase):
        """
        初始化编排器

        Args:
            ai_provider: AI提供商
        """
        self.ai_provider = ai_provider
        self._graph = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化LangGraph"""
        if self._initialized:
            return

        try:
            # 构建状态图
            workflow = StateGraph(ChatState)

            # 添加节点
            workflow.add_node("analyze_intent", self._analyze_intent_node)
            workflow.add_node("gather_context", self._gather_context_node)
            workflow.add_node("generate_response", self._generate_response_node)
            workflow.add_node("post_process", self._post_process_node)
            workflow.add_node("error_handler", self._error_handler_node)

            # 设置入口点
            workflow.set_entry_point("analyze_intent")

            # 添加边
            workflow.add_edge("analyze_intent", "gather_context")
            workflow.add_edge("gather_context", "generate_response")
            workflow.add_edge("generate_response", "post_process")
            workflow.add_edge("post_process", END)

            # 添加条件边
            workflow.add_conditional_edges(
                "generate_response",
                self._should_handle_error,
                {
                    "error": "error_handler",
                    "success": "post_process"
                }
            )
            workflow.add_edge("error_handler", END)

            # 编译应用
            self._graph = workflow.compile()
            self._initialized = True

            logger.info("LangGraph编排器初始化成功")

        except Exception as e:
            logger.error(f"LangGraph编排器初始化失败: {str(e)}")
            raise BusinessException(
                error_code="LANGGRAPH_INIT_FAILED",
                message=f"LangGraph编排器初始化失败: {str(e)}"
            )

    async def process_conversation(
        self,
        state: ChatState,
        config: Optional[RunnableConfig] = None
    ) -> ChatState:
        """
        处理对话

        Args:
            state: 对话状态
            config: 运行配置

        Returns:
            更新后的对话状态
        """
        if not self._initialized:
            await self.initialize()

        try:
            result = await self._graph.ainvoke(state, config=config)

            # 处理LangGraph返回的字典格式
            if isinstance(result, dict):
                # 转换为ChatState对象
                return ChatState(
                    messages=result.get("messages", state.messages),
                    user_context=result.get("user_context", state.user_context),
                    conversation_metadata=result.get("conversation_metadata", state.conversation_metadata),
                    current_intent=result.get("current_intent", state.current_intent),
                    required_actions=result.get("required_actions", state.required_actions),
                    processing_state=result.get("processing_state", state.processing_state),
                    error_info=result.get("error_info", state.error_info)
                )
            else:
                return result
        except Exception as e:
            logger.error(f"对话处理失败: {str(e)}")
            # 返回错误状态
            error_state = ChatState(
                messages=state.messages,
                user_context=state.user_context,
                conversation_metadata=state.conversation_metadata,
                processing_state="error",
                error_info={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            return error_state

    async def _analyze_intent_node(self, state: ChatState) -> ChatState:
        """分析用户意图节点"""
        try:
            if not state.messages:
                state.current_intent = "unknown"
            else:
                last_message = state.messages[-1]
                if hasattr(last_message, 'content'):
                    state.current_intent = self._analyze_intent(last_message.content)
                else:
                    state.current_intent = "unknown"

            state.processing_state = "intent_analyzed"
            return state

        except Exception as e:
            logger.error(f"意图分析失败: {str(e)}")
            state.processing_state = "error"
            state.error_info = {"error": "intent_analysis_failed", "details": str(e)}
            return state

    async def _gather_context_node(self, state: ChatState) -> ChatState:
        """收集上下文节点"""
        try:
            # 这里可以根据意图收集相关上下文
            # 目前保持简单实现
            state.processing_state = "context_gathered"
            return state

        except Exception as e:
            logger.error(f"上下文收集失败: {str(e)}")
            state.processing_state = "error"
            state.error_info = {"error": "context_gathering_failed", "details": str(e)}
            return state

    async def _generate_response_node(self, state: ChatState) -> ChatState:
        """生成回复节点"""
        try:
            # 使用AI提供商生成回复
            response_content = await self.ai_provider.generate_response(
                state.messages,
                {
                    "intent": state.current_intent,
                    "user_context": state.user_context,
                    "conversation_metadata": state.conversation_metadata
                }
            )

            # 创建AI回复消息
            ai_message = AIMessage(content=response_content)
            state.messages = add_messages(state.messages, [ai_message])

            state.processing_state = "response_generated"
            return state

        except Exception as e:
            logger.error(f"回复生成失败: {str(e)}")
            state.processing_state = "error"
            state.error_info = {"error": "response_generation_failed", "details": str(e)}
            return state

    async def _post_process_node(self, state: ChatState) -> ChatState:
        """后处理节点"""
        try:
            # 执行后处理逻辑，如提取需要执行的动作
            state.required_actions = self._extract_required_actions(state)
            state.processing_state = "completed"
            return state

        except Exception as e:
            logger.error(f"后处理失败: {str(e)}")
            state.processing_state = "error"
            state.error_info = {"error": "post_processing_failed", "details": str(e)}
            return state

    async def _error_handler_node(self, state: ChatState) -> ChatState:
        """错误处理节点"""
        try:
            # 生成错误回复
            error_message = "抱歉，处理您的请求时遇到了问题。请稍后再试。"
            ai_message = AIMessage(content=error_message)
            state.messages = add_messages(state.messages, [ai_message])

            state.processing_state = "error_handled"
            state.required_actions = []
            return state

        except Exception as e:
            logger.error(f"错误处理失败: {str(e)}")
            state.processing_state = "critical_error"
            return state

    def _should_handle_error(self, state: ChatState) -> str:
        """判断是否需要处理错误"""
        return "error" if state.processing_state == "error" else "success"

    def _analyze_intent(self, content: str) -> str:
        """分析用户意图"""
        content_lower = content.lower()

        # 简单的意图识别逻辑
        intent_patterns = {
            "task_help": ["任务", "待办", "todo", "任务管理", "task"],
            "productivity_advice": ["效率", "生产力", "如何提高", "怎么提升", "效率建议"],
            "focus_help": ["专注", "集中注意力", "分心", "干扰", "专注力"],
            "time_management": ["时间管理", "安排", "计划", "时间分配"],
            "goal_setting": ["目标", "计划", "目标设定", "制定目标"],
            "habit_development": ["习惯", "养成", "坚持", "习惯培养"],
            "greeting": ["你好", "hello", "hi", "嗨", "您好"],
            "thanks": ["谢谢", "感谢", "thank", "谢了"],
            "question": ["什么", "为什么", "如何", "怎么", "?", "？"],
            "general": ["一般", "普通", "随便", "聊天"]
        }

        for intent, patterns in intent_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                return intent

        return "general"

    def _extract_required_actions(self, state: ChatState) -> List[str]:
        """提取需要执行的动作"""
        actions = []

        # 基于意图确定需要的动作
        if state.current_intent == "task_help":
            actions.extend(["analyze_tasks", "provide_task_suggestions"])
        elif state.current_intent == "productivity_advice":
            actions.extend(["analyze_productivity", "generate_recommendations"])
        elif state.current_intent == "focus_help":
            actions.extend(["analyze_focus_patterns", "suggest_focus_techniques"])

        return actions


class MessageHandler:
    """消息处理工具类"""

    @staticmethod
    def create_system_message(chat_mode: str, user_context: Dict[str, Any] = None) -> str:
        """
        创建系统消息

        Args:
            chat_mode: 聊天模式
            user_context: 用户上下文

        Returns:
            系统消息内容
        """
        system_prompts = {
            "general": "您是一个友善的AI助手，可以帮助用户处理各种问题和任务。",
            "task_assistant": "您是一个专业的任务管理助手，可以帮助用户管理任务、提供建议、分析进度。请专注于任务相关的帮助。",
            "productivity_coach": "您是一位生产力教练，专注于帮助用户提高工作效率、培养良好习惯、实现目标。请提供实用的生产力建议。",
            "focus_guide": "您是一位专注力指导师，可以帮助用户提高专注力、管理干扰、保持高效的工作状态。请专注于专注相关的建议。"
        }

        base_prompt = system_prompts.get(chat_mode, system_prompts["general"])

        # 添加用户上下文信息
        if user_context:
            context_info = []
            if "level" in user_context:
                context_info.append(f"用户等级: {user_context['level']}")
            if "current_streak" in user_context:
                context_info.append(f"当前连续记录: {user_context['current_streak']}天")

            if context_info:
                base_prompt += f"\n\n用户信息: {', '.join(context_info)}"

        return base_prompt

    @staticmethod
    def format_response(response: str, processing_time_ms: int = 0) -> Dict[str, Any]:
        """
        格式化回复响应

        Args:
            response: AI回复内容
            processing_time_ms: 处理时间（毫秒）

        Returns:
            格式化的响应数据
        """
        return {
            "content": response,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": os.getenv("LLM_MODEL", "unknown"),
            "provider": "anthropic"
        }


class AIClientFactory:
    """AI客户端工厂"""

    _providers = {
        "claude": ClaudeProvider,
        # 可以轻松添加其他提供商
    }

    @classmethod
    def create_provider(cls, provider_type: str, config: AIConfig) -> AIProviderBase:
        """
        创建AI提供商

        Args:
            provider_type: 提供商类型
            config: AI配置

        Returns:
            AI提供商实例
        """
        if provider_type not in cls._providers:
            raise ValidationException(
                f"不支持的AI提供商类型: {provider_type}",
                field="provider_type",
                value=provider_type,
                details={"supported_types": list(cls._providers.keys())}
            )

        provider_class = cls._providers[provider_type]
        return provider_class(config)

    @classmethod
    def get_default_provider(cls) -> str:
        """获取默认提供商类型"""
        return "claude"