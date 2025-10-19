"""
ChatService单元测试

测试ChatService的所有功能，包括对话管理、消息处理、
LangGraph集成、智能功能等。

遵循TDD最佳实践：
- 测试驱动开发，先写测试再实现功能
- 完整的边界条件和异常情况测试
- Mock依赖，隔离测试单元
- 95%+代码覆盖率要求
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid
import asyncio

# 导入测试目标
from src.services.chat_service import (
    ChatService, ChatMode, ConversationStatus, MessageType,
    ChatMessage, Conversation, ChatState
)
from src.services.exceptions import (
    ValidationException, ResourceNotFoundException,
    AuthorizationException, BusinessException
)

# 导入数据模型
from src.models.user import User
from src.models.task import Task, TaskStatus, PriorityLevel
from src.models.focus import FocusSession


class TestChatService:
    """ChatService主要功能测试类"""

    @pytest.fixture
    def mock_repos(self):
        """创建模拟的Repository对象"""
        user_repo = Mock()
        task_repo = Mock()
        focus_repo = Mock()

        return {
            'user_repo': user_repo,
            'task_repo': task_repo,
            'focus_repo': focus_repo
        }

    @pytest.fixture
    def chat_service(self, mock_repos):
        """创建ChatService实例"""
        return ChatService(
            user_repo=mock_repos['user_repo'],
            task_repo=mock_repos['task_repo'],
            focus_repo=mock_repos['focus_repo']
        )

    @pytest.fixture
    def sample_user(self):
        """创建示例用户对象"""
        return User(
            id="user_001",
            nickname="testuser",
            email="test@example.com",
            created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def sample_conversation_data(self):
        """创建示例对话数据"""
        return {
            "user_id": "user_001",
            "title": "测试对话",
            "chat_mode": ChatMode.GENERAL,
            "initial_context": {"test": True}
        }

    # ==================== 初始化测试 ====================

    def test_chat_service_initialization(self, mock_repos):
        """测试ChatService初始化"""
        service = ChatService(
            user_repo=mock_repos['user_repo'],
            task_repo=mock_repos['task_repo'],
            focus_repo=mock_repos['focus_repo']
        )

        assert service._service_name == "ChatService"
        assert service.user_repo == mock_repos['user_repo']
        assert service.task_repo == mock_repos['task_repo']
        assert service.focus_repo == mock_repos['focus_repo']
        assert isinstance(service.conversations, dict)
        assert isinstance(service.messages, dict)
        assert service.langgraph_app is not None  # 即使是mock也应该存在

    def test_chat_service_ai_config_loading(self, mock_repos, monkeypatch):
        """测试AI配置加载"""
        # 设置环境变量
        monkeypatch.setenv("AI_MODEL", "gpt-4")
        monkeypatch.setenv("AI_API_KEY", "test_key")
        monkeypatch.setenv("AI_BASE_URL", "https://api.openai.com")
        monkeypatch.setenv("AI_TEMPERATURE", "0.8")
        monkeypatch.setenv("AI_MAX_TOKENS", "1500")

        service = ChatService(**mock_repos)

        config = service.ai_config
        assert config["model"] == "gpt-4"
        assert config["api_key"] == "test_key"
        assert config["base_url"] == "https://api.openai.com"
        assert config["temperature"] == 0.8
        assert config["max_tokens"] == 1500

    # ==================== 对话创建测试 ====================

    def test_create_conversation_success(self, chat_service, mock_repos, sample_user, sample_conversation_data):
        """测试成功创建对话"""
        # 配置mock
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 执行测试
        result = chat_service.create_conversation(**sample_conversation_data)

        # 验证结果
        assert "conversation_id" in result
        assert result["title"] == sample_conversation_data["title"]
        assert result["status"] == ConversationStatus.ACTIVE.value
        assert result["chat_mode"] == sample_conversation_data["chat_mode"].value
        assert "created_at" in result
        assert "initial_message" in result
        assert "capabilities" in result

        # 验证对话已保存
        assert result["conversation_id"] in chat_service.conversations
        conversation = chat_service.conversations[result["conversation_id"]]
        assert conversation.user_id == sample_conversation_data["user_id"]
        assert conversation.title == sample_conversation_data["title"]
        assert conversation.status == ConversationStatus.ACTIVE

        # 验证初始消息已添加
        assert result["conversation_id"] in chat_service.messages
        messages = chat_service.messages[result["conversation_id"]]
        assert len(messages) > 0
        assert messages[0].message_type == MessageType.SYSTEM

    def test_create_conversation_different_modes(self, chat_service, mock_repos, sample_user):
        """测试不同聊天模式的对话创建"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        modes = [
            (ChatMode.GENERAL, "通用对话"),
            (ChatMode.TASK_ASSISTANT, "任务管理"),
            (ChatMode.PRODUCTIVITY_COACH, "生产力"),
            (ChatMode.FOCUS_GUIDE, "专注")
        ]

        for mode, expected_capability in modes:
            result = chat_service.create_conversation(
                user_id="user_001",
                title=f"{mode.value}对话",
                chat_mode=mode
            )

            assert result["chat_mode"] == mode.value
            assert any(expected_capability in capability for capability in result["capabilities"])

    @pytest.mark.parametrize("invalid_field,value,error_code", [
        ("user_id", "", "CHAT_INVALID_USER_ID"),
        ("user_id", None, "CHAT_INVALID_USER_ID"),
        ("user_id", 123, "CHAT_INVALID_USER_ID"),
        ("title", "", "CHAT_INVALID_TITLE"),
        ("title", None, "CHAT_INVALID_TITLE"),
        ("title", 123, "CHAT_INVALID_TITLE"),
        ("title", "a" * 101, "CHAT_TITLE_TOO_LONG"),
        ("chat_mode", "invalid", "CHAT_INVALID_CHAT_MODE"),
    ])
    def test_create_conversation_validation_errors(
        self, chat_service, invalid_field, value, error_code
    ):
        """测试创建对话时的参数验证错误"""
        params = {
            "user_id": "user_001",
            "title": "测试对话",
            "chat_mode": ChatMode.GENERAL
        }
        params[invalid_field] = value

        with pytest.raises(ValidationException) as exc_info:
            chat_service.create_conversation(**params)

        # ValidationException的error_code在details中
        assert exc_info.value.details.get("error_code") == error_code

    def test_create_conversation_user_not_found(self, chat_service, mock_repos):
        """测试用户不存在时创建对话"""
        mock_repos['user_repo'].get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundException) as exc_info:
            chat_service.create_conversation(
                user_id="nonexistent_user",
                title="测试对话",
                chat_mode=ChatMode.GENERAL
            )

        assert exc_info.value.details.get("error_code") == "CHAT_USER_NOT_FOUND"

    def test_create_conversation_repository_error(self, chat_service, mock_repos):
        """测试Repository异常处理"""
        mock_repos['user_repo'].get_by_id.side_effect = Exception("Database error")

        with pytest.raises(BusinessException) as exc_info:
            chat_service.create_conversation(
                user_id="user_001",
                title="测试对话",
                chat_mode=ChatMode.GENERAL
            )

        assert exc_info.value.error_code == "CHAT_CREATE_CONVERSATION_FAILED"
        assert "Database error" in str(exc_info.value)

    # ==================== 对话获取测试 ====================

    def test_get_conversation_success(self, chat_service, mock_repos, sample_user):
        """测试成功获取对话"""
        # 先创建对话
        mock_repos['user_repo'].get_by_id.return_value = sample_user
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )
        conversation_id = create_result["conversation_id"]

        # 获取对话
        result = chat_service.get_conversation(conversation_id, "user_001")

        # 验证结果
        assert "conversation_info" in result
        assert "messages" in result
        assert "context" in result
        assert "metadata" in result
        assert "statistics" in result

        conversation_info = result["conversation_info"]
        assert conversation_info["id"] == conversation_id
        assert conversation_info["title"] == "测试对话"

        # 验证统计信息
        stats = result["statistics"]
        assert "total_messages" in stats
        assert "user_messages" in stats
        assert "assistant_messages" in stats

    def test_get_conversation_access_denied(self, chat_service, mock_repos, sample_user):
        """测试无权限访问对话"""
        # 创建对话
        mock_repos['user_repo'].get_by_id.return_value = sample_user
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 尝试用其他用户ID访问
        with pytest.raises(AuthorizationException) as exc_info:
            chat_service.get_conversation(create_result["conversation_id"], "user_002")

        assert exc_info.value.details.get("error_code") == "CHAT_ACCESS_DENIED"

    def test_get_conversation_not_found(self, chat_service):
        """测试获取不存在的对话"""
        with pytest.raises(ResourceNotFoundException) as exc_info:
            chat_service.get_conversation("nonexistent_conv", "user_001")

        assert exc_info.value.error_code == "CHAT_CONVERSATION_NOT_FOUND"

    @pytest.mark.parametrize("invalid_conv_id,invalid_user_id", [
        ("", "user_001"),
        (None, "user_001"),
        (123, "user_001"),
        ("conv_001", ""),
        ("conv_001", None),
        ("conv_001", 123),
    ])
    def test_get_conversation_validation_errors(
        self, chat_service, invalid_conv_id, invalid_user_id
    ):
        """测试获取对话时的参数验证错误"""
        with pytest.raises(ValidationException):
            chat_service.get_conversation(invalid_conv_id, invalid_user_id)

    # ==================== 对话列表测试 ====================

    def test_list_user_conversations_success(self, chat_service, mock_repos, sample_user):
        """测试成功获取用户对话列表"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建多个对话
        conversation_ids = []
        for i in range(5):
            result = chat_service.create_conversation(
                user_id="user_001",
                title=f"对话 {i+1}",
                chat_mode=ChatMode.GENERAL
            )
            conversation_ids.append(result["conversation_id"])

        # 获取对话列表
        result = chat_service.list_user_conversations("user_001")

        # 验证结果
        assert "conversations" in result
        assert "pagination" in result
        assert "filter_info" in result

        conversations = result["conversations"]
        assert len(conversations) == 5

        # 验证排序（最新的在前）
        for i in range(len(conversations) - 1):
            assert conversations[i]["last_message_time"] >= conversations[i+1]["last_message_time"]

        # 验证分页信息
        pagination = result["pagination"]
        assert pagination["total_count"] == 5
        assert pagination["limit"] == 20
        assert pagination["offset"] == 0
        assert pagination["has_next"] is False
        assert pagination["has_prev"] is False

    def test_list_user_conversations_with_status_filter(self, chat_service, mock_repos, sample_user):
        """测试按状态过滤对话列表"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建不同状态的对话
        conv1 = chat_service.create_conversation(
            user_id="user_001", title="对话1", chat_mode=ChatMode.GENERAL
        )
        conv2 = chat_service.create_conversation(
            user_id="user_001", title="对话2", chat_mode=ChatMode.GENERAL
        )

        # 修改一个对话状态
        chat_service.conversations[conv2["conversation_id"]].status = ConversationStatus.COMPLETED

        # 按状态过滤
        result = chat_service.list_user_conversations(
            "user_001", status=ConversationStatus.ACTIVE
        )

        assert len(result["conversations"]) == 1
        assert result["conversations"][0]["conversation_id"] == conv1["conversation_id"]
        assert result["filter_info"]["status_filter"] == "active"

    def test_list_user_conversations_pagination(self, chat_service, mock_repos, sample_user):
        """测试对话列表分页"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建多个对话
        for i in range(10):
            chat_service.create_conversation(
                user_id="user_001",
                title=f"对话 {i+1}",
                chat_mode=ChatMode.GENERAL
            )

        # 测试第一页
        result1 = chat_service.list_user_conversations("user_001", limit=3, offset=0)
        assert len(result1["conversations"]) == 3
        assert result1["pagination"]["has_next"] is True
        assert result1["pagination"]["has_prev"] is False

        # 测试第二页
        result2 = chat_service.list_user_conversations("user_001", limit=3, offset=3)
        assert len(result2["conversations"]) == 3
        assert result2["pagination"]["has_next"] is True
        assert result2["pagination"]["has_prev"] is True

        # 测试最后一页
        result3 = chat_service.list_user_conversations("user_001", limit=3, offset=9)
        assert len(result3["conversations"]) == 1
        assert result3["pagination"]["has_next"] is False
        assert result3["pagination"]["has_prev"] is True

    @pytest.mark.parametrize("invalid_limit,invalid_offset", [
        (-1, 0),
        (0, 0),
        (101, 0),
        (20, -1),
        (20, 1.5),
    ])
    def test_list_conversations_validation_errors(
        self, chat_service, invalid_limit, invalid_offset
    ):
        """测试获取对话列表时的参数验证错误"""
        with pytest.raises(ValidationException):
            chat_service.list_user_conversations("user_001", limit=invalid_limit, offset=invalid_offset)

    # ==================== 消息发送测试 ====================

    @pytest.mark.asyncio
    async def test_send_message_sync_success(self, chat_service, mock_repos, sample_user):
        """测试同步发送消息成功"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )
        conversation_id = create_result["conversation_id"]

        # 发送消息
        result = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id="user_001",
            content="你好，我需要帮助",
            stream=False
        )

        # 验证回复
        assert "message_id" in result
        assert "content" in result
        assert "conversation_id" in result
        assert "created_at" in result
        assert "processing_time_ms" in result
        assert "metadata" in result

        # 验证消息已保存
        messages = chat_service.messages[conversation_id]
        assert len(messages) >= 2  # 系统消息 + 用户消息 + AI回复

        user_messages = [msg for msg in messages if msg.message_type == MessageType.USER]
        ai_messages = [msg for msg in messages if msg.message_type == MessageType.ASSISTANT]

        assert len(user_messages) == 1
        assert len(ai_messages) >= 1
        assert user_messages[0].content == "你好，我需要帮助"

    @pytest.mark.asyncio
    async def test_send_message_stream_success(self, chat_service, mock_repos, sample_user):
        """测试流式发送消息成功"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )
        conversation_id = create_result["conversation_id"]

        # 发送流式消息
        stream_response = chat_service.send_message(
            conversation_id=conversation_id,
            user_id="user_001",
            content="请介绍一下番茄工作法",
            stream=True
        )

        # 收集流式响应
        chunks = []
        async for chunk in stream_response:
            chunks.append(chunk)
            assert "chunk" in chunk
            assert "content" in chunk
            assert "is_complete" in chunk

        # 验证流式响应
        assert len(chunks) > 0
        assert chunks[-1]["is_complete"] is True

        # 验证完整消息已保存
        final_content = chunks[-1]["content"]
        assert len(final_content) > 0

    @pytest.mark.asyncio
    async def test_send_message_different_chat_modes(self, chat_service, mock_repos, sample_user):
        """测试不同聊天模式的消息回复"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        test_cases = [
            (ChatMode.TASK_ASSISTANT, "如何管理任务？"),
            (ChatMode.PRODUCTIVITY_COACH, "如何提高效率？"),
            (ChatMode.FOCUS_GUIDE, "如何保持专注？"),
        ]

        for mode, question in test_cases:
            # 创建对话
            create_result = chat_service.create_conversation(
                user_id="user_001",
                title=f"{mode.value}测试",
                chat_mode=mode
            )

            # 发送消息
            result = await chat_service.send_message(
                conversation_id=create_result["conversation_id"],
                user_id="user_001",
                content=question,
                stream=False
            )

            # 验证回复内容与模式相关
            assert result["content"] is not None
            assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_send_message_with_additional_context(self, chat_service, mock_repos, sample_user):
        """测试带额外上下文的消息发送"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.TASK_ASSISTANT
        )
        conversation_id = create_result["conversation_id"]

        # 发送带上下文的消息
        additional_context = {
            "current_task": "完成项目文档",
            "deadline": "2025-01-25",
            "priority": "high"
        }

        result = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id="user_001",
            content="我需要帮助完成这个任务",
            additional_context=additional_context,
            stream=False
        )

        # 验证上下文被正确处理
        assert result["metadata"] is not None

        # 验证对话上下文已更新
        conversation = chat_service.conversations[conversation_id]
        assert "current_task" in conversation.context
        assert conversation.context["current_task"] == "完成项目文档"

    @pytest.mark.asyncio
    async def test_send_message_validation_errors(self, chat_service, mock_repos, sample_user):
        """测试发送消息时的参数验证错误"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 测试各种无效参数
        invalid_params = [
            {"conversation_id": "", "user_id": "user_001", "content": "test"},
            {"conversation_id": None, "user_id": "user_001", "content": "test"},
            {"conversation_id": "conv_001", "user_id": "", "content": "test"},
            {"conversation_id": "conv_001", "user_id": None, "content": "test"},
            {"conversation_id": "conv_001", "user_id": "user_001", "content": ""},
            {"conversation_id": "conv_001", "user_id": "user_001", "content": None},
            {"conversation_id": "conv_001", "user_id": "user_001", "content": "a" * 10001},
        ]

        for params in invalid_params:
            with pytest.raises(ValidationException):
                await chat_service.send_message(**params)

    @pytest.mark.asyncio
    async def test_send_message_conversation_not_active(self, chat_service, mock_repos, sample_user):
        """测试向非活跃对话发送消息"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 修改对话状态为非活跃
        conversation_id = create_result["conversation_id"]
        chat_service.conversations[conversation_id].status = ConversationStatus.COMPLETED

        # 尝试发送消息
        with pytest.raises(BusinessException) as exc_info:
            await chat_service.send_message(
                conversation_id=conversation_id,
                user_id="user_001",
                content="测试消息"
            )

        assert exc_info.value.error_code == "CHAT_CONVERSATION_NOT_ACTIVE"

    # ==================== 智能功能测试 ====================

    @pytest.mark.asyncio
    async def test_get_task_suggestions_success(self, chat_service, mock_repos, sample_user):
        """测试获取任务建议成功"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 模拟用户数据
        mock_tasks = [
            Mock(status=TaskStatus.IN_PROGRESS),
            Mock(status=TaskStatus.COMPLETED),
        ]
        mock_repos['task_repo'].find_by_user.return_value = mock_tasks

        result = await chat_service.get_task_suggestions("user_001")

        # 验证结果结构
        assert "suggestions" in result
        assert "context_info" in result
        assert "generated_at" in result

        # 验证建议内容
        suggestions = result["suggestions"]
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

        # 验证上下文信息
        context_info = result["context_info"]
        assert "user_level" in context_info
        assert "active_tasks" in context_info

    @pytest.mark.asyncio
    async def test_get_task_suggestions_with_conversation(
        self, chat_service, mock_repos, sample_user
    ):
        """测试在对话上下文中获取任务建议"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="任务助手对话",
            chat_mode=ChatMode.TASK_ASSISTANT
        )

        result = await chat_service.get_task_suggestions(
            user_id="user_001",
            conversation_id=create_result["conversation_id"]
        )

        # 验证对话上下文被添加
        assert "conversation_context" in result
        assert result["conversation_context"]["conversation_id"] == create_result["conversation_id"]
        assert result["conversation_context"]["message_added"] is True

        # 验证消息已添加到对话
        messages = chat_service.messages[create_result["conversation_id"]]
        suggestion_messages = [msg for msg in messages if "建议" in msg.content]
        assert len(suggestion_messages) > 0

    @pytest.mark.asyncio
    async def test_analyze_productivity_patterns_success(self, chat_service, mock_repos, sample_user):
        """测试生产力模式分析成功"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        result = await chat_service.analyze_productivity_patterns("user_001", days=30)

        # 验证结果结构
        assert "analysis_period" in result
        assert "patterns" in result
        assert "insights" in result
        assert "recommendations" in result
        assert "data_summary" in result
        assert "generated_at" in result

        # 验证分析期间
        analysis_period = result["analysis_period"]
        assert "start_date" in analysis_period
        assert "end_date" in analysis_period
        assert analysis_period["days_analyzed"] == 30

        # 验证模式分析
        patterns = result["patterns"]
        assert "peak_hours" in patterns
        assert "productivity_trend" in patterns
        assert "focus_patterns" in patterns

        # 验证洞察和建议
        assert isinstance(result["insights"], list)
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_analyze_productivity_patterns_with_conversation(
        self, chat_service, mock_repos, sample_user
    ):
        """测试在对话上下文中分析生产力模式"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="生产力教练对话",
            chat_mode=ChatMode.PRODUCTIVITY_COACH
        )

        result = await chat_service.analyze_productivity_patterns(
            user_id="user_001",
            days=7,
            conversation_id=create_result["conversation_id"]
        )

        # 验证对话上下文
        assert "conversation_context" in result
        assert result["conversation_context"]["conversation_id"] == create_result["conversation_id"]
        assert result["conversation_context"]["summary_added"] is True

        # 验证分析摘要已添加到对话
        messages = chat_service.messages[create_result["conversation_id"]]
        summary_messages = [msg for msg in messages if "分析摘要" in msg.content]
        assert len(summary_messages) > 0

    # ==================== LangGraph集成测试 ====================

    def test_langgraph_app_initialization(self, chat_service):
        """测试LangGraph应用初始化"""
        # 即使LangGraph不可用，也应该创建mock应用
        assert chat_service.langgraph_app is not None

    @pytest.mark.asyncio
    async def test_chat_state_handling(self, chat_service):
        """测试ChatState状态处理"""
        # 创建测试状态
        state = ChatState(
            messages=[],
            user_context={"user_id": "test"},
            task_context={"active_tasks": 3},
            current_intent="task_help",
            processing_state="analyzing"
        )

        # 测试意图分析节点
        result_state = await chat_service._analyze_intent_node(state)
        assert result_state.processing_state == "intent_analyzed"

        # 测试上下文收集节点
        result_state = await chat_service._gather_context_node(result_state)
        assert result_state.processing_state == "context_gathered"

        # 测试回复生成节点
        result_state = await chat_service._generate_response_node(result_state)
        assert result_state.processing_state == "response_generated"
        assert len(result_state.messages) > 0

        # 测试后处理节点
        result_state = await chat_service._post_process_node(result_state)
        assert result_state.processing_state == "completed"

    # ==================== 辅助方法测试 ====================

    def test_analyze_intent(self, chat_service):
        """测试意图分析方法"""
        test_cases = [
            ("如何管理任务", "task_help"),
            ("怎么提高效率", "productivity_advice"),
            ("如何保持专注", "focus_help"),
            ("时间怎么安排", "time_management"),
            ("设定目标", "goal_setting"),
            ("养成习惯", "habit_development"),
            ("你好", "greeting"),
            ("谢谢", "thanks"),
            ("天气怎么样", "general_question"),
            ("随便聊聊", "general"),
        ]

        for content, expected_intent in test_cases:
            intent = chat_service._analyze_intent(content)
            assert intent == expected_intent, f"Failed for content: {content}"

    def test_generate_conversation_id(self, chat_service):
        """测试对话ID生成"""
        id1 = chat_service._generate_conversation_id()
        id2 = chat_service._generate_conversation_id()

        assert id1 != id2
        assert id1.startswith("conv_")
        assert len(id1) > len("conv_")

    def test_generate_message_id(self, chat_service):
        """测试消息ID生成"""
        id1 = chat_service._generate_message_id()
        id2 = chat_service._generate_message_id()

        assert id1 != id2
        assert id1.startswith("msg_")
        assert len(id1) > len("msg_")

    def test_create_message(self, chat_service):
        """测试消息对象创建"""
        message = chat_service._create_message(
            conversation_id="conv_001",
            message_type=MessageType.USER,
            content="测试消息",
            metadata={"test": True},
            processing_time_ms=100
        )

        assert message.conversation_id == "conv_001"
        assert message.message_type == MessageType.USER
        assert message.content == "测试消息"
        assert message.metadata["test"] is True
        assert message.processing_time_ms == 100
        assert message.token_count > 0
        assert isinstance(message.created_at, datetime)

    def test_calculate_conversation_stats(self, chat_service):
        """测试对话统计计算"""
        # 创建测试消息
        messages = [
            chat_service._create_message("conv_001", MessageType.SYSTEM, "系统消息"),
            chat_service._create_message("conv_001", MessageType.USER, "用户消息"),
            chat_service._create_message("conv_001", MessageType.ASSISTANT, "AI回复", processing_time_ms=150),
        ]

        conversation = Mock(
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            updated_at=datetime.now(timezone.utc)
        )

        stats = chat_service._calculate_conversation_stats(conversation, messages)

        assert stats["total_messages"] == 3
        assert stats["user_messages"] == 1
        assert stats["assistant_messages"] == 1
        assert stats["total_tokens"] > 0
        assert stats["average_response_time_ms"] == 150.0
        assert stats["conversation_duration_minutes"] == 30.0

    def test_empty_conversation_stats(self, chat_service):
        """测试空对话的统计计算"""
        conversation = Mock()
        stats = chat_service._calculate_conversation_stats(conversation, [])

        assert stats["total_messages"] == 0
        assert stats["user_messages"] == 0
        assert stats["assistant_messages"] == 0
        assert stats["total_tokens"] == 0
        assert stats["average_response_time_ms"] == 0
        assert stats["conversation_duration_minutes"] == 0

    # ==================== 异常处理测试 ====================

    @pytest.mark.asyncio
    async def test_message_processing_error_handling(self, chat_service, mock_repos, sample_user):
        """测试消息处理异常处理"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 模拟处理异常
        with patch.object(chat_service, '_generate_mock_response', side_effect=Exception("Processing error")):
            result = await chat_service.send_message(
                conversation_id=create_result["conversation_id"],
                user_id="user_001",
                content="测试消息",
                stream=False
            )

            # 验证错误回复
            assert result["content"] is not None
            assert "抱歉" in result["content"]
            assert result["metadata"]["error"] is True
            assert "error_info" in result

    @pytest.mark.asyncio
    async def test_stream_message_error_handling(self, chat_service, mock_repos, sample_user):
        """测试流式消息异常处理"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 模拟流式处理异常
        async def mock_stream_with_error():
            yield {"chunk": "正常内容", "content": "正常内容", "is_complete": False}
            yield {"chunk": "\n\n错误信息", "content": "正常内容\n\n错误信息", "is_complete": True, "error": True}

        with patch.object(chat_service, '_process_message_stream', return_value=mock_stream_with_error()):
            stream_response = chat_service.send_message(
                conversation_id=create_result["conversation_id"],
                user_id="user_001",
                content="测试消息",
                stream=True
            )

            # 收集流式响应
            chunks = []
            async for chunk in stream_response:
                chunks.append(chunk)

            # 验证错误处理
            assert len(chunks) >= 1
            assert chunks[-1].get("error") is True

    # ==================== 边界条件测试 ====================

    @pytest.mark.asyncio
    async def test_very_long_message_handling(self, chat_service, mock_repos, sample_user):
        """测试超长消息处理"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 发送接近限制长度的消息
        long_content = "a" * 9999  # 接近10000字符限制
        result = await chat_service.send_message(
            conversation_id=create_result["conversation_id"],
            user_id="user_001",
            content=long_content,
            stream=False
        )

        assert result["content"] is not None
        assert len(result["content"]) > 0

    def test_concurrent_conversation_creation(self, chat_service, mock_repos, sample_user):
        """测试并发对话创建"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        import concurrent.futures
        import threading

        def create_conversation(index):
            return chat_service.create_conversation(
                user_id="user_001",
                title=f"并发对话 {index}",
                chat_mode=ChatMode.GENERAL
            )

        # 并发创建多个对话
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_conversation, i) for i in range(10)]
            results = [future.result() for future in futures]

        # 验证所有对话都创建成功
        assert len(results) == 10
        conversation_ids = [result["conversation_id"] for result in results]
        assert len(set(conversation_ids)) == 10  # 确保ID唯一

        # 验证所有对话都已保存
        for conv_id in conversation_ids:
            assert conv_id in chat_service.conversations

    # ==================== 性能测试 ====================

    @pytest.mark.asyncio
    async def test_message_processing_performance(self, chat_service, mock_repos, sample_user):
        """测试消息处理性能"""
        mock_repos['user_repo'].get_by_id.return_value = sample_user

        # 创建对话
        create_result = chat_service.create_conversation(
            user_id="user_001",
            title="性能测试对话",
            chat_mode=ChatMode.GENERAL
        )

        # 测试多条消息的处理时间
        import time
        start_time = time.time()

        for i in range(5):
            result = await chat_service.send_message(
                conversation_id=create_result["conversation_id"],
                user_id="user_001",
                content=f"性能测试消息 {i+1}",
                stream=False
            )
            assert result["processing_time_ms"] >= 0

        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # 转换为毫秒

        # 验证总体性能（5条消息应在合理时间内完成）
        assert total_time < 5000  # 应在5秒内完成

        # 验证平均处理时间
        messages = chat_service.messages[create_result["conversation_id"]]
        ai_messages = [msg for msg in messages if msg.message_type == MessageType.ASSISTANT]
        avg_time = sum(msg.processing_time_ms for msg in ai_messages) / len(ai_messages)
        assert avg_time < 1000  # 平均处理时间应少于1秒


class TestChatServiceIntegration:
    """ChatService集成测试类"""

    @pytest.fixture
    def service_with_mocks(self):
        """创建带有完整Mock的ChatService"""
        user_repo = Mock()
        task_repo = Mock()
        focus_repo = Mock()

        service = ChatService(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo
        )

        return service, user_repo, task_repo, focus_repo

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, service_with_mocks):
        """测试完整的对话流程"""
        service, user_repo, task_repo, focus_repo = service_with_mocks

        # 配置用户mock
        user_repo.get_by_id.return_value = User(
            id="user_001",
            nickname="testuser",
            created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc)
        )

        # 1. 创建对话
        conv_result = service.create_conversation(
            user_id="user_001",
            title="完整流程测试",
            chat_mode=ChatMode.TASK_ASSISTANT
        )

        # 2. 发送多条消息
        messages = [
            "我需要帮助管理我的任务",
            "我今天有3个重要任务要完成",
            "你能帮我制定一个计划吗？"
        ]

        for msg in messages:
            result = await service.send_message(
                conversation_id=conv_result["conversation_id"],
                user_id="user_001",
                content=msg,
                stream=False
            )
            assert result["content"] is not None

        # 3. 获取对话信息
        conversation_info = service.get_conversation(
            conv_result["conversation_id"],
            "user_001"
        )

        # 验证对话状态
        assert conversation_info["conversation_info"]["status"] == "active"
        assert len(conversation_info["messages"]) >= len(messages) + 1  # +1 for system message

        # 4. 获取任务建议
        suggestions = await service.get_task_suggestions(
            user_id="user_001",
            conversation_id=conv_result["conversation_id"]
        )

        assert len(suggestions["suggestions"]) > 0
        assert "conversation_context" in suggestions

        # 5. 获取对话列表
        conv_list = service.list_user_conversations("user_001")
        assert len(conv_list["conversations"]) == 1
        assert conv_list["conversations"][0]["conversation_id"] == conv_result["conversation_id"]

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, service_with_mocks):
        """测试错误恢复流程"""
        service, user_repo, task_repo, focus_repo = service_with_mocks

        # 配置用户mock
        user_repo.get_by_id.return_value = User(
            id="user_001",
            nickname="testuser",
            created_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc)
        )

        # 创建对话
        conv_result = service.create_conversation(
            user_id="user_001",
            title="错误恢复测试",
            chat_mode=ChatMode.GENERAL
        )

        # 模拟处理错误的消息
        with patch.object(service, '_generate_mock_response', side_effect=Exception("临时错误")):
            result = await service.send_message(
                conversation_id=conv_result["conversation_id"],
                user_id="user_001",
                content="会触发错误的消息",
                stream=False
            )

            # 验证错误处理
            assert result["metadata"]["error"] is True
            assert "抱歉" in result["content"]

        # 验证后续消息可以正常处理
        normal_result = await service.send_message(
            conversation_id=conv_result["conversation_id"],
            user_id="user_001",
            content="正常消息",
            stream=False
        )

        assert normal_result["metadata"].get("error") is not True
        assert len(normal_result["content"]) > 0

        # 验证对话仍然可用
        conversation_info = service.get_conversation(
            conv_result["conversation_id"],
            "user_001"
        )
        assert conversation_info["conversation_info"]["status"] == "active"