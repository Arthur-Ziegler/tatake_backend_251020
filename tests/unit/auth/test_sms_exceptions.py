"""
SMS相关异常类单元测试

测试新增的SMS认证相关异常类，确保异常的继承关系、错误码和消息格式符合规范。
采用TDD方式，先写测试再实现异常类。

测试覆盖：
- 异常继承关系
- 错误码验证
- 消息格式测试
- 异常层级关系
- 自定义消息覆盖
"""

import pytest

from src.domains.auth.exceptions import (
    # 新增SMS异常
    RateLimitException,
    DailyLimitException,
    AccountLockedException,
    VerificationNotFoundException,
    VerificationExpiredException,
    InvalidVerificationCodeException,
    PhoneNotFoundException,
    PhoneAlreadyExistsException,
    PhoneAlreadyBoundException,

    # 基础异常类
    AuthenticationException,
    SMSException
)


class TestRateLimitException:
    """发送频率限制异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = RateLimitException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)
        assert isinstance(exception, Exception)

    def test_default_message(self):
        """测试默认消息"""
        exception = RateLimitException()
        assert exception.message == "短信发送过于频繁，请稍后再试"
        assert exception.error_code == "SMS_RATE_LIMIT"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "请在60秒后重试"
        exception = RateLimitException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "SMS_RATE_LIMIT"

    def test_str_representation(self):
        """测试字符串表示"""
        exception = RateLimitException()
        str_repr = str(exception)
        assert "短信发送过于频繁，请稍后再试" in str_repr

    def test_error_code_constant(self):
        """测试错误码常量"""
        assert RateLimitException().error_code == "SMS_RATE_LIMIT"


class TestDailyLimitException:
    """每日次数限制异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = DailyLimitException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = DailyLimitException()
        assert exception.message == "今日短信发送次数已达上限"
        assert exception.error_code == "SMS_DAILY_LIMIT"

    def test_custom_message_with_count(self):
        """测试带次数的自定义消息"""
        custom_message = "今日已发送5次，已达上限"
        exception = DailyLimitException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "SMS_DAILY_LIMIT"


class TestAccountLockedException:
    """账号锁定异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = AccountLockedException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = AccountLockedException()
        assert exception.message == "账号已锁定，请稍后再试"
        assert exception.error_code == "ACCOUNT_LOCKED"

    def test_custom_message_with_time(self):
        """测试带时间的自定义消息"""
        custom_message = "账号已锁定至2025-01-01 12:00:00"
        exception = AccountLockedException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "ACCOUNT_LOCKED"


class TestVerificationNotFoundException:
    """验证码不存在异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = VerificationNotFoundException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = VerificationNotFoundException()
        assert exception.message == "验证码不存在"
        assert exception.error_code == "VERIFICATION_NOT_FOUND"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "未找到该手机号的验证码"
        exception = VerificationNotFoundException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "VERIFICATION_NOT_FOUND"


class TestVerificationExpiredException:
    """验证码过期异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = VerificationExpiredException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = VerificationExpiredException()
        assert exception.message == "验证码已过期"
        assert exception.error_code == "VERIFICATION_EXPIRED"

    def test_custom_message_with_time(self):
        """测试带时间的自定义消息"""
        custom_message = "验证码已过期，请重新获取"
        exception = VerificationExpiredException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "VERIFICATION_EXPIRED"


class TestInvalidVerificationCodeException:
    """验证码错误异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = InvalidVerificationCodeException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = InvalidVerificationCodeException()
        assert exception.message == "验证码错误"
        assert exception.error_code == "INVALID_VERIFICATION_CODE"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "验证码错误，还剩3次尝试机会"
        exception = InvalidVerificationCodeException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "INVALID_VERIFICATION_CODE"


class TestPhoneNotFoundException:
    """手机号未注册异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = PhoneNotFoundException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = PhoneNotFoundException()
        assert exception.message == "手机号未注册"
        assert exception.error_code == "PHONE_NOT_FOUND"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "该手机号尚未注册账号"
        exception = PhoneNotFoundException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "PHONE_NOT_FOUND"


class TestPhoneAlreadyExistsException:
    """手机号已注册异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = PhoneAlreadyExistsException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = PhoneAlreadyExistsException()
        assert exception.message == "手机号已注册"
        assert exception.error_code == "PHONE_ALREADY_EXISTS"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "该手机号已被其他账号使用"
        exception = PhoneAlreadyExistsException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "PHONE_ALREADY_EXISTS"


class TestPhoneAlreadyBoundException:
    """手机号已绑定异常测试"""

    def test_inheritance(self):
        """测试继承关系"""
        exception = PhoneAlreadyBoundException()
        assert isinstance(exception, SMSException)
        assert isinstance(exception, AuthenticationException)

    def test_default_message(self):
        """测试默认消息"""
        exception = PhoneAlreadyBoundException()
        assert exception.message == "手机号已绑定"
        assert exception.error_code == "PHONE_ALREADY_BOUND"

    def test_custom_message(self):
        """测试自定义消息"""
        custom_message = "该手机号已绑定其他账号"
        exception = PhoneAlreadyBoundException(custom_message)
        assert exception.message == custom_message
        assert exception.error_code == "PHONE_ALREADY_BOUND"


class TestExceptionHierarchy:
    """异常层级关系测试"""

    def test_all_sms_exceptions_inherit_from_base(self):
        """测试所有SMS异常都继承自基础异常"""
        sms_exceptions = [
            RateLimitException,
            DailyLimitException,
            AccountLockedException,
            VerificationNotFoundException,
            VerificationExpiredException,
            InvalidVerificationCodeException,
            PhoneNotFoundException,
            PhoneAlreadyExistsException,
            PhoneAlreadyBoundException,
        ]

        for exception_class in sms_exceptions:
            # 创建实例
            exception = exception_class()

            # 验证继承关系
            assert isinstance(exception, SMSException)
            assert isinstance(exception, AuthenticationException)
            assert isinstance(exception, Exception)

            # 验证有错误码
            assert hasattr(exception, 'error_code')
            assert hasattr(exception, 'message')
            assert exception.error_code is not None
            assert exception.message is not None

    def test_error_codes_are_unique(self):
        """测试错误码都是唯一的"""
        exceptions = [
            RateLimitException(),
            DailyLimitException(),
            AccountLockedException(),
            VerificationNotFoundException(),
            VerificationExpiredException(),
            InvalidVerificationCodeException(),
            PhoneNotFoundException(),
            PhoneAlreadyExistsException(),
            PhoneAlreadyBoundException(),
        ]

        error_codes = [exc.error_code for exc in exceptions]
        assert len(error_codes) == len(set(error_codes)), "错误码应该唯一"

    def test_exception_catch_hierarchy(self):
        """测试异常捕获层级"""
        try:
            raise RateLimitException()
        except SMSException as e:
            assert isinstance(e, RateLimitException)
            assert e.error_code == "SMS_RATE_LIMIT"
        except AuthenticationException:
            pytest.fail("应该被SMSException捕获")

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as original_error:
                raise RateLimitException("包装错误") from original_error
        except RateLimitException as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "原始错误"