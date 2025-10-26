"""
核心异常类测试

测试系统中使用的所有核心异常类，包括：
1. BaseException基础异常类
2. BusinessException业务逻辑异常
3. ValidationException验证异常
4. ResourceNotFoundException资源未找到异常
5. AuthenticationException认证异常
6. AuthorizationException授权异常
7. DuplicateResourceException重复资源异常
8. InsufficientBalanceException余额不足异常

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from typing import Optional, Dict, Any

# 直接导入源文件中的异常类
from src.core.exceptions import (
    BaseException,
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    AuthenticationException,
    AuthorizationException,
    DuplicateResourceException,
    InsufficientBalanceException
)


@pytest.mark.unit
class TestBaseException:
    """基础异常类测试"""

    def test_base_exception_creation_minimal(self):
        """测试最小参数创建基础异常"""
        exception = BaseException("测试错误")

        assert exception.message == "测试错误"
        assert exception.error_code is None
        assert exception.user_message == "测试错误"
        assert exception.details == {}
        assert exception.cause is None

    def test_base_exception_creation_full(self):
        """测试完整参数创建基础异常"""
        error_code = "TEST_ERROR"
        user_message = "用户友好的错误消息"
        details = {"field": "test_field", "value": "test_value"}
        cause = ValueError("原始错误")

        exception = BaseException(
            message="内部错误消息",
            error_code=error_code,
            user_message=user_message,
            details=details,
            cause=cause
        )

        assert exception.message == "内部错误消息"
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.details == details
        assert exception.cause == cause

    def test_base_exception_to_dict(self):
        """测试基础异常转换为字典"""
        exception = BaseException(
            message="测试错误",
            error_code="TEST_CODE",
            user_message="用户消息",
            details={"key": "value"}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "TEST_CODE",
            "message": "用户消息",
            "details": {"key": "value"}
        }

        assert result == expected

    def test_base_exception_inheritance(self):
        """测试基础异常继承关系"""
        exception = BaseException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)

    def test_base_exception_str_representation(self):
        """测试基础异常字符串表示"""
        message = "测试异常消息"
        exception = BaseException(message)

        assert str(exception) == message

    def test_base_exception_user_message_fallback(self):
        """测试用户消息回退机制"""
        # 当user_message为None时，应该使用message
        exception1 = BaseException(message="内部消息", user_message=None)
        assert exception1.user_message == "内部消息"

        # 当提供user_message时，应该使用user_message
        exception2 = BaseException(message="内部消息", user_message="用户消息")
        assert exception2.user_message == "用户消息"

    def test_base_exception_details_fallback(self):
        """测试详情回退机制"""
        # 当details为None时，应该使用空字典
        exception1 = BaseException(message="测试", details=None)
        assert exception1.details == {}

        # 当提供details时，应该使用提供的details
        exception2 = BaseException(message="测试", details={"key": "value"})
        assert exception2.details == {"key": "value"}


@pytest.mark.unit
class TestBusinessException:
    """业务逻辑异常测试"""

    def test_business_exception_creation_default(self):
        """测试默认业务异常创建"""
        exception = BusinessException()

        assert exception.message == "业务逻辑错误"
        assert exception.error_code == "BUSINESS_ERROR"
        assert exception.user_message == "业务逻辑错误"
        assert exception.details == {}
        assert exception.cause is None

    def test_business_exception_creation_custom(self):
        """测试自定义业务异常创建"""
        message = "违反业务规则"
        error_code = "BUSINESS_RULE_VIOLATION"
        user_message = "您的操作违反了业务规则"
        details = {"rule": "no_duplicate_names"}
        cause = ValueError("规则验证失败")

        exception = BusinessException(
            message=message,
            error_code=error_code,
            user_message=user_message,
            details=details,
            cause=cause
        )

        assert exception.message == message
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.details == details
        assert exception.cause == cause

    def test_business_exception_inheritance(self):
        """测试业务异常继承关系"""
        exception = BusinessException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, BusinessException)

    def test_business_exception_to_dict(self):
        """测试业务异常转换为字典"""
        exception = BusinessException(
            error_code="CUSTOM_BUSINESS_ERROR",
            user_message="业务错误",
            details={"operation": "create_user"}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "CUSTOM_BUSINESS_ERROR",
            "message": "业务错误",
            "details": {"operation": "create_user"}
        }

        assert result == expected

    def test_business_exception_with_only_message(self):
        """测试仅提供消息的业务异常"""
        message = "自定义业务错误"
        exception = BusinessException(message=message)

        assert exception.message == message
        assert exception.error_code == "BUSINESS_ERROR"
        assert exception.user_message == message


@pytest.mark.unit
class TestValidationException:
    """验证异常测试"""

    def test_validation_exception_creation_default(self):
        """测试默认验证异常创建"""
        exception = ValidationException()

        assert exception.message == "数据验证失败"
        assert exception.error_code == "VALIDATION_ERROR"
        assert exception.user_message == "数据验证失败"
        assert exception.details == {}
        assert exception.cause is None

    def test_validation_exception_creation_field_validation(self):
        """测试字段验证异常创建"""
        exception = ValidationException(
            message="字段验证失败",
            error_code="FIELD_VALIDATION_ERROR",
            user_message="字段值不符合要求",
            details={"field": "email", "value": "invalid-email", "constraint": "email格式"},
            cause=ValueError("Email格式无效")
        )

        assert exception.message == "字段验证失败"
        assert exception.error_code == "FIELD_VALIDATION_ERROR"
        assert exception.user_message == "字段值不符合要求"
        assert exception.details["field"] == "email"
        assert exception.details["value"] == "invalid-email"
        assert exception.details["constraint"] == "email格式"

    def test_validation_exception_inheritance(self):
        """测试验证异常继承关系"""
        exception = ValidationException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, ValidationException)

    def test_validation_exception_multiple_field_errors(self):
        """测试多字段验证异常"""
        exception = ValidationException(
            message="多个字段验证失败",
            details={
                "errors": [
                    {"field": "name", "message": "名称不能为空"},
                    {"field": "age", "message": "年龄必须大于0"},
                    {"field": "email", "message": "邮箱格式无效"}
                ]
            }
        )

        assert len(exception.details["errors"]) == 3
        assert exception.details["errors"][0]["field"] == "name"


@pytest.mark.unit
class TestResourceNotFoundException:
    """资源未找到异常测试"""

    def test_resource_not_found_creation_default(self):
        """测试默认资源未找到异常创建"""
        exception = ResourceNotFoundException()

        assert exception.message == "资源未找到"
        assert exception.resource_type == "资源"
        assert exception.error_code == "RESOURCE_NOT_FOUND"
        assert exception.user_message == "资源未找到"

    def test_resource_not_found_creation_custom(self):
        """测试自定义资源未找到异常创建"""
        resource_type = "用户"
        error_code = "USER_NOT_FOUND"
        user_message = "指定的用户不存在"
        details = {"user_id": 123, "search_criteria": "username=test"}

        exception = ResourceNotFoundException(
            resource_type=resource_type,
            error_code=error_code,
            user_message=user_message,
            details=details
        )

        assert exception.message == f"{resource_type}未找到"
        assert exception.resource_type == resource_type
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.details == details

    def test_resource_not_found_inheritance(self):
        """测试资源未找到异常继承关系"""
        exception = ResourceNotFoundException("任务")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, ResourceNotFoundException)

    def test_resource_not_found_message_generation(self):
        """测试资源未找到异常消息生成"""
        resource_types = ["用户", "任务", "项目", "订单"]

        for resource_type in resource_types:
            exception = ResourceNotFoundException(resource_type=resource_type)
            expected_message = f"{resource_type}未找到"
            assert exception.message == expected_message
            assert exception.user_message == expected_message

    def test_resource_not_found_to_dict(self):
        """测试资源未找到异常转换为字典"""
        exception = ResourceNotFoundException(
            resource_type="用户",
            error_code="USER_NOT_FOUND",
            details={"user_id": 456}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "USER_NOT_FOUND",
            "message": "用户未找到",
            "details": {"user_id": 456}
        }

        assert result == expected


@pytest.mark.unit
class TestAuthenticationException:
    """认证异常测试"""

    def test_authentication_exception_creation_default(self):
        """测试默认认证异常创建"""
        exception = AuthenticationException()

        assert exception.message == "认证失败: "
        assert exception.reason == ""
        assert exception.error_code == "AUTHENTICATION_ERROR"
        assert exception.user_message == "身份验证失败，请重新登录"
        assert exception.details == {}
        assert exception.user_identifier is None

    def test_authentication_exception_creation_custom(self):
        """测试自定义认证异常创建"""
        reason = "令牌已过期"
        error_code = "TOKEN_EXPIRED"
        user_message = "登录已过期，请重新登录"
        user_identifier = "user@example.com"
        details = {"token_expiry": "2024-01-01T00:00:00Z"}

        exception = AuthenticationException(
            reason=reason,
            error_code=error_code,
            user_message=user_message,
            user_identifier=user_identifier,
            details=details
        )

        assert exception.message == f"认证失败: {reason}"
        assert exception.reason == reason
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.user_identifier == user_identifier
        assert exception.details == details

    def test_authentication_exception_inheritance(self):
        """测试认证异常继承关系"""
        exception = AuthenticationException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, AuthenticationException)

    def test_authentication_exception_message_generation(self):
        """测试认证异常消息生成"""
        reasons = ["令牌无效", "令牌过期", "用户名或密码错误", "账户被锁定"]

        for reason in reasons:
            exception = AuthenticationException(reason=reason)
            expected_message = f"认证失败: {reason}"
            assert exception.message == expected_message

    def test_authentication_exception_user_identifier_in_details(self):
        """测试用户标识符包含在详情中"""
        user_identifier = "user_123"
        exception = AuthenticationException(
            reason="测试原因",
            user_identifier=user_identifier
        )

        assert exception.details["user_identifier"] == user_identifier

    def test_authentication_exception_to_dict(self):
        """测试认证异常转换为字典"""
        exception = AuthenticationException(
            reason="令牌无效",
            user_identifier="user_456",
            details={"ip_address": "192.168.1.100"}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "AUTHENTICATION_ERROR",
            "message": "身份验证失败，请重新登录",
            "details": {
                "user_identifier": "user_456",
                "ip_address": "192.168.1.100"
            }
        }

        assert result == expected


@pytest.mark.unit
class TestAuthorizationException:
    """授权异常测试"""

    def test_authorization_exception_creation_default(self):
        """测试默认授权异常创建"""
        exception = AuthorizationException()

        assert exception.message == "权限不足"
        assert exception.error_code == "AUTHORIZATION_ERROR"
        assert exception.user_message == "您没有权限执行此操作"
        assert exception.details == {}
        assert exception.required_permission is None

    def test_authorization_exception_creation_custom(self):
        """测试自定义授权异常创建"""
        message = "禁止访问管理员功能"
        error_code = "ADMIN_ACCESS_DENIED"
        user_message = "您没有管理员权限，请联系管理员"
        required_permission = "admin.access"
        details = "需要管理员权限才能访问此功能"

        exception = AuthorizationException(
            message=message,
            error_code=error_code,
            user_message=user_message,
            required_permission=required_permission,
            details=details
        )

        assert exception.message == message
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.required_permission == required_permission

    def test_authorization_exception_inheritance(self):
        """测试授权异常继承关系"""
        exception = AuthorizationException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, AuthorizationException)

    def test_authorization_exception_required_permission_in_details(self):
        """测试所需权限包含在详情中"""
        required_permission = "users.create"
        exception = AuthorizationException(
            required_permission=required_permission
        )

        assert exception.details["required_permission"] == required_permission

    def test_authorization_exception_to_dict(self):
        """测试授权异常转换为字典"""
        exception = AuthorizationException(
            required_permission="tasks.delete",
            details={"user_role": "user", "resource": "task_123"}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "AUTHORIZATION_ERROR",
            "message": "您没有权限执行此操作",
            "details": {
                "required_permission": "tasks.delete",
                "user_role": "user",
                "resource": "task_123"
            }
        }

        assert result == expected


@pytest.mark.unit
class TestDuplicateResourceException:
    """重复资源异常测试"""

    def test_duplicate_resource_creation_default(self):
        """测试默认重复资源异常创建"""
        exception = DuplicateResourceException()

        assert exception.message == "资源已存在"
        assert exception.resource_type == "资源"
        assert exception.error_code == "DUPLICATE_RESOURCE"
        assert exception.conflict_field is None
        assert exception.conflict_value is None

    def test_duplicate_resource_creation_with_conflict(self):
        """测试带冲突信息的重复资源异常创建"""
        resource_type = "用户"
        conflict_field = "email"
        conflict_value = "test@example.com"

        exception = DuplicateResourceException(
            resource_type=resource_type,
            conflict_field=conflict_field,
            conflict_value=conflict_value
        )

        expected_message = f"{resource_type}已存在，{conflict_field}: {conflict_value}"
        assert exception.message == expected_message
        assert exception.resource_type == resource_type
        assert exception.conflict_field == conflict_field
        assert exception.conflict_value == conflict_value

    def test_duplicate_resource_creation_full(self):
        """测试完整参数的重复资源异常创建"""
        resource_type = "用户"
        conflict_field = "username"
        conflict_value = "testuser"
        error_code = "USERNAME_DUPLICATE"
        user_message = "用户名已存在，请选择其他用户名"
        details = {"existing_user_id": 123}

        exception = DuplicateResourceException(
            resource_type=resource_type,
            conflict_field=conflict_field,
            conflict_value=conflict_value,
            error_code=error_code,
            user_message=user_message,
            details=details
        )

        assert exception.resource_type == resource_type
        assert exception.conflict_field == conflict_field
        assert exception.conflict_value == conflict_value
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.details == details

    def test_duplicate_resource_inheritance(self):
        """测试重复资源异常继承关系"""
        exception = DuplicateResourceException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, DuplicateResourceException)

    def test_duplicate_resource_message_generation(self):
        """测试重复资源异常消息生成"""
        test_cases = [
            ("用户", "email", "test@example.com"),
            ("任务", "title", "测试任务"),
            ("项目", "name", "测试项目"),
            ("订单", "order_number", "ORD123")
        ]

        for resource_type, conflict_field, conflict_value in test_cases:
            exception = DuplicateResourceException(
                resource_type=resource_type,
                conflict_field=conflict_field,
                conflict_value=conflict_value
            )
            expected_message = f"{resource_type}已存在，{conflict_field}: {conflict_value}"
            assert exception.message == expected_message

    def test_duplicate_resource_to_dict(self):
        """测试重复资源异常转换为字典"""
        exception = DuplicateResourceException(
            resource_type="用户",
            conflict_field="email",
            conflict_value="test@example.com",
            details={"existing_id": 456}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "DUPLICATE_RESOURCE",
            "message": "用户已存在，email: test@example.com",
            "details": {
                "conflict_field": "email",
                "conflict_value": "test@example.com",
                "existing_id": 456
            }
        }

        assert result == expected


@pytest.mark.unit
class TestInsufficientBalanceException:
    """余额不足异常测试"""

    def test_insufficient_balance_creation_default(self):
        """测试默认余额不足异常创建"""
        exception = InsufficientBalanceException()

        assert exception.message == "余额不足"
        assert exception.error_code == "INSUFFICIENT_BALANCE"
        assert exception.user_message == "账户余额不足，请充值后重试"
        assert exception.required_amount is None
        assert exception.current_balance is None

    def test_insufficient_balance_creation_with_amounts(self):
        """测试带金额的余额不足异常创建"""
        required_amount = 100.0
        current_balance = 50.0

        exception = InsufficientBalanceException(
            required_amount=required_amount,
            current_balance=current_balance
        )

        expected_message = f"余额不足，需要: {required_amount}"
        assert exception.message == expected_message
        assert exception.required_amount == required_amount
        assert exception.current_balance == current_balance

    def test_insufficient_balance_creation_full(self):
        """测试完整参数的余额不足异常创建"""
        required_amount = 200.50
        current_balance = 75.25
        error_code = "PAYMENT_INSUFFICIENT"
        user_message = "余额不足，当前余额75.25元，需要200.50元"
        details = {"operation": "purchase_item", "item_price": 200.50}

        exception = InsufficientBalanceException(
            required_amount=required_amount,
            current_balance=current_balance,
            error_code=error_code,
            user_message=user_message,
            details=details
        )

        assert exception.required_amount == required_amount
        assert exception.current_balance == current_balance
        assert exception.error_code == error_code
        assert exception.user_message == user_message
        assert exception.details == details

    def test_insufficient_balance_inheritance(self):
        """测试余额不足异常继承关系"""
        exception = InsufficientBalanceException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, BaseException)
        assert isinstance(exception, InsufficientBalanceException)

    def test_insufficient_balance_message_generation(self):
        """测试余额不足异常消息生成"""
        test_cases = [
            (None, None, "余额不足"),
            (50.0, None, "余额不足，需要: 50.0"),
            (None, 25.0, "余额不足"),
            (100.0, 75.0, "余额不足，需要: 100.0")
        ]

        for required_amount, current_balance, expected_start in test_cases:
            exception = InsufficientBalanceException(
                required_amount=required_amount,
                current_balance=current_balance
            )
            assert exception.message.startswith(expected_start)

    def test_insufficient_balance_to_dict(self):
        """测试余额不足异常转换为字典"""
        exception = InsufficientBalanceException(
            required_amount=150.0,
            current_balance=25.0,
            details={"transaction_type": "payment"}
        )

        result = exception.to_dict()

        expected = {
            "error_code": "INSUFFICIENT_BALANCE",
            "message": "账户余额不足，请充值后重试",
            "details": {
                "required_amount": 150.0,
                "current_balance": 25.0,
                "transaction_type": "payment"
            }
        }

        assert result == expected


@pytest.mark.integration
class TestExceptionHierarchy:
    """异常层次结构测试"""

    def test_all_exceptions_inherit_from_base(self):
        """测试所有异常都继承自BaseException"""
        exception_classes = [
            BusinessException,
            ValidationException,
            ResourceNotFoundException,
            AuthenticationException,
            AuthorizationException,
            DuplicateResourceException,
            InsufficientException
        ]

        for exception_class in exception_classes:
            exception = exception_class("测试")
            assert isinstance(exception, BaseException)
            assert isinstance(exception, Exception)

    def test_exception_error_codes_uniqueness(self):
        """测试异常错误码唯一性"""
        exceptions = [
            BusinessException(error_code="BUSINESS_ERROR"),
            ValidationException(error_code="VALIDATION_ERROR"),
            ResourceNotFoundException(error_code="RESOURCE_NOT_FOUND"),
            AuthenticationException(error_code="AUTHENTICATION_ERROR"),
            AuthorizationException(error_code="AUTHORIZATION_ERROR"),
            DuplicateResourceException(error_code="DUPLICATE_RESOURCE"),
            InsufficientBalanceException(error_code="INSUFFICIENT_BALANCE")
        ]

        # 验证默认错误码不重复
        error_codes = [exc.error_code for exc in exceptions]
        assert len(error_codes) == len(set(error_codes))

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as original_error:
                # 使用原始异常作为cause
                raise BusinessException(
                    message="业务逻辑处理失败",
                    cause=original_error
                )
        except BusinessException as business_error:
            assert business_error.cause is not None
            assert isinstance(business_error.cause, ValueError)
            assert str(business_error.cause) == "原始错误"

    def test_exception_serialization_consistency(self):
        """测试异常序列化一致性"""
        exceptions = [
            BusinessException("业务错误", details={"field": "test"}),
            ValidationException("验证错误", error_code="VALID_ERROR"),
            ResourceNotFoundException("资源不存在"),
            AuthenticationException(reason="令牌无效"),
            AuthorizationException(required_permission="admin"),
            DuplicateResourceException("重复资源", conflict_field="id"),
            InsufficientBalanceException(required_amount=100.0)
        ]

        for exception in exceptions:
            # 测试to_dict方法存在
            assert hasattr(exception, 'to_dict')
            result = exception.to_dict()

            # 验证返回格式
            assert isinstance(result, dict)
            assert "error_code" in result
            assert "message" in result
            assert "details" in result

    def test_exception_user_friendly_messages(self):
        """测试异常用户友好消息"""
        exceptions = [
            (BusinessException, "业务逻辑错误"),
            (ValidationException, "数据验证失败"),
            (ResourceNotFoundException("资源"), "资源未找到"),
            (AuthenticationException(), "身份验证失败，请重新登录"),
            (AuthorizationException(), "您没有权限执行此操作"),
            (DuplicateResourceException("资源"), "资源已存在"),
            (InsufficientBalanceException(), "账户余额不足，请充值后重试")
        ]

        for exception_class, expected_default_message in exceptions:
            exception = exception_class()
            assert exception.user_message == expected_default_message


@pytest.mark.parametrize("exception_class,expected_base", [
    (BaseException, "BaseException"),
    (BusinessException, "BaseException"),
    (ValidationException, "BaseException"),
    (ResourceNotFoundException, "BaseException"),
    (AuthenticationException, "BaseException"),
    (AuthorizationException, "BaseException"),
    (DuplicateResourceException, "BaseException"),
    (InsufficientBalanceException, "BaseException")
])
def test_exception_inheritance_parametrized(exception_class, expected_base):
    """参数化测试异常继承"""
    exception = exception_class("测试")
    assert isinstance(exception, expected_base)


@pytest.mark.parametrize("message,expected_user_message", [
    ("内部错误", "内部错误"),
    ("内部错误", "用户友好消息"),
    ("Validation failed", "数据验证失败"),
    ("Authentication failed", "身份验证失败，请重新登录")
])
def test_user_message_fallback_parametrized(message, expected_user_message):
    """参数化测试用户消息回退机制"""
    exception = BaseException(message=message, user_message=expected_user_message)
    assert exception.user_message == expected_user_message


@pytest.mark.parametrize("details_type,expected_details", [
    (None, {}),
    ({"key": "value"}, {"key": "value"}),
    ({"errors": []}, {"errors": []})
])
def test_details_fallback_parametrized(details_type, expected_details):
    """参数化测试详情回退机制"""
    exception = BaseException(message="测试", details=details_type)
    assert exception.details == expected_details


@pytest.fixture
def sample_exception():
    """示例异常对象"""
    return BusinessException(
        message="示例业务异常",
        error_code="SAMPLE_ERROR",
        user_message="这是一个示例异常",
        details={"operation": "test"}
    )


@pytest.fixture
def sample_validation_error():
    """示例验证错误"""
    return ValidationException(
        message="字段验证失败",
        details={
            "field": "email",
            "value": "invalid-email",
            "rule": "email_format"
        }
    )


def test_with_fixtures(sample_exception, sample_validation_error):
    """使用fixtures的测试"""
    # 测试示例异常
    assert sample_exception.message == "示例业务异常"
    assert sample_exception.error_code == "SAMPLE_ERROR"
    assert sample_exception.details["operation"] == "test"

    # 测试验证错误
    assert sample_validation_error.message == "字段验证失败"
    assert sample_validation_error.details["field"] == "email"
    assert sample_validation_error.details["rule"] == "email_format"