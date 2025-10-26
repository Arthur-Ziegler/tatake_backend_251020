"""
任务搜索工具测试套件

测试驱动开发（TDD）：先编写测试，再实现功能。
本文件包含对 task_search.py 中 search_tasks 工具的全面测试。

测试覆盖范围：
1. 基本功能：search_tasks返回简化任务列表
2. 参数验证：query, limit, state参数验证
3. 数据筛选：状态筛选、限制数量筛选
4. 错误处理：无效参数、数据库错误处理
5. Token优化：Token消耗估算和优化
6. 辅助函数：estimate_token_count, validate_search_parameters

设计原则：
1. 每个测试用例独立运行，不依赖其他测试
2. 覆盖正常情况、边界情况和异常情况
3. 使用清晰的测试数据和期望结果
4. Mock外部依赖，确保测试稳定性和速度
5. 验证返回格式的正确性和完整性

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Dict, Any, List

# 测试用例专用的logger
logger = logging.getLogger(__name__)


class TestSearchTasks:
    """测试 search_tasks 主要功能"""

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_basic_functionality(self, mock_context):
        """测试基本搜索功能"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # Mock上下文和服务
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "编程任务",
                "description": "完成Python项目开发",
                "status": "pending",
                "priority": "high",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 0.0
            },
            {
                "id": "task-2",
                "title": "文档编写",
                "description": "编写API文档",
                "status": "completed",
                "priority": "medium",
                "created_at": "2024-12-24T15:20:00Z",
                "completion_percentage": 100.0
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用搜索函数
        result = _search_tasks_impl("编程相关任务", 50, None)

        # 解析JSON结果
        result_data = json.loads(result)

        # 验证基本结构
        assert result_data["success"] is True
        assert "tasks" in result_data
        assert "total" in result_data
        assert "llm_hint" in result_data
        assert "estimated_tokens" in result_data

        # 验证任务数据
        tasks = result_data["tasks"]
        assert len(tasks) == 2
        assert tasks[0]["id"] == "task-1"
        assert tasks[0]["title"] == "编程任务"
        assert tasks[1]["status"] == "completed"

        # 验证服务调用
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="temp-user-id",
            status=None,
            parent_id=None,
            limit=50,
            offset=0
        )

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_with_state_filter(self, mock_context):
        """测试状态筛选功能"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # Mock只返回pending任务
        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "未完成编程任务",
                "description": "完成Python项目",
                "status": "pending",
                "priority": "high",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 0.0
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用搜索函数，筛选pending状态
        result = _search_tasks_impl("未完成任务", 30, "pending")
        result_data = json.loads(result)

        # 验证结果
        assert result_data["success"] is True
        assert result_data["state_filter"] == "pending"
        assert len(result_data["tasks"]) == 1
        assert result_data["tasks"][0]["status"] == "pending"

        # 验证服务调用参数
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="temp-user-id",
            status="pending",
            parent_id=None,
            limit=30,
            offset=0
        )

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_limit_optimization(self, mock_context):
        """测试限制数量和Token优化"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 创建100个模拟任务
        mock_tasks = []
        for i in range(100):
            mock_tasks.append({
                "id": f"task-{i}",
                "title": f"任务 {i}",
                "description": f"任务描述 {i}" * 10,  # 长描述
                "status": "pending",
                "priority": "medium",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 0.0
            })

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = mock_tasks

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 测试限制为20个任务
        result = _search_tasks_impl("大量任务搜索", 20, None)
        result_data = json.loads(result)

        # 验证限制生效
        assert result_data["success"] is True
        assert result_data["total"] == 20
        assert result_data["limit"] == 20
        assert len(result_data["tasks"]) == 20

        # 验证Token估算存在
        assert "estimated_tokens" in result_data
        assert result_data["estimated_tokens"] > 0

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_description_truncation(self, mock_context):
        """测试长描述截断功能"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # Mock包含长描述的任务
        long_description = "这是一个非常长的任务描述，" * 20  # 超过100字符的描述

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-long-desc",
                "title": "长描述任务",
                "description": long_description,
                "status": "pending",
                "priority": "medium",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 0.0
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用搜索函数
        result = _search_tasks_impl("长描述任务", 50, None)
        result_data = json.loads(result)

        # 验证描述被截断
        task = result_data["tasks"][0]
        assert len(task["description"]) <= 103  # 100字符 + "..."
        assert task["description"].endswith("...")

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_limit_adjustment(self, mock_context):
        """测试limit超过100时的自动调整"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = []

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 调用limit超过100的搜索
        result = _search_tasks_impl("测试任务", 150, None)
        result_data = json.loads(result)

        # 验证limit被调整为100
        assert result_data["limit"] == 100

        # 验证服务调用时使用调整后的limit
        mock_task_service.get_tasks.assert_called_once_with(
            user_id="temp-user-id",
            status=None,
            parent_id=None,
            limit=100,  # 应该是调整后的值
            offset=0
        )


class TestSearchTasksParameterValidation:
    """测试 search_tasks 参数验证"""

    def test_search_tasks_empty_query(self):
        """测试空查询参数"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 测试空字符串查询
        result = _search_tasks_impl("", 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "INVALID_PARAMETERS" in str(result_data)
        assert "搜索查询不能为空" in str(result_data)

        # 测试None查询
        result = _search_tasks_impl(None, 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False

    def test_search_tasks_invalid_limit(self):
        """测试无效limit参数"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 测试负数limit
        result = _search_tasks_impl("测试任务", -10, None)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "限制数量必须大于0" in str(result_data)

        # 测试零limit
        result = _search_tasks_impl("测试任务", 0, None)
        result_data = json.loads(result)

        assert result_data["success"] is False

    def test_search_tasks_invalid_state(self):
        """测试无效state参数"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 测试无效状态
        result = _search_tasks_impl("测试任务", 50, "invalid_state")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "状态筛选必须是以下之一" in str(result_data)

    def test_search_tasks_whitespace_query(self):
        """测试只包含空格的查询"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        result = _search_tasks_impl("   ", 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False

        result = _search_tasks_impl("\t\n", 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False


class TestSearchTasksErrorHandling:
    """测试搜索工具的错误处理"""

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_database_error(self, mock_context):
        """测试数据库错误处理"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # Mock数据库异常
        mock_context.return_value.__enter__.side_effect = Exception("数据库连接失败")

        result = _search_tasks_impl("测试任务", 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "SEARCH_FAILED" in str(result_data)
        assert "数据库连接失败" in str(result_data)

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_tasks_service_error(self, mock_context):
        """测试服务层错误处理"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # Mock服务异常
        mock_task_service = Mock()
        mock_task_service.get_tasks.side_effect = Exception("服务内部错误")

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        result = _search_tasks_impl("测试任务", 50, None)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "SEARCH_FAILED" in str(result_data)


class TestEstimateTokenCount:
    """测试Token估算辅助函数"""

    def test_estimate_token_count_empty_string(self):
        """测试空字符串的Token估算"""
        from src.domains.chat.tools.task_search import estimate_token_count

        result = estimate_token_count("")
        assert result == 0

        result = estimate_token_count(None)
        assert result == 0

    def test_estimate_token_count_chinese_text(self):
        """测试中文文本的Token估算"""
        from src.domains.chat.tools.task_search import estimate_token_count

        chinese_text = "这是一个中文测试文本，用于验证Token估算功能"
        result = estimate_token_count(chinese_text)

        # 中文字符数 * 1.5（考虑标点符号）
        chinese_chars = len([c for c in chinese_text if '\u4e00' <= c <= '\u9fff' or c in '，。？！；：""''（）【】《》'])
        expected = int(chinese_chars * 1.5 + (len(chinese_text) - chinese_chars) * 0.25)
        assert result == expected
        assert result > 0

    def test_estimate_token_count_english_text(self):
        """测试英文文本的Token估算"""
        from src.domains.chat.tools.task_search import estimate_token_count

        english_text = "This is an English text for token estimation testing"
        result = estimate_token_count(english_text)

        # 非中文字符数 * 0.25
        expected = int(len(english_text) * 0.25)
        assert result == expected
        assert result > 0

    def test_estimate_token_count_mixed_text(self):
        """测试中英混合文本的Token估算"""
        from src.domains.chat.tools.task_search import estimate_token_count

        mixed_text = "This is mixed text with 中文内容 and English words"
        result = estimate_token_count(mixed_text)

        # 应该分别计算中英文字符
        chinese_chars = len([c for c in mixed_text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(mixed_text) - chinese_chars
        expected = int(chinese_chars * 1.5 + other_chars * 0.25)

        assert result == expected


class TestValidateSearchParameters:
    """测试参数验证辅助函数"""

    def test_validate_search_parameters_valid(self):
        """测试有效参数验证"""
        from src.domains.chat.tools.task_search import validate_search_parameters

        result = validate_search_parameters("测试查询", 50, "pending")

        assert result["valid"] is True
        assert len(result["errors"]) == 0

        result = validate_search_parameters("query", 10, None)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_search_parameters_invalid_query(self):
        """测试无效查询参数"""
        from src.domains.chat.tools.task_search import validate_search_parameters

        # 测试空查询
        result = validate_search_parameters("", 50, None)

        assert result["valid"] is False
        assert "搜索查询不能为空" in result["errors"]

        result = validate_search_parameters(None, 50, None)

        assert result["valid"] is False

    def test_validate_search_parameters_invalid_limit(self):
        """测试无效limit参数"""
        from src.domains.chat.tools.task_search import validate_search_parameters

        # 测试负数limit
        result = validate_search_parameters("查询", -1, None)

        assert result["valid"] is False
        assert "限制数量必须大于0" in result["errors"]

        # 测试超过100的limit
        result = validate_search_parameters("查询", 101, None)

        assert result["valid"] is False
        assert "限制数量不能超过100" in result["errors"]

    def test_validate_search_parameters_invalid_state(self):
        """测试无效state参数"""
        from src.domains.chat.tools.task_search import validate_search_parameters

        result = validate_search_parameters("查询", 50, "invalid_state")

        assert result["valid"] is False
        assert any("状态筛选必须是以下之一" in error for error in result["errors"])

    def test_validate_search_parameters_multiple_errors(self):
        """测试多个参数错误"""
        from src.domains.chat.tools.task_search import validate_search_parameters

        result = validate_search_parameters("", -5, "invalid_state")

        assert result["valid"] is False
        assert len(result["errors"]) == 3  # query, limit, state都有错误


class TestSearchTasksIntegration:
    """集成测试：测试完整工作流程"""

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_full_workflow_success(self, mock_context):
        """测试完整工作流程成功场景"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 模拟真实任务数据
        mock_tasks = [
            {
                "id": "task-1",
                "title": "完成项目开发",
                "description": "使用Python和FastAPI完成RESTful API开发，包括用户认证、任务管理等功能模块",
                "status": "pending",
                "priority": "high",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 45.0
            },
            {
                "id": "task-2",
                "title": "编写技术文档",
                "description": "编写API接口文档和用户使用手册",
                "status": "completed",
                "priority": "medium",
                "created_at": "2024-12-24T15:20:00Z",
                "completion_percentage": 100.0
            }
        ]

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = mock_tasks

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 执行搜索
        result = _search_tasks_impl("开发相关任务", 10, "pending")
        result_data = json.loads(result)

        # 验证完整响应结构
        assert result_data["success"] is True
        assert result_data["query"] == "开发相关任务"
        # 模拟返回了所有任务，pending状态筛选在真实场景生效
        assert result_data["total"] == 2  # Mock返回了2个任务
        assert result_data["limit"] == 10
        assert result_data["state_filter"] == "pending"
        assert "estimated_tokens" in result_data
        assert "llm_hint" in result_data

        # 验证LLM提示内容
        llm_hint = result_data["llm_hint"]
        assert "开发相关任务" in llm_hint
        assert "找到2个任务" in llm_hint
        assert "根据用户意图分析任务匹配度" in llm_hint

        # 验证返回任务数据的完整性
        task = result_data["tasks"][0]
        required_fields = ["id", "title", "description", "status", "priority", "created_at", "completion_percentage"]
        for field in required_fields:
            assert field in task

        # 验证描述截断
        assert len(task["description"]) <= 103  # 长描述应该被截断

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_llm_hint_content_quality(self, mock_context):
        """测试LLM提示内容质量"""
        from src.domains.chat.tools.task_search import _search_tasks_impl

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = [
            {
                "id": "task-1",
                "title": "编程任务",
                "description": "Python开发",
                "status": "pending",
                "priority": "high",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": 0.0
            }
        ]

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        result = _search_tasks_impl("Python编程", 5, None)
        result_data = json.loads(result)

        llm_hint = result_data["llm_hint"]

        # 验证LLM提示包含关键指导信息
        assert "Python编程" in llm_hint
        assert "任务标题和描述的关键词匹配" in llm_hint
        assert "任务状态" in llm_hint
        assert "优先级" in llm_hint
        assert "完成百分比" in llm_hint
        assert "最相关的" in llm_hint


# 性能测试
class TestPerformance:
    """性能测试"""

    @patch('src.domains.chat.tools.task_search.get_task_service_context')
    def test_search_performance_with_large_dataset(self, mock_context):
        """测试大数据集搜索性能"""
        import time
        from src.domains.chat.tools.task_search import _search_tasks_impl

        # 创建大量模拟任务
        large_mock_tasks = []
        for i in range(1000):
            large_mock_tasks.append({
                "id": f"task-{i}",
                "title": f"任务 {i}",
                "description": f"任务描述 {i}",
                "status": "pending" if i % 2 == 0 else "completed",
                "priority": "medium",
                "created_at": "2024-12-25T10:30:00Z",
                "completion_percentage": float(i % 100)
            })

        mock_task_service = Mock()
        mock_task_service.get_tasks.return_value = large_mock_tasks

        mock_context.return_value.__enter__.return_value = {
            'task_service': mock_task_service
        }

        # 测试性能
        start_time = time.time()
        result = _search_tasks_impl("性能测试", 100, None)
        end_time = time.time()

        execution_time = end_time - start_time

        # 验证性能要求（应该在合理时间内完成）
        assert execution_time < 1.0, f"搜索耗时过长: {execution_time}秒"

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["tasks"]) == 100

    def test_token_estimation_performance(self):
        """测试Token估算性能"""
        import time
        from src.domains.chat.tools.task_search import estimate_token_count

        # 创建大文本
        large_text = "测试文本内容" * 1000

        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            estimate_token_count(large_text)

        end_time = time.time()
        avg_time = (end_time - start_time) / iterations

        assert avg_time < 0.001, f"Token估算平均时间过长: {avg_time}秒"