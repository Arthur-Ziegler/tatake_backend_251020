"""
UltraThink大模型集成器

提供与真实UltraThink大模型的API集成，支持：
1. 大模型API调用和响应处理
2. 上下文管理和对话历史
3. 错误处理和重试机制
4. 成本监控和使用统计
5. MCP优先原则实现

设计原则：
1. 单一职责：专注于大模型API集成
2. 接口隔离：清晰的输入输出接口
3. 依赖注入：通过构造函数注入配置
4. 错误恢复：优雅处理API异常

作者：TaKeKe团队
版本：1.0.0
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class UltraThinkConfig:
    """UltraThink模型配置"""
    api_base_url: str = "https://api.302.ai/v1"
    api_key: str = ""
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """初始化后处理"""
        if not self.api_key:
            self.api_key = os.getenv('ULTRATHINK_API_KEY', '')

        if not self.api_key:
            raise ValueError("UltraThink API Key未配置，请设置ULTRATHINK_API_KEY环境变量")


@dataclass
class LLMMessage:
    """LLM消息结构"""
    role: str  # system, user, assistant
    content: str
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    model: str
    usage: Dict[str, int]
    response_time: float
    timestamp: str

    @property
    def token_count(self) -> int:
        """获取总Token数"""
        return self.usage.get('total_tokens', 0)

    @property
    def cost_estimate(self) -> float:
        """估算成本（简化计算）"""
        # 这里可以根据实际定价策略计算
        return self.token_count * 0.00001  # 示例定价


class UltraThinkLMIntegrator:
    """UltraThink大模型集成器"""

    def __init__(self, config: Optional[UltraThinkConfig] = None):
        """初始化集成器

        Args:
            config: UltraThink配置，如果为None则使用默认配置
        """
        self.config = config or UltraThinkConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.conversation_history: List[LLMMessage] = []
        self.usage_stats = {
            'total_calls': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'errors': 0
        }

        logger.info(f"🤖 UltraThink集成器已初始化，模型: {self.config.model}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def _ensure_session(self):
        """确保HTTP会话已创建"""
        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'Bearer {self.config.api_key}',
                'Content-Type': 'application/json'
            }
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
            logger.info("🌐 HTTP会话已创建")

    async def close(self):
        """关闭资源"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🔌 HTTP会话已关闭")

    def _prepare_messages(self, prompt: str, context: Optional[str] = None) -> List[Dict[str, str]]:
        """准备API请求消息

        Args:
            prompt: 用户提示
            context: 可选的上下文信息

        Returns:
            格式化的消息列表
        """
        messages = []

        # 添加系统消息
        system_message = {
            "role": "system",
            "content": self._get_system_prompt()
        }
        messages.append(system_message)

        # 添加上下文（如果提供）
        if context:
            context_message = {
                "role": "system",
                "content": f"上下文信息：\n{context}"
            }
            messages.append(context_message)

        # 添加用户提示
        user_message = {
            "role": "user",
            "content": prompt
        }
        messages.append(user_message)

        return messages

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个专业的AI助手，专门用于测试和验证聊天工具的功能。

你的职责：
1. 理解用户的工具调用请求
2. 分析工具响应的正确性
3. 提供专业的功能验证建议
4. 模拟真实用户的使用场景

请始终以专业、准确的方式回应，专注于工具功能验证。"""

    async def call_ultrathink(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """调用UltraThink大模型API

        Args:
            prompt: 用户提示
            context: 可选的上下文信息
            temperature: 温度参数，如果为None则使用配置值
            max_tokens: 最大Token数，如果为None则使用配置值

        Returns:
            LLM响应对象

        Raises:
            RuntimeError: API调用失败
        """
        await self._ensure_session()

        # 准备请求数据
        messages = self._prepare_messages(prompt, context)
        request_data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        # 记录开始时间
        start_time = datetime.now(timezone.utc)

        # 执行API调用（带重试）
        response_data = await self._call_with_retry(request_data)

        # 计算响应时间
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 解析响应
        response = LLMResponse(
            content=response_data.get('content', ''),
            model=response_data.get('model', self.config.model),
            usage=response_data.get('usage', {}),
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # 更新使用统计
        self._update_stats(response)

        # 记录对话历史
        self.conversation_history.append(LLMMessage(role="user", content=prompt))
        self.conversation_history.append(LLMMessage(role="assistant", content=response.content))

        logger.info(f"✅ UltraThink调用完成，Token: {response.token_count}, 耗时: {response_time:.2f}s")

        return response

    async def _call_with_retry(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的API调用

        Args:
            request_data: 请求数据

        Returns:
            API响应数据

        Raises:
            RuntimeError: 所有重试都失败
        """
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🔄 UltraThink API调用尝试 {attempt + 1}/{self.config.max_retries}")

                # 发送请求
                async with self.session.post(
                    f"{self.config.api_base_url}/chat/completions",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()

                        # 提取内容
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            content = response_data['choices'][0]['message'].get('content', '')
                            return {
                                'content': content,
                                'model': response_data.get('model', self.config.model),
                                'usage': response_data.get('usage', {})
                            }
                        else:
                            raise RuntimeError(f"API响应格式异常: {response_data}")

                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"API请求失败: HTTP {response.status}, {error_text}")

            except Exception as e:
                last_exception = e
                logger.warning(f"⚠️ 第{attempt + 1}次尝试失败: {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        # 所有重试都失败
        error_msg = f"UltraThink API调用失败，已重试{self.config.max_retries}次: {last_exception}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    def _update_stats(self, response: LLMResponse):
        """更新使用统计

        Args:
            response: LLM响应对象
        """
        self.usage_stats['total_calls'] += 1
        self.usage_stats['total_tokens'] += response.token_count
        self.usage_stats['total_cost'] += response.cost_estimate

    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        return {
            'model': self.config.model,
            'api_base_url': self.config.api_base_url,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'timeout': self.config.timeout,
            'max_retries': self.config.max_retries
        }

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计

        Returns:
            使用统计信息
        """
        stats = self.usage_stats.copy()
        stats['avg_tokens_per_call'] = (
            stats['total_tokens'] / stats['total_calls']
            if stats['total_calls'] > 0 else 0
        )
        stats['avg_response_time'] = (
            sum(msg.response_time for msg in self.conversation_history if hasattr(msg, 'response_time')) /
            len(self.conversation_history) if self.conversation_history else 0
        )
        return stats

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史

        Returns:
            对话历史列表
        """
        return [asdict(msg) for msg in self.conversation_history]

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        logger.info("🧹 对话历史已清空")

    @asynccontextmanager
    async def scoped_call(self, prompt: str, context: Optional[str] = None):
        """作用域调用的上下文管理器

        Args:
            prompt: 用户提示
            context: 可选的上下文信息
        """
        try:
            response = await self.call_ultrathink(prompt, context)
            yield response
        except Exception as e:
            logger.error(f"❌ UltraThink作用域调用失败: {e}")
            raise

    async def test_connection(self) -> bool:
        """测试API连接

        Returns:
            连接是否正常
        """
        try:
            test_prompt = "请简单回复'连接正常'"
            response = await self.call_ultrathink(test_prompt)
            return bool(response.content)
        except Exception as e:
            logger.error(f"❌ 连接测试失败: {e}")
            return False

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            # 注意：这里不能直接调用async方法，只是标记需要清理
            logger.warning("⚠️ 检测到未正确关闭的HTTP会话，请使用async with语句或手动调用close()")


# 便利函数
async def create_ultrathink_integrator() -> UltraThinkLMIntegrator:
    """创建UltraThink集成器实例

    Returns:
        配置好的集成器实例
    """
    config = UltraThinkConfig()
    return UltraThinkLMIntegrator(config)


async def quick_ultrathink_call(prompt: str, context: Optional[str] = None) -> str:
    """快速调用UltraThink

    Args:
        prompt: 用户提示
        context: 可选的上下文信息

    Returns:
        模型响应内容
    """
    async with await create_ultrathink_integrator() as integrator:
        response = await integrator.call_ultrathink(prompt, context)
        return response.content


# 导出所有公共类和函数
__all__ = [
    'UltraThinkConfig',
    'LLMMessage',
    'LLMResponse',
    'UltraThinkLMIntegrator',
    'create_ultrathink_integrator',
    'quick_ultrathink_call'
]