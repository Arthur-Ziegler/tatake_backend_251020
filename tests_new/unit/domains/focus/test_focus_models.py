"""
Focus领域模型测试

测试FocusSession模型的基本功能，采用极简设计：
1. 仅记录6个核心字段
2. 时区安全的时间处理
3. 简单的业务逻辑

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.domains.focus.models import FocusSession, SessionTypeConst


@pytest.mark.unit
class TestFocusSessionModel:
    """FocusSession模型测试类"""

    def test_focus_session_creation_minimal(self):
        """测试FocusSession最小化创建"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        focus_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )

        assert focus_session.id is not None
        assert focus_session.user_id == user_id
        assert focus_session.task_id == task_id
        assert focus_session.session_type == SessionTypeConst.FOCUS
        assert focus_session.start_time is not None
        assert focus_session.end_time is None  # 进行中的会话

    def test_focus_session_with_all_fields(self):
        """测试包含所有字段的FocusSession"""
        user_id = str(uuid4())
        task_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=25)

        focus_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS,
            start_time=start_time,
            end_time=end_time
        )

        assert focus_session.user_id == user_id
        assert focus_session.task_id == task_id
        assert focus_session.session_type == SessionTypeConst.FOCUS
        assert focus_session.start_time == start_time
        assert focus_session.end_time == end_time

    def test_focus_session_different_session_types(self):
        """测试不同会话类型的FocusSession"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        # 测试专注会话
        focus_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )
        assert focus_session.session_type == SessionTypeConst.FOCUS
        assert focus_session.end_time is None  # 进行中

        # 测试短休息
        break_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.BREAK
        )
        assert break_session.session_type == SessionTypeConst.BREAK
        assert break_session.end_time is None  # 进行中

        # 测试长休息
        long_break_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.LONG_BREAK
        )
        assert long_break_session.session_type == SessionTypeConst.LONG_BREAK
        assert long_break_session.end_time is None  # 进行中

        # 测试暂停
        pause_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.PAUSE
        )
        assert pause_session.session_type == SessionTypeConst.PAUSE
        assert pause_session.end_time is None  # 进行中

    def test_focus_session_timestamps(self):
        """测试时间戳自动生成和手动设置"""
        user_id = str(uuid4())
        task_id = str(uuid4())
        before_creation = datetime.now(timezone.utc)

        # 测试自动生成start_time
        auto_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )

        after_creation = datetime.now(timezone.utc)
        assert before_creation <= auto_session.start_time <= after_creation

        # 测试手动设置时间
        manual_start_time = datetime.now(timezone.utc)
        manual_end_time = manual_start_time + timedelta(minutes=25)

        manual_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS,
            start_time=manual_start_time,
            end_time=manual_end_time
        )

        assert manual_session.start_time == manual_start_time
        assert manual_session.end_time == manual_end_time

    def test_focus_session_string_representation(self):
        """测试字符串表示"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )

        repr_str = repr(session)

        # 验证字符串包含关键信息
        assert "FocusSession" in repr_str
        assert str(session.id) in repr_str
        assert SessionTypeConst.FOCUS in repr_str

    def test_focus_session_active_by_default(self):
        """测试FocusSession默认为进行中状态"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )

        # end_time为None表示会话正在进行中
        assert session.end_time is None

    def test_focus_session_uuid_fields(self):
        """测试UUID字段处理"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )

        # 验证UUID可以正确存储和访问
        assert session.id is not None
        assert isinstance(session.id, str)

        # 验证传入的UUID可以正确存储
        manual_id = str(uuid4())
        manual_session = FocusSession(
            id=manual_id,
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )
        assert manual_session.id == manual_id

    def test_focus_session_timezone_aware(self):
        """测试时区感知的datetime"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        # 测试时区感知的时间
        utc_time = datetime.now(timezone.utc)
        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS,
            start_time=utc_time
        )

        assert session.start_time.tzinfo is not None
        assert session.start_time.tzinfo == timezone.utc

    def test_focus_session_completion_detection(self):
        """测试会话完成检测逻辑"""
        user_id = str(uuid4())
        task_id = str(uuid4())

        # 进行中的会话（end_time为None）
        active_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS
        )
        assert active_session.end_time is None

        # 已完成的会话（有end_time）
        completed_session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            session_type=SessionTypeConst.FOCUS,
            end_time=datetime.now(timezone.utc)
        )
        assert completed_session.end_time is not None