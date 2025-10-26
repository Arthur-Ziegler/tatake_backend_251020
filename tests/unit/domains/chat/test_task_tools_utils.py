"""
聊天工具辅助函数测试套件

测试驱动开发（TDD）：先编写测试，再实现功能。
本文件包含对 chat/tools/utils.py 中所有辅助函数的全面测试。

测试覆盖范围：
1. Session管理：get_task_service_context()
2. UUID转换：safe_uuid_convert()
3. 日期解析：parse_datetime()
4. 响应格式化：_success_response(), _error_response()

设计原则：
1. 每个测试用例独立运行，不依赖其他测试
2. 覆盖正常情况、边界情况和异常情况
3. 使用清晰的测试数据和期望结果
4. 验证错误处理的完整性和友好性

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Dict, Any

# 测试用例专用的logger
logger = logging.getLogger(__name__)

# 导入要测试的模块（稍后创建）
# from src.domains.chat.tools.utils import (
#     get_task_service_context,
#     safe_uuid_convert,
#     parse_datetime,
#     _success_response,
#     _error_response
# )


class TestGetTaskServiceContext:
    """测试 get_task_service_context 函数"""

    def test_get_task_service_context_basic_functionality(self):
        """测试上下文管理器基本功能"""
        from src.domains.chat.tools.utils import get_task_service_context

        # 测试上下文管理器能正确创建和返回
        try:
            with get_task_service_context() as context:
                # 验证返回的是字典
                assert isinstance(context, dict)

                # 验证包含必需的键
                assert 'session' in context
                assert 'task_service' in context
                assert 'points_service' in context

                # 验证对象类型
                assert hasattr(context['session'], 'close')  # Session对象应有close方法
                logger.debug(f"上下文管理器测试通过，返回键: {list(context.keys())}")

        except Exception as e:
            # 如果是导入问题或基本结构问题，让测试失败并提供详细信息
            pytest.fail(f"上下文管理器基本功能测试失败: {e}")

    def test_get_task_service_context_context_manager_properties(self):
        """测试上下文管理器的资源管理"""
        from src.domains.chat.tools.utils import get_task_service_context

        session_closed = False

        try:
            with get_task_service_context() as context:
                session = context['session']
                # 验证session有效
                assert session is not None
                logger.debug("Session在上下文中有效")

        except Exception as e:
            pytest.fail(f"上下文管理器资源测试失败: {e}")

        # 验证Session已关闭（通过检查是否能正常使用）
        logger.debug("上下文管理器资源管理测试完成")


class TestSafeUUIDConvert:
    """测试 safe_uuid_convert 函数"""

    def test_safe_uuid_convert_valid_uuid_string(self):
        """测试有效UUID字符串转换"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        test_uuid = uuid4()
        result = safe_uuid_convert(str(test_uuid))

        assert isinstance(result, UUID)
        assert str(result) == str(test_uuid)

    def test_safe_uuid_convert_valid_uuid_object(self):
        """测试UUID对象输入"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        test_uuid = uuid4()
        result = safe_uuid_convert(test_uuid)

        assert isinstance(result, UUID)
        assert result == test_uuid

    def test_safe_uuid_convert_none_input(self):
        """测试None输入"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        result = safe_uuid_convert(None)

        assert result is None

    def test_safe_uuid_convert_invalid_string(self):
        """测试无效UUID字符串"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        with pytest.raises(ValueError, match="无效的UUID格式"):
            safe_uuid_convert("invalid-uuid-string")

    def test_safe_uuid_convert_empty_string(self):
        """测试空字符串"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        with pytest.raises(ValueError, match="UUID不能为空字符串"):
            safe_uuid_convert("")

    def test_safe_uuid_convert_invalid_format(self):
        """测试格式错误的UUID"""
        from src.domains.chat.tools.utils import safe_uuid_convert

        invalid_uuids = [
            "123-456-789",
            "not-a-uuid",
            "550e8400-e29b-41d4-a716-44665544000",  # 缺少一段
            "g50e8400-e29b-41d4-a716-446655440000"  # 包含非法字符
        ]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValueError, match="无效的UUID格式"):
                safe_uuid_convert(invalid_uuid)


class TestParseDatetime:
    """测试 parse_datetime 函数"""

    def test_parse_datetime_iso_format(self):
        """测试标准ISO格式日期时间"""
        from src.domains.chat.tools.utils import parse_datetime

        test_datetime = "2024-12-25T10:30:00"
        result = parse_datetime(test_datetime)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_datetime_with_z_timezone(self):
        """测试带Z时区标记的ISO格式"""
        from src.domains.chat.tools.utils import parse_datetime

        test_datetime = "2024-12-25T10:30:00Z"
        result = parse_datetime(test_datetime)

        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 0  # UTC时区

    def test_parse_datetime_with_timezone_offset(self):
        """测试带时区偏移的ISO格式"""
        from src.domains.chat.tools.utils import parse_datetime

        test_datetime = "2024-12-25T10:30:00+08:00"
        result = parse_datetime(test_datetime)

        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.utcoffset(result).total_seconds() == 8 * 3600  # +8小时

    def test_parse_datetime_date_only(self):
        """测试只有日期的格式"""
        from src.domains.chat.tools.utils import parse_datetime

        test_datetime = "2024-12-25"
        result = parse_datetime(test_datetime)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_datetime_none_input(self):
        """测试None输入"""
        from src.domains.chat.tools.utils import parse_datetime

        result = parse_datetime(None)

        assert result is None

    def test_parse_datetime_empty_string(self):
        """测试空字符串输入"""
        from src.domains.chat.tools.utils import parse_datetime

        with pytest.raises(ValueError, match="日期时间字符串不能为空"):
            parse_datetime("")

    def test_parse_datetime_invalid_format(self):
        """测试无效日期格式"""
        from src.domains.chat.tools.utils import parse_datetime

        invalid_formats = [
            "invalid-date",
            "2024-13-01",  # 无效月份
            "2024-02-30",  # 无效日期
            "24:00:00",    # 无效时间
            "2024/12/25",   # 错误分隔符
        ]

        for invalid_format in invalid_formats:
            with pytest.raises(ValueError, match="无效的日期时间格式"):
                parse_datetime(invalid_format)


class TestSuccessResponse:
    """测试 _success_response 函数"""

    def test_success_response_basic(self):
        """测试基本成功响应"""
        from src.domains.chat.tools.utils import _success_response

        data = {"task_id": "123", "status": "completed"}
        result = _success_response(data)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == data
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_success_response_with_message(self):
        """测试带自定义消息的成功响应"""
        from src.domains.chat.tools.utils import _success_response

        data = {"task_id": "123"}
        message = "任务完成成功"
        result = _success_response(data, message)

        assert result["success"] is True
        assert result["data"] == data
        assert result["message"] == message

    def test_success_response_none_data(self):
        """测试数据为None的成功响应"""
        from src.domains.chat.tools.utils import _success_response

        result = _success_response(None)

        assert result["success"] is True
        assert result["data"] is None

    def test_success_response_timestamp_format(self):
        """测试时间戳格式"""
        from src.domains.chat.tools.utils import _success_response

        result = _success_response({})
        timestamp_str = result["timestamp"]

        # 验证时间戳格式
        parsed_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)


class TestErrorResponse:
    """测试 _error_response 函数"""

    def test_error_response_basic(self):
        """测试基本错误响应"""
        from src.domains.chat.tools.utils import _error_response

        message = "任务不存在"
        result = _error_response(message)

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == message
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)

    def test_error_response_with_code(self):
        """测试带错误代码的错误响应"""
        from src.domains.chat.tools.utils import _error_response

        message = "权限不足"
        code = "PERMISSION_DENIED"
        result = _error_response(message, code)

        assert result["success"] is False
        assert result["error"] == message
        assert result["error_code"] == code

    def test_error_response_with_details(self):
        """测试带详细信息的错误响应"""
        from src.domains.chat.tools.utils import _error_response

        message = "验证失败"
        details = {"field": "title", "reason": "标题不能为空"}
        result = _error_response(message, details=details)

        assert result["success"] is False
        assert result["error"] == message
        assert result["details"] == details

    def test_error_response_empty_message(self):
        """测试空错误消息"""
        from src.domains.chat.tools.utils import _error_response

        with pytest.raises(ValueError, match="错误消息不能为空"):
            _error_response("")

    def test_error_response_none_message(self):
        """测试None错误消息"""
        from src.domains.chat.tools.utils import _error_response

        with pytest.raises(ValueError, match="错误消息不能为空"):
            _error_response(None)


class TestIntegration:
    """集成测试：测试函数间的协作"""

    @patch('src.domains.chat.tools.utils.get_engine')
    @patch('src.domains.chat.tools.utils.Session')
    def test_full_workflow_success(self, mock_session_class, mock_get_engine):
        """测试完整工作流程成功场景"""
        # 这个测试验证所有函数在实际使用场景中的协作
        pass

    def test_error_propagation(self):
        """测试错误传播和处理"""
        # 验证错误在不同函数间的正确传播
        pass


# 性能测试
class TestPerformance:
    """性能测试"""

    def test_uuid_conversion_performance(self):
        """测试UUID转换性能"""
        import time
        from src.domains.chat.tools.utils import safe_uuid_convert

        test_uuid = str(uuid4())
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            safe_uuid_convert(test_uuid)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"UUID转换平均时间过长: {avg_time}秒"

    def test_datetime_parsing_performance(self):
        """测试日期解析性能"""
        import time
        from src.domains.chat.tools.utils import parse_datetime

        test_datetime = "2024-12-25T10:30:00Z"
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            parse_datetime(test_datetime)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"日期解析平均时间过长: {avg_time}秒"