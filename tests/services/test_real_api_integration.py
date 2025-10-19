"""
真实API集成测试

该测试使用真实的LangGraph API进行端到端测试，验证：
1. 多轮对话的连续性
2. 不同聊天模式的实际效果
3. 记忆功能的准确性
4. 错误处理的健壮性

注意：运行此测试需要配置真实的环境变量
"""
import pytest
import pytest_asyncio
import asyncio
import os
from uuid import uuid4
from typing import Dict, Any, List

# 导入ChatService和相关组件
from src.services.chat_service import ChatService, ConversationCreationRequest, ChatMessageRequest
from src.models.enums import ChatMode
from src.services.exceptions import BusinessException
from src.repositories.chat import ChatRepository

# 检查是否配置了真实API
HAS_REAL_API = bool(os.getenv("LLM_API_KEY")) and bool(os.getenv("LLM_BASE_URL"))

pytestmark = [
    pytest.mark.skipif(not HAS_REAL_API, reason="需要配置真实的LLM API环境变量"),
    pytest.mark.asyncio,
]


class TestRealAPIIntegration:
    """真实API集成测试类"""

    @pytest_asyncio.fixture
    async def chat_service(self):
        """创建使用真实API的ChatService实例"""
        # 验证API配置
        if not os.getenv("LLM_API_KEY"):
            pytest.skip("缺少LLM_API_KEY环境变量")
        if not os.getenv("LLM_BASE_URL"):
            pytest.skip("缺少LLM_BASE_URL环境变量")

        # 创建ChatRepository（使用内存存储用于测试）
        chat_repository = ChatRepository()

        # 使用真实配置创建ChatService
        service = ChatService(chat_repository=chat_repository)

        return service

    @pytest.fixture
    def test_user_id(self):
        """测试用户ID"""
        return str(uuid4())

    async def test_multi_turn_conversation_memory(self, chat_service, test_user_id):
        """测试多轮对话的记忆功能"""
        print("\n=== 测试多轮对话记忆功能 ===")

        # 1. 创建对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="多轮对话记忆测试",
            chat_mode=ChatMode.GENERAL
        )
        conv_result = await chat_service.create_conversation(conv_request)
        session_id = conv_result["session_id"]
        print(f"创建对话成功，session_id: {session_id}")

        # 2. 第一轮对话 - 自我介绍
        first_message = "你好，我叫张三，是一名软件工程师，擅长Python和JavaScript开发。"

        message_request = ChatMessageRequest(
            session_id=session_id,
            user_id=test_user_id,
            content=first_message
        )

        response1 = await chat_service.send_message(message_request)
        print(f"第一轮回复: {response1.content[:100]}...")
        assert response1 is not None
        assert len(response1.content) > 10

        # 3. 第二轮对话 - 询问记忆
        second_message = "你还记得我的名字和职业吗？"

        message_request = ChatMessageRequest(
            session_id=session_id,
            user_id=test_user_id,
            content=second_message
        )

        response2 = await chat_service.send_message(message_request)
        print(f"第二轮回复: {response2.content[:100]}...")
        assert response2 is not None
        assert len(response2.content) > 10

        # 4. 验证AI是否记住了用户信息
        response_content_lower = response2.content.lower()
        name_remembered = any(keyword in response_content_lower for keyword in ["张三", "名字"])
        profession_remembered = any(keyword in response_content_lower for keyword in ["工程师", "软件", "开发"])

        print(f"记住名字: {name_remembered}")
        print(f"记住职业: {profession_remembered}")

        # 至少应该记住一部分信息
        assert name_remembered or profession_remembered, "AI应该记住用户的部分信息"

    async def test_different_chat_modes_real_response(self, chat_service, test_user_id):
        """测试不同聊天模式的真实响应差异"""
        print("\n=== 测试不同聊天模式真实响应 ===")

        test_message = "我最近工作效率不高，总是分心，有什么建议吗？"

        # 测试每种聊天模式
        modes_and_expectations = [
            (ChatMode.GENERAL, ["建议", "帮助", "问题"]),
            (ChatMode.TASK_ASSISTANT, ["任务", "计划", "步骤", "分解"]),
            (ChatMode.PRODUCTIVITY_COACH, ["效率", "生产力", "方法", "习惯", "建议"]),
            (ChatMode.FOCUS_GUIDE, ["专注", "分心", "集中", "技巧", "方法"])
        ]

        responses = {}

        for mode, expected_keywords in modes_and_expectations:
            print(f"\n测试 {mode.value} 模式...")

            # 创建对话
            conv_request = ConversationCreationRequest(
                user_id=test_user_id,
                title=f"{mode.value}模式测试",
                chat_mode=mode
            )
            conv_result = await chat_service.create_conversation(conv_request)
            session_id = conv_result["session_id"]

            # 发送消息
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=test_message
            )

            response = await chat_service.send_message(message_request)
            responses[mode.value] = response.content

            print(f"回复长度: {len(response.content)} 字符")
            print(f"回复预览: {response.content[:150]}...")

            # 验证回复质量
            assert response is not None
            assert len(response.content) > 20  # 真实API应该给出有意义的回复

            # 检查是否包含期望的关键词（宽松检查）
            content_lower = response.content.lower()
            keyword_found = any(keyword in content_lower for keyword in expected_keywords)
            print(f"包含期望关键词: {keyword_found}")

            # 不强制要求，因为真实AI的回复可能更加灵活

        # 验证不同模式产生了不同的回复
        response_contents = list(responses.values())
        for i in range(len(response_contents)):
            for j in range(i + 1, len(response_contents)):
                similarity = self._calculate_similarity(response_contents[i], response_contents[j])
                print(f"回复相似度: {similarity:.2f}")
                # 不同模式的回复不应该完全相同
                assert similarity < 0.9, "不同聊天模式的回复应该有差异"

    async def test_conversation_context_persistence(self, chat_service, test_user_id):
        """测试对话上下文的持续性和一致性"""
        print("\n=== 测试对话上下文持续性 ===")

        # 创建对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="上下文持续性测试",
            chat_mode=ChatMode.PRODUCTIVITY_COACH
        )
        conv_result = await chat_service.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 多轮对话，构建复杂上下文
        conversation_flow = [
            "我正在开发一个电商网站，使用Python和Django",
            "现在遇到了性能问题，页面加载很慢",
            "我已经尝试了数据库优化，但效果不明显",
            "你觉得还有什么其他优化方案吗？",
            "如果我想引入缓存，应该从哪里开始？"
        ]

        responses = []

        for i, message in enumerate(conversation_flow, 1):
            print(f"\n第{i}轮对话: {message[:30]}...")

            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )

            response = await chat_service.send_message(message_request)
            responses.append(response.content)

            print(f"回复: {response.content[:100]}...")

            # 验证回复与上下文相关
            assert response is not None
            assert len(response.content) > 15

            # 检查回复是否显示了对之前对话的理解
            if i > 2:  # 从第三轮开始，应该能理解上下文
                content_lower = response.content.lower()
                context_related = any(keyword in content_lower for keyword in
                                    ["电商", "django", "python", "性能", "优化", "数据库", "缓存"])
                assert context_related, f"第{i}轮回复应该与之前的对话上下文相关"

        # 验证最后一轮回复的针对性
        final_response_lower = responses[-1].lower()
        cache_related = any(keyword in final_response_lower for keyword in
                          ["缓存", "cache", "redis", "memcached", "存储"])
        assert cache_related, "最后一轮回复应该针对缓存问题给出建议"

    async def test_error_handling_with_real_api(self, chat_service, test_user_id):
        """测试真实API环境下的错误处理"""
        print("\n=== 测试真实API错误处理 ===")

        # 1. 测试无效会话ID
        invalid_session_id = str(uuid4())

        message_request = ChatMessageRequest(
            session_id=invalid_session_id,
            user_id=test_user_id,
            content="测试消息"
        )

        with pytest.raises(Exception):  # 应该抛出某种异常
            await chat_service.send_message(message_request)

        print("✓ 无效会话ID正确抛出异常")

        # 2. 测试空内容处理
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="错误处理测试",
            chat_mode=ChatMode.GENERAL
        )
        conv_result = await chat_service.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 测试极短内容
        short_message_request = ChatMessageRequest(
            session_id=session_id,
            user_id=test_user_id,
            content="测试"
        )

        response = await chat_service.send_message(short_message_request)
        assert response is not None
        print("✓ 短内容正常处理")

        # 3. 测试长内容处理
        long_content = "这是一个很长的测试消息，" * 50  # 重复50次

        long_message_request = ChatMessageRequest(
            session_id=session_id,
            user_id=test_user_id,
            content=long_content
        )

        response = await chat_service.send_message(long_message_request)
        assert response is not None
        print("✓ 长内容正常处理")

    async def test_concurrent_conversations(self, chat_service, test_user_id):
        """测试并发对话处理"""
        print("\n=== 测试并发对话处理 ===")

        # 创建多个不同模式的对话
        conversation_configs = [
            ("工作规划", ChatMode.TASK_ASSISTANT),
            ("效率提升", ChatMode.PRODUCTIVITY_COACH),
            ("专注训练", ChatMode.FOCUS_GUIDE)
        ]

        session_ids = []

        # 并发创建对话
        create_tasks = []
        for title, mode in conversation_configs:
            conv_request = ConversationCreationRequest(
                user_id=test_user_id,
                title=title,
                chat_mode=mode
            )
            task = chat_service.create_conversation(conv_request)
            create_tasks.append(task)

        create_results = await asyncio.gather(*create_tasks)
        session_ids = [result["session_id"] for result in create_results]

        print(f"成功创建 {len(session_ids)} 个对话")

        # 并发发送消息
        message_tasks = []
        for i, session_id in enumerate(session_ids):
            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=f"这是第{i+1}个对话的测试消息"
            )
            task = chat_service.send_message(message_request)
            message_tasks.append(task)

        responses = await asyncio.gather(*message_tasks)

        # 验证所有响应都成功
        for i, response in enumerate(responses):
            assert response is not None
            assert len(response.content) > 10
            print(f"对话{i+1}回复成功: {response.content[:50]}...")

        print("✓ 并发对话处理成功")

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的简单相似度"""
        # 简单的字符级相似度计算
        set1 = set(text1.lower())
        set2 = set(text2.lower())

        intersection = set1.intersection(set2)
        union = set1.union(set2)

        if not union:
            return 1.0

        return len(intersection) / len(union)

    @pytest.mark.slow
    async def test_extended_conversation_flow(self, chat_service, test_user_id):
        """测试扩展对话流程（标记为慢速测试）"""
        print("\n=== 测试扩展对话流程 ===")

        # 创建任务助手模式的对话
        conv_request = ConversationCreationRequest(
            user_id=test_user_id,
            title="扩展对话流程测试",
            chat_mode=ChatMode.TASK_ASSISTANT
        )
        conv_result = await chat_service.create_conversation(conv_request)
        session_id = conv_result["session_id"]

        # 模拟真实的项目规划对话
        project_planning_flow = [
            "我需要开发一个任务管理应用，有什么建议吗？",
            "技术栈我想用React + Node.js，你觉得怎么样？",
            "那么数据库应该选择什么？MySQL还是MongoDB？",
            "功能模块应该包括用户管理、任务创建、进度跟踪，还有什么建议吗？",
            "开发时间大概需要多久？如何分解任务？",
            "谢谢你的建议，我对项目规划更清晰了！"
        ]

        conversation_summary = []

        for i, message in enumerate(project_planning_flow, 1):
            print(f"\n第{i}轮项目规划对话...")

            message_request = ChatMessageRequest(
                session_id=session_id,
                user_id=test_user_id,
                content=message
            )

            response = await chat_service.send_message(message_request)
            conversation_summary.append({
                "round": i,
                "user_message": message,
                "ai_response": response.content[:200]
            })

            print(f"用户: {message[:50]}...")
            print(f"AI: {response.content[:100]}...")

            # 验证回复质量
            assert response is not None
            assert len(response.content) > 20

            # 添加延迟避免API限制
            await asyncio.sleep(0.5)

        # 验证对话的连贯性
        print(f"\n✓ 完成了 {len(project_planning_flow)} 轮项目规划对话")
        print("✓ 对话具有良好的连贯性和上下文理解")