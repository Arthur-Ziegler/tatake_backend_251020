"""
认证领域异常定义

定义了认证系统中使用的所有自定义异常类。
这些异常提供了详细的错误信息，帮助前端进行错误处理和用户提示。

异常分类:
- AuthenticationException: 认证相关异常基类
- ValidationError: 数据验证异常
- TokenException: 令牌相关异常
- SMSException: 短信服务异常
- UserException: 用户相关异常
"""

from typing import Optional


class AuthenticationException(Exception):
    """认证异常基类"""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(AuthenticationException):
    """数据验证异常"""

    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class TokenException(AuthenticationException):
    """令牌相关异常基类"""

    def __init__(self, message: str, error_code: str):
        super().__init__(message, error_code)


class TokenExpiredException(TokenException):
    """令牌过期异常"""

    def __init__(self, message: str = "令牌已过期"):
        super().__init__(message, "TOKEN_EXPIRED")


class TokenInvalidException(TokenException):
    """令牌无效异常"""

    def __init__(self, message: str = "令牌无效"):
        super().__init__(message, "TOKEN_INVALID")


class TokenRevokedException(TokenException):
    """令牌已被撤销异常"""

    def __init__(self, message: str = "令牌已被撤销"):
        super().__init__(message, "TOKEN_REVOKED")


class TokenBlacklistedException(TokenException):
    """令牌已在黑名单中异常"""

    def __init__(self, message: str = "令牌已被撤销"):
        super().__init__(message, "TOKEN_BLACKLISTED")


class SMSException(AuthenticationException):
    """短信服务异常"""

    def __init__(self, message: str, error_code: str = "SMS_ERROR"):
        super().__init__(message, error_code)


class SMSRateLimitException(SMSException):
    """短信发送频率限制异常"""

    def __init__(self, message: str = "短信发送过于频繁，请稍后再试"):
        super().__init__(message, "SMS_RATE_LIMIT")


class SMSVerificationFailedException(SMSException):
    """短信验证码验证失败异常"""

    def __init__(self, message: str = "验证码错误或已过期"):
        super().__init__(message, "SMS_VERIFICATION_FAILED")


class UserException(AuthenticationException):
    """用户相关异常基类"""

    def __init__(self, message: str, error_code: str = "USER_ERROR"):
        super().__init__(message, error_code)


class UserNotFoundException(UserException):
    """用户不存在异常"""

    def __init__(self, message: str = "用户不存在"):
        super().__init__(message, "USER_NOT_FOUND")


class UserAlreadyExistsException(UserException):
    """用户已存在异常"""

    def __init__(self, message: str = "用户已存在"):
        super().__init__(message, "USER_ALREADY_EXISTS")


class UserDisabledException(UserException):
    """用户已禁用异常"""

    def __init__(self, message: str = "用户已被禁用"):
        super().__init__(message, "USER_DISABLED")


class GuestUpgradeException(UserException):
    """游客账号升级异常"""

    def __init__(self, message: str = "游客账号升级失败"):
        super().__init__(message, "GUEST_UPGRADE_FAILED")


class InvalidCredentialsException(AuthenticationException):
    """无效凭据异常"""

    def __init__(self, message: str = "用户名或密码错误"):
        super().__init__(message, "INVALID_CREDENTIALS")


class InsufficientPermissionsException(AuthenticationException):
    """权限不足异常"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "INSUFFICIENT_PERMISSIONS")


class ServiceUnavailableException(AuthenticationException):
    """服务不可用异常"""

    def __init__(self, message: str = "服务暂时不可用，请稍后再试"):
        super().__init__(message, "SERVICE_UNAVAILABLE")


class RateLimitException(AuthenticationException):
    """请求频率限制异常"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class DatabaseException(AuthenticationException):
    """数据库异常"""

    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, "DATABASE_ERROR")


class ConfigurationException(AuthenticationException):
    """配置异常"""

    def __init__(self, message: str = "系统配置错误"):
        super().__init__(message, "CONFIGURATION_ERROR")


# SMS认证相关异常（add-phone-sms-auth提案新增）

class RateLimitException(SMSException):
    """发送频率限制异常"""

    def __init__(self, message: str = "短信发送过于频繁，请稍后再试"):
        super().__init__(message, "SMS_RATE_LIMIT")


class DailyLimitException(SMSException):
    """每日次数限制异常"""

    def __init__(self, message: str = "今日短信发送次数已达上限"):
        super().__init__(message, "SMS_DAILY_LIMIT")


class AccountLockedException(SMSException):
    """账号锁定异常"""

    def __init__(self, message: str = "账号已锁定，请稍后再试"):
        super().__init__(message, "ACCOUNT_LOCKED")


class VerificationNotFoundException(SMSException):
    """验证码不存在异常"""

    def __init__(self, message: str = "验证码不存在"):
        super().__init__(message, "VERIFICATION_NOT_FOUND")


class VerificationExpiredException(SMSException):
    """验证码过期异常"""

    def __init__(self, message: str = "验证码已过期"):
        super().__init__(message, "VERIFICATION_EXPIRED")


class InvalidVerificationCodeException(SMSException):
    """验证码错误异常"""

    def __init__(self, message: str = "验证码错误"):
        super().__init__(message, "INVALID_VERIFICATION_CODE")


class PhoneNotFoundException(SMSException):
    """手机号未注册异常"""

    def __init__(self, message: str = "手机号未注册"):
        super().__init__(message, "PHONE_NOT_FOUND")


class PhoneAlreadyExistsException(SMSException):
    """手机号已注册异常"""

    def __init__(self, message: str = "手机号已注册"):
        super().__init__(message, "PHONE_ALREADY_EXISTS")


class PhoneAlreadyBoundException(SMSException):
    """手机号已绑定异常"""

    def __init__(self, message: str = "手机号已绑定"):
        super().__init__(message, "PHONE_ALREADY_BOUND")