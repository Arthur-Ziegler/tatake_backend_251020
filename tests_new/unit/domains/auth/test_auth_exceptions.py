"""
Auth领域异常测试

测试认证系统的异常定义和行为，包括：
1. 异常创建和属性验证
2. 异常继承关系
3. 错误代码和消息格式
4. 异常字符串表示

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from src.domains.auth.exceptions import (
    AuthenticationException,
    ValidationError,
    TokenException,
    TokenExpiredException,
    TokenInvalidException,
    UserNotFoundException,
)


@pytest.mark.unit
class TestAuthenticationException:
    """认证异常基类测试"""

    def test_authentication_exception_basic_creation(self):
        """测试基本认证异常创建"""
        message = "认证失败"
        error_code = "AUTH_FAILED"

        exception = AuthenticationException(message, error_code)

        assert exception.message == message
        assert exception.error_code == error_code
        assert str(exception) == message

    def test_authentication_exception_without_error_code(self):
        """测试不带错误码的认证异常"""
        message = "认证失败"

        exception = AuthenticationException(message)

        assert exception.message == message
        assert exception.error_code is None
        assert str(exception) == message

    def test_authentication_exception_inheritance(self):
        """测试异常继承关系"""
        exception = AuthenticationException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, AuthenticationException)


@pytest.mark.unit
class TestValidationError:
    """验证异常测试"""

    def test_validation_error_basic_creation(self):
        """测试基本验证异常创建"""
        message = "数据验证失败"
        field = "email"

        exception = ValidationError(message, field)

        assert exception.message == message
        assert exception.field == field
        assert exception.error_code == "VALIDATION_ERROR"
        assert str(exception) == message

    def test_validation_error_without_field(self):
        """测试不带字段名的验证异常"""
        message = "数据验证失败"

        exception = ValidationError(message)

        assert exception.message == message
        assert exception.field is None
        assert exception.error_code == "VALIDATION_ERROR"

    def test_validation_error_inheritance(self):
        """测试验证异常继承关系"""
        exception = ValidationError("测试")

        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, ValidationError)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("message,field", [
        ("用户名不能为空", "username"),
        ("密码格式不正确", "password"),
        ("邮箱格式无效", "email"),
        ("手机号格式错误", "phone"),
    ])
    def test_validation_error_various_scenarios(self, message, field):
        """测试各种验证异常场景"""
        exception = ValidationError(message, field)

        assert exception.message == message
        assert exception.field == field
        assert exception.error_code == "VALIDATION_ERROR"


@pytest.mark.unit
class TestTokenException:
    """令牌异常测试"""

    def test_token_exception_creation(self):
        """测试令牌异常创建"""
        message = "令牌处理失败"
        error_code = "TOKEN_ERROR"

        exception = TokenException(message, error_code)

        assert exception.message == message
        assert exception.error_code == error_code
        assert str(exception) == message

    def test_token_exception_inheritance(self):
        """测试令牌异常继承关系"""
        exception = TokenException("测试", "TEST_ERROR")

        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, TokenException)
        assert isinstance(exception, Exception)


@pytest.mark.unit
class TestTokenExpiredException:
    """令牌过期异常测试"""

    def test_token_expired_exception_default_message(self):
        """测试令牌过期异常默认消息"""
        exception = TokenExpiredException()

        assert exception.message == "令牌已过期"
        assert exception.error_code == "TOKEN_EXPIRED"
        assert str(exception) == "令牌已过期"

    def test_token_expired_exception_custom_message(self):
        """测试令牌过期异常自定义消息"""
        message = "访问令牌已过期，请重新登录"
        exception = TokenExpiredException(message)

        assert exception.message == message
        assert exception.error_code == "TOKEN_EXPIRED"
        assert str(exception) == message

    def test_token_expired_exception_inheritance(self):
        """测试令牌过期异常继承关系"""
        exception = TokenExpiredException()

        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, TokenException)
        assert isinstance(exception, TokenExpiredException)
        assert isinstance(exception, Exception)


@pytest.mark.unit
class TestTokenInvalidException:
    """令牌无效异常测试"""

    def test_token_invalid_exception_creation(self):
        """测试令牌无效异常创建"""
        message = "令牌格式无效"
        exception = TokenInvalidException(message)

        assert exception.message == message
        assert exception.error_code == "TOKEN_INVALID"
        assert str(exception) == message

    def test_token_invalid_exception_inheritance(self):
        """测试令牌无效异常继承关系"""
        exception = TokenInvalidException("测试")

        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, TokenException)
        assert isinstance(exception, TokenInvalidException)
        assert isinstance(exception, Exception)


@pytest.mark.unit
class TestUserNotFoundException:
    """用户未找到异常测试"""

    def test_user_not_found_exception_default_creation(self):
        """测试用户未找到异常默认创建"""
        exception = UserNotFoundException()

        assert exception.message == "用户不存在"
        assert exception.error_code == "USER_NOT_FOUND"
        assert str(exception) == "用户不存在"

    def test_user_not_found_exception_custom_message(self):
        """测试用户未找到异常自定义消息"""
        message = "指定的用户不存在"
        exception = UserNotFoundException(message)

        assert exception.message == message
        assert exception.error_code == "USER_NOT_FOUND"
        assert str(exception) == message

    def test_user_not_found_exception_inheritance(self):
        """测试用户未找到异常继承关系"""
        exception = UserNotFoundException("test_user")

        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, UserNotFoundException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("message", [
        "用户不存在",
        "指定的用户不存在，请检查用户ID",
        "无法找到该用户信息",
        "用户账户已被删除或不存在",
    ])
    def test_user_not_found_exception_various_messages(self, message):
        """测试各种用户未找到异常消息"""
        exception = UserNotFoundException(message)

        assert exception.message == message
        assert exception.error_code == "USER_NOT_FOUND"


@pytest.mark.integration
class TestExceptionIntegration:
    """异常集成测试"""

    def test_exception_hierarchy_consistency(self):
        """测试异常层次结构一致性"""
        # 所有自定义异常都应该继承自AuthenticationException
        base_exception = AuthenticationException("base")
        validation_exception = ValidationError("validation")
        token_exception = TokenException("token", "TOKEN_ERROR")
        token_expired = TokenExpiredException()
        token_invalid = TokenInvalidException("invalid")
        user_not_found = UserNotFoundException("user123")

        # 验证继承关系
        assert isinstance(validation_exception, AuthenticationException)
        assert isinstance(token_exception, AuthenticationException)
        assert isinstance(token_expired, AuthenticationException)
        assert isinstance(token_invalid, AuthenticationException)
        assert isinstance(user_not_found, AuthenticationException)

    def test_exception_error_codes_uniqueness(self):
        """测试异常错误码唯一性"""
        exceptions = [
            ValidationError("test", "field1"),
            TokenException("test", "TOKEN_ERROR"),
            TokenExpiredException(),
            TokenInvalidException("test"),
            UserNotFoundException("user123"),
        ]

        error_codes = set()
        for exc in exceptions:
            assert exc.error_code not in error_codes, f"重复的错误码: {exc.error_code}"
            error_codes.add(exc.error_code)

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        # 测试基类异常
        with pytest.raises(AuthenticationException) as exc_info:
            raise AuthenticationException("认证失败")

        assert exc_info.value.message == "认证失败"

        # 测试验证异常
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("数据验证失败", "email")

        assert exc_info.value.field == "email"
        assert exc_info.value.error_code == "VALIDATION_ERROR"

        # 测试令牌异常
        with pytest.raises(TokenExpiredException) as exc_info:
            raise TokenExpiredException()

        assert exc_info.value.error_code == "TOKEN_EXPIRED"

        # 测试用户未找到异常
        with pytest.raises(UserNotFoundException) as exc_info:
            raise UserNotFoundException("test_user")

        assert exc_info.value.message == "test_user"

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as original_error:
                raise ValidationError("包装的验证错误", "field") from original_error
        except ValidationError as chained_error:
            # 验证异常链
            assert chained_error.__cause__ is not None
            assert isinstance(chained_error.__cause__, ValueError)
            assert chained_error.__cause__.args[0] == "原始错误"
            assert chained_error.message == "包装的验证错误"