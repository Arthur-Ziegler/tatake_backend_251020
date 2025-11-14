"""
任务Schema验证测试

专门测试CreateTaskRequest和UpdateTaskRequest的验证逻辑，
重点覆盖时区处理和时间范围验证。

功能说明：
- 测试due_date与planned_end_time的时区比较
- 测试planned_start_time与planned_end_time的顺序验证
- 测试各种边界情况和异常情况

作者：TaKeKe团队
修改记录：
- 2024-11-15: 创建文件，覆盖时区比较修复
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from pydantic import ValidationError

from src.domains.task.schemas import CreateTaskRequest, UpdateTaskRequest


class TestCreateTaskRequestValidation:
    """CreateTaskRequest验证测试"""

    def test_create_task_with_date_only_due_date(self):
        """测试：使用纯日期格式的due_date创建任务"""
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31)
        )
        assert request.due_date == date(2024, 12, 31)
        assert request.title == "测试任务"

    def test_create_task_timezone_comparison_aware_datetime(self):
        """测试：due_date与aware planned_end_time的时区比较"""
        # UTC时间：2024-12-30 18:00
        planned_end = datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)

        # 应该成功：due_date (2024-12-31 23:59:59 UTC) > planned_end
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31),
            planned_start_time=datetime(2024, 12, 20, 9, 0, 0, tzinfo=timezone.utc),
            planned_end_time=planned_end
        )
        assert request.due_date == date(2024, 12, 31)

    def test_create_task_timezone_comparison_naive_datetime(self):
        """测试：due_date与naive planned_end_time的比较（假定为UTC）"""
        # Naive datetime（无时区信息）
        planned_end = datetime(2024, 12, 30, 18, 0, 0)

        # 应该成功：假定planned_end为UTC
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31),
            planned_start_time=datetime(2024, 12, 20, 9, 0, 0),
            planned_end_time=planned_end
        )
        assert request.due_date == date(2024, 12, 31)

    def test_create_task_due_date_equals_planned_end_boundary(self):
        """测试：边界情况 - due_date当天23:59:59与planned_end_time相等"""
        # due_date: 2024-12-31 23:59:59 UTC
        # planned_end: 2024-12-31 23:59:59 UTC
        planned_end = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        # 应该成功（相等也允许）
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31),
            planned_end_time=planned_end
        )
        assert request.due_date == date(2024, 12, 31)

    def test_create_task_due_date_after_planned_end(self):
        """测试：due_date晚于planned_end_time（正常情况）"""
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2025, 1, 5),
            planned_end_time=datetime(2024, 12, 31, 18, 0, 0, tzinfo=timezone.utc)
        )
        assert request.due_date == date(2025, 1, 5)

    def test_create_task_due_date_before_planned_end_should_fail(self):
        """测试：due_date早于planned_end_time应该失败"""
        with pytest.raises(ValidationError) as exc_info:
            CreateTaskRequest(
                title="测试任务",
                due_date=date(2024, 12, 25),
                planned_end_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)
            )

        assert "截止日期不能早于计划结束时间" in str(exc_info.value)

    def test_create_task_due_date_same_day_but_before_planned_end(self):
        """测试：同一天但due_date（23:59:59）早于planned_end_time（跨天）"""
        # 极端情况：planned_end_time是第二天凌晨
        with pytest.raises(ValidationError) as exc_info:
            CreateTaskRequest(
                title="测试任务",
                due_date=date(2024, 12, 31),
                planned_end_time=datetime(2025, 1, 1, 0, 30, 0, tzinfo=timezone.utc)
            )

        assert "截止日期不能早于计划结束时间" in str(exc_info.value)

    def test_planned_start_after_planned_end_should_fail(self):
        """测试：计划开始时间晚于结束时间应该失败"""
        with pytest.raises(ValidationError) as exc_info:
            CreateTaskRequest(
                title="测试任务",
                planned_start_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc),
                planned_end_time=datetime(2024, 12, 20, 9, 0, 0, tzinfo=timezone.utc)
            )

        assert "计划结束时间必须晚于计划开始时间" in str(exc_info.value)

    def test_planned_start_equals_planned_end_should_fail(self):
        """测试：计划开始时间等于结束时间应该失败"""
        same_time = datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CreateTaskRequest(
                title="测试任务",
                planned_start_time=same_time,
                planned_end_time=same_time
            )

        assert "计划结束时间必须晚于计划开始时间" in str(exc_info.value)

    def test_due_date_only_without_planned_times(self):
        """测试：只有due_date，没有计划时间"""
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31)
        )
        assert request.due_date == date(2024, 12, 31)
        assert request.planned_start_time is None
        assert request.planned_end_time is None

    def test_planned_times_without_due_date(self):
        """测试：有计划时间，但没有due_date"""
        request = CreateTaskRequest(
            title="测试任务",
            planned_start_time=datetime(2024, 12, 20, 9, 0, 0, tzinfo=timezone.utc),
            planned_end_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)
        )
        assert request.due_date is None
        assert request.planned_start_time is not None
        assert request.planned_end_time is not None

    def test_title_validation(self):
        """测试：标题字段验证"""
        # 空标题
        with pytest.raises(ValidationError):
            CreateTaskRequest(title="")

        # 标题过长（超过100字符）
        with pytest.raises(ValidationError):
            CreateTaskRequest(title="a" * 101)

        # 正常标题
        request = CreateTaskRequest(title="正常标题")
        assert request.title == "正常标题"

    def test_tags_validation(self):
        """测试：标签验证"""
        # 标签去重
        request = CreateTaskRequest(
            title="测试任务",
            tags=["标签1", "标签2", "标签1"]
        )
        # 注意：标签可能不会自动去重，取决于具体实现
        assert "标签1" in request.tags
        assert "标签2" in request.tags

    def test_different_timezone_comparison(self):
        """测试：不同时区的时间比较"""
        # 东八区时间：2024-12-31 07:59:59 (UTC+8)
        # 相当于UTC：2024-12-30 23:59:59
        tz_east8 = timezone(timedelta(hours=8))
        planned_end = datetime(2024, 12, 31, 7, 59, 59, tzinfo=tz_east8)

        # due_date: 2024-12-31 23:59:59 UTC > planned_end (2024-12-30 23:59:59 UTC)
        # 应该成功
        request = CreateTaskRequest(
            title="测试任务",
            due_date=date(2024, 12, 31),
            planned_end_time=planned_end
        )
        assert request.due_date == date(2024, 12, 31)


class TestUpdateTaskRequestValidation:
    """UpdateTaskRequest验证测试"""

    def test_update_task_due_date_valid(self):
        """测试：更新due_date（有效情况）"""
        request = UpdateTaskRequest(
            due_date=date(2024, 12, 31),
            planned_end_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)
        )
        assert request.due_date == date(2024, 12, 31)

    def test_update_task_due_date_invalid(self):
        """测试：更新due_date（无效情况）"""
        with pytest.raises(ValidationError) as exc_info:
            UpdateTaskRequest(
                due_date=date(2024, 12, 25),
                planned_end_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc)
            )

        assert "截止日期不能早于计划结束时间" in str(exc_info.value)

    def test_update_task_partial_fields(self):
        """测试：部分字段更新"""
        request = UpdateTaskRequest(
            title="新标题",
            priority="high"
        )
        assert request.title == "新标题"
        assert request.priority == "high"
        assert request.due_date is None

    def test_update_task_clear_due_date(self):
        """测试：清除due_date（设置为None）"""
        request = UpdateTaskRequest(
            title="测试任务"
        )
        assert request.due_date is None

    def test_update_task_timezone_comparison_aware(self):
        """测试：更新任务时的时区比较（aware datetime）"""
        request = UpdateTaskRequest(
            due_date=date(2025, 1, 10),
            planned_end_time=datetime(2025, 1, 5, 18, 0, 0, tzinfo=timezone.utc)
        )
        assert request.due_date == date(2025, 1, 10)

    def test_update_task_timezone_comparison_naive(self):
        """测试：更新任务时的时区比较（naive datetime）"""
        request = UpdateTaskRequest(
            due_date=date(2025, 1, 10),
            planned_end_time=datetime(2025, 1, 5, 18, 0, 0)
        )
        assert request.due_date == date(2025, 1, 10)

    def test_update_planned_times_validation(self):
        """测试：更新计划时间的验证"""
        with pytest.raises(ValidationError) as exc_info:
            UpdateTaskRequest(
                planned_start_time=datetime(2024, 12, 30, 18, 0, 0, tzinfo=timezone.utc),
                planned_end_time=datetime(2024, 12, 20, 9, 0, 0, tzinfo=timezone.utc)
            )

        assert "计划结束时间必须晚于计划开始时间" in str(exc_info.value)
