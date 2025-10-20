"""
FastAPI应用基础结构测试

测试FastAPI应用的基础功能是否正常工作，包括应用启动、基础路由、
健康检查接口等。
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.main import app

# 创建测试客户端
client = TestClient(app)


class TestFastAPIBasicStructure:
    """FastAPI基础结构测试类"""

    def test_app_exists(self):
        """测试FastAPI应用实例是否存在"""
        assert app is not None
        assert hasattr(app, 'title')
        assert app.title == "TaKeKe API"

    def test_root_endpoint(self):
        """测试根路径端点"""
        response = client.get("/")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert "timestamp" in data
        assert "traceId" in data

        # 验证响应内容
        assert data["code"] == 200
        assert "API服务正常运行" in data["message"]
        assert "name" in data["data"]
        assert "version" in data["data"]

    def test_health_check_endpoint(self):
        """测试健康检查端点"""
        response = client.get("/health")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "data" in data

        # 验证健康检查内容
        assert data["code"] == 200
        assert "服务健康" in data["message"]
        assert data["data"]["status"] == "healthy"
        assert "version" in data["data"]

    def test_api_info_endpoint(self):
        """测试API信息端点"""
        response = client.get("/api/v1/info")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应格式
        data = response.json()
        assert "code" in data
        assert "data" in data

        # 验证API信息内容
        assert data["data"]["total_endpoints"] == 46  # 更新为46个端点
        assert "endpoints" in data["data"]
        assert "认证系统" in data["data"]["endpoints"]
        assert "documentation" in data["data"]

    def test_openapi_docs_endpoint(self):
        """测试OpenAPI文档端点"""
        response = client.get("/openapi.json")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证OpenAPI格式
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "TaKeKe API"

    def test_swagger_docs_endpoint(self):
        """测试Swagger文档端点"""
        response = client.get("/docs")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应内容类型
        assert "text/html" in response.headers["content-type"]

    def test_redoc_docs_endpoint(self):
        """测试ReDoc文档端点"""
        response = client.get("/redoc")

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应内容类型
        assert "text/html" in response.headers["content-type"]

    def test_cors_headers(self):
        """测试CORS头设置"""
        # 测试OPTIONS请求
        response = client.options("/")

        # 验证CORS头存在
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_request_id_header(self):
        """测试请求ID头"""
        response = client.get("/")

        # 验证请求ID头存在
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

        # 验证请求ID格式
        request_id = response.headers["x-request-id"]
        assert len(request_id) > 0

    def test_error_handling_404(self):
        """测试404错误处理"""
        response = client.get("/nonexistent-endpoint")

        # 验证响应状态码
        assert response.status_code == 404

        # 验证错误响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "timestamp" in data
        assert "traceId" in data

    def test_error_handling_method_not_allowed(self):
        """测试405错误处理"""
        response = client.delete("/")

        # 验证响应状态码
        assert response.status_code == 405

        # 验证错误响应格式
        data = response.json()
        assert "code" in data
        assert "message" in data


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])