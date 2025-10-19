"""
测试枚举类型定义
验证所有枚举类型的定义、值转换、比较和字符串表示功能
"""
import pytest
from enum import Enum

# 导入待实现的枚举类型
from src.models.enums import (
    TaskStatus,
    PriorityLevel,
    SessionType
)


class TestTaskStatus:
    """任务状态枚举测试类"""

    def test_task_status_enum_exists(self):
        """验证TaskStatus枚举存在且可导入"""
        assert TaskStatus is not None
        assert issubclass(TaskStatus, Enum)
        assert issubclass(TaskStatus, str)

    def test_task_status_values(self):
        """测试TaskStatus枚举值定义"""
        # 验证所有期望的枚举值存在
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.DELETED == "deleted"

    def test_task_status_enum_members(self):
        """测试TaskStatus枚举成员"""
        # 验证枚举成员数量
        assert len(TaskStatus) == 5

        # 验证枚举成员名称
        expected_names = ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", "DELETED"]
        actual_names = [member.name for member in TaskStatus]
        assert actual_names == expected_names

    def test_task_status_string_conversion(self):
        """测试TaskStatus字符串转换"""
        # 枚举值应该等于其字符串值
        assert str(TaskStatus.PENDING) == "pending"
        assert str(TaskStatus.IN_PROGRESS) == "in_progress"
        assert str(TaskStatus.COMPLETED) == "completed"
        assert str(TaskStatus.CANCELLED) == "cancelled"
        assert str(TaskStatus.DELETED) == "deleted"

    def test_task_status_value_access(self):
        """测试TaskStatus值访问"""
        # 通过.value访问
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"

        # 通过名称获取枚举
        assert TaskStatus["PENDING"] == TaskStatus.PENDING
        assert TaskStatus["COMPLETED"] == TaskStatus.COMPLETED

    def test_task_status_from_string(self):
        """测试从字符串创建TaskStatus"""
        # 通过值获取枚举
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("completed") == TaskStatus.COMPLETED

    def test_task_status_comparison(self):
        """测试TaskStatus比较操作"""
        # 枚举值比较
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.COMPLETED

        # 字符串比较
        assert TaskStatus.PENDING == "pending"
        assert "pending" == TaskStatus.PENDING

    def test_task_status_iteration(self):
        """测试TaskStatus迭代"""
        # 获取所有状态
        all_statuses = list(TaskStatus)
        assert len(all_statuses) == 5
        assert TaskStatus.PENDING in all_statuses
        assert TaskStatus.COMPLETED in all_statuses

    def test_task_status_ordering_consistency(self):
        """测试TaskStatus枚举值的顺序一致性"""
        # 验证枚举定义顺序
        status_list = list(TaskStatus)
        assert status_list[0] == TaskStatus.PENDING
        assert status_list[1] == TaskStatus.IN_PROGRESS
        assert status_list[2] == TaskStatus.COMPLETED
        assert status_list[3] == TaskStatus.CANCELLED
        assert status_list[4] == TaskStatus.DELETED

    def test_task_status_class_methods(self):
        """测试TaskStatus类方法"""
        # 测试get_active_statuses方法
        active_statuses = TaskStatus.get_active_statuses()
        assert TaskStatus.PENDING in active_statuses
        assert TaskStatus.IN_PROGRESS in active_statuses
        assert TaskStatus.COMPLETED in active_statuses
        assert TaskStatus.CANCELLED not in active_statuses
        assert TaskStatus.DELETED not in active_statuses

        # 测试get_completed_statuses方法
        completed_statuses = TaskStatus.get_completed_statuses()
        assert TaskStatus.COMPLETED in completed_statuses
        assert TaskStatus.CANCELLED in completed_statuses
        assert TaskStatus.PENDING not in completed_statuses

    def test_task_status_instance_methods(self):
        """测试TaskStatus实例方法"""
        # 测试is_active方法
        assert TaskStatus.PENDING.is_active() is True
        assert TaskStatus.IN_PROGRESS.is_active() is True
        assert TaskStatus.COMPLETED.is_active() is True
        assert TaskStatus.CANCELLED.is_active() is False
        assert TaskStatus.DELETED.is_active() is False

        # 测试is_completed方法
        assert TaskStatus.COMPLETED.is_completed() is True
        assert TaskStatus.CANCELLED.is_completed() is True
        assert TaskStatus.PENDING.is_completed() is False
        assert TaskStatus.IN_PROGRESS.is_completed() is False


class TestPriorityLevel:
    """优先级枚举测试类"""

    def test_priority_level_enum_exists(self):
        """验证PriorityLevel枚举存在且可导入"""
        assert PriorityLevel is not None
        assert issubclass(PriorityLevel, Enum)
        assert issubclass(PriorityLevel, str)

    def test_priority_level_values(self):
        """测试PriorityLevel枚举值定义"""
        assert PriorityLevel.LOW == "low"
        assert PriorityLevel.MEDIUM == "medium"
        assert PriorityLevel.HIGH == "high"

    def test_priority_level_enum_members(self):
        """测试PriorityLevel枚举成员"""
        assert len(PriorityLevel) == 3

        expected_names = ["LOW", "MEDIUM", "HIGH"]
        actual_names = [member.name for member in PriorityLevel]
        assert actual_names == expected_names

    def test_priority_level_string_conversion(self):
        """测试PriorityLevel字符串转换"""
        assert str(PriorityLevel.LOW) == "low"
        assert str(PriorityLevel.MEDIUM) == "medium"
        assert str(PriorityLevel.HIGH) == "high"

    def test_priority_level_comparison(self):
        """测试PriorityLevel比较操作"""
        assert PriorityLevel.LOW == PriorityLevel.LOW
        assert PriorityLevel.LOW != PriorityLevel.HIGH
        assert PriorityLevel.LOW == "low"

    def test_priority_level_from_string(self):
        """测试从字符串创建PriorityLevel"""
        assert PriorityLevel("low") == PriorityLevel.LOW
        assert PriorityLevel("high") == PriorityLevel.HIGH

    def test_priority_level_class_methods(self):
        """测试PriorityLevel类方法"""
        # 测试get_numeric_value方法
        assert PriorityLevel.get_numeric_value(PriorityLevel.LOW) == 1
        assert PriorityLevel.get_numeric_value(PriorityLevel.MEDIUM) == 2
        assert PriorityLevel.get_numeric_value(PriorityLevel.HIGH) == 3

        # 测试无效优先级的错误处理
        with pytest.raises(ValueError, match="无效的优先级"):
            PriorityLevel.get_numeric_value("invalid")

    def test_priority_level_instance_methods(self):
        """测试PriorityLevel实例方法"""
        # 测试is_higher_than方法
        assert PriorityLevel.HIGH.is_higher_than(PriorityLevel.MEDIUM) is True
        assert PriorityLevel.HIGH.is_higher_than(PriorityLevel.LOW) is True
        assert PriorityLevel.MEDIUM.is_higher_than(PriorityLevel.LOW) is True

        assert PriorityLevel.LOW.is_higher_than(PriorityLevel.MEDIUM) is False
        assert PriorityLevel.LOW.is_higher_than(PriorityLevel.HIGH) is False
        assert PriorityLevel.MEDIUM.is_higher_than(PriorityLevel.HIGH) is False

        # 测试相同优先级
        assert PriorityLevel.MEDIUM.is_higher_than(PriorityLevel.MEDIUM) is False


class TestSessionType:
    """会话类型枚举测试类"""

    def test_session_type_enum_exists(self):
        """验证SessionType枚举存在且可导入"""
        assert SessionType is not None
        assert issubclass(SessionType, Enum)
        assert issubclass(SessionType, str)

    def test_session_type_values(self):
        """测试SessionType枚举值定义"""
        assert SessionType.FOCUS == "focus"
        assert SessionType.BREAK == "break"
        assert SessionType.LONG_BREAK == "long_break"

    def test_session_type_enum_members(self):
        """测试SessionType枚举成员"""
        assert len(SessionType) == 3

        expected_names = ["FOCUS", "BREAK", "LONG_BREAK"]
        actual_names = [member.name for member in SessionType]
        assert actual_names == expected_names

    def test_session_type_string_conversion(self):
        """测试SessionType字符串转换"""
        assert str(SessionType.FOCUS) == "focus"
        assert str(SessionType.BREAK) == "break"
        assert str(SessionType.LONG_BREAK) == "long_break"

    def test_session_type_comparison(self):
        """测试SessionType比较操作"""
        assert SessionType.FOCUS == SessionType.FOCUS
        assert SessionType.FOCUS != SessionType.BREAK
        assert SessionType.FOCUS == "focus"

    def test_session_type_from_string(self):
        """测试从字符串创建SessionType"""
        assert SessionType("focus") == SessionType.FOCUS
        assert SessionType("long_break") == SessionType.LONG_BREAK

    def test_session_type_class_methods(self):
        """测试SessionType类方法"""
        # 测试get_default_duration方法
        assert SessionType.get_default_duration(SessionType.FOCUS) == 25
        assert SessionType.get_default_duration(SessionType.BREAK) == 5
        assert SessionType.get_default_duration(SessionType.LONG_BREAK) == 15

        # 测试无效会话类型的错误处理
        with pytest.raises(ValueError, match="无效的会话类型"):
            SessionType.get_default_duration("invalid")

    def test_session_type_instance_methods(self):
        """测试SessionType实例方法"""
        # 测试is_break_session方法
        assert SessionType.BREAK.is_break_session() is True
        assert SessionType.LONG_BREAK.is_break_session() is True
        assert SessionType.FOCUS.is_break_session() is False

        # 测试is_work_session方法
        assert SessionType.FOCUS.is_work_session() is True
        assert SessionType.BREAK.is_work_session() is False
        assert SessionType.LONG_BREAK.is_work_session() is False


class TestEnumIntegration:
    """枚举集成测试类"""

    def test_enums_are_distinct(self):
        """测试不同枚举类型之间是独立的"""
        # 确保不同枚举的值不会混淆
        assert TaskStatus.PENDING != PriorityLevel.LOW
        assert PriorityLevel.MEDIUM != SessionType.BREAK

    def test_enum_inheritance(self):
        """测试枚举继承结构"""
        # 所有枚举都继承自str和Enum
        for enum_class in [TaskStatus, PriorityLevel, SessionType]:
            assert issubclass(enum_class, str)
            assert issubclass(enum_class, Enum)

    def test_enum_serialization_compatibility(self):
        """测试枚举序列化兼容性"""
        # 枚举应该可以序列化为JSON兼容的字符串
        import json

        task_status = TaskStatus.COMPLETED
        priority = PriorityLevel.HIGH
        session_type = SessionType.FOCUS

        # 直接序列化枚举
        assert json.dumps(str(task_status)) == '"completed"'
        assert json.dumps(str(priority)) == '"high"'
        assert json.dumps(str(session_type)) == '"focus"'

        # 在字典中序列化
        data = {
            "status": task_status,
            "priority": priority,
            "session_type": session_type
        }
        json_str = json.dumps({k: str(v) for k, v in data.items()})
        parsed = json.loads(json_str)

        assert parsed["status"] == "completed"
        assert parsed["priority"] == "high"
        assert parsed["session_type"] == "focus"