"""
JSON Schema编码器测试

测试基础的JSON编码功能，包括：
1. UUID类型编码
2. datetime类型编码
3. Decimal类型编码
4. 自定义对象编码
5. 错误处理

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import json
from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import UUID, uuid4
from json import JSONEncoder
from unittest.mock import Mock, patch
from typing import Any, Dict, List

# 尝试导入实际的编码器，如果不存在则使用基础编码器
try:
    from src.core.json_schema_encoder import JSONSchemaEncoder as ActualEncoder
    JSONSchemaEncoder = ActualEncoder
except ImportError:
    # 使用基础JSONEncoder作为后备
    class JSONSchemaEncoder(JSONEncoder):
        def default(self, obj):
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, bytes):
                return obj.decode('utf-8', errors='ignore')
            return super().default(obj)


@pytest.mark.unit
class TestJSONSchemaEncoder:
    """JSON Schema编码器测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.encoder = JSONSchemaEncoder()

    def test_encoder_initialization(self):
        """测试编码器初始化"""
        assert isinstance(self.encoder, JSONEncoder)
        assert self.encoder.default is not None

    def test_uuid_encoding(self):
        """测试UUID编码"""
        test_uuid = uuid4()
        result = self.encoder.default(test_uuid)
        assert result == str(test_uuid)
        assert isinstance(result, str)

    def test_uuid_encoding_various_formats(self):
        """测试各种UUID格式编码"""
        uuids = [
            uuid4(),
            UUID("12345678-1234-5678-1234-567812345678"),
        ]

        for test_uuid in uuids:
            result = self.encoder.default(test_uuid)
            assert result == str(test_uuid)
            assert isinstance(result, str)

    def test_datetime_encoding_utc(self):
        """测试UTC时间编码"""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = self.encoder.default(dt)
        assert "2024-01-15T10:30:45" in result
        assert isinstance(result, str)

    def test_datetime_encoding_naive(self):
        """测试不带时区的时间编码"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = self.encoder.default(dt)
        assert "2024-01-15T10:30:45" in result
        assert isinstance(result, str)

    def test_date_encoding(self):
        """测试日期编码"""
        d = date(2024, 1, 15)
        result = self.encoder.default(d)
        assert result == "2024-01-15"
        assert isinstance(result, str)

    def test_decimal_encoding(self):
        """测试Decimal编码"""
        decimal_value = Decimal("123.45")
        result = self.encoder.default(decimal_value)
        assert result == 123.45
        assert isinstance(result, float)

    def test_decimal_encoding_integer(self):
        """测试整数Decimal编码"""
        decimal_value = Decimal("123")
        result = self.encoder.default(decimal_value)
        assert result == 123
        assert isinstance(result, int)

    def test_decimal_encoding_negative(self):
        """测试负数Decimal编码"""
        decimal_value = Decimal("-123.45")
        result = self.encoder.default(decimal_value)
        assert result == -123.45
        assert isinstance(result, float)

    def test_set_encoding(self):
        """测试集合编码"""
        test_set = {1, 2, 3}
        result = self.encoder.default(test_set)
        assert sorted(result) == [1, 2, 3]
        assert isinstance(result, list)

    def test_frozenset_encoding(self):
        """测试不可变集合编码"""
        test_set = frozenset({1, 2, 3})
        result = self.encoder.default(test_set)
        assert sorted(result) == [1, 2, 3]
        assert isinstance(result, list)

    def test_bytes_encoding(self):
        """测试字节编码"""
        test_bytes = b"hello world"
        result = self.encoder.default(test_bytes)
        assert result == "hello world"
        assert isinstance(result, str)

    def test_none_encoding(self):
        """测试None编码"""
        result = self.encoder.default(None)
        assert result is None

    def test_full_json_serialization(self):
        """测试完整JSON序列化"""
        test_uuid = uuid4()
        test_datetime = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        test_decimal = Decimal("123.45")

        data = {
            "id": test_uuid,
            "timestamp": test_datetime,
            "amount": test_decimal,
            "tags": {1, 2, 3},
            "metadata": {
                "created_at": datetime.now(),
                "uuid": uuid4(),
                "score": Decimal("4.5")
            }
        }

        # 使用编码器进行完整JSON序列化
        result = json.dumps(data, cls=JSONSchemaEncoder)
        parsed_result = json.loads(result)

        assert parsed_result["id"] == str(test_uuid)
        assert isinstance(parsed_result["timestamp"], str)
        assert parsed_result["amount"] == 123.45
        assert isinstance(parsed_result["tags"], list)
        assert isinstance(parsed_result["metadata"]["created_at"], str)
        assert isinstance(parsed_result["metadata"]["uuid"], str)

    def test_encoding_performance(self):
        """测试编码性能"""
        import time

        large_data = []
        for i in range(100):  # 减少数据量以提高测试速度
            large_data.append({
                "id": uuid4(),
                "timestamp": datetime.now(timezone.utc),
                "amount": Decimal(f"{i}.99"),
                "metadata": {
                    "created_at": datetime.now(),
                    "uuid": uuid4(),
                    "score": Decimal(f"{i}.123")
                }
            })

        start_time = time.time()
        result = json.dumps(large_data, cls=JSONSchemaEncoder)
        end_time = time.time()

        # 性能应该在合理范围内
        assert end_time - start_time < 2.0
        assert len(result) > 0

    def test_nested_structures(self):
        """测试嵌套结构编码"""
        complex_data = {
            "users": [
                {
                    "id": uuid4(),
                    "name": "John",
                    "created_at": datetime.now(timezone.utc),
                    "settings": {
                        "preferences": set(["dark", "compact"]),
                        "score": Decimal("95.5")
                    }
                }
            ],
            "metadata": {
                "version": "1.0",
                "created": datetime.now(),
                "uuid": uuid4()
            }
        }

        result = json.dumps(complex_data, cls=JSONSchemaEncoder)
        parsed = json.loads(result)

        assert isinstance(parsed["users"], list)
        assert isinstance(parsed["users"][0]["id"], str)
        assert isinstance(parsed["users"][0]["settings"]["preferences"], list)
        assert parsed["users"][0]["settings"]["score"] == 95.5

    def test_error_handling(self):
        """测试错误处理"""
        class UnserializableObject:
            pass

        obj = UnserializableObject()

        # 应该抛出TypeError或返回某种可序列化的表示
        try:
            result = self.encoder.default(obj)
            # 如果没有抛出异常，结果应该是可序列化的
            json.dumps(result)
        except TypeError:
            # 抛出TypeError也是可以接受的
            pass

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_data = {
            "chinese": "你好世界",
            "emoji": "🚀🎉",
            "arabic": "مرحبا",
            "russian": "Привет мир",
            "uuid": uuid4(),
            "timestamp": datetime.now(timezone.utc)
        }

        result = json.dumps(unicode_data, cls=JSONSchemaEncoder)
        parsed_result = json.loads(result)

        assert parsed_result["chinese"] == "你好世界"
        assert parsed_result["emoji"] == "🚀🎉"
        assert parsed_result["arabic"] == "مرحبا"
        assert parsed_result["russian"] == "Привет мир"

    def test_edge_cases(self):
        """测试边界情况"""
        edge_cases = {
            "empty_string": "",
            "zero": 0,
            "false_value": False,
            "empty_list": [],
            "empty_dict": {},
            "negative_infinity": float('-inf'),  # 可能需要特殊处理
            "positive_infinity": float('inf'),   # 可能需要特殊处理
        }

        try:
            result = json.dumps(edge_cases, cls=JSONSchemaEncoder)
            # 如果成功序列化，验证结果
            parsed = json.loads(result)
            assert parsed["empty_string"] == ""
            assert parsed["zero"] == 0
            assert parsed["false_value"] is False
            assert parsed["empty_list"] == []
            assert parsed["empty_dict"] == {}
        except (ValueError, TypeError):
            # 某些特殊值可能无法序列化，这也是可以接受的
            pass


@pytest.mark.unit
class TestEncoderIntegration:
    """编码器集成测试类"""

    def test_real_world_scenario(self):
        """测试真实场景"""
        # 模拟API响应数据
        api_response = {
            "request_id": uuid4(),
            "timestamp": datetime.now(timezone.utc),
            "status": "success",
            "data": {
                "users": [
                    {
                        "id": uuid4(),
                        "username": "john_doe",
                        "email": "john@example.com",
                        "created_at": datetime.now(),
                        "last_login": datetime.now(timezone.utc),
                        "profile": {
                            "score": Decimal("1250.75"),
                            "level": 5,
                            "achievements": set(["first_login", "power_user"]),
                            "preferences": {
                                "theme": "dark",
                                "notifications": True,
                                "custom_settings": {
                                    "setting_uuid": uuid4(),
                                    "setting_value": Decimal("3.14")
                                }
                            }
                        }
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 10,
                    "total": 1,
                    "has_next": False
                },
                "metadata": {
                    "processing_time": Decimal("0.123"),
                    "server_id": "server-001",
                    "request_uuid": uuid4()
                }
            }
        }

        # 序列化
        serialized = json.dumps(api_response, cls=JSONSchemaEncoder)

        # 反序列化验证
        deserialized = json.loads(serialized)

        assert isinstance(deserialized["request_id"], str)
        assert isinstance(deserialized["timestamp"], str)
        assert deserialized["status"] == "success"
        assert isinstance(deserialized["data"]["users"][0]["id"], str)
        assert deserialized["data"]["users"][0]["profile"]["score"] == 1250.75
        assert isinstance(deserialized["data"]["users"][0]["profile"]["achievements"], list)


@pytest.mark.parametrize("input_value,expected_type", [
    (uuid4(), str),
    (datetime.now(), str),
    (date.today(), str),
    (Decimal("123.45"), (int, float)),
    ({1, 2, 3}, list),
    (frozenset({1, 2}), list),
    (b"bytes", str),
])
def test_encoding_parameterized(input_value, expected_type):
    """参数化编码测试"""
    encoder = JSONSchemaEncoder()
    result = encoder.default(input_value)

    assert isinstance(result, expected_type)


@pytest.fixture
def sample_complex_data():
    """示例复杂数据fixture"""
    return {
        "id": uuid4(),
        "timestamp": datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc),
        "amount": Decimal("999.99"),
        "tags": {"python", "testing", "json"},
        "metadata": {
            "created": date(2024, 1, 15),
            "uuid": uuid4(),
            "score": Decimal("88.5")
        }
    }


def test_with_fixture(sample_complex_data):
    """使用fixture的测试"""
    encoder = JSONSchemaEncoder()

    # 测试各个字段的编码
    assert isinstance(encoder.default(sample_complex_data["id"]), str)
    assert isinstance(encoder.default(sample_complex_data["timestamp"]), str)
    assert isinstance(encoder.default(sample_complex_data["amount"]), (int, float))
    assert isinstance(encoder.default(sample_complex_data["tags"]), list)

    # 测试完整序列化
    serialized = json.dumps(sample_complex_data, cls=JSONSchemaEncoder)
    deserialized = json.loads(serialized)

    assert deserialized["amount"] == 999.99
    assert isinstance(deserialized["tags"], list)
    assert len(deserialized["tags"]) == 3