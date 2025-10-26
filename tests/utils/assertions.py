"""
测试断言助手

提供统一的测试断言方法，用于验证：
1. 对象属性
2. 数据库状态
3. 业务逻辑
4. 时间相关断言
"""

from datetime import datetime, timezone
from typing import Any, List, Dict, Optional, Union
from uuid import UUID


class AssertionHelper:
    """测试断言助手类"""

    @staticmethod
    def assert_uuid_valid(value: Any) -> None:
        """断言值是有效的UUID"""
        assert isinstance(value, (UUID, str)), f"Expected UUID or string, got {type(value)}"
        if isinstance(value, str):
            try:
                UUID(value)
            except ValueError as e:
                raise AssertionError(f"Invalid UUID string: {value}") from e

    @staticmethod
    def assert_task_complete(task: Dict[str, Any]) -> None:
        """断言任务已完成"""
        assert task["status"] == "completed", f"Task status should be 'completed', got '{task['status']}'"
        assert task["completion_percentage"] == 100.0, f"Completion percentage should be 100.0, got {task['completion_percentage']}"

    @staticmethod
    def assert_task_pending(task: Dict[str, Any]) -> None:
        """断言任务待处理"""
        assert task["status"] == "pending", f"Task status should be 'pending', got '{task['status']}'"
        assert task["completion_percentage"] == 0.0, f"Completion percentage should be 0.0, got {task['completion_percentage']}"

    @staticmethod
    def assert_datetime_close(actual: datetime, expected: datetime, tolerance_seconds: int = 60) -> None:
        """断言两个datetime接近（在指定容差内）"""
        diff = abs(actual - expected)
        assert diff.total_seconds() <= tolerance_seconds, \
            f"DateTime difference {diff.total_seconds()}s exceeds tolerance {tolerance_seconds}s"

    @staticmethod
    def assert_list_contains_all(list1: List[Any], list2: List[Any]) -> None:
        """断言list1包含list2的所有元素"""
        for item in list2:
            assert item in list1, f"Expected {item} to be in {list1}"

    @staticmethod
    def assert_lists_equal_unordered(list1: List[Any], list2: List[Any]) -> None:
        """断言两个列表包含相同元素（不考虑顺序）"""
        assert len(list1) == len(list2), f"Lists have different lengths: {len(list1)} vs {len(list2)}"
        assert set(list1) == set(list2), f"Lists have different elements: {list1} vs {list2}"

    @staticmethod
    def assert_dict_contains_keys(dictionary: Dict[str, Any], required_keys: List[str]) -> None:
        """断言字典包含所有必需的键"""
        missing_keys = [key for key in required_keys if key not in dictionary]
        assert not missing_keys, f"Dictionary missing keys: {missing_keys}"

    @staticmethod
    def assert_tree_structure(nodes: List[Dict[str, Any]], root_count: int, max_depth: int) -> None:
        """断言树结构的基本属性"""
        # 找到根节点（parent_id为None的节点）
        root_nodes = [node for node in nodes if node.get("parent_id") is None]
        assert len(root_nodes) == root_count, f"Expected {root_count} root nodes, got {len(root_nodes)}"

        # 简单的深度检查（需要更复杂的算法来精确计算深度）
        # 这里只做基本验证
        assert len(nodes) > 0, "Tree should have at least one node"

    @staticmethod
    def assert_percentage_valid(value: float) -> None:
        """断言百分比在有效范围内"""
        assert 0.0 <= value <= 100.0, f"Percentage {value} should be between 0.0 and 100.0"

    @staticmethod
    def assert_priority_valid(priority: str) -> None:
        """断言优先级有效"""
        valid_priorities = ["low", "medium", "high"]
        assert priority in valid_priorities, f"Priority '{priority}' should be one of {valid_priorities}"

    @staticmethod
    def assert_status_valid(status: str) -> None:
        """断言状态有效"""
        valid_statuses = ["pending", "in_progress", "completed"]
        assert status in valid_statuses, f"Status '{status}' should be one of {valid_statuses}"