"""
Focus领域Service层测试

测试FocusService的业务逻辑，包括：
1. 专注会话的创建和管理
2. 自动关闭机制
3. 会话类型转换
4. 业务规则验证

使用简化后的FocusSession模型（仅6个核心字段）。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID

from src.domains.focus.service import FocusService
from src.domains.focus.models import FocusSession, SessionTypeConst
from src.domains.focus.schemas import StartFocusRequest
from src.domains.focus.exceptions import FocusException
from src.domains.task.models import Task


@pytest.mark.unit
class TestFocusService:
    """FocusService测试类"""

    @pytest.fixture
    def service(self, test_db_session):
        """创建Service实例"""
        return FocusService(test_db_session)

    @pytest.fixture
    def sample_user_id(self) -> str:
        """示例用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_task_id(self) -> str:
        """示例任务ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_task(self, test_db_session, sample_user_id, sample_task_id):
        """创建示例任务"""
        task = Task(
            id=sample_task_id,
            user_id=str(sample_user_id),
            title="测试任务",
            description="用于测试Focus的任务",
            priority="medium"
        )
        test_db_session.add(task)
        test_db_session.commit()
        test_db_session.refresh(task)
        return task

    def test_start_focus_session_success(self, service, sample_user_id, sample_task):
        """测试成功开始专注会话"""
        request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )

        response = service.start_focus(sample_user_id, request)

        # 验证响应
        assert response.id is not None
        assert response.user_id == sample_user_id
        assert response.task_id == sample_task.id
        assert response.session_type == SessionTypeConst.FOCUS
        assert response.start_time is not None
        assert response.end_time is None
        assert response.is_active is True

    def test_start_focus_session_invalid_task(self, service, sample_user_id):
        """测试开始专注会话时任务不存在"""
        fake_task_id = str(uuid4())
        request = StartFocusRequest(
            task_id=fake_task_id,
            session_type=SessionTypeConst.FOCUS
        )

        with pytest.raises(FocusException) as exc_info:
            service.start_focus(sample_user_id, request)

        assert "任务不存在或无权限" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_start_break_session_success(self, service, sample_user_id, sample_task):
        """测试开始休息会话"""
        request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.BREAK
        )

        response = service.start_focus(sample_user_id, request)

        assert response.session_type == SessionTypeConst.BREAK
        assert response.is_active is True

    def test_start_focus_auto_close_previous(self, service, sample_user_id, sample_task):
        """测试开始新会话时自动关闭之前的活跃会话"""
        # 创建第一个会话
        first_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        first_response = service.start_focus(sample_user_id, first_request)
        assert first_response.end_time is None

        # 创建第二个会话
        second_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.BREAK
        )
        second_response = service.start_focus(sample_user_id, second_request)

        # 验证第一个会话被自动关闭
        first_session_reloaded = service.repository.get_by_id(first_response.id)
        assert first_session_reloaded.end_time is not None

        # 验证第二个会话活跃
        assert second_response.end_time is None
        assert second_response.is_active is True

    def test_pause_focus_session_success(self, service, sample_user_id, sample_task):
        """测试暂停专注会话成功"""
        # 先开始专注会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)

        # 暂停专注会话
        pause_response = service.pause_focus(focus_response.id, sample_user_id)

        # 验证暂停会话
        assert pause_response.session_type == "pause"
        assert pause_response.task_id == sample_task.id
        assert pause_response.end_time is None
        assert pause_response.is_active is True

        # 验证原专注会话已结束
        original_session = service.repository.get_by_id(focus_response.id)
        assert original_session.end_time is not None

    def test_pause_focus_session_not_found(self, service, sample_user_id):
        """测试暂停不存在的会话"""
        fake_session_id = str(uuid4())

        with pytest.raises(FocusException) as exc_info:
            service.pause_focus(fake_session_id, sample_user_id)

        assert "会话不存在或无权限" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_pause_focus_session_wrong_user(self, service, sample_user_id, sample_task):
        """测试暂停其他用户的会话"""
        other_user_id = str(uuid4())

        # 先创建会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)

        # 尝试用其他用户ID暂停
        with pytest.raises(FocusException) as exc_info:
            service.pause_focus(focus_response.id, other_user_id)

        assert "会话不存在或无权限" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_pause_inactive_session(self, service, sample_user_id, sample_task):
        """测试暂停已结束的会话"""
        # 先开始并完成会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)

        # 完成会话
        service.complete_focus(focus_response.id, sample_user_id)

        # 尝试暂停已完成的会话
        with pytest.raises(FocusException) as exc_info:
            service.pause_focus(focus_response.id, sample_user_id)

        assert "只能暂停进行中的会话" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    def test_resume_focus_session_success(self, service, sample_user_id, sample_task):
        """测试恢复专注会话成功"""
        # 先开始专注会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)

        # 暂停专注会话
        pause_response = service.pause_focus(focus_response.id, sample_user_id)

        # 恢复专注会话
        resume_response = service.resume_focus(pause_response.id, sample_user_id)

        # 验证恢复的专注会话
        assert resume_response.session_type == "focus"
        assert resume_response.task_id == sample_task.id
        assert resume_response.end_time is None
        assert resume_response.is_active is True

        # 验证暂停会话已结束
        pause_session = service.repository.get_by_id(pause_response.id)
        assert pause_session.end_time is not None

    def test_resume_from_non_pause_session(self, service, sample_user_id, sample_task):
        """测试从非暂停会话恢复"""
        # 先开始专注会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)

        # 尝试从专注会话恢复（应该是错误的）
        with pytest.raises(FocusException) as exc_info:
            service.resume_focus(focus_response.id, sample_user_id)

        assert "只能从暂停会话恢复" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    def test_complete_focus_session_success(self, service, sample_user_id, sample_task):
        """测试完成专注会话成功"""
        # 先开始专注会话
        start_request = StartFocusRequest(
            task_id=sample_task.id,
            session_type=SessionTypeConst.FOCUS
        )
        focus_response = service.start_focus(sample_user_id, start_request)
        assert focus_response.end_time is None

        # 完成会话
        complete_response = service.complete_focus(focus_response.id, sample_user_id)

        # 验证完成的会话
        assert complete_response.id == focus_response.id
        assert complete_response.end_time is not None
        assert complete_response.end_time > complete_response.start_time
        assert complete_response.is_active is False

    def test_complete_focus_session_not_found(self, service, sample_user_id):
        """测试完成不存在的会话"""
        fake_session_id = str(uuid4())

        with pytest.raises(FocusException) as exc_info:
            service.complete_focus(fake_session_id, sample_user_id)

        assert "会话不存在或无权限" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_get_user_sessions_empty(self, service, sample_user_id):
        """测试获取用户会话列表（空）"""
        response = service.get_user_sessions(sample_user_id)

        assert response.sessions == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 50
        assert response.has_more is False

    def test_get_user_sessions_with_data(self, service, sample_user_id, sample_task):
        """测试获取用户会话列表（有数据）"""
        # 创建多个会话
        sessions = []
        for i in range(3):
            request = StartFocusRequest(
                task_id=sample_task.id,
                session_type=SessionTypeConst.FOCUS if i % 2 == 0 else SessionTypeConst.BREAK
            )
            response = service.start_focus(sample_user_id, request)
            sessions.append(response)

        # 完成前两个会话
        service.complete_focus(sessions[0].id, sample_user_id)
        service.complete_focus(sessions[1].id, sample_user_id)

        # 获取会话列表
        list_response = service.get_user_sessions(sample_user_id, page=1, page_size=2)

        assert len(list_response.sessions) == 2
        assert list_response.total == 3
        assert list_response.page == 1
        assert list_response.page_size == 2
        assert list_response.has_more is True
        # 按时间倒序，最新的在前
        assert list_response.sessions[0].start_time >= list_response.sessions[1].start_time

    def test_focus_service_error_handling(self, service, sample_user_id, sample_task):
        """测试Service错误处理"""
        # 测试无效的请求
        with pytest.raises(Exception):
            # 这里可以测试各种边界情况
            invalid_request = StartFocusRequest(
                task_id=str(uuid4()),  # 不存在的任务
                session_type="invalid_type"  # 无效类型
            )
            service.start_focus(sample_user_id, invalid_request)