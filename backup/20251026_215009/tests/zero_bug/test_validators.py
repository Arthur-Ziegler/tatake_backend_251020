"""
零Bug测试体系 - 验证器系统测试

测试验证器系统的正确性，确保业务规则验证的严格性。

测试原则：
1. 规则即测试：每个业务规则都有对应测试
2. 错误即文档：每个错误消息都明确指导修复
3. 边界即安全：所有边界条件都有保护
4. 组合即复杂：验证器组合正确工作
"""

import pytest
from datetime import datetime, timezone
from src.core.types import (
    TaskTitle, TaskDescription, TaskStatus, TaskPriority, Percentage,
    UserId, TaskId
)
from src.core.validators import (
    ValidationError, BusinessRuleViolationError, DataConsistencyError,
    RequiredValidator, TypeValidator, RangeValidator, RegexValidator,
    TaskTitleValidator, TaskStatusValidator, TaskStatusTransitionValidator,
    TaskPriorityValidator, TaskCompletionValidator,
    CompositeValidator, ConditionalValidator,
    ValidatorFactory
)


class TestValidationError:
    """验证错误测试 - 验证错误处理机制"""

    def test_validation_error_creation(self):
        """
        用例：创建验证错误
        条件：提供错误消息和字段信息
        期望：正确创建ValidationError对象
        验证：错误信息完整且格式正确
        """
        # Given - 错误信息
        message = "标题不能为空"
        field = "任务标题"
        value = ""

        # When - 创建错误
        error = ValidationError(message, field, value)

        # Then - 验证错误对象
        assert error.message == message
        assert error.field == field
        assert error.value == value
        assert str(error) == f"{field}: {message}"

    def test_validation_error_without_field(self):
        """
        用例：创建无字段验证错误
        条件：只提供错误消息
        期望：正确创建ValidationError对象
        验证：错误消息正确显示
        """
        # Given - 只有错误消息
        message = "通用验证错误"

        # When - 创建错误
        error = ValidationError(message)

        # Then - 验证错误对象
        assert error.message == message
        assert error.field is None
        assert str(error) == message

    def test_business_rule_violation_error(self):
        """
        用例：创建业务规则违反错误
        条件：违反特定业务规则
        期望：创建BusinessRuleViolationError
        验证：继承关系和类型正确
        """
        # Given - 业务规则错误
        message = "已完成的任务不能删除"

        # When - 创建错误
        error = BusinessRuleViolationError(message, "任务状态", "completed")

        # Then - 验证错误类型
        assert isinstance(error, ValidationError)
        assert isinstance(error, BusinessRuleViolationError)
        assert str(error) == "任务状态: 已完成的任务不能删除"


class TestRequiredValidator:
    """必填验证器测试"""

    def test_validate_non_empty_value_should_succeed(self):
        """
        用例：验证非空值
        条件：提供非空值
        期望：验证通过，返回原值
        验证：非空值正确处理
        """
        # Given - 非空值
        validator = RequiredValidator("测试字段")
        valid_values = ["text", 123, True, [], {}]

        # When & Then - 验证所有非空值
        for value in valid_values:
            result = validator.validate(value)
            assert result == value

    def test_validate_none_should_fail(self):
        """
        用例：验证None值
        条件：值为None
        期望：抛出ValidationError
        验证：None值被正确拒绝
        """
        # Given - None值
        validator = RequiredValidator("必填字段")

        # When & Then - 应该抛出异常
        with pytest.raises(ValidationError, match="必填字段是必填的"):
            validator.validate(None)

    def test_validate_empty_string_should_fail(self):
        """
        用例：验证空字符串
        条件：值为空字符串或只有空格
        期望：抛出ValidationError
        验证：空字符串被正确拒绝
        """
        # Given - 空字符串
        validator = RequiredValidator("字符串字段")
        empty_values = ["", "   ", "\t", "\n"]

        # When & Then - 验证空字符串被拒绝
        for empty_value in empty_values:
            with pytest.raises(ValidationError, match="字符串字段不能为空字符串"):
                validator.validate(empty_value)


class TestTypeValidator:
    """类型验证器测试"""

    def test_validate_correct_type_should_succeed(self):
        """
        用例：验证正确类型
        条件：值类型匹配期望类型
        期望：验证通过，返回原值
        验证：类型匹配正确
        """
        # Given - 类型验证器
        string_validator = TypeValidator(str, "字符串字段")
        int_validator = TypeValidator(int, "整数字段")

        # When & Then - 验证正确类型
        assert string_validator.validate("text") == "text"
        assert int_validator.validate(123) == 123

    def test_validate_wrong_type_should_fail(self):
        """
        用例：验证错误类型
        条件：值类型不匹配期望类型
        期望：抛出ValidationError
        验证：类型错误被正确识别
        """
        # Given - 类型验证器
        string_validator = TypeValidator(str, "字符串字段")

        # When & Then - 验证错误类型
        with pytest.raises(ValidationError, match="期望类型 str，实际类型 int"):
            string_validator.validate(123)

        with pytest.raises(ValidationError, match="期望类型 str，实际类型 NoneType"):
            string_validator.validate(None)

    def test_validate_complex_types(self):
        """
        用例：验证复杂类型
        条件：验证列表、字典等复杂类型
        期望：复杂类型正确验证
        验证：类型验证器支持所有Python类型
        """
        # Given - 复杂类型验证器
        list_validator = TypeValidator(list, "列表字段")
        dict_validator = TypeValidator(dict, "字典字段")

        # When & Then - 验证复杂类型
        assert list_validator.validate([1, 2, 3]) == [1, 2, 3]
        assert dict_validator.validate({"key": "value"}) == {"key": "value"}

        with pytest.raises(ValidationError):
            list_validator.validate("not a list")

        with pytest.raises(ValidationError):
            dict_validator.validate("not a dict")


class TestRangeValidator:
    """范围验证器测试"""

    def test_validate_in_range_should_succeed(self):
        """
        用例：验证范围内值
        条件：值在指定范围内
        期望：验证通过，返回原值
        验证：范围检查正确
        """
        # Given - 范围验证器
        validator = RangeValidator(min_value=0, max_value=100, "数值字段")

        # When & Then - 验证范围内的值
        assert validator.validate(0) == 0
        assert validator.validate(50) == 50
        assert validator.validate(100) == 100

    def test_validate_out_of_range_should_fail(self):
        """
        用例：验证范围外值
        条件：值超出指定范围
        期望：抛出ValidationError
        验证：范围边界严格执行
        """
        # Given - 范围验证器
        validator = RangeValidator(min_value=0, max_value=100, "数值字段")

        # When & Then - 验证超出范围的值
        with pytest.raises(ValidationError, match="值不能小于 0"):
            validator.validate(-1)

        with pytest.raises(ValidationError, match="值不能大于 100"):
            validator.validate(101)

    def test_validate_partial_range(self):
        """
        用例：验证部分范围
        条件：只设置最小值或最大值
        期望：部分范围正确验证
        验证：单向边界检查
        """
        # Given - 只有最小值
        min_validator = RangeValidator(min_value=18, "年龄字段")
        # Given - 只有最大值
        max_validator = RangeValidator(max_value=65, "年龄字段")

        # When & Then - 验证部分范围
        assert min_validator.validate(18) == 18
        assert min_validator.validate(30) == 30
        with pytest.raises(ValidationError):
            min_validator.validate(17)

        assert max_validator.validate(65) == 65
        assert max_validator.validate(30) == 30
        with pytest.raises(ValidationError):
            max_validator.validate(66)


class TestTaskTitleValidator:
    """任务标题验证器测试"""

    def test_validate_valid_title_should_succeed(self):
        """
        用例：验证有效任务标题
        条件：提供符合要求的标题
        期望：验证成功，返回TaskTitle对象
        验证：标题验证正确
        """
        # Given - 任务标题验证器
        validator = TaskTitleValidator()

        # When - 验证有效标题
        title = validator.validate("完成项目开发")

        # Then - 验证结果
        assert isinstance(title, TaskTitle)
        assert str(title) == "完成项目开发"

    def test_validate_invalid_title_should_fail(self):
        """
        用例：验证无效任务标题
        条件：提供不符合要求的标题
        期望：抛出ValidationError
        验证：无效标题被正确拒绝
        """
        # Given - 任务标题验证器
        validator = TaskTitleValidator()

        # When & Then - 验证各种无效标题
        with pytest.raises(ValidationError, match="长度不能少于 1 字符"):
            validator.validate("")

        with pytest.raises(ValidationError, match="长度不能超过 100 字符"):
            validator.validate("a" * 101)


class TestTaskStatusValidator:
    """任务状态验证器测试"""

    def test_validate_valid_status_should_succeed(self):
        """
        用例：验证有效任务状态
        条件：提供预定义的状态值
        期望：验证成功，返回TaskStatus对象
        验证：状态验证正确
        """
        # Given - 任务状态验证器
        validator = TaskStatusValidator()

        # When - 验证有效状态
        status = validator.validate("in_progress")

        # Then - 验证结果
        assert isinstance(status, TaskStatus)
        assert str(status) == "in_progress"

    def test_validate_invalid_status_should_fail(self):
        """
        用例：验证无效任务状态
        条件：提供未定义的状态值
        期望：抛出ValidationError
        验证：无效状态被正确拒绝
        """
        # Given - 任务状态验证器
        validator = TaskStatusValidator()

        # When & Then - 验证无效状态
        with pytest.raises(ValidationError, match="无效的任务状态"):
            validator.validate("invalid_status")


class TestTaskStatusTransitionValidator:
    """任务状态转换验证器测试"""

    def test_validate_valid_transition_should_succeed(self):
        """
        用例：验证有效状态转换
        条件：状态转换符合业务规则
        期望：验证成功，返回目标状态
        验证：合法转换被允许
        """
        # Given - 当前状态和转换验证器
        current_status = TaskStatus(TaskStatus.PENDING)
        validator = TaskStatusTransitionValidator(current_status)

        # When - 验证合法转换
        target_status = validator.validate(TaskStatus(TaskStatus.IN_PROGRESS))

        # Then - 验证结果
        assert isinstance(target_status, TaskStatus)
        assert str(target_status) == TaskStatus.IN_PROGRESS

    def test_validate_invalid_transition_should_fail(self):
        """
        用例：验证无效状态转换
        条件：状态转换违反业务规则
        期望：抛出BusinessRuleViolationError
        验证：非法转换被拒绝
        """
        # Given - 当前状态和转换验证器
        current_status = TaskStatus(TaskStatus.COMPLETED)
        validator = TaskStatusTransitionValidator(current_status)

        # When & Then - 验证非法转换
        with pytest.raises(BusinessRuleViolationError, match="不能从状态 completed 转换到 in_progress"):
            validator.validate(TaskStatus(TaskStatus.IN_PROGRESS))


class TestTaskPriorityValidator:
    """任务优先级验证器测试"""

    def test_validate_valid_priority_should_succeed(self):
        """
        用例：验证有效任务优先级
        条件：提供预定义的优先级值
        期望：验证成功，返回TaskPriority对象
        验证：优先级验证正确
        """
        # Given - 任务优先级验证器
        validator = TaskPriorityValidator()

        # When - 验证有效优先级
        priority = validator.validate("high")

        # Then - 验证结果
        assert isinstance(priority, TaskPriority)
        assert str(priority) == "high"
        assert priority.level == 3

    def test_validate_invalid_priority_should_fail(self):
        """
        用例：验证无效任务优先级
        条件：提供未定义的优先级值
        期望：抛出ValidationError
        验证：无效优先级被正确拒绝
        """
        # Given - 任务优先级验证器
        validator = TaskPriorityValidator()

        # When & Then - 验证无效优先级
        with pytest.raises(ValidationError, match="无效的任务优先级"):
            validator.validate("invalid_priority")


class TestTaskCompletionValidator:
    """任务完成百分比验证器测试"""

    def test_validate_valid_percentage_should_succeed(self):
        """
        用例：验证有效完成百分比
        条件：百分比值在0-100之间
        期望：验证成功，返回Percentage对象
        验证：百分比验证正确
        """
        # Given - 任务完成验证器
        validator = TaskCompletionValidator()

        # When - 验证有效百分比
        percentage = validator.validate(75.5)

        # Then - 验证结果
        assert isinstance(percentage, Percentage)
        assert str(percentage) == "75.5%"

    def test_validate_invalid_percentage_should_fail(self):
        """
        用例：验证无效完成百分比
        条件：百分比值超出0-100范围
        期望：抛出ValidationError
        验证：无效百分比被正确拒绝
        """
        # Given - 任务完成验证器
        validator = TaskCompletionValidator()

        # When & Then - 验证无效百分比
        with pytest.raises(ValidationError, match="百分比必须在 0.0-100.0 之间"):
            validator.validate(-10.0)

        with pytest.raises(ValidationError, match="百分比必须在 0.0-100.0 之间"):
            validator.validate(110.0)


class TestCompositeValidator:
    """复合验证器测试"""

    def test_validate_with_all_validators_should_succeed(self):
        """
        用例：使用所有验证器验证有效值
        条件：值通过所有验证器
        期望：验证成功，返回处理后的值
        验证：验证器链正确工作
        """
        # Given - 复合验证器
        validators = [
            RequiredValidator("字段"),
            TypeValidator(str, "字段"),
            RangeValidator(min_length=1, max_length=10, "字段")
        ]
        composite = CompositeValidator(validators, "字段")

        # When - 验证有效值
        result = composite.validate("test")

        # Then - 验证结果
        assert result == "test"

    def test_validate_with_first_validator_failing_should_fail(self):
        """
        用例：第一个验证器失败
        条件：值未通过第一个验证器
        期望：立即失败，不执行后续验证器
        验证：快速失败机制
        """
        # Given - 复合验证器
        validators = [
            RequiredValidator("字段"),  # 这会失败
            TypeValidator(str, "字段"),
        ]
        composite = CompositeValidator(validators, "字段")

        # When & Then - 第一个验证器失败
        with pytest.raises(ValidationError, match="字段是必填的"):
            composite.validate(None)

    def test_validate_with_last_validator_failing_should_fail(self):
        """
        用例：最后一个验证器失败
        条件：值未通过最后一个验证器
        期望：在最后一个验证器处失败
        验证：所有验证器都执行
        """
        # Given - 复合验证器
        validators = [
            TypeValidator(str, "字段"),  # 这会通过
            RangeValidator(min_length=5, max_length=10, "字段"),  # 这会失败
        ]
        composite = CompositeValidator(validators, "字段")

        # When & Then - 最后一个验证器失败
        with pytest.raises(ValidationError, match="值不能小于 5"):
            composite.validate("test")  # 长度为4，小于5


class TestConditionalValidator:
    """条件验证器测试"""

    def test_validate_condition_true_should_use_true_validator(self):
        """
        用例：条件为真时使用true_validator
        条件：条件函数返回True
        期望：使用true_validator进行验证
        验证：条件逻辑正确
        """
        # Given - 条件验证器
        def is_string(value):
            return isinstance(value, str)

        true_validator = RangeValidator(min_length=3, max_length=10, "字符串")
        conditional = ConditionalValidator(is_string, true_validator)

        # When - 验证字符串
        result = conditional.validate("test")

        # Then - 使用true_validator验证
        assert result == "test"

    def test_validate_condition_false_should_use_false_validator(self):
        """
        用例：条件为假时使用false_validator
        条件：条件函数返回False
        期望：使用false_validator进行验证
        验证：条件逻辑正确
        """
        # Given - 条件验证器
        def is_string(value):
            return isinstance(value, str)

        true_validator = RangeValidator(min_length=3, max_length=10, "字符串")
        false_validator = TypeValidator(int, "数字")
        conditional = ConditionalValidator(is_string, true_validator, false_validator)

        # When - 验证数字（条件为假）
        result = conditional.validate(123)

        # Then - 使用false_validator验证
        assert result == 123

    def test_validate_condition_false_without_false_validator_should_pass(self):
        """
        用例：条件为假且无false_validator
        条件：条件函数返回False且未设置false_validator
        期望：直接返回原值
        验证：可选验证器机制
        """
        # Given - 条件验证器
        def is_string(value):
            return isinstance(value, str)

        true_validator = RangeValidator(min_length=3, max_length=10, "字符串")
        conditional = ConditionalValidator(is_string, true_validator)

        # When - 验证数字（条件为假，无false_validator）
        result = conditional.validate(123)

        # Then - 直接返回原值
        assert result == 123


class TestValidatorFactory:
    """验证器工厂测试"""

    def test_create_task_title_validator(self):
        """
        用例：创建任务标题验证器
        条件：调用工厂方法
        期望：返回TaskTitleValidator实例
        验证：工厂方法正确创建验证器
        """
        # When - 创建验证器
        validator = ValidatorFactory.task_title()

        # Then - 验证类型
        assert isinstance(validator, TaskTitleValidator)
        assert validator.field_name == "任务标题"

    def test_create_task_description_validator(self):
        """
        用例：创建任务描述验证器
        条件：调用工厂方法
        期望：返回TaskDescriptionValidator实例
        验证：工厂方法正确创建验证器
        """
        # When - 创建验证器
        validator = ValidatorFactory.task_description()

        # Then - 验证类型
        assert isinstance(validator, TaskDescriptionValidator)
        assert validator.field_name == "任务描述"

    def test_create_task_status_validator(self):
        """
        用例：创建任务状态验证器
        条件：调用工厂方法
        期望：返回TaskStatusValidator实例
        验证：工厂方法正确创建验证器
        """
        # When - 创建验证器
        validator = ValidatorFactory.task_status()

        # Then - 验证类型
        assert isinstance(validator, TaskStatusValidator)
        assert validator.field_name == "任务状态"

    def test_create_task_status_validator_with_current_status(self):
        """
        用例：创建带当前状态的状态验证器
        条件：提供当前状态
        期望：返回TaskStatusTransitionValidator实例
        验证：工厂方法根据参数创建不同验证器
        """
        # Given - 当前状态
        current_status = TaskStatus(TaskStatus.PENDING)

        # When - 创建转换验证器
        validator = ValidatorFactory.task_status(current_status)

        # Then - 验证类型
        assert isinstance(validator, TaskStatusTransitionValidator)
        assert validator.current_status == current_status

    def test_create_required_string_validator(self):
        """
        用例：创建必填字符串验证器
        条件：指定长度范围
        期望：返回复合验证器
        验证：复合验证器正确组合
        """
        # When - 创建验证器
        validator = ValidatorFactory.required_string(min_length=1, max_length=50, "测试字段")

        # Then - 验证复合验证器
        assert isinstance(validator, CompositeValidator)
        assert validator.field_name == "测试字段"
        assert len(validator.validators) == 3  # Required + Type + Range

    def test_factory_validators_work_correctly(self):
        """
        用例：工厂创建的验证器正确工作
        条件：使用工厂创建的验证器验证数据
        期望：验证器功能正确
        验证：工厂创建的验证器与手动创建的等效
        """
        # Given - 工厂创建的验证器
        title_validator = ValidatorFactory.task_title()
        status_validator = ValidatorFactory.task_status()
        priority_validator = ValidatorFactory.task_priority()

        # When & Then - 验证器正确工作
        title = title_validator.validate("测试标题")
        assert isinstance(title, TaskTitle)

        status = status_validator.validate("in_progress")
        assert isinstance(status, TaskStatus)

        priority = priority_validator.validate("high")
        assert isinstance(priority, TaskPriority)

        # 验证错误情况
        with pytest.raises(ValidationError):
            title_validator.validate("")