"""
类型工具测试

测试基础的类型功能，包括：
1. 基本类型验证
2. 类型转换功能
3. 类型检查工具

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4


@pytest.mark.unit
class TestBasicTypes:
    """基础类型测试类"""

    def test_string_type_validation(self):
        """测试字符串类型验证"""
        # 基本字符串验证
        assert isinstance("hello", str)
        assert isinstance("", str)
        assert not isinstance(123, str)
        assert not isinstance(None, str)

    def test_number_type_validation(self):
        """测试数字类型验证"""
        # 整数验证
        assert isinstance(123, int)
        assert isinstance(0, int)
        assert isinstance(-456, int)

        # 浮点数验证
        assert isinstance(123.45, float)
        assert isinstance(0.0, float)
        assert isinstance(-1.23, float)

        # 非数字类型
        assert not isinstance("123", int)
        assert not isinstance("123.45", float)

    def test_boolean_type_validation(self):
        """测试布尔类型验证"""
        assert isinstance(True, bool)
        assert isinstance(False, bool)
        assert not isinstance(1, bool)
        assert not isinstance(0, bool)
        assert not isinstance("true", bool)

    def test_datetime_type_validation(self):
        """测试日期时间类型验证"""
        # 有效的日期时间
        now = datetime.now()
        utc_now = datetime.now(timezone.utc)

        assert isinstance(now, datetime)
        assert isinstance(utc_now, datetime)

        # 无效的日期时间
        assert not isinstance("2024-01-01", datetime)
        assert not isinstance(1234567890, datetime)

    def test_uuid_type_validation(self):
        """测试UUID类型验证"""
        test_uuid = uuid4()

        assert isinstance(test_uuid, UUID)
        assert not isinstance("12345678-1234-5678-1234-567812345678", UUID)
        assert not isinstance(123, UUID)

    def test_list_type_validation(self):
        """测试列表类型验证"""
        # 有效列表
        assert isinstance([], list)
        assert isinstance([1, 2, 3], list)
        assert isinstance(["a", "b", "c"], list)

        # 无效列表
        assert not isinstance("not a list", list)
        assert not isinstance(123, list)
        assert not isinstance(None, list)

    def test_dict_type_validation(self):
        """测试字典类型验证"""
        # 有效字典
        assert isinstance({}, dict)
        assert isinstance({"key": "value"}, dict)
        assert isinstance({"a": 1, "b": 2}, dict)

        # 无效字典
        assert not isinstance("not a dict", dict)
        assert not isinstance(123, dict)
        assert not isinstance([], dict)


@pytest.mark.unit
class TestTypeConversion:
    """类型转换测试类"""

    def test_string_to_int_conversion(self):
        """测试字符串到整数转换"""
        # 有效转换
        assert int("123") == 123
        assert int("0") == 0
        assert int("-456") == -456

        # 无效转换会抛出异常
        with pytest.raises(ValueError):
            int("not_a_number")

    def test_string_to_float_conversion(self):
        """测试字符串到浮点数转换"""
        # 有效转换
        assert float("123.45") == 123.45
        assert float("0.0") == 0.0
        assert float("-1.23") == -1.23

        # 无效转换
        with pytest.raises(ValueError):
            float("not_a_number")

    def test_int_to_string_conversion(self):
        """测试整数到字符串转换"""
        assert str(123) == "123"
        assert str(0) == "0"
        assert str(-456) == "-456"

    def test_float_to_string_conversion(self):
        """测试浮点数到字符串转换"""
        assert str(123.45) == "123.45"
        assert str(0.0) == "0.0"
        assert str(-1.23) == "-1.23"

    def test_string_to_bool_conversion(self):
        """测试字符串到布尔转换"""
        # 常见的字符串到布尔转换模式
        truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes"]
        falsy_values = ["false", "False", "FALSE", "0", "no", "No", ""]

        for value in truthy_values:
            # 这些通常被认为是真值
            assert value.lower() in ["true", "1", "yes"] or value == "1"

        for value in falsy_values:
            # 这些通常被认为是假值
            assert value.lower() in ["false", "0", "no", ""]


@pytest.mark.unit
class TestTypeUtilities:
    """类型工具测试类"""

    def test_type_checking_functions(self):
        """测试类型检查函数"""
        # 基本类型检查
        def is_string(value):
            return isinstance(value, str)

        def is_number(value):
            return isinstance(value, (int, float))

        def is_boolean(value):
            return isinstance(value, bool)

        # 测试类型检查函数
        assert is_string("hello") is True
        assert is_string(123) is False

        assert is_number(123) is True
        assert is_number(123.45) is True
        assert is_number("123") is False

        assert is_boolean(True) is True
        assert is_boolean(False) is True
        assert is_boolean(1) is False

    def test_type_validation_with_constraints(self):
        """测试带约束的类型验证"""
        def validate_string_length(value, min_length=0, max_length=None):
            if not isinstance(value, str):
                return False
            if len(value) < min_length:
                return False
            if max_length is not None and len(value) > max_length:
                return False
            return True

        # 测试字符串长度验证
        assert validate_string_length("hello", min_length=3) is True
        assert validate_string_length("hi", min_length=3) is False
        assert validate_string_length("very long string", max_length=10) is False

    def test_nullable_type_handling(self):
        """测试可空类型处理"""
        def is_nullable_string(value):
            return value is None or isinstance(value, str)

        # 测试可空字符串
        assert is_nullable_string(None) is True
        assert is_nullable_string("hello") is True
        assert is_nullable_string(123) is False

    def test_optional_type_handling(self):
        """测试可选类型处理"""
        def process_optional_string(value):
            if value is None:
                return "default"
            if isinstance(value, str):
                return value.upper()
            raise TypeError("Expected string or None")

        # 测试可选字符串处理
        assert process_optional_string(None) == "default"
        assert process_optional_string("hello") == "HELLO"

        with pytest.raises(TypeError):
            process_optional_string(123)

    def test_union_type_validation(self):
        """测试联合类型验证"""
        def is_string_or_number(value):
            return isinstance(value, (str, int, float))

        # 测试联合类型
        assert is_string_or_number("hello") is True
        assert is_string_or_number(123) is True
        assert is_string_or_number(123.45) is True
        assert is_string_or_number(True) is False
        assert is_string_or_number([]) is False


@pytest.mark.unit
class TestComplexTypes:
    """复杂类型测试类"""

    def test_nested_type_validation(self):
        """测试嵌套类型验证"""
        def validate_string_list(value):
            if not isinstance(value, list):
                return False
            return all(isinstance(item, str) for item in value)

        # 测试字符串列表
        assert validate_string_list(["a", "b", "c"]) is True
        assert validate_string_list([]) is True
        assert validate_string_list(["a", 123, "c"]) is False
        assert validate_string_list("not a list") is False

    def test_dict_with_specific_types(self):
        """测试特定类型的字典"""
        def validate_string_dict(value):
            if not isinstance(value, dict):
                return False
            return all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())

        # 测试字符串字典
        assert validate_string_dict({"a": "1", "b": "2"}) is True
        assert validate_string_dict({}) is True
        assert validate_string_dict({"a": 1}) is False
        assert validate_string_dict({1: "1"}) is False

    def test_optional_nested_types(self):
        """测试可选嵌套类型"""
        def validate_optional_string_list(value):
            if value is None:
                return True
            if not isinstance(value, list):
                return False
            return all(isinstance(item, str) for item in value)

        # 测试可选字符串列表
        assert validate_optional_string_list(None) is True
        assert validate_optional_string_list(["a", "b"]) is True
        assert validate_optional_string_list([1, 2]) is False


@pytest.mark.parametrize("input_value,expected_type", [
    ("hello", str),
    (123, int),
    (123.45, float),
    (True, bool),
    ([1, 2, 3], list),
    ({"key": "value"}, dict),
])
def test_type_parameterized(input_value, expected_type):
    """参数化类型测试"""
    assert isinstance(input_value, expected_type)


@pytest.mark.parametrize("string_value,should_be_numeric", [
    ("123", True),
    ("123.45", True),
    ("-456", True),
    ("-1.23", True),
    ("0", True),
    ("0.0", True),
    ("abc", False),
    ("12a34", False),
    ("", False),
    (" 123 ", False),  # 包含空格
])
def test_numeric_string_detection(string_value, should_be_numeric):
    """参数化数字字符串检测测试"""
    def is_numeric_string(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    assert is_numeric_string(string_value) == should_be_numeric


@pytest.fixture
def sample_data():
    """示例数据fixture"""
    return {
        "string": "hello",
        "integer": 123,
        "float": 123.45,
        "boolean": True,
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "none": None
    }


def test_with_fixture(sample_data):
    """使用fixture的测试"""
    # 验证各种类型
    assert isinstance(sample_data["string"], str)
    assert isinstance(sample_data["integer"], int)
    assert isinstance(sample_data["float"], float)
    assert isinstance(sample_data["boolean"], bool)
    assert isinstance(sample_data["list"], list)
    assert isinstance(sample_data["dict"], dict)
    assert sample_data["none"] is None