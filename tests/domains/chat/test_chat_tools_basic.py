"""
聊天基础工具测试套件

测试聊天系统的基础工具功能，包括：
1. 芝麻开门工具 (sesame_opener)
2. 计算器工具 (calculator)

测试重点：
- 工具调用流程验证
- 参数验证
- 响应格式验证
- 错误处理
- JSON解析正确性

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

# 导入测试基础设施
from .test_chat_tools_infrastructure import (
    ToolCallLogger,
    MockToolServiceContext,
    ToolResponseValidator,
    ToolTestDataFactory,
    ChatToolsTestConfig
)

# 导入要测试的工具
from src.domains.chat.tools.password_opener import sesame_opener
from src.domains.chat.tools.calculator import calculator

# 配置日志
logger = logging.getLogger(__name__)


class TestBasicTools:
    """基础工具测试类"""

    def setup_method(self):
        """设置测试方法"""
        self.call_logger = ToolCallLogger()
        self.service_context = MockToolServiceContext()

        # Mock服务上下文
        services = self.service_context.get_services()
        self.mock_task_service = services['task_service']
        self.mock_points_service = services['points_service']

    def teardown_method(self):
        """清理测试方法"""
        self.call_logger.clear()

    def test_sesame_opener_success(self):
        """测试芝麻开门工具成功场景"""
        # 准备测试数据
        test_command = "芝麻开门"
        expected_tool_name = "sesame_opener"

        # 调用工具
        result = sesame_opener.invoke({'command': test_command})

        # 验证响应 - 芝麻开门工具返回字符串而非JSON
        assert "芝麻开门成功" in result, "芝麻开门工具响应验证失败"

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 1, "应该有一次工具调用"
        assert calls[0]['tool_name'] == expected_tool_name, "工具名称不正确"
        assert 'command' in calls[0]['parameters'], "参数应该包含command"
        assert calls[0]['parameters']['command'] == test_command, "命令参数不正确"

        logger.info(f"✅ 芝麻开门工具测试通过")

    def test_sesame_opener_no_keyword(self):
        """测试芝麻开门工具无关键词场景"""
        test_command = "普通问候"
        expected_tool_name = "sesame_opener"

        # 调用工具
        result = sesame_opener.invoke({'command': test_command})

        # 验证响应 - 芝麻开门工具返回字符串而非JSON
        assert "芝麻开门" in result, "错误消息应包含关键词"
        assert "请说芝麻开门" in result, "错误消息应包含提示"

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 1, "应该有一次工具调用"

        logger.info(f"✅ 芝麻开门工具无关键词测试通过")

    def test_calculator_basic_math(self):
        """测试计算器基本数学运算"""
        test_expression = "10 + 5"
        expected_result = 15

        # 调用工具
        result = calculator.invoke({'expression': test_expression})

        # 验证响应
        assert ToolResponseValidator.validate_success_response(result), "计算器响应验证失败"

        # 验证结果
        try:
            result_data = json.loads(result)
            assert 'success' in result_data, "响应应该包含成功标识"
            if 'data' in result_data:
                assert str(expected_result) in result_data['data'], "计算结果不正确"
        except json.JSONDecodeError:
            pytest.fail("响应不是有效的JSON格式")

        # 验证调用日志
        calls = self.call_logger.get_calls()
        assert len(calls) == 1, "应该有一次工具调用"
        assert calls[0]['tool_name'] == 'calculator', "工具名称不正确"
        assert 'expression' in calls[0]['parameters'], "参数应该包含表达式"
        assert calls[0]['parameters']['expression'] == test_expression, "表达式参数不正确"

        logger.info(f"✅ 计算器基本运算测试通过")

    def test_calculator_division_by_zero(self):
        """测试计算器除零错误处理"""
        test_expression = "10 / 0"

        # 调用工具
        result = calculator.invoke({'expression': test_expression})

        # 验证响应
        assert not ToolResponseValidator.validate_success_response(result), "除零应该返回错误"
        assert ToolResponseValidator.validate_error_response(result), "错误响应格式不正确"
        assert "除零错误" in result, "错误消息应包含除零"
        assert "CALCULATION_ERROR" in result, "应该返回计算错误代码"

        logger.info(f"✅ 计算器除零错误测试通过")

    def test_calculator_invalid_expression(self):
        """测试计算器无效表达式错误处理"""
        test_expression = "invalid_math_expression"

        # 调用工具
        result = calculator.invoke({'expression': test_expression})

        # 验证响应
        assert not ToolResponseValidator.validate_success_response(result), "无效表达式应该返回错误"
        assert ToolResponseValidator.validate_error_response(result), "错误响应格式不正确"
        assert "表达式错误" in result, "错误消息应包含表达式"
        assert "CALCULATION_ERROR" in result, "应该返回计算错误代码"

        logger.info(f"✅ 计算器无效表达式测试通过")

    def run_all_tests(self):
        """运行所有基础工具测试"""
        try:
            logger.info("🔄 开始运行基础工具测试...")

            # 测试芝麻开门工具
            self.test_sesame_opener_success(self.mock_context)
            self.test_sesame_opener_no_keyword(self.mock_context)

            # 测试计算器
            self.test_calculator_basic_math(self.mock_context)
            self.test_calculator_division_by_zero(self.mock_context)
            self.test_calculator_invalid_expression(self.mock_context)

            logger.info("✅ 所有基础工具测试通过")
            return True

        except Exception as e:
            logger.error(f"❌ 基础工具测试失败: {e}")
            return False


# 测试数据
test_data_factory = ToolTestDataFactory()


class TestCalculatorFunctions:
    """计算器特定测试函数"""

    @staticmethod
    def test_addition():
        """测试加法运算"""
        result = calculator.invoke({'expression': '5 + 3'})
        assert ToolResponseValidator.validate_success_response(result)
        result_data = json.loads(result)
        assert result_data['data'] == '8', "5+3应该等于8"

    @staticmethod
    def test_subtraction():
        """测试减法运算"""
        result = calculator.invoke({'expression': '10 - 4'})
        assert ToolResponseValidator.validate_success_response(result)
        result_data = json.loads(result)
        assert result_data['data'] == '6', "10-4应该等于6"

    @staticmethod
    def test_multiplication():
        """测试乘法运算"""
        result = calculator.invoke({'expression': '3 * 4'})
        assert ToolResponseValidator.validate_success_response(result)
        result_data = json.loads(result)
        assert result_data['data'] == '12', "3*4应该等于12"

    @staticmethod
    def test_division():
        """测试除法运算"""
        result = calculator.invoke({'expression': '15 / 3'})
        assert ToolResponseValidator.validate_success_response(result)
        result_data = json.loads(result)
        assert result_data['data'] == '5', "15/3应该等于5"


if __name__ == "__main__":
    """运行基础工具测试"""
    test_instance = TestBasicTools()

    try:
        # 运行测试
        success = test_instance.run_all_tests()

        if success:
            print("🎉 所有基础工具测试通过！")
        else:
            print("❌ 基础工具测试失败！")

    except Exception as e:
        print(f"💥 测试执行异常: {e}")