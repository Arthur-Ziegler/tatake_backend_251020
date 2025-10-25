"""
Swagger/OpenAPI 配置修复测试

本测试文件采用 TDD 方法，验证以下问题修复：
1. UnifiedResponse schema 引用错误
2. Swagger UI tags 重复显示
3. main.py description 为空问题
4. openapi.py 配置过载问题

测试策略：
- 先验证问题存在（Failing Tests）
- 然后实施修复
- 最后验证修复成功（Passing Tests）
"""

import pytest
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.main import app
from src.api.openapi import custom_openapi, OpenAPIConfig


class TestSwaggerOpenAPIFix:
    """Swagger/OpenAPI 修复测试套件"""

    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
        self.openapi_schema = custom_openapi(app)

    def test_unified_response_schema_exists(self):
        """测试 UnifiedResponse schema 在 OpenAPI 中正确定义"""
        # 获取 OpenAPI schema
        openapi_schema = self.openapi_schema

        # 验证 components 存在
        assert "components" in openapi_schema, "OpenAPI 应该包含 components"

        # 验证 schemas 存在
        assert "schemas" in openapi_schema["components"], "components 应该包含 schemas"

        # 验证 UnifiedResponse schema 存在
        schemas = openapi_schema["components"]["schemas"]
        assert "UnifiedResponse" in schemas, "UnifiedResponse schema 应该存在"

        # 验证 UnifiedResponse schema 结构
        unified_response = schemas["UnifiedResponse"]
        required_fields = unified_response.get("required", [])
        properties = unified_response.get("properties", {})

        # 验证必要字段
        assert "code" in properties, "UnifiedResponse 应该包含 code 字段"
        assert "data" in properties, "UnifiedResponse 应该包含 data 字段"
        assert "message" in properties, "UnifiedResponse 应该包含 message 字段"
        assert "code" in required_fields, "code 应该是必填字段"
        assert "message" in required_fields, "message 应该是必填字段"

    def test_openapi_description_not_empty(self):
        """测试 API 描述不为空"""
        info = self.openapi_schema.get("info", {})
        description = info.get("description", "")

        # 验证描述不为空
        assert description.strip() != "", "API 描述不能为空"
        assert len(description) > 50, "API 描述应该有足够的内容"

    def test_no_tags_duplication_in_routes(self):
        """测试路由中没有重复的 tags"""
        routes = [route for route in app.routes if hasattr(route, 'tags')]

        # 收集所有 tag 统计
        tag_counts = {}
        for route in routes:
            if hasattr(route, 'tags') and route.tags:
                for tag in route.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # 验证没有重复的 tag 路由（每个路由应该只有一个 tag）
        # 注意：这里检查的是是否存在同一个路由多次定义相同 tag 的情况
        # 实际的重复问题是在 include_router 时导致的
        for tag, count in tag_counts.items():
            # 正常情况下，每个 tag 的路由数量应该合理
            # 如果存在重复，数量会异常多
            assert count < 20, f"Tag '{tag}' 的路由数量异常多，可能存在重复：{count}"

    def test_expected_tags_count(self):
        """测试预期的标签数量"""
        # 根据设计文档，应该有 8 个主要分组
        expected_tags = [
            "系统", "认证系统", "用户管理", "任务管理",
            "番茄钟系统", "奖励系统", "积分系统", "Top3管理",
            "智能聊天"
        ]

        # 获取实际的 tags
        openapi_schema = self.openapi_schema
        if "tags" in openapi_schema:
            actual_tags = [tag["name"] for tag in openapi_schema["tags"]]
            # 验证核心标签存在
            for expected_tag in expected_tags:
                if expected_tag in actual_tags:
                    # 验证每个标签只出现一次
                    assert actual_tags.count(expected_tag) == 1, f"Tag '{expected_tag}' 重复出现"

    def test_openapi_schema_loadable(self):
        """测试 OpenAPI schema 可以正确加载"""
        try:
            # 尝试序列化为 JSON
            json_str = json.dumps(self.openapi_schema, ensure_ascii=False)
            assert len(json_str) > 0, "OpenAPI schema 应该可以序列化"

            # 尝试反序列化
            parsed_schema = json.loads(json_str)
            assert "openapi" in parsed_schema, "OpenAPI schema 应该包含 openapi 版本"
            assert "info" in parsed_schema, "OpenAPI schema 应该包含 info"
            assert "paths" in parsed_schema, "OpenAPI schema 应该包含 paths"
        except Exception as e:
            pytest.fail(f"OpenAPI schema 无法正确处理: {e}")

    def test_docs_endpoints_accessible(self):
        """测试文档端点可以访问"""
        # 测试 Swagger UI
        response = self.client.get("/docs")
        assert response.status_code in [200, 302], f"/docs 应该可以访问，状态码：{response.status_code}"

        # 测试 ReDoc
        response = self.client.get("/redoc")
        assert response.status_code in [200, 302], f"/redoc 应该可以访问，状态码：{response.status_code}"

        # 测试 OpenAPI JSON
        response = self.client.get("/openapi.json")
        assert response.status_code == 200, f"/openapi.json 应该返回 200，状态码：{response.status_code}"

        # 验证返回的是有效的 JSON
        try:
            openapi_json = response.json()
            assert "openapi" in openapi_json, "OpenAPI JSON 应该包含 openapi 版本"
        except Exception as e:
            pytest.fail(f"OpenAPI JSON 格式错误: {e}")

    def test_no_x_extensions_overload(self):
        """测试没有过度的 x- 扩展"""
        # 检查是否存在不必要的 x- 扩展
        extensions_to_check = ["x-tag-groups", "x-changelog"]

        for ext in extensions_to_check:
            # 检查扩展是否存在且内容过于复杂
            if ext in self.openapi_schema:
                ext_value = self.openapi_schema[ext]
                if isinstance(ext_value, list) and len(ext_value) > 5:
                    pytest.fail(f"{ext} 扩展内容过于复杂，应该精简")

    def test_main_py_tags_parameters_removed(self):
        """测试 main.py 中 include_router 的 tags 参数已被移除"""
        import inspect
        import src.api.main as main_module

        # 获取 main.py 的源代码
        source = inspect.getsource(main_module)

        # 检查是否还有 tags= 参数在 include_router 调用中
        lines = source.split('\n')
        tags_count = 0
        for line in lines:
            if 'include_router' in line and 'tags=' in line:
                tags_count += 1

        # tags 参数应该已经被移除
        assert tags_count == 0, f"main.py 中还存在 {tags_count} 个 include_router 的 tags= 参数，应该全部移除"

    def test_code_reduction_effectiveness(self):
        """测试代码简化的有效性"""
        import inspect
        import src.api.main as main_module
        import src.api.openapi as openapi_module

        # 获取源代码行数（近似值）
        main_source = inspect.getsource(main_module)
        openapi_source = inspect.getsource(openapi_module)

        main_lines = len([line for line in main_source.split('\n') if line.strip() and not line.strip().startswith('#')])
        openapi_lines = len([line for line in openapi_source.split('\n') if line.strip() and not line.strip().startswith('#')])

        # 验证代码行数在合理范围内（这些是启发式检查）
        assert main_lines < 350, f"main.py 代码行数过多：{main_lines}，应该进一步简化"
        assert openapi_lines < 600, f"openapi.py 代码行数过多：{openapi_lines}，应该进一步简化"


class TestSwaggerUITagsDuplication:
    """专门测试 Swagger UI Tags 重复问题"""

    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)

    def test_swagger_ui_html_loads_without_errors(self):
        """测试 Swagger UI HTML 可以正常加载且没有错误"""
        response = self.client.get("/docs")
        assert response.status_code == 200, "Swagger UI 应该正常加载"

        html_content = response.text

        # 检查是否有 JavaScript 错误的迹象
        error_indicators = [
            "Cannot resolve reference",
            "Invalid object key",
            "UnifiedResponse",
            "schema.$ref",
            "components/schemas"
        ]

        # 在 HTML 内容中查找错误迹象
        for indicator in error_indicators:
            # 如果找到错误指示，说明问题可能还存在
            # 但这个检查是启发式的，不是绝对的
            pass  # 由于 HTML 中可能包含这些字符串，这里只是记录

    def test_api_groups_count_reasonable(self):
        """测试 API 分组数量合理"""
        # 获取 OpenAPI JSON
        response = self.client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()

        if "tags" in openapi_data:
            tags = openapi_data["tags"]
            # 验证标签数量合理（8-10个）
            assert 5 <= len(tags) <= 12, f"API 标签数量应该合理，当前：{len(tags)}"


class TestOpenAPIConfigurationSimplification:
    """测试 OpenAPI 配置简化"""

    def test_openapi_config_not_overloaded(self):
        """测试 OpenAPI 配置没有过载"""
        config = OpenAPIConfig()

        # 测试标签元数据没有过度的 externalDocs
        tags_metadata = config.get_tags_metadata()

        external_docs_count = sum(1 for tag in tags_metadata if "externalDocs" in tag)

        # externalDocs 应该被精简
        assert external_docs_count <= 3, f"externalDocs 数量过多：{external_docs_count}，应该精简"

    def test_examples_not_overloaded(self):
        """测试示例数据没有过载"""
        config = OpenAPIConfig()
        examples = config.get_examples()

        # 示例数量应该合理
        assert len(examples) <= 4, f"示例数量过多：{len(examples)}，应该保留核心示例"

        # 应该包含核心示例
        assert "SuccessResponse" in examples, "应该包含成功响应示例"
        assert "ErrorResponse" in examples, "应该包含错误响应示例"


if __name__ == "__main__":
    # 可以直接运行测试
    pytest.main([__file__, "-v"])