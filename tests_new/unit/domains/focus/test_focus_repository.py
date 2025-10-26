"""
Focus领域Repository层测试

测试FocusRepository的数据库操作，包括：
1. CRUD操作
2. 查询优化
3. 事务处理
4. 自动关闭逻辑

遵循模块化设计原则，将Repository层的测试与Model和Service层分离。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from typing import List

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from src.domains.focus.models import FocusSession, SessionTypeConst
from src.domains.focus.repository import FocusRepository


@pytest.mark.unit
class TestFocusRepository:
    """FocusRepository测试类"""

    @pytest.fixture
    def repository(self, test_db_session):
        """创建Repository实例"""
        return FocusRepository(test_db_session)

    @pytest.fixture
    def sample_user_id(self) -> str:
        """示例用户ID"""
        return str(uuid4())

    @pytest.fixture
    def sample_task_id(self) -> str:
        """示例任务ID"""
        return str(uuid4())

    def test_create_focus_session(self, repository, sample_user_id, sample_task_id):
        """测试创建Focus会话"""
        session_data = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )

        created_session = repository.create(session_data)

        # 验证创建结果
        assert created_session.id is not None
        assert created_session.user_id == sample_user_id
        assert created_session.task_id == sample_task_id
        assert created_session.session_type == SessionTypeConst.FOCUS
        assert created_session.end_time is None  # 活跃会话
        assert created_session.start_time is not None

    def test_create_session_auto_close_previous(self, repository, sample_user_id, sample_task_id):
        """测试创建会话时自动关闭之前的活跃会话"""
        # 创建第一个会话
        first_session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_first = repository.create(first_session)
        assert created_first.end_time is None

        # 创建第二个会话，应该自动关闭第一个
        second_session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.BREAK
        )
        created_second = repository.create(second_session)

        # 验证第一个会话被自动关闭
        first_session_reloaded = repository.get_by_id(created_first.id)
        assert first_session_reloaded.end_time is not None

        # 验证第二个会话活跃
        assert created_second.end_time is None

    def test_get_focus_session_by_id(self, repository, sample_user_id, sample_task_id):
        """测试根据ID获取Focus会话"""
        # 创建会话
        session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_session = repository.create(session)

        # 根据ID获取
        retrieved_session = repository.get_by_id(created_session.id)

        assert retrieved_session is not None
        assert retrieved_session.id == created_session.id
        assert retrieved_session.user_id == sample_user_id
        assert retrieved_session.task_id == sample_task_id

    def test_get_active_session_by_user(self, repository, sample_user_id, sample_task_id):
        """测试获取用户的活跃会话"""
        # 创建活跃会话
        active_session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_active = repository.create(active_session)

        # 获取活跃会话
        retrieved_active = repository.get_active_session(sample_user_id)

        assert retrieved_active is not None
        assert retrieved_active.id == created_active.id
        assert retrieved_active.end_time is None

    def test_get_active_session_none_when_completed(self, repository, sample_user_id, sample_task_id):
        """测试当会话已完成时，活跃会话返回None"""
        # 创建并完成会话
        session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_session = repository.create(session)

        # 完成会话
        repository.complete_session(created_session.id, sample_user_id)

        # 获取活跃会话应该返回None
        active_session = repository.get_active_session(sample_user_id)
        assert active_session is None

    def test_complete_session(self, repository, sample_user_id, sample_task_id):
        """测试完成会话"""
        # 创建活跃会话
        session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_session = repository.create(session)
        assert created_session.end_time is None

        # 完成会话
        completed_session = repository.complete_session(created_session.id, sample_user_id)

        assert completed_session is not None
        assert completed_session.end_time is not None
        assert completed_session.end_time > completed_session.start_time

    def test_complete_session_wrong_user(self, repository, sample_user_id, sample_task_id):
        """测试完成会话时用户ID不匹配"""
        other_user_id = str(uuid4())

        # 创建活跃会话
        session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_session = repository.create(session)

        # 尝试用错误的用户ID完成会话
        result = repository.complete_session(created_session.id, other_user_id)
        assert result is None

    def test_complete_session_not_found(self, repository, sample_user_id):
        """测试完成不存在的会话"""
        fake_session_id = str(uuid4())
        result = repository.complete_session(fake_session_id, sample_user_id)
        assert result is None

    def test_get_user_sessions_with_pagination(self, repository, sample_user_id, sample_task_id):
        """测试获取用户会话列表（分页）"""
        # 创建多个会话
        sessions = []
        for i in range(5):
            session = FocusSession(
                user_id=sample_user_id,
                task_id=sample_task_id,
                session_type=SessionTypeConst.FOCUS,
                start_time=datetime.now(timezone.utc) - timedelta(hours=i+1)
            )
            created = repository.create(session)
            sessions.append(created)

        # 完成前3个会话
        for i in range(3):
            repository.complete_session(sessions[i].id, sample_user_id)

        # 获取第一页
        page_sessions, total = repository.get_user_sessions(
            sample_user_id, page=1, page_size=2
        )
        assert len(page_sessions) == 2
        assert total == 5
        # 按时间倒序，最新的在前
        assert page_sessions[0].start_time > page_sessions[1].start_time

        # 获取第二页
        page_sessions_2, total_2 = repository.get_user_sessions(
            sample_user_id, page=2, page_size=2
        )
        assert len(page_sessions_2) == 2
        assert total_2 == 5

    def test_get_user_sessions_with_type_filter(self, repository, sample_user_id, sample_task_id):
        """测试根据类型过滤用户会话"""
        # 创建不同类型的会话
        focus_session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_focus = repository.create(focus_session)

        break_session = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.BREAK
        )
        created_break = repository.create(break_session)

        # 完成break会话
        repository.complete_session(created_break.id, sample_user_id)

        # 只获取FOCUS类型的会话
        focus_sessions, total = repository.get_user_sessions(
            sample_user_id, session_type=SessionTypeConst.FOCUS
        )
        assert len(focus_sessions) == 1
        assert focus_sessions[0].session_type == SessionTypeConst.FOCUS
        assert total == 1

        # 只获取BREAK类型的会话
        break_sessions, total = repository.get_user_sessions(
            sample_user_id, session_type=SessionTypeConst.BREAK
        )
        assert len(break_sessions) == 1
        assert break_sessions[0].session_type == SessionTypeConst.BREAK
        assert total == 1

    def test_get_sessions_by_task(self, repository, sample_user_id, sample_task_id):
        """测试获取特定任务的会话列表"""
        other_task_id = str(uuid4())

        # 为不同任务创建会话
        task1_session1 = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_task1_1 = repository.create(task1_session1)

        task1_session2 = FocusSession(
            user_id=sample_user_id,
            task_id=sample_task_id,
            session_type=SessionTypeConst.BREAK
        )
        created_task1_2 = repository.create(task1_session2)

        task2_session = FocusSession(
            user_id=sample_user_id,
            task_id=other_task_id,
            session_type=SessionTypeConst.FOCUS
        )
        created_task2 = repository.create(task2_session)

        # 获取第一个任务的会话
        task1_sessions = repository.get_sessions_by_task(sample_user_id, sample_task_id)
        assert len(task1_sessions) == 2
        session_ids = {s.id for s in task1_sessions}
        assert session_ids == {created_task1_1.id, created_task1_2.id}

        # 获取第二个任务的会话
        task2_sessions = repository.get_sessions_by_task(sample_user_id, other_task_id)
        assert len(task2_sessions) == 1
        assert task2_sessions[0].id == created_task2.id

    def test_get_sessions_by_task_empty_result(self, repository, sample_user_id):
        """测试获取不存在任务的会话列表"""
        fake_task_id = str(uuid4())
        sessions = repository.get_sessions_by_task(sample_user_id, fake_task_id)
        assert sessions == []

    def test_repository_error_handling(self, repository, sample_user_id, sample_task_id):
        """测试Repository错误处理"""
        # 测试创建无效会话（空用户ID）
        with pytest.raises(Exception):
            invalid_session = FocusSession(
                user_id="",  # 空字符串可能导致数据库约束错误
                task_id=sample_task_id,
                session_type=SessionTypeConst.FOCUS
            )
            repository.create(invalid_session)