"""
增强用户Profile API Schema OpenAPI测试

测试增强的用户Profile相关schema是否正确注册到OpenAPI文档中。

作者：TaKeKe团队
版本：1.0.0 - Profile功能增强
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


class TestEnhancedProfileSchemaOpenAPI:
    """增强用户Profile Schema OpenAPI测试类"""

    @pytest.fixture
    def client(self):
        """测试客户端fixture"""
        return TestClient(app)

    def test_enhanced_profile_schemas_in_openapi(self, client):
        """
        测试增强Profile相关Schema是否包含在OpenAPI文档中

        Given: 应用实例
        When: 获取OpenAPI文档
        Then: 应该包含所有增强的Profile Schema
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # 验证components/schemas存在
        assert "components" in openapi_data
        assert "schemas" in openapi_data["components"]

        schemas = openapi_data["components"]["schemas"]

        # 验证基础Profile Schema存在
        assert "UserProfileResponse" in schemas
        assert "UpdateProfileRequest" in schemas

        # 验证增强Profile Schema存在
        assert "EnhancedUserProfileResponse" in schemas
        assert "EnhancedUpdateProfileRequest" in schemas

    def test_enhanced_user_profile_response_schema_structure(self, client):
        """
        测试EnhancedUserProfileResponse的Schema结构

        Given: 应用实例
        When: 检查EnhancedUserProfileResponse Schema
        Then: 应该包含所有新字段的定义
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        schema = openapi_data["components"]["schemas"]["EnhancedUserProfileResponse"]

        # 验证schema类型
        assert schema["type"] == "object"

        # 验证必需字段
        required_fields = schema.get("required", [])
        required_fields_set = set(required_fields)

        # 基础字段
        assert "id" in required_fields_set
        assert "nickname" in required_fields_set
        assert "is_active" in required_fields_set
        assert "created_at" in required_fields_set

        # 验证可选字段存在
        properties = schema.get("properties", {})

        # 基础字段
        assert "avatar" in properties
        assert "bio" in properties
        assert "wechat_openid" in properties
        assert "is_guest" in properties
        assert "last_login_at" in properties

        # 新增个人信息字段
        assert "gender" in properties
        assert "birthday" in properties

        # 偏好设置字段
        assert "theme" in properties
        assert "language" in properties

        # 业务相关字段
        assert "points_balance" in properties
        assert "stats" in properties

    def test_enhanced_update_profile_request_schema_structure(self, client):
        """
        测试EnhancedUpdateProfileRequest的Schema结构

        Given: 应用实例
        When: 检查EnhancedUpdateProfileRequest Schema
        Then: 应该包含所有可更新字段的定义
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        schema = openapi_data["components"]["schemas"]["EnhancedUpdateProfileRequest"]

        # 验证schema类型
        assert schema["type"] == "object"

        # 验证所有字段都是可选的（没有required字段）
        assert "required" not in schema or len(schema.get("required", [])) == 0

        # 验证所有字段存在
        properties = schema.get("properties", {})

        # 基础字段
        assert "nickname" in properties
        assert "avatar_url" in properties
        assert "bio" in properties

        # 新增个人信息字段
        assert "gender" in properties
        assert "birthday" in properties

        # 偏好设置字段
        assert "theme" in properties
        assert "language" in properties

    def test_enhanced_profile_api_paths_in_openapi(self, client):
        """
        测试增强Profile API路径是否在OpenAPI文档中

        Given: 应用实例
        When: 检查OpenAPI文档
        Then: 应该包含增强Profile API路径
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # 验证paths存在
        assert "paths" in openapi_data
        paths = openapi_data["paths"]

        # 验证增强Profile API路径存在
        assert "/user/profile/enhanced" in paths

        enhanced_profile_path = paths["/user/profile/enhanced"]

        # 验证GET方法存在
        assert "get" in enhanced_profile_path

        # 验证PUT方法存在
        assert "put" in enhanced_profile_path

    def test_enhanced_profile_get_response_schema_reference(self, client):
        """
        测试增强Profile GET响应的Schema引用

        Given: 应用实例
        When: 检查GET /user/profile/enhanced的响应Schema
        Then: 应该引用EnhancedUserProfileResponse
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # 获取GET操作的响应schema
        get_operation = openapi_data["paths"]["/user/profile/enhanced"]["get"]

        # 验证响应引用
        assert "responses" in get_operation
        get_responses = get_operation["responses"]

        # 检查200响应
        assert "200" in get_responses
        response_200 = get_responses["200"]

        # 验证content存在
        assert "content" in response_200
        content = response_200["content"]

        # 验证application/json内容类型
        assert "application/json" in content
        json_content = content["application/json"]

        # 验证schema引用
        assert "schema" in json_content
        schema_ref = json_content["schema"]

        # 应该引用UnifiedResponse，其中包含EnhancedUserProfileResponse
        assert "$ref" in schema_ref
        assert schema_ref["$ref"] == "#/components/schemas/UnifiedResponse"

    def test_enhanced_profile_put_request_schema_reference(self, client):
        """
        测试增强Profile PUT请求的Schema引用

        Given: 应用实例
        When: 检查PUT /user/profile/enhanced的请求Schema
        Then: 应该引用EnhancedUpdateProfileRequest
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # 获取PUT操作的请求schema
        put_operation = openapi_data["paths"]["/user/profile/enhanced"]["put"]

        # 验证请求体存在
        assert "requestBody" in put_operation
        request_body = put_operation["requestBody"]

        # 验证content存在
        assert "content" in request_body
        content = request_body["content"]

        # 验证application/json内容类型
        assert "application/json" in content
        json_content = content["application/json"]

        # 验证schema引用
        assert "schema" in json_content
        schema_ref = json_content["schema"]

        # 应该引用EnhancedUpdateProfileRequest
        assert "$ref" in schema_ref
        assert schema_ref["$ref"] == "#/components/schemas/EnhancedUpdateProfileRequest"

    def test_schema_descriptions_and_examples(self, client):
        """
        测试Schema描述和示例

        Given: 应用实例
        When: 检查增强Profile Schema
        Then: 应该包含描述信息和示例
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        # 检查EnhancedUserProfileResponse
        profile_schema = openapi_data["components"]["schemas"]["EnhancedUserProfileResponse"]

        # 验证描述存在
        assert "description" in profile_schema
        assert profile_schema["description"] == "增强用户信息响应"

        # 检查示例存在
        assert "example" in profile_schema
        example = profile_schema["example"]

        # 验证示例包含新字段
        assert "gender" in example
        assert "birthday" in example
        assert "theme" in example
        assert "language" in example
        assert "points_balance" in example
        assert "stats" in example

        # 检查EnhancedUpdateProfileRequest
        update_schema = openapi_data["components"]["schemas"]["EnhancedUpdateProfileRequest"]

        # 验证描述存在
        assert "description" in update_schema
        assert update_schema["description"] == "增强的更新用户信息请求模型"

        # 验证示例存在
        assert "example" in update_schema
        update_example = update_schema["example"]

        # 验证示例包含新字段
        assert "gender" in update_example
        assert "birthday" in update_example
        assert "theme" in update_example
        assert "language" in update_example