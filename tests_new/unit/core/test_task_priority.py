"""
TaskPriority严格单元测试

测试TaskPriority枚举类型的所有功能，包括：
1. 基本构造和验证
2. Pydantic V2兼容性
3. 序列化/反序列化
4. JSON Schema生成
5. 类型安全检查
6. 错误处理

作者：TaTakeKe团队
版本：1.0.0 - TaskPriority类型严格测试
"""

import pytest
import json
from typing import Any
from pydantic import BaseModel, Field
from pydantic_core import core_schema

from src.core.types import TaskPriority, TaskStatus


class TestTaskPriorityBasics:
    """TaskPriority基础功能测试"""

    def test_init_valid_values(self):
        """测试有效值的初始化"""
        priority = TaskPriority("low")
        assert priority.value == "low"
        assert str(priority) == "low"

        priority = TaskPriority("medium")
        assert priority.value == "medium"
        assert str(priority) == "medium"

        priority = TaskPriority("high")
        assert priority.value == "high"
        assert str(priority) == "high"

    def test_init_invalid_value(self):
        """测试无效值的初始化"""
        with pytest.raises(ValueError) as exc_info:
            TaskPriority("invalid")

        assert "无效的任务优先级" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)
        assert "low" in str(exc_info.value)
        assert "medium" in str(exc_info.value)
        assert "high" in str(exc_info.value)

    def test_from_string_classmethod(self):
        """测试from_string类方法"""
        priority = TaskPriority.from_string("high")
        assert isinstance(priority, TaskPriority)
        assert priority.value == "high"

    def test_level_property(self):
        """测试优先级数值属性"""
        low = TaskPriority("low")
        medium = TaskPriority("medium")
        high = TaskPriority("high")

        assert low.level == 1
        assert medium.level == 2
        assert high.level == 3

    def test_is_higher_than_method(self):
        """测试优先级比较方法"""
        low = TaskPriority("low")
        medium = TaskPriority("medium")
        high = TaskPriority("high")

        assert high.is_higher_than(medium) is True
        assert high.is_higher_than(low) is True
        assert medium.is_higher_than(low) is True

        assert low.is_higher_than(medium) is False
        assert low.is_higher_than(high) is False
        assert medium.is_higher_than(high) is False

    def test_equality_and_hash(self):
        """测试相等性和哈希"""
        priority1 = TaskPriority("high")
        priority2 = TaskPriority("high")
        priority3 = TaskPriority("low")

        assert priority1 == priority2
        assert priority1 != priority3
        assert hash(priority1) == hash(priority2)
        assert hash(priority1) != hash(priority3)

    def test_allowed_values_constancy(self):
        """测试允许值的常量性"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"

        # 确保不允许修改
        with pytest.raises(AttributeError):
            TaskPriority.LOW = "modified"


class TestTaskPriorityPydanticCompatibility:
    """TaskPriority Pydantic V2兼容性测试"""

    def test_model_dump_method(self):
        """测试model_dump方法"""
        priority = TaskPriority("high")
        assert priority.model_dump() == "high"

        priority = TaskPriority("medium")
        assert priority.model_dump() == "medium"

    def test_model_dump_json_method(self):
        """测试model_dump_json方法"""
        priority = TaskPriority("high")
        json_str = priority.model_dump_json()
        assert json.loads(json_str) == "high"

        priority = TaskPriority("low")
        json_str = priority.model_dump_json()
        assert json.loads(json_str) == "low"

    def test_model_json_schema_classmethod(self):
        """测试model_json_schema类方法"""
        schema = TaskPriority.model_json_schema()

        assert isinstance(schema, dict)
        assert schema["title"] == "TaskPriority"
        assert schema["type"] == "string"
        assert set(schema["enum"]) == {"low", "medium", "high"}
        assert "description" in schema
        assert "任务优先级枚举" in schema["description"]

    def test_get_pydantic_core_schema_classmethod(self):
        """测试__get_pydantic_core_schema__类方法"""
        schema_func = TaskPriority.__get_pydantic_core_schema__(TaskPriority, None)
        assert callable(schema_func)

        # 测试生成的schema
        core_schema_result = schema_func()
        assert isinstance(core_schema_result, dict)
        assert "union" in core_schema_result

    def test_get_pydantic_json_schema_classmethod(self):
        """测试__get_pydantic_json_schema__类方法"""
        schema = TaskPriority.__get_pydantic_json_schema__(None, None)

        assert isinstance(schema, dict)
        assert schema["title"] == "TaskPriority"
        assert schema["type"] == "string"
        assert set(schema["enum"]) == {"low", "medium", "high"}


class TestTaskPriorityInPydanticModels:
    """TaskPriority在Pydantic模型中的使用测试"""

    def test_task_model_with_priority_field(self):
        """测试在Pydantic模型中使用TaskPriority"""
        class TaskModel(BaseModel):
            title: str
            priority: TaskPriority = Field(default=TaskPriority.MEDIUM)

        # 测试默认值
        task1 = TaskModel(title="Test Task")
        assert isinstance(task1.priority, TaskPriority)
        assert task1.priority.value == "medium"

        # 测试显式设置
        task2 = TaskModel(title="High Priority Task", priority=TaskPriority("high"))
        assert task2.priority.value == "high"

    def test_task_model_serialization(self):
        """测试包含TaskPriority的模型序列化"""
        class TaskModel(BaseModel):
            title: str
            priority: TaskPriority

        task = TaskModel(title="Test", priority=TaskPriority("high"))

        # 测试model_dump
        data = task.model_dump()
        assert data["priority"] == "high"

        # 测试model_dump_json
        json_str = task.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["priority"] == "high"

    def test_task_model_validation_with_string(self):
        """测试用字符串验证TaskPriority字段"""
        class TaskModel(BaseModel):
            title: str
            priority: TaskPriority

        # Pydantic应该能自动转换字符串
        task = TaskModel(title="Test", priority="low")
        assert isinstance(task.priority, TaskPriority)
        assert task.priority.value == "low"

    def test_task_model_validation_with_invalid_string(self):
        """测试用无效字符串验证TaskPriority字段"""
        class TaskModel(BaseModel):
            title: str
            priority: TaskPriority

        with pytest.raises(ValueError) as exc_info:
            TaskModel(title="Test", priority="invalid")

        assert "无效的任务优先级" in str(exc_info.value)


class TestTaskPriorityEdgeCases:
    """TaskPriority边界情况测试"""

    def test_case_sensitivity(self):
        """测试大小写敏感性"""
        # 应该是大小写敏感的
        with pytest.raises(ValueError):
            TaskPriority("LOW")
        with pytest.raises(ValueError):
            TaskPriority("Medium")
        with pytest.raises(ValueError):
            TaskPriority("HIGH")

    def test_whitespace_handling(self):
        """测试空白字符处理"""
        with pytest.raises(ValueError):
            TaskPriority(" low ")
        with pytest.raises(ValueError):
            TaskPriority("")
        with pytest.raises(ValueError):
            TaskPriority("  ")

    def test_immutability(self):
        """测试不可变性"""
        priority = TaskPriority("high")

        # _value属性应该是不可变的
        with pytest.raises(AttributeError):
            priority._value = "low"

    def test_string_representation_consistency(self):
        """测试字符串表示的一致性"""
        priorities = ["low", "medium", "high"]
        for value in priorities:
            priority = TaskPriority(value)
            assert str(priority) == value
            assert priority.value == value
            assert priority.model_dump() == value


class TestTaskPriorityComparisonAndLogic:
    """TaskPriority比较和逻辑测试"""

    def test_level_consistency(self):
        """测试优先级数值的一致性"""
        assert TaskPriority("low").level < TaskPriority("medium").level
        assert TaskPriority("medium").level < TaskPriority("high").level
        assert TaskPriority("high").level > TaskPriority("low").level

    def test_comparison_symmetry(self):
        """测试比较的对称性"""
        low = TaskPriority("low")
        high = TaskPriority("high")

        assert high.is_higher_than(low) is True
        assert low.is_higher_than(high) is False

    def test_comparison_with_self(self):
        """测试与自身的比较"""
        medium = TaskPriority("medium")
        assert medium.is_higher_than(medium) is False

    def test_all_allowed_values(self):
        """测试所有允许的值都能正确创建"""
        allowed_values = ["low", "medium", "high"]

        for value in allowed_values:
            priority = TaskPriority(value)
            assert priority.value == value
            assert str(priority) == value


class TestTaskPriorityConstants:
    """TaskPriority常量测试"""

    def test_constant_values(self):
        """测试常量值的正确性"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.MEDIUM == "medium"
        assert TaskPriority.HIGH == "high"

    def test_constant_immutability(self):
        """测试常量的不可变性"""
        # 常量应该是不可变的
        original_low = TaskPriority.LOW
        original_medium = TaskPriority.MEDIUM
        original_high = TaskPriority.HIGH

        # 尝试修改应该失败
        with pytest.raises(AttributeError):
            TaskPriority.LOW = "modified"

        # 验证值没有改变
        assert TaskPriority.LOW == original_low
        assert TaskPriority.MEDIUM == original_medium
        assert TaskPriority.HIGH == original_high


class TestTaskPriorityIntegration:
    """TaskPriority集成测试"""

    def test_collection_usage(self):
        """测试在集合中的使用"""
        priorities = [
            TaskPriority("low"),
            TaskPriority("medium"),
            TaskPriority("high")
        ]

        # 测试可以放入set
        priority_set = set(priorities)
        assert len(priority_set) == 3

        # 测试可以放入list
        priority_list = list(priorities)
        assert len(priority_list) == 3

        # 测试可以作为dict的key
        priority_dict = {p: f"level_{p.level}" for p in priorities}
        assert priority_dict[TaskPriority("high")] == "level_3"

    def test_json_serialization_roundtrip(self):
        """测试JSON序列化往返"""
        original = TaskPriority("high")

        # 序列化
        json_str = json.dumps(original.model_dump())

        # 反序列化
        value = json.loads(json_str)
        reconstructed = TaskPriority(value)

        assert original == reconstructed
        assert original.value == reconstructed.value

    def test_type_checking(self):
        """测试类型检查"""
        priority = TaskPriority("medium")

        assert isinstance(priority, TaskPriority)
        assert not isinstance(priority, str)
        assert not isinstance(priority, TaskStatus)

        # 但是可以被当作字符串使用
        assert str(priority) == "medium"
        assert priority.value == "medium"


@pytest.mark.performance
class TestTaskPriorityPerformance:
    """TaskPriority性能测试"""

    def test_creation_performance(self):
        """测试创建性能"""
        import time

        start_time = time.time()

        for _ in range(10000):
            TaskPriority("medium")

        duration = time.time() - start_time
        assert duration < 1.0, f"TaskPriority创建性能测试失败: {duration:.3f}s"

    def test_comparison_performance(self):
        """测试比较性能"""
        import time

        high = TaskPriority("high")
        low = TaskPriority("low")

        start_time = time.time()

        for _ in range(10000):
            high.is_higher_than(low)

        duration = time.time() - start_time
        assert duration < 1.0, f"TaskPriority比较性能测试失败: {duration:.3f}s"

    def test_serialization_performance(self):
        """测试序列化性能"""
        import time

        priority = TaskPriority("high")

        start_time = time.time()

        for _ in range(1000):
            priority.model_dump()
            priority.model_dump_json()

        duration = time.time() - start_time
        assert duration < 0.5, f"TaskPriority序列化性能测试失败: {duration:.3f}s"