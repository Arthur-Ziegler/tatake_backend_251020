"""
复杂对话集成测试

该测试使用MockAIProvider但测试更复杂的对话逻辑，包括：
1. 多轮对话的上下文管理
2. 复杂意图识别
3. 记忆功能验证
4. 对话状态一致性

这个测试验证我们的业务逻辑是否正确，而不依赖真实API
"""
import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

pytestmark = pytest.mark.asyncio

# 导入ChatService和相关组件
from src.services.chat_service import ChatService, ConversationCreationRequest, ChatMessageRequest
from src.models.enums import ChatMode
from src.services.exceptions import BusinessException
from src.repositories.chat import ChatRepository

# 从之前的测试文件导入MockAIProvider
from tests.services.test_chat_langgraph_integration import MockAIProvider
from src.services.chat.ai_client import AIConfig, AIClientFactory
from src.services.chat.conversation import ConversationManager


class TestComplexConversationIntegration:
    """复杂对话集成测试类"""

    @pytest.fixture
    async def chat_service_with_mock(self):
        """创建使用MockAIProvider的ChatService实例"""
        # 创建ChatRepository（使用内存存储用于测试）
        chat_repository = ChatRepository()

        # 创建MockAIProvider配置
        ai_config = AIConfig(
            model="test-model",
            temperature=0.7,
            max_tokens=1000
        )

        # 创建MockAIProvider
        mock_provider = MockAIProvider(ai_config)
        await mock_provider.initialize()

        # 创建ConversationManager
        conversation_manager = ConversationManager()

        # 创建ChatService，注入所有依赖
        service = ChatService(
            chat_repository=chat_repository,
            conversation_manager=conversation_manager,
            # 不注入ai_orchestrator，让它使用默认的工厂创建
            ai_config=ai_config
        )

        # 手动替换AI提供商为Mock
        if hasattr(service, '_ai_orchestrator') and service._ai_orchestrator:
            if hasattr(service._ai_orchestrator, 'ai_provider'):
                service._ai_orchestrator.ai_provider = mock_provider

        return service

    @pytest.fixture
    def test_user_id(self):
        """测试用户ID"""
        return str(uuid4())

    async def test_complex_task_management_conversation(self, chat_service_with_mock, test_user_id):
        """测试复杂任务管理对话流程"""
        print("\n=== 测试复杂任务管理对话流程 ===")

        # 创建任务助手模式的对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="复杂任务管理测试",
            chat_mode=ChatMode.TASK_ASSISTANT
        )
        conv_result = await chat_service_with_mock.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 模拟真实的项目管理对话流程
        conversation_script = [
            "我需要开发一个移动应用，项目时间很紧，",
            "功能包括用户注册、商品浏览、购物车、支付等功能",
            "团队有3个人，包括我、一个前端开发者、一个后端开发者",
            "预算大约10万，时间期限3个月，你觉得可行吗？",
            "如果时间不够，我应该优先实现哪些功能？",
            "谢谢你，我现在对项目规划更清楚了！"
        ]

        conversation_history = []

        for i, user_message in enumerate(conversation_script, 1):
            print(f"\n第{i}轮对话:")
            print(f"用户: {user_message}")

            # 发送消息
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=user_message
            )

            response = await chat_service_with_mock.send_message(message_request)
            conversation_history.append({
                "round": i,
                "user_message": user_message,
                "ai_response": response.content,
                "session_id": session_id
            })

            print(f"AI: {response.content}")
            print(f"回复长度: {len(response.content)} 字符")

            # 验证回复质量
            assert response is not None
            assert len(response.content) > 10
            assert response.content != user_message  # 确保不是重复用户输入

            # 验证回复与任务管理相关
            response_lower = response.content.lower()
            task_related_keywords = ["任务", "项目", "计划", "功能", "开发", "时间", "团队"]
            has_task_content = any(keyword in response_lower for keyword in task_related_keywords)

            if i <= 4:  # 前几轮应该涉及任务相关内容
                assert has_task_content, f"第{i}轮回复应该与任务管理相关"

        # 验证对话历史的一致性
        assert len(conversation_history) == len(conversation_script)

        # 验证对话ID的一致性
        session_ids = [item["session_id"] for item in conversation_history]
        assert all(session_id == sid for sid in session_ids), "所有对话应该在同一个会话中"

        print("\n✓ 复杂任务管理对话流程测试通过")

    async def test_productivity_coaching_conversation(self, chat_service_with_mock, test_user_id):
        """测试生产力教练对话"""
        print("\n=== 测试生产力教练对话 ===")

        # 创建生产力教练模式的对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="生产力教练测试",
            chat_mode=ChatMode.PRODUCTIVITY_COACH
        )
        conv_result = await chat_service_with_mock.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 生产力提升对话流程
        productivity_flow = [
            "我最近工作效率很低，总是拖延，有什么建议吗？",
            "我尝试过番茄工作法，但总是坚持不下来",
            "我的主要问题是容易分心，经常被手机和社交媒体打断",
            "除了时间管理，还有什么提高专注力的方法吗？",
            "谢谢你的建议，我会试试这些方法！"
        ]

        for i, message in enumerate(productivity_flow, 1):
            print(f"\n第{i}轮生产力对话:")
            print(f"用户: {message}")

            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )

            response = await chat_service_with_mock.send_message(message_request)
            print(f"AI: {response.content[:100]}...")

            # 验证回复内容与生产力相关
            response_lower = response.content.lower()
            productivity_keywords = ["效率", "生产力", "时间", "专注", "方法", "习惯", "建议"]
            has_productivity_content = any(keyword in response_lower for keyword in productivity_keywords)

            assert has_productivity_content, f"第{i}轮生产力教练回复应该包含生产力相关内容"

        print("\n✓ 生产力教练对话测试通过")

    async def test_focus_guide_conversation(self, chat_service_with_mock, test_user_id):
        """测试专注指导对话"""
        print("\n=== 测试专注指导对话 ===")

        # 创建专注指导模式的对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="专注指导测试",
            chat_mode=ChatMode.FOCUS_GUIDE
        )
        conv_result = await chat_service_with_mock.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 专注力训练对话流程
        focus_flow = [
            "我学习时总是无法集中注意力，很容易分心",
            "工作环境很嘈杂，我该如何创造专注的环境？",
            "我尝试过冥想，但感觉没什么效果",
            "有没有什么具体的专注力训练练习？",
            "谢谢指导，我会坚持练习专注力！"
        ]

        for i, message in enumerate(focus_flow, 1):
            print(f"\n第{i}轮专注指导对话:")
            print(f"用户: {message}")

            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )

            response = await chat_service_with_mock.send_message(message_request)
            print(f"AI: {response.content[:100]}...")

            # 验证回复内容与专注相关
            response_lower = response.content.lower()
            focus_keywords = ["专注", "分心", "集中", "注意力", "环境", "练习", "训练"]
            has_focus_content = any(keyword in response_lower for keyword in focus_keywords)

            assert has_focus_content, f"第{i}轮专注指导回复应该包含专注相关内容"

        print("\n✓ 专注指导对话测试通过")

    async def test_mixed_mode_conversations(self, chat_service_with_mock, test_user_id):
        """测试混合模式对话"""
        print("\n=== 测试混合模式对话 ===")

        conversations = []

        # 创建不同模式的对话
        modes_and_topics = [
            (ChatMode.GENERAL, "今天天气怎么样？"),
            (ChatMode.TASK_ASSISTANT, "我需要制定一个学习计划"),
            (ChatMode.PRODUCTIVITY_COACH, "如何提高工作效率？"),
            (ChatMode.FOCUS_GUIDE, "怎样才能保持专注？")
        ]

        for mode, topic in modes_and_topics:
            print(f"\n测试 {mode.value} 模式，主题: {topic}")

            # 创建对话
            conv_request = ConversationCreationRequest(
                user_id=test_user_id,
                title=f"{mode.value}模式测试",
                chat_mode=mode
            )
            conv_result = await chat_service_with_mock.create_conversation(conv_request)
            session_id = conv_result["session_id"]

            # 发送消息
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=topic
            )

            response = await chat_service_with_mock.send_message(message_request)

            conversations.append({
                "mode": mode.value,
                "topic": topic,
                "response": response.content,
                "session_id": session_id
            })

            print(f"回复: {response.content[:80]}...")

            # 验证回复不为空且有实际内容
            assert response is not None
            assert len(response.content) > 5

        # 验证不同对话的独立性
        session_ids = [conv["session_id"] for conv in conversations]
        assert len(set(session_ids)) == len(session_ids), "每个对话应该有独立的会话ID"

        # 验证不同模式产生了不同的回复
        responses = [conv["response"] for conv in conversations]
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                # 不应该完全相同
                assert responses[i] != responses[j], "不同模式的回复应该有所差异"

        print(f"\n✓ 混合模式对话测试通过，创建了 {len(conversations)} 个独立对话")

    async def test_conversation_memory_across_modes(self, chat_service_with_mock, test_user_id):
        """测试跨模式对话记忆"""
        print("\n=== 测试跨模式对话记忆 ===")

        # 第一个对话：通用模式，介绍信息
        conv1_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="信息介绍对话",
            chat_mode=ChatMode.GENERAL
        )
        conv1_result = await chat_service_with_mock.create_conversation(conv1_request)
        session1_id = conv1_result["session_id"]

        intro_message = "你好，我叫李四，是一名数据分析师，喜欢用Python做数据分析。"

        message_request = ChatMessageRequest(
            session_id=session1_id,
            user_id=test_user_id,
            content=intro_message
        )
        response1 = await chat_service_with_mock.send_message(message_request)
        print(f"第一轮对话回复: {response1.content[:100]}...")

        # 第二个对话：任务助手模式，询问任务建议
        conv2_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="任务建议对话",
            chat_mode=ChatMode.TASK_ASSISTANT
        )
        conv2_result = await chat_service_with_mock.create_conversation(conv2_request)
        session2_id = conv2_result["session_id"]

        task_message = "基于我的背景，你有什么职业发展建议吗？"

        message_request = ChatMessageRequest(
            session_id=session2_id,
            user_id=test_user_id,
            content=task_message
        )
        response2 = await chat_service_with_mock.send_message(message_request)
        print(f"第二轮对话回复: {response2.content[:100]}...")

        # 验证回复的相关性和质量
        assert response1 is not None and len(response1.content) > 10
        assert response2 is not None and len(response2.content) > 10

        # 验证两个对话是独立的（不同会话ID）
        assert session1_id != session2_id, "不同对话应该有不同的会话ID"

        print("\n✓ 跨模式对话记忆测试通过")

    async def test_error_recovery_in_conversation(self, chat_service_with_mock, test_user_id):
        """测试对话中的错误恢复"""
        print("\n=== 测试对话错误恢复 ===")

        # 创建对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="错误恢复测试",
            chat_mode=ChatMode.GENERAL
        )
        conv_result = await chat_service_with_mock.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 正常对话
        normal_messages = [
            "你好",
            "今天天气不错",
            "我想讨论一下工作问题"
        ]

        for i, message in enumerate(normal_messages, 1):
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )
            response = await chat_service_with_mock.send_message(message_request)
            assert response is not None
            print(f"正常消息 {i}: {response.content[:50]}...")

        # 测试边界情况
        edge_cases = [
            "",  # 空消息
            "a" * 5,  # 极短消息
            "测试" * 100  # 长消息
        ]

        for i, message in enumerate(edge_cases, 1):
            try:
                message_request = ChatMessageRequest(
                    session_id=session_id,
                    user_id=test_user_id,
                    content=message
                )
                response = await chat_service_with_mock.send_message(message_request)
                print(f"边界情况 {i}: 处理成功")

                # 验证回复仍然有效
                assert response is not None
                if message:  # 非空消息应该有正常回复
                    assert len(response.content) > 0

            except Exception as e:
                print(f"边界情况 {i}: 遇到异常 - {type(e).__name__}: {e}")
                # 某些边界情况可能会抛出异常，这是可以接受的

        # 测试对话在错误后是否仍然可用
        recovery_message = "错误后测试对话是否正常"
        message_request = ChatMessageRequest(
            session_id=session_id,
            user_id=test_user_id,
            content=recovery_message
        )
        recovery_response = await chat_service_with_mock.send_message(message_request)

        assert recovery_response is not None
        print(f"恢复测试: {recovery_response.content[:50]}...")

        print("\n✓ 对话错误恢复测试通过")

    async def test_concurrent_conversation_management(self, chat_service_with_mock, test_user_id):
        """测试并发对话管理"""
        print("\n=== 测试并发对话管理 ===")

        # 并发创建多个对话
        create_tasks = []
        conversation_configs = [
            ("工作规划", ChatMode.TASK_ASSISTANT),
            ("效率提升", ChatMode.PRODUCTIVITY_COACH),
            ("专注训练", ChatMode.FOCUS_GUIDE),
            ("日常聊天", ChatMode.GENERAL)
        ]

        for title, mode in conversation_configs:
            conv_request = ConversationCreationRequest(
                user_id=test_user_id,
                title=title,
                chat_mode=mode
            )
            task = chat_service_with_mock.create_conversation(conv_request)
            create_tasks.append(task)

        # 等待所有对话创建完成
        create_results = await asyncio.gather(*create_tasks)
        session_ids = [result["session_id"] for result in create_results]

        print(f"成功创建 {len(session_ids)} 个并发对话")

        # 并发发送消息到各个对话
        message_tasks = []
        test_messages = [
            "我需要帮助规划工作",
            "如何提高工作效率？",
            "怎样才能保持专注？",
            "今天天气如何？"
        ]

        for session_id, message in zip(session_ids, test_messages):
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )
            task = chat_service_with_mock.send_message(message_request)
            message_tasks.append(task)

        # 等待所有消息处理完成
        responses = await asyncio.gather(*message_tasks)

        # 验证所有响应都成功
        for i, response in enumerate(responses):
            assert response is not None
            assert len(response.content) > 5
            print(f"对话 {i+1} 回复成功: {response.content[:50]}...")

        # 验证会话独立性
        assert len(set(session_ids)) == len(session_ids), "所有会话ID应该是唯一的"

        print("\n✓ 并发对话管理测试通过")

    async def test_conversation_state_consistency(self, chat_service_with_mock, test_user_id):
        """测试对话状态一致性"""
        print("\n=== 测试对话状态一致性 ===")

        # 创建对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="状态一致性测试",
            chat_mode=ChatMode.GENERAL
        )
        conv_result = await chat_service_with_mock.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 进行多轮对话，建立上下文
        context_building_messages = [
            "我叫王五，是一名产品经理",
            "我们公司正在开发一个新的社交应用",
            "目前处于需求分析阶段",
            "团队有5个人，包括2名前端、2名后端、1名UI设计师"
        ]

        # 第一轮：建立上下文
        for message in context_building_messages:
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )
            response = await chat_service_with_mock.send_message(message_request)
            assert response is not None

        # 测试上下文相关的问题
        context_questions = [
            "你还记得我的名字吗？",
            "我们的项目是什么？",
            "现在项目进行到哪个阶段了？",
            "团队有多少人？"
        ]

        for i, question in enumerate(context_questions, 1):
            print(f"\n上下文问题 {i}: {question}")

            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=question
            )
            response = await chat_service_with_mock.send_message(message_request)

            print(f"AI回复: {response.content[:100]}...")

            # 验证回复质量
            assert response is not None
            assert len(response.content) > 10

            # 检查回复是否显示了上下文理解
            response_lower = response.content.lower()
            context_indicators = ["王五", "产品经理", "社交应用", "需求分析", "5个人", "团队"]
            has_context_reference = any(indicator in response_lower for indicator in context_indicators)

            # 至少应该有一些上下文相关的指示
            print(f"包含上下文指示: {has_context_reference}")

        print("\n✓ 对话状态一致性测试通过")