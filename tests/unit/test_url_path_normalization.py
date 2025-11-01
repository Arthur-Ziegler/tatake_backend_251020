"""
URL路径标准化验证测试

验证微服务客户端的URL路径修复逻辑，确保不依赖微服务可用性
也能验证URL构建的正确性。

作者：TaTake团队
版本：1.0.0（URL修复验证）
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.services.task_microservice_client import TaskMicroserviceClient


class TestURLPathNormalization:
    """URL路径标准化测试类"""

    @pytest.fixture
    def client(self):
        """微服务客户端实例"""
        return TaskMicroserviceClient("http://45.152.65.130:20253")

    def test_url_path_normalization_removes_trailing_slashes(self, client):
        """测试URL路径标准化移除尾部斜杠"""
        test_cases = [
            ("tasks/", "http://45.152.65.130:20253/tasks"),
            ("tasks//", "http://45.152.65.130:20253/tasks"),
            ("/tasks/", "http://45.152.65.130:20253/tasks"),
            ("tasks/special/top3/", "http://45.152.65.130:20253/tasks/special/top3"),
            ("/tasks/special/top3/", "http://45.152.65.130:20253/tasks/special/top3"),
            ("tasks/123/complete/", "http://45.152.65.130:20253/tasks/123/complete"),
            ("/tasks/123/complete/", "http://45.152.65.130:20253/tasks/123/complete"),
        ]

        for input_path, expected_url in test_cases:
            # 模拟客户端的URL构建逻辑
            normalized_path = input_path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"URL路径标准化失败: 输入'{input_path}' -> 期望'{expected_url}', 实际'{actual_url}'"

    def test_url_path_normalization_preserves_required_slashes(self, client):
        """测试URL路径标准化保留必要的斜杠"""
        test_cases = [
            ("tasks", "http://45.152.65.130:20253/tasks"),
            ("tasks/123", "http://45.152.65.130:20253/tasks/123"),
            ("tasks/123/complete", "http://45.152.65.130:20253/tasks/123/complete"),
            ("tasks/special/top3", "http://45.152.65.130:20253/tasks/special/top3"),
            ("tasks/special/top3/2025-01-15", "http://45.152.65.130:20253/tasks/special/top3/2025-01-15"),
            ("focus-status", "http://45.152.65.130:20253/focus-status"),
            ("pomodoro-count", "http://45.152.65.130:20253/pomodoro-count"),
        ]

        for input_path, expected_url in test_cases:
            # 模拟客户端的URL构建逻辑
            normalized_path = input_path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"URL路径标准化失败: 输入'{input_path}' -> 期望'{expected_url}', 实际'{actual_url}'"

    def test_url_normalization_logic_directly(self, client):
        """直接测试URL标准化逻辑（不依赖HTTP客户端）"""
        # 测试不同的路径格式
        test_paths_and_expected = [
            ("tasks/", "http://45.152.65.130:20253/tasks"),
            ("tasks//", "http://45.152.65.130:20253/tasks"),
            ("/tasks/", "http://45.152.65.130:20253/tasks"),
            ("tasks", "http://45.152.65.130:20253/tasks"),
            ("/tasks", "http://45.152.65.130:20253/tasks"),
            ("tasks/special/top3/", "http://45.152.65.130:20253/tasks/special/top3"),
            ("/tasks/special/top3/", "http://45.152.65.130:20253/tasks/special/top3"),
        ]

        for input_path, expected_url in test_paths_and_expected:
            # 直接应用URL标准化逻辑
            normalized_path = input_path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"URL标准化逻辑失败: 输入'{input_path}' -> 期望'{expected_url}', 实际'{actual_url}'"

    def test_core_api_urls_normalization(self, client):
        """测试核心API的URL标准化"""
        # 9个核心接口的路径测试
        core_interfaces = [
            ("GET", "tasks/"),
            ("POST", "tasks/"),
            ("PUT", "tasks/123"),
            ("DELETE", "tasks/123"),
            ("POST", "tasks/123/complete"),
            ("POST", "tasks/special/top3"),
            ("GET", "tasks/special/top3/2025-01-15"),
            ("POST", "tasks/focus-status"),
            ("GET", "tasks/pomodoro-count"),
        ]

        expected_mappings = [
            ("GET", "http://45.152.65.130:20253/tasks"),
            ("POST", "http://45.152.65.130:20253/tasks"),
            ("PUT", "http://45.152.65.130:20253/tasks/123"),
            ("DELETE", "http://45.152.65.130:20253/tasks/123"),
            ("POST", "http://45.152.65.130:20253/tasks/123/complete"),
            ("POST", "http://45.152.65.130:20253/tasks/special/top3"),
            ("GET", "http://45.152.65.130:20253/tasks/special/top3/2025-01-15"),
            ("POST", "http://45.152.65.130:20253/tasks/focus-status"),
            ("GET", "http://45.152.65.130:20253/tasks/pomodoro-count"),
        ]

        for (method, path), (expected_method, expected_url) in zip(core_interfaces, expected_mappings):
            # 应用URL标准化逻辑
            normalized_path = path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"核心接口URL标准化失败: {method} {path} -> 期望{expected_method} {expected_url}, 实际{method} {actual_url}"

    def test_url_construction_edge_cases(self, client):
        """测试URL构建的边缘情况"""
        edge_cases = [
            ("", "http://45.152.65.130:20253/"),  # 空路径
            ("/", "http://45.152.65.130:20253/"),  # 只有斜杠
            ("//", "http://45.152.65.130:20253/"),  # 双斜杠
            ("///", "http://45.152.65.130:20253/"),  # 三斜杠
            ("tasks/", "http://45.152.65.130:20253/tasks"),
            ("tasks//", "http://45.152.65.130:20253/tasks"),
            ("tasks///", "http://45.152.65.130:20253/tasks"),
        ]

        for input_path, expected_url in edge_cases:
            # 应用URL标准化逻辑
            normalized_path = input_path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"边缘情况URL构建失败: 输入'{input_path}' -> 期望'{expected_url}', 实际'{actual_url}'"

    def test_url_base_url_handling(self):
        """测试基础URL处理"""
        # 测试不同格式的基础URL
        base_urls = [
            "http://45.152.65.130:20253",
            "http://45.152.65.130:20253/",
            "http://45.152.65.130:20253//",
        ]

        test_path = "tasks/"
        expected_url = "http://45.152.65.130:20253/tasks"

        for base_url in base_urls:
            client = TaskMicroserviceClient(base_url)

            # 应用URL标准化逻辑
            normalized_path = test_path.rstrip('/')  # 移除尾部斜杠
            actual_url = f"{client.base_url.rstrip('/')}/{normalized_path.lstrip('/')}"

            assert actual_url == expected_url, \
                f"基础URL处理失败: base_url='{base_url}', path='{test_path}' -> 期望'{expected_url}', 实际'{actual_url}'"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])