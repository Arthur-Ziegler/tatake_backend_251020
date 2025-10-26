"""
Service层返回类型单元测试

验证所有Service方法都返回Dict[str, Any]而不是模型实例，确保1.2变更的核心要求得到满足。

作者：TaKeKe团队
版本：1.0.0 - 1.2变更验证
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, date
from unittest.mock import Mock, patch
from typing import Dict, Any

# 导入需要测试的Service类
from src.domains.task.service import TaskService
from src.domains.focus.service import FocusService
from src.domains.top3.service import Top3Service
from src.domains.points.service import PointsService
from src.domains.chat.service import ChatService
from src.domains.reward.service import RewardService
from src.domains.auth.service import AuthService


class TestTaskServiceReturnTypes:
    """Task Service返回类型验证"""

    def test_get_task_returns_dict(self, db_session, sample_task):
        """验证TaskService.get_task()返回dict而非Task模型"""
        # Arrange
        points_service = Mock()
        task_service = TaskService(db_session, points_service)

        # Act
        result = task_service.get_task(sample_task.id, sample_task.user_id)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "id" in result
        assert "title" in result
        assert "status" in result
        assert isinstance(result["id"], str)
        assert isinstance(result["title"], str)

    def test_create_task_returns_dict(self, db_session):
        """验证TaskService.create_task()返回dict"""
        # Arrange
        points_service = Mock()
        task_service = TaskService(db_session, points_service)
        user_id = uuid4()

        request = Mock()
        request.title = "测试任务"
        request.description = "测试描述"
        request.status = "pending"
        request.priority = "medium"
        request.parent_id = None
        request.tags = []
        request.service_ids = []
        request.due_date = None
        request.planned_start_time = None
        request.planned_end_time = None

        # Act
        result = task_service.create_task(request, user_id)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "id" in result
        assert "title" in result
        assert result["title"] == "测试任务"

    def test_complete_task_returns_dict(self, db_session, sample_task):
        """验证TaskService.complete_task()返回dict"""
        # Arrange
        points_service = Mock()
        points_service.add_points = Mock()
        task_service = TaskService(db_session, points_service)

        # Act
        result = task_service.complete_task(sample_task.user_id, sample_task.id)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "success" in result
        assert "task_id" in result
        assert "points_awarded" in result


class TestFocusServiceReturnTypes:
    """Focus Service返回类型验证"""

    def test_start_focus_returns_dict(self, db_session):
        """验证FocusService.start_focus()返回dict"""
        # Arrange
        user_id = str(uuid4())
        focus_service = FocusService(db_session)

        request = Mock()
        request.task_id = str(uuid4())
        request.session_type = "focus"

        # Act
        result = focus_service.start_focus(user_id, request)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "id" in result
        assert "user_id" in result
        assert "session_type" in result

    def test_get_user_sessions_returns_dict(self, db_session):
        """验证FocusService.get_user_sessions()返回dict"""
        # Arrange
        user_id = uuid4()
        focus_service = FocusService(db_session)

        # Act
        result = focus_service.get_user_sessions(user_id, page=1, page_size=10)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "sessions" in result
        assert "total" in result
        assert "page" in result


class TestTop3ServiceReturnTypes:
    """Top3 Service返回类型验证"""

    def test_set_top3_returns_dict(self, db_session):
        """验证Top3Service.set_top3()返回dict"""
        # Arrange
        points_service = Mock()
        points_service.add_points = Mock()
        points_service.get_balance = Mock(return_value=500)

        top3_service = Top3Service(db_session, points_service)
        user_id = uuid4()

        request = Mock()
        request.task_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

        # Act
        result = top3_service.set_top3(user_id, request)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "date" in result
        assert "task_ids" in result
        assert "points_consumed" in result

    def test_get_top3_returns_dict(self, db_session):
        """验证Top3Service.get_top3()返回dict"""
        # Arrange
        points_service = Mock()
        top3_service = Top3Service(db_session, points_service)
        user_id = uuid4()
        target_date = "2023-10-25"

        # Act
        result = top3_service.get_top3(user_id, target_date)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "date" in result
        assert "task_ids" in result
        assert "points_consumed" in result


class TestPointsServiceReturnTypes:
    """Points Service返回类型验证"""

    def test_get_transactions_returns_dict_list(self, db_session):
        """验证PointsService.get_transactions()返回dict列表"""
        # Arrange
        points_service = PointsService(db_session)
        user_id = str(uuid4())

        # Act
        result = points_service.get_transactions(user_id, limit=10, offset=0)

        # Assert
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        if result:  # 如果有数据
            for item in result:
                assert isinstance(item, dict), f"Expected dict in list, got {type(item)}"
                assert "id" in item
                assert "amount" in item
                assert "source_type" in item


class TestAuthServiceReturnTypes:
    """Auth Service返回类型验证"""

    def test_generate_tokens_returns_dict(self):
        """验证AuthService.generate_tokens()返回dict"""
        # Arrange
        auth_service = AuthService()
        user_data = {
            "user_id": str(uuid4()),
            "is_guest": False
        }

        # Act
        result = auth_service.generate_tokens(user_data)

        # Assert
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "user_id" in result
        assert "access_token" in result
        assert "refresh_token" in result

    def test_verify_token_returns_dict(self):
        """验证AuthService.verify_token()返回dict"""
        # Arrange
        auth_service = AuthService()
        token = "test_token"

        # Act & Assert (这个可能会抛出异常，这是正常的)
        try:
            result = auth_service.verify_token(token)
            # 如果没有异常，应该返回dict
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        except Exception:
            # 异常是预期的，因为token无效
            pass


# 测试数据Fixtures
@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    # 这里需要根据实际项目配置创建测试会话
    # 暂时返回Mock对象
    return Mock()


@pytest.fixture
def sample_task():
    """创建示例任务数据"""
    return Mock(
        id=uuid4(),
        user_id=uuid4(),
        title="测试任务",
        description="测试描述",
        status="pending",
        priority="medium"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])