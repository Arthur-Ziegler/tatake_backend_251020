"""
测试OpenAPI配置和生成的功能

这个测试文件验证OpenAPI配置的正确性，确保描述、示例和元数据
能够正确传递到生成的OpenAPI规范中。
"""

import pytest
import sys
import os

# 添加src目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.api.main import app
from src.api.openapi import OpenAPIConfig


class TestOpenAPIGeneration:
    """测试OpenAPI生成功能"""

    def test_api_info_description_length(self):
        """测试API基础信息的描述长度应该大于24字符"""
        config = OpenAPIConfig()
        api_info = config.get_api_info()

        # 验证描述长度
        description = api_info.get("description", "")
        assert len(description) > 100, f"API描述太短，当前只有{len(description)}字符"

        # 验证关键内容存在
        assert "TaKeKe" in description, "描述中应该包含TaKeKe"
        assert "任务管理" in description, "描述中应该包含任务管理功能"

    def test_generated_openapi_description(self):
        """测试实际生成的OpenAPI规范中的描述"""
        openapi_schema = app.openapi()
        info = openapi_schema.get("info", {})
        description = info.get("description", "")

        # 这是当前的问题：生成的描述长度只有24字符
        assert len(description) > 100, f"生成的OpenAPI描述太短，当前只有{len(description)}字符"
        print(f"当前生成的描述长度: {len(description)}字符")

    def test_openapi_components_exist(self):
        """测试OpenAPI组件是否存在"""
        openapi_schema = app.openapi()
        components = openapi_schema.get("components", {})

        # 验证必要的组件存在
        assert "securitySchemes" in components, "缺少安全方案定义"
        assert len(components.get("securitySchemes", {})) > 0, "安全方案不能为空"

        # 当前问题：examples应该存在但实际不存在
        assert "examples" in components, "缺少示例数据定义"
        assert len(components.get("examples", {})) > 0, "示例数据不能为空"

    def test_tags_metadata_quality(self):
        """测试标签元数据的质量"""
        config = OpenAPIConfig()
        tags = config.get_tags_metadata()

        assert len(tags) >= 5, "标签数量应该不少于5个"

        for tag in tags:
            assert "name" in tag, "每个标签必须有name"
            assert "description" in tag, "每个标签必须有description"
            assert len(tag["description"]) > 10, "标签描述应该详细"

    def test_security_schemes_completeness(self):
        """测试安全方案的完整性"""
        config = OpenAPIConfig()
        security_schemes = config.get_security_schemes()

        assert "BearerAuth" in security_schemes, "必须包含Bearer认证"
        assert security_schemes["BearerAuth"]["type"] == "http", "Bearer认证类型应该是http"
        assert security_schemes["BearerAuth"]["scheme"] == "bearer", "Bearer认证scheme应该是bearer"

    def test_examples_quality(self):
        """测试示例数据的质量"""
        config = OpenAPIConfig()
        examples = config.get_examples()

        assert "SuccessResponse" in examples, "必须包含成功响应示例"
        assert "ErrorResponse" in examples, "必须包含错误响应示例"

        # 验证示例数据的完整性
        success_example = examples["SuccessResponse"]["value"]
        assert "code" in success_example, "成功响应应该包含code字段"
        assert "data" in success_example, "成功响应应该包含data字段"
        assert "traceId" in success_example, "成功响应应该包含traceId字段"

        # 验证新增的示例类型
        assert "TaskCompletionReward" in examples, "必须包含任务完成奖励示例"
        assert "AuthenticationSuccess" in examples, "必须包含认证成功示例"


if __name__ == "__main__":
    # 运行测试以验证当前问题
    test_class = TestOpenAPIGeneration()

    print("=== 测试OpenAPI配置问题 ===")
    try:
        test_class.test_api_info_description_length()
        print("✅ 配置类中的描述长度正常")
    except AssertionError as e:
        print(f"❌ 配置类描述问题: {e}")

    try:
        test_class.test_generated_openapi_description()
        print("✅ 生成的OpenAPI描述长度正常")
    except AssertionError as e:
        print(f"❌ 生成描述问题: {e}")

    try:
        test_class.test_openapi_components_exist()
        print("✅ OpenAPI组件完整")
    except AssertionError as e:
        print(f"❌ 组件问题: {e}")

    try:
        test_class.test_examples_quality()
        print("✅ 示例数据质量正常")
    except AssertionError as e:
        print(f"❌ 示例数据问题: {e}")

    print("\n=== 问题诊断完成 ===")