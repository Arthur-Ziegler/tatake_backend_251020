"""
统一响应格式和错误处理测试

测试API的统一响应格式和错误处理机制，确保所有响应都遵循一致的格式，
包含TraceID追踪，错误信息详细且格式统一。
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.main import app
from api.responses import create_success_response, create_error_response

# 创建测试客户端
client = TestClient(app)


class TestUnifiedResponseFormat:
    """统一响应格式测试类"""

    def test_success_response_format(self):
        """测试成功响应格式"""
        response = client.get("/")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应格式结构
        data = response.json()

        # 必需字段验证
        required_fields = ["code", "message", "data", "timestamp", "traceId"]
        for field in required_fields:
            assert field in data, f"响应缺少必需字段: {field}"

        # 字段类型验证
        assert isinstance(data["code"], int)
        assert isinstance(data["message"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["traceId"], str)
        assert len(data["traceId"]) > 0

        # 成功响应验证
        assert data["code"] == 200
        assert "API服务正常运行" in data["message"]

    def test_error_response_format_404(self):
        """测试404错误响应格式"""
        response = client.get("/nonexistent-endpoint")

        # 验证响应状态码
        assert response.status_code == 404

        # 验证错误响应格式结构
        data = response.json()

        # 必需字段验证
        required_fields = ["code", "message", "data", "timestamp", "traceId"]
        for field in required_fields:
            assert field in data, f"错误响应缺少必需字段: {field}"

        # 错误响应验证
        assert data["code"] == 404
        assert "未找到" in data["message"]
        assert data["data"] is None
        assert len(data["traceId"]) > 0

    def test_error_response_format_405(self):
        """测试405错误响应格式"""
        response = client.delete("/")

        # 验证响应状态码
        assert response.status_code == 405

        # 验证错误响应格式结构
        data = response.json()

        # 必需字段验证
        required_fields = ["code", "message", "data", "timestamp", "traceId"]
        for field in required_fields:
            assert field in data, f"错误响应缺少必需字段: {field}"

        # 错误响应验证
        assert data["code"] == 405
        assert "不被允许" in data["message"]
        assert data["data"] is None

    def test_trace_id_consistency(self):
        """测试TraceID的一致性"""
        response = client.get("/")

        # 验证TraceID在响应头中存在
        assert "x-request-id" in response.headers

        # 验证响应头和响应体中的TraceID一致
        header_trace_id = response.headers["x-request-id"]
        body_trace_id = response.json()["traceId"]

        assert header_trace_id == body_trace_id, "响应头和响应体中的TraceID不一致"

    def test_error_details_with_context(self):
        """测试错误响应包含详细的上下文信息"""
        # 测试参数验证错误（如果有相关端点）
        response = client.post("/api/v1/auth/login", json={})

        if response.status_code != 200:
            data = response.json()

            # 验证错误响应包含足够的信息
            assert "code" in data
            assert "message" in data
            assert "traceId" in data
            assert "timestamp" in data

    def test_response_time_header(self):
        """测试响应时间头"""
        response = client.get("/")

        # 验证处理时间头存在
        assert "x-process-time" in response.headers

        # 验证处理时间是数值格式
        process_time = response.headers["x-process-time"]
        assert float(process_time) >= 0, "处理时间应该是非负数"

    def test_response_functions_directly(self):
        """测试响应函数的直接调用"""
        # 测试成功响应函数
        success_data = {"test": "data"}
        success_response = create_success_response(
            data=success_data,
            message="测试成功响应"
        )

        # 验证成功响应是JSONResponse对象
        assert hasattr(success_response, 'body')

        # 解析响应体
        import json
        response_data = json.loads(success_response.body.decode())

        # 验证成功响应结构
        assert response_data["code"] == 200
        assert response_data["message"] == "测试成功响应"
        assert response_data["data"] == success_data
        assert "timestamp" in response_data
        assert "traceId" in response_data

        # 测试错误响应函数
        error_response = create_error_response(
            message="测试错误",
            status_code=400,
            error_code="TEST_ERROR"
        )

        # 解析错误响应体
        error_data = json.loads(error_response.body.decode())

        # 验证错误响应结构
        assert error_data["code"] == 400
        assert error_data["message"] == "测试错误"
        assert error_data["data"] is None
        assert error_data["errorCode"] == "TEST_ERROR"

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = client.get("/")
        data = response.json()

        # 验证时间戳是ISO格式
        timestamp = data["timestamp"]

        # 尝试解析ISO格式时间戳
        from datetime import datetime
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed_time is not None
        except ValueError:
            pytest.fail("时间戳不是有效的ISO格式")

    def test_content_type_headers(self):
        """测试内容类型头"""
        response = client.get("/")

        # 验证内容类型头
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_error_message_localization(self):
        """测试错误消息本地化（中文）"""
        response = client.get("/nonexistent-endpoint")
        data = response.json()

        # 验证错误消息是中文
        message = data["message"]
        # 简单检查是否包含中文字符
        try:
            message.encode('ascii')
            has_chinese = False
        except UnicodeEncodeError:
            has_chinese = True

        assert has_chinese, "错误消息应该支持中文显示"

    def test_api_info_response_structure(self):
        """测试API信息响应的详细结构"""
        response = client.get("/api/v1/info")
        data = response.json()

        # 验证API信息结构
        assert "code" in data
        assert "data" in data
        assert data["code"] == 200

        # 验证API数据结构
        api_data = data["data"]
        assert "api_name" in api_data
        assert "api_version" in api_data
        assert "api_prefix" in api_data
        assert "total_endpoints" in api_data
        assert "documentation" in api_data

        # 验证文档信息
        docs = api_data["documentation"]
        assert "swagger" in docs
        assert "redoc" in docs
        assert "openapi" in docs

    def test_health_response_structure(self):
        """测试健康检查响应的详细结构"""
        response = client.get("/health")
        data = response.json()

        # 验证健康检查结构
        assert "code" in data
        assert "data" in data
        assert data["code"] == 200

        # 验证健康数据结构
        health_data = data["data"]
        assert "status" in health_data
        assert "version" in health_data
        assert "timestamp" in health_data

        # 验证健康状态
        assert health_data["status"] == "healthy"


class TestErrorHandlingEdgeCases:
    """错误处理边界情况测试类"""

    def test_malformed_json_request(self):
        """测试格式错误的JSON请求"""
        response = client.post(
            "/nonexistent-endpoint",  # 使用不存在的端点确保404
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # 应该返回404错误
        assert response.status_code == 404

        # 验证错误响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "traceId" in data

    def test_large_payload_handling(self):
        """测试大负载处理"""
        # 创建一个大的请求体
        large_data = {"key": "x" * 10000}

        response = client.post(
            "/api/v1/auth/login",
            json=large_data
        )

        # 验证响应格式统一（无论成功或失败）
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "traceId" in data

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_data = {
            "message": "测试中文字符 🚀 emoji",
            "special_chars": "àáâãäåæçèéêë"
        }

        response = client.post(
            "/nonexistent-endpoint",  # 使用不存在的端点确保404
            json=unicode_data
        )

        # 验证响应能正确处理Unicode
        assert response.status_code == 404

        # 验证响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "traceId" in data

        # 验证错误消息能处理中文
        assert "未找到" in data["message"]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])