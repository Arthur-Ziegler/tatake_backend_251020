"""
零Bug测试体系 - 类型系统测试

测试严格类型系统的正确性，每个测试都是一个用例文档。

测试原则：
1. 测试即文档：每个测试都描述一个具体的用例
2. 边界全覆盖：测试所有边界条件和异常情况
3. 确定性验证：确保类型系统的严格性和一致性
"""

import pytest
from datetime import datetime, timezone
from src.core.types import (
    TaskTitle, TaskDescription, TaskStatus, TaskPriority, Percentage,
    UserId, TaskId, WeChatOpenId, EmailAddress, UTCDateTime,
    IdGenerator, TypeValidator
)


class TestTaskTitle:
    """任务标题测试 - 验证标题的严格约束"""

    def test_create_valid_title_should_succeed(self):
        """
        用例：创建有效的任务标题
        条件：标题长度在1-100字符之间
        期望：创建成功，返回TaskTitle对象
        验证：标题值正确去除首尾空格
        """
        # Given - 有效的标题
        title_text = "  完成项目开发  "

        # When - 创建TaskTitle
        title = TaskTitle(title_text)

        # Then - 验证结果
        assert str(title) == "完成项目开发"
        assert title.value == "完成项目开发"
        assert title.min_length == 1
        assert title.max_length == 100

    def test_create_empty_title_should_fail(self):
        """
        用例：创建空标题
        条件：标题为空字符串
        期望：抛出ValueError
        验证：错误消息明确指出长度不足
        """
        # Given - 空标题
        title_text = ""

        # When & Then - 应该抛出异常
        with pytest.raises(ValueError, match="长度不能少于 1 字符"):
            TaskTitle(title_text)

    def test_create_whitespace_only_title_should_fail(self):
        """
        用例：创建只有空格的标题
        条件：标题只包含空格
        期望：抛出ValueError
        验证：空格被去除后仍然为空
        """
        # Given - 只有空格的标题
        title_text = "   "

        # When & Then - 应该抛出异常
        with pytest.raises(ValueError, match="长度不能少于 1 字符"):
            TaskTitle(title_text)

    def test_create_too_long_title_should_fail(self):
        """
        用例：创建超长标题
        条件：标题长度超过100字符
        期望：抛出ValueError
        验证：错误消息指明长度限制
        """
        # Given - 超长标题（101字符）
        title_text = "a" * 101

        # When & Then - 应该抛出异常
        with pytest.raises(ValueError, match="长度不能超过 100 字符"):
            TaskTitle(title_text)

    def test_create_non_string_title_should_fail(self):
        """
        用例：创建非字符串类型标题
        条件：标题为非字符串类型
        期望：抛出TypeError
        验证：错误消息指明类型错误
        """
        # Given - 非字符串标题
        invalid_titles = [123, None, [], {}, True]

        # When & Then - 每个都应该抛出异常
        for invalid_title in invalid_titles:
            with pytest.raises(TypeError, match="必须是字符串"):
                TaskTitle(invalid_title)

    def test_title_edge_cases(self):
        """
        用例：标题边界情况测试
        条件：测试各种边界情况
        期望：符合预期的行为
        验证：边界条件正确处理
        """
        # 1字符标题（最小边界）
        title_1_char = TaskTitle("a")
        assert str(title_1_char) == "a"

        # 100字符标题（最大边界）
        title_100_char = TaskTitle("a" * 100)
        assert len(str(title_100_char)) == 100

        # 包含特殊字符
        title_special = TaskTitle("项目开发！@#￥%……&*（）")
        assert "项目开发" in str(title_special)

        # 包含中文字符
        title_chinese = TaskTitle("完成项目开发")
        assert "项目开发" in str(title_chinese)


class TestTaskDescription:
    """任务描述测试 - 验证描述的灵活约束"""

    def test_create_valid_description_should_succeed(self):
        """
        用例：创建有效的任务描述
        条件：描述长度在0-1000字符之间
        期望：创建成功，返回TaskDescription对象
        验证：描述值正确去除首尾空格
        """
        # Given - 有效的描述
        description_text = "  这是项目的详细描述  "

        # When - 创建TaskDescription
        description = TaskDescription(description_text)

        # Then - 验证结果
        assert str(description) == "这是项目的详细描述"
        assert description.min_length == 0
        assert description.max_length == 1000

    def test_create_empty_description_should_succeed(self):
        """
        用例：创建空描述
        条件：描述为空或None
        期望：创建成功，允许空描述
        验证：空描述被正确处理
        """
        # Given - 空描述
        description = TaskDescription("")
        assert str(description) == ""

        # Given - None描述
        description_none = TaskDescription(None)
        assert str(description_none) == ""

    def test_create_max_length_description_should_succeed(self):
        """
        用例：创建最大长度描述
        条件：描述长度为1000字符
        期望：创建成功
        验证：最大边界正确处理
        """
        # Given - 最大长度描述
        description_text = "a" * 1000

        # When - 创建描述
        description = TaskDescription(description_text)

        # Then - 验证结果
        assert len(str(description)) == 1000

    def test_create_too_long_description_should_fail(self):
        """
        用例：创建超长描述
        条件：描述长度超过1000字符
        期望：抛出ValueError
        验证：长度限制严格执行
        """
        # Given - 超长描述
        description_text = "a" * 1001

        # When & Then - 应该抛出异常
        with pytest.raises(ValueError, match="长度不能超过 1000 字符"):
            TaskDescription(description_text)


class TestTaskStatus:
    """任务状态测试 - 验证状态枚举和转换规则"""

    def test_create_valid_status_should_succeed(self):
        """
        用例：创建有效的任务状态
        条件：使用预定义的状态值
        期望：创建成功，返回TaskStatus对象
        验证：状态值正确设置
        """
        # Given & When - 创建各种状态
        pending = TaskStatus(TaskStatus.PENDING)
        in_progress = TaskStatus(TaskStatus.IN_PROGRESS)
        completed = TaskStatus(TaskStatus.COMPLETED)

        # Then - 验证结果
        assert str(pending) == TaskStatus.PENDING
        assert str(in_progress) == TaskStatus.IN_PROGRESS
        assert str(completed) == TaskStatus.COMPLETED

    def test_create_invalid_status_should_fail(self):
        """
        用例：创建无效的任务状态
        条件：使用未定义的状态值
        期望：抛出ValueError
        验证：只允许预定义的状态值
        """
        # Given - 无效状态
        invalid_statuses = ["invalid", "pending ", "", None, 123]

        # When & Then - 每个都应该抛出异常
        for invalid_status in invalid_statuses:
            with pytest.raises(ValueError, match="无效的任务状态"):
                TaskStatus(invalid_status)

    def test_status_transition_validation(self):
        """
        用例：状态转换验证
        条件：测试各种状态转换
        期望：只有合法的转换才被允许
        验证：状态转换规则正确执行
        """
        # Given - 各种状态
        pending = TaskStatus(TaskStatus.PENDING)
        in_progress = TaskStatus(TaskStatus.IN_PROGRESS)
        completed = TaskStatus(TaskStatus.COMPLETED)

        # Then - 验证合法转换
        assert pending.can_transition_to(in_progress) is True
        assert pending.can_transition_to(completed) is True
        assert in_progress.can_transition_to(completed) is True
        assert in_progress.can_transition_to(pending) is True
        assert completed.can_transition_to(pending) is True

        # 验证非法转换
        assert completed.can_transition_to(in_progress) is False

    def test_status_from_string(self):
        """
        用例：从字符串创建状态
        条件：使用字符串创建状态
        期望：正确创建对应的状态对象
        验证：工厂方法正确工作
        """
        # Given & When - 从字符串创建状态
        pending = TaskStatus.from_string("pending")
        completed = TaskStatus.from_string("completed")

        # Then - 验证结果
        assert str(pending) == "pending"
        assert str(completed) == "completed"


class TestTaskPriority:
    """任务优先级测试 - 验证优先级枚举和比较"""

    def test_create_valid_priority_should_succeed(self):
        """
        用例：创建有效的任务优先级
        条件：使用预定义的优先级值
        期望：创建成功，返回TaskPriority对象
        验证：优先级值和等级正确
        """
        # Given & When - 创建各种优先级
        low = TaskPriority(TaskPriority.LOW)
        medium = TaskPriority(TaskPriority.MEDIUM)
        high = TaskPriority(TaskPriority.HIGH)

        # Then - 验证结果
        assert str(low) == TaskPriority.LOW
        assert str(medium) == TaskPriority.MEDIUM
        assert str(high) == TaskPriority.HIGH

        # 验证优先级等级
        assert low.level == 1
        assert medium.level == 2
        assert high.level == 3

    def test_priority_comparison(self):
        """
        用例：优先级比较
        条件：比较不同优先级
        期望：正确比较优先级高低
        验证：比较逻辑正确
        """
        # Given - 不同优先级
        low = TaskPriority(TaskPriority.LOW)
        medium = TaskPriority(TaskPriority.MEDIUM)
        high = TaskPriority(TaskPriority.HIGH)

        # Then - 验证比较结果
        assert high.is_higher_than(medium) is True
        assert high.is_higher_than(low) is True
        assert medium.is_higher_than(low) is True

        assert low.is_higher_than(medium) is False
        assert low.is_higher_than(high) is False
        assert medium.is_higher_than(high) is False


class TestPercentage:
    """百分比测试 - 验证百分比数值约束"""

    def test_create_valid_percentage_should_succeed(self):
        """
        用例：创建有效的百分比
        条件：百分比值在0.0-100.0之间
        期望：创建成功，返回Percentage对象
        验证：值被正确标准化为两位小数
        """
        # Given & When - 创建各种百分比
        zero = Percentage(0.0)
        half = Percentage(50.0)
        complete = Percentage(100.0)
        decimal = Percentage(33.333)

        # Then - 验证结果
        assert str(zero) == "0.0%"
        assert str(half) == "50.0%"
        assert str(complete) == "100.0%"
        assert str(decimal) == "33.33%"  # 四舍五入到两位小数

    def test_create_negative_percentage_should_fail(self):
        """
        用例：创建负百分比
        条件：百分比值小于0
        期望：抛出ValueError
        验证：负值被严格禁止
        """
        # Given - 负百分比
        negative_values = [-1.0, -0.1, -100.0]

        # When & Then - 每个都应该抛出异常
        for value in negative_values:
            with pytest.raises(ValueError, match="百分比必须在 0.0-100.0 之间"):
                Percentage(value)

    def test_create_over_100_percentage_should_fail(self):
        """
        用例：创建超过100%的百分比
        条件：百分比值大于100
        期望：抛出ValueError
        验证：超过100%被严格禁止
        """
        # Given - 超大百分比
        over_values = [100.1, 101.0, 200.0]

        # When & Then - 每个都应该抛出异常
        for value in over_values:
            with pytest.raises(ValueError, match="百分比必须在 0.0-100.0 之间"):
                Percentage(value)

    def test_create_non_numeric_percentage_should_fail(self):
        """
        用例：创建非数字百分比
        条件：百分比值不是数字类型
        期望：抛出TypeError
        验证：类型检查严格执行
        """
        # Given - 非数字值
        invalid_values = ["50", None, [], {}, True]

        # When & Then - 每个都应该抛出异常
        for value in invalid_values:
            with pytest.raises(TypeError, match="百分比必须是数字"):
                Percentage(value)

    def test_percentage_helper_methods(self):
        """
        用例：百分比辅助方法
        条件：使用工厂方法和判断方法
        期望：正确创建和判断百分比
        验证：辅助方法正确工作
        """
        # Given & When - 使用工厂方法
        zero = Percentage.zero()
        complete = Percentage.complete()

        # Then - 验证结果
        assert str(zero) == "0.0%"
        assert str(complete) == "100.0%"
        assert zero.is_complete() is False
        assert complete.is_complete() is True

        # Given - 接近100%的值
        almost_complete = Percentage(99.99)
        # Then - 验证判断
        assert almost_complete.is_complete() is False


class TestIdGenerator:
    """ID生成器测试 - 验证ID生成和解析"""

    def test_generate_user_id_should_succeed(self):
        """
        用例：生成用户ID
        条件：调用用户ID生成器
        期望：生成符合格式的用户ID
        验证：ID格式和唯一性
        """
        # When - 生成用户ID
        user_id = IdGenerator.generate_user_id()

        # Then - 验证格式
        assert isinstance(user_id, UserId)
        assert str(user_id).startswith("user_")
        assert len(str(user_id)) == 4 + 32  # "user_" + 32字符UUID

    def test_generate_task_id_should_succeed(self):
        """
        用例：生成任务ID
        条件：调用任务ID生成器
        期望：生成符合格式的任务ID
        验证：ID格式和唯一性
        """
        # When - 生成任务ID
        task_id = IdGenerator.generate_task_id()

        # Then - 验证格式
        assert isinstance(task_id, TaskId)
        assert str(task_id).startswith("task_")
        assert len(str(task_id)) == 4 + 32

    def test_generate_multiple_ids_should_be_unique(self):
        """
        用例：生成多个ID
        条件：连续生成多个ID
        期望：所有ID都是唯一的
        验证：唯一性保证
        """
        # When - 生成多个ID
        user_ids = [IdGenerator.generate_user_id() for _ in range(10)]
        task_ids = [IdGenerator.generate_task_id() for _ in range(10)]

        # Then - 验证唯一性
        assert len(set(str(uid) for uid in user_ids)) == 10
        assert len(set(str(tid) for tid in task_ids)) == 10

    def test_parse_valid_id_should_succeed(self):
        """
        用例：解析有效ID
        条件：提供格式正确的ID
        期望：解析成功，返回原ID
        验证：解析逻辑正确
        """
        # Given - 有效ID
        valid_user_id = "user_1234567890abcdef1234567890abcdef"
        valid_task_id = "task_1234567890abcdef1234567890abcdef"

        # When - 解析ID
        parsed_user_id = IdGenerator.parse_id(valid_user_id, "user")
        parsed_task_id = IdGenerator.parse_id(valid_task_id, "task")

        # Then - 验证结果
        assert parsed_user_id == valid_user_id
        assert parsed_task_id == valid_task_id

    def test_parse_invalid_id_should_fail(self):
        """
        用例：解析无效ID
        条件：提供格式错误的ID
        期望：抛出ValueError
        验证：格式验证严格执行
        """
        # Given - 各种无效ID
        invalid_ids = [
            "invalid_prefix_1234567890abcdef1234567890abcdef",  # 错误前缀
            "user_1234567890abcdef1234567890abcde",             # UUID太短
            "user_1234567890abcdef1234567890abcdef123",         # UUID太长
            "user_1234567890abcdef1234567890abcdeg",            # 无效UUID字符
            "user_",                                            # 缺少UUID
        ]

        # When & Then - 每个都应该抛出异常
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError):
                IdGenerator.parse_id(invalid_id, "user")


class TestTypeValidator:
    """类型验证器测试 - 验证类型验证功能"""

    def test_validate_task_title_should_succeed(self):
        """
        用例：验证任务标题
        条件：提供有效的标题
        期望：验证成功，返回TaskTitle对象
        验证：验证器正确工作
        """
        # Given - 有效标题
        title_text = "完成项目开发"

        # When - 验证标题
        title = TypeValidator.validate_task_title(title_text)

        # Then - 验证结果
        assert isinstance(title, TaskTitle)
        assert str(title) == title_text

    def test_validate_invalid_task_title_should_fail(self):
        """
        用例：验证无效任务标题
        条件：提供无效的标题
        期望：抛出异常
        验证：验证器正确拒绝无效输入
        """
        # Given - 无效标题
        invalid_titles = ["", "a" * 101, None]

        # When & Then - 每个都应该抛出异常
        for invalid_title in invalid_titles:
            with pytest.raises((ValueError, TypeError)):
                TypeValidator.validate_task_title(invalid_title)

    def test_validate_task_status_should_succeed(self):
        """
        用例：验证任务状态
        条件：提供有效的状态
        期望：验证成功，返回TaskStatus对象
        验证：状态验证正确
        """
        # Given - 有效状态
        status_text = "in_progress"

        # When - 验证状态
        status = TypeValidator.validate_task_status(status_text)

        # Then - 验证结果
        assert isinstance(status, TaskStatus)
        assert str(status) == status_text

    def test_validate_percentage_should_succeed(self):
        """
        用例：验证百分比
        条件：提供有效的百分比数值
        期望：验证成功，返回Percentage对象
        验证：百分比验证正确
        """
        # Given - 有效百分比
        percentage_value = 75.5

        # When - 验证百分比
        percentage = TypeValidator.validate_percentage(percentage_value)

        # Then - 验证结果
        assert isinstance(percentage, Percentage)
        assert str(percentage) == "75.5%"


class TestUTCDateTime:
    """UTC时间测试 - 验证时间类型的安全约束"""

    def test_create_utc_datetime_should_succeed(self):
        """
        用例：创建UTC时间
        条件：提供UTC时间
        期望：创建成功，返回UTCDateTime对象
        验证：时间正确转换为UTC
        """
        # Given - UTC时间
        utc_time = datetime(2023, 10, 24, 15, 30, 0, tzinfo=timezone.utc)

        # When - 创建UTCDateTime
        utc_datetime = UTCDateTime(utc_time)

        # Then - 验证结果
        assert utc_datetime.value == utc_time
        assert str(utc_datetime) == utc_time.isoformat()

    def test_create_non_utc_datetime_should_convert(self):
        """
        用例：创建非UTC时间
        条件：提供其他时区的时间
        期望：自动转换为UTC时间
        验证：时区转换正确
        """
        # Given - 东八区时间
        from datetime import timezone, timedelta
        cst = timezone(timedelta(hours=8))
        local_time = datetime(2023, 10, 24, 23, 30, 0, tzinfo=cst)

        # When - 创建UTCDateTime
        utc_datetime = UTCDateTime(local_time)

        # Then - 验证转换为UTC
        assert utc_datetime.value.hour == 15  # 23:30 CST = 15:30 UTC

    def test_create_datetime_without_timezone_should_fail(self):
        """
        用例：创建无时区时间
        条件：提供没有时区信息的时间
        期望：抛出TypeError
        验证：时区信息必须提供
        """
        # Given - 无时区时间
        naive_time = datetime(2023, 10, 24, 15, 30, 0)

        # When & Then - 应该抛出异常
        with pytest.raises(TypeError, match="时间必须包含时区信息"):
            UTCDateTime(naive_time)

    def test_utc_datetime_now(self):
        """
        用例：获取当前UTC时间
        条件：调用now()方法
        期望：返回当前UTC时间
        验证：时间格式正确
        """
        # When - 获取当前时间
        now = UTCDateTime.now()

        # Then - 验证结果
        assert isinstance(now, UTCDateTime)
        assert now.value.tzinfo == timezone.utc
        assert now.is_future() is False  # 刚创建的时间不应该是未来时间

    def test_utc_datetime_from_string(self):
        """
        用例：从字符串创建时间
        条件：提供ISO格式的时间字符串
        期望：正确解析为UTCDateTime对象
        验证：字符串解析正确
        """
        # Given - ISO格式字符串
        iso_string = "2023-10-24T15:30:00+00:00"

        # When - 从字符串创建
        utc_datetime = UTCDateTime.from_string(iso_string)

        # Then - 验证结果
        assert isinstance(utc_datetime, UTCDateTime)
        assert utc_datetime.value.year == 2023
        assert utc_datetime.value.month == 10
        assert utc_datetime.value.day == 24