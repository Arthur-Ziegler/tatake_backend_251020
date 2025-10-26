"""
Top3领域异常测试

测试Top3领域的异常定义和处理，包括：
1. 异常创建和属性验证
2. 异常继承关系
3. 错误消息格式
4. 状态码验证
5. 日期参数处理

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest

from src.domains.top3.exceptions import (
    Top3Exception,
    Top3AlreadyExistsException,
    Top3NotFoundException
)


@pytest.mark.unit
class TestTop3Exception:
    """Top3基础异常测试类"""

    def test_top3_exception_creation(self):
        """测试Top3基础异常创建"""
        detail = "测试错误详情"
        status_code = 400

        exception = Top3Exception(detail, status_code)

        assert exception.detail == detail
        assert exception.status_code == status_code
        assert str(exception) == detail

    def test_top3_exception_default_status_code(self):
        """测试Top3基础异常默认状态码"""
        exception = Top3Exception("测试错误")

        assert exception.status_code == 400
        assert exception.detail == "测试错误"

    def test_top3_exception_custom_status_code(self):
        """测试自定义状态码的Top3异常"""
        exception = Top3Exception("权限错误", 403)

        assert exception.status_code == 403
        assert exception.detail == "权限错误"

    def test_top3_exception_inheritance(self):
        """测试Top3异常继承关系"""
        exception = Top3Exception("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, Top3Exception)

    @pytest.mark.parametrize("detail,status_code", [
        ("网络错误", 500),
        ("权限不足", 403),
        ("参数错误", 400),
        ("未找到", 404),
    ])
    def test_top3_exception_various_scenarios(self, detail, status_code):
        """测试各种Top3异常场景"""
        exception = Top3Exception(detail, status_code)

        assert exception.detail == detail
        assert exception.status_code == status_code


@pytest.mark.unit
class TestTop3AlreadyExistsException:
    """Top3已存在异常测试类"""

    def test_top3_already_exists_creation(self):
        """测试Top3已存在异常创建"""
        date = "2025-01-15"
        exception = Top3AlreadyExistsException(date)

        assert f"{date}的Top3已设置" in exception.detail
        assert "每天只能设置一次" in exception.detail
        assert exception.status_code == 400

    def test_top3_already_exists_various_dates(self):
        """测试各种日期格式的已存在异常"""
        dates = [
            "2025-01-15",
            "2025-12-31",
            "2024-02-29",  # 闰年
            "2023-06-01"
        ]

        for date in dates:
            exception = Top3AlreadyExistsException(date)
            assert date in exception.detail
            assert exception.status_code == 400

    def test_top3_already_exists_inheritance(self):
        """测试Top3已存在异常继承关系"""
        exception = Top3AlreadyExistsException("2025-01-15")

        assert isinstance(exception, Exception)
        assert isinstance(exception, Top3Exception)
        assert isinstance(exception, Top3AlreadyExistsException)

    def test_top3_already_exists_message_completeness(self):
        """测试Top3已存在异常消息完整性"""
        date = "2025-01-15"
        exception = Top3AlreadyExistsException(date)

        expected_message = f"{date}的Top3已设置，每天只能设置一次"
        assert exception.detail == expected_message


@pytest.mark.unit
class TestTop3NotFoundException:
    """Top3未找到异常测试类"""

    def test_top3_not_found_creation(self):
        """测试Top3未找到异常创建"""
        date = "2025-01-15"
        exception = Top3NotFoundException(date)

        assert f"{date}的Top3不存在" in exception.detail
        assert exception.status_code == 404

    def test_top3_not_found_various_dates(self):
        """测试各种日期格式的未找到异常"""
        dates = [
            "2025-01-15",
            "2024-12-31",
            "2023-02-28",
            "2026-08-25"
        ]

        for date in dates:
            exception = Top3NotFoundException(date)
            assert date in exception.detail
            assert exception.status_code == 404

    def test_top3_not_found_inheritance(self):
        """测试Top3未找到异常继承关系"""
        exception = Top3NotFoundException("2025-01-15")

        assert isinstance(exception, Exception)
        assert isinstance(exception, Top3Exception)
        assert isinstance(exception, Top3NotFoundException)

    def test_top3_not_found_message_completeness(self):
        """测试Top3未找到异常消息完整性"""
        date = "2025-01-15"
        exception = Top3NotFoundException(date)

        expected_message = f"{date}的Top3不存在"
        assert exception.detail == expected_message


@pytest.mark.integration
class TestTop3ExceptionsIntegration:
    """Top3异常集成测试类"""

    def test_exception_hierarchy_consistency(self):
        """测试异常层次结构一致性"""
        # 所有自定义异常都应该继承自Top3Exception
        base_exception = Top3Exception("base")
        already_exists = Top3AlreadyExistsException("2025-01-15")
        not_found = Top3NotFoundException("2025-01-15")

        # 验证继承关系
        assert isinstance(already_exists, Top3Exception)
        assert isinstance(not_found, Top3Exception)
        assert isinstance(base_exception, Top3Exception)

    def test_exception_status_codes_uniqueness(self):
        """测试异常状态码分配"""
        already_exists = Top3AlreadyExistsException("2025-01-15")
        not_found = Top3NotFoundException("2025-01-15")

        # 验证状态码分配合理
        assert already_exists.status_code == 400  # 客户端错误
        assert not_found.status_code == 404      # 未找到

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        # 测试基类异常
        with pytest.raises(Top3Exception) as exc_info:
            raise Top3Exception("基础异常")

        assert exc_info.value.detail == "基础异常"

        # 测试Top3已存在异常
        with pytest.raises(Top3AlreadyExistsException) as exc_info:
            raise Top3AlreadyExistsException("2025-01-15")

        assert "2025-01-15的Top3已设置" in exc_info.value.detail

        # 测试Top3未找到异常
        with pytest.raises(Top3NotFoundException) as exc_info:
            raise Top3NotFoundException("2025-01-15")

        assert "2025-01-15的Top3不存在" in exc_info.value.detail

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("数据库查询失败")
            except ValueError as original_error:
                raise Top3NotFoundException("2025-01-15") from original_error
        except Top3NotFoundException as chained_error:
            # 验证异常链
            assert chained_error.__cause__ is not None
            assert isinstance(chained_error.__cause__, ValueError)
            assert chained_error.__cause__.args[0] == "数据库查询失败"

    def test_exception_serialization(self):
        """测试异常序列化兼容性"""
        exception = Top3AlreadyExistsException("2025-01-15")

        # 验证异常可以正常序列化为JSON兼容格式
        error_dict = {
            "type": "Top3AlreadyExistsException",
            "detail": exception.detail,
            "status_code": exception.status_code,
            "message": str(exception)
        }

        assert error_dict["type"] == "Top3AlreadyExistsException"
        assert "2025-01-15的Top3已设置" in error_dict["detail"]
        assert error_dict["status_code"] == 400
        assert "2025-01-15的Top3已设置" in error_dict["message"]

    def test_real_world_scenario(self):
        """测试真实世界场景"""
        date = "2025-01-15"

        # 场景1：尝试重复设置Top3
        try:
            raise Top3AlreadyExistsException(date)
        except Top3AlreadyExistsException as e:
            assert e.status_code == 400
            assert "每天只能设置一次" in e.detail

        # 场景2：查询不存在的Top3
        try:
            raise Top3NotFoundException(date)
        except Top3NotFoundException as e:
            assert e.status_code == 404
            assert f"{date}的Top3不存在" in e.detail

    def test_exception_error_message_quality(self):
        """测试异常错误消息质量"""
        # 测试所有异常类型都有清晰的错误信息
        base_exception = Top3Exception("基础Top3错误")
        exists_exception = Top3AlreadyExistsException("2025-01-15")
        not_found_exception = Top3NotFoundException("2025-01-15")

        # 验证所有异常都包含有意义的错误信息
        assert len(str(base_exception)) > 5
        assert len(str(exists_exception)) > 10
        assert len(str(not_found_exception)) > 10

        # 验证消息包含关键信息
        assert "Top3" in str(exists_exception)
        assert "Top3" in str(not_found_exception)


@pytest.mark.parametrize("exception_class,expected_status_code", [
    (Top3Exception, 400),
    (Top3AlreadyExistsException, 400),
    (Top3NotFoundException, 404),
])
def test_exception_status_codes(exception_class, expected_status_code):
    """参数化测试异常状态码"""
    if exception_class == Top3Exception:
        exception = exception_class("test", expected_status_code)
    else:
        exception = exception_class("2025-01-15")
    assert exception.status_code == expected_status_code


@pytest.mark.parametrize("exception_class", [
    Top3AlreadyExistsException,
    Top3NotFoundException,
])
def test_exception_inheritance_chain(exception_class):
    """参数化测试异常继承链"""
    exception = exception_class("2025-01-15")
    assert isinstance(exception, Top3Exception)
    assert isinstance(exception, Exception)


@pytest.mark.parametrize("date", [
    "2025-01-15",
    "2024-12-31",
    "2023-06-01",
    "2026-08-25",
])
def test_date_parameter_handling(date):
    """参数化测试日期参数处理"""
    exists_exception = Top3AlreadyExistsException(date)
    not_found_exception = Top3NotFoundException(date)

    # 验证日期参数正确包含在错误消息中
    assert date in exists_exception.detail
    assert date in not_found_exception.detail

    # 验证消息格式正确
    assert f"{date}的Top3已设置" in exists_exception.detail
    assert f"{date}的Top3不存在" in not_found_exception.detail