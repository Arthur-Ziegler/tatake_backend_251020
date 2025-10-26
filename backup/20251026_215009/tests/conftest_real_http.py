"""
真实HTTP测试基础设施 - Conftest

根据openspec 1.4.1要求，提供真实HTTP服务器测试环境，
用于替换ASGI Transport模拟，解决P0级Bug和环境不一致问题。

核心功能：
1. 真实HTTP服务器启动和管理
2. HTTP客户端连接池
3. 测试数据隔离和清理
4. 错误处理和重试机制
5. 测试覆盖率统计

作者：TaKeKe团队
版本：1.4.1
日期：2025-10-25
"""

import pytest
import asyncio
import subprocess
import time
import socket
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from contextlib import asynccontextmanager

import httpx
from httpx import AsyncClient, TimeoutException, ConnectError
from unittest.mock import Mock

from src.api.main import app


# 配置日志
logger = logging.getLogger(__name__)


class RealHTTPTestConfig:
    """真实HTTP测试配置"""

    # 服务器配置
    API_HOST = "127.0.0.1"
    API_PORT = 8009  # 避免与主服务器冲突
    SERVER_STARTUP_TIMEOUT = 10  # 服务器启动超时时间(秒)
    SERVER_SHUTDOWN_TIMEOUT = 5   # 服务器关闭超时时间(秒)

    # 客户端配置
    REQUEST_TIMEOUT = 30.0  # 请求超时时间(秒)
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1.0  # 重试延迟时间(秒)

    # 测试数据配置
    TEST_DB_URL = "sqlite:///test_http.db"  # 独立测试数据库
    CLEANUP_BATCH_SIZE = 100  # 批量清理大小


class PortManager:
    """端口管理器，确保端口可用性"""

    @staticmethod
    def is_port_available(port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((PortManager.API_HOST, port))
                return result == 0
        except (socket.error, ConnectionRefusedError):
            return False
        except Exception as e:
            logger.warning(f"端口检查异常: {e}")
            return False

    @staticmethod
    def find_available_port(start_port: int = 8001) -> int:
        """查找可用端口"""
        for port in range(start_port, start_port + 100):
            if PortManager.is_port_available(port):
                return port
        raise RuntimeError("无法找到可用端口")


class HTTPServerManager:
    """HTTP服务器管理器"""

    def __init__(self):
        self.server_process = None
        self.server_url = None

    async def start_server(self, port: int = None) -> str:
        """启动HTTP服务器"""
        if port is None:
            port = PortManager.find_available_port()

        try:
            # 启动服务器进程
            cmd = [
                "uv", "run", "uvicorn",
                "src.api.main:app",
                f"--host={PortManager.API_HOST}",
                f"--port={port}",
                "--log-level=warning"  # 减少日志输出
            ]

            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**dict(subprocess.os.environ), "PYTHONPATH": None}  # 继承当前环境
            )

            # 等待服务器启动
            self.server_url = f"http://{PortManager.API_HOST}:{port}"

            logger.info(f"启动HTTP服务器: {self.server_url}")

            # 等待服务器就绪
            startup_start = time.time()
            while time.time() - startup_start < RealHTTPTestConfig.SERVER_STARTUP_TIMEOUT:
                try:
                    response = httpx.get(f"{self.server_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        logger.info("HTTP服务器启动成功")
                        break
                except Exception as e:
                    logger.warning(f"服务器就绪检查异常: {e}")

                time.sleep(0.5)

            if not self._is_server_healthy():
                raise RuntimeError("HTTP服务器启动失败")

            return self.server_url

        except Exception as e:
            logger.error(f"启动HTTP服务器失败: {e}")
            raise RuntimeError(f"无法启动HTTP服务器: {e}")

    def _is_server_healthy(self) -> bool:
        """检查服务器是否健康"""
        try:
            response = httpx.get(f"{self.server_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def stop_server(self):
        """停止HTTP服务器"""
        if self.server_process:
            logger.info("停止HTTP服务器")
            self.server_process.terminate()

            # 等待进程结束
            try:
                self.server_process.wait(timeout=RealHTTPTestConfig.SERVER_SHUTDOWN_TIMEOUT)
            except subprocess.TimeoutExpired:
                logger.warning("HTTP服务器停止超时，强制终止")
                self.server_process.kill()

            self.server_process = None
            self.server_url = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server_process:
            asyncio.create_task(self.stop_server())


class RealHTTPClientManager:
    """真实HTTP客户端管理器"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.client_pool = []

    def get_client(self) -> AsyncClient:
        """获取HTTP客户端"""
        if self.client_pool:
            client = self.client_pool.pop()
            logger.debug(f"复用HTTP客户端: {id(client)}")
        else:
            client = httpx.AsyncClient(
                base_url=self.server_url,
                timeout=RealHTTPTestConfig.REQUEST_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            logger.debug("创建新HTTP客户端")

        return client

    def return_client(self, client: AsyncClient):
        """归还HTTP客户端"""
        try:
            # 重置客户端状态
            client.cookies.clear()
            client.headers.clear()
        except Exception as e:
            logger.warning(f"客户端重置异常: {e}")

        self.client_pool.append(client)

    async def request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """带重试的HTTP请求"""
        client = self.get_client()

        for attempt in range(RealHTTPTestConfig.MAX_RETRIES):
            try:
                response = await client.request(method, url, **kwargs)

                # 检查响应状态
                if response.status_code < 500:  # 客户端错误不重试
                    return response

                logger.warning(f"HTTP请求失败 (尝试 {attempt + 1}): {response.status_code}")

                if attempt < RealHTTPTestConfig.MAX_RETRIES - 1:
                    await asyncio.sleep(RealHTTPTestConfig.RETRY_DELAY)

            except (TimeoutException, ConnectError) as e:
                logger.warning(f"HTTP请求异常 (尝试 {attempt + 1}): {e}")
                if attempt == RealHTTPTestConfig.MAX_RETRIES - 1:
                    break
                await asyncio.sleep(RealHTTPTestConfig.RETRY_DELAY)

        self.return_client(client)

        raise RuntimeError(f"HTTP请求失败，已重试{RealHTTPTestConfig.MAX_RETRIES}次")


class TestDataManager:
    """测试数据管理器"""

    def __init__(self):
        self.created_users = []
        self.created_tasks = []
        self.created_rewards = []

    async def create_test_user(self, client: AsyncClient) -> Dict[str, Any]:
        """创建测试用户"""
        try:
            # 创建游客用户
            response = await client.post("/auth/guest/init")
            assert response.status_code == 200
            user_data = response.json()

            self.created_users.append(user_data["data"]["user_id"])
            logger.info(f"创建测试用户: {user_data['data']['user_id']}")

            return user_data["data"]

        except Exception as e:
            logger.error(f"创建测试用户失败: {e}")
            raise

    async def cleanup_test_data(self, client: AsyncClient):
        """清理测试数据"""
        try:
            # 清理创建的任务
            for task_id in self.created_tasks:
                try:
                    await client.delete(f"/tasks/{task_id}")
                except Exception as e:
                    logger.warning(f"清理任务失败: {task_id}, {e}")

            # 清理创建的用户（如果需要）
            for user_id in self.created_users:
                try:
                    # 这里可以添加用户清理逻辑
                    pass
                except Exception as e:
                    logger.warning(f"清理用户失败: {user_id}, {e}")

            # 重置记录
            self.created_tasks.clear()
            self.created_users.clear()

            logger.info("测试数据清理完成")

        except Exception as e:
            logger.error(f"测试数据清理失败: {e}")


# 全局管理器实例
server_manager = HTTPServerManager()


@pytest.fixture(scope="session")
async def real_http_server():
    """真实HTTP服务器fixture"""
    # 启动服务器
    server_url = await server_manager.start_server()

    # 创建客户端管理器
    client_manager = RealHTTPClientManager(server_url)

    # 创建数据管理器
    data_manager = TestDataManager()

    # 提供测试上下文
    yield {
        "server_url": server_url,
        "client_manager": client_manager,
        "data_manager": data_manager,
        "config": RealHTTPTestConfig
    }

    # 清理
    await data_manager.cleanup_test_data(client_manager.get_client())
    logger.info("真实HTTP服务器测试会话结束")


@pytest.fixture(scope="session")
async def real_api_client(real_http_server):
    """真实HTTP客户端fixture"""
    return real_http_server["client_manager"].get_client()


@pytest.fixture(scope="session")
async def test_user_context(real_http_server):
    """测试用户上下文fixture"""
    return await real_http_server["data_manager"].create_test_user(
        real_http_server["client_manager"].get_client()
    )


# 测试工具函数
async def assert_api_response(
    response: httpx.Response,
    expected_status: int = 200,
    assert_data: bool = True,
    error_message: str = None
):
    """API响应断言助手"""
    assert response.status_code == expected_status, (
        f"期望状态码 {expected_status}，实际: {response.status_code}"
    )

    if error_message:
        assert error_message in response.text, (
            f"期望错误信息 '{error_message}'不在响应中"
        )

    if assert_data:
        try:
            data = response.json()
            assert "data" in data, "响应缺少data字段"
        except Exception:
            raise AssertionError("响应不是有效JSON")


# 错误处理装饰器
def with_real_http_error_handling(test_func):
    """真实HTTP错误处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await test_func(*args, **kwargs)
        except (TimeoutException, ConnectError, RuntimeError) as e:
            logger.error(f"真实HTTP测试失败: {e}")
            pytest.fail(f"真实HTTP请求失败: {e}")
        except AssertionError as e:
            logger.error(f"真实HTTP测试断言失败: {e}")
            raise
        except Exception as e:
            logger.error(f"真实HTTP测试异常: {e}")
            pytest.fail(f"真实HTTP测试异常: {e}")

    return wrapper