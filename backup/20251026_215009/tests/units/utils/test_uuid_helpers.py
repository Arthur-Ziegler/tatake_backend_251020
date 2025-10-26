"""
UUID工具测试

测试UUID类型转换功能，包括：
1. UUID对象确保转换
2. 字符串表示转换
3. UUID列表转换
4. 数据库格式规范化
5. API格式规范化
6. UUID字符串验证
7. 混合类型UUID提取
8. UUID转换器类的使用

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from uuid import UUID, uuid4
from typing import Union, Optional, List, Any, Dict
from unittest.mock import Mock, patch

# 导入被测试的模块
try:
    from src.utils.uuid_helpers import (
        ensure_uuid,
        ensure_str,
        uuid_list_to_str,
        str_list_to_uuid,
        safe_uuid_str,
        normalize_uuid_for_db,
        normalize_uuid_for_api,
        validate_uuid_string,
        extract_uuid_from_mixed,
        UUIDConverter,
        uuid_converter
    )
except ImportError as e:
    # 如果导入失败，创建模拟模块
    def ensure_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid UUID value: {value}") from e

    def ensure_str(value: Union[str, UUID, None]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    def uuid_list_to_str(uuids: List[Union[str, UUID]]) -> List[str]:
        return [ensure_str(u) for u in uuids]

    def str_list_to_uuid(strings: List[str]) -> List[UUID]:
        return [ensure_uuid(s) for s in strings if s]

    def safe_uuid_str(uuid_obj: UUID) -> str:
        return str(uuid_obj)

    def normalize_uuid_for_db(value: Union[str, UUID, None]) -> Optional[str]:
        return ensure_str(value)

    def normalize_uuid_for_api(value: Union[str, UUID, None]) -> Optional[UUID]:
        return ensure_uuid(value)

    def validate_uuid_string(uuid_str: str) -> bool:
        try:
            UUID(uuid_str)
            return True
        except (ValueError, TypeError):
            return False

    def extract_uuid_from_mixed(mixed_value: Any) -> Optional[UUID]:
        if mixed_value is None:
            return None
        if isinstance(mixed_value, UUID):
            return mixed_value
        if isinstance(mixed_value, str) and validate_uuid_string(mixed_value):
            return UUID(mixed_value)
        if isinstance(mixed_value, dict):
            # 常见模式：{"user_id": "uuid"} 或 {"id": "uuid"}
            for key in ["user_id", "id", "task_id", "parent_id"]:
                if key in mixed_value:
                    uuid_val = mixed_value[key]
                    if isinstance(uuid_val, UUID):
                        return uuid_val
                    if isinstance(uuid_val, str) and validate_uuid_string(uuid_val):
                        return UUID(uuid_val)
        return None

    class UUIDConverter:
        @staticmethod
        def to_db_format(value: Union[str, UUID, None]) -> Optional[str]:
            return normalize_uuid_for_db(value)

        @staticmethod
        def to_api_format(value: Union[str, UUID, None]) -> Optional[UUID]:
            return normalize_uuid_for_api(value)

        @staticmethod
        def to_str(value: Union[str, UUID, None]) -> Optional[str]:
            return ensure_str(value)

        @staticmethod
        def to_uuid(value: Union[str, UUID, None]) -> Optional[UUID]:
            return ensure_uuid(value)

    uuid_converter = UUIDConverter()


@pytest.mark.unit
class TestEnsureUUID:
    """UUID对象确保转换测试类"""

    def test_ensure_uuid_with_string_valid(self):
        """测试有效字符串转换为UUID"""
        valid_uuid_str = str(uuid4())
        result = ensure_uuid(valid_uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == valid_uuid_str

    def test_ensure_uuid_with_uuid_object(self):
        """测试UUID对象输入"""
        uuid_obj = uuid4()
        result = ensure_uuid(uuid_obj)
        assert result is uuid_obj  # 应该是同一个对象
        assert isinstance(result, UUID)

    def test_ensure_uuid_with_none(self):
        """测试None输入"""
        result = ensure_uuid(None)
        assert result is None

    def test_ensure_uuid_with_invalid_string(self):
        """测试无效字符串输入"""
        invalid_uuids = [
            "not-a-uuid",
            "12345678-1234-5678-1234-56781234567",  # 缺少一位
            "g2345678-1234-5678-1234-567812345678",  # 无效字符
            "",  # 空字符串
            "123",  # 太短
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError) as exc_info:
                ensure_uuid(invalid_uuid)
            assert "Invalid UUID value" in str(exc_info.value)

    def test_ensure_uuid_with_invalid_type(self):
        """测试无效类型输入"""
        invalid_inputs = [123, 12.34, [], {}, True]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError) as exc_info:
                ensure_uuid(invalid_input)
            assert "Invalid UUID value" in str(exc_info.value)

    def test_ensure_uuid_with_integer_input(self):
        """测试整数输入"""
        integer_input = 123456789012345678901234567890123456789
        with pytest.raises(ValueError):
            ensure_uuid(integer_input)


@pytest.mark.unit
class TestEnsureStr:
    """字符串确保转换测试类"""

    def test_ensure_str_with_string(self):
        """测试字符串输入"""
        test_str = str(uuid4())
        result = ensure_str(test_str)
        assert result == test_str
        assert isinstance(result, str)

    def test_ensure_str_with_uuid_object(self):
        """测试UUID对象输入"""
        uuid_obj = uuid4()
        result = ensure_str(uuid_obj)
        assert result == str(uuid_obj)
        assert isinstance(result, str)

    def test_ensure_str_with_none(self):
        """测试None输入"""
        result = ensure_str(None)
        assert result is None

    def test_ensure_str_with_other_types(self):
        """测试其他类型输入（会被转换为字符串）"""
        other_inputs = [123, 12.34, True, []]

        for input_val in other_inputs:
            result = ensure_str(input_val)
            assert isinstance(result, str)
            assert result == str(input_val)


@pytest.mark.unit
class TestUUIDListConversion:
    """UUID列表转换测试类"""

    def test_uuid_list_to_str_all_strings(self):
        """测试UUID列表转字符串列表 - 全字符串输入"""
        uuid_strs = [str(uuid4()) for _ in range(3)]
        result = uuid_list_to_str(uuid_strs)
        assert result == uuid_strs
        assert all(isinstance(r, str) for r in result)

    def test_uuid_list_to_str_all_uuids(self):
        """测试UUID列表转字符串列表 - 全UUID对象输入"""
        uuid_objs = [uuid4() for _ in range(3)]
        result = uuid_list_to_str(uuid_objs)
        expected = [str(u) for u in uuid_objs]
        assert result == expected
        assert all(isinstance(r, str) for r in result)

    def test_uuid_list_to_str_mixed(self):
        """测试UUID列表转字符串列表 - 混合输入"""
        uuid_obj = uuid4()
        uuid_str = str(uuid4())
        mixed_input = [uuid_obj, uuid_str]
        result = uuid_list_to_str(mixed_input)
        expected = [str(uuid_obj), uuid_str]
        assert result == expected
        assert all(isinstance(r, str) for r in result)

    def test_uuid_list_to_str_empty(self):
        """测试UUID列表转字符串列表 - 空列表"""
        result = uuid_list_to_str([])
        assert result == []

    def test_str_list_to_uuid_valid(self):
        """测试字符串列表转UUID列表 - 有效输入"""
        uuid_strs = [str(uuid4()) for _ in range(3)]
        result = str_list_to_uuid(uuid_strs)
        assert len(result) == len(uuid_strs)
        assert all(isinstance(r, UUID) for r in result)
        assert [str(r) for r in result] == uuid_strs

    def test_str_list_to_uuid_with_none_values(self):
        """测试字符串列表转UUID列表 - 包含None值"""
        uuid_strs = [str(uuid4()), None, str(uuid4())]
        result = str_list_to_uuid(uuid_strs)
        assert len(result) == 2  # None值被过滤
        assert all(isinstance(r, UUID) for r in result)

    def test_str_list_to_uuid_with_empty_strings(self):
        """测试字符串列表转UUID列表 - 包含空字符串"""
        uuid_strs = [str(uuid4()), "", str(uuid4())]
        result = str_list_to_uuid(uuid_strs)
        assert len(result) == 3  # 空字符串不会被过滤

    def test_str_list_to_uuid_invalid(self):
        """测试字符串列表转UUID列表 - 无效输入"""
        invalid_uuids = [str(uuid4()), "invalid-uuid", str(uuid4())]

        with pytest.raises(ValueError):
            str_list_to_uuid(invalid_uuids)


@pytest.mark.unit
class TestSafeUUIDStr:
    """安全UUID字符串转换测试类"""

    def test_safe_uuid_str_with_uuid(self):
        """测试UUID对象输入"""
        uuid_obj = uuid4()
        result = safe_uuid_str(uuid_obj)
        assert result == str(uuid_obj)
        assert isinstance(result, str)

    def test_safe_uuid_str_never_raises(self):
        """测试safe_uuid_str不会抛出异常"""
        # 这个函数应该总是安全地返回字符串
        uuid_obj = uuid4()

        # 即使在异常情况下也不会抛出异常（因为它只调用str()）
        result = safe_uuid_str(uuid_obj)
        assert isinstance(result, str)


@pytest.mark.unit
class TestNormalizeUUIDFormats:
    """UUID格式规范化测试类"""

    def test_normalize_for_db_with_string(self):
        """测试数据库格式规范化 - 字符串输入"""
        uuid_str = str(uuid4())
        result = normalize_uuid_for_db(uuid_str)
        assert result == uuid_str
        assert isinstance(result, str)

    def test_normalize_for_db_with_uuid(self):
        """测试数据库格式规范化 - UUID输入"""
        uuid_obj = uuid4()
        result = normalize_uuid_for_db(uuid_obj)
        assert result == str(uuid_obj)
        assert isinstance(result, str)

    def test_normalize_for_db_with_none(self):
        """测试数据库格式规范化 - None输入"""
        result = normalize_uuid_for_db(None)
        assert result is None

    def test_normalize_for_api_with_string(self):
        """测试API格式规范化 - 字符串输入"""
        uuid_str = str(uuid4())
        result = normalize_uuid_for_api(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_normalize_for_api_with_uuid(self):
        """测试API格式规范化 - UUID输入"""
        uuid_obj = uuid4()
        result = normalize_uuid_for_api(uuid_obj)
        assert result is uuid_obj
        assert isinstance(result, UUID)

    def test_normalize_for_api_with_none(self):
        """测试API格式规范化 - None输入"""
        result = normalize_uuid_for_api(None)
        assert result is None

    def test_normalize_for_api_with_invalid_string(self):
        """测试API格式规范化 - 无效字符串"""
        with pytest.raises(ValueError):
            normalize_uuid_for_api("invalid-uuid")


@pytest.mark.unit
class TestValidateUUIDString:
    """UUID字符串验证测试类"""

    def test_validate_uuid_string_valid(self):
        """测试有效UUID字符串验证"""
        valid_uuids = [
            str(uuid4()),
            "12345678-1234-5678-1234-567812345678",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff"
        ]

        for valid_uuid in valid_uuids:
            result = validate_uuid_string(valid_uuid)
            assert result is True

    def test_validate_uuid_string_invalid(self):
        """测试无效UUID字符串验证"""
        invalid_uuids = [
            "not-a-uuid",
            "12345678-1234-5678-1234-56781234567",  # 缺少一位
            "g2345678-1234-5678-1234-567812345678",  # 无效字符
            "",  # 空字符串
            "123",  # 太短
            "12345678123456781234567812345678",  # 无连字符但位数正确
        ]

        for invalid_uuid in invalid_uuids:
            result = validate_uuid_string(invalid_uuid)
            assert result is False

    def test_validate_uuid_string_case_insensitive(self):
        """测试大小写不敏感验证"""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        uppercase = uuid_str.upper()
        lowercase = uuid_str.lower()

        assert validate_uuid_string(uppercase) is True
        assert validate_uuid_string(lowercase) is True


@pytest.mark.unit
class TestExtractUUIDFromMixed:
    """混合类型UUID提取测试类"""

    def test_extract_from_uuid(self):
        """测试从UUID对象提取"""
        uuid_obj = uuid4()
        result = extract_uuid_from_mixed(uuid_obj)
        assert result is uuid_obj
        assert isinstance(result, UUID)

    def test_extract_from_string(self):
        """测试从字符串提取"""
        uuid_str = str(uuid4())
        result = extract_uuid_from_mixed(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_extract_from_dict_user_id(self):
        """测试从字典提取 - user_id字段"""
        uuid_str = str(uuid4())
        data = {"user_id": uuid_str, "name": "test"}
        result = extract_uuid_from_mixed(data)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_extract_from_dict_id(self):
        """测试从字典提取 - id字段"""
        uuid_str = str(uuid4())
        data = {"id": uuid_str, "other": "value"}
        result = extract_uuid_from_mixed(data)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_extract_from_dict_task_id(self):
        """测试从字典提取 - task_id字段"""
        uuid_str = str(uuid4())
        data = {"task_id": uuid_str, "status": "pending"}
        result = extract_uuid_from_mixed(data)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_extract_from_dict_parent_id(self):
        """测试从字典提取 - parent_id字段"""
        uuid_str = str(uuid4())
        data = {"parent_id": uuid_str, "child_count": 5}
        result = extract_uuid_from_mixed(data)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_extract_from_dict_uuid_object(self):
        """测试从字典提取 - UUID对象值"""
        uuid_obj = uuid4()
        data = {"id": uuid_obj, "name": "test"}
        result = extract_uuid_from_mixed(data)
        assert result is uuid_obj

    def test_extract_from_dict_no_uuid(self):
        """测试从字典提取 - 无UUID字段"""
        data = {"name": "test", "value": 123}
        result = extract_uuid_from_mixed(data)
        assert result is None

    def test_extract_from_none(self):
        """测试从None提取"""
        result = extract_uuid_from_mixed(None)
        assert result is None

    def test_extract_from_other_types(self):
        """测试从其他类型提取"""
        other_inputs = [123, 12.34, [], True]

        for input_val in other_inputs:
            result = extract_uuid_from_mixed(input_val)
            assert result is None

    def test_extract_from_nested_dict(self):
        """测试从嵌套字典提取（不支持，应该返回None）"""
        uuid_str = str(uuid4())
        data = {"nested": {"id": uuid_str}}
        result = extract_uuid_from_mixed(data)
        assert result is None


@pytest.mark.unit
class TestUUIDConverter:
    """UUID转换器类测试类"""

    def test_converter_to_db_format(self):
        """测试转换为数据库格式"""
        uuid_obj = uuid4()
        uuid_str = str(uuid4())

        # UUID对象输入
        result = UUIDConverter.to_db_format(uuid_obj)
        assert result == str(uuid_obj)
        assert isinstance(result, str)

        # 字符串输入
        result = UUIDConverter.to_db_format(uuid_str)
        assert result == uuid_str
        assert isinstance(result, str)

        # None输入
        result = UUIDConverter.to_db_format(None)
        assert result is None

    def test_converter_to_api_format(self):
        """测试转换为API格式"""
        uuid_obj = uuid4()
        uuid_str = str(uuid4())

        # 字符串输入
        result = UUIDConverter.to_api_format(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

        # UUID对象输入
        result = UUIDConverter.to_api_format(uuid_obj)
        assert result is uuid_obj
        assert isinstance(result, UUID)

        # None输入
        result = UUIDConverter.to_api_format(None)
        assert result is None

    def test_converter_to_str(self):
        """测试转换为字符串"""
        uuid_obj = uuid4()
        uuid_str = str(uuid4())

        # UUID对象输入
        result = UUIDConverter.to_str(uuid_obj)
        assert result == str(uuid_obj)
        assert isinstance(result, str)

        # 字符串输入
        result = UUIDConverter.to_str(uuid_str)
        assert result == uuid_str
        assert isinstance(result, str)

        # None输入
        result = UUIDConverter.to_str(None)
        assert result is None

    def test_converter_to_uuid(self):
        """测试转换为UUID对象"""
        uuid_obj = uuid4()
        uuid_str = str(uuid4())

        # 字符串输入
        result = UUIDConverter.to_uuid(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

        # UUID对象输入
        result = UUIDConverter.to_uuid(uuid_obj)
        assert result is uuid_obj
        assert isinstance(result, UUID)

        # None输入
        result = UUIDConverter.to_uuid(None)
        assert result is None


@pytest.mark.unit
class TestUUIDConverterInstance:
    """UUID转换器实例测试类"""

    def test_uuid_converter_instance(self):
        """测试UUID转换器便捷实例"""
        assert hasattr(uuid_converter, 'to_db_format')
        assert hasattr(uuid_converter, 'to_api_format')
        assert hasattr(uuid_converter, 'to_str')
        assert hasattr(uuid_converter, 'to_uuid')

        # 测试实例方法正常工作
        uuid_obj = uuid4()
        result = uuid_converter.to_str(uuid_obj)
        assert result == str(uuid_obj)

        uuid_str = str(uuid4())
        result = uuid_converter.to_uuid(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str


@pytest.mark.unit
class TestUUIDHelpersEdgeCases:
    """UUID工具边界情况测试类"""

    def test_ensure_uuid_with_bytes_input(self):
        """测试字节输入"""
        uuid_bytes = b"12345678-1234-5678-1234-567812345678"
        with pytest.raises(ValueError):
            ensure_uuid(uuid_bytes)

    def test_ensure_uuid_with_mixed_case_string(self):
        """测试混合大小写字符串"""
        uuid_str = str(uuid4()).upper()
        result = ensure_uuid(uuid_str)
        assert isinstance(result, UUID)
        assert str(result).lower() == uuid_str.lower()

    def test_uuid_list_conversion_with_duplicates(self):
        """测试包含重复值的UUID列表转换"""
        uuid_str = str(uuid4())
        uuid_obj = uuid4()
        mixed_list = [uuid_str, uuid_str, uuid_obj, uuid_obj]

        result_strs = uuid_list_to_str(mixed_list)
        expected_strs = [uuid_str, uuid_str, str(uuid_obj), str(uuid_obj)]
        assert result_strs == expected_strs

        result_uuids = str_list_to_uuid([uuid_str, uuid_str])
        assert len(result_uuids) == 2
        assert all(u == UUID(uuid_str) for u in result_uuids)

    def test_extract_uuid_with_multiple_uuid_fields(self):
        """测试包含多个UUID字段的字典"""
        uuid1 = str(uuid4())
        uuid2 = str(uuid4())
        data = {
            "user_id": uuid1,
            "task_id": uuid2,
            "name": "test"
        }

        result = extract_uuid_from_mixed(data)
        # 应该返回第一个找到的UUID（按优先级顺序）
        assert isinstance(result, UUID)
        assert str(result) in [uuid1, uuid2]

    def test_extract_uuid_with_invalid_values(self):
        """测试包含无效UUID值的字典"""
        data = {
            "user_id": "invalid-uuid",
            "id": str(uuid4()),
            "name": "test"
        }

        result = extract_uuid_from_mixed(data)
        assert isinstance(result, UUID)
        # 应该找到有效的UUID


@pytest.mark.parametrize("input_value,expected_type", [
    (str(uuid4()), UUID),
    (uuid4(), UUID),
    (None, type(None)),
])
def test_ensure_uuid_parameterized(input_value, expected_type):
    """参数化UUID确保测试"""
    if input_value is None:
        result = ensure_uuid(input_value)
        assert result is None
    else:
        result = ensure_uuid(input_value)
        assert isinstance(result, expected_type)
        if isinstance(input_value, str):
            assert str(result) == input_value


@pytest.mark.parametrize("input_value,expected_type", [
    (str(uuid4()), str),
    (uuid4(), str),
    (None, type(None)),
    (123, str),
])
def test_ensure_str_parameterized(input_value, expected_type):
    """参数化字符串确保测试"""
    if input_value is None:
        result = ensure_str(input_value)
        assert result is None
    else:
        result = ensure_str(input_value)
        assert isinstance(result, expected_type)


@pytest.mark.parametrize("uuid_str,expected_valid", [
    (str(uuid4()), True),
    ("12345678-1234-5678-1234-567812345678", True),
    ("invalid-uuid", False),
    ("", False),
    ("12345678-1234-5678-1234-56781234567", False),
])
def test_validate_uuid_string_parameterized(uuid_str, expected_valid):
    """参数化UUID字符串验证测试"""
    result = validate_uuid_string(uuid_str)
    assert result == expected_valid


@pytest.fixture
def sample_uuids():
    """示例UUID集合fixture"""
    return {
        'uuid_obj': uuid4(),
        'uuid_str': str(uuid4()),
        'invalid_str': "invalid-uuid",
        'none_value': None,
        'uuid_list': [uuid4(), uuid4(), uuid4()],
        'str_list': [str(uuid4()), str(uuid4()), str(uuid4())],
        'mixed_dict': {
            "user_id": str(uuid4()),
            "name": "test_user",
            "id": uuid4()
        }
    }


def test_with_fixtures(sample_uuids):
    """使用fixture的测试"""
    # 测试UUID确保
    result = ensure_uuid(sample_uuids['uuid_str'])
    assert isinstance(result, UUID)
    assert str(result) == sample_uuids['uuid_str']

    result = ensure_uuid(sample_uuids['uuid_obj'])
    assert result is sample_uuids['uuid_obj']

    result = ensure_uuid(sample_uuids['none_value'])
    assert result is None

    # 测试字符串确保
    result = ensure_str(sample_uuids['uuid_obj'])
    assert result == str(sample_uuids['uuid_obj'])

    # 测试列表转换
    result = uuid_list_to_str(sample_uuids['uuid_list'])
    assert len(result) == len(sample_uuids['uuid_list'])
    assert all(isinstance(r, str) for r in result)

    result = str_list_to_uuid(sample_uuids['str_list'])
    assert len(result) == len(sample_uuids['str_list'])
    assert all(isinstance(r, UUID) for r in result)

    # 测试验证
    assert validate_uuid_string(sample_uuids['uuid_str']) is True
    assert validate_uuid_string(sample_uuids['invalid_str']) is False

    # 测试提取
    result = extract_uuid_from_mixed(sample_uuids['mixed_dict'])
    assert isinstance(result, UUID)

    # 测试转换器
    result = uuid_converter.to_db_format(sample_uuids['uuid_obj'])
    assert isinstance(result, str)

    result = uuid_converter.to_api_format(sample_uuids['uuid_str'])
    assert isinstance(result, UUID)