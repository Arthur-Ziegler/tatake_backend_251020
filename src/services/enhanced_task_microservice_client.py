"""
增强版Task微服务客户端

提供与Task微服务(http://45.152.65.130:20253)通信的完整HTTP客户端功能。
实现智能路径映射、UUID验证、连接池管理、重试机制等高级功能。

核心功能：
1. 智能路径映射：适配客户端API路径与微服务RESTful路径的差异
2. UUID格式验证：确保所有ID参数符合UUID标准
3. 直接响应透传：微服务响应格式已符合标准，无需转换
4. 连接池管理：优化网络性能和资源使用
5. 增强错误处理：详细的网络错误处理和降级策略
6. 重试机制：智能重试可恢复的错误

路径映射策略：
- POST /tasks/query → GET /api/v1/tasks/{user_id}
- PUT /tasks/{task_id} → PUT /api/v1/tasks/{user_id}/{task_id}
- DELETE /tasks/{task_id} → DELETE /api/v1/tasks/{user_id}/{task_id}
- POST /tasks/{task_id}/complete → POST /api/v1/tasks/{user_id}/{task_id}/complete
- POST /tasks/top3/query → GET /api/v1/tasks/top3/{user_id}/{date}
- POST /tasks/focus-status → POST /api/v1/focus/sessions
- GET /tasks/pomodoro-count → GET /api/v1/pomodoros/count

作者：TaTakeKe团队
版本：3.0.0（增强版）
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Tuple, Set
from uuid import UUID

import httpx
from pydantic import BaseModel

from src.api.config import config


class TaskMicroserviceError(Exception):
    """Task微服务调用异常"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        original_error: Optional[Exception] = None,
        is_recoverable: bool = False
    ):
        self.message = message
        self.status_code = status_code
        self.original_error = original_error
        self.is_recoverable = is_recoverable
        super().__init__(self.message)


class UUIDValidator:
    """UUID格式验证器"""

    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """
        验证用户ID格式

        Args:
            user_id (str): 用户ID

        Returns:
            str: 验证后的用户ID

        Raises:
            ValueError: 用户ID格式无效
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")

        try:
            UUID(user_id)
            return user_id
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {user_id}")

    @staticmethod
    def validate_task_id(task_id: str) -> str:
        """
        验证任务ID格式

        Args:
            task_id (str): 任务ID

        Returns:
            str: 验证后的任务ID

        Raises:
            ValueError: 任务ID格式无效
        """
        if not task_id:
            raise ValueError("task_id cannot be empty")

        try:
            UUID(task_id)
            return task_id
        except ValueError:
            raise ValueError(f"Invalid UUID format for task_id: {task_id}")


class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self, client_config: Optional['EnhancedTaskMicroserviceClient'] = None):
        """初始化连接池管理器"""
        self.logger = logging.getLogger(__name__)

        # 从客户端配置读取参数，如果没有配置则使用默认值
        if client_config:
            connect_timeout = getattr(client_config, 'connect_timeout', 5.0)
            read_timeout = getattr(client_config, 'read_timeout', 30.0)
            write_timeout = getattr(client_config, 'write_timeout', 10.0)
            pool_timeout = getattr(client_config, 'pool_timeout', 60.0)
            max_keepalive = getattr(client_config, 'max_keepalive_connections', 20)
            max_connections = getattr(client_config, 'max_connections', 100)
        else:
            # 使用默认配置
            connect_timeout = 5.0
            read_timeout = 30.0
            write_timeout = 10.0
            pool_timeout = 60.0
            max_keepalive = 20
            max_connections = 100

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=connect_timeout,   # 连接超时
                read=read_timeout,         # 读取超时
                write=write_timeout,       # 写入超时
                pool=pool_timeout          # 连接池超时
            ),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive,  # 最大保持连接数
                max_connections=max_connections           # 最大连接数
            )
        )
        self.logger.info(f"连接池管理器初始化完成，超时配置: connect={connect_timeout}s, read={read_timeout}s, write={write_timeout}s, pool={pool_timeout}s")
        self.logger.info(f"连接池限制: max_keepalive={max_keepalive}, max_connections={max_connections}")

    async def close(self):
        """关闭连接池"""
        await self.client.aclose()
        self.logger.info("连接池已关闭")

    def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端实例"""
        return self.client


class ErrorHandlingStrategy:
    """错误处理策略"""

    @staticmethod
    def handle_network_error(error: Exception) -> TaskMicroserviceError:
        """
        处理网络错误

        Args:
            error (Exception): 原始错误

        Returns:
            TaskMicroserviceError: 处理后的错误
        """
        if isinstance(error, httpx.ConnectError):
            return TaskMicroserviceError(
                "Task微服务连接失败，请稍后重试",
                status_code=503,
                original_error=error,
                is_recoverable=True
            )
        elif isinstance(error, httpx.TimeoutException):
            return TaskMicroserviceError(
                "Task微服务响应超时，请稍后重试",
                status_code=504,
                original_error=error,
                is_recoverable=True
            )
        else:
            return TaskMicroserviceError(
                f"网络异常: {str(error)}",
                status_code=500,
                original_error=error,
                is_recoverable=True
            )

    @staticmethod
    def map_http_status(http_status: int, response_data: Dict[str, Any]) -> int:
        """
        映射HTTP状态码到业务错误码

        Args:
            http_status (int): HTTP状态码
            response_data (Dict[str, Any]): 响应数据

        Returns:
            int: 业务错误码
        """
        # 如果响应数据中已有错误码，直接使用
        if isinstance(response_data, dict) and "code" in response_data:
            return response_data["code"]

        # 否则根据HTTP状态码映射
        status_mapping = {
            400: 400,  # 请求参数错误
            401: 401,  # 未认证
            403: 403,  # 无权限
            404: 404,  # 资源不存在
            409: 409,  # 资源冲突
            422: 422,  # 数据验证失败
        }

        return status_mapping.get(http_status, http_status)


class EnhancedTaskMicroserviceClient:
    """
    增强版Task微服务客户端

    提供与Task微服务通信的完整HTTP客户端功能，包括：
    - 智能路径映射和重写
    - 严格的UUID格式验证
    - 连接池管理和复用
    - 增强的错误处理和重试机制
    - 直接响应透传（无需格式转换）
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化增强版微服务客户端

        Args:
            base_url (str): 微服务基础URL，默认从环境变量读取
        """
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url or getattr(config, 'task_service_url', 'http://45.152.65.130:20253/api/v1')

        # 强制使用正确的Task微服务URL，忽略环境变量
        if '127.0.0.1:20252' in self.base_url:
            self.base_url = 'http://45.152.65.130:20253/api/v1'
            self.logger.warning(f"检测到错误的本地微服务URL，强制使用正确URL: {self.base_url}")

        # 确保base_url包含/api/v1后缀
        if not self.base_url.endswith('/api/v1'):
            # 移除末尾的斜杠，然后添加/api/v1
            self.base_url = self.base_url.rstrip('/') + '/api/v1'
            self.logger.warning(f"base_url缺少/api/v1后缀，已自动补全: {self.base_url}")

        self.logger.info(f"增强版Task微服务客户端初始化，base_url: {self.base_url}")
        self.logger.info(f"调试信息：强制URL覆盖已启用，将忽略错误的本地环境变量")

        # 初始化组件
        self.path_mappings = self._build_path_mappings()
        self.connection_pool = ConnectionPoolManager(self)
        self.error_strategy = ErrorHandlingStrategy()

        # 从配置读取重试配置
        self.max_retries = getattr(config, 'task_service_max_retries', 3)
        retry_delays_str = getattr(config, 'task_service_retry_delays', '1.0,2.0,4.0')
        self.retry_delays = [float(delay.strip()) for delay in retry_delays_str.split(',')]

        # 超时配置
        self.connect_timeout = getattr(config, 'task_service_connect_timeout', 5.0)
        self.read_timeout = getattr(config, 'task_service_read_timeout', 30.0)
        self.write_timeout = getattr(config, 'task_service_write_timeout', 10.0)
        self.pool_timeout = getattr(config, 'task_service_pool_timeout', 60.0)

        # 连接池配置
        self.max_keepalive_connections = getattr(config, 'task_service_max_keepalive_connections', 20)
        self.max_connections = getattr(config, 'task_service_max_connections', 100)

        # 健康检查缓存
        health_check_interval = getattr(config, 'task_service_health_check_interval', 60)
        self._health_status: Dict[str, Any] = {
            "status": "unknown",
            "last_check": 0,
            "cache_ttl": health_check_interval
        }

    def _build_path_mappings(self) -> Dict[Tuple[str, str], Tuple[str, str]]:
        """
        构建路径映射表

        Returns:
            Dict[Tuple[str, str], Tuple[str, str]]: 路径映射表
        """
        return {
            # 查询任务：POST query → GET with user_id
            ("POST", "tasks/query"): ("GET", "tasks/{user_id}"),

            # 单个任务CRUD：需要user_id路径参数
            ("PUT", "tasks/{task_id}"): ("PUT", "tasks/{user_id}/{task_id}"),
            ("DELETE", "tasks/{task_id}"): ("DELETE", "tasks/{user_id}/{task_id}"),
            ("POST", "tasks/{task_id}/complete"): ("POST", "tasks/{user_id}/{task_id}/complete"),

            # Top3管理
            ("POST", "tasks/top3/query"): ("GET", "tasks/top3/{user_id}/{date}"),

            # 专注和番茄钟
            ("POST", "tasks/focus-status"): ("POST", "focus/sessions"),
            ("GET", "tasks/pomodoro-count"): ("GET", "pomodoros/count")
        }

    def rewrite_path_and_method(self, method: str, original_path: str, user_id: str, **kwargs) -> tuple[str, str]:
        """
        根据映射规则重写API路径和方法

        Args:
            method (str): HTTP方法
            original_path (str): 原始路径
            user_id (str): 用户ID
            **kwargs: 其他路径参数

        Returns:
            tuple[str, str]: (新方法, 重写后的路径)

        Raises:
            ValueError: 缺少必需参数时抛出异常
        """
        key = (method.upper(), original_path)

        if key not in self.path_mappings:
            return method.upper(), original_path  # 无需映射

        new_method, new_path_template = self.path_mappings[key]

        # 构建新路径
        if "{task_id}" in new_path_template:
            task_id = kwargs.get("task_id")
            if not task_id:
                raise ValueError("task_id is required for this operation")
            new_path = new_path_template.format(user_id=user_id, task_id=task_id)
            return new_method, new_path

        elif "{date}" in new_path_template:
            date = kwargs.get("date")
            if not date:
                raise ValueError("date is required for this operation")
            new_path = new_path_template.format(user_id=user_id, date=date)
            return new_method, new_path

        elif "{user_id}" in new_path_template:
            new_path = new_path_template.format(user_id=user_id)
            return new_method, new_path

        else:
            return new_method, new_path_template

    def _get_headers(self) -> Dict[str, str]:
        """
        获取HTTP请求头

        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TaKeKe-Backend/3.0.0"
        }

    async def _check_health(self) -> bool:
        """
        检查微服务健康状态

        Returns:
            bool: 微服务是否健康
        """
        current_time = time.time()

        # 检查缓存状态
        if (self._health_status["status"] == "healthy" and
            current_time - self._health_status["last_check"] < self._health_status["cache_ttl"]):
            return True

        try:
            client = self.connection_pool.get_client()
            response = await client.get(
                f"{self.base_url.rstrip('/')}/health",
                headers=self._get_headers()
            )

            is_healthy = response.status_code == 200
            self._health_status = {
                "status": "healthy" if is_healthy else "unhealthy",
                "last_check": current_time,
                "cache_ttl": self._health_status["cache_ttl"]
            }

            self.logger.debug(f"微服务健康检查结果: {is_healthy}")
            return is_healthy

        except Exception as e:
            self._health_status = {
                "status": "unhealthy",
                "last_check": current_time,
                "cache_ttl": self._health_status["cache_ttl"]
            }
            self.logger.warning(f"微服务健康检查失败: {e}")
            return False

    async def _execute_request_with_retry(
        self,
        method: str,
        url: str,
        request_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        执行带重试机制的HTTP请求

        Args:
            method (str): HTTP方法
            url (str): 请求URL
            request_data (Dict[str, Any]): 请求体数据
            params (Dict[str, Any]): 查询参数
            headers (Dict[str, str]): 请求头

        Returns:
            httpx.Response: HTTP响应

        Raises:
            TaskMicroserviceError: 请求失败时抛出异常
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                client = self.connection_pool.get_client()
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=request_data,
                    params=params,
                    headers=headers or self._get_headers()
                )

                # 检查是否是可重试的错误
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=None,
                        response=response
                    )

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    self.logger.warning(f"请求失败，{delay}秒后重试 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                    await asyncio.sleep(delay)
                else:
                    break

            except httpx.HTTPStatusError as e:
                # HTTP状态码错误不重试
                raise e

        # 重试次数用尽，抛出最后一个错误
        if last_error:
            raise self.error_strategy.handle_network_error(last_error)
        else:
            raise TaskMicroserviceError("请求重试次数用尽", status_code=500)

    async def call_microservice(
        self,
        method: str,
        path: str,
        user_id: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用微服务API

        Args:
            method (str): HTTP方法 (GET, POST, PUT, DELETE)
            path (str): API路径，不包含基础URL
            user_id (str): 用户ID
            data (Dict[str, Any], optional): 请求体数据
            params (Dict[str, Any], optional): 查询参数
            **kwargs: 其他路径参数

        Returns:
            Dict[str, Any]: 微服务响应数据

        Raises:
            TaskMicroserviceError: 调用失败时抛出异常
        """
        print(f"🎯 CALL_MICROSERVICE 被调用: method={method}, path={path}, user_id={user_id}")
        print(f"🔍 即将验证UUID格式...")

        # 1. 验证UUID格式
        try:
            validated_user_id = UUIDValidator.validate_user_id(user_id)
            print(f"✅ UUID验证成功: {validated_user_id}")
        except Exception as e:
            print(f"❌ UUID验证失败: {e}")
            raise

        # 2. 重写路径和方法
        try:
            print(f"🔄 开始路径重写和方法映射...")
            new_method, new_path = self.rewrite_path_and_method(method, path, validated_user_id, **kwargs)
            full_url = f"{self.base_url.rstrip('/')}/{new_path.lstrip('/')}"
            print(f"✅ 路径重写完成: {method} {path} -> {new_method} {new_path}")
            print(f"🔗 完整URL: {full_url}")
        except Exception as e:
            print(f"❌ 路径重写失败: {e}")
            raise

        # 3. 准备请求参数
        request_data = data.copy() if data else {}
        if new_method in ["POST", "PUT", "PATCH"]:
            request_data["user_id"] = validated_user_id

        # 4. 查询参数处理
        query_params = params.copy() if params else {}
        if new_method == "GET" and "user_id" not in query_params:
            query_params["user_id"] = validated_user_id

        self.logger.info(f"调用微服务: {new_method} {full_url}")
        self.logger.info(f"调试信息：原始方法={method} -> 新方法={new_method}")
        self.logger.info(f"调试信息：原始路径={path} -> 重写后路径={new_path}")
        self.logger.info(f"调试信息：请求数据={request_data}, 查询参数={query_params}")

        try:
            # 5. 执行HTTP请求（带重试）
            response = await self._execute_request_with_retry(
                method=new_method,
                url=full_url,
                request_data=request_data,
                params=query_params
            )

            self.logger.debug(f"微服务响应状态: {response.status_code}")

            # 6. 解析响应数据
            try:
                response_data = response.json()
                self.logger.debug(f"微服务响应数据: {response_data}")
            except Exception as e:
                self.logger.error(f"解析响应JSON失败: {e}")
                self.logger.error(f"原始响应内容: {response.text}")

                # 无法解析JSON时的错误处理
                if response.status_code >= 400:
                    error_code = self.error_strategy.map_http_status(response.status_code, {})
                    return {
                        "code": error_code,
                        "success": False,
                        "message": f"微服务返回错误: HTTP {response.status_code}",
                        "data": None
                    }

                return {
                    "code": 500,
                    "success": False,
                    "message": f"微服务响应格式错误: {response.text[:100]}",
                    "data": None
                }

            # 7. 检查HTTP状态码
            if response.status_code >= 400:
                error_code = self.error_strategy.map_http_status(response.status_code, response_data)
                error_message = response_data.get("message", f"HTTP {response.status_code}")

                return {
                    "code": error_code,
                    "success": False,
                    "message": error_message,
                    "data": response_data.get("data")
                }

            # 8. 直接返回微服务响应（无需格式转换）
            if isinstance(response_data, dict):
                # 确保响应包含必要的字段
                if "success" not in response_data:
                    response_data["success"] = response_data.get("code") == 200
                if "code" not in response_data:
                    response_data["code"] = 200 if response_data.get("success") else 500
                if "message" not in response_data:
                    response_data["message"] = "success" if response_data.get("success") else "error"

            return response_data

        except Exception as e:
            self.logger.error(f"微服务调用异常: {full_url}, error={e}")
            if isinstance(e, TaskMicroserviceError):
                raise
            else:
                raise self.error_strategy.handle_network_error(e)

    async def health_check(self) -> bool:
        """
        检查微服务健康状态

        Returns:
            bool: 微服务是否可用
        """
        return await self._check_health()

    async def close(self):
        """
        关闭客户端连接池
        """
        await self.connection_pool.close()
        self.logger.info("增强版Task微服务客户端已关闭")


# 全局客户端实例
_enhanced_task_microservice_client: Optional[EnhancedTaskMicroserviceClient] = None


def get_enhanced_task_microservice_client() -> EnhancedTaskMicroserviceClient:
    """
    获取增强版Task微服务客户端实例（单例模式）

    Returns:
        EnhancedTaskMicroserviceClient: 客户端实例
    """
    global _enhanced_task_microservice_client
    if _enhanced_task_microservice_client is None:
        _enhanced_task_microservice_client = EnhancedTaskMicroserviceClient()
    return _enhanced_task_microservice_client