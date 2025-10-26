"""
Focus领域UUID架构单元测试

测试FocusService和Focus Repository的UUID处理，确保：
1. UUIDConverter的正确使用
2. 参数验证和错误处理
3. 类型安全和一致性
4. 与其他领域Service的UUID兼容性

遵循TDD原则：先写测试→最小实现→优化重构

作者：TaKeKe团队
版本：1.0.0 - Focus领域UUID架构重构
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from src.domains.focus.service import FocusService
from src.domains.focus.models import FocusSession, SessionTypeConst
from src.domains.focus.schemas import StartFocusRequest, FocusSessionResponse
from src.domains.focus.exceptions import FocusException
from src.core.uuid_converter import UUIDConverter
from tests.conftest import test_db_session


@pytest.mark.unit
class TestFocusUUIDArchitecture:
    """Focus领域UUID架构测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        pass

    def test_uuid_converter_string_conversion(self):
        """测试UUIDConverter字符串转换功能"""
        uuid_obj = uuid4()
        result = UUIDConverter.ensure_string(uuid_obj)

        # 验证转换结果
        assert isinstance(result, str)
        assert len(result) == 36  # UUID字符串长度
        assert result.count('-') == 4  # UUID格式验证

    def test_uuid_converter_uuid_conversion(self):
        """测试UUIDConverter UUID对象转换功能"""
        uuid_str = str(uuid4())
        result = UUIDConverter.ensure_uuid(uuid_str)

        # 验证转换结果
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_uuid_converter_is_valid_uuid_string(self):
        """测试UUIDConverter UUID格式验证"""
        # 测试有效的UUID字符串
        valid_uuid_str = str(uuid4())
        assert UUIDConverter.is_valid_uuid_string(valid_uuid_str) is True

        # 测试无效的UUID字符串
        invalid_uuids = [
            "invalid-uuid",
            "12345",
            "not-a-uuid",
            "",
            "short-uuid"
        ]
        for invalid_uuid in invalid_uuids:
            assert UUIDConverter.is_valid_uuid_string(invalid_uuid) is False

    def test_start_focus_request_validation_success(self, test_db_session):
        """测试StartFocusRequest验证成功"""
        valid_request_data = {
            "task_id": str(uuid4()),
            "session_type": SessionTypeConst.FOCUS
        }

        request = StartFocusRequest(**valid_request_data)

        # 验证数据
        assert request.task_id == valid_request_data["task_id"]
        assert request.session_type == SessionTypeConst.FOCUS

    def test_start_focus_request_validation_invalid_uuid(self, test_db_session):
        """测试StartFocusRequest UUID验证失败"""
        invalid_request_data = {
            "task_id": "invalid-uuid-format",
            "session_type": SessionTypeConst.FOCUS
        }

        with pytest.raises(ValueError) as exc_info:
            StartFocusRequest(**invalid_request_data)
        assert "任务ID格式无效" in str(exc_info.value)

    def test_start_focus_request_validation_empty_task_id(self, test_db_session):
        """测试StartFocusRequest空任务ID验证失败"""
        invalid_request_data = {
            "task_id": "",
            "session_type": SessionTypeConst.FOCUS
        }

        with pytest.raises(ValueError) as exc_info:
            StartFocusRequest(**invalid_request_data)
        assert "任务ID不能为空" in str(exc_info.value)

    def test_focus_service_start_focus_uuid_handling(self, test_db_session):
        """测试FocusService.start_focus的UUID处理"""
        user_id = uuid4()
        task_id = uuid4()

        # Mock依赖服务
        mock_task_repo = Mock()
        mock_task_repo.get_by_id.return_value = Mock(user_id=str(user_id))

        service = FocusService(test_db_session)

        request = StartFocusRequest(
            task_id=str(task_id),
            session_type=SessionTypeConst.FOCUS
        )

        with patch.object(service, 'repository') as mock_repo, \
             patch('src.domains.focus.service.TaskRepository') as mock_task_repo_class:

            mock_task_repo_class.return_value = mock_task_repo

            # Mock Repository create方法
            mock_session = Mock(spec=FocusSession)
            mock_session.id = str(uuid4())
            mock_session.user_id = str(user_id)
            mock_session.task_id = str(task_id)
            mock_session.session_type = SessionTypeConst.FOCUS
            mock_session.start_time = datetime.now(timezone.utc)
            mock_session.end_time = None

            mock_repo.create.return_value = mock_session

            result = service.start_focus(user_id, request)

            # 验证UUID转换正确
            assert isinstance(result, dict)
            assert "id" in result
            assert "user_id" in result
            assert "task_id" in result

    def test_focus_service_pause_focus_uuid_handling(self, test_db_session):
        """测试FocusService.pause_focus的UUID处理"""
        user_id = uuid4()
        session_id = uuid4()
        task_id = uuid4()

        service = FocusService(test_db_session)

        # Mock现有的会话
        mock_session = Mock(spec=FocusSession)
        mock_session.id = str(session_id)
        mock_session.user_id = str(user_id)
        mock_session.task_id = str(task_id)
        mock_session.session_type = SessionTypeConst.FOCUS
        mock_session.end_time = None
        mock_session.is_active = True

        with patch.object(service, 'repository') as mock_repo:
            mock_repo.get_by_id.return_value = mock_session
            mock_repo.complete_session.return_value = mock_session

            # Mock暂停会话
            mock_pause_session = Mock(spec=FocusSession)
            mock_pause_session.id = str(uuid4())
            mock_pause_session.user_id = str(user_id)
            mock_pause_session.task_id = str(task_id)
            mock_pause_session.session_type = "pause"
            mock_pause_session.start_time = datetime.now(timezone.utc)
            mock_pause_session.end_time = None

            mock_repo.create.return_value = mock_pause_session

            result = service.pause_focus(session_id, user_id)

            # 验证UUID处理
            assert isinstance(result, dict)
            assert "id" in result

    def test_focus_service_resume_focus_uuid_handling(self, test_db_session):
        """测试FocusService.resume_focus的UUID处理"""
        user_id = uuid4()
        session_id = uuid4()
        task_id = uuid4()

        service = FocusService(test_db_session)

        # Mock暂停会话
        mock_pause_session = Mock(spec=FocusSession)
        mock_pause_session.id = str(session_id)
        mock_pause_session.user_id = str(user_id)
        mock_pause_session.task_id = str(task_id)
        mock_pause_session.session_type = "pause"
        mock_pause_session.end_time = None
        mock_pause_session.is_active = True

        with patch.object(service, 'repository') as mock_repo:
            mock_repo.get_by_id.return_value = mock_pause_session
            mock_repo.complete_session.return_value = mock_pause_session

            # Mock新的专注会话
            mock_focus_session = Mock(spec=FocusSession)
            mock_focus_session.id = str(uuid4())
            mock_focus_session.user_id = str(user_id)
            mock_focus_session.task_id = str(task_id)
            mock_focus_session.session_type = SessionTypeConst.FOCUS
            mock_focus_session.start_time = datetime.now(timezone.utc)
            mock_focus_session.end_time = None

            mock_repo.create.return_value = mock_focus_session

            result = service.resume_focus(session_id, user_id)

            # 验证UUID处理
            assert isinstance(result, dict)
            assert "id" in result

    def test_focus_service_complete_focus_uuid_handling(self, test_db_session):
        """测试FocusService.complete_focus的UUID处理"""
        user_id = uuid4()
        session_id = uuid4()
        task_id = uuid4()

        service = FocusService(test_db_session)

        # Mock会话
        mock_session = Mock(spec=FocusSession)
        mock_session.id = str(session_id)
        mock_session.user_id = str(user_id)
        mock_session.task_id = str(task_id)
        mock_session.session_type = SessionTypeConst.FOCUS
        mock_session.end_time = None

        with patch.object(service, 'repository') as mock_repo:
            mock_repo.get_by_id.return_value = mock_session
            mock_repo.complete_session.return_value = mock_session

            result = service.complete_focus(session_id, user_id)

            # 验证UUID处理
            assert isinstance(result, dict)
            assert "id" in result

    def test_focus_service_get_user_sessions_uuid_handling(self, test_db_session):
        """测试FocusService.get_user_sessions的UUID处理"""
        user_id = uuid4()

        service = FocusService(test_db_session)

        # Mock Repository返回
        with patch.object(service, 'repository') as mock_repo:
            mock_repo.get_user_sessions.return_value = ([], 0)

            result = service.get_user_sessions(user_id, 1, 20)

            # 验证返回结构
            assert isinstance(result, dict)
            assert "sessions" in result
            assert "total" in result
            assert "page" in result
            assert "page_size" in result
            assert "has_more" in result

    def test_focus_service_uuid_string_input_support(self, test_db_session):
        """测试FocusService支持字符串UUID输入"""
        user_id_str = str(uuid4())
        task_id_str = str(uuid4())

        # Mock依赖服务
        mock_task_repo = Mock()
        mock_task_repo.get_by_id.return_value = Mock(user_id=user_id_str)

        service = FocusService(test_db_session)

        request = StartFocusRequest(
            task_id=task_id_str,
            session_type=SessionTypeConst.FOCUS
        )

        with patch.object(service, 'repository') as mock_repo, \
             patch('src.domains.focus.service.TaskRepository') as mock_task_repo_class:

            mock_task_repo_class.return_value = mock_task_repo

            # Mock Repository create方法
            mock_session = Mock(spec=FocusSession)
            mock_session.id = str(uuid4())
            mock_session.user_id = user_id_str
            mock_session.task_id = task_id_str
            mock_session.session_type = SessionTypeConst.FOCUS
            mock_session.start_time = datetime.now(timezone.utc)
            mock_session.end_time = None

            mock_repo.create.return_value = mock_session

            # 使用字符串UUID调用
            result = service.start_focus(user_id_str, request)

            # 验证成功处理
            assert isinstance(result, dict)
            assert "id" in result

    def test_focus_service_exception_handling_with_uuid(self, test_db_session):
        """测试FocusService异常处理中的UUID处理"""
        user_id = uuid4()
        invalid_task_id = uuid4()

        service = FocusService(test_db_session)

        request = StartFocusRequest(
            task_id=str(invalid_task_id),
            session_type=SessionTypeConst.FOCUS
        )

        with patch.object(service, 'repository') as mock_repo, \
             patch('src.domains.focus.service.TaskRepository') as mock_task_repo_class:

            # Mock任务不存在
            mock_task_repo = Mock()
            mock_task_repo.get_by_id.return_value = None
            mock_task_repo_class.return_value = mock_task_repo

            # 测试任务不存在异常
            with pytest.raises(FocusException) as exc_info:
                service.start_focus(user_id, request)

            assert exc_info.value.status_code == 404
            assert "任务不存在或无权限" in str(exc_info.value)

    def test_focus_service_mixed_uuid_types(self, test_db_session):
        """测试FocusService处理混合UUID类型"""
        user_id_uuid = uuid4()
        user_id_str = str(user_id_uuid)
        task_id = uuid4()

        # Mock依赖服务
        mock_task_repo = Mock()
        mock_task_repo.get_by_id.return_value = Mock(user_id=user_id_str)

        service = FocusService(test_db_session)

        request = StartFocusRequest(
            task_id=str(task_id),
            session_type=SessionTypeConst.FOCUS
        )

        with patch.object(service, 'repository') as mock_repo, \
             patch('src.domains.focus.service.TaskRepository') as mock_task_repo_class:

            mock_task_repo_class.return_value = mock_task_repo

            # Mock Repository create方法
            mock_session = Mock(spec=FocusSession)
            mock_session.id = str(uuid4())
            mock_session.user_id = user_id_str
            mock_session.task_id = str(task_id)
            mock_session.session_type = SessionTypeConst.FOCUS
            mock_session.start_time = datetime.now(timezone.utc)
            mock_session.end_time = None

            mock_repo.create.return_value = mock_session

            # 测试使用UUID对象
            result_uuid = service.start_focus(user_id_uuid, request)
            assert isinstance(result_uuid, dict)

            # 重置mock
            mock_repo.reset_mock()

            # 测试使用字符串
            result_str = service.start_focus(user_id_str, request)
            assert isinstance(result_str, dict)

            # 验证结果一致性
            assert result_uuid["task_id"] == result_str["task_id"]
            assert result_uuid["session_type"] == result_str["session_type"]

    def test_uuid_converter_error_handling(self):
        """测试UUIDConverter错误处理"""
        # 测试无效UUID字符串
        invalid_uuids = [
            "invalid-uuid",
            "12345",
            "not-a-uuid",
            "short-uuid",
            "",
            None
        ]

        for invalid_uuid in invalid_uuids:
            if invalid_uuid is None:
                with pytest.raises(TypeError):
                    UUIDConverter.ensure_string(invalid_uuid)
            else:
                with pytest.raises((TypeError, ValueError)):
                    UUIDConverter.ensure_uuid(invalid_uuid)

    def test_integration_uuid_flow_with_task_service(self, test_db_session):
        """测试与Task服务的UUID流转集成"""
        user_id = uuid4()
        task_id = uuid4()

        # Mock TaskRepository
        mock_task = Mock()
        mock_task.id = str(task_id)
        mock_task.user_id = str(user_id)

        service = FocusService(test_db_session)

        request = StartFocusRequest(
            task_id=str(task_id),
            session_type=SessionTypeConst.FOCUS
        )

        with patch.object(service, 'repository') as mock_repo, \
             patch('src.domains.focus.service.TaskRepository') as mock_task_repo_class:

            mock_task_repo = Mock()
            mock_task_repo.get_by_id.return_value = mock_task
            mock_task_repo_class.return_value = mock_task_repo

            # Mock Repository create方法
            mock_session = Mock(spec=FocusSession)
            mock_session.id = str(uuid4())
            mock_session.user_id = str(user_id)
            mock_session.task_id = str(task_id)
            mock_session.session_type = SessionTypeConst.FOCUS
            mock_session.start_time = datetime.now(timezone.utc)
            mock_session.end_time = None

            mock_repo.create.return_value = mock_session

            # 验证TaskRepository调用参数转换
            result = service.start_focus(user_id, request)
            assert isinstance(result, dict)

            # 验证TaskRepository被调用时使用了正确的UUID转换
            mock_task_repo.get_by_id.assert_called_once_with(
                task_id=str(task_id),
                user_id=str(user_id)
            )