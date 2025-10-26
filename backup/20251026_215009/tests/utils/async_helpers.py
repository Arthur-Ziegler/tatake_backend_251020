"""
异步测试辅助工具

提供异步测试中常用的辅助功能，包括：
1. 异步上下文管理
2. 异步Mock工具
3. 异步断言助手
4. 并发测试支持

作者：TaKeKe团队
版本：1.0.0 - 异步测试工具
"""

import asyncio
from typing import Any, Awaitable, Callable, List, Optional
from unittest.mock import AsyncMock


class AsyncTestHelper:
    """异步测试辅助类"""

    @staticmethod
    async def run_async(func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        运行异步函数

        在同步测试环境中运行异步函数的便捷方法。
        """
        return await func(*args, **kwargs)

    @staticmethod
    async def gather_async(*tasks: Awaitable[Any]) -> List[Any]:
        """
        并发运行多个异步任务

        用于测试并发场景。
        """
        return await asyncio.gather(*tasks)

    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1,
    ) -> bool:
        """
        等待条件满足

        用于测试异步状态变化。
        """
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition():
                return True
            await asyncio.sleep(interval)

        return False

    @staticmethod
    def create_async_mock(return_value: Any = None) -> AsyncMock:
        """
        创建异步Mock对象

        自动配置异步Mock的返回值。
        """
        mock = AsyncMock()
        mock.return_value = return_value
        return mock

    @staticmethod
    async def assert_async_raises(
        async_func: Callable[..., Awaitable[Any]],
        expected_exception: type,
        *args,
        **kwargs
    ) -> Exception:
        """
        断言异步函数抛出指定异常

        类似pytest.raises，但用于异步函数。
        """
        try:
            await async_func(*args, **kwargs)
            raise AssertionError(f"Expected {expected_exception.__name__} but no exception was raised")
        except expected_exception as e:
            return e
        except Exception as e:
            raise AssertionError(f"Expected {expected_exception.__name__} but got {type(e).__name__}: {e}")

    @staticmethod
    async def measure_async_time(
        async_func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> tuple[Any, float]:
        """
        测量异步函数执行时间

        返回 (结果, 耗时秒数)。
        """
        import time
        start_time = time.time()
        result = await async_func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration


class AsyncContextManager:
    """异步上下文管理器辅助类"""

    def __init__(self):
        self.enter_stack = []
        self.exit_stack = []

    async def enter(self, context_manager):
        """进入异步上下文"""
        result = await context_manager.__aenter__()
        self.enter_stack.append(context_manager)
        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出所有上下文"""
        # 按照相反的顺序退出上下文
        for context_manager in reversed(self.enter_stack):
            try:
                await context_manager.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                # 记录错误但继续清理其他上下文
                pass
        self.enter_stack.clear()


class AsyncMockDatabase:
    """异步数据库Mock工具"""

    def __init__(self):
        self.data = {}
        self.queries = []

    async def execute(self, query, *args, **kwargs):
        """Mock数据库执行"""
        self.queries.append({"query": query, "args": args, "kwargs": kwargs})
        return self

    def scalar(self):
        """Mock scalar结果"""
        return self

    def scalars(self):
        """Mock scalars结果"""
        return self

    def all(self):
        """Mock all结果"""
        return []

    def first(self):
        """Mock first结果"""
        return None


class AsyncSMSMock:
    """异步SMS Mock工具"""

    def __init__(self):
        self.messages = []
        self.failures = []

    async def send_code(self, phone: str, code: str) -> dict:
        """Mock发送短信验证码"""
        message = {"phone": phone, "code": code, "success": True}
        self.messages.append(message)

        # 模拟网络延迟
        await asyncio.sleep(0.01)

        return {"success": True, "message_id": f"mock_{len(self.messages)}"}

    def get_last_message(self) -> Optional[dict]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def clear_messages(self):
        """清空消息记录"""
        self.messages.clear()
        self.failures.clear()


class AsyncAssertionHelper:
    """异步断言助手"""

    @staticmethod
    async def assert_eventually(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        message: str = "Condition not met within timeout"
    ):
        """
        断言条件最终会成立

        用于测试异步状态变化。
        """
        helper = AsyncTestHelper()
        result = await helper.wait_for_condition(condition, timeout)
        if not result:
            raise AssertionError(message)

    @staticmethod
    async def assert_no_exception_raised(
        async_func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ):
        """
        断言异步函数不会抛出异常

        与assert_async_raises相反。
        """
        try:
            await async_func(*args, **kwargs)
        except Exception as e:
            raise AssertionError(f"Expected no exception but got {type(e).__name__}: {e}")

    @staticmethod
    async def assert_async_called_with(
        mock_async_func: AsyncMock,
        *expected_args,
        **expected_kwargs
    ):
        """
        断言异步Mock函数被以指定参数调用
        """
        mock_async_func.assert_called_once_with(*expected_args, **expected_kwargs)

    @staticmethod
    async def assert_async_called(async_func: AsyncMock):
        """
        断言异步Mock函数被调用
        """
        async_func.assert_called()


# 便捷函数
def async_test(func):
    """
    异步测试装饰器

    自动运行异步测试函数。
    """
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper