"""
测试辅助工具集

提供测试中常用的辅助函数和工具类，确保测试的一致性和可靠性。

作者: TaTakeKe团队
版本: 零Bug测试体系 v1.0
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from contextlib import contextmanager

from httpx import Response


class APITestClient:
    """API测试客户端

    def __init__(self, base_url: str = "http://localhost:8001"):
        """
        初始化API测试客户端

        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = None
        self.access_token = None
        self.user_id = None

    def authenticate(self, access_token: str, user_id: str) -> None:
        """
        设置认证信息

        Args:
            access_token: 访问令牌
            user_id: 用户ID
        """
        self.access_token = access_token
        self.user_id = user_id

    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def assert_response_success(self, response: Response, message: str = "API调用失败") -> None:
        """
        断言API响应成功

        Args:
            response: HTTP响应对象
            message: 错误消息

        Raises:
            AssertionError: 响应不成功时抛出
        """
        assert response.status_code == 200, f"{message}: HTTP {response.status_code}"

        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert data.get("code") == 200, f"{message}: API返回码 {data.get('code')}"


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_user_data(overrides: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成测试用户数据

        Args:
            overrides: 覆盖默认值

        Returns:
            用户数据字典
        """
        user_data = {
            "wechat_openid": f"test_user_{uuid.uuid4().hex[:8]}",
            "username": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@test.com",
            "phone": f"138{uuid.uuid4().hex[:8]}",
            "is_guest": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if overrides:
            user_data.update(overrides)

        return user_data

    @staticmethod
    def generate_task_data(user_id: str, overrides: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成测试任务数据

        Args:
            user_id: 用户ID
            overrides: 覆盖默认值

        Returns:
            任务数据字典
        """
        task_data = {
            "title": f"测试任务_{uuid.uuid4().hex[:8]}",
            "description": "这是一个测试任务描述",
            "priority": "medium",
            "status": "pending",
            "user_id": user_id,
            "parent_id": None,
            "completion_percentage": 0,
            "estimated_hours": 2.0,
            "actual_hours": 0.0,
            "tags": ["test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if overrides:
            task_data.update(overrides)

        return task_data

    @staticmethod
    def generate_top3_task_data(user_id: str, overrides: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成Top3测试任务数据

        Args:
            user_id: 用户ID
            overrides: 覆盖默认值

        Returns:
            Top3任务数据字典
        """
        task_data = TestDataGenerator.generate_task_data(user_id, {
            "title": f"Top3测试任务_{uuid.uuid4().hex[:8]}",
            "description": "这是一个Top3测试任务描述",
            "priority": "high"
        })

        if overrides:
            task_data.update(overrides)

        return task_data


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self) -> None:
        """开始计时"""
        self.start_time = time.time()

    def stop(self) -> float:
        """停止计时并返回耗时"""
        if self.start_time is None:
            raise ValueError("必须先调用start()方法")

        self.end_time = time.time()
        return self.end_time - self.start_time

    def get_elapsed_time(self) -> float:
        """获取已耗时（秒）"""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or time.time()
        return end_time - self.start_time

    @contextmanager
    def measure(self):
        """上下文管理器计时"""
        self.start()
        try:
            yield self
        finally:
            elapsed = self.stop()
            if elapsed > 1.0:  # 如果超过1秒，记录警告
                print(f"⚠️  耗时过长: {elapsed:.2f}秒")


class DatabaseTestHelper:
    """数据库测试辅助类"""

    @staticmethod
    def assert_record_exists(table_class, filters: Dict, session, message: str = "记录不存在") -> None:
        """
        断言记录存在

        Args:
            table_class: 表模型类
            filters: 过滤条件
            session: 数据库会话
            message: 错误消息

        Raises:
            AssertionError: 记录不存在时抛出
        """
        record = session.query(table_class).filter_by(**filters).first()
        assert record is not None, f"{message}: {table_class.__name__} with filters {filters}"

    @staticmethod
    def assert_record_count(table_class, filters: Dict, expected_count: int, session,
                              message: str = "记录数量不匹配") -> None:
        """
        断言记录数量匹配

        Args:
            table_class: 表模型类
            filters: 过滤条件
            expected_count: 期望数量
            session: 数据库会话
            message: 错误消息

        Raises:
            AssertionError: 数量不匹配时抛出
        """
        count = session.query(table_class).filter_by(**filters).count()
        assert count == expected_count, f"{message}: 期望 {expected_count}，实际 {count}"

    @staticmethod
    def assert_field_value(record, field_name: str, expected_value: Any, message: str = None) -> None:
        """
        断言字段值匹配

        Args:
            record: 记录对象
            field_name: 字段名
            expected_value: 期望值
            message: 错误消息

        Raises:
            AssertionError: 值不匹配时抛出
        """
        actual_value = getattr(record, field_name)
        error_msg = message or f"字段 {field_name} 期望值 {expected_value}，实际值 {actual_value}"
        assert actual_value == expected_value, error_msg


class SecurityTestHelper:
    """安全测试辅助类"""

    @staticmethod
    def generate_test_token() -> str:
        """
        生成测试用JWT Token

        Returns:
            测试Token
        """
        import jwt
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "is_guest": False,
            "jwt_version": 1,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "token_type": "access"
        }

        # 这里应该使用真实的密钥，测试环境下可以使用测试密钥
        secret_key = "test_secret_key_change_in_production"

        return jwt.encode(payload, secret_key, algorithm="HS256")

    @staticmethod
    def assert_no_secrets_in_codebase(file_path: str) -> None:
        """
        断言代码中没有硬编码的秘密

        Args:
            file_path: 文件路径

        Raises:
            AssertionError: 发现硬编码秘密时抛出
        """
        import re

        # 常见秘密模式
        secret_patterns = [
            r'password\s*=\s*["\']?[^"\']+[\'"]?',  # password = "secret"
            r'api_key\s*=\s*["\']?[^"\']+[\'"]?',     # api_key = "secret"
            r'secret\s*=\s*["\']?[^"\']+[\'"]?',       # secret = "secret"
            r'token\s*=\s*["\']?[^"\']+[\'"]?',        # token = "secret"
            r'private_key\s*=\s*["\']?[^"\']+[\'"]?',  # private_key = "secret"
        ]

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        line_number = 0
        for line in content.split('\n'):
            line_number += 1
            for pattern in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # 检查是否是测试文件或注释
                    if '/tests/' in file_path or line.strip().startswith('#'):
                        continue
                    assert False, f"在文件 {file_path}:{line_number} 发现可能的硬编码秘密"


class TestEnvironmentManager:
    """测试环境管理器"""

    def __init__(self):
        self.test_env_vars = {}
        self.original_env_vars = {}

    def set_test_env_var(self, key: str, value: str) -> None:
        """
        设置测试环境变量

        Args:
            key: 环境变量名
            value: 环境变量值
        """
        import os

        # 保存原始值
        if key not in self.original_env_vars:
            self.original_env_vars[key] = os.environ.get(key)

        # 设置测试值
        os.environ[key] = value
        self.test_env_vars[key] = value

    def cleanup_env_vars(self) -> None:
        """清理测试环境变量"""
        import os

        for key in self.test_env_vars:
            if key in self.original_env_vars:
                if self.original_env_vars[key] is not None:
                    os.environ[key] = self.original_env_vars[key]
                else:
                    os.environ.pop(key, None)
            else:
                os.environ.pop(key, None)

        self.test_env_vars.clear()
        self.original_env_vars.clear()


class AssertHelper:
    """断言辅助类"""

    @staticmethod
    def assert_dict_equal(actual: Dict, expected: Dict, ignore_keys: List[str] = None,
                        message: str = "字典不相等") -> None:
        """
        断言两个字典相等，可忽略指定键

        Args:
            actual: 实际字典
            expected: 期望字典
            ignore_keys: 要忽略的键列表
            message: 错误消息

        Raises:
            AssertionError: 字典不相等时抛出
        """
        if ignore_keys:
            actual_filtered = {k: v for k, v in actual.items() if k not in ignore_keys}
            expected_filtered = {k: v for k, v in expected.items() if k not in ignore_keys}
        else:
            actual_filtered = actual
            expected_filtered = expected

        assert actual_filtered == expected_filtered, message

    @staticmethod
    def assert_list_equal(actual: List, expected: List, message: str = "列表不相等") -> None:
        """
        断言两个列表相等

        Args:
            actual: 实际列表
            expected: 期望列表
            message: 错误消息

        Raises:
            AssertionError: 列表不相等时抛出
        """
        assert actual == expected, f"{message}: 期望 {expected}，实际 {actual}"

    @staticmethod
    def assert_datetime_close(actual: datetime, expected: datetime,
                           tolerance_seconds: int = 1, message: str = "时间不匹配") -> None:
        """
        断言两个时间接近

        Args:
            actual: 实际时间
            expected: 期望时间
            tolerance_seconds: 容差秒数
            message: 错误消息

        Raises:
            AssertionError: 时间不匹配时抛出
        """
        time_diff = abs((actual - expected).total_seconds())
        assert time_diff <= tolerance_seconds, f"{message}: 时间差 {time_diff}秒超过容差 {tolerance_seconds}秒"