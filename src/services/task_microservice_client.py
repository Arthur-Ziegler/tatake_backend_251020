"""
Task微服务客户端

提供与Task微服务(http://45.152.65.130:20253)通信的HTTP客户端功能。
实现响应格式转换、错误处理和超时配置。

核心功能：
1. HTTP调用封装：call_task_service()
2. 响应格式转换：transform_response()
3. 错误处理：统一的异常处理机制
4. 超时配置：连接和读取超时设置
5. 9个核心接口支持：任务CRUD、Top3管理、完成按钮、专注状态、番茄钟计数

9个核心接口：
1. GET /tasks - 查询所有任务（前端过滤）
2. POST /tasks - 创建任务
3. DELETE /tasks/{task_id} - 删除任务
4. PUT /tasks/{task_id} - 修改任务
5. POST /tasks/special/top3 - 设置Top3（无积分消耗）
6. GET /tasks/special/top3/{date} - 查看Top3
7. POST /tasks/{task_id}/complete - 任务完成按钮（含奖励）
8. POST /tasks/focus-status - 发送专注状态
9. GET /tasks/pomodoro-count - 查看番茄钟计数

设计原则：
1. 代理模式：保持API路径完全不变
2. 格式转换：微服务格式 → 本地格式
3. 用户ID传递：在请求体中传递user_id
4. 错误处理：详细的错误信息和状态码映射
5. 超时控制：防止微服务响应缓慢影响主服务

作者：TaTake团队
版本：2.0.0（适配9个核心接口）
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
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url or getattr(config, 'task_service_url', 'http://45.152.65.130:20253')
        self.logger.info(f"Task微服务客户端初始化，base_url: {self.base_url}")
        self.timeout = httpx.Timeout(
            connect=5.0,  # 连接超时5秒
            read=30.0,    # 读取超时30秒
            write=10.0,   # 写入超时10秒
            pool=60.0     # 连接池超时60秒
        )

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

    def transform_response(self, microservice_response) -> Dict[str, Any]:
        """
        转换微服务响应格式为本地API格式

        微服务可能有多种响应格式：
        1. 标准格式：{"success": true, "message": "success", "data": {...}}
        2. 错误格式：{"success": false, "message": "接口不存在", "data": null}
        3. 数组格式（查询接口直接返回数组）：[{...}, {...}]

        转换后格式（code, message, data）：
        {
            "code": 200,
            "data": {...},
            "message": "success"
        }

        Args:
            microservice_response: 微服务响应（可能是字典或数组）

        Returns:
            Dict[str, Any]: 转换后的响应格式

        Raises:
            TaskMicroserviceError: 响应格式无效时抛出异常
        """
        try:
            # 检查响应类型
            if isinstance(microservice_response, dict):
                # 字典格式响应
                # 检查是否是标准微服务响应格式
                if "success" in microservice_response:
                    # 标准格式：{"success": true, "message": "success", "data": {...}}
                    success = microservice_response.get("success", False)
                    message = microservice_response.get("message", "success")
                    data = microservice_response.get("data", None)

                    if success:
                        # 成功响应
                        return {
                            "code": 200,
                            "data": data,
                            "message": message
                        }
                    else:
                        # 失败响应
                        error_code = microservice_response.get("code", 400)
                        return {
                            "code": error_code,
                            "data": None,
                            "message": message
                        }
                else:
                    # 其他字典格式，直接作为data处理
                    return {
                        "code": 200,
                        "data": microservice_response,
                        "message": "success"
                    }
            elif isinstance(microservice_response, list):
                # 数组格式响应（如查询接口直接返回数组）
                return {
                    "code": 200,
                    "data": microservice_response,
                    "message": "success"
                }
            else:
                raise ValueError(f"不支持的响应格式: {type(microservice_response)}")

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
        # 构建完整URL - 微服务对尾部斜杠敏感，必须去掉尾部斜杠
        normalized_path = path.rstrip('/')  # 移除尾部斜杠
        url = f"{self.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

        # 将user_id添加到请求体中（微服务期望的格式）
        request_data = data.copy() if data else {}
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            request_data["user_id"] = user_id

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

                # 记录响应状态和内容
                self.logger.debug(f"微服务响应状态: {response.status_code}")
                self.logger.debug(f"微服务响应头: {dict(response.headers)}")

                # 解析响应内容
                response_data = None
                try:
                    response_data = response.json()
                    self.logger.debug(f"微服务响应JSON: {response_data}")
                except Exception as e:
                    self.logger.error(f"解析响应JSON失败: {e}")
                    self.logger.error(f"原始响应内容: {response.text}")

                    # 检查是否是连接错误
                    if response.status_code == 0:
                        return {
                            "code": 503,
                            "data": None,
                            "message": "微服务不可用，请检查微服务状态"
                        }

                    # 如果无法解析JSON，检查状态码
                    if response.status_code >= 400:
                        return {
                            "code": response.status_code,
                            "data": None,
                            "message": f"微服务返回错误: HTTP {response.status_code}"
                        }

                    # 其他情况，构造基础错误响应
                    return {
                        "code": 500,
                        "data": None,
                        "message": f"微服务响应格式错误: {response.text[:100]}"
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
                transformed_response = self.transform_response(response_data)

                # 特殊处理：检查是否是"接口不存在"错误
                if (not transformed_response.get("success", True) and
                    "接口不存在" in transformed_response.get("message", "")):
                    return {
                        "code": 501,
                        "data": None,
                        "message": f"功能暂未实现：{path} 接口尚未在微服务中实现"
                    }

                return transformed_response

        except httpx.TimeoutException as e:
            self.logger.error(f"微服务调用超时: {url}")
            raise TaskMicroserviceError(
                "微服务调用超时，请稍后重试",
                status_code=504,
                original_error=e
            )
        except httpx.ConnectError as e:
            self.logger.error(f"微服务连接失败: {url}")
            # 不抛出异常，而是返回错误响应
            return {
                "code": 503,
                "data": None,
                "message": f"任务微服务不可用，URL: {self.base_url}，请检查微服务状态"
            }
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


# ============================
# 9个核心接口的便捷方法
# ============================

async def get_all_tasks(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    1. 查询所有任务（前端过滤）

    Args:
        user_id (str): 用户ID
        page (int): 页码
        page_size (int): 每页大小
        status_filter (str): 状态过滤

    Returns:
        Dict[str, Any]: 任务列表响应
    """
    # 使用POST /tasks/query端点查询任务
    # 注意：call_task_service会自动添加user_id，所以这里不需要重复添加
    data = {
        "page": page,
        "page_size": page_size
    }
    if status_filter:
        data["status"] = status_filter

    return await call_task_service("POST", "tasks/query", user_id, data=data)

async def create_task(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    2. 创建任务

    Args:
        user_id (str): 用户ID
        title (str): 任务标题
        description (str): 任务描述
        priority (str): 优先级
        due_date (str): 截止日期

    Returns:
        Dict[str, Any]: 创建的任务响应
    """
    data = {
        "title": title,
        "description": description,
        "priority": priority,
        "due_date": due_date
    }
    return await call_task_service("POST", "tasks", user_id, data=data)

async def delete_task(
    user_id: str,
    task_id: str
) -> Dict[str, Any]:
    """
    3. 删除任务

    Args:
        user_id (str): 用户ID
        task_id (str): 任务ID

    Returns:
        Dict[str, Any]: 删除结果响应
    """
    return await call_task_service("DELETE", f"tasks/{task_id}", user_id)

async def update_task(
    user_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    4. 修改任务

    Args:
        user_id (str): 用户ID
        task_id (str): 任务ID
        title (str): 任务标题
        description (str): 任务描述
        priority (str): 优先级
        status (str): 状态
        due_date (str): 截止日期

    Returns:
        Dict[str, Any]: 更新的任务响应
    """
    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if priority is not None:
        data["priority"] = priority
    if status is not None:
        data["status"] = status
    if due_date is not None:
        data["due_date"] = due_date

    return await call_task_service("PUT", f"tasks/{task_id}", user_id, data=data)

async def set_top3(
    user_id: str,
    date: str,
    task_ids: list
) -> Dict[str, Any]:
    """
    5. 设置Top3（无积分消耗）

    Args:
        user_id (str): 用户ID
        date (str): 日期 YYYY-MM-DD
        task_ids (list): 任务ID列表

    Returns:
        Dict[str, Any]: Top3设置结果
    """
    data = {
        "date": date,
        "task_ids": task_ids
    }
    return await call_task_service("POST", "tasks/top3", user_id, data=data)

async def get_top3(
    user_id: str,
    date: str
) -> Dict[str, Any]:
    """
    6. 查看Top3

    Args:
        user_id (str): 用户ID
        date (str): 日期 YYYY-MM-DD

    Returns:
        Dict[str, Any]: Top3查询结果
    """
    data = {
        "date": date
    }
    return await call_task_service("POST", "tasks/top3/query", user_id, data=data)

async def complete_task(
    user_id: str,
    task_id: str,
    completion_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    7. 任务完成按钮（含奖励）

    Args:
        user_id (str): 用户ID
        task_id (str): 任务ID
        completion_data (Dict): 完成数据

    Returns:
        Dict[str, Any]: 完成结果和奖励信息
    """
    data = completion_data or {}
    return await call_task_service("POST", f"tasks/{task_id}/complete", user_id, data=data)

async def send_focus_status(
    user_id: str,
    focus_status: str,
    task_id: Optional[str] = None,
    duration_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    8. 发送专注状态

    Args:
        user_id (str): 用户ID
        focus_status (str): 专注状态 (start, break, complete, pause)
        task_id (str): 相关任务ID
        duration_minutes (int): 专注时长（分钟）

    Returns:
        Dict[str, Any]: 专注状态记录结果
    """
    data = {
        "focus_status": focus_status,
        "task_id": task_id,
        "duration_minutes": duration_minutes
    }
    return await call_task_service("POST", "tasks/focus-status", user_id, data=data)

async def get_pomodoro_count(
    user_id: str,
    date_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    9. 查看番茄钟计数

    Args:
        user_id (str): 用户ID
        date_filter (str): 日期过滤 (today, week, month)

    Returns:
        Dict[str, Any]: 番茄钟统计数据
    """
    params = {}
    if date_filter:
        params["date_filter"] = date_filter

    return await call_task_service("GET", "tasks/pomodoro-count", user_id, params=params)


# 便捷函数（保持向后兼容）
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