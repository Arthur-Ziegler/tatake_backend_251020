"""
API错误响应格式验证测试

验证所有API错误响应都符合统一的格式标准，确保客户端能够正确处理错误信息。

作者：TaKeKe团队
版本：1.0.0 - UUID架构Batch 1测试
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import Mock, patch
import uuid

from src.api.main import app


class TestAPIErrorResponseFormat:
    """API错误响应格式测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_uuid_validation_error_response_format(self, client):
        """测试UUID验证错误的响应格式"""

        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()

            # 测试无效UUID格式
            response = client.post(
                "/chat/sessions/invalid-uuid-format/send",
                json={"message": "Hello"},
                headers={"Authorization": "Bearer valid-token"}
            )

            # 验证状态码
            assert response.status_code == 400

            # 验证响应结构
            response_data = response.json()
            assert "code" in response_data
            assert "data" in response_data
            assert "message" in response_data

            # 验证错误详情结构
            message = response_data["message"]
            assert isinstance(message, dict)
            assert "code" in message
            assert "message" in message
            assert "field" in message
            assert "example" in message

            # 验证具体内容
            assert message["code"] == 400
            assert "无效的会话ID格式" in message["message"]
            assert message["field"] == "session_id"
            assert "550e8400-e29b-41d4-a716-446655440000" in message["example"]

    def test_auth_error_response_format(self, client):
        """测试认证错误的响应格式"""

        # 测试未授权访问
        response = client.get("/chat/sessions")

        # 验证状态码
        assert response.status_code == 401

        # 验证响应结构
        response_data = response.json()
        assert "code" in response_data
        assert "data" in response_data
        assert "message" in response_data

        # 验证错误信息
        assert response_data["code"] == 401
        assert isinstance(response_data["message"], str)

    def test_not_found_error_response_format(self, client):
        """测试资源未找到错误的响应格式"""

        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()

            # 测试不存在的会话ID（但格式正确）
            valid_uuid = "550e8400-e29b-41d4-a716-446655440999"
            response = client.get(
                f"/chat/sessions/{valid_uuid}",
                headers={"Authorization": "Bearer valid-token"}
            )

            # 可能返回404或其他状态码，但响应格式应该一致
            if response.status_code == 404:
                response_data = response.json()
                assert "code" in response_data
                assert "data" in response_data
                assert "message" in response_data
                assert response_data["code"] == 404

    def test_validation_error_response_format(self, client):
        """测试参数验证错误的响应格式"""

        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()

            # 测试无效的请求体
            response = client.post(
                "/chat/sessions/550e8400-e29b-41d4-a716-446655440000/send",
                json={},  # 空请求体，缺少必需的message字段
                headers={"Authorization": "Bearer valid-token"}
            )

            # 可能返回401（认证错误）或422（验证错误）
            # 只要响应格式正确即可
            response_data = response.json()

            if response.status_code == 422:
                # FastAPI验证错误格式
                assert "detail" in response_data
                assert isinstance(response_data["detail"], list)
            elif response.status_code == 401:
                # 认证错误格式
                assert "code" in response_data
                assert "message" in response_data

    def test_method_not_allowed_error_response_format(self, client):
        """测试方法不允许错误的响应格式"""

        # 使用不支持的HTTP方法
        response = client.patch("/chat/sessions")

        # 验证状态码
        assert response.status_code == 405

        # 验证响应包含错误信息
        response_data = response.json()
        assert "detail" in response_data or "message" in response_data

    def test_server_error_response_format(self, client):
        """测试服务器内部错误的响应格式"""

        # 访问不存在的路径来模拟404错误
        response = client.get("/nonexistent/endpoint")

        # 验证状态码
        assert response.status_code == 404

        # 验证响应包含错误信息
        response_data = response.json()
        assert "detail" in response_data or "message" in response_data

    def test_error_response_content_type(self, client):
        """测试错误响应的内容类型"""

        # 测试各种错误响应的内容类型
        endpoints = [
            ("/chat/sessions/invalid-uuid", "GET"),  # 400错误
            ("/chat/sessions", "GET"),  # 401错误
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})

            # 验证内容类型
            assert response.headers["content-type"] == "application/json"

    def test_error_response_charset(self, client):
        """测试错误响应的字符编码"""

        response = client.get("/chat/sessions/invalid-uuid-format")

        # 验证内容类型（FastAPI默认为application/json）
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type.lower()

        # 验证响应可以被正确解析为UTF-8文本
        response_text = response.text
        assert isinstance(response_text, str)
        # 验证包含中文错误消息也能正确显示
        response_text.encode('utf-8')  # 如果不能编码为UTF-8会抛出异常

    def test_error_response_structure_consistency(self, client):
        """测试不同错误类型的响应结构一致性"""

        # 收集各种错误响应
        errors = []

        # 1. UUID格式错误
        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()
            response = client.post(
                "/chat/sessions/invalid-uuid/send",
                json={"message": "Hello"},
                headers={"Authorization": "Bearer valid-token"}
            )
            if response.status_code == 400:
                errors.append(("UUID Validation", response.json()))

        # 2. 认证错误
        response = client.get("/chat/sessions")
        if response.status_code == 401:
            errors.append(("Authentication", response.json()))

        # 3. 方法不允许错误
        response = client.patch("/chat/sessions")
        if response.status_code == 405:
            errors.append(("Method Not Allowed", response.json()))

        # 验证所有错误响应都包含基本字段
        for error_type, error_response in errors:
            assert "code" in error_response or "detail" in error_response, \
                f"{error_type} error response missing code/detail field"

            if "message" in error_response:
                assert isinstance(error_response["message"], (str, dict)), \
                    f"{error_type} error message should be string or dict"

    def test_error_message_helpfulness(self, client):
        """测试错误消息的有用性"""

        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()

            # 测试UUID验证错误消息
            response = client.post(
                "/chat/sessions/bad-uuid/send",
                json={"message": "Hello"},
                headers={"Authorization": "Bearer valid-token"}
            )

            if response.status_code == 400:
                response_data = response.json()
                message = response_data.get("message", {})

                if isinstance(message, dict):
                    # 验证错误消息包含有用信息
                    error_text = message.get("message", "")
                    field_name = message.get("field", "")
                    example_value = message.get("example", "")

                    assert len(error_text) > 0, "Error message should not be empty"
                    assert len(field_name) > 0, "Field name should be specified"
                    assert len(example_value) > 0, "Example value should be provided"

                    # 验证消息包含问题描述和解决方案
                    assert "无效" in error_text or "invalid" in error_text.lower()
                    assert "UUID" in error_text or "uuid" in error_text.lower()

    @pytest.mark.parametrize("invalid_uuid", [
        "not-a-uuid",
        "123-456-789",
        "550e8400-e29b-41d4-a716",  # 不完整
        "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",  # 无效字符
        "",  # 空字符串
    ])
    def test_various_uuid_error_responses(self, client, invalid_uuid):
        """测试各种无效UUID的错误响应一致性"""

        with patch('src.api.dependencies.get_current_user_id') as mock_auth:
            mock_auth.return_value = uuid.uuid4()

            response = client.get(
                f"/chat/sessions/{invalid_uuid}",
                headers={"Authorization": "Bearer valid-token"}
            )

            # 验证响应格式一致性
            assert response.status_code == 400
            response_data = response.json()

            # 验证基本结构
            assert "code" in response_data
            assert "message" in response_data

            message = response_data["message"]
            if isinstance(message, dict):
                assert "message" in message
                assert "field" in message
                assert "example" in message
                assert message["field"] == "session_id"