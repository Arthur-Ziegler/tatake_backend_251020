"""
响应工具模块测试

测试统一响应格式工具，包括：
1. 成功响应创建
2. 错误响应创建
3. 分页响应创建
4. JSON响应生成
5. 标准响应类方法
6. HTTP异常处理
7. 响应数据验证

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import json
from unittest.mock import Mock
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import status

from src.api.response_utils import (
    ResponseCode,
    create_success_response,
    create_error_response,
    create_pagination_response,
    json_response,
    error_json_response,
    StandardResponse,
    response,
    http_exception_handler,
    validate_response_data
)


@pytest.mark.unit
class TestResponseCode:
    """响应状态码常量测试类"""

    def test_response_code_constants(self):
        """测试响应状态码常量"""
        # 验证所有常量值正确
        assert ResponseCode.SUCCESS == 200
        assert ResponseCode.CREATED == 201
        assert ResponseCode.BAD_REQUEST == 400
        assert ResponseCode.UNAUTHORIZED == 401
        assert ResponseCode.PAYMENT_REQUIRED == 402
        assert ResponseCode.FORBIDDEN == 403
        assert ResponseCode.NOT_FOUND == 404
        assert ResponseCode.INTERNAL_ERROR == 500

    def test_response_code_type(self):
        """测试响应状态码类型"""
        # 验证所有常量都是整数
        for attr_name in dir(ResponseCode):
            if not attr_name.startswith('_'):
                attr_value = getattr(ResponseCode, attr_name)
                assert isinstance(attr_value, int)


@pytest.mark.unit
class TestCreateSuccessResponse:
    """成功响应创建测试类"""

    def test_create_success_response_default(self):
        """测试默认成功响应"""
        result = create_success_response()

        assert result["code"] == 200
        assert result["message"] == "操作成功"
        assert result["data"] is None

    def test_create_success_response_with_data(self):
        """测试带数据的成功响应"""
        test_data = {"id": 1, "name": "test"}
        result = create_success_response(data=test_data)

        assert result["code"] == 200
        assert result["message"] == "操作成功"
        assert result["data"] == test_data

    def test_create_success_response_custom_message(self):
        """测试自定义消息的成功响应"""
        custom_message = "创建用户成功"
        result = create_success_response(message=custom_message)

        assert result["code"] == 200
        assert result["message"] == custom_message
        assert result["data"] is None

    def test_create_success_response_custom_code(self):
        """测试自定义状态码的成功响应"""
        result = create_success_response(code=201)

        assert result["code"] == 201
        assert result["message"] == "操作成功"
        assert result["data"] is None

    def test_create_success_response_all_parameters(self):
        """测试所有参数的成功响应"""
        test_data = {"id": 1}
        custom_message = "更新成功"
        custom_code = 201

        result = create_success_response(
            data=test_data,
            message=custom_message,
            code=custom_code
        )

        assert result["code"] == custom_code
        assert result["message"] == custom_message
        assert result["data"] == test_data

    def test_create_success_response_complex_data(self):
        """测试复杂数据的成功响应"""
        complex_data = {
            "user": {
                "id": 1,
                "profile": {
                    "name": "张三",
                    "email": "zhangsan@example.com"
                }
            },
            "permissions": ["read", "write"]
        }

        result = create_success_response(data=complex_data)

        assert result["data"] == complex_data

    def test_create_success_response_list_data(self):
        """测试列表数据的成功响应"""
        list_data = [1, 2, 3, "test", {"key": "value"}]

        result = create_success_response(data=list_data)

        assert result["data"] == list_data

    def test_create_success_response_empty_data(self):
        """测试空数据的成功响应"""
        empty_data = {}

        result = create_success_response(data=empty_data)

        assert result["data"] == empty_data


@pytest.mark.unit
class TestCreateErrorResponse:
    """错误响应创建测试类"""

    def test_create_error_response_default(self):
        """测试默认错误响应"""
        result = create_error_response("测试错误")

        assert result["code"] == 400
        assert result["message"] == "测试错误"
        assert result["data"] == {}

    def test_create_error_response_custom_code(self):
        """测试自定义状态码的错误响应"""
        result = create_error_response("未找到", code=404)

        assert result["code"] == 404
        assert result["message"] == "未找到"
        assert result["data"] == {}

    def test_create_error_response_with_data(self):
        """测试带数据的错误响应"""
        error_data = {"field": "email", "error": "邮箱格式无效"}
        result = create_error_response("验证失败", data=error_data)

        assert result["code"] == 400
        assert result["message"] == "验证失败"
        assert result["data"] == error_data

    def test_create_error_response_with_detail(self):
        """测试带详细信息的错误响应"""
        result = create_error_response("参数错误", detail="用户名不能为空")

        # detail参数在当前实现中未被使用，但应该能正常传递
        assert result["code"] == 400
        assert result["message"] == "参数错误"
        assert result["data"] == {}

    def test_create_error_response_none_data(self):
        """测试None数据的错误响应"""
        result = create_error_response("测试错误", data=None)

        assert result["data"] == {}

    def test_create_error_response_all_parameters(self):
        """测试所有参数的错误响应"""
        error_data = {"field": "password"}
        result = create_error_response(
            message="密码错误",
            code=401,
            data=error_data,
            detail="密码长度不足"
        )

        assert result["code"] == 401
        assert result["message"] == "密码错误"
        assert result["data"] == error_data


@pytest.mark.unit
class TestCreatePaginationResponse:
    """分页响应创建测试类"""

    def test_create_pagination_response_default(self):
        """测试默认分页响应"""
        items = [1, 2, 3]
        result = create_pagination_response(
            items=items,
            current_page=1,
            total_pages=10,
            total_count=100
        )

        assert result["code"] == 200
        assert result["message"] == "获取成功"
        assert result["data"]["items"] == items
        assert result["data"]["pagination"]["current_page"] == 1
        assert result["data"]["pagination"]["total_pages"] == 10
        assert result["data"]["pagination"]["total_count"] == 100

    def test_create_pagination_response_custom_page_size(self):
        """测试自定义页面大小的分页响应"""
        items = ["a", "b"]
        result = create_pagination_response(
            items=items,
            current_page=2,
            total_pages=5,
            total_count=50,
            page_size=10
        )

        assert result["data"]["items"] == items
        assert result["data"]["pagination"]["current_page"] == 2
        assert result["data"]["pagination"]["total_pages"] == 5
        assert result["data"]["pagination"]["total_count"] == 50

    def test_create_pagination_response_custom_message(self):
        """测试自定义消息的分页响应"""
        items = []
        result = create_pagination_response(
            items=items,
            current_page=1,
            total_pages=0,
            total_count=0,
            message="无数据"
        )

        assert result["message"] == "无数据"
        assert result["data"]["items"] == []

    def test_create_pagination_response_complex_items(self):
        """测试复杂项的分页响应"""
        complex_items = [
            {"id": 1, "name": "任务1", "status": "completed"},
            {"id": 2, "name": "任务2", "status": "pending"}
        ]

        result = create_pagination_response(
            items=complex_items,
            current_page=1,
            total_pages=1,
            total_count=2
        )

        assert result["data"]["items"] == complex_items

    def test_create_pagination_response_empty_items(self):
        """测试空项的分页响应"""
        result = create_pagination_response(
            items=[],
            current_page=1,
            total_pages=0,
            total_count=0
        )

        assert result["data"]["items"] == []
        assert result["data"]["pagination"]["total_pages"] == 0
        assert result["data"]["pagination"]["total_count"] == 0

    def test_create_pagination_response_large_numbers(self):
        """测试大数值的分页响应"""
        result = create_pagination_response(
            items=[1, 2, 3],
            current_page=1000,
            total_pages=5000,
            total_count=100000
        )

        assert result["data"]["pagination"]["current_page"] == 1000
        assert result["data"]["pagination"]["total_pages"] == 5000
        assert result["data"]["pagination"]["total_count"] == 100000


@pytest.mark.unit
class TestJsonResponse:
    """JSON响应测试类"""

    def test_json_response_default(self):
        """测试默认JSON响应"""
        result = json_response()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200

        # 验证内容
        content = json.loads(result.body)
        assert content["code"] == 200
        assert content["message"] == "操作成功"
        assert content["data"] is None

    def test_json_response_with_data(self):
        """测试带数据的JSON响应"""
        test_data = {"test": "data"}
        result = json_response(data=test_data)

        content = json.loads(result.body)
        assert content["data"] == test_data

    def test_json_response_custom_message(self):
        """测试自定义消息的JSON响应"""
        custom_message = "创建成功"
        result = json_response(message=custom_message)

        content = json.loads(result.body)
        assert content["message"] == custom_message

    def test_json_response_custom_code(self):
        """测试自定义状态码的JSON响应"""
        result = json_response(code=201)

        content = json.loads(result.body)
        assert content["code"] == 201

    def test_json_response_custom_status_code(self):
        """测试自定义HTTP状态码的JSON响应"""
        result = json_response(status_code=201)

        assert result.status_code == 201

    def test_json_response_all_parameters(self):
        """测试所有参数的JSON响应"""
        test_data = {"id": 1}
        result = json_response(
            data=test_data,
            message="创建用户成功",
            code=201,
            status_code=201
        )

        assert result.status_code == 201
        content = json.loads(result.body)
        assert content["code"] == 201
        assert content["message"] == "创建用户成功"
        assert content["data"] == test_data


@pytest.mark.unit
class TestErrorJsonResponse:
    """错误JSON响应测试类"""

    def test_error_json_response_default(self):
        """测试默认错误JSON响应"""
        result = error_json_response("错误消息")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

        content = json.loads(result.body)
        assert content["code"] == 400
        assert content["message"] == "错误消息"
        assert content["data"] == {}

    def test_error_json_response_custom_code(self):
        """测试自定义状态码的错误JSON响应"""
        result = error_json_response("未找到", code=404)

        content = json.loads(result.body)
        assert content["code"] == 404

    def test_error_json_response_custom_status_code(self):
        """测试自定义HTTP状态码的错误JSON响应"""
        result = error_json_response("未授权", status_code=401)

        assert result.status_code == 401

    def test_error_json_response_with_data(self):
        """测试带数据的错误JSON响应"""
        error_data = {"field": "email", "error": "格式无效"}
        result = error_json_response("验证失败", data=error_data)

        content = json.loads(result.body)
        assert content["data"] == error_data

    def test_error_json_response_all_parameters(self):
        """测试所有参数的错误JSON响应"""
        error_data = {"detail": "详细错误信息"}
        result = error_json_response(
            message="业务错误",
            code=422,
            status_code=422,
            data=error_data
        )

        assert result.status_code == 422
        content = json.loads(result.body)
        assert content["code"] == 422
        assert content["message"] == "业务错误"
        assert content["data"] == error_data


@pytest.mark.unit
class TestStandardResponse:
    """标准响应类测试类"""

    def test_response_instance(self):
        """测试响应实例"""
        # 验证response实例存在
        assert response is not None
        assert isinstance(response, StandardResponse)

    def test_success_method(self):
        """测试成功响应方法"""
        test_data = {"test": "data"}
        result = StandardResponse.success(data=test_data)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200

        content = json.loads(result.body)
        assert content["code"] == 200
        assert content["data"] == test_data

    def test_created_method(self):
        """测试创建成功响应方法"""
        test_data = {"id": 1}
        result = StandardResponse.created(data=test_data)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 201

        content = json.loads(result.body)
        assert content["code"] == 201
        assert content["message"] == "创建成功"
        assert content["data"] == test_data

    def test_bad_request_method(self):
        """测试请求错误响应方法"""
        error_data = {"field": "name", "error": "必填"}
        result = StandardResponse.bad_request(
            message="参数错误",
            data=error_data
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

        content = json.loads(result.body)
        assert content["code"] == 400
        assert content["message"] == "参数错误"
        assert content["data"] == error_data

    def test_unauthorized_method(self):
        """测试未授权响应方法"""
        result = StandardResponse.unauthorized("token无效")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 401

        content = json.loads(result.body)
        assert content["code"] == 401
        assert content["message"] == "token无效"

    def test_payment_required_method(self):
        """测试积分不足响应方法"""
        result = StandardResponse.payment_required("积分余额不足")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 402

        content = json.loads(result.body)
        assert content["code"] == 402
        assert content["message"] == "积分余额不足"

    def test_forbidden_method(self):
        """测试禁止操作响应方法"""
        result = StandardResponse.forbidden("权限不足")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 403

        content = json.loads(result.body)
        assert content["code"] == 403
        assert content["message"] == "权限不足"

    def test_not_found_method(self):
        """测试资源不存在响应方法"""
        result = StandardResponse.not_found("用户不存在")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

        content = json.loads(result.body)
        assert content["code"] == 404
        assert content["message"] == "用户不存在"

    def test_server_error_method(self):
        """测试服务器错误响应方法"""
        result = StandardResponse.server_error("数据库连接失败")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

        content = json.loads(result.body)
        assert content["code"] == 500
        assert content["message"] == "数据库连接失败"

    def test_paginated_method(self):
        """测试分页响应方法"""
        items = [{"id": 1}, {"id": 2}]
        result = StandardResponse.paginated(
            items=items,
            current_page=1,
            total_pages=5,
            total_count=50,
            page_size=10,
            message="获取用户列表成功"
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200

        content = json.loads(result.body)
        assert content["code"] == 200
        assert content["message"] == "获取用户列表成功"
        assert content["data"]["items"] == items
        assert content["data"]["pagination"]["current_page"] == 1
        assert content["data"]["pagination"]["total_pages"] == 5
        assert content["data"]["pagination"]["total_count"] == 50

    def test_default_messages(self):
        """测试默认消息"""
        # 测试各种默认消息
        methods_with_default_messages = [
            (StandardResponse.success, "操作成功"),
            (StandardResponse.created, "创建成功"),
            (StandardResponse.bad_request, "请求参数错误"),
            (StandardResponse.unauthorized, "未授权访问"),
            (StandardResponse.payment_required, "积分不足"),
            (StandardResponse.forbidden, "禁止操作"),
            (StandardResponse.not_found, "资源不存在"),
            (StandardResponse.server_error, "服务器内部错误")
        ]

        for method, expected_message in methods_with_default_messages:
            result = method()
            content = json.loads(result.body)
            assert content["message"] == expected_message


@pytest.mark.unit
class TestHttpExceptionHandler:
    """HTTP异常处理器测试类"""

    def test_http_exception_handler_400(self):
        """测试400异常处理"""
        exc = HTTPException(status_code=400, detail="参数错误")
        result = http_exception_handler(exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

        content = json.loads(result.body)
        assert content["code"] == 400
        assert content["message"] == "参数错误"

    def test_http_exception_handler_401(self):
        """测试401异常处理"""
        exc = HTTPException(status_code=401, detail="未授权")
        result = http_exception_handler(exc)

        assert result.status_code == 401
        content = json.loads(result.body)
        assert content["code"] == 401
        assert content["message"] == "未授权"

    def test_http_exception_handler_404(self):
        """测试404异常处理"""
        exc = HTTPException(status_code=404, detail="资源不存在")
        result = http_exception_handler(exc)

        assert result.status_code == 404
        content = json.loads(result.body)
        assert content["code"] == 404
        assert content["message"] == "资源不存在"

    def test_http_exception_handler_500(self):
        """测试500异常处理"""
        exc = HTTPException(status_code=500, detail="服务器错误")
        result = http_exception_handler(exc)

        assert result.status_code == 500
        content = json.loads(result.body)
        assert content["code"] == 500
        assert content["message"] == "服务器错误"

    def test_http_exception_handler_without_detail(self):
        """测试无详细信息的异常处理"""
        exc = HTTPException(status_code=400)
        result = http_exception_handler(exc)

        content = json.loads(result.body)
        assert content["message"] == "请求失败"

    def test_http_exception_handler_unknown_status_code(self):
        """测试未知状态码的异常处理"""
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        result = http_exception_handler(exc)

        assert result.status_code == 418
        content = json.loads(result.body)
        assert content["code"] == 500  # 未知状态码映射到500
        assert content["message"] == "I'm a teapot"

    def test_status_code_mapping_completeness(self):
        """测试状态码映射完整性"""
        # 测试所有映射的状态码
        status_codes = [400, 401, 402, 403, 404, 500]
        expected_codes = [400, 401, 402, 403, 404, 500]

        for http_status, expected_code in zip(status_codes, expected_codes):
            exc = HTTPException(status_code=http_status, detail="test")
            result = http_exception_handler(exc)
            content = json.loads(result.body)
            assert content["code"] == expected_code


@pytest.mark.unit
class TestValidateResponseData:
    """响应数据验证测试类"""

    def test_validate_none_data(self):
        """测试None数据验证"""
        assert validate_response_data(None) is True

    def test_validate_basic_types(self):
        """测试基本类型数据验证"""
        # 字符串
        assert validate_response_data("test string") is True

        # 整数
        assert validate_response_data(42) is True

        # 浮点数
        assert validate_response_data(3.14) is True

        # 布尔值
        assert validate_response_data(True) is True
        assert validate_response_data(False) is True

    def test_validate_dict_data(self):
        """测试字典数据验证"""
        # 空字典
        assert validate_response_data({}) is True

        # 简单字典
        assert validate_response_data({"key": "value"}) is True

        # 复杂嵌套字典
        complex_dict = {
            "user": {
                "id": 1,
                "profile": {
                    "name": "张三",
                    "emails": ["a@example.com", "b@example.com"]
                }
            },
            "permissions": ["read", "write"]
        }
        assert validate_response_data(complex_dict) is True

    def test_validate_list_data(self):
        """测试列表数据验证"""
        # 空列表
        assert validate_response_data([]) is True

        # 简单列表
        assert validate_response_data([1, 2, 3]) is True

        # 混合类型列表
        mixed_list = [1, "string", {"key": "value"}, [4, 5]]
        assert validate_response_data(mixed_list) is True

    def test_validate_serializable_objects(self):
        """测试可序列化对象验证"""
        # 具有自定义__dict__的对象
        class TestClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        test_obj = TestClass()
        assert validate_response_data(test_obj) is True

    def test_validate_non_serializable_data(self):
        """测试不可序列化数据验证"""
        # 函数对象
        def test_function():
            pass

        assert validate_response_data(test_function) is False

        # 生成器对象
        def generator():
            yield 1
            yield 2

        gen = generator()
        assert validate_response_data(gen) is False

    def test_validate_circular_reference(self):
        """测试循环引用数据验证"""
        # 创建循环引用
        circular_dict = {}
        circular_dict["self"] = circular_dict

        # 应该返回False，因为无法序列化
        assert validate_response_data(circular_dict) is False


@pytest.mark.integration
class TestResponseUtilsIntegration:
    """响应工具集成测试类"""

    def test_complete_response_flow(self):
        """测试完整响应流程"""
        # 创建成功响应
        success_data = {"user": {"id": 1, "name": "张三"}}
        success_response = StandardResponse.success(
            data=success_data,
            message="用户创建成功"
        )

        # 验证响应结构
        assert isinstance(success_response, JSONResponse)
        assert success_response.status_code == 200

        content = json.loads(success_response.body)
        assert content["code"] == 200
        assert content["message"] == "用户创建成功"
        assert content["data"] == success_data

    def test_error_response_flow(self):
        """测试错误响应流程"""
        # 模拟HTTP异常
        http_exc = HTTPException(
            status_code=404,
            detail="用户ID不存在"
        )

        # 处理异常
        error_response = http_exception_handler(http_exc)

        # 验证错误响应
        assert isinstance(error_response, JSONResponse)
        assert error_response.status_code == 404

        content = json.loads(error_response.body)
        assert content["code"] == 404
        assert content["message"] == "用户ID不存在"

    def test_pagination_response_flow(self):
        """测试分页响应流程"""
        # 模拟分页数据
        users = [
            {"id": 1, "name": "用户1"},
            {"id": 2, "name": "用户2"},
            {"id": 3, "name": "用户3"}
        ]

        # 创建分页响应
        paginated_response = StandardResponse.paginated(
            items=users,
            current_page=1,
            total_pages=5,
            total_count=15,
            page_size=3,
            message="获取用户列表成功"
        )

        # 验证分页响应
        assert isinstance(paginated_response, JSONResponse)
        assert paginated_response.status_code == 200

        content = json.loads(paginated_response.body)
        assert content["code"] == 200
        assert content["message"] == "获取用户列表成功"
        assert len(content["data"]["items"]) == 3
        assert content["data"]["pagination"]["current_page"] == 1
        assert content["data"]["pagination"]["total_pages"] == 5
        assert content["data"]["pagination"]["total_count"] == 15

    def test_response_data_validation_integration(self):
        """测试响应数据验证集成"""
        # 测试各种数据类型的验证
        test_cases = [
            (None, True),
            ("string", True),
            ({"key": "value"}, True),
            ([1, 2, 3], True),
            (lambda x: x, False)  # 函数不可序列化
        ]

        for data, expected in test_cases:
            result = validate_response_data(data)
            assert result == expected

    def test_response_consistency(self):
        """测试响应一致性"""
        # 验证所有响应都遵循相同的格式
        responses = [
            StandardResponse.success({"test": "data"}),
            StandardResponse.created({"id": 1}),
            StandardResponse.bad_request("参数错误"),
            StandardResponse.not_found("资源不存在")
        ]

        for response in responses:
            content = json.loads(response.body)

            # 验证必需字段存在
            assert "code" in content
            assert "message" in content
            assert "data" in content

            # 验证字段类型
            assert isinstance(content["code"], int)
            assert isinstance(content["message"], str)
            assert isinstance(content["data"], (dict, list))


@pytest.mark.parametrize("data_type,test_data", [
    ("string", "test string"),
    ("integer", 42),
    ("float", 3.14),
    ("boolean", True),
    ("dict", {"key": "value"}),
    ("list", [1, 2, 3]),
    ("none", None)
])
def test_validate_response_data_parametrized(data_type, test_data):
    """参数化测试响应数据验证"""
    result = validate_response_data(test_data)
    assert result is True, f"Data type {data_type} should be valid"


@pytest.mark.parametrize("method_name,expected_code,expected_status", [
    ("success", 200, 200),
    ("created", 201, 201),
    ("bad_request", 400, 400),
    ("unauthorized", 401, 401),
    ("payment_required", 402, 402),
    ("forbidden", 403, 403),
    ("not_found", 404, 404),
    ("server_error", 500, 500)
])
def test_standard_response_methods_parametrized(method_name, expected_code, expected_status):
    """参数化测试标准响应方法"""
    method = getattr(StandardResponse, method_name)
    result = method()

    assert isinstance(result, JSONResponse)
    assert result.status_code == expected_status

    content = json.loads(result.body)
    assert content["code"] == expected_code


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "profile": {
            "first_name": "张",
            "last_name": "三"
        }
    }


@pytest.fixture
def sample_error_data():
    """示例错误数据"""
    return {
        "field": "email",
        "error": "邮箱格式无效",
        "value": "invalid-email"
    }


def test_with_fixtures(sample_user_data, sample_error_data):
    """使用fixtures的测试"""
    # 测试成功响应
    success_result = StandardResponse.success(data=sample_user_data)
    success_content = json.loads(success_result.body)
    assert success_content["data"] == sample_user_data

    # 测试错误响应
    error_result = StandardResponse.bad_request(
        message="验证失败",
        data=sample_error_data
    )
    error_content = json.loads(error_result.body)
    assert error_content["data"] == sample_error_data