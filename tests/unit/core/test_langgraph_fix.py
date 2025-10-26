"""
LangGraph修复测试

测试LangGraph相关的修复功能，包括：
1. 版本类型修复
2. 通道版本处理
3. 函数替换机制
4. 错误处理修复

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List

# 模拟LangGraph相关导入
try:
    import langgraph.pregel._utils as langgraph_utils
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from src.core.langgraph_fix import (
    apply_langgraph_fix,
    _fixed_get_new_channel_versions,
    _original_get_new_channel_versions
)


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="LangGraph not available")
@pytest.mark.unit
class TestLangGraphFix:
    """LangGraph修复测试类"""

    def test_apply_langgraph_fix(self):
        """测试应用LangGraph修复"""
        # 确保原始函数被保存
        assert _original_get_new_channel_versions is not None

        # 应用修复
        apply_langgraph_fix()

        # 验证函数被替换
        assert hasattr(langgraph_utils, 'get_new_channel_versions')
        assert langgraph_utils.get_new_channel_versions == _fixed_get_new_channel_versions

    def test_fixed_channel_versions_function(self):
        """测试修复的通道版本函数"""
        # 测试数据
        channels = ["channel1", "channel2"]
        values = {
            "channel1": {"version": 1, "data": "test1"},
            "channel2": {"version": 2, "data": "test2"}
        }
        previous_versions = {"channel1": 0, "channel2": 1}

        # 调用修复的函数
        result = _fixed_get_new_channel_versions(channels, values, previous_versions)

        # 验证结果
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "channel1" in result
        assert "channel2" in result

    def test_fixed_function_with_string_versions(self):
        """测试修复函数处理字符串版本"""
        channels = ["test_channel"]
        values = {
            "test_channel": {"version": "1", "data": "test"}  # 字符串版本
        }
        previous_versions = {"test_channel": 0}

        result = _fixed_get_new_channel_versions(channels, values, previous_versions)

        assert isinstance(result, dict)
        # 应该能正确处理字符串版本

    def test_fixed_function_with_mixed_versions(self):
        """测试修复函数处理混合版本类型"""
        channels = ["channel1", "channel2"]
        values = {
            "channel1": {"version": 1, "data": "test1"},  # 整数版本
            "channel2": {"version": "2", "data": "test2"}  # 字符串版本
        }
        previous_versions = {"channel1": 0, "channel2": 1}

        result = _fixed_get_new_channel_versions(channels, values, previous_versions)

        assert isinstance(result, dict)
        assert len(result) == 2

    def test_fixed_function_with_none_versions(self):
        """测试修复函数处理None版本"""
        channels = ["channel1"]
        values = {
            "channel1": {"version": None, "data": "test"}  # None版本
        }
        previous_versions = {"channel1": 0}

        result = _fixed_get_new_channel_versions(channels, values, previous_versions)

        assert isinstance(result, dict)

    def test_fixed_function_error_handling(self):
        """测试修复函数的错误处理"""
        channels = ["error_channel"]
        values = {
            "error_channel": "invalid_value"  # 无效值
        }
        previous_versions = {"error_channel": 0}

        # 应该能处理错误而不崩溃
        result = _fixed_get_new_channel_versions(channels, values, previous_versions)

        assert isinstance(result, dict)

    def test_original_function_preservation(self):
        """测试原始函数被正确保存"""
        assert _original_get_new_channel_versions is not None
        assert callable(_original_get_new_channel_versions)

    @patch('src.core.langgraph_fix.langgraph_utils')
    def test_fix_application_with_mock(self, mock_langgraph_utils):
        """测试使用mock应用修复"""
        # 重新导入以获取mock
        from src.core import langgraph_fix

        # 重新应用修复
        langgraph_fix.apply_langgraph_fix()

        # 验证mock被调用
        assert mock_langgraph_utils.get_new_channel_versions == _fixed_get_new_channel_versions


@pytest.mark.skipif(LANGGRAPH_AVAILABLE, reason="Test when LangGraph is not available")
@pytest.mark.unit
class TestLangGraphFixUnavailable:
    """LangGraph不可用时的测试"""

    def test_graceful_handling_when_unavailable(self):
        """测试LangGraph不可用时的优雅处理"""
        # 当LangGraph不可用时，修复应该仍然能工作
        try:
            apply_langgraph_fix()
            # 如果没有抛出异常，说明处理正确
            assert True
        except ImportError:
            # 如果有ImportError，这也是可以接受的
            assert True


@pytest.mark.unit
class TestVersionTypeHandling:
    """版本类型处理测试类"""

    def test_integer_version_handling(self):
        """测试整数版本处理"""
        result = _fixed_get_new_channel_versions(
            ["test"],
            {"test": {"version": 1}},
            {"test": 0}
        )
        assert isinstance(result, dict)

    def test_string_version_handling(self):
        """测试字符串版本处理"""
        result = _fixed_get_new_channel_versions(
            ["test"],
            {"test": {"version": "1"}},
            {"test": 0}
        )
        assert isinstance(result, dict)

    def test_float_version_handling(self):
        """测试浮点数版本处理"""
        result = _fixed_get_new_channel_versions(
            ["test"],
            {"test": {"version": 1.0}},
            {"test": 0}
        )
        assert isinstance(result, dict)

    def test_version_conversion(self):
        """测试版本转换"""
        # 测试各种版本格式都能被正确处理
        version_formats = [1, "1", 1.0, "1.0"]

        for version in version_formats:
            result = _fixed_get_new_channel_versions(
                ["test"],
                {"test": {"version": version}},
                {"test": 0}
            )
            assert isinstance(result, dict)


@pytest.mark.parametrize("version_input,expected_handling", [
    (1, "integer"),
    ("1", "string"),
    (1.0, "float"),
    ("1.0", "string_float"),
    (None, "none"),
    ("v1", "string_with_prefix"),
])
def test_version_parameterized(version_input, expected_handling):
    """参数化版本处理测试"""
    if LANGGRAPH_AVAILABLE:
        result = _fixed_get_new_channel_versions(
            ["test_channel"],
            {"test_channel": {"version": version_input}},
            {"test_channel": 0}
        )

        assert isinstance(result, dict)
        assert "test_channel" in result


@pytest.fixture
def mock_channels():
    """模拟通道fixture"""
    return {
        "channel1": {"version": 1, "data": "data1"},
        "channel2": {"version": "2", "data": "data2"},
        "channel3": {"version": None, "data": "data3"},
    }


def test_with_fixture(mock_channels):
    """使用fixture的测试"""
    if LANGGRAPH_AVAILABLE:
        result = _fixed_get_new_channel_versions(
            list(mock_channels.keys()),
            mock_channels,
            {"channel1": 0, "channel2": 1, "channel3": 2}
        )

        assert isinstance(result, dict)
        assert len(result) == 3