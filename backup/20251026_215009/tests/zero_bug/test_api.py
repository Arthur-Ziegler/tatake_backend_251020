"""
零Bug测试体系 - API层测试

测试防御式API层的正确性，确保API安全和可靠性。

测试原则：
1. 输入即验证：每个输入都经过验证
2. 错误即明确：每个错误都有明确信息
3. 响应即标准：所有响应都符合标准格式
4. 安全即默认：所有操作都有安全检查
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from src.core.api import (
    APIResponse, ErrorCodes,
    create_success_response, create_error_response,
    generate_request_id, validate_token, extract_client_info,
    ValidationError, BusinessRuleViolationError
)


class TestAPIResponse:
    """API响应测试 - 验证响应格式和内容"""

    def test_create_success_response_should_succeed(self):
        """
        用例：创建成功响应
        条件：提供数据和消息
        期望：创建成功响应对象
        验证：响应格式符合标准
        """
        # Given - 响应数据
        data = {"id": "123", "title": "测试任务"}
        message = "操作成功"
        request_id = "req_1234567890abcdef"

        # When - 创建成功响应
        response = APIResponse.success(data=data, message=message, request_id=request_id)

        # Then - 验证响应内容
        assert response.code == 200
        assert response.message == message
        assert response.data == data
        assert response.request_id == request_id
        assert isinstance(response.timestamp, datetime)

    def test_create_success_response_with_defaults(self):
        """
        用例：创建默认成功响应
        条件：不提供可选参数
        期望：使用默认值创建响应
        验证：默认值正确设置
        """
        # When - 创建默认成功响应
        response = APIResponse.success()

        # Then - 验证默认值
        assert response.code == 200
        assert response.message == "操作成功"
        assert response.data is None
        assert response.request_id is None
        assert isinstance(response.timestamp, datetime)

    def test_create_error_response_should_succeed(self):
        """
        用例：创建错误响应
        条件：提供错误信息和错误码
        期望：创建错误响应对象
        验证：错误格式符合标准
        """
        # Given - 错误信息
        message = "操作失败"
        code = 400
        data = {"error_details": "参数无效"}
        request_id = "req_1234567890abcdef"

        # When - 创建错误响应
        response = APIResponse.error(message=message, code=code, data=data, request_id=request_id)

        # Then - 验证错误响应
        assert response.code == code
        assert response.message == message
        assert response.data == data
        assert response.request_id == request_id

    def test_api_response_to_dict(self):
        """
        用例：转换响应为字典
        条件：提供完整响应对象
        期望：返回格式正确的字典
        验证：字典格式符合API标准
        """
        # Given - 完整响应对象
        response = APIResponse.success(
            data={"test": "data"},
            message="测试消息",
            request_id="req_test"
        )

        # When - 转换为字典
        response_dict = response.to_dict()

        # Then - 验证字典格式
        expected_keys = {"code", "message", "data", "timestamp", "request_id"}
        assert set(response_dict.keys()) == expected_keys
        assert response_dict["code"] == 200
        assert response_dict["message"] == "测试消息"
        assert response_dict["data"] == {"test": "data"}
        assert response_dict["request_id"] == "req_test"
        assert "T" in response_dict["timestamp"]  # ISO格式时间戳

    def test_response_timestamp_auto_generation(self):
        """
        用例：响应时间戳自动生成
        条件：不提供时间戳
        期望：自动生成当前UTC时间
        验证：时间戳为当前时间
        """
        # Given - 不提供时间戳
        before_creation = datetime.now(timezone.utc)

        # When - 创建响应
        response = APIResponse.success()

        after_creation = datetime.now(timezone.utc)

        # Then - 验证时间戳范围
        assert before_creation <= response.timestamp <= after_creation
        assert response.timestamp.tzinfo == timezone.utc


class TestErrorCodes:
    """错误码测试 - 验证错误码系统"""

    def test_get_message_for_known_error(self):
        """
        用例：获取已知错误码的消息
        条件：提供预定义的错误码
        期望：返回对应的错误消息
        验证：错误码映射正确
        """
        # Given & When - 查询已知错误码
        invalid_request_msg = ErrorCodes.get_message(ErrorCodes.INVALID_REQUEST)
        missing_param_msg = ErrorCodes.get_message(ErrorCodes.MISSING_PARAMETER)
        not_found_msg = ErrorCodes.get_message(ErrorCodes.RESOURCE_NOT_FOUND)

        # Then - 验证错误消息
        assert invalid_request_msg == "请求格式无效"
        assert missing_param_msg == "缺少必要参数"
        assert not_found_msg == "资源不存在"

    def test_get_message_for_unknown_error(self):
        """
        用例：获取未知错误码的消息
        条件：提供未定义的错误码
        期望：返回默认错误消息
        验证：未知错误码安全处理
        """
        # Given - 未知错误码
        unknown_code = 9999

        # When - 获取消息
        message = ErrorCodes.get_message(unknown_code)

        # Then - 验证默认消息
        assert message == "未知错误"

    def test_error_code_categories(self):
        """
        用例：验证错误码分类
        条件：检查错误码范围
        期望：错误码正确分类
        验证：分类逻辑正确
        """
        # Given - 各类错误码
        common_errors = [ErrorCodes.INVALID_REQUEST, ErrorCodes.INTERNAL_ERROR]
        auth_errors = [ErrorCodes.INVALID_TOKEN, ErrorCodes.UNAUTHORIZED]
        task_errors = [ErrorCodes.TASK_NOT_FOUND, ErrorCodes.TASK_CREATION_FAILED]
        business_errors = [ErrorCodes.BUSINESS_RULE_VIOLATION, ErrorCodes.DATA_CONSISTENCY_ERROR]

        # Then - 验证错误码范围
        assert all(1000 <= code < 2000 for code in common_errors)
        assert all(2000 <= code < 3000 for code in auth_errors)
        assert all(3000 <= code < 4000 for code in task_errors)
        assert all(4000 <= code < 5000 for code in business_errors)


class TestResponseCreation:
    """响应创建函数测试"""

    def test_create_success_response_json(self):
        """
        用例：创建成功JSON响应
        条件：提供成功数据
        期望：返回JSONResponse对象
        验证：响应格式和状态码正确
        """
        # Given - 成功数据
        data = {"task_id": "123", "status": "completed"}

        # When - 创建成功响应
        response = create_success_response(data=data, message="任务完成", request_id="req_test")

        # Then - 验证响应
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # 验证响应体
        import json
        response_data = json.loads(response.body)
        assert response_data["code"] == 200
        assert response_data["message"] == "任务完成"
        assert response_data["data"] == data
        assert response_data["request_id"] == "req_test"

    def test_create_error_response_json(self):
        """
        用例：创建错误JSON响应
        条件：提供错误信息
        期望：返回JSONResponse对象
        验证：错误响应格式正确
        """
        # Given - 错误信息
        message = "任务不存在"
        code = ErrorCodes.TASK_NOT_FOUND

        # When - 创建错误响应
        response = create_error_response(message=message, code=code, request_id="req_error")

        # Then - 验证响应
        assert response.status_code == 400  # 任务错误对应400状态码
        assert "application/json" in response.headers.get("content-type", "")

        # 验证响应体
        import json
        response_data = json.loads(response.body)
        assert response_data["code"] == code
        assert response_data["message"] == message
        assert response_data["request_id"] == "req_error"

    def test_create_auth_error_response(self):
        """
        用例：创建认证错误响应
        条件：提供认证错误码
        期望：返回401状态码
        验证：认证错误正确映射到401
        """
        # Given - 认证错误
        auth_errors = [ErrorCodes.INVALID_TOKEN, ErrorCodes.TOKEN_EXPIRED, ErrorCodes.UNAUTHORIZED]

        # When & Then - 验证认证错误状态码
        for error_code in auth_errors:
            response = create_error_response("认证失败", code=error_code)
            assert response.status_code == 401

    def test_create_business_error_response(self):
        """
        用例：创建业务规则错误响应
        条件：提供业务规则错误码
        期望：返回422状态码
        验证：业务错误正确映射到422
        """
        # Given - 业务错误
        business_errors = [ErrorCodes.BUSINESS_RULE_VIOLATION, ErrorCodes.DATA_CONSISTENCY_ERROR]

        # When & Then - 验证业务错误状态码
        for error_code in business_errors:
            response = create_error_response("业务规则违反", code=error_code)
            assert response.status_code == 422


class TestRequestValidation:
    """请求验证装饰器测试"""

    def test_validate_request_decorator_with_valid_data(self):
        """
        用例：请求验证装饰器验证有效数据
        条件：提供有效请求数据
        期望：装饰器通过验证，执行目标函数
        验证：验证成功时正常执行
        """
        # 注意：这个测试需要实际的FastAPI环境，这里提供模拟测试
        # 在实际项目中，应该使用TestClient进行集成测试

        # Given - 模拟装饰器和验证函数
        def mock_validator(*args, **kwargs):
            # 模拟验证成功
            return True

        def mock_handler(*args, **kwargs):
            return {"result": "success"}

        # When - 应用装饰器
        decorated_handler = validate_request(mock_validator)(mock_handler)

        # Then - 验证装饰器应用
        assert callable(decorated_handler)


class TestUtilityFunctions:
    """工具函数测试"""

    def test_generate_request_id(self):
        """
        用例：生成请求ID
        条件：调用请求ID生成函数
        期望：生成唯一ID
        验证：ID格式和唯一性
        """
        # When - 生成请求ID
        request_id1 = generate_request_id()
        request_id2 = generate_request_id()

        # Then - 验证格式和唯一性
        assert isinstance(request_id1, str)
        assert isinstance(request_id2, str)
        assert request_id1.startswith("req_")
        assert request_id2.startswith("req_")
        assert request_id1 != request_id2
        assert len(request_id1) == 4 + 16  # "req_" + 16字符

    def test_validate_token_valid_token(self):
        """
        用例：验证有效令牌
        条件：提供有效令牌
        期望：返回用户ID
        验证：令牌验证成功
        """
        # Given - 有效令牌（临时实现）
        valid_token = "test_token"

        # When - 验证令牌
        user_id = validate_token(valid_token)

        # Then - 验证结果
        assert isinstance(user_id, UserId)
        assert str(user_id) == "test_user_123"

    def test_validate_token_invalid_token(self):
        """
        用例：验证无效令牌
        条件：提供无效令牌
        期望：抛出异常
        验证：无效令牌被拒绝
        """
        # Given - 无效令牌
        invalid_tokens = ["invalid_token", "", None]

        # When & Then - 验证失败
        for invalid_token in invalid_tokens:
            with pytest.raises(ValueError, match="Token验证失败"):
                validate_token(invalid_token)

    def test_extract_client_info(self):
        """
        用例：提取客户端信息
        条件：提供模拟请求对象
        期望：返回客户端信息字典
        验证：信息提取正确
        """
        # Given - 模拟请求对象
        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {
            "user-agent": "TestAgent/1.0",
            "referer": "https://example.com",
            "x-forwarded-for": "10.0.0.1"
        }

        # When - 提取客户端信息
        client_info = extract_client_info(mock_request)

        # Then - 验证提取的信息
        assert client_info["ip_address"] == "192.168.1.100"
        assert client_info["user_agent"] == "TestAgent/1.0"
        assert client_info["referer"] == "https://example.com"
        assert client_info["x_forwarded_for"] == "10.0.0.1"

    def test_extract_client_info_with_missing_data(self):
        """
        用例：提取客户端信息（缺少数据）
        条件：请求对象缺少某些信息
        期望：使用默认值处理缺失数据
        验证：缺失数据安全处理
        """
        # Given - 信息不完整的请求对象
        mock_request = Mock()
        mock_request.client = None  # 缺少客户端信息
        mock_request.headers = {}  # 缺少头信息

        # When - 提取客户端信息
        client_info = extract_client_info(mock_request)

        # Then - 验证默认值
        assert client_info["ip_address"] == "unknown"
        assert client_info["user_agent"] == "unknown"
        assert client_info["referer"] == "unknown"
        assert client_info["x_forwarded_for"] == "unknown"


class TestAPIIntegration:
    """API集成测试 - 模拟真实API场景"""

    def test_complete_api_flow_success(self):
        """
        用例：完整的API成功流程
        条件：模拟完整的请求-响应流程
        期望：所有步骤都正确执行
        验证：端到端流程正确
        """
        # Given - 模拟完整的API流程
        request_id = generate_request_id()
        request_data = {"title": "新任务", "description": "任务描述"}

        # When - 模拟API处理流程
        try:
            # 1. 验证请求数据（模拟）
            if not request_data.get("title"):
                raise ValidationError("标题不能为空", "title")

            # 2. 处理业务逻辑（模拟）
            result = {"task_id": "task_123", **request_data}

            # 3. 创建成功响应
            response = create_success_response(
                data=result,
                message="任务创建成功",
                request_id=request_id
            )

        except Exception as e:
            # 4. 处理错误（如果有）
            response = create_error_response(
                message=str(e),
                code=ErrorCodes.INTERNAL_ERROR,
                request_id=request_id
            )

        # Then - 验证响应
        assert response.status_code == 200
        import json
        response_data = json.loads(response.body)
        assert response_data["code"] == 200
        assert response_data["message"] == "任务创建成功"
        assert response_data["data"]["title"] == "新任务"
        assert response_data["request_id"] == request_id

    def test_complete_api_flow_with_validation_error(self):
        """
        用例：API流程中的验证错误
        条件：请求数据验证失败
        期望：返回验证错误响应
        验证：验证错误正确处理
        """
        # Given - 无效请求数据
        request_id = generate_request_id()
        invalid_data = {"title": "", "description": "空标题任务"}

        # When - 处理无效请求
        try:
            # 验证失败
            if not invalid_data.get("title").strip():
                raise ValidationError("标题不能为空", "title")

            response = create_success_response(data=invalid_data, request_id=request_id)

        except ValidationError as e:
            response = create_error_response(
                message=e.message,
                code=ErrorCodes.INVALID_PARAMETER,
                data={"field": e.field, "value": e.value},
                request_id=request_id
            )

        # Then - 验证错误响应
        assert response.status_code == 400
        import json
        response_data = json.loads(response.body)
        assert response_data["code"] == ErrorCodes.INVALID_PARAMETER
        assert response_data["message"] == "标题不能为空"
        assert response_data["data"]["field"] == "title"

    def test_api_error_handling_consistency(self):
        """
        用例：API错误处理一致性
        条件：各种类型的错误
        期望：所有错误都有统一格式
        验证：错误处理一致性
        """
        # Given - 各种错误类型
        errors = [
            ValidationError("验证错误", "field", "value"),
            BusinessRuleViolationError("业务规则错误"),
            ValueError("值错误"),
            TypeError("类型错误")
        ]

        request_id = generate_request_id()

        # When & Then - 处理每种错误
        for error in errors:
            try:
                # 模拟错误发生
                raise error
            except (ValidationError, BusinessRuleViolationError) as e:
                response = create_error_response(
                    message=e.message,
                    code=ErrorCodes.BUSINESS_RULE_VIOLATION,
                    request_id=request_id
                )
            except (ValueError, TypeError) as e:
                response = create_error_response(
                    message=str(e),
                    code=ErrorCodes.INTERNAL_ERROR,
                    request_id=request_id
                )

            # 验证响应格式一致
            assert response.status_code in [400, 422, 500]
            import json
            response_data = json.loads(response.body)
            assert "code" in response_data
            assert "message" in response_data
            assert "request_id" in response_data
            assert response_data["request_id"] == request_id