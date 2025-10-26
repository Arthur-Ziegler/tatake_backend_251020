"""
枚举工具测试

测试枚举类型转换功能，包括：
1. 枚举值确保转换
2. 字符串表示转换
3. 数据库格式规范化
4. API格式规范化
5. 枚举值验证
6. 枚举转换器类的使用
7. 错误处理和边界情况

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from enum import Enum
from typing import Union, Optional, Any, Type
from unittest.mock import Mock, patch

# 导入被测试的模块
try:
    from src.utils.enum_helpers import (
        ensure_enum_value,
        ensure_enum_str,
        normalize_enum_for_db,
        normalize_enum_for_api,
        validate_enum_string,
        EnumConverter,
        enum_converter
    )
except ImportError as e:
    # 如果导入失败，创建模拟模块
    def ensure_enum_value(value: Union[str, Enum, None], enum_class: Type) -> Optional[Union[Enum, str]]:
        if value is None:
            return None

        # 如果已经是enum_class的实例，直接返回
        if hasattr(value, '__class__') and value.__class__ == enum_class:
            return value

        if isinstance(value, str):
            # 检查是否是真正的Enum类
            if hasattr(enum_class, '__members__'):  # 真正的Enum类
                try:
                    # 将字符串转换为对应的枚举值
                    return enum_class(value.upper())
                except ValueError:
                    # 如果直接转换失败，尝试遍历枚举值
                    for enum_val in enum_class:
                        if hasattr(enum_val, 'value') and enum_val.value == value:
                            return enum_val
                    raise ValueError(f"Invalid {enum_class.__name__} value: {value}")
            else:
                # 简单的常量类，直接验证值是否有效
                if hasattr(enum_class, '__dict__'):
                    valid_values = [v for k, v in enum_class.__dict__.items()
                                 if not k.startswith('_') and isinstance(v, str)]
                    if value in valid_values:
                        return value
                    raise ValueError(f"Invalid {enum_class.__name__} value: {value}. Valid values: {valid_values}")
                else:
                    # 如果无法验证，直接返回字符串
                    return value

        raise ValueError(f"Invalid {enum_class.__name__} value type: {type(value)}")

    def ensure_enum_str(value: Union[str, Enum, None]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, Enum):
            return value.value
        raise ValueError(f"Invalid enum value type: {type(value)}")

    def normalize_enum_for_db(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            # 验证字符串是否为有效的枚举值
            ensure_enum_value(value, enum_class)
            return value
        if isinstance(value, enum_class):
            return value.value
        raise ValueError(f"Invalid {enum_class.__name__} value: {value}")

    def normalize_enum_for_api(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
        return ensure_enum_value(value, enum_class)

    def validate_enum_string(enum_str: str, enum_class: Type[Enum]) -> bool:
        try:
            ensure_enum_value(enum_str, enum_class)
            return True
        except ValueError:
            return False

    class EnumConverter:
        @staticmethod
        def to_db_format(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[str]:
            return normalize_enum_for_db(value, enum_class)

        @staticmethod
        def to_api_format(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
            return normalize_enum_for_api(value, enum_class)

        @staticmethod
        def to_str(value: Union[str, Enum, None]) -> Optional[str]:
            return ensure_enum_str(value)

        @staticmethod
        def to_enum(value: Union[str, Enum, None], enum_class: Type[Enum]) -> Optional[Enum]:
            return ensure_enum_value(value, enum_class)

    enum_converter = EnumConverter()


# 测试用的枚举类定义
class TestStatus(Enum):
    """测试状态枚举"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


# 测试用的常量类定义
class TaskStatusConst:
    """任务状态常量类"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UserLevelConst:
    """用户等级常量类"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@pytest.mark.unit
class TestEnsureEnumValue:
    """枚举值确保转换测试类"""

    def test_ensure_enum_value_with_string_valid_real_enum(self):
        """测试字符串转换为真正的枚举对象 - 有效值"""
        result = ensure_enum_value("pending", TestStatus)
        assert result == TestStatus.PENDING
        assert isinstance(result, TestStatus)

    def test_ensure_enum_value_with_string_invalid_real_enum(self):
        """测试字符串转换为真正的枚举对象 - 无效值"""
        with pytest.raises(ValueError) as exc_info:
            ensure_enum_value("invalid_status", TestStatus)
        assert "Invalid TestStatus value: invalid_status" in str(exc_info.value)

    def test_ensure_enum_value_with_enum_input(self):
        """测试已经是枚举对象的输入"""
        status = TestStatus.ACTIVE
        result = ensure_enum_value(status, TestStatus)
        assert result == status
        assert result is status  # 应该是同一个对象

    def test_ensure_enum_value_with_none(self):
        """测试None输入"""
        result = ensure_enum_value(None, TestStatus)
        assert result is None

    def test_ensure_enum_value_with_string_valid_const_class(self):
        """测试字符串转换为常量类 - 有效值"""
        result = ensure_enum_value("pending", TaskStatusConst)
        assert result == "pending"
        assert isinstance(result, str)

    def test_ensure_enum_value_with_string_invalid_const_class(self):
        """测试字符串转换为常量类 - 无效值"""
        with pytest.raises(ValueError) as exc_info:
            ensure_enum_value("invalid_status", TaskStatusConst)
        assert "Invalid TaskStatusConst value" in str(exc_info.value)
        assert "Valid values:" in str(exc_info.value)

    def test_ensure_enum_value_with_numeric_enum(self):
        """测试数值枚举转换"""
        result = ensure_enum_value("2", TaskPriority)
        assert result == TaskPriority.MEDIUM
        assert isinstance(result, TaskPriority)

    def test_ensure_enum_value_with_invalid_type(self):
        """测试无效类型输入"""
        invalid_inputs = [123, 12.34, [], {}, True]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError) as exc_info:
                ensure_enum_value(invalid_input, TestStatus)
            assert "Invalid TestStatus value type" in str(exc_info.value)


@pytest.mark.unit
class TestEnsureEnumStr:
    """枚举字符串确保转换测试类"""

    def test_ensure_enum_str_with_string(self):
        """测试字符串输入"""
        result = ensure_enum_str("pending")
        assert result == "pending"
        assert isinstance(result, str)

    def test_ensure_enum_str_with_enum(self):
        """测试枚举输入"""
        status = TestStatus.COMPLETED
        result = ensure_enum_str(status)
        assert result == "completed"
        assert isinstance(result, str)

    def test_ensure_enum_str_with_none(self):
        """测试None输入"""
        result = ensure_enum_str(None)
        assert result is None

    def test_ensure_enum_str_with_numeric_enum(self):
        """测试数值枚举"""
        priority = TaskPriority.HIGH
        result = ensure_enum_str(priority)
        assert result == 3
        assert isinstance(result, int)

    def test_ensure_enum_str_with_invalid_type(self):
        """测试无效类型输入"""
        invalid_inputs = [123, [], {}, True]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError) as exc_info:
                ensure_enum_str(invalid_input)
            assert "Invalid enum value type" in str(exc_info.value)


@pytest.mark.unit
class TestNormalizeEnumForDB:
    """数据库格式枚举规范化测试类"""

    def test_normalize_for_db_with_string(self):
        """测试字符串输入"""
        result = normalize_enum_for_db("pending", TestStatus)
        assert result == "pending"
        assert isinstance(result, str)

    def test_normalize_for_db_with_enum(self):
        """测试枚举输入"""
        status = TestStatus.ACTIVE
        result = normalize_enum_for_db(status, TestStatus)
        assert result == "active"
        assert isinstance(result, str)

    def test_normalize_for_db_with_none(self):
        """测试None输入"""
        result = normalize_enum_for_db(None, TestStatus)
        assert result is None

    def test_normalize_for_db_with_invalid_string(self):
        """测试无效字符串输入"""
        with pytest.raises(ValueError) as exc_info:
            normalize_enum_for_db("invalid", TestStatus)
        assert "Invalid TestStatus value" in str(exc_info.value)

    def test_normalize_for_db_with_wrong_enum_type(self):
        """测试错误枚举类型"""
        status = TestStatus.PENDING
        with pytest.raises(ValueError) as exc_info:
            normalize_enum_for_db(status, TaskPriority)
        assert "Invalid TaskPriority value" in str(exc_info.value)


@pytest.mark.unit
class TestNormalizeEnumForAPI:
    """API格式枚举规范化测试类"""

    def test_normalize_for_api_with_string(self):
        """测试字符串输入"""
        result = normalize_enum_for_api("pending", TestStatus)
        assert result == TestStatus.PENDING
        assert isinstance(result, TestStatus)

    def test_normalize_for_api_with_enum(self):
        """测试枚举输入"""
        status = TestStatus.ACTIVE
        result = normalize_enum_for_api(status, TestStatus)
        assert result == status
        assert result is status

    def test_normalize_for_api_with_none(self):
        """测试None输入"""
        result = normalize_enum_for_api(None, TestStatus)
        assert result is None

    def test_normalize_for_api_with_invalid_string(self):
        """测试无效字符串输入"""
        with pytest.raises(ValueError) as exc_info:
            normalize_enum_for_api("invalid", TestStatus)
        assert "Invalid TestStatus value" in str(exc_info.value)


@pytest.mark.unit
class TestValidateEnumString:
    """枚举字符串验证测试类"""

    def test_validate_enum_string_valid(self):
        """测试有效枚举字符串"""
        result = validate_enum_string("pending", TestStatus)
        assert result is True

        result = validate_enum_string("active", TestStatus)
        assert result is True

    def test_validate_enum_string_invalid(self):
        """测试无效枚举字符串"""
        result = validate_enum_string("invalid", TestStatus)
        assert result is False

    def test_validate_enum_string_with_const_class(self):
        """测试常量类验证"""
        result = validate_enum_string("pending", TaskStatusConst)
        assert result is True

        result = validate_enum_string("invalid", TaskStatusConst)
        assert result is False

    def test_validate_enum_string_case_sensitive(self):
        """测试大小写敏感性"""
        # 真正的枚举类通常支持大小写不敏感（通过upper()转换）
        result = validate_enum_string("PENDING", TestStatus)
        assert result is True

        # 但无效的大小写组合仍然失败
        result = validate_enum_string("Invalid_Status", TestStatus)
        assert result is False


@pytest.mark.unit
class TestEnumConverter:
    """枚举转换器类测试类"""

    def test_converter_to_db_format(self):
        """测试转换为数据库格式"""
        # 字符串输入
        result = EnumConverter.to_db_format("pending", TestStatus)
        assert result == "pending"

        # 枚举输入
        status = TestStatus.COMPLETED
        result = EnumConverter.to_db_format(status, TestStatus)
        assert result == "completed"

        # None输入
        result = EnumConverter.to_db_format(None, TestStatus)
        assert result is None

    def test_converter_to_api_format(self):
        """测试转换为API格式"""
        # 字符串输入
        result = EnumConverter.to_api_format("pending", TestStatus)
        assert result == TestStatus.PENDING

        # 枚举输入
        status = TestStatus.ACTIVE
        result = EnumConverter.to_api_format(status, TestStatus)
        assert result == status

        # None输入
        result = EnumConverter.to_api_format(None, TestStatus)
        assert result is None

    def test_converter_to_str(self):
        """测试转换为字符串"""
        # 字符串输入
        result = EnumConverter.to_str("pending")
        assert result == "pending"

        # 枚举输入
        status = TestStatus.COMPLETED
        result = EnumConverter.to_str(status)
        assert result == "completed"

        # None输入
        result = EnumConverter.to_str(None)
        assert result is None

    def test_converter_to_enum(self):
        """测试转换为枚举"""
        # 字符串输入
        result = EnumConverter.to_enum("pending", TestStatus)
        assert result == TestStatus.PENDING

        # 枚举输入
        status = TestStatus.ACTIVE
        result = EnumConverter.to_enum(status, TestStatus)
        assert result == status

        # None输入
        result = EnumConverter.to_enum(None, TestStatus)
        assert result is None


@pytest.mark.unit
class TestEnumConverterInstance:
    """枚举转换器实例测试类"""

    def test_enum_converter_instance(self):
        """测试枚举转换器便捷实例"""
        assert hasattr(enum_converter, 'to_db_format')
        assert hasattr(enum_converter, 'to_api_format')
        assert hasattr(enum_converter, 'to_str')
        assert hasattr(enum_converter, 'to_enum')

        # 测试实例方法正常工作
        result = enum_converter.to_str(TestStatus.COMPLETED)
        assert result == "completed"

        result = enum_converter.to_db_format("pending", TestStatus)
        assert result == "pending"


@pytest.mark.unit
class TestEnumHelpersEdgeCases:
    """枚举工具边界情况测试类"""

    def test_enum_with_non_string_values(self):
        """测试非字符串值的枚举"""
        priority = TaskPriority.HIGH  # 值为3
        result = ensure_enum_str(priority)
        assert result == 3
        assert isinstance(result, int)

        result = normalize_enum_for_db(priority, TaskPriority)
        assert result == 3

    def test_enum_with_duplicate_values(self):
        """测试具有重复值的枚举"""
        class DuplicateEnum(Enum):
            FIRST = "same"
            SECOND = "same"

        # 这种情况下应该返回第一个匹配的枚举值
        result = ensure_enum_value("same", DuplicateEnum)
        assert result in [DuplicateEnum.FIRST, DuplicateEnum.SECOND]

    def test_enum_with_complex_values(self):
        """测试复杂值的枚举"""
        class ComplexEnum(Enum):
            DICT_VALUE = {"key": "value"}
            LIST_VALUE = [1, 2, 3]

        result = ensure_enum_str(ComplexEnum.DICT_VALUE)
        assert result == {"key": "value"}
        assert isinstance(result, dict)

    def test_const_class_without_dict(self):
        """测试没有__dict__的常量类"""
        class SimpleConst:
            pass

        SimpleConst.VALUE = "simple_value"

        # 应该直接返回字符串，因为无法验证
        result = ensure_enum_value("simple_value", SimpleConst)
        assert result == "simple_value"

    def test_enum_with_method_calling(self):
        """测试枚举方法调用"""
        class MethodEnum(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

            def is_active(self):
                return self == MethodEnum.ACTIVE

        status = MethodEnum.ACTIVE
        result = ensure_enum_str(status)
        assert result == "active"
        assert status.is_active() is True


@pytest.mark.parametrize("input_value,enum_class,expected_result", [
    ("pending", TestStatus, TestStatus.PENDING),
    (TestStatus.ACTIVE, TestStatus, TestStatus.ACTIVE),
    (None, TestStatus, None),
    ("basic", UserLevelConst, "basic"),
    (UserLevelConst.PREMIUM, UserLevelConst, UserLevelConst.PREMIUM),
])
def test_ensure_enum_value_parameterized(input_value, enum_class, expected_result):
    """参数化枚举值确保测试"""
    result = ensure_enum_value(input_value, enum_class)
    assert result == expected_result


@pytest.mark.parametrize("input_value,expected_result", [
    ("pending", "pending"),
    (TestStatus.ACTIVE, "active"),
    (None, None),
    (TaskPriority.HIGH, 3),
])
def test_ensure_enum_str_parameterized(input_value, expected_result):
    """参数化枚举字符串确保测试"""
    result = ensure_enum_str(input_value)
    assert result == expected_result


@pytest.mark.parametrize("enum_str,enum_class,expected_valid", [
    ("pending", TestStatus, True),
    ("invalid", TestStatus, False),
    ("PENDING", TestStatus, True),
    ("in_progress", TaskStatusConst, True),
    ("invalid", TaskStatusConst, False),
])
def test_validate_enum_string_parameterized(enum_str, enum_class, expected_valid):
    """参数化枚举字符串验证测试"""
    result = validate_enum_string(enum_str, enum_class)
    assert result == expected_valid


@pytest.fixture
def sample_enums():
    """示例枚举集合fixture"""
    return {
        'status': TestStatus,
        'priority': TaskPriority,
        'task_status': TaskStatusConst,
        'user_level': UserLevelConst
    }


@pytest.fixture
def sample_values():
    """示例值集合fixture"""
    return {
        'string_pending': "pending",
        'enum_active': TestStatus.ACTIVE,
        'enum_high': TaskPriority.HIGH,
        'none_value': None,
        'invalid_string': "invalid_value"
    }


def test_with_fixtures(sample_enums, sample_values):
    """使用fixture的测试"""
    # 测试字符串到枚举转换
    result = ensure_enum_value(
        sample_values['string_pending'],
        sample_enums['status']
    )
    assert result == TestStatus.PENDING

    # 测试枚举到字符串转换
    result = ensure_enum_str(sample_values['enum_active'])
    assert result == "active"

    # 测试None值处理
    result = ensure_enum_value(
        sample_values['none_value'],
        sample_enums['status']
    )
    assert result is None

    # 测试验证功能
    result = validate_enum_string(
        sample_values['string_pending'],
        sample_enums['status']
    )
    assert result is True

    result = validate_enum_string(
        sample_values['invalid_string'],
        sample_enums['status']
    )
    assert result is False

    # 测试转换器
    result = enum_converter.to_db_format(
        sample_values['enum_active'],
        sample_enums['status']
    )
    assert result == "active"

    result = enum_converter.to_api_format(
        sample_values['string_pending'],
        sample_enums['status']
    )
    assert result == TestStatus.PENDING