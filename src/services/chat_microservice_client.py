"""
聊天微服务客户端

提供与聊天微服务(45.152.65.130:20252)通信的HTTP客户端功能。
实现聊天流式响应和消息历史获取功能。

核心功能：
1. 流式聊天：POST /chat/stream
2. 获取消息历史：GET /api/sessions/{session_id}/messages
3. 健康检查：GET /health
4. 响应格式转换：微服务格式 → 本地格式

设计原则：
1. 异步支持：支持流式响应
2. 错误处理：详细的错误信息和状态码映射
3. 超时控制：防止微服务响应缓慢影响主服务
4. 类型安全：严格的数据验证

作者：TaKeKe团队
版本：1.0.0
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from src.api.config import config, get_chat_service_url, get_chat_service_timeout


class ChatMicroserviceError(Exception):
    """聊天微服务调用异常"""

    def __init__(self, message: str, status_code: int = 500, original_error: Optional[Exception] = None):
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(self.message)


class ChatMicroserviceClient:
    """
    聊天微服务客户端

    提供与聊天微服务通信的完整HTTP客户端功能，包括：
    - 异步HTTP调用
    - 流式响应处理
    - 消息历史获取
    - 错误处理和重试
    """

    def __init__(self):
        """初始化客户端（增强版：连接池）"""
        self.base_url = get_chat_service_url()
        self.timeout = int(get_chat_service_timeout())
        self.logger = logging.getLogger(__name__)

        # 创建HTTP客户端（增强：连接池）
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 健康状态
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"聊天微服务健康检查失败: {e}")
            return False

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取会话消息历史

        Args:
            session_id: 会话ID
            limit: 每页消息数量
            offset: 分页偏移量

        Returns:
            Dict[str, Any]: 消息历史数据

        Raises:
            ChatMicroserviceError: API调用失败时抛出
        """
        try:
            url = f"{self.base_url}/api/sessions/{session_id}/messages"
            params = {"limit": limit, "offset": offset}

            self.logger.info(f"获取会话消息历史: session_id={session_id}")
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"获取消息历史成功: session_id={session_id}, 消息数量={len(data.get('data', {}).get('messages', []))}")
                return data
            else:
                error_msg = f"获取消息历史失败: HTTP {response.status_code}"
                self.logger.error(error_msg)
                raise ChatMicroserviceError(error_msg, response.status_code)

        except httpx.RequestError as e:
            error_msg = f"网络请求失败: {e}"
            self.logger.error(error_msg)
            raise ChatMicroserviceError(error_msg, 500, e)
        except Exception as e:
            error_msg = f"获取消息历史异常: {e}"
            self.logger.error(error_msg)
            raise ChatMicroserviceError(error_msg, 500, e)

    async def stream_chat(
        self,
        session_id: str,
        message: str
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天

        Args:
            session_id: 会话ID
            message: 用户消息

        Yields:
            str: AI响应的token流

        Raises:
            ChatMicroserviceError: API调用失败时抛出
        """
        try:
            url = f"{self.base_url}/chat/stream"
            payload = {
                "session_id": session_id,
                "message": message
            }

            self.logger.info(f"开始流式聊天: session_id={session_id}, message={message[:50]}...")

            # 使用流式请求
            async with self.client.stream(
                "POST",
                url,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_msg = f"流式聊天失败: HTTP {response.status_code}"
                    self.logger.error(error_msg)
                    raise ChatMicroserviceError(error_msg, response.status_code)

                # 逐行读取流式响应
                async for line in response.aiter_lines():
                    if line.strip():
                        # 处理SSE格式: data: {"type":"token","content":"我"}
                        if line.startswith('data: '):
                            json_str = line[6:]  # 去掉 'data: ' 前缀
                            try:
                                data = json.loads(json_str)
                                if isinstance(data, dict):
                                    if data.get('type') == 'token' and 'content' in data:
                                        # 提取token的content字段
                                        yield data['content']
                                    elif data.get('type') == 'done':
                                        # 流式结束，停止生成
                                        break
                            except json.JSONDecodeError:
                                # 如果不是JSON，直接返回字符串
                                yield json_str
                        else:
                            # 非SSE格式，直接返回
                            yield line

        except httpx.RequestError as e:
            error_msg = f"流式聊天网络请求失败: {e}"
            self.logger.error(error_msg)
            raise ChatMicroserviceError(error_msg, 500, e)
        except Exception as e:
            error_msg = f"流式聊天异常: {e}"
            self.logger.error(error_msg)
            raise ChatMicroserviceError(error_msg, 500, e)


# 单例实例
_chat_client_instance: Optional[ChatMicroserviceClient] = None


def get_chat_microservice_client() -> ChatMicroserviceClient:
    """
    获取聊天微服务客户端单例实例

    Returns:
        ChatMicroserviceClient: 客户端实例
    """
    global _chat_client_instance
    if _chat_client_instance is None:
        _chat_client_instance = ChatMicroserviceClient()
    return _chat_client_instance


async def close_chat_microservice_client():
    """关闭聊天微服务客户端"""
    global _chat_client_instance
    if _chat_client_instance is not None:
        await _chat_client_instance.close()
        _chat_client_instance = None