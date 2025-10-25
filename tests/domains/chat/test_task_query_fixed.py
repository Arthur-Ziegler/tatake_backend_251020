"""
任务查询工具测试套件（修复版）

测试驱动开发（TDD）：先编写测试，再验证功能实现。
本文件包含对 chat/tools/task_query.py 中所有工具函数的全面测试。

修复说明：
1. 使用正确的LangChain工具调用方式：tool.invoke(params)
2. 修复Mock的配置方式
3. 确保JSON响应格式的正确解析

作者：TaKeKe团队
版本：1.0.1
"""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from typing import Dict, Any, List

# 测试用例专用的logger
logger = logging.getLogger(__name__)

# 导入要测试的模块
from src.domains.chat.tools.task_query import (
    query_tasks,
    get_task_detail,
    validate_query_parameters,
    validate_task_id,
    get_tool_info,
    AVAILABLE_TOOLS
)


class TestQueryTools:
    """测试任务查询工具（合并测试类以提高效率）"""

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_basic_success(self, mock_context):
        """测试基本查询成功场景"""
        # 模拟服务上下文
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "测试任务1",
                "status": "pending",
                "priority": "medium"
            },
            {
                "id": "task-2",
                "title": "测试任务2",
                "status": "completed",
                "priority": "high"
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具 - 使用invoke方法
        result = query_tasks.invoke({})
        result_data = json.loads(result)

        # 验证结果
        assert result_data["success"] is True
        assert "data" in result_data
        assert "tasks" in result_data["data"]
        assert "pagination" in result_data["data"]
        assert len(result_data["data"]["tasks"]) == 2
        assert result_data["data"]["pagination"]["limit"] == 20
        assert result_data["data"]["pagination"]["offset"] == 0

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status=None,
            parent_id=None,
            limit=20,
            offset=0
        )

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_with_parameters(self, mock_context):
        """测试带参数的查询"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "已完成任务",
                "status": "completed",
                "priority": "high"
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具 - 带参数
        result = query_tasks.invoke({
            "status": "completed",
            "limit": 10,
            "offset": 5
        })
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 1

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status="completed",
            parent_id=None,
            limit=10,
            offset=5
        )

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_with_parent_id(self, mock_context):
        """测试带父任务ID筛选的查询"""
        parent_id = str(uuid4())
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "child-task-1",
                "title": "子任务1",
                "status": "pending",
                "parent_id": parent_id
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks.invoke({"parent_id": parent_id})
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 1

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="placeholder",
            status=None,
            parent_id=parent_id,
            limit=20,
            offset=0
        )

    def test_query_tasks_invalid_parameters(self):
        """测试无效参数"""
        # 测试各种无效参数
        invalid_params_list = [
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"parent_id": "invalid-uuid"}
        ]

        for invalid_params in invalid_params_list:
            result = query_tasks.invoke(invalid_params)
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "INVALID_PARAMETERS" in result_data.get("error_code", "")

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_empty_result(self, mock_context):
        """测试空结果查询"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = []

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = query_tasks.invoke({})
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]["tasks"]) == 0
        assert result_data["data"]["pagination"]["count"] == 0

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_query_tasks_service_exception(self, mock_context):
        """测试服务异常处理"""
        mock_context.side_effect = Exception("数据库连接失败")

        # 调用工具
        result = query_tasks.invoke({})
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "QUERY_FAILED" in result_data.get("error_code", "")

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_success(self, mock_context):
        """测试成功获取任务详情"""
        task_id = str(uuid4())
        expected_task = {
            "id": task_id,
            "title": "测试任务",
            "description": "这是一个测试任务",
            "status": "pending",
            "priority": "high",
            "created_at": "2024-12-25T10:30:00Z"
        }

        mock_task_service = Mock()
        mock_task_service.get_task.return_value = expected_task

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = get_task_detail.invoke({"task_id": task_id})
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["data"]["task"] == expected_task
        assert "获取成功" in result_data["message"]

        # 验证服务调用参数
        mock_task_service.get_task.assert_called_once_with(
            task_id=UUID(task_id),
            user_id="placeholder"
        )

    def test_get_task_detail_invalid_task_id(self):
        """测试无效任务ID"""
        invalid_task_ids = [
            "",
            None,
            "   ",
            "invalid-uuid",
            "123-456-789",
            "not-a-uuid-at-all",
            "550e8400-e29b-41d4-a716-44665544000"  # 缺少一段
        ]

        for invalid_id in invalid_task_ids:
            if invalid_id is None:
                # None需要特殊处理
                try:
                    result = get_task_detail.invoke({"task_id": invalid_id})
                    result_data = json.loads(result)
                    assert result_data["success"] is False
                except Exception:
                    # 如果工具参数验证本身失败，这也是可以接受的
                    pass
            else:
                result = get_task_detail.invoke({"task_id": invalid_id})
                result_data = json.loads(result)

                assert result_data["success"] is False
                assert "INVALID_PARAMETERS" in result_data.get("error_code", "")

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_get_task_detail_service_exception(self, mock_context):
        """测试服务异常"""
        task_id = str(uuid4())

        mock_task_service = Mock()
        mock_task_service.get_task.side_effect = Exception("任务不存在")

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用工具
        result = get_task_detail.invoke({"task_id": task_id})
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "GET_DETAIL_FAILED" in result_data.get("error_code", "")


class TestValidationFunctions:
    """测试验证函数（这些函数不需要LangChain工具调用）"""

    def test_validate_query_parameters_valid_cases(self):
        """测试有效参数验证"""
        valid_cases = [
            (None, None, 20, 0),
            ("completed", None, 50, 10),
            ("pending", str(uuid4()), 10, 0),
            (None, str(uuid4()), 100, 50)
        ]

        for status, parent_id, limit, offset in valid_cases:
            assert validate_query_parameters(status, parent_id, limit, offset) is True

    def test_validate_query_parameters_invalid_cases(self):
        """测试无效参数验证"""
        invalid_cases = [
            (None, None, 0, 0),  # limit = 0
            (None, None, -1, 0),  # negative limit
            (None, None, 101, 0),  # limit > 100
            (None, None, 20, -1),  # negative offset
            ("invalid", None, 20, 0),  # invalid status
            (None, "invalid-uuid", 20, 0),  # invalid parent_id
        ]

        for status, parent_id, limit, offset in invalid_cases:
            assert validate_query_parameters(status, parent_id, limit, offset) is False

    def test_validate_task_id_valid_cases(self):
        """测试有效任务ID验证"""
        valid_ids = [
            str(uuid4()),
            str(uuid4()),  # 不同的UUID
        ]

        for task_id in valid_ids:
            assert validate_task_id(task_id) is True

    def test_validate_task_id_invalid_cases(self):
        """测试无效任务ID验证"""
        invalid_ids = [
            "",
            None,
            "   ",
            "\t\n",
            "invalid-uuid",
            "123-456-789",
            "not-a-uuid",
            "550e8400-e29b-41d4-a716-44665544000",  # 缺少一段
            "g50e8400-e29b-41d4-a716-446655440000"  # 包含非法字符
        ]

        for task_id in invalid_ids:
            assert validate_task_id(task_id) is False


class TestToolMetadata:
    """测试工具元数据"""

    def test_get_tool_info_structure(self):
        """测试工具信息结构"""
        info = get_tool_info()

        assert isinstance(info, dict)
        assert "tools" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) == 2

        # 检查工具名称
        tool_names = [tool["name"] for tool in info["tools"]]
        assert "query_tasks" in tool_names
        assert "get_task_detail" in tool_names

    def test_available_tools_properties(self):
        """测试可用工具属性"""
        assert isinstance(AVAILABLE_TOOLS, list)
        assert len(AVAILABLE_TOOLS) == 2

        # 验证每个工具都有LangChain工具的标准属性
        for tool in AVAILABLE_TOOLS:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'args')
            assert hasattr(tool, 'invoke')

            # 验证工具名称
            assert tool.name in ['query_tasks', 'get_task_detail']

            # 验证工具描述
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

            # 验证工具参数
            assert hasattr(tool, 'args')
            # args可能是字符串或字典，取决于LangChain版本


class TestResponseFormat:
    """测试响应格式"""

    @patch('src.domains.chat.tools.task_query.get_task_service_context')
    def test_success_response_format(self, mock_context):
        """测试成功响应格式"""
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = []

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        result = query_tasks.invoke({})
        parsed_result = json.loads(result)

        # 验证成功响应的必要字段
        required_fields = ["success", "data", "message", "timestamp"]
        for field in required_fields:
            assert field in parsed_result

        # 验证字段类型
        assert isinstance(parsed_result["success"], bool)
        assert isinstance(parsed_result["data"], dict)
        assert isinstance(parsed_result["message"], str)
        assert isinstance(parsed_result["timestamp"], str)

    def test_error_response_format(self):
        """测试错误响应格式"""
        result = query_tasks.invoke({"limit": -1})
        parsed_result = json.loads(result)

        # 验证错误响应的必要字段
        required_fields = ["success", "error", "timestamp"]
        for field in required_fields:
            assert field in parsed_result

        # 验证字段类型
        assert isinstance(parsed_result["success"], bool)
        assert isinstance(parsed_result["error"], str)
        assert isinstance(parsed_result["timestamp"], str)

        # 验证错误响应成功字段为False
        assert parsed_result["success"] is False


class TestErrorHandling:
    """测试错误处理"""

    def test_tool_error_handling_consistency(self):
        """测试工具错误处理一致性"""
        # 测试query_tasks的各种错误情况
        query_error_cases = [
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"parent_id": "invalid"},
        ]

        for error_params in query_error_cases:
            result = query_tasks.invoke(error_params)
            parsed_result = json.loads(result)

            assert parsed_result["success"] is False
            assert "error" in parsed_result
            assert "timestamp" in parsed_result

        # 测试get_task_detail的各种错误情况
        detail_error_cases = [
            {"task_id": ""},
            {"task_id": "invalid-uuid"},
            {"task_id": "123-456-789"},
        ]

        for error_params in detail_error_cases:
            result = get_task_detail.invoke(error_params)
            parsed_result = json.loads(result)

            assert parsed_result["success"] is False
            assert "error" in parsed_result
            assert "timestamp" in parsed_result


# 性能测试
class TestPerformance:
    """性能测试"""

    def test_validation_performance(self):
        """测试验证函数性能"""
        import time

        # 测试参数验证性能
        iterations = 1000
        parent_id = str(uuid4())

        start_time = time.time()
        for _ in range(iterations):
            validate_query_parameters("completed", parent_id, 20, 0)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"参数验证平均时间过长: {avg_time}秒"

        # 测试任务ID验证性能
        task_id = str(uuid4())
        start_time = time.time()
        for _ in range(iterations):
            validate_task_id(task_id)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        assert avg_time < 0.001, f"任务ID验证平均时间过长: {avg_time}秒"


if __name__ == "__main__":
    # 可以直接运行这个文件进行快速测试
    pytest.main([__file__, "-v"])