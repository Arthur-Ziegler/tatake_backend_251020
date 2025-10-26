"""
统一API响应格式测试

测试简化的统一响应格式，确保所有响应只包含
code、message、data三个字段。包括：
1. 成功响应创建
2. 错误响应创建
3. 特定状态码响应
4. 响应格式一致性验证

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import json
from fastapi import status
from fastapi.responses import JSONResponse

from src.api.responses import (
    create_success_response,
    create_error_response,
    create_not_found_response,
    create_unauthorized_response,
    create_forbidden_response
)


@pytest.mark.unit
class TestCreateSuccessResponse:
    """成功响应创建测试类"""

    def test_create_success_response_default(self):
        """测试默认成功响应"""
        result = create_success_response()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200

        content = json.loads(result.body)
        assert "code" in content
        assert "message" in content
        assert "data" in content

        assert content["code"] == 200
        assert content["message"] == "success"
        assert content["data"] is None

    def test_create_success_response_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "测试数据"}
        result = create_success_response(data=test_data)

        content = json.loads(result.body)
        assert content["data"] == test_data
        assert content["code"] == 200
        assert content["message"] == "success"

    def test_create_success_response_custom_message(self):
        """测试自定义消息的成功响应"""
        custom_message = "操作完成"
        result = create_success_response(message=custom_message)

        content = json.loads(result.body)
        assert content["message"] == custom_message
        assert content["code"] == 200
        assert content["data"] is None

    def test_create_success_response_custom_status_code(self):
        """测试自定义状态码的成功响应"""
        result = create_success_response(status_code=201)

        assert result.status_code == 201
        content = json.loads(result.body)
        assert content["code"] == 201
        assert content["message"] == "success"
        assert content["data"] is None

    def test_create_success_response_all_parameters(self):
        """测试所有参数的成功响应"""
        test_data = {"user_id": 123}
        custom_message = "用户创建成功"
        custom_status = 201

        result = create_success_response(
            data=test_data,
            message=custom_message,
            status_code=custom_status
        )

        assert result.status_code == custom_status
        content = json.loads(result.body)
        assert content["code"] == custom_status
        assert content["message"] == custom_message
        assert content["data"] == test_data

    def test_create_success_response_complex_data(self):
        """测试复杂数据结构的成功响应"""
        complex_data = {
            "user": {
                "id": 1,
                "profile": {
                    "name": "张三",
                    "emails": ["a@test.com", "b@test.com"]
                },
                "roles": ["admin", "user"]
            },
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }

        result = create_success_response(data=complex_data)

        content = json.loads(result.body)
        assert content["data"] == complex_data

    def test_create_success_response_list_data(self):
        """测试列表数据的成功响应"""
        list_data = [
            {"id": 1, "name": "任务1"},
            {"id": 2, "name": "任务2"},
            {"id": 3, "name": "任务3"}
        ]

        result = create_success_response(data=list_data)

        content = json.loads(result.body)
        assert content["data"] == list_data

    def test_create_success_response_empty_data(self):
        """测试空数据的成功响应"""
        empty_data = {}
        result = create_success_response(data=empty_data)

        content = json.loads(result.body)
        assert content["data"] == empty_data

    def test_create_success_response_format_consistency(self):
        """测试响应格式一致性"""
        result = create_success_response(data={"test": "data"})
        content = json.loads(result.body)

        # 验证只包含三个必需字段
        assert set(content.keys()) == {"code", "message", "data"}

        # 验证字段类型
        assert isinstance(content["code"], int)
        assert isinstance(content["message"], str)
        assert isinstance(content["data"], (dict, list, str, int, float, bool, type(None)))


@pytest.mark.unit
class TestCreateErrorResponse:
    """错误响应创建测试类"""

    def test_create_error_response_default(self):
        """测试默认错误响应"""
        result = create_error_response("测试错误")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

        content = json.loads(result.body)
        assert "code" in content
        assert "message" in content
        assert "data" in content

        assert content["code"] == 400
        assert content["message"] == "测试错误"
        assert content["data"] is None

    def test_create_error_response_custom_message(self):
        """测试自定义消息的错误响应"""
        error_message = "参数验证失败"
        result = create_error_response(error_message)

        content = json.loads(result.body)
        assert content["message"] == error_message
        assert content["code"] == 400
        assert content["data"] is None

    def test_create_error_response_custom_status_code(self):
        """测试自定义状态码的错误响应"""
        result = create_error_response("业务逻辑错误", status_code=422)

        assert result.status_code == 422
        content = json.loads(result.body)
        assert content["code"] == 422
        assert content["message"] == "业务逻辑错误"
        assert content["data"] is None

    def test_create_error_response_format_consistency(self):
        """测试错误响应格式一致性"""
        result = create_error_response("测试错误", status_code=500)
        content = json.loads(result.body)

        # 验证只包含三个必需字段
        assert set(content.keys()) == {"code", "message", "data"}

        # 验证字段值
        assert content["code"] == 500
        assert content["message"] == "测试错误"
        assert content["data"] is None

    def test_create_error_response_various_status_codes(self):
        """测试各种状态码的错误响应"""
        test_cases = [
            (400, "请求错误"),
            (401, "认证失败"),
            (403, "权限不足"),
            (404, "资源不存在"),
            (422, "参数验证失败"),
            (500, "服务器错误")
        ]

        for status_code, message in test_cases:
            result = create_error_response(message, status_code)

            assert result.status_code == status_code
            content = json.loads(result.body)
            assert content["code"] == status_code
            assert content["message"] == message
            assert content["data"] is None


@pytest.mark.unit
class TestCreateNotFoundResponse:
    """未找到响应创建测试类"""

    def test_create_not_found_response_default(self):
        """测试默认未找到响应"""
        result = create_not_found_response()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

        content = json.loads(result.body)
        assert content["code"] == 404
        assert content["message"] == "资源未找到"
        assert content["data"] is None

    def test_create_not_found_response_custom_message(self):
        """测试自定义消息的未找到响应"""
        custom_message = "用户ID不存在"
        result = create_not_found_response(custom_message)

        content = json.loads(result.body)
        assert content["code"] == 404
        assert content["message"] == custom_message
        assert content["data"] is None

    def test_create_not_found_response_format_consistency(self):
        """测试未找到响应格式一致性"""
        result = create_not_found_response("测试资源未找到")
        content = json.loads(result.body)

        # 验证只包含三个必需字段
        assert set(content.keys()) == {"code", "message", "data"}

        # 验证字段值
        assert content["code"] == 404
        assert content["message"] == "测试资源未找到"
        assert content["data"] is None


@pytest.mark.unit
class TestCreateUnauthorizedResponse:
    """未授权响应创建测试类"""

    def test_create_unauthorized_response_default(self):
        """测试默认未授权响应"""
        result = create_unauthorized_response()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 401

        content = json.loads(result.body)
        assert content["code"] == 401
        assert content["message"] == "未授权访问"
        assert content["data"] is None

    def test_create_unauthorized_response_custom_message(self):
        """测试自定义消息的未授权响应"""
        custom_message = "Token已过期"
        result = create_unauthorized_response(custom_message)

        content = json.loads(result.body)
        assert content["code"] == 401
        assert content["message"] == custom_message
        assert content["data"] is None

    def test_create_unauthorized_response_format_consistency(self):
        """测试未授权响应格式一致性"""
        result = create_unauthorized_response("认证失败")
        content = json.loads(result.body)

        # 验证只包含三个必需字段
        assert set(content.keys()) == {"code", "message", "data"}

        # 验证字段值
        assert content["code"] == 401
        assert content["message"] == "认证失败"
        assert content["data"] is None


@pytest.mark.unit
class TestCreateForbiddenResponse:
    """禁止访问响应创建测试类"""

    def test_create_forbidden_response_default(self):
        """测试默认禁止访问响应"""
        result = create_forbidden_response()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 403

        content = json.loads(result.body)
        assert content["code"] == 403
        assert content["message"] == "禁止访问"
        assert content["data"] is None

    def test_create_forbidden_response_custom_message(self):
        """测试自定义消息的禁止访问响应"""
        custom_message = "权限不足，无法访问此资源"
        result = create_forbidden_response(custom_message)

        content = json.loads(result.body)
        assert content["code"] == 403
        assert content["message"] == custom_message
        assert content["data"] is None

    def test_create_forbidden_response_format_consistency(self):
        """测试禁止访问响应格式一致性"""
        result = create_forbidden_response("访问被拒绝")
        content = json.loads(result.body)

        # 验证只包含三个必需字段
        assert set(content.keys()) == {"code", "message", "data"}

        # 验证字段值
        assert content["code"] == 403
        assert content["message"] == "访问被拒绝"
        assert content["data"] is None


@pytest.mark.integration
class TestResponseIntegration:
    """响应集成测试类"""

    def test_all_response_functions_format_consistency(self):
        """测试所有响应函数格式一致性"""
        # 创建各种响应
        responses = [
            create_success_response(data={"test": "success"}),
            create_error_response("测试错误", status_code=400),
            create_not_found_response("资源未找到"),
            create_unauthorized_response("未授权"),
            create_forbidden_response("禁止访问")
        ]

        for response in responses:
            content = json.loads(response.body)

            # 验证所有响应都只包含三个必需字段
            assert set(content.keys()) == {"code", "message", "data"}

            # 验证字段类型
            assert isinstance(content["code"], int)
            assert isinstance(content["message"], str)
            assert isinstance(content["data"], (dict, list, str, int, float, bool, type(None)))

    def test_status_code_consistency(self):
        """测试状态码一致性"""
        # 验证响应的状态码与响应体中的code一致
        test_cases = [
            (create_success_response(), 200),
            (create_success_response(status_code=201), 201),
            (create_error_response("错误", status_code=400), 400),
            (create_not_found_response(), 404),
            (create_unauthorized_response(), 401),
            (create_forbidden_response(), 403)
        ]

        for response, expected_status in test_cases:
            assert response.status_code == expected_status

            content = json.loads(response.body)
            assert content["code"] == expected_status

    def test_response_content_type(self):
        """测试响应内容类型"""
        responses = [
            create_success_response(),
            create_error_response("错误"),
            create_not_found_response(),
            create_unauthorized_response(),
            create_forbidden_response()
        ]

        for response in responses:
            assert response.headers["content-type"] == "application/json"

    def test_response_serialization(self):
        """测试响应序列化"""
        # 测试包含各种数据类型的响应
        complex_data = {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3, {"nested": "value"}],
            "object": {"nested_key": "nested_value"}
        }

        result = create_success_response(data=complex_data)
        content = json.loads(result.body)

        assert content["data"] == complex_data

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_data = {
            "chinese": "测试中文",
            "emoji": "😀🎉",
            "special": "特殊字符：@#$%^&*()"
        }

        result = create_success_response(data=unicode_data)
        content = json.loads(result.body)

        assert content["data"] == unicode_data

    def test_error_message_chinese(self):
        """测试中文错误消息"""
        error_messages = [
            "参数验证失败",
            "用户不存在",
            "权限不足",
            "服务器内部错误",
            "数据库连接失败"
        ]

        for message in error_messages:
            result = create_error_response(message)
            content = json.loads(result.body)
            assert content["message"] == message

    def test_real_world_scenarios(self):
        """测试真实世界场景"""
        # 场景1：用户登录成功
        login_data = {
            "user_id": 123,
            "username": "testuser",
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        }
        login_response = create_success_response(
            data=login_data,
            message="登录成功"
        )

        # 场景2：用户注册失败
        register_response = create_error_response(
            message="邮箱已被注册",
            status_code=409
        )

        # 场景3：访问不存在的资源
        not_found_response = create_not_found_response("任务ID不存在")

        # 验证所有场景的响应都符合格式
        for response in [login_response, register_response, not_found_response]:
            content = json.loads(response.body)
            assert set(content.keys()) == {"code", "message", "data"}
            assert content["code"] == response.status_code


@pytest.mark.parametrize("status_code,message", [
    (200, "操作成功"),
    (201, "创建成功"),
    (400, "请求错误"),
    (401, "未授权"),
    (403, "禁止访问"),
    (404, "资源未找到"),
    (422, "参数验证失败"),
    (500, "服务器错误")
])
def test_status_code_and_message_combinations(status_code, message):
    """参数化测试状态码和消息组合"""
    if status_code >= 400:
        # 错误响应
        result = create_error_response(message, status_code)
    else:
        # 成功响应
        result = create_success_response(message=message, status_code=status_code)

    assert result.status_code == status_code
    content = json.loads(result.body)
    assert content["code"] == status_code
    assert content["message"] == message


@pytest.mark.parametrize("data_type,test_data", [
    ("dict", {"key": "value"}),
    ("list", [1, 2, 3]),
    ("string", "test string"),
    ("integer", 42),
    ("float", 3.14),
    ("boolean", True),
    ("null", None),
    ("empty_dict", {}),
    ("empty_list", [])
])
def test_various_data_types(data_type, test_data):
    """参数化测试各种数据类型"""
    result = create_success_response(data=test_data)
    content = json.loads(result.body)
    assert content["data"] == test_data


@pytest.mark.parametrize("function_name,expected_status", [
    ("create_success_response", 200),
    ("create_error_response", 400),
    ("create_not_found_response", 404),
    ("create_unauthorized_response", 401),
    ("create_forbidden_response", 403)
])
def test_function_default_status_codes(function_name, expected_status):
    """参数化测试函数默认状态码"""
    function_map = {
        "create_success_response": create_success_response,
        "create_error_response": lambda msg: create_error_response(msg),
        "create_not_found_response": create_not_found_response,
        "create_unauthorized_response": create_unauthorized_response,
        "create_forbidden_response": create_forbidden_response
    }

    func = function_map[function_name]

    if function_name == "create_error_response":
        result = func("测试错误")
    else:
        result = func()

    assert result.status_code == expected_status

    content = json.loads(result.body)
    assert content["code"] == expected_status


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "roles": ["user"]
    }


@pytest.fixture
def sample_error_message():
    """示例错误消息"""
    return "测试错误消息"


def test_with_fixtures(sample_user_data, sample_error_message):
    """使用fixtures的测试"""
    # 测试成功响应
    success_result = create_success_response(
        data=sample_user_data,
        message="用户信息获取成功"
    )
    success_content = json.loads(success_result.body)
    assert success_content["data"] == sample_user_data

    # 测试错误响应
    error_result = create_error_response(sample_error_message)
    error_content = json.loads(error_result.body)
    assert error_content["message"] == sample_error_message


def test_response_edge_cases():
    """测试边界情况"""
    # 测试空字符串
    result1 = create_success_response(data="", message="")
    content1 = json.loads(result1.body)
    assert content1["data"] == ""
    assert content1["message"] == ""

    # 测试零值
    result2 = create_success_response(data=0)
    content2 = json.loads(result2.body)
    assert content2["data"] == 0

    # 测试False值
    result3 = create_success_response(data=False)
    content3 = json.loads(result3.body)
    assert content3["data"] is False

    # 测试嵌套的None值
    nested_data = {"key": None, "list": [None, 1, "test"]}
    result4 = create_success_response(data=nested_data)
    content4 = json.loads(result4.body)
    assert content4["data"] == nested_data