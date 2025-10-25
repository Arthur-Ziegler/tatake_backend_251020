"""
Focus领域Service层

提供番茄钟系统的核心业务逻辑，实现极简的会话管理。

Service职责：
1. 实现4个核心API的业务逻辑
2. 处理会话状态转换
3. 验证任务存在性
4. 协调Repository层操作

核心功能：
1. start: 开始新会话（自动关闭前一个会话）
2. pause: 暂停当前会话
3. resume: 恢复专注会话
4. complete: 完成当前会话

设计原则：
1. 极简化：不计算duration，不管理复杂状态
2. 自动化：内置自动关闭逻辑
3. 无状态：每次操作都是独立的
4. 验证优先：确保操作的有效性

作者：TaKeKe团队
版本：2.0.0 - 简化版本
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from sqlmodel import Session

from src.core.uuid_converter import UUIDConverter
from .models import FocusSession, SessionTypeConst
from .schemas import StartFocusRequest, FocusSessionResponse, FocusSessionListResponse
from .repository import FocusRepository
from .exceptions import FocusException

# 配置日志
logger = logging.getLogger(__name__)


def _build_session_response(session: FocusSession) -> Dict[str, Any]:
    """
    构建FocusSession响应，只包含6个核心字段

    Args:
        session: FocusSession数据库模型实例

    Returns:
        Dict[str, Any]: 响应数据字典
    """
    session_data = {
        'id': session.id,
        'user_id': session.user_id,
        'task_id': session.task_id,
        'session_type': session.session_type,
        'start_time': session.start_time,
        'end_time': session.end_time
    }
    return session_data


class FocusService:
    """
    专注会话业务服务

    提供极简的番茄钟会话管理：
    - 4个核心操作：start, pause, resume, complete
    - 自动会话状态管理
    - 任务关联验证
    """

    def __init__(self, session: Session):
        """
        初始化服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.repository = FocusRepository(session)

    def start_focus(self, user_id: Union[UUID, str], request: StartFocusRequest) -> Dict[str, Any]:
        """
        开始专注会话

        业务逻辑：
        1. 验证任务是否存在
        2. 创建新会话（Repository自动关闭前一个会话）
        3. 返回会话信息

        Args:
            user_id: 用户ID (UUID对象)
            request: 开始会话请求

        Returns:
            会话响应

        Raises:
            FocusException: 任务不存在或创建失败
        """
        try:
            # 验证任务是否存在（导入TaskRepository）
            from ..task.repository import TaskRepository
            task_repo = TaskRepository(self.session)
            task = task_repo.get_by_id(
                task_id=UUIDConverter.ensure_string(request.task_id),
                user_id=UUIDConverter.ensure_string(user_id)
            )
            if not task:
                raise FocusException(f"任务不存在或无权限: {request.task_id}", status_code=404)

            # 创建新会话
            focus_session = FocusSession(
                user_id=UUIDConverter.ensure_string(user_id),
                task_id=UUIDConverter.ensure_string(request.task_id),
                session_type=request.session_type,
                start_time=datetime.now(timezone.utc)
            )
            created_session = self.repository.create(focus_session)

            logger.info(f"用户 {user_id} 开始会话 {created_session.id} 类型: {request.session_type}")
            return _build_session_response(created_session)

        except FocusException:
            raise
        except Exception as e:
            logger.error(f"开始会话失败: {e}")
            raise FocusException("开始会话失败", status_code=500)

    def pause_focus(self, session_id: Union[UUID, str], user_id: Union[UUID, str]) -> Dict[str, Any]:
        """
        暂停专注会话

        业务逻辑：
        1. 验证原会话是否存在且属于当前用户
        2. 完成原会话
        3. 创建新的pause类型会话

        Args:
            session_id: 要暂停的会话ID
            user_id: 用户ID

        Returns:
            新的暂停会话响应

        Raises:
            FocusException: 会话不存在或操作失败
        """
        try:
            # 转换UUID为字符串用于数据库查询
            session_id_str = UUIDConverter.ensure_string(session_id)
            user_id_str = UUIDConverter.ensure_string(user_id)

            # 获取并验证原会话
            original_session = self.repository.get_by_id(session_id_str)
            if not original_session or original_session.user_id != user_id_str:
                raise FocusException("会话不存在或无权限", status_code=404)

            if not original_session.is_active:
                raise FocusException("只能暂停进行中的会话", status_code=400)

            # 完成原会话
            completed_session = self.repository.complete_session(session_id_str, user_id_str)
            if not completed_session:
                raise FocusException("完成原会话失败", status_code=500)

            # 创建暂停会话
            pause_session = FocusSession(
                user_id=user_id_str,
                task_id=original_session.task_id,
                session_type="pause",
                start_time=datetime.now(timezone.utc)
            )
            created_session = self.repository.create(pause_session)

            logger.info(f"用户 {user_id} 暂停会话 {session_id}，创建暂停会话 {created_session.id}")
            return _build_session_response(created_session)

        except FocusException:
            raise
        except Exception as e:
            logger.error(f"暂停会话失败: {e}")
            raise FocusException("暂停会话失败", status_code=500)

    def resume_focus(self, session_id: Union[UUID, str], user_id: Union[UUID, str]) -> Dict[str, Any]:
        """
        恢复专注会话

        业务逻辑：
        1. 验证暂停会话是否存在且属于当前用户
        2. 完成暂停会话
        3. 创建新的focus类型会话

        Args:
            session_id: 暂停会话ID
            user_id: 用户ID

        Returns:
            新的专注会话响应

        Raises:
            FocusException: 会话不存在或操作失败
        """
        try:
            # 转换UUID为字符串用于数据库查询
            session_id_str = UUIDConverter.ensure_string(session_id)
            user_id_str = UUIDConverter.ensure_string(user_id)

            # 获取并验证暂停会话
            pause_session = self.repository.get_by_id(session_id_str)
            if not pause_session or pause_session.user_id != user_id_str:
                raise FocusException("暂停会话不存在或无权限", status_code=404)

            if not pause_session.is_active:
                raise FocusException("只能恢复进行中的暂停会话", status_code=400)

            if pause_session.session_type != "pause":
                raise FocusException("只能从暂停会话恢复", status_code=400)

            # 完成暂停会话
            completed_pause = self.repository.complete_session(session_id_str, user_id_str)
            if not completed_pause:
                raise FocusException("完成暂停会话失败", status_code=500)

            # 创建新的专注会话
            focus_session = FocusSession(
                user_id=user_id_str,
                task_id=pause_session.task_id,
                session_type="focus",
                start_time=datetime.now(timezone.utc)
            )
            created_session = self.repository.create(focus_session)

            logger.info(f"用户 {user_id} 恢复会话，从暂停会话 {session_id} 创建专注会话 {created_session.id}")
            return _build_session_response(created_session)

        except FocusException:
            raise
        except Exception as e:
            logger.error(f"恢复会话失败: {e}")
            raise FocusException("恢复会话失败", status_code=500)

    def complete_focus(self, session_id: Union[UUID, str], user_id: Union[UUID, str]) -> Dict[str, Any]:
        """
        完成专注会话

        业务逻辑：
        1. 验证会话是否存在且属于当前用户
        2. 完成会话

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            完成的会话响应

        Raises:
            FocusException: 会话不存在或操作失败
        """
        try:
            # 转换UUID为字符串用于数据库查询
            session_id_str = UUIDConverter.ensure_string(session_id)
            user_id_str = UUIDConverter.ensure_string(user_id)

            # 验证会话存在
            session = self.repository.get_by_id(session_id_str)
            if not session or session.user_id != user_id_str:
                raise FocusException("会话不存在或无权限", status_code=404)

            # 完成会话
            completed_session = self.repository.complete_session(session_id_str, user_id_str)
            if not completed_session:
                raise FocusException("完成会话失败", status_code=500)

            logger.info(f"用户 {user_id} 完成会话 {session_id}")
            return _build_session_response(completed_session)

        except FocusException:
            raise
        except Exception as e:
            logger.error(f"完成会话失败: {e}")
            raise FocusException("完成会话失败", status_code=500)

    def get_user_sessions(
        self,
        user_id: Union[UUID, str],
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        获取用户会话列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页大小

        Returns:
            会话列表响应
        """
        try:
            user_id_str = UUIDConverter.ensure_string(user_id)
            sessions, total = self.repository.get_user_sessions(user_id_str, page, page_size)
            session_responses = [_build_session_response(session) for session in sessions]

            has_more = page * page_size < total
            return {
                "sessions": session_responses,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": has_more
            }

        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return {
                "sessions": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False
            }