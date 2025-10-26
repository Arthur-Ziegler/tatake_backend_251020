"""
Chat域Schemas单元测试

严格TDD方法：
1. 请求模型测试
2. 响应模型测试
3. 数据验证测试
4. 字段验证测试
5. 序列化测试
6. 边界条件测试
7. 错误处理测试

作者：TaTakeKe团队
版本：1.0.0 - Schemas单元测试
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from src.domains.chat.schemas import (
    CreateSessionRequest,
    SendMessageRequest,
    ChatSessionResponse,
    MessageResponse,
    ChatMessageItem,
    ChatHistoryResponse,
    SessionInfoResponse,
    ChatSessionItem,
    SessionListResponse,
    DeleteSessionResponse,
    ChatHealthResponse
)


@pytest.mark.unit
class TestCreateSessionRequest:
    """创建会话请求模型测试类"""

    def test_create_session_request_with_title(self):
        """测试带标题的创建会话请求"""
        request = CreateSessionRequest(title="测试会话")

        assert request.title == "测试会话"
        assert isinstance(request, CreateSessionRequest)

    def test_create_session_request_without_title(self):
        """测试不带标题的创建会话请求"""
        request = CreateSessionRequest()

        assert request.title is None
        assert isinstance(request, CreateSessionRequest)

    def test_create_session_request_empty_title(self):
        """测试空标题"""
        request = CreateSessionRequest(title="")

        assert request.title == ""

    def test_create_session_request_long_title(self):
        """测试长标题"""
        long_title = "这是一个很长的会话标题" * 10
        request = CreateSessionRequest(title=long_title)

        assert request.title == long_title

    def test_create_session_request_serialization(self):
        """测试序列化"""
        request = CreateSessionRequest(title="测试会话")
        data = request.model_dump()

        assert isinstance(data, dict)
        assert data["title"] == "测试会话"

    def test_create_session_request_json_schema(self):
        """测试JSON Schema"""
        schema = CreateSessionRequest.model_json_schema()

        assert isinstance(schema, dict)
        assert "title" in schema["properties"]
        assert "title" in schema.get("example", {})


@pytest.mark.unit
class TestSendMessageRequest:
    """发送消息请求模型测试类"""

    def test_send_message_request_valid(self):
        """测试有效的发送消息请求"""
        request = SendMessageRequest(message="你好，世界！")

        assert request.message == "你好，世界！"
        assert isinstance(request, SendMessageRequest)

    def test_send_message_request_with_whitespace(self):
        """测试带空格的消息"""
        request = SendMessageRequest(message="  你好，世界！  ")

        assert request.message == "你好，世界！"  # 应该被strip处理

    def test_send_message_request_empty_message(self):
        """测试空消息"""
        with pytest.raises(ValidationError) as exc_info:
            SendMessageRequest(message="")

        assert "消息内容不能为空" in str(exc_info.value)

    def test_send_message_request_whitespace_only(self):
        """测试只有空格的消息"""
        with pytest.raises(ValidationError) as exc_info:
            SendMessageRequest(message="   ")

        assert "消息内容不能为空" in str(exc_info.value)

    def test_send_message_request_none_message(self):
        """测试None消息"""
        with pytest.raises(ValidationError) as exc_info:
            SendMessageRequest(message=None)

        # None值会在类型检查阶段失败，不是我们的自定义验证
        assert "Input should be a valid string" in str(exc_info.value)

    def test_send_message_request_serialization(self):
        """测试序列化"""
        request = SendMessageRequest(message="测试消息")
        data = request.model_dump()

        assert isinstance(data, dict)
        assert data["message"] == "测试消息"

    def test_send_message_request_json_schema(self):
        """测试JSON Schema"""
        schema = SendMessageRequest.model_json_schema()

        assert isinstance(schema, dict)
        assert "message" in schema["properties"]
        assert "message" in schema.get("example", {})

    def test_send_message_request_validator_function(self):
        """测试字段验证函数"""
        # 正常情况
        request = SendMessageRequest(message="正常消息")
        assert request.message == "正常消息"

        # 空格情况
        request = SendMessageRequest(message="  正常消息  ")
        assert request.message == "正常消息"


@pytest.mark.unit
class TestChatSessionResponse:
    """聊天会话响应模型测试类"""

    @pytest.fixture
    def sample_session_response_data(self):
        """提供示例会话响应数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "测试会话",
            "created_at": "2024-01-01T12:00:00Z",
            "welcome_message": "你好！我是AI助手。",
            "status": "created"
        }

    def test_chat_session_response_creation(self, sample_session_response_data):
        """测试创建会话响应"""
        response = ChatSessionResponse(**sample_session_response_data)

        assert response.session_id == sample_session_response_data["session_id"]
        assert response.title == sample_session_response_data["title"]
        assert response.created_at == sample_session_response_data["created_at"]
        assert response.welcome_message == sample_session_response_data["welcome_message"]
        assert response.status == sample_session_response_data["status"]

    def test_chat_session_response_serialization(self, sample_session_response_data):
        """测试序列化"""
        response = ChatSessionResponse(**sample_session_response_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert data == sample_session_response_data

    def test_chat_session_response_json_schema(self):
        """测试JSON Schema"""
        schema = ChatSessionResponse.model_json_schema()

        required_fields = ["session_id", "title", "created_at", "welcome_message", "status"]
        for field in required_fields:
            assert field in schema["required"]

    def test_chat_session_response_missing_required_field(self):
        """测试缺少必需字段"""
        with pytest.raises(ValidationError):
            ChatSessionResponse(
                session_id="123",
                title="测试"
                # 缺少其他必需字段
            )

    def test_chat_session_response_invalid_session_id(self):
        """测试无效的session_id类型"""
        with pytest.raises(ValidationError):
            ChatSessionResponse(
                session_id=123,  # 应该是字符串
                title="测试",
                created_at="2024-01-01T12:00:00Z",
                welcome_message="测试",
                status="created"
            )


@pytest.mark.unit
class TestMessageResponse:
    """消息响应模型测试类"""

    @pytest.fixture
    def sample_message_response_data(self):
        """提供示例消息响应数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_message": "你好",
            "ai_response": "你好！有什么可以帮助你的吗？",
            "timestamp": "2024-01-01T12:01:00Z",
            "status": "success"
        }

    def test_message_response_creation(self, sample_message_response_data):
        """测试创建消息响应"""
        response = MessageResponse(**sample_message_response_data)

        assert response.session_id == sample_message_response_data["session_id"]
        assert response.user_message == sample_message_response_data["user_message"]
        assert response.ai_response == sample_message_response_data["ai_response"]
        assert response.timestamp == sample_message_response_data["timestamp"]
        assert response.status == sample_message_response_data["status"]

    def test_message_response_serialization(self, sample_message_response_data):
        """测试序列化"""
        response = MessageResponse(**sample_message_response_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert data == sample_message_response_data

    def test_message_response_json_schema(self):
        """测试JSON Schema"""
        schema = MessageResponse.model_json_schema()

        required_fields = ["session_id", "user_message", "ai_response", "timestamp", "status"]
        for field in required_fields:
            assert field in schema["required"]


@pytest.mark.unit
class TestChatMessageItem:
    """聊天消息项模型测试类"""

    @pytest.fixture
    def sample_message_item_data(self):
        """提供示例消息项数据"""
        return {
            "type": "human",
            "content": "测试消息内容",
            "timestamp": "2024-01-01T12:01:00Z"
        }

    def test_message_item_creation(self, sample_message_item_data):
        """测试创建消息项"""
        item = ChatMessageItem(**sample_message_item_data)

        assert item.type == sample_message_item_data["type"]
        assert item.content == sample_message_item_data["content"]
        assert item.timestamp == sample_message_item_data["timestamp"]

    def test_message_item_ai_type(self):
        """测试AI类型消息"""
        item = ChatMessageItem(
            type="ai",
            content="AI回复",
            timestamp="2024-01-01T12:02:00Z"
        )

        assert item.type == "ai"
        assert item.content == "AI回复"

    def test_message_item_serialization(self, sample_message_item_data):
        """测试序列化"""
        item = ChatMessageItem(**sample_message_item_data)
        data = item.model_dump()

        assert isinstance(data, dict)
        assert data == sample_message_item_data

    def test_message_item_json_schema(self):
        """测试JSON Schema"""
        schema = ChatMessageItem.model_json_schema()

        required_fields = ["type", "content", "timestamp"]
        for field in required_fields:
            assert field in schema["required"]


@pytest.mark.unit
class TestChatHistoryResponse:
    """聊天历史响应模型测试类"""

    @pytest.fixture
    def sample_history_response_data(self):
        """提供示例历史响应数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "messages": [
                {
                    "type": "human",
                    "content": "你好",
                    "timestamp": "2024-01-01T12:01:00Z"
                },
                {
                    "type": "ai",
                    "content": "你好！",
                    "timestamp": "2024-01-01T12:01:05Z"
                }
            ],
            "total_count": 2,
            "limit": 50,
            "timestamp": "2024-01-01T12:02:00Z",
            "status": "success"
        }

    def test_history_response_creation(self, sample_history_response_data):
        """测试创建历史响应"""
        response = ChatHistoryResponse(**sample_history_response_data)

        assert response.session_id == sample_history_response_data["session_id"]
        assert len(response.messages) == 2
        assert response.total_count == sample_history_response_data["total_count"]
        assert response.limit == sample_history_response_data["limit"]
        assert response.status == sample_history_response_data["status"]

    def test_history_response_empty_messages(self):
        """测试空消息列表"""
        response = ChatHistoryResponse(
            session_id="123",
            messages=[],
            total_count=0,
            limit=50,
            timestamp="2024-01-01T12:02:00Z",
            status="success"
        )

        assert response.messages == []
        assert response.total_count == 0

    def test_history_response_serialization(self, sample_history_response_data):
        """测试序列化"""
        response = ChatHistoryResponse(**sample_history_response_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert len(data["messages"]) == 2

    def test_history_response_nested_validation(self):
        """测试嵌套对象验证"""
        # 测试messages列表中缺少必需字段的情况
        with pytest.raises(ValidationError):
            ChatHistoryResponse(
                session_id="123",
                messages=[
                    {
                        "type": "human",
                        # 缺少content和timestamp字段
                    }
                ],
                total_count=1,
                limit=50,
                timestamp="2024-01-01T12:02:00Z",
                status="success"
            )

        # 测试正常情况（任何字符串值都是有效的type）
        response = ChatHistoryResponse(
            session_id="123",
            messages=[
                {
                    "type": "custom_type",  # 任何字符串都是有效的
                    "content": "测试",
                    "timestamp": "2024-01-01T12:01:00Z"
                }
            ],
            total_count=1,
            limit=50,
            timestamp="2024-01-01T12:02:00Z",
            status="success"
        )
        assert response.messages[0].type == "custom_type"


@pytest.mark.unit
class TestSessionInfoResponse:
    """会话信息响应模型测试类"""

    @pytest.fixture
    def sample_session_info_data(self):
        """提供示例会话信息数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "测试会话",
            "message_count": 5,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:05:00Z",
            "status": "active"
        }

    def test_session_info_creation(self, sample_session_info_data):
        """测试创建会话信息"""
        info = SessionInfoResponse(**sample_session_info_data)

        assert info.session_id == sample_session_info_data["session_id"]
        assert info.title == sample_session_info_data["title"]
        assert info.message_count == sample_session_info_data["message_count"]
        assert info.status == sample_session_info_data["status"]

    def test_session_info_zero_message_count(self):
        """测试零消息数量"""
        info = SessionInfoResponse(
            session_id="123",
            title="新会话",
            message_count=0,
            created_at="2024-01-01T12:00:00Z",
            updated_at="2024-01-01T12:00:00Z",
            status="active"
        )

        assert info.message_count == 0

    def test_session_info_serialization(self, sample_session_info_data):
        """测试序列化"""
        info = SessionInfoResponse(**sample_session_info_data)
        data = info.model_dump()

        assert isinstance(data, dict)
        assert data == sample_session_info_data


@pytest.mark.unit
class TestChatSessionItem:
    """聊天会话项模型测试类"""

    @pytest.fixture
    def sample_session_item_data(self):
        """提供示例会话项数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "测试会话",
            "message_count": 5,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:05:00Z"
        }

    def test_session_item_creation(self, sample_session_item_data):
        """测试创建会话项"""
        item = ChatSessionItem(**sample_session_item_data)

        assert item.session_id == sample_session_item_data["session_id"]
        assert item.title == sample_session_item_data["title"]
        assert item.message_count == sample_session_item_data["message_count"]

    def test_session_item_serialization(self, sample_session_item_data):
        """测试序列化"""
        item = ChatSessionItem(**sample_session_item_data)
        data = item.model_dump()

        assert isinstance(data, dict)
        assert data == sample_session_item_data


@pytest.mark.unit
class TestSessionListResponse:
    """会话列表响应模型测试类"""

    @pytest.fixture
    def sample_session_list_data(self):
        """提供示例会话列表数据"""
        return {
            "user_id": "test-user-123",
            "sessions": [
                {
                    "session_id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "会话1",
                    "message_count": 5,
                    "created_at": "2024-01-01T12:00:00Z",
                    "updated_at": "2024-01-01T12:05:00Z"
                },
                {
                    "session_id": "123e4567-e89b-12d3-a456-426614174001",
                    "title": "会话2",
                    "message_count": 3,
                    "created_at": "2024-01-01T11:00:00Z",
                    "updated_at": "2024-01-01T11:03:00Z"
                }
            ],
            "total_count": 2,
            "limit": 20,
            "timestamp": "2024-01-01T12:10:00Z",
            "status": "success",
            "note": ""
        }

    def test_session_list_creation(self, sample_session_list_data):
        """测试创建会话列表"""
        response = SessionListResponse(**sample_session_list_data)

        assert response.user_id == sample_session_list_data["user_id"]
        assert len(response.sessions) == 2
        assert response.total_count == sample_session_list_data["total_count"]
        assert response.status == sample_session_list_data["status"]

    def test_session_list_empty_sessions(self):
        """测试空会话列表"""
        response = SessionListResponse(
            user_id="test-user",
            sessions=[],
            total_count=0,
            limit=20,
            timestamp="2024-01-01T12:10:00Z",
            status="success",
            note=""
        )

        assert response.sessions == []
        assert response.total_count == 0

    def test_session_list_serialization(self, sample_session_list_data):
        """测试序列化"""
        response = SessionListResponse(**sample_session_list_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert len(data["sessions"]) == 2


@pytest.mark.unit
class TestDeleteSessionResponse:
    """删除会话响应模型测试类"""

    @pytest.fixture
    def sample_delete_response_data(self):
        """提供示例删除响应数据"""
        return {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "deleted",
            "timestamp": "2024-01-01T12:15:00Z",
            "note": ""
        }

    def test_delete_response_creation(self, sample_delete_response_data):
        """测试创建删除响应"""
        response = DeleteSessionResponse(**sample_delete_response_data)

        assert response.session_id == sample_delete_response_data["session_id"]
        assert response.status == sample_delete_response_data["status"]
        assert response.note == sample_delete_response_data["note"]

    def test_delete_response_with_note(self):
        """测试带备注的删除响应"""
        response = DeleteSessionResponse(
            session_id="123",
            status="deleted",
            timestamp="2024-01-01T12:15:00Z",
            note="会话已成功删除"
        )

        assert response.note == "会话已成功删除"

    def test_delete_response_serialization(self, sample_delete_response_data):
        """测试序列化"""
        response = DeleteSessionResponse(**sample_delete_response_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert data == sample_delete_response_data


@pytest.mark.unit
class TestChatHealthResponse:
    """聊天健康检查响应模型测试类"""

    @pytest.fixture
    def sample_health_data(self):
        """提供示例健康检查数据"""
        return {
            "status": "healthy",
            "database": {
                "status": "healthy",
                "file_exists": True,
                "connected": True,
                "checkpointer_ok": True,
                "store_ok": True
            },
            "graph_initialized": True,
            "timestamp": "2024-01-01T12:20:00Z"
        }

    def test_health_response_creation(self, sample_health_data):
        """测试创建健康检查响应"""
        response = ChatHealthResponse(**sample_health_data)

        assert response.status == sample_health_data["status"]
        assert response.database == sample_health_data["database"]
        assert response.graph_initialized == sample_health_data["graph_initialized"]

    def test_health_response_unhealthy(self):
        """测试不健康状态"""
        response = ChatHealthResponse(
            status="unhealthy",
            database={
                "status": "error",
                "file_exists": False,
                "connected": False,
                "checkpointer_ok": False,
                "store_ok": False
            },
            graph_initialized=False,
            timestamp="2024-01-01T12:20:00Z"
        )

        assert response.status == "unhealthy"
        assert response.graph_initialized is False

    def test_health_response_serialization(self, sample_health_data):
        """测试序列化"""
        response = ChatHealthResponse(**sample_health_data)
        data = response.model_dump()

        assert isinstance(data, dict)
        assert data == sample_health_data

    def test_health_response_nested_dict(self):
        """测试嵌套字典结构"""
        database_info = {
            "custom_field": "custom_value",
            "numeric_field": 123,
            "boolean_field": True
        }

        response = ChatHealthResponse(
            status="healthy",
            database=database_info,
            graph_initialized=True,
            timestamp="2024-01-01T12:20:00Z"
        )

        assert response.database == database_info
        assert response.database["custom_field"] == "custom_value"


@pytest.mark.integration
class TestSchemasIntegration:
    """Schemas集成测试类"""

    def test_complete_workflow_schemas(self):
        """测试完整工作流的Schema使用"""
        # 1. 创建会话请求
        create_request = CreateSessionRequest(title="测试会话")

        # 2. 发送消息请求
        send_request = SendMessageRequest(message="你好，AI助手")

        # 3. 会话响应
        session_response = ChatSessionResponse(
            session_id="123",
            title="测试会话",
            created_at="2024-01-01T12:00:00Z",
            welcome_message="你好！",
            status="created"
        )

        # 4. 消息响应
        message_response = MessageResponse(
            session_id="123",
            user_message="你好，AI助手",
            ai_response="你好！有什么可以帮助你的吗？",
            timestamp="2024-01-01T12:01:00Z",
            status="success"
        )

        # 5. 验证数据一致性
        assert create_request.title == session_response.title
        assert send_request.message == message_response.user_message
        assert session_response.session_id == message_response.session_id

    def test_schema_serialization_roundtrip(self):
        """测试Schema序列化往返"""
        original_data = {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "测试会话",
            "message_count": 5,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:05:00Z",
            "status": "active"
        }

        # 对象 -> dict -> 对象
        info = SessionInfoResponse(**original_data)
        serialized = info.model_dump()
        restored = SessionInfoResponse(**serialized)

        assert restored.session_id == original_data["session_id"]
        assert restored.title == original_data["title"]
        assert restored.message_count == original_data["message_count"]

    def test_nested_schema_validation(self):
        """测试嵌套Schema验证"""
        messages = [
            ChatMessageItem(
                type="human",
                content="用户消息",
                timestamp="2024-01-01T12:01:00Z"
            ),
            ChatMessageItem(
                type="ai",
                content="AI回复",
                timestamp="2024-01-01T12:01:05Z"
            )
        ]

        history_response = ChatHistoryResponse(
            session_id="123",
            messages=messages,
            total_count=2,
            limit=50,
            timestamp="2024-01-01T12:02:00Z",
            status="success"
        )

        assert len(history_response.messages) == 2
        assert history_response.messages[0].type == "human"
        assert history_response.messages[1].type == "ai"


@pytest.mark.performance
class TestSchemasPerformance:
    """Schemas性能测试类"""

    def test_schema_creation_performance(self):
        """测试Schema创建性能"""
        import time

        start_time = time.time()

        for i in range(1000):
            request = SendMessageRequest(message=f"测试消息{i}")

        duration = time.time() - start_time
        assert duration < 1.0, f"Schema创建性能不达标: {duration:.3f}秒"

    def test_schema_validation_performance(self):
        """测试Schema验证性能"""
        import time

        start_time = time.time()

        for i in range(1000):
            try:
                SendMessageRequest(message=f"测试消息{i}")
            except ValidationError:
                pass

        duration = time.time() - start_time
        assert duration < 1.0, f"Schema验证性能不达标: {duration:.3f}秒"

    def test_schema_serialization_performance(self):
        """测试Schema序列化性能"""
        import time

        responses = []
        for i in range(100):
            response = MessageResponse(
                session_id=f"session-{i}",
                user_message=f"用户消息{i}",
                ai_response=f"AI回复{i}",
                timestamp="2024-01-01T12:01:00Z",
                status="success"
            )
            responses.append(response)

        start_time = time.time()

        for response in responses:
            data = response.model_dump()

        duration = time.time() - start_time
        assert duration < 0.5, f"Schema序列化性能不达标: {duration:.3f}秒"


@pytest.mark.regression
class TestSchemasRegression:
    """Schemas回归测试类"""

    def test_regression_message_validation_edge_cases(self):
        """回归测试：消息验证边界情况"""
        # 测试各种空值情况
        invalid_messages = ["", "   ", "\n", "\t", "\r\n"]

        for invalid_msg in invalid_messages:
            with pytest.raises(ValidationError):
                SendMessageRequest(message=invalid_msg)

    def test_regression_field_types_consistency(self):
        """回归测试：字段类型一致性"""
        # 确保所有时间戳字段都是字符串类型
        response = MessageResponse(
            session_id="123",
            user_message="测试",
            ai_response="回复",
            timestamp="2024-01-01T12:01:00Z",  # 字符串类型
            status="success"
        )

        assert isinstance(response.session_id, str)
        assert isinstance(response.user_message, str)
        assert isinstance(response.ai_response, str)
        assert isinstance(response.timestamp, str)
        assert isinstance(response.status, str)

    def test_regression_required_fields_validation(self):
        """回归测试：必需字段验证"""
        # 测试每个模型的必需字段
        with pytest.raises(ValidationError):
            ChatSessionResponse(
                # 缺少所有必需字段
            )

        with pytest.raises(ValidationError):
            MessageResponse(
                # 缺少所有必需字段
            )

    def test_regression_example_data_validity(self):
        """回归测试：示例数据有效性"""
        # 验证所有模型的示例数据都是有效的
        create_request = CreateSessionRequest(title="日常对话")
        send_request = SendMessageRequest(message="你好，请帮我计算1+2等于多少？")

        session_response = ChatSessionResponse(
            session_id="123e4567-e89b-12d3-a456-426614174000",
            title="日常对话",
            created_at="2024-01-01T12:00:00Z",
            welcome_message="你好！我是你的AI助手，很高兴为你服务。",
            status="created"
        )

        message_response = MessageResponse(
            session_id="123e4567-e89b-12d3-a456-426614174000",
            user_message="你好，请帮我计算1+2等于多少？",
            ai_response="1+2 = 3",
            timestamp="2024-01-01T12:01:00Z",
            status="success"
        )

        # 所有对象都应该成功创建
        assert create_request.title == "日常对话"
        assert send_request.message == "你好，请帮我计算1+2等于多少？"
        assert session_response.status == "created"
        assert message_response.ai_response == "1+2 = 3"