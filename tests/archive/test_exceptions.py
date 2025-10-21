"""
异常类测试

测试服务层异常类的功能和行为，确保异常处理机制正常工作。
遵循TDD原则，验证异常的创建、属性访问、字典转换等功能。
"""

import pytest
from datetime import datetime

from src.services.exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    InsufficientBalanceException,
    DuplicateResourceException,
    AuthenticationException,
    AuthorizationException,
    create_exception,
    wrap_repository_error,
    EXCEPTION_MAP
)
from src.repositories.base import (
    RepositoryNotFoundError,
    RepositoryValidationError,
    RepositoryIntegrityError
)


class TestBusinessException:
    """BusinessException基础异常类测试"""

    def test_business_exception_creation_minimal(self):
        """测试最小参数创建BusinessException"""
        error_code = "SERVICE_TEST_ERROR"
        message = "Test error message"

        exception = BusinessException(error_code, message)

        assert exception.error_code == error_code
        assert exception.message == message
        assert exception.user_message == message  # 默认使用message
        assert exception.details == {}
        assert exception.suggestions == []
        assert exception.cause is None
        assert exception.debug_info is not None
        assert "timestamp" in exception.debug_info
        assert "exception_type" in exception.debug_info

    def test_business_exception_creation_full(self):
        """测试完整参数创建BusinessException"""
        error_code = "SERVICE_TEST_ERROR"
        message = "Technical error message"
        user_message = "用户友好错误消息"
        details = {"field": "email", "value": "test@example.com"}
        suggestions = ["建议1", "建议2"]
        cause = ValueError("Original error")

        exception = BusinessException(
            error_code=error_code,
            message=message,
            details=details,
            user_message=user_message,
            suggestions=suggestions,
            cause=cause
        )

        assert exception.error_code == error_code
        assert exception.message == message
        assert exception.user_message == user_message
        assert exception.details == details
        assert exception.suggestions == suggestions
        assert exception.cause == cause

    def test_business_exception_to_dict(self):
        """测试异常转换为字典"""
        exception = BusinessException(
            error_code="SERVICE_TEST_ERROR",
            message="Test error",
            details={"field": "email"},
            suggestions=["建议1"]
        )

        result = exception.to_dict()

        assert isinstance(result, dict)
        assert result["error_code"] == "SERVICE_TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["user_message"] == "Test error"
        assert result["details"] == {"field": "email"}
        assert result["suggestions"] == ["建议1"]
        assert "debug_info" in result
        assert "timestamp" in result["debug_info"]

    def test_business_exception_add_detail(self):
        """测试添加详细信息"""
        exception = BusinessException("SERVICE_TEST_ERROR", "Test error")

        exception.add_detail("field", "email")
        exception.add_detail("value", "test@example.com")

        assert exception.details == {"field": "email", "value": "test@example.com"}

    def test_business_exception_add_suggestion(self):
        """测试添加修复建议"""
        exception = BusinessException("SERVICE_TEST_ERROR", "Test error")

        exception.add_suggestion("建议1")
        exception.add_suggestion("建议2")

        assert exception.suggestions == ["建议1", "建议2"]

    def test_business_exception_str_representation(self):
        """测试异常字符串表示"""
        exception = BusinessException(
            "SERVICE_TEST_ERROR",
            "Technical message",
            user_message="用户消息"
        )

        assert str(exception) == "[SERVICE_TEST_ERROR] 用户消息"

    def test_business_exception_repr(self):
        """测试异常详细表示"""
        exception = BusinessException("SERVICE_TEST_ERROR", "Test message")

        result = repr(exception)

        assert "BusinessException" in result
        assert "SERVICE_TEST_ERROR" in result
        assert "Test message" in result


class TestValidationException:
    """ValidationException验证异常类测试"""

    def test_validation_exception_basic(self):
        """测试基础ValidationException"""
        exception = ValidationException(
            message="Field validation failed",
            field="email",
            value="invalid-email"
        )

        assert exception.error_code == "SERVICE_VALIDATION_ERROR"
        assert "Field validation failed" in exception.message
        assert exception.details["field"] == "email"
        assert exception.details["invalid_value"] == "invalid-email"

    def test_validation_exception_without_field(self):
        """测试不带字段的ValidationException"""
        exception = ValidationException(message="General validation error")

        assert exception.error_code == "SERVICE_VALIDATION_ERROR"
        assert "field" not in exception.details

    def test_validation_exception_inheritance(self):
        """测试ValidationException继承关系"""
        exception = ValidationException(message="Test error")

        assert isinstance(exception, BusinessException)


class TestResourceNotFoundException:
    """ResourceNotFoundException资源未找到异常类测试"""

    def test_resource_not_found_with_id(self):
        """测试根据ID创建ResourceNotFoundException"""
        exception = ResourceNotFoundException(
            resource_type="User",
            resource_id="user123"
        )

        assert exception.error_code == "SERVICE_RESOURCE_NOT_FOUND"
        assert "User" in exception.message
        assert "user123" in exception.message
        assert exception.details["resource_type"] == "User"
        assert exception.details["resource_id"] == "user123"

    def test_resource_not_found_with_criteria(self):
        """测试根据搜索条件创建ResourceNotFoundException"""
        search_criteria = {"email": "test@example.com", "status": "active"}
        exception = ResourceNotFoundException(
            resource_type="User",
            search_criteria=search_criteria
        )

        assert exception.error_code == "SERVICE_RESOURCE_NOT_FOUND"
        assert "User" in exception.message
        assert exception.details["search_criteria"] == search_criteria

    def test_resource_not_found_minimal(self):
        """测试最小参数创建ResourceNotFoundException"""
        exception = ResourceNotFoundException(resource_type="Task")

        assert exception.error_code == "SERVICE_RESOURCE_NOT_FOUND"
        assert "Task" in exception.message


class TestInsufficientBalanceException:
    """InsufficientBalanceException余额不足异常类测试"""

    def test_insufficient_balance_exception(self):
        """测试InsufficientBalanceException"""
        exception = InsufficientBalanceException(
            current_balance=50,
            required_amount=100,
            balance_type="积分"
        )

        assert exception.error_code == "SERVICE_INSUFFICIENT_BALANCE"
        assert "50" in exception.message
        assert "100" in exception.message
        assert exception.details["current_balance"] == 50
        assert exception.details["required_amount"] == 100
        assert exception.details["balance_type"] == "积分"
        assert exception.details["shortfall"] == 50
        assert len(exception.suggestions) > 0  # 应该有默认建议


class TestDuplicateResourceException:
    """DuplicateResourceException重复资源异常类测试"""

    def test_duplicate_resource_exception(self):
        """测试DuplicateResourceException"""
        exception = DuplicateResourceException(
            resource_type="User",
            conflict_field="email",
            conflict_value="test@example.com",
            existing_resource_id="user123"
        )

        assert exception.error_code == "SERVICE_DUPLICATE_RESOURCE"
        assert "User" in exception.message
        assert "email" in exception.message
        assert "test@example.com" in exception.message
        assert exception.details["resource_type"] == "User"
        assert exception.details["conflict_field"] == "email"
        assert exception.details["conflict_value"] == "test@example.com"
        assert exception.details["existing_resource_id"] == "user123"
        assert len(exception.suggestions) > 0  # 应该有默认建议


class TestAuthenticationException:
    """AuthenticationException认证异常类测试"""

    def test_authentication_exception(self):
        """测试AuthenticationException"""
        exception = AuthenticationException(
            reason="invalid credentials",
            user_identifier="test@example.com"
        )

        assert exception.error_code == "SERVICE_AUTHENTICATION_ERROR"
        assert "invalid credentials" in exception.message
        assert exception.details["reason"] == "invalid credentials"
        assert exception.details["user_identifier"] == "test@example.com"
        assert "用户名或密码错误" in exception.user_message

    def test_authentication_exception_token_expired(self):
        """测试令牌过期的AuthenticationException"""
        exception = AuthenticationException(reason="token expired")

        assert "登录已过期" in exception.user_message

    def test_authentication_exception_permission_denied(self):
        """测试权限不足的AuthenticationException"""
        exception = AuthenticationException(reason="permission denied")

        assert "权限不足" in exception.user_message


class TestAuthorizationException:
    """AuthorizationException授权异常类测试"""

    def test_authorization_exception(self):
        """测试AuthorizationException"""
        exception = AuthorizationException(
            required_permission="admin:delete",
            user_id="user123",
            resource_id="resource456"
        )

        assert exception.error_code == "SERVICE_AUTHORIZATION_ERROR"
        assert "admin:delete" in exception.message
        assert exception.details["required_permission"] == "admin:delete"
        assert exception.details["user_id"] == "user123"
        assert exception.details["resource_id"] == "resource456"
        assert exception.user_message == "权限不足，无法执行此操作"


class TestCreateException:
    """create_exception工具函数测试"""

    def test_create_business_exception(self):
        """测试创建BusinessException"""
        exception = create_exception(
            "SERVICE_UNKNOWN_ERROR",
            "Unknown error occurred",
            user_message="未知错误"
        )

        assert isinstance(exception, BusinessException)
        assert exception.error_code == "SERVICE_UNKNOWN_ERROR"
        assert exception.message == "Unknown error occurred"
        assert exception.user_message == "未知错误"

    def test_create_validation_exception(self):
        """测试创建ValidationException"""
        exception = create_exception(
            "SERVICE_VALIDATION_ERROR",
            "Validation failed",
            field="email"
        )

        assert isinstance(exception, ValidationException)
        assert exception.error_code == "SERVICE_VALIDATION_ERROR"
        assert exception.details.get("field") == "email"

    def test_create_resource_not_found_exception(self):
        """测试创建ResourceNotFoundException"""
        exception = create_exception(
            "SERVICE_RESOURCE_NOT_FOUND",
            "User not found",
            resource_type="User",
            resource_id="123"
        )

        assert isinstance(exception, ResourceNotFoundException)
        assert exception.details["resource_type"] == "User"
        assert exception.details["resource_id"] == "123"

    def test_create_insufficient_balance_exception(self):
        """测试创建InsufficientBalanceException"""
        exception = create_exception(
            "SERVICE_INSUFFICIENT_BALANCE",
            "Insufficient points",
            current_balance=50,
            required_amount=100
        )

        assert isinstance(exception, InsufficientBalanceException)
        assert exception.details["current_balance"] == 50
        assert exception.details["required_amount"] == 100

    def test_create_unknown_error_code(self):
        """测试未知错误代码时创建BusinessException"""
        exception = create_exception(
            "UNKNOWN_ERROR_CODE",
            "Unknown error"
        )

        assert isinstance(exception, BusinessException)
        assert exception.error_code == "UNKNOWN_ERROR_CODE"


class TestWrapRepositoryError:
    """wrap_repository_error工具函数测试"""

    def test_wrap_repository_not_found_error(self):
        """测试包装RepositoryNotFoundError"""
        repo_error = RepositoryNotFoundError("User not found")
        service_exception = wrap_repository_error(repo_error, "UserService.get_user")

        assert isinstance(service_exception, ResourceNotFoundException)
        assert service_exception.cause == repo_error
        assert "UserService.get_user" in service_exception.user_message

    def test_wrap_repository_validation_error(self):
        """测试包装RepositoryValidationError"""
        repo_error = RepositoryValidationError("Invalid email format")
        service_exception = wrap_repository_error(repo_error, "UserService.create_user")

        assert isinstance(service_exception, ValidationException)
        assert service_exception.cause == repo_error
        assert "UserService.create_user" in service_exception.message

    def test_wrap_repository_integrity_error(self):
        """测试包装RepositoryIntegrityError"""
        repo_error = RepositoryIntegrityError("Duplicate email")
        service_exception = wrap_repository_error(repo_error, "UserService.create_user")

        assert isinstance(service_exception, DuplicateResourceException)
        assert service_exception.cause == repo_error
        assert "UserService.create_user" in service_exception.user_message

    def test_wrap_generic_exception(self):
        """测试包装通用异常"""
        generic_error = ValueError("Generic error")
        service_exception = wrap_repository_error(generic_error, "UserService.some_method")

        assert isinstance(service_exception, BusinessException)
        assert service_exception.error_code == "SERVICE_REPOSITORY_ERROR"
        assert service_exception.cause == generic_error
        assert "UserService.some_method" in service_exception.message


class TestExceptionMapping:
    """异常映射测试"""

    def test_exception_mapping_completeness(self):
        """测试异常映射的完整性"""
        expected_codes = {
            "SERVICE_VALIDATION_ERROR",
            "SERVICE_RESOURCE_NOT_FOUND",
            "SERVICE_INSUFFICIENT_BALANCE",
            "SERVICE_DUPLICATE_RESOURCE",
            "SERVICE_AUTHENTICATION_ERROR",
            "SERVICE_AUTHORIZATION_ERROR"
        }

        mapped_codes = set(EXCEPTION_MAP.keys())
        assert mapped_codes == expected_codes

    def test_exception_mapping_values(self):
        """测试异常映射值的正确性"""
        assert EXCEPTION_MAP["SERVICE_VALIDATION_ERROR"] == ValidationException
        assert EXCEPTION_MAP["SERVICE_RESOURCE_NOT_FOUND"] == ResourceNotFoundException
        assert EXCEPTION_MAP["SERVICE_INSUFFICIENT_BALANCE"] == InsufficientBalanceException
        assert EXCEPTION_MAP["SERVICE_DUPLICATE_RESOURCE"] == DuplicateResourceException
        assert EXCEPTION_MAP["SERVICE_AUTHENTICATION_ERROR"] == AuthenticationException
        assert EXCEPTION_MAP["SERVICE_AUTHORIZATION_ERROR"] == AuthorizationException

    def test_all_exceptions_inherit_from_business_exception(self):
        """测试所有异常都继承自BusinessException"""
        for exception_class in EXCEPTION_MAP.values():
            assert issubclass(exception_class, BusinessException)


@pytest.mark.unit
class TestExceptionPerformance:
    """异常性能测试"""

    def test_exception_creation_performance(self, performance_monitor):
        """测试异常创建性能"""
        with performance_monitor("exception_creation", max_time_seconds=0.01):
            for _ in range(1000):
                BusinessException(
                    error_code="SERVICE_TEST_ERROR",
                    message="Test error",
                    details={"test": True}
                )

    def test_exception_to_dict_performance(self, performance_monitor):
        """测试异常字典转换性能"""
        exception = BusinessException(
            error_code="SERVICE_TEST_ERROR",
            message="Test error",
            details={"field": "email", "value": "test@example.com"},
            suggestions=["建议1", "建议2"]
        )

        with performance_monitor("exception_to_dict", max_time_seconds=0.05):
            for _ in range(1000):
                exception.to_dict()