"""
Focus领域异常测试

测试Focus领域的异常定义和处理，包括：
1. 异常创建和属性验证
2. 异常继承关系
3. 错误消息格式
4. 状态码验证
5. 异常字符串表示

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest

from src.domains.focus.exceptions import (
    FocusException,
    SessionNotFoundException,
    SessionNotActiveException,
    TaskNotFoundException,
    PermissionDeniedException,
    DatabaseOperationException
)


@pytest.mark.unit
class TestFocusException:
    """Focus基础异常测试类"""

    def test_focus_exception_creation(self):
        """测试Focus基础异常创建"""
        detail = "测试错误详情"
        status_code = 400

        exception = FocusException(detail, status_code)

        assert exception.detail == detail
        assert exception.status_code == status_code
        assert detail in str(exception)

    def test_focus_exception_default_status_code(self):
        """测试Focus基础异常默认状态码"""
        exception = FocusException("测试错误")

        assert exception.status_code == 400
        assert exception.detail == "测试错误"

    def test_focus_exception_string_representation(self):
        """测试Focus异常字符串表示"""
        detail = "测试错误详情"
        status_code = 500
        exception = FocusException(detail, status_code)

        # 验证字符串表示包含关键信息
        str_repr = str(exception)
        assert "FocusException" in str_repr
        assert str(status_code) in str_repr
        assert detail in str_repr

    def test_focus_exception_inheritance(self):
        """测试Focus异常继承关系"""
        exception = FocusException("测试")

        assert isinstance(exception, Exception)
        assert isinstance(exception, FocusException)


@pytest.mark.unit
class TestSessionNotFoundException:
    """会话未找到异常测试类"""

    def test_session_not_found_with_id(self):
        """测试带会话ID的异常创建"""
        session_id = "session_12345"
        exception = SessionNotFoundException(session_id)

        assert exception.detail == f"会话不存在: {session_id}"
        assert exception.status_code == 404
        assert str(exception) == f"会话不存在: {session_id}"

    def test_session_not_found_without_id(self):
        """测试不带会话ID的异常创建"""
        exception = SessionNotFoundException()

        assert exception.detail == "会话不存在"
        assert exception.status_code == 404
        assert str(exception) == "会话不存在"

    def test_session_not_found_inheritance(self):
        """测试会话未找到异常继承关系"""
        exception = SessionNotFoundException("test_session")

        assert isinstance(exception, FocusException)
        assert isinstance(exception, SessionNotFoundException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("session_id", [
        "session_123",
        "uuid-string-12345-67890",
        "123e4567-e89b-12d3-a456-426614174000",
        "session_with_underscores"
    ])
    def test_session_not_found_various_ids(self, session_id):
        """测试各种会话ID格式的异常"""
        exception = SessionNotFoundException(session_id)

        assert exception.detail == f"会话不存在: {session_id}"
        assert exception.status_code == 404


@pytest.mark.unit
class TestSessionNotActiveException:
    """会话未激活异常测试类"""

    def test_session_not_active_with_id(self):
        """测试带会话ID的未激活异常"""
        session_id = "inactive_session_123"
        exception = SessionNotActiveException(session_id)

        assert exception.detail == f"会话未激活或已完成: {session_id}"
        assert exception.status_code == 400
        assert str(exception) == f"会话未激活或已完成: {session_id}"

    def test_session_not_active_without_id(self):
        """测试不带会话ID的未激活异常"""
        exception = SessionNotActiveException()

        assert exception.detail == "会话未激活或已完成"
        assert exception.status_code == 400
        assert str(exception) == "会话未激活或已完成"

    def test_session_not_active_inheritance(self):
        """测试会话未激活异常继承关系"""
        exception = SessionNotActiveException("test_session")

        assert isinstance(exception, FocusException)
        assert isinstance(exception, SessionNotActiveException)
        assert isinstance(exception, Exception)


@pytest.mark.unit
class TestTaskNotFoundException:
    """任务未找到异常测试类"""

    def test_task_not_found_with_id(self):
        """测试带任务ID的异常创建"""
        task_id = "task_12345"
        exception = TaskNotFoundException(task_id)

        assert exception.detail == f"任务不存在: {task_id}"
        assert exception.status_code == 404
        assert str(exception) == f"任务不存在: {task_id}"

    def test_task_not_found_without_id(self):
        """测试不带任务ID的异常创建"""
        exception = TaskNotFoundException()

        assert exception.detail == "任务不存在"
        assert exception.status_code == 404
        assert str(exception) == "任务不存在"

    def test_task_not_found_inheritance(self):
        """测试任务未找到异常继承关系"""
        exception = TaskNotFoundException("test_task")

        assert isinstance(exception, FocusException)
        assert isinstance(exception, TaskNotFoundException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("task_id", [
        "task_123",
        "task_uuid_string",
        "12345678-1234-5678-9012-123456789012",
        "task_with_dashes-and_underscores"
    ])
    def test_task_not_found_various_ids(self, task_id):
        """测试各种任务ID格式的异常"""
        exception = TaskNotFoundException(task_id)

        assert exception.detail == f"任务不存在: {task_id}"
        assert exception.status_code == 404


@pytest.mark.unit
class TestPermissionDeniedException:
    """权限不足异常测试类"""

    def test_permission_denied_default_resource(self):
        """测试默认资源的权限异常"""
        exception = PermissionDeniedException()

        assert exception.detail == "无权限访问资源"
        assert exception.status_code == 403
        assert str(exception) == "无权限访问资源"

    def test_permission_denied_custom_resource(self):
        """测试自定义资源的权限异常"""
        resource = "会话管理"
        exception = PermissionDeniedException(resource)

        assert exception.detail == f"无权限访问{resource}"
        assert exception.status_code == 403
        assert str(exception) == f"无权限访问{resource}"

    def test_permission_denied_inheritance(self):
        """测试权限不足异常继承关系"""
        exception = PermissionDeniedException("测试资源")

        assert isinstance(exception, FocusException)
        assert isinstance(exception, PermissionDeniedException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("resource", [
        "用户数据",
        "系统配置",
        "管理员功能",
        "敏感信息",
        "数据库操作"
    ])
    def test_permission_denied_various_resources(self, resource):
        """测试各种资源的权限异常"""
        exception = PermissionDeniedException(resource)

        assert exception.detail == f"无权限访问{resource}"
        assert exception.status_code == 403


@pytest.mark.unit
class TestDatabaseOperationException:
    """数据库操作异常测试类"""

    def test_database_operation_default(self):
        """测试默认数据库操作异常"""
        exception = DatabaseOperationException()

        assert exception.detail == "数据库操作失败"
        assert exception.status_code == 500
        assert str(exception) == "数据库操作失败"

    def test_database_operation_custom(self):
        """测试自定义数据库操作异常"""
        operation = "插入数据"
        exception = DatabaseOperationException(operation)

        assert exception.detail == f"数据库{operation}失败"
        assert exception.status_code == 500
        assert str(exception) == f"数据库{operation}失败"

    def test_database_operation_inheritance(self):
        """测试数据库操作异常继承关系"""
        exception = DatabaseOperationException("测试操作")

        assert isinstance(exception, FocusException)
        assert isinstance(exception, DatabaseOperationException)
        assert isinstance(exception, Exception)

    @pytest.mark.parametrize("operation", [
        "创建表",
        "插入数据",
        "更新记录",
        "删除数据",
        "查询数据",
        "连接数据库",
        "事务提交",
        "事务回滚"
    ])
    def test_database_operation_various_operations(self, operation):
        """测试各种数据库操作的异常"""
        exception = DatabaseOperationException(operation)

        assert exception.detail == f"数据库{operation}失败"
        assert exception.status_code == 500


@pytest.mark.integration
class TestFocusExceptionsIntegration:
    """Focus异常集成测试类"""

    def test_exception_hierarchy_consistency(self):
        """测试异常层次结构一致性"""
        # 所有自定义异常都应该继承自FocusException
        base_exception = FocusException("base")
        session_not_found = SessionNotFoundException("session")
        session_not_active = SessionNotActiveException("session")
        task_not_found = TaskNotFoundException("task")
        permission_denied = PermissionDeniedException("resource")
        db_operation = DatabaseOperationException("operation")

        # 验证继承关系
        assert isinstance(session_not_found, FocusException)
        assert isinstance(session_not_active, FocusException)
        assert isinstance(task_not_found, FocusException)
        assert isinstance(permission_denied, FocusException)
        assert isinstance(db_operation, FocusException)

    def test_exception_error_codes_uniqueness(self):
        """测试异常错误码唯一性"""
        exceptions = [
            SessionNotFoundException("test"),
            SessionNotActiveException("test"),
            TaskNotFoundException("test"),
            PermissionDeniedException("test"),
            DatabaseOperationException("test"),
        ]

        status_codes = set()
        for exc in exceptions:
            assert exc.status_code not in status_codes, f"重复的状态码: {exc.status_code}"
            status_codes.add(exc.status_code)

        # 验证所有主要HTTP状态码都被使用
        expected_codes = {403, 404, 400, 500}
        assert status_codes == expected_codes

    def test_exception_raising_and_catching(self):
        """测试异常抛出和捕获"""
        # 测试基类异常
        with pytest.raises(FocusException) as exc_info:
            raise FocusException("基础异常")

        assert exc_info.value.detail == "基础异常"

        # 测试会话未找到异常
        with pytest.raises(SessionNotFoundException) as exc_info:
            raise SessionNotFoundException("session_123")

        assert exc_info.value.status_code == 404

        # 测试权限异常
        with pytest.raises(PermissionDeniedException) as exc_info:
            raise PermissionDeniedException("管理员功能")

        assert exc_info.value.status_code == 403

    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as original_error:
                raise SessionNotFoundException("chained_error") from original_error
        except SessionNotFoundException as chained_error:
            # 验证异常链
            assert chained_error.__cause__ is not None
            assert isinstance(chained_error.__cause__, ValueError)
            assert chained_error.__cause__.args[0] == "原始错误"
            assert chained_error.detail == "chained_error"

    def test_exception_serialization(self):
        """测试异常序列化兼容性"""
        exception = SessionNotFoundException("test_session")

        # 验证异常可以正常序列化为JSON兼容格式
        error_dict = {
            "type": "SessionNotFoundException",
            "detail": exception.detail,
            "status_code": exception.status_code,
            "message": str(exception)
        }

        assert error_dict["type"] == "SessionNotFoundException"
        assert error_dict["detail"] == "会话不存在: test_session"
        assert error_dict["status_code"] == 404
        assert "SessionNotFoundException (404)" in error_dict["message"]


@pytest.mark.parametrize("exception_class,expected_status_code", [
    (SessionNotFoundException, 404),
    (TaskNotFoundException, 404),
    (PermissionDeniedException, 403),
    (SessionNotActiveException, 400),
    (DatabaseOperationException, 500),
])
def test_exception_status_codes(exception_class, expected_status_code):
    """参数化测试异常状态码"""
    exception = exception_class("test")
    assert exception.status_code == expected_status_code


@pytest.mark.parametrize("exception_class", [
    SessionNotFoundException,
    TaskNotFoundException,
    PermissionDeniedException,
    SessionNotActiveException,
    DatabaseOperationException,
])
def test_exception_inheritance_chain(exception_class):
    """参数化测试异常继承链"""
    exception = exception_class("test")
    assert isinstance(exception, FocusException)
    assert isinstance(exception, Exception)