"""
UUID转换器测试

测试基础的UUID功能，包括：
1. UUID创建和验证
2. UUID格式转换
3. UUID字符串解析

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from uuid import UUID, uuid4, uuid1
from typing import Any, Optional


@pytest.mark.unit
class TestUUIDBasics:
    """UUID基础功能测试类"""

    def test_uuid_creation(self):
        """测试UUID创建"""
        test_uuid = uuid4()

        assert isinstance(test_uuid, UUID)
        assert test_uuid.version == 4
        assert len(str(test_uuid)) == 36
        assert str(test_uuid).count('-') == 4

    def test_uuid_from_string(self):
        """测试从字符串创建UUID"""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        test_uuid = UUID(uuid_str)

        assert isinstance(test_uuid, UUID)
        assert str(test_uuid) == uuid_str

    def test_uuid_to_string(self):
        """测试UUID转字符串"""
        test_uuid = uuid4()
        uuid_str = str(test_uuid)

        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36
        assert uuid_str.count('-') == 4

    def test_uuid_validation(self):
        """测试UUID验证"""
        valid_uuid = uuid4()
        invalid_values = [
            "not-a-uuid",
            "12345678-1234-5678-1234-56781234567",  # 缺少一位
            "g2345678-1234-5678-1234-567812345678",  # 无效字符
            123,  # 数字
            None
        ]

        # 验证有效UUID
        assert isinstance(valid_uuid, UUID)

        # 验证无效值
        for invalid_value in invalid_values:
            if isinstance(invalid_value, str):
                try:
                    UUID(invalid_value)
                    assert False, f"Should have failed for {invalid_value}"
                except ValueError:
                    pass  # 期望的行为

    def test_uuid_version_check(self):
        """测试UUID版本检查"""
        uuid_v1 = uuid1()
        uuid_v4 = uuid4()

        assert uuid_v1.version == 1
        assert uuid_v4.version == 4

    def test_uuid_equality(self):
        """测试UUID相等性"""
        uuid1 = uuid4()
        uuid2 = uuid4()
        uuid1_copy = UUID(str(uuid1))

        assert uuid1 == uuid1_copy
        assert uuid1 != uuid2
        assert hash(uuid1) == hash(uuid1_copy)

    def test_uuid_bytes_conversion(self):
        """测试UUID字节转换"""
        test_uuid = uuid4()
        uuid_bytes = test_uuid.bytes

        assert isinstance(uuid_bytes, bytes)
        assert len(uuid_bytes) == 16

        # 测试从字节创建UUID
        uuid_from_bytes = UUID(bytes=uuid_bytes)
        assert uuid_from_bytes == test_uuid

    def test_uuid_int_conversion(self):
        """测试UUID整数转换"""
        test_uuid = uuid4()
        uuid_int = int(test_uuid)

        assert isinstance(uuid_int, int)
        assert 0 <= uuid_int < 2**128

        # 测试从整数创建UUID
        uuid_from_int = UUID(int=uuid_int)
        assert uuid_from_int == test_uuid


@pytest.mark.unit
class TestUUIDFormatting:
    """UUID格式测试类"""

    def test_standard_format(self):
        """测试标准格式"""
        test_uuid = uuid4()
        standard_str = str(test_uuid)

        # 验证标准格式 (8-4-4-4-12)
        parts = standard_str.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_compact_format(self):
        """测试紧凑格式（无连字符）"""
        test_uuid = uuid4()
        standard_str = str(test_uuid)
        compact_str = standard_str.replace('-', '')

        assert len(compact_str) == 32
        assert '-' not in compact_str

        # 验证可以转换回来
        reconstructed = f"{compact_str[0:8]}-{compact_str[8:12]}-{compact_str[12:16]}-{compact_str[16:20]}-{compact_str[20:32]}"
        assert UUID(reconstructed) == test_uuid

    def test_uppercase_format(self):
        """测试大写格式"""
        test_uuid = uuid4()
        uppercase_str = str(test_uuid).upper()

        assert uppercase_str == uppercase_str.upper()
        assert UUID(uppercase_str) == test_uuid

    def test_lowercase_format(self):
        """测试小写格式"""
        test_uuid = uuid4()
        lowercase_str = str(test_uuid).lower()

        assert lowercase_str == lowercase_str.lower()
        assert UUID(lowercase_str) == test_uuid

    def test_format_with_braces(self):
        """测试带大括号的格式"""
        test_uuid = uuid4()
        uuid_str = str(test_uuid)
        with_braces = f"{{{uuid_str}}}"

        # 验证可以解析带大括号的UUID（如果去除大括号）
        clean_uuid = with_braces.strip('{}')
        assert UUID(clean_uuid) == test_uuid

    def test_format_with_urn(self):
        """测试带URN前缀的格式"""
        test_uuid = uuid4()
        uuid_str = str(test_uuid)
        urn_format = f"urn:uuid:{uuid_str}"

        # 验证可以解析URN格式（如果去除前缀）
        clean_uuid = urn_format.replace("urn:uuid:", "")
        assert UUID(clean_uuid) == test_uuid


@pytest.mark.unit
class TestUUIDValidation:
    """UUID验证测试类"""

    def test_valid_uuid_strings(self):
        """测试有效UUID字符串"""
        valid_uuids = [
            "12345678-1234-5678-1234-567812345678",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]

        for uuid_str in valid_uuids:
            uuid_obj = UUID(uuid_str)
            assert isinstance(uuid_obj, UUID)
            assert str(uuid_obj) == uuid_str.lower()

    def test_invalid_uuid_strings(self):
        """测试无效UUID字符串"""
        invalid_uuids = [
            "12345678-1234-5678-1234-56781234567",  # 缺少一位
            "12345678-1234-5678-1234-5678123456789",  # 多一位
            "g2345678-1234-5678-1234-567812345678",  # 无效字符
            "12345678-1234-5678-1234-56781234567",   # 格式错误
            "12345678123456781234567812345678",       # 无连字符但位数正确
            "not-a-uuid",                               # 完全无效
            "",                                        # 空字符串
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError):
                UUID(invalid_uuid)

    def test_case_insensitive_parsing(self):
        """测试大小写不敏感解析"""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        uppercase = uuid_str.upper()
        lowercase = uuid_str.lower()
        mixed_case = "12345678-1234-5678-1234-567812345678".upper()

        uuid_from_lower = UUID(lowercase)
        uuid_from_upper = UUID(uppercase)
        uuid_from_mixed = UUID(mixed_case)

        assert uuid_from_lower == uuid_from_upper == uuid_from_mixed


@pytest.mark.unit
class TestUUIDComparison:
    """UUID比较测试类"""

    def test_uuid_comparison(self):
        """测试UUID比较"""
        uuid1 = uuid4()
        uuid2 = uuid4()

        # 相同UUID比较
        uuid1_copy = UUID(str(uuid1))
        assert uuid1 == uuid1_copy
        assert not (uuid1 != uuid1_copy)

        # 不同UUID比较
        assert uuid1 != uuid2
        assert not (uuid1 == uuid2)

    def test_uuid_sorting(self):
        """测试UUID排序"""
        uuids = [uuid4() for _ in range(10)]
        sorted_uuids = sorted(uuids)

        # 验证排序结果
        assert len(sorted_uuids) == len(uuids)
        assert all(sorted_uuids[i] <= sorted_uuids[i+1] for i in range(len(sorted_uuids)-1))

    def test_string_uuid_comparison(self):
        """测试字符串UUID比较"""
        test_uuid = uuid4()
        uuid_str = str(test_uuid)

        assert uuid_str == str(test_uuid)
        assert UUID(uuid_str) == test_uuid


@pytest.mark.parametrize("uuid_input,should_be_valid", [
    ("12345678-1234-5678-1234-567812345678", True),
    ("12345678123456781234567812345678", True),  # 无连字符
    ("12345678-1234-5678-1234-56781234567", False),  # 缺少字符
    ("g2345678-1234-5678-1234-567812345678", False),  # 无效字符
    ("not-a-uuid", False),  # 完全无效
    ("", False),  # 空字符串
])
def test_uuid_validation_parameterized(uuid_input, should_be_valid):
    """参数化UUID验证测试"""
    if should_be_valid:
        try:
            if '-' in uuid_input:
                uuid_obj = UUID(uuid_input)
            else:
                # 无连字符格式需要特殊处理
                formatted = f"{uuid_input[0:8]}-{uuid_input[8:12]}-{uuid_input[12:16]}-{uuid_input[16:20]}-{uuid_input[20:32]}"
                uuid_obj = UUID(formatted)
            assert isinstance(uuid_obj, UUID)
        except ValueError:
            pytest.fail(f"Expected valid UUID for {uuid_input}")
    else:
        with pytest.raises(ValueError):
            UUID(uuid_input)


@pytest.fixture
def sample_uuids():
    """示例UUID集合fixture"""
    return [
        uuid4(),
        uuid1(),
        UUID("12345678-1234-5678-1234-567812345678"),
        UUID("00000000-0000-0000-0000-000000000000"),
    ]


def test_with_fixture(sample_uuids):
    """使用fixture的测试"""
    for test_uuid in sample_uuids:
        # 测试各种转换
        string_repr = str(test_uuid)
        bytes_repr = test_uuid.bytes
        int_repr = int(test_uuid)

        # 验证转换结果
        assert isinstance(string_repr, str)
        assert isinstance(bytes_repr, bytes) and len(bytes_repr) == 16
        assert isinstance(int_repr, int) and 0 <= int_repr < 2**128

        # 验证往返转换
        assert UUID(string_repr) == test_uuid
        assert UUID(bytes=bytes_repr) == test_uuid
        assert UUID(int=int_repr) == test_uuid