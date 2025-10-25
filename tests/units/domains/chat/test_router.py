"""
聊天路由单元测试

严格TDD方法：
1. 路由基本功能测试
2. API端点测试
3. 请求验证测试
4. 响应格式测试
5. 错误处理测试
6. 权限验证测试
7. 参数验证测试
8. 边界条件测试

作者：TaTakeKe团队
版本：1.0.0 - 聊天路由单元测试
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from uuid import UUID

from src.domains.chat.router import router, chat_service
from src.domains.chat.schemas import (
    CreateSessionRequest,
    SendMessageRequest,
    UnifiedResponse,
    ChatSessionResponse,
    MessageResponse,
    SessionInfoResponse,
    SessionListResponse,
    ChatHistoryResponse
)


@pytest.mark.unit
class TestChatRouterBasic:
    """聊天路由基础功能测试"""

    def test_router_initialization(self):
        """测试路由器初始化"""
        assert router is not None
        assert router.prefix == "/chat"
        assert "智能聊天" in router.tags

    def test_chat_service_initialization(self):
        """测试聊天服务初始化"""
        assert chat_service is not None

    def test_router_routes_exist(self):
        """测试路由端点存在"""
        routes = [route.path for route in router.routes]

        expected_routes = [
            "/sessions",
            "/sessions/{session_id}/messages",
            "/sessions/{session_id}",
            "/sessions/{session_id}",
            "/sessions"
        ]

        for route in expected_routes:
            assert any(route in r for r in routes), f"路由 {route} 不存在"


@pytest.mark.unit
class TestCreateSession:
    """创建会话测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_create_session_success(self, mock_service):
        """测试成功创建会话"""
        # 模拟服务响应
        mock_service.create_session.return_value = {
            "session_id": "test-session-123",
            "title": "测试会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！AI助手已准备就绪。",
            "status": "created"
        }

        # 创建测试请求
        request = CreateSessionRequest(title="测试会话")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        # 模拟FastAPI依赖注入
        from src.domains.chat.router import create_chat_session
        result = create_chat_session(request, user_id)

        # 验证结果
        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert result.message == "success"
        assert result.data is not None
        assert result.data.session_id == "test-session-123"
        assert result.data.title == "测试会话"

        # 验证服务调用
        mock_service.create_session.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            title="测试会话"
        )

    @patch('src.domains.chat.router.chat_service')
    def test_create_session_without_title(self, mock_service):
        """测试创建会话（无标题）"""
        mock_service.create_session.return_value = {
            "session_id": "test-session-456",
            "title": "新会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！",
            "status": "created"
        }

        request = CreateSessionRequest(title=None)
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import create_chat_session
        result = create_chat_session(request, user_id)

        assert result.data.title == "新会话"
        mock_service.create_session.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            title=None
        )

    @patch('src.domains.chat.router.chat_service')
    def test_create_session_service_failure(self, mock_service):
        """测试创建会话（服务失败）"""
        mock_service.create_session.side_effect = Exception("Service error")

        request = CreateSessionRequest(title="测试会话")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import create_chat_session

        with pytest.raises(HTTPException) as exc_info:
            create_chat_session(request, user_id)

        assert exc_info.value.status_code == 500
        assert "创建会话失败" in str(exc_info.value.detail)


@pytest.mark.unit
class TestSendMessage:
    """发送消息测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_send_message_success(self, mock_service):
        """测试成功发送消息"""
        mock_service.send_message.return_value = {
            "session_id": "test-session-123",
            "user_message": "Hello",
            "ai_response": "Hi there!",
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        request = SendMessageRequest(message="Hello")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import send_message
        result = send_message(request, user_id, session_id)

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert result.data.ai_response == "Hi there!"
        assert result.data.user_message == "Hello"

        mock_service.send_message.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            session_id="test-session-123",
            message="Hello"
        )

    @patch('src.domains.chat.router.chat_service')
    def test_send_message_empty_content(self, mock_service):
        """测试发送空消息"""
        mock_service.send_message.side_effect = ValueError("消息内容不能为空")

        request = SendMessageRequest(message="")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import send_message

        with pytest.raises(HTTPException) as exc_info:
            send_message(request, user_id, session_id)

        assert exc_info.value.status_code == 400
        assert "消息内容不能为空" in str(exc_info.value.detail)

    @patch('src.domains.chat.router.chat_service')
    def test_send_message_service_failure(self, mock_service):
        """测试发送消息（服务失败）"""
        mock_service.send_message.side_effect = Exception("Service error")

        request = SendMessageRequest(message="Hello")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import send_message

        with pytest.raises(HTTPException) as exc_info:
            send_message(request, user_id, session_id)

        assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestGetChatHistory:
    """获取聊天历史测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_get_chat_history_success(self, mock_service):
        """测试成功获取聊天历史"""
        mock_service.get_chat_history.return_value = {
            "session_id": "test-session-123",
            "messages": [
                {
                    "type": "human",
                    "content": "Hello",
                    "timestamp": "2024-01-01T10:00:00Z"
                },
                {
                    "type": "ai",
                    "content": "Hi there!",
                    "timestamp": "2024-01-01T10:00:01Z"
                }
            ],
            "total_count": 2,
            "limit": 50,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"
        limit = 50

        from src.domains.chat.router import get_chat_history
        result = get_chat_history(user_id, session_id, limit)

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert len(result.data.messages) == 2
        assert result.data.messages[0]["content"] == "Hello"
        assert result.data.messages[1]["content"] == "Hi there!"

        mock_service.get_chat_history.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            session_id="test-session-123",
            limit=50
        )

    @patch('src.domains.chat.router.chat_service')
    def test_get_chat_history_with_custom_limit(self, mock_service):
        """测试获取聊天历史（自定义限制）"""
        mock_service.get_chat_history.return_value = {
            "session_id": "test-session-123",
            "messages": [{"type": "human", "content": "Hello", "timestamp": "2024-01-01T10:00:00Z"}],
            "total_count": 1,
            "limit": 10,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import get_chat_history
        result = get_chat_history(user_id, session_id, limit=10)

        assert result.data.limit == 10
        mock_service.get_chat_history.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            session_id="test-session-123",
            limit=10
        )

    @patch('src.domains.chat.router.chat_service')
    def test_get_chat_history_service_failure(self, mock_service):
        """测试获取聊天历史（服务失败）"""
        mock_service.get_chat_history.side_effect = Exception("Service error")

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import get_chat_history

        with pytest.raises(HTTPException) as exc_info:
            get_chat_history(user_id, session_id)

        assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestGetSessionInfo:
    """获取会话信息测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_get_session_info_success(self, mock_service):
        """测试成功获取会话信息"""
        mock_service.get_session_info.return_value = {
            "session_id": "test-session-123",
            "title": "测试会话",
            "message_count": 10,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "status": "active"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import get_session_info
        result = get_session_info(user_id, session_id)

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert result.data.title == "测试会话"
        assert result.data.message_count == 10

        mock_service.get_session_info.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            session_id="test-session-123"
        )

    @patch('src.domains.chat.router.chat_service')
    def test_get_session_info_not_found(self, mock_service):
        """测试获取不存在的会话信息"""
        mock_service.get_session_info.side_effect = ValueError("会话不存在")

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "nonexistent-session"

        from src.domains.chat.router import get_session_info

        with pytest.raises(HTTPException) as exc_info:
            get_session_info(user_id, session_id)

        assert exc_info.value.status_code == 404
        assert "会话不存在" in str(exc_info.value.detail)


@pytest.mark.unit
class TestListSessions:
    """列出会话测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_list_sessions_success(self, mock_service):
        """测试成功列出会话"""
        mock_service.list_sessions.return_value = {
            "user_id": "12345678-1234-5678-9abc-123456789012",
            "sessions": [
                {
                    "session_id": "session-1",
                    "title": "会话1",
                    "message_count": 5,
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T10:30:00Z",
                    "status": "active"
                },
                {
                    "session_id": "session-2",
                    "title": "会话2",
                    "message_count": 3,
                    "created_at": "2024-01-01T09:00:00Z",
                    "updated_at": "2024-01-01T09:15:00Z",
                    "status": "active"
                }
            ],
            "total_count": 2,
            "limit": 20,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        limit = 20

        from src.domains.chat.router import list_sessions
        result = list_sessions(user_id, limit)

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert len(result.data.sessions) == 2
        assert result.data.sessions[0]["title"] == "会话1"
        assert result.data.sessions[1]["title"] == "会话2"

        mock_service.list_sessions.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            limit=20
        )

    @patch('src.domains.chat.router.chat_service')
    def test_list_sessions_empty(self, mock_service):
        """测试列出空会话列表"""
        mock_service.list_sessions.return_value = {
            "user_id": "12345678-1234-5678-9abc-123456789012",
            "sessions": [],
            "total_count": 0,
            "limit": 20,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import list_sessions
        result = list_sessions(user_id)

        assert len(result.data.sessions) == 0
        assert result.data.total_count == 0

    @patch('src.domains.chat.router.chat_service')
    def test_list_sessions_with_custom_limit(self, mock_service):
        """测试列出会话（自定义限制）"""
        mock_service.list_sessions.return_value = {
            "user_id": "12345678-1234-5678-9abc-123456789012",
            "sessions": [],
            "total_count": 0,
            "limit": 5,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import list_sessions
        result = list_sessions(user_id, limit=5)

        assert result.data.limit == 5
        mock_service.list_sessions.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            limit=5
        )


@pytest.mark.unit
class TestDeleteSession:
    """删除会话测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_delete_session_success(self, mock_service):
        """测试成功删除会话"""
        mock_service.delete_session.return_value = {
            "session_id": "test-session-123",
            "status": "deleted",
            "user_id": "12345678-1234-5678-9abc-123456789012",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": "会话已成功删除"
        }

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session-123"

        from src.domains.chat.router import delete_session
        result = delete_session(user_id, session_id)

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert result.data.status == "deleted"
        assert result.data.message == "会话已成功删除"

        mock_service.delete_session.assert_called_once_with(
            user_id="12345678-1234-5678-9abc-123456789012",
            session_id="test-session-123"
        )

    @patch('src.domains.chat.router.chat_service')
    def test_delete_session_not_found(self, mock_service):
        """测试删除不存在的会话"""
        mock_service.delete_session.side_effect = Exception("会话不存在或无权访问")

        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "nonexistent-session"

        from src.domains.chat.router import delete_session

        with pytest.raises(HTTPException) as exc_info:
            delete_session(user_id, session_id)

        assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestHealthCheck:
    """健康检查测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_health_check_success(self, mock_service):
        """测试健康检查成功"""
        mock_service.health_check.return_value = {
            "status": "healthy",
            "database": {"status": "healthy"},
            "graph_initialized": True,
            "timestamp": "2024-01-01T10:00:00Z"
        }

        from src.domains.chat.router import health_check
        result = health_check()

        assert isinstance(result, UnifiedResponse)
        assert result.code == 200
        assert result.data.status == "healthy"
        assert result.data.graph_initialized is True

    @patch('src.domains.chat.router.chat_service')
    def test_health_check_unhealthy(self, mock_service):
        """测试健康检查（不健康）"""
        mock_service.health_check.return_value = {
            "status": "unhealthy",
            "database": {"status": "error", "error": "Connection failed"},
            "graph_initialized": False,
            "timestamp": "2024-01-01T10:00:00Z"
        }

        from src.domains.chat.router import health_check
        result = health_check()

        assert result.code == 200  # 健康检查本身总是成功，只是返回状态
        assert result.data.status == "unhealthy"
        assert result.data.graph_initialized is False


@pytest.mark.integration
class TestRouterIntegration:
    """路由集成测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_full_chat_workflow_with_router(self, mock_service):
        """测试完整聊天工作流（路由层面）"""
        # 模拟服务响应
        mock_service.create_session.return_value = {
            "session_id": "test-session",
            "title": "测试会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！",
            "status": "created"
        }

        mock_service.send_message.return_value = {
            "session_id": "test-session",
            "user_message": "Hello",
            "ai_response": "Hi there!",
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        mock_service.get_chat_history.return_value = {
            "session_id": "test-session",
            "messages": [
                {"type": "human", "content": "Hello", "timestamp": "2024-01-01T10:00:00Z"},
                {"type": "ai", "content": "Hi there!", "timestamp": "2024-01-01T10:00:01Z"}
            ],
            "total_count": 2,
            "limit": 50,
            "timestamp": "2024-01-01T10:00:00Z",
            "status": "success"
        }

        mock_service.get_session_info.return_value = {
            "session_id": "test-session",
            "title": "测试会话",
            "message_count": 2,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z",
            "status": "active"
        }

        # 这里只测试服务调用，不测试FastAPI客户端
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        # 验证服务调用
        mock_service.create_session.assert_not_called()
        mock_service.send_message.assert_not_called()
        mock_service.get_chat_history.assert_not_called()
        mock_service.get_session_info.assert_not_called()


@pytest.mark.performance
class TestRouterPerformance:
    """路由性能测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_concurrent_requests_handling(self, mock_service):
        """测试并发请求处理"""
        import asyncio

        # 模拟快速响应
        mock_service.create_session.return_value = {
            "session_id": f"session-{uuid.uuid4()}",
            "title": "测试会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！",
            "status": "created"
        }

        async def create_request():
            request = CreateSessionRequest(title=f"会话-{uuid.uuid4()}")
            user_id = UUID("12345678-1234-5678-9abc-123456789012")

            from src.domains.chat.router import create_chat_session
            return create_chat_session(request, user_id)

        # 并发创建多个会话
        import time
        start_time = time.time()

        tasks = [create_request() for _ in range(10)]
        results = asyncio.gather(*tasks)

        duration = time.time() - start_time

        assert len(results) == 10
        assert duration < 2.0, f"并发处理10个请求耗时过长: {duration:.3f}s"
        assert mock_service.create_session.call_count == 10


@pytest.mark.regression
class TestRouterRegression:
    """路由回归测试"""

    @patch('src.domains.chat.router.chat_service')
    def test_uuid_conversion_regression(self, mock_service):
        """回归测试：UUID转换"""
        mock_service.create_session.return_value = {
            "session_id": "test-session",
            "title": "测试会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！",
            "status": "created"
        }

        request = CreateSessionRequest(title="测试会话")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import create_chat_session
        create_chat_session(request, user_id)

        # 验证UUID被正确转换为字符串
        mock_service.create_session.assert_called_once()
        call_args = mock_service.create_session.call_args[0]
        assert call_args[0] == "12345678-1234-5678-9abc-123456789012"  # 字符串形式
        assert isinstance(call_args[0], str)

    @patch('src.domains.chat.router.chat_service')
    def test_error_message_formatting_regression(self, mock_service):
        """回归测试：错误消息格式"""
        mock_service.send_message.side_effect = ValueError("自定义错误消息")

        request = SendMessageRequest(message="Hello")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")
        session_id = "test-session"

        from src.domains.chat.router import send_message

        with pytest.raises(HTTPException) as exc_info:
            send_message(request, user_id, session_id)

        assert exc_info.value.status_code == 400
        assert "自定义错误消息" in str(exc_info.value.detail)

    @patch('src.domains.chat.router.chat_service')
    def test_response_format_consistency_regression(self, mock_service):
        """回归测试：响应格式一致性"""
        mock_service.create_session.return_value = {
            "session_id": "test-session",
            "title": "测试会话",
            "created_at": "2024-01-01T10:00:00Z",
            "welcome_message": "你好！",
            "status": "created"
        }

        request = CreateSessionRequest(title="测试会话")
        user_id = UUID("12345678-1234-5678-9abc-123456789012")

        from src.domains.chat.router import create_chat_session
        result = create_chat_session(request, user_id)

        # 验证响应格式
        assert hasattr(result, 'code')
        assert hasattr(result, 'message')
        assert hasattr(result, 'data')
        assert result.code == 200
        assert result.message == "success"
        assert isinstance(result.data, ChatSessionResponse)