"""
Swagger UI优化测试套件

这个测试文件用于验证当前OpenAPI实现的状态，并确保所有优化工作符合预期。
采用TDD方法，先定义测试标准，然后实现改进。

测试覆盖：
1. 基础OpenAPI配置质量
2. 描述长度和内容质量
3. 示例数据完整性
4. OpenAPI 3.1规范合规性
5. 中文化和本地化
6. 变更日志功能
"""

import pytest
import sys
import os

# 添加src目录到Python路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.api.main import app
from src.api.openapi import OpenAPIConfig


class TestOpenAPIConfiguration:
    """测试OpenAPI配置的基础质量"""

    def test_api_info_description_quality(self):
        """测试API基础信息的描述质量应该满足企业级标准"""
        config = OpenAPIConfig()
        api_info = config.get_api_info()

        # 验证描述长度（要求从24字符提升到500+字符）
        description = api_info.get("description", "")
        assert len(description) > 500, f"API描述太短，当前只有{len(description)}字符，需要500+字符"

        # 验证关键内容存在
        assert "TaKeKe" in description, "描述中应该包含TaKeKe"
        assert "任务管理" in description, "描述中应该包含任务管理功能"
        assert "奖励系统" in description, "描述中应该包含奖励系统功能"
        assert "API" in description, "描述中应该包含API相关信息"

    def test_tags_metadata_completeness(self):
        """测试标签元数据的完整性"""
        config = OpenAPIConfig()
        tags = config.get_tags_metadata()

        assert len(tags) >= 5, f"标签数量太少，当前只有{len(tags)}个，需要至少5个"

        # 验证每个标签的完整性
        for tag in tags:
            assert "name" in tag, f"标签{tag}缺少name字段"
            assert "description" in tag, f"标签{tag}缺少description字段"
            assert len(tag["description"]) > 10, f"标签{tag['name']}的描述太短"

    def test_security_schemes_completeness(self):
        """测试安全方案的完整性"""
        config = OpenAPIConfig()
        security_schemes = config.get_security_schemes()

        assert "BearerAuth" in security_schemes, "必须包含Bearer认证"
        bearer_auth = security_schemes["BearerAuth"]
        assert bearer_auth["type"] == "http", "Bearer认证类型应该是http"
        assert bearer_auth["scheme"] == "bearer", "Bearer认证scheme应该是bearer"
        assert "description" in bearer_auth, "Bearer认证应该有详细描述"

    def test_examples_quality_and_diversity(self):
        """测试示例数据的质量和多样性"""
        config = OpenAPIConfig()
        examples = config.get_examples()

        # 验证基础示例存在
        assert "SuccessResponse" in examples, "必须包含成功响应示例"
        assert "ErrorResponse" in examples, "必须包含错误响应示例"

        # 验证示例的完整性
        success_example = examples["SuccessResponse"]["value"]
        assert "code" in success_example, "成功响应应该包含code字段"
        assert "data" in success_example, "成功响应应该包含data字段"
        assert "traceId" in success_example, "成功响应应该包含traceId字段"

        # 验证业务场景示例
        expected_business_examples = [
            "TaskCompletionReward",
            "AuthenticationSuccess"
        ]
        for example_name in expected_business_examples:
            assert example_name in examples, f"必须包含{example_name}示例"

    def test_server_info_configuration(self):
        """测试服务器信息配置"""
        config = OpenAPIConfig()
        servers = config.get_server_info()

        assert len(servers) >= 1, "至少需要配置一个服务器"

        for server in servers:
            assert "url" in server, "服务器配置必须包含url"
            assert "description" in server, "服务器配置必须包含描述"


class TestGeneratedOpenAPICompliance:
    """测试生成的OpenAPI规范的合规性"""

    def test_openapi_description_transfer(self):
        """测试OpenAPI描述是否正确传递到生成的规范"""
        openapi_schema = app.openapi()
        info = openapi_schema.get("info", {})
        description = info.get("description", "")

        # 这是关键测试：确保配置中的长描述正确传递
        assert len(description) > 500, f"生成的OpenAPI描述太短，当前只有{len(description)}字符"

    def test_components_existence_and_quality(self):
        """测试组件的存在性和质量"""
        openapi_schema = app.openapi()
        components = openapi_schema.get("components", {})

        # 验证必要组件存在
        assert "securitySchemes" in components, "缺少安全方案定义"
        assert "examples" in components, "缺少示例数据定义"
        assert "schemas" in components, "缺少Schema定义"

        # 验证组件内容质量
        security_schemes = components.get("securitySchemes", {})
        assert len(security_schemes) >= 1, "安全方案不能为空"

        examples = components.get("examples", {})
        assert len(examples) >= 4, f"示例数据太少，当前只有{len(examples)}个"

        schemas = components.get("schemas", {})
        assert len(schemas) >= 3, f"Schema定义太少，当前只有{len(schemas)}个"

    def test_openapi_31_compliance(self):
        """测试OpenAPI 3.1规范合规性"""
        openapi_schema = app.openapi()

        # 验证基础OpenAPI 3.1结构
        assert "openapi" in openapi_schema, "缺少openapi版本字段"
        assert "info" in openapi_schema, "缺少info字段"
        assert "paths" in openapi_schema, "缺少paths字段"

        # 验证扩展功能
        assert "x-tag-groups" in openapi_schema, "缺少标签分组扩展"
        assert "x-changelog" in openapi_schema, "缺少变更日志扩展"

    def test_changelog_system_functionality(self):
        """测试变更日志系统功能"""
        openapi_schema = app.openapi()
        changelog = openapi_schema.get("x-changelog", [])

        assert len(changelog) >= 1, "变更日志不能为空"

        # 验证每个变更记录的完整性
        for change in changelog:
            assert "version" in change, "变更记录必须包含版本号"
            assert "date" in change, "变更记录必须包含日期"
            assert "changes" in change, "变更记录必须包含变更内容"

    def test_chinese_localization_quality(self):
        """测试中文化质量"""
        openapi_schema = app.openapi()

        # 验证主要文本内容是否为中文
        info = openapi_schema.get("info", {})
        description = info.get("description", "")
        assert "TaKeKe" in description, "描述应该包含中文内容"
        assert "任务" in description, "描述应该包含中文任务相关内容"

        # 验证标签是否为中文
        tag_groups = openapi_schema.get("x-tag-groups", [])
        for group in tag_groups:
            tags = group.get("tags", [])
            for tag in tags:
                # 至少应该有一些中文标签
                if any(char in tag for char in "认证任务奖励系统"):
                    return True

        # 如果没有找到中文标签，这里会失败
        assert False, "标签中应该包含中文内容"


class TestBusinessScenarioExamples:
    """测试业务场景示例的完整性"""

    def test_endpoint_documentation_quality(self):
        """测试端点文档质量"""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        total_endpoints = 0
        documented_endpoints = 0

        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    total_endpoints += 1

                    # 检查是否有基本文档
                    summary = details.get("summary", "")
                    description = details.get("description", "")

                    if len(summary) > 5 and len(description) > 20:
                        documented_endpoints += 1

        documentation_rate = documented_endpoints / total_endpoints if total_endpoints > 0 else 0
        assert documentation_rate >= 0.7, f"端点文档覆盖率太低，当前只有{documentation_rate:.1%}"

    def test_authentication_flow_examples(self):
        """测试认证流程示例"""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        # 检查认证端点
        auth_endpoints = ['/auth/login', '/auth/register', '/auth/guest/init']
        found_auth_endpoints = 0

        for endpoint in auth_endpoints:
            if endpoint in paths:
                found_auth_endpoints += 1
                method_details = paths[endpoint].get('post', {})

                # 检查是否有描述
                description = method_details.get('description', '')
                assert len(description) > 10, f"{endpoint}端点描述太短"

        assert found_auth_endpoints >= 2, f"认证端点太少，只找到{found_auth_endpoints}个"

    def test_task_management_examples(self):
        """测试任务管理示例"""
        openapi_schema = app.openapi()
        paths = openapi_schema.get("paths", {})

        # 检查任务管理端点
        task_endpoints = ['/tasks/', '/tasks/{task_id}', '/tasks/{task_id}/complete']
        found_task_endpoints = 0

        for endpoint in task_endpoints:
            # 处理路径参数
            matching_paths = [p for p in paths.keys() if
                            endpoint.replace('{task_id}', '{task_id}') in p or
                            endpoint.replace('{task_id}', '{id}') in p]

            if matching_paths:
                found_task_endpoints += len(matching_paths)

        assert found_task_endpoints >= 2, f"任务管理端点太少，只找到{found_task_endpoints}个"


def run_comprehensive_test():
    """运行综合测试以评估当前状态"""
    print("=== Swagger UI 优化状态评估 ===")

    # 运行所有测试
    test_classes = [
        TestOpenAPIConfiguration,
        TestGeneratedOpenAPICompliance,
        TestBusinessScenarioExamples
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]

        for test_method in test_methods:
            total_tests += 1
            try:
                getattr(test_instance, test_method)()
                passed_tests += 1
                print(f"✅ {test_class.__name__}.{test_method}")
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test_method}: {str(e)}")
                print(f"❌ {test_class.__name__}.{test_method}: {str(e)}")

    print(f"\n=== 测试结果总结 ===")
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {len(failed_tests)}")
    print(f"通过率: {passed_tests/total_tests:.1%}")

    if failed_tests:
        print(f"\n=== 失败测试详情 ===")
        for failure in failed_tests:
            print(f"❌ {failure}")

    return passed_tests == total_tests


if __name__ == "__main__":
    # 运行综合评估
    success = run_comprehensive_test()
    exit(0 if success else 1)