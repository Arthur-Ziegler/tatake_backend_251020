"""
Points领域异常测试

测试Points领域的异常定义和处理，包括：
1. 异常创建和属性验证
2. 异常继承关系
3. 错误消息格式
4. 自定义属性测试
5. UUID类型验证

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
from uuid import uuid4, UUID

from src.domains.points.exceptions import (
    PointsException,
    PointsNotFoundException,
    PointsInsufficientException
)


@pytest.mark.unit
class TestPointsException:
    """Points基础异常测试类"""

    def test_points_exception_creation(self):
        """测试Points基础异常创建"""
        message = "测试错误消息"
        exception = PointsException(message)

        assert str(exception) == message

    def test_points_exception_inheritance(self):
        """测试Points异常继承关系"""
        exception = PointsException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, PointsException)

    def test_points_exception_empty_message(self):
        """测试空消息异常"""
        exception = PointsException("")
        assert str(exception) == ""

    @pytest.mark.parametrize("message", [
        "积分计算错误",
        "数据库连接失败",
        "参数验证错误",
        ""
    ])
    def test_points_exception_various_messages(self, message):
        """测试各种错误消息"""
        exception = PointsException(message)
        assert str(exception) == message


@pytest.mark.unit
class TestPointsNotFoundException:
    """积分未找到异常测试类"""

    def test_points_not_found_with_id(self):
        """测试带积分ID的异常创建"""
        points_id = uuid4()
        message = "积分记录不存在"
        exception = PointsNotFoundException(message, points_id)

        assert str(exception) == message
        assert exception.points_id == points_id

    def test_points_not_found_without_id(self):
        """测试不带积分ID的异常创建"""
        message = "积分记录不存在"
        exception = PointsNotFoundException(message)

        assert str(exception) == message
        assert exception.points_id is None

    def test_points_not_found_with_string_id(self):
        """测试字符串ID的异常创建"""
        points_id_str = "550e8400-e29b-41d4-a716-446655440000"
        points_id = UUID(points_id_str)
        message = "积分记录不存在"
        exception = PointsNotFoundException(message, points_id)

        assert str(exception) == message
        assert exception.points_id == points_id
        assert str(exception.points_id) == points_id_str

    def test_points_not_found_inheritance(self):
        """测试积分未找到异常继承关系"""
        exception = PointsNotFoundException("测试", uuid4())

        assert isinstance(exception, Exception)
        assert isinstance(exception, PointsException)
        assert isinstance(exception, PointsNotFoundException)

    def test_points_not_found_attributes(self):
        """测试积分未找到异常属性"""
        points_id = uuid4()
        message = "用户积分记录未找到"
        exception = PointsNotFoundException(message, points_id)

        # 验证所有属性
        assert hasattr(exception, 'points_id')
        assert hasattr(exception, '__str__')
        assert isinstance(exception.points_id, UUID)

    @pytest.mark.parametrize("message", [
        "积分记录不存在",
        "用户积分未找到",
        "积分数据缺失",
        "无法找到积分信息"
    ])
    def test_points_not_found_various_messages(self, message):
        """测试各种错误消息"""
        points_id = uuid4()
        exception = PointsNotFoundException(message, points_id)

        assert str(exception) == message
        assert exception.points_id == points_id

    @pytest.mark.parametrize("points_id", [
        uuid4(),
        UUID("550e8400-e29b-41d4-a716-446655440000"),
        UUID("123e4567-e89b-12d3-a456-426614174000"),
    ])
    def test_points_not_found_various_ids(self, points_id):
        """测试各种积分ID"""
        message = "积分不存在"
        exception = PointsNotFoundException(message, points_id)

        assert exception.points_id == points_id
        assert isinstance(exception.points_id, UUID)


@pytest.mark.unit
class TestPointsInsufficientException:
    """积分不足异常测试类"""

    def test_points_insufficient_with_amounts(self):
        """测试带积分数量的异常创建"""
        message = "积分不足"
        required = 100
        current = 50
        exception = PointsInsufficientException(message, required, current)

        assert str(exception) == message
        assert exception.required_points == required
        assert exception.current_points == current

    def test_points_insufficient_without_amounts(self):
        """测试不带积分数量的异常创建"""
        message = "积分不足"
        exception = PointsInsufficientException(message)

        assert str(exception) == message
        assert exception.required_points is None
        assert exception.current_points is None

    def test_points_insufficient_partial_amounts(self):
        """测试部分积分数量的异常创建"""
        message = "积分不足"
        required = 100
        current = None
        exception = PointsInsufficientException(message, required, current)

        assert str(exception) == message
        assert exception.required_points == required
        assert exception.current_points is None

    def test_points_insufficient_inheritance(self):
        """测试积分不足异常继承关系"""
        exception = PointsInsufficientException("测试", 100, 50)

        assert isinstance(exception, Exception)
        assert isinstance(exception, PointsException)
        assert isinstance(exception, PointsInsufficientException)

    def test_points_insufficient_attributes(self):
        """测试积分不足异常属性"""
        message = "积分不足，无法完成兑换"
        required = 200
        current = 80
        exception = PointsInsufficientException(message, required, current)

        # 验证所有属性
        assert hasattr(exception, 'required_points')
        assert hasattr(exception, 'current_points')
        assert exception.required_points == required
        assert exception.current_points == current

    @pytest.mark.parametrize("message", [
        "积分不足",
        "余额不够",
        "积分余额不足",
        "无法扣除足够的积分"
    ])
    def test_points_insufficient_various_messages(self, message):
        """测试各种错误消息"""
        required = 100
        current = 20
        exception = PointsInsufficientException(message, required, current)

        assert str(exception) == message
        assert exception.required_points == required
        assert exception.current_points == current

    @pytest.mark.parametrize("required,current", [
        (100, 50),
        (50, 0),
        (1000, 999),
        (1, 0),
        (500, 250),
        (0, 0),
        (100, 100)
    ])
    def test_points_insufficient_various_amounts(self, required, current):
        """测试各种积分数量"""
        message = "积分不足"
        exception = PointsInsufficientException(message, required, current)

        assert str(exception) == message
        assert exception.required_points == required
        assert exception.current_points == current

    def test_points_insufficient_large_amounts(self):
        """测试大额积分数量"""
        message = "积分不足"
        required = 1000000
        current = 500000
        exception = PointsInsufficientException(message, required, current)

        assert exception.required_points == required
        assert exception.current_points == current

    def test_points_insufficient_negative_amounts(self):
        """测试负数积分数量（边界情况）"""
        message = "积分不足"
        required = 100
        current = -50
        exception = PointsInsufficientException(message, required, current)

        # 允许负数，因为这可能是错误情况
        assert exception.required_points == required
        assert exception.current_points == current


@pytest.mark.integration
class TestPointsExceptionsIntegration:
    """Points异常集成测试类"""

    def test_exception_hierarchy_consistency(self):
        """测试异常层次结构一致性"""
        # 所有自定义异常都应该继承自PointsException
        base_exception = PointsException("base")
        points_not_found = PointsNotFoundException("test", uuid4())
        points_insufficient = PointsInsufficientException("test", 100, 50)

        # 验证继承关系
        assert isinstance(points_not_found, PointsException)
        assert isinstance(points_insufficient, PointsException)
        assert isinstance(base_exception, PointsException)

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        # 测试基类异常
        with pytest.raises(PointsException) as exc_info:
            raise PointsException("基础异常")

        assert str(exc_info.value) == "基础异常"

        # 测试积分未找到异常
        test_id = uuid4()
        with pytest.raises(PointsNotFoundException) as exc_info:
            raise PointsNotFoundException("积分未找到", test_id)

        assert exc_info.value.points_id == test_id

        # 测试积分不足异常
        with pytest.raises(PointsInsufficientException) as exc_info:
            raise PointsInsufficientException("积分不足", 100, 50)

        assert exc_info.value.required_points == 100
        assert exc_info.value.current_points == 50

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始计算错误")
            except ValueError as original_error:
                raise PointsNotFoundException("链式异常", uuid4()) from original_error
        except PointsNotFoundException as chained_error:
            # 验证异常链
            assert chained_error.__cause__ is not None
            assert isinstance(chained_error.__cause__, ValueError)
            assert chained_error.__cause__.args[0] == "原始计算错误"

    def test_exception_serialization(self):
        """测试异常序列化兼容性"""
        points_id = uuid4()
        exception = PointsNotFoundException("测试积分未找到", points_id)

        # 验证异常可以正常序列化为字典
        error_dict = {
            "type": "PointsNotFoundException",
            "message": str(exception),
            "points_id": str(exception.points_id) if exception.points_id else None
        }

        assert error_dict["type"] == "PointsNotFoundException"
        assert error_dict["message"] == "测试积分未找到"
        assert error_dict["points_id"] == str(points_id)

    def test_exception_context_in_real_scenario(self):
        """测试真实场景中的异常使用"""
        user_id = uuid4()
        required_points = 200
        current_points = 50

        # 模拟真实业务场景
        if current_points < required_points:
            exception = PointsInsufficientException(
                f"用户积分不足：需要{required_points}积分，当前只有{current_points}积分",
                required_points,
                current_points
            )

            assert required_points in exception.required_points
            assert current_points in exception.current_points
            assert "用户积分不足" in str(exception)

    def test_exception_error_message_completeness(self):
        """测试异常错误消息完整性"""
        # 测试所有异常类型都有详细的错误信息
        base_exception = PointsException("基础积分异常")
        not_found_exception = PointsNotFoundException("用户积分记录未找到", uuid4())
        insufficient_exception = PointsInsufficientException("积分余额不足", 100, 20)

        # 验证所有异常都包含有意义的错误信息
        assert len(str(base_exception)) > 5
        assert len(str(not_found_exception)) > 5
        assert len(str(insufficient_exception)) > 5

    def test_exception_with_none_values(self):
        """测试包含None值的异常"""
        # 测试带None值的异常不会出错
        exception1 = PointsNotFoundException("测试", None)
        exception2 = PointsInsufficientException("测试", None, None)

        assert exception1.points_id is None
        assert exception2.required_points is None
        assert exception2.current_points is None


@pytest.mark.parametrize("exception_class,creation_args", [
    (PointsException, ["测试消息"]),
    (PointsNotFoundException, ["测试消息", uuid4()]),
    (PointsInsufficientException, ["测试消息", 100, 50]),
])
def test_exception_creation_parameters(exception_class, creation_args):
    """参数化测试异常创建参数"""
    exception = exception_class(*creation_args)
    assert isinstance(exception, exception_class)
    assert isinstance(exception, PointsException)


@pytest.mark.parametrize("required,current,difference", [
    (100, 50, 50),
    (50, 0, 50),
    (1000, 999, 1),
    (200, 50, 150),
    (100, 100, 0),  # 刚好相等
])
def test_points_difference_calculation(required, current, difference):
    """参数化测试积分差值计算场景"""
    exception = PointsInsufficientException("积分不足", required, current)

    # 验证差值计算（模拟业务逻辑）
    actual_difference = exception.required_points - exception.current_points
    assert actual_difference == difference


@pytest.mark.parametrize("points_id", [
    None,
    uuid4(),
    UUID("550e8400-e29b-41d4-a716-446655440000"),
])
def test_points_id_variations(points_id):
    """参数化测试积分ID变体"""
    exception = PointsNotFoundException("积分记录测试", points_id)

    if points_id is None:
        assert exception.points_id is None
    else:
        assert exception.points_id == points_id
        assert isinstance(exception.points_id, UUID)