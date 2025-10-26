"""
验证器测试

测试基础的验证功能，包括：
1. 字符串验证
2. 数字验证
3. 类型验证
4. 自定义验证规则

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import UUID
from email.utils import parseaddr
import re


@pytest.mark.unit
class TestStringValidation:
    """字符串验证测试类"""

    def test_string_length_validation(self):
        """测试字符串长度验证"""
        def validate_length(value, min_length=0, max_length=None):
            if not isinstance(value, str):
                return False
            if len(value) < min_length:
                return False
            if max_length is not None and len(value) > max_length:
                return False
            return True

        # 测试最小长度
        assert validate_length("hello", min_length=3) is True
        assert validate_length("hi", min_length=3) is False

        # 测试最大长度
        assert validate_length("hello", max_length=10) is True
        assert validate_length("very long string", max_length=10) is False

        # 测试范围
        assert validate_length("hello", min_length=3, max_length=10) is True
        assert validate_length("hi", min_length=3, max_length=10) is False
        assert validate_length("very long", min_length=3, max_length=10) is False

    def test_string_pattern_validation(self):
        """测试字符串模式验证"""
        def validate_pattern(value, pattern):
            if not isinstance(value, str):
                return False
            return bool(re.match(pattern, value))

        # 测试邮箱模式
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        assert validate_pattern("test@example.com", email_pattern) is True
        assert validate_pattern("invalid-email", email_pattern) is False

        # 测试数字模式
        number_pattern = r"^\d+$"
        assert validate_pattern("123", number_pattern) is True
        assert validate_pattern("abc", number_pattern) is False
        assert validate_pattern("123abc", number_pattern) is False

    def test_string_empty_validation(self):
        """测试字符串空值验证"""
        def validate_not_empty(value):
            return isinstance(value, str) and len(value) > 0

        assert validate_not_empty("hello") is True
        assert validate_not_empty("") is False
        assert validate_not_empty("   ") is True  # 空格不算空
        assert validate_not_empty(None) is False

    def test_string_whitespace_handling(self):
        """测试字符串空白处理"""
        def validate_no_surrounding_whitespace(value):
            if not isinstance(value, str):
                return False
            return value == value.strip()

        assert validate_no_surrounding_whitespace("hello") is True
        assert validate_no_surrounding_whitespace("  hello") is False
        assert validate_no_surrounding_whitespace("hello  ") is False
        assert validate_no_surrounding_whitespace("  hello  ") is False


@pytest.mark.unit
class TestNumberValidation:
    """数字验证测试类"""

    def test_integer_validation(self):
        """测试整数验证"""
        def validate_integer(value):
            return isinstance(value, int)

        assert validate_integer(123) is True
        assert validate_integer(-456) is True
        assert validate_integer(0) is True

        assert validate_integer(123.45) is False
        assert validate_integer("123") is False
        assert validate_integer(None) is False

    def test_float_validation(self):
        """测试浮点数验证"""
        def validate_float(value):
            return isinstance(value, (int, float))

        assert validate_float(123) is True
        assert validate_float(123.45) is True
        assert validate_float(-1.23) is True

        assert validate_float("123") is False
        assert validate_float(None) is False

    def test_range_validation(self):
        """测试范围验证"""
        def validate_range(value, min_value=None, max_value=None):
            if not isinstance(value, (int, float)):
                return False
            if min_value is not None and value < min_value:
                return False
            if max_value is not None and value > max_value:
                return False
            return True

        # 测试最小值
        assert validate_range(10, min_value=5) is True
        assert validate_range(3, min_value=5) is False

        # 测试最大值
        assert validate_range(3, max_value=10) is True
        assert validate_range(15, max_value=10) is False

        # 测试范围
        assert validate_range(7, min_value=5, max_value=10) is True
        assert validate_range(3, min_value=5, max_value=10) is False
        assert validate_range(15, min_value=5, max_value=10) is False

    def test_positive_negative_validation(self):
        """测试正负数验证"""
        def validate_positive(value):
            return isinstance(value, (int, float)) and value > 0

        def validate_non_negative(value):
            return isinstance(value, (int, float)) and value >= 0

        def validate_negative(value):
            return isinstance(value, (int, float)) and value < 0

        assert validate_positive(5) is True
        assert validate_positive(0) is False
        assert validate_positive(-5) is False

        assert validate_non_negative(5) is True
        assert validate_non_negative(0) is True
        assert validate_non_negative(-5) is False

        assert validate_negative(5) is False
        assert validate_negative(0) is False
        assert validate_negative(-5) is True


@pytest.mark.unit
class TestTypeValidation:
    """类型验证测试类"""

    def test_basic_type_validation(self):
        """测试基本类型验证"""
        def validate_type(value, expected_type):
            return isinstance(value, expected_type)

        # 字符串类型
        assert validate_type("hello", str) is True
        assert validate_type(123, str) is False

        # 数字类型
        assert validate_type(123, int) is True
        assert validate_type(123.45, int) is False

        # 布尔类型
        assert validate_type(True, bool) is True
        assert validate_type(1, bool) is False

        # 列表类型
        assert validate_type([1, 2, 3], list) is True
        assert validate_type("not a list", list) is False

        # 字典类型
        assert validate_type({"key": "value"}, dict) is True
        assert validate_type("not a dict", dict) is False

    def test_union_type_validation(self):
        """测试联合类型验证"""
        def validate_union(value, types):
            return isinstance(value, tuple(types))

        # 字符串或数字
        assert validate_union("hello", (str, int)) is True
        assert validate_union(123, (str, int)) is True
        assert validate_union(123.45, (str, int)) is False

        # 多种类型
        assert validate_union(True, (str, int, bool)) is True
        assert validate_union([1, 2, 3], (str, int, bool)) is False

    def test_nullable_validation(self):
        """测试可空验证"""
        def validate_nullable(value, base_type):
            return value is None or isinstance(value, base_type)

        # 可空字符串
        assert validate_nullable(None, str) is True
        assert validate_nullable("hello", str) is True
        assert validate_nullable(123, str) is False

        # 可空整数
        assert validate_nullable(None, int) is True
        assert validate_nullable(123, int) is True
        assert validate_nullable("123", int) is False

    def test_optional_validation(self):
        """测试可选验证"""
        def validate_optional(value, validator_func):
            if value is None:
                return True
            return validator_func(value)

        def validate_string_length(value):
            return isinstance(value, str) and len(value) >= 3

        # 可选字符串长度验证
        assert validate_optional(None, validate_string_length) is True
        assert validate_optional("hello", validate_string_length) is True
        assert validate_optional("hi", validate_string_length) is False


@pytest.mark.unit
class TestCustomValidation:
    """自定义验证测试类"""

    def test_email_validation(self):
        """测试邮箱验证"""
        def validate_email(value):
            if not isinstance(value, str):
                return False
            try:
                name, email = parseaddr(value)
                return "@" in email and "." in email.split("@")[-1]
            except:
                return False

        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com"
        ]

        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "",
            "not-an-email"
        ]

        for email in valid_emails:
            assert validate_email(email) is True, f"Should validate: {email}"

        for email in invalid_emails:
            assert validate_email(email) is False, f"Should not validate: {email}"

    def test_url_validation(self):
        """测试URL验证"""
        def validate_url(value):
            if not isinstance(value, str):
                return False
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            return url_pattern.match(value) is not None

        valid_urls = [
            "https://www.example.com",
            "http://example.org",
            "https://subdomain.example.com/path",
            "https://example.com:8080",
            "http://localhost:3000"
        ]

        invalid_urls = [
            "not-a-url",
            "example.com",  # 缺少协议
            "http://",
            "://example.com",
            "",
            "just text"
        ]

        for url in valid_urls:
            assert validate_url(url) is True, f"Should validate: {url}"

        for url in invalid_urls:
            assert validate_url(url) is False, f"Should not validate: {url}"

    def test_phone_validation(self):
        """测试电话号码验证"""
        def validate_phone(value):
            if not isinstance(value, str):
                return False
            # 简单的电话号码验证（只包含数字、空格、括号、连字符、加号）
            phone_pattern = re.compile(r'^[\d\s\-\+\(\)]+$')
            return phone_pattern.match(value) is not None and len(re.sub(r'\D', '', value)) >= 10

        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "5551234567",
            "+86 138 0013 8000"
        ]

        invalid_phones = [
            "123",  # 太短
            "abc-def-ghij",  # 包含字母
            "",  # 空
            "not-a-phone"
        ]

        for phone in valid_phones:
            assert validate_phone(phone) is True, f"Should validate: {phone}"

        for phone in invalid_phones:
            assert validate_phone(phone) is False, f"Should not validate: {phone}"

    def test_custom_rule_validation(self):
        """测试自定义规则验证"""
        def validate_even_number(value):
            if not isinstance(value, int):
                return False
            return value % 2 == 0

        def validate_palindrome(value):
            if not isinstance(value, str):
                return False
            return value == value[::-1]

        # 测试偶数验证
        assert validate_even_number(2) is True
        assert validate_even_number(4) is True
        assert validate_even_number(3) is False
        assert validate_even_number(0) is True

        # 测试回文验证
        assert validate_palindrome("racecar") is True
        assert validate_palindrome("level") is True
        assert validate_palindrome("hello") is False
        assert validate_palindrome("") is True  # 空字符串是回文


@pytest.mark.unit
class TestConditionalValidation:
    """条件验证测试类"""

    def test_conditional_validation(self):
        """测试条件验证"""
        def validate_conditionally(value, condition, validator):
            if condition(value):
                return validator(value)
            return True  # 条件不满足时跳过验证

        def is_string(value):
            return isinstance(value, str)

        def validate_length_at_least_5(value):
            return len(value) >= 5

        # 条件验证：如果是字符串，长度至少为5
        assert validate_conditionally("hello world", is_string, validate_length_at_least_5) is True
        assert validate_conditionally("hi", is_string, validate_length_at_least_5) is False
        assert validate_conditionally(123, is_string, validate_length_at_least_5) is True  # 跳过验证

    def test_dependent_validation(self):
        """测试依赖验证"""
        def validate_with_dependencies(value, dependencies):
            # value: 要验证的值
            # dependencies: 依赖的其他字段值
            if value is None:
                return True

            # 示例：如果password字段有值，confirm_password必须匹配
            password = dependencies.get('password')
            confirm_password = value

            if password is not None:
                return password == confirm_password

            return True

        # 测试密码确认验证
        assert validate_with_dependencies("secret123", {'password': 'secret123'}) is True
        assert validate_with_dependencies("different", {'password': 'secret123'}) is False
        assert validate_with_dependencies("any", {'password': None}) is True  # 没有密码时跳过


@pytest.mark.parametrize("value,min_length,max_length,expected", [
    ("hello", 3, 10, True),
    ("hi", 3, 10, False),      # 太短
    ("very long string", 3, 10, False),  # 太长
    ("", 0, 5, True),          # 允许空字符串
    (123, 1, 10, False),       # 不是字符串
])
def test_length_validation_parameterized(value, min_length, max_length, expected):
    """参数化长度验证测试"""
    def validate_length(value, min_length=0, max_length=None):
        if not isinstance(value, str):
            return False
        if len(value) < min_length:
            return False
        if max_length is not None and len(value) > max_length:
            return False
        return True

    result = validate_length(value, min_length, max_length)
    assert result == expected


@pytest.mark.parametrize("value,min_val,max_val,expected", [
    (5, 1, 10, True),
    (0, 1, 10, False),        # 小于最小值
    (15, 1, 10, False),       # 大于最大值
    (5, None, 10, True),      # 只有最大值
    (5, 1, None, True),       # 只有最小值
    ("5", 1, 10, False),      # 不是数字
])
def test_range_validation_parameterized(value, min_val, max_val, expected):
    """参数化范围验证测试"""
    def validate_range(value, min_value=None, max_value=None):
        if not isinstance(value, (int, float)):
            return False
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
        return True

    result = validate_range(value, min_val, max_val)
    assert result == expected


@pytest.fixture
def validation_rules():
    """验证规则fixture"""
    return {
        'string_min_length': lambda x: isinstance(x, str) and len(x) >= 3,
        'positive_integer': lambda x: isinstance(x, int) and x > 0,
        'valid_email': lambda x: isinstance(x, str) and '@' in x and '.' in x.split('@')[-1],
    }


def test_with_fixture(validation_rules):
    """使用fixture的测试"""
    # 测试字符串最小长度
    assert validation_rules['string_min_length']("hello") is True
    assert validation_rules['string_min_length']("hi") is False

    # 测试正整数
    assert validation_rules['positive_integer'](5) is True
    assert validation_rules['positive_integer'](-5) is False

    # 测试邮箱
    assert validation_rules['valid_email']("test@example.com") is True
    assert validation_rules['valid_email']("invalid-email") is False