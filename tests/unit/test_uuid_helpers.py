"""UUID类型转换工具集单元测试

测试src/utils/uuid_helpers.py中的所有函数，
确保UUID类型处理的正确性和可靠性。

作者：TaKeKe团队
版本：1.4.2
日期：2025-10-25
"""

import pytest
from uuid import uuid4, UUID
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
    UUIDConverter
)


class TestUUIDHelpers:
    """UUID类型转换工具集测试类"""

    def test_ensure_uuid_with_string(self):
        """测试ensure_uuid函数处理字符串输入"""
        test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = ensure_uuid(test_uuid_str)

        assert result is not None
        assert isinstance(result, UUID)
        assert str(result) == test_uuid_str

    def test_ensure_uuid_with_uuid_object(self):
        """测试ensure_uuid函数处理UUID对象输入"""
        test_uuid_obj = uuid4()
        result = ensure_uuid(test_uuid_obj)

        assert result is not None
        assert isinstance(result, UUID)
        assert result == test_uuid_obj

    def test_ensure_uuid_with_none(self):
        """测试ensure_uuid函数处理None输入"""
        result = ensure_uuid(None)

        assert result is None

    def test_ensure_uuid_with_invalid_string(self):
        """测试ensure_uuid函数处理无效字符串"""
        invalid_uuid = "invalid-uuid-string"

        with pytest.raises(ValueError, match="Invalid UUID value"):
            ensure_uuid(invalid_uuid)

    def test_ensure_str_with_string(self):
        """测试ensure_str函数处理字符串输入"""
        test_str = "test-string"
        result = ensure_str(test_str)

        assert result is not None
        assert isinstance(result, str)
        assert result == test_str

    def test_ensure_str_with_uuid_object(self):
        """测试ensure_str函数处理UUID对象输入"""
        test_uuid_obj = uuid4()
        result = ensure_str(test_uuid_obj)

        assert result is not None
        assert isinstance(result, str)
        assert result == str(test_uuid_obj)

    def test_ensure_str_with_none(self):
        """测试ensure_str函数处理None输入"""
        result = ensure_str(None)

        assert result is None

    def test_uuid_list_to_str(self):
        """测试UUID列表转字符串列表"""
        test_uuids = [
            uuid4(),
            "550e8400-e29b-41d4-a716-446655440001",
            None,
            "another-string"
        ]
        result = uuid_list_to_str(test_uuids)

        assert len(result) == 4
        assert result[1] == str(test_uuids[1])  # UUID对象转字符串
        assert result[2] == test_uuids[1]  # 字符串保持不变
        assert result[3] is None  # None被过滤

    def test_str_list_to_uuid(self):
        """测试字符串列表转UUID列表"""
        test_strings = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "another-string",
            None
        ]
        result = str_list_to_uuid(test_strings)

        assert len(result) == 3  # None被过滤
        assert isinstance(result[0], UUID)
        assert isinstance(result[1], UUID)
        assert str(result[0]) == test_strings[0]

    def test_safe_uuid_str(self):
        """测试safe_uuid_str函数"""
        test_uuid = uuid4()
        result = safe_uuid_str(test_uuid)

        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_normalize_uuid_for_db(self):
        """测试数据库格式规范化"""
        test_uuid_obj = uuid4()
        test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        # 测试UUID对象输入
        result_obj = normalize_uuid_for_db(test_uuid_obj)
        assert result_obj == str(test_uuid_obj)

        # 测试字符串输入
        result_str = normalize_uuid_for_db(test_uuid_str)
        assert result_str == test_uuid_str

        # 测试None输入
        result_none = normalize_uuid_for_db(None)
        assert result_none is None

    def test_normalize_uuid_for_api(self):
        """测试API格式规范化"""
        test_uuid_obj = uuid4()
        test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        # 测试UUID对象输入
        result_obj = normalize_uuid_for_api(test_uuid_obj)
        assert result_obj == test_uuid_obj

        # 测试字符串输入
        result_str = normalize_uuid_for_api(test_uuid_str)
        assert result_str == test_uuid_obj  # 字符串转UUID对象

        # 测试None输入
        result_none = normalize_uuid_for_api(None)
        assert result_none is None

    def test_validate_uuid_string(self):
        """测试UUID字符串验证"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        invalid_uuid = "invalid-uuid"

        # 测试有效UUID
        assert validate_uuid_string(valid_uuid) is True

        # 测试无效UUID
        assert validate_uuid_string(invalid_uuid) is False

    def test_extract_uuid_from_mixed(self):
        """测试从混合类型中提取UUID"""
        test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        test_uuid_obj = uuid4()

        # 测试从字符串提取
        result_str = extract_uuid_from_mixed(test_uuid_str)
        assert result_str == test_uuid_obj

        # 测试从UUID对象提取
        result_obj = extract_uuid_from_mixed(test_uuid_obj)
        assert result_obj == test_uuid_obj

        # 测试从字典提取
        result_dict = extract_uuid_from_mixed({
            "user_id": test_uuid_str
        })
        assert result_dict == test_uuid_obj

        # 测试从嵌套字典提取
        result_nested = extract_uuid_from_mixed({
            "data": {"id": test_uuid_str}
        })
        assert result_nested == test_uuid_obj

        # 测试None输入
        result_none = extract_uuid_from_mixed(None)
        assert result_none is None

    def test_uuid_converter_class(self):
        """测试UUIDConverter类"""
        converter = UUIDConverter()

        test_uuid_obj = uuid4()
        test_uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        # 测试各种转换方法
        assert converter.to_db_format(test_uuid_obj) == str(test_uuid_obj)
        assert converter.to_db_format(test_uuid_str) == test_uuid_str
        assert converter.to_api_format(test_uuid_obj) == test_uuid_obj
        assert converter.to_api_format(test_uuid_str) == test_uuid_obj
        assert converter.to_str(test_uuid_obj) == str(test_uuid_obj)
        assert converter.to_str(test_uuid_str) == test_uuid_str
        assert converter.to_uuid(test_uuid_obj) == test_uuid_obj
        assert converter.to_uuid(test_uuid_str) == test_uuid_obj
        assert converter.to_db_format(None) is None
        assert converter.to_api_format(None) is None
        assert converter.to_str(None) is None
        assert converter.to_uuid(None) is None

    def test_error_handling(self):
        """测试错误处理"""
        # 测试非字符串/UUID的输入
        with pytest.raises(ValueError):
            ensure_uuid(123)  # 数字

        with pytest.raises(ValueError):
            ensure_uuid([])    # 列表

        with pytest.raises(ValueError):
            ensure_uuid({})    # 字典