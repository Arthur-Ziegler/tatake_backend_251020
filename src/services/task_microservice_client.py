"""
Task微服务客户端

提供与Task微服务(localhost:20252)通信的HTTP客户端功能。
实现响应格式转换、错误处理和超时配置。

核心功能：
1. HTTP调用封装：call_task_service()
2. 响应格式转换：transform_response()
3. 错误处理：统一的异常处理机制
4. 超时配置：连接和读取超时设置

设计原则：
1. 代理模式：保持API路径完全不变
2. 格式转换：微服务格式 → 本地格式
3. 错误处理：详细的错误信息和状态码映射
4. 超时控制：防止微服务响应缓慢影响主服务

作者：TaKeKe团队
版本：1.0.0（Task微服务迁移）
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from src.api.config import config


class TaskMicroserviceError(Exception):
    """Task微服务调用异常"""

    def __init__(self, message: str, status_code: int = 500, original_error: Optional[Exception] = None):
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(self.message)


class TaskMicroserviceClient:
    """
    Task微服务客户端

    提供与Task微服务通信的完整HTTP客户端功能，包括：
    - 异步HTTP调用
    - 响应格式转换
    - 错误处理和重试机制
    - 超时配置
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化微服务客户端

        Args:
            base_url (str): 微服务基础URL，默认从环境变量读取
        """
        self.base_url = base_url or getattr(config, 'task_service_url', 'http://127.0.0.1:20252/api/v1')
        self.timeout = httpx.Timeout(
            connect=5.0,  # 连接超时5秒
            read=30.0,    # 读取超时30秒
            write=10.0,   # 写入超时10秒
            pool=60.0     # 连接池超时60秒
        )
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> Dict[str, str]:
        """
        获取HTTP请求头

        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TaKeKe-Backend/1.0.0"
        }

    def transform_response(self, microservice_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换微服务响应格式为本地API格式

        微服务格式：
        {
            "success": true,
            "data": {...}
        }

        转换后格式：
        {
            "code": 200,
            "data": {...},
            "message": "success"
        }

        Args:
            microservice_response (Dict[str, Any]): 微服务响应

        Returns:
            Dict[str, Any]: 转换后的响应格式

        Raises:
            TaskMicroserviceError: 响应格式无效时抛出异常
        """
        try:
            # 验证响应格式
            if not isinstance(microservice_response, dict):
                raise ValueError("响应必须是字典格式")

            success = microservice_response.get("success", False)
            data = microservice_response.get("data", None)

            if success:
                # 成功响应
                return {
                    "code": 200,
                    "data": data,
                    "message": "success"
                }
            else:
                # 失败响应，提取错误信息
                error_message = microservice_response.get("message", "操作失败")
                error_code = microservice_response.get("code", 400)

                return {
                    "code": error_code,
                    "data": None,
                    "message": error_message
                }

        except Exception as e:
            self.logger.error(f"响应格式转换失败: {e}")
            raise TaskMicroserviceError(
                f"响应格式转换失败: {str(e)}",
                status_code=500,
                original_error=e
            )

    def map_error_status(self, http_status: int, error_content: Dict[str, Any]) -> int:
        """
        将HTTP状态码映射为业务错误码

        Args:
            http_status (int): HTTP状态码
            error_content (Dict[str, Any]): 错误响应内容

        Returns:
            int: 业务错误码
        """
        # 根据HTTP状态码和错误内容映射业务错误码
        if http_status == 400:
            return 400  # 请求参数错误
        elif http_status == 401:
            return 401  # 未认证
        elif http_status == 403:
            return 403  # 无权限
        elif http_status == 404:
            return 404  # 资源不存在
        elif http_status == 409:
            return 409  # 资源冲突
        elif http_status == 422:
            return 422  # 数据验证失败
        elif 500 <= http_status < 600:
            return 500  # 服务器内部错误
        else:
            return http_status

    async def call_task_service(
        self,
        method: str,
        path: str,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用Task微服务API

        Args:
            method (str): HTTP方法 (GET, POST, PUT, DELETE)
            path (str): API路径，不包含基础URL
            user_id (str): 用户ID
            data (Dict[str, Any], optional): 请求体数据
            params (Dict[str, Any], optional): 查询参数

        Returns:
            Dict[str, Any]: 转换后的响应数据

        Raises:
            TaskMicroserviceError: 调用失败时抛出异常
        """
        # 构建完整URL
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

        # 将user_id添加到请求体中（微服务期望的格式）
        request_data = data.copy() if data else {}
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            request_data["user_id"] = user_id

        # 添加微服务必需但原API不需要的字段
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            if "service_ids" not in request_data:
                request_data["service_ids"] = []
            if "priority" not in request_data:
                request_data["priority"] = "medium"
            if "tags" not in request_data:
                request_data["tags"] = []

        # 构建查询参数，确保user_id在GET请求时传递
        query_params = params.copy() if params else {}
        if method.upper() == 'GET':
            query_params["user_id"] = user_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                self.logger.debug(f"调用微服务: {method} {url}, params={query_params}")

                # 发送HTTP请求
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=request_data,
                    params=query_params,
                    headers=self._get_headers()
                )

                self.logger.debug(f"微服务响应: status={response.status_code}")

                # 解析响应内容
                try:
                    response_data = response.json()
                except Exception as e:
                    self.logger.error(f"解析响应JSON失败: {e}")
                    # 如果无法解析JSON，构建基础错误响应
                    response_data = {
                        "success": False,
                        "message": f"响应解析失败: {response.text}",
                        "code": response.status_code
                    }

                # 检查HTTP状态码
                if response.status_code >= 400:
                    error_code = self.map_error_status(response.status_code, response_data)
                    error_message = response_data.get("message", f"HTTP {response.status_code}")

                    return {
                        "code": error_code,
                        "data": None,
                        "message": error_message
                    }

                # 转换响应格式
                return self.transform_response(response_data)

        except httpx.TimeoutException as e:
            self.logger.error(f"微服务调用超时: {url}")
            raise TaskMicroserviceError(
                "微服务调用超时，请稍后重试",
                status_code=504,
                original_error=e
            )
        except httpx.ConnectError as e:
            self.logger.error(f"微服务连接失败: {url}")
            raise TaskMicroserviceError(
                "微服务不可用，请稍后重试",
                status_code=503,
                original_error=e
            )
        except Exception as e:
            self.logger.error(f"微服务调用异常: {url}, error={e}")
            raise TaskMicroserviceError(
                f"微服务调用失败: {str(e)}",
                status_code=500,
                original_error=e
            )

    async def health_check(self) -> bool:
        """
        检查微服务健康状态

        Returns:
            bool: 微服务是否可用
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers()
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"微服务健康检查失败: {e}")
            return False


# 全局客户端实例
_task_microservice_client: Optional[TaskMicroserviceClient] = None


def get_task_microservice_client() -> TaskMicroserviceClient:
    """
    获取Task微服务客户端实例（单例模式）

    Returns:
        TaskMicroserviceClient: 客户端实例
    """
    global _task_microservice_client
    if _task_microservice_client is None:
        _task_microservice_client = TaskMicroserviceClient()
    return _task_microservice_client


# 便捷函数
async def call_task_service(
    method: str,
    path: str,
    user_id: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    便捷函数：调用Task微服务

    Args:
        method (str): HTTP方法
        path (str): API路径
        user_id (str): 用户ID
        data (Dict[str, Any], optional): 请求体数据
        params (Dict[str, Any], optional): 查询参数

    Returns:
        Dict[str, Any]: 响应数据
    """
    client = get_task_microservice_client()
    return await client.call_task_service(method, path, user_id, data, params)