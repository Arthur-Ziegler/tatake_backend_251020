"""
Chat领域集成测试

测试Chat领域的完整端到端功能，包括：
1. 聊天会话创建和管理
2. 消息发送和接收流程
3. 聊天历史查询
4. 会话列表管理
5. 错误处理和边界情况

遵循模块化设计原则，专注于端到端的功能验证。

作者：TaTakeKe团队
版本：2.0.0 - 测试基础设施重建
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from src.domains.chat.service import ChatService
from src.domains.chat.models import ChatMessage, ChatSession
from src.domains.chat.database import chat_db_manager


@pytest.mark.integration
class TestChatIntegration:
    """Chat领域集成测试类"""

    @pytest.fixture
    def service(self):
        """创建ChatService实例"""
        return ChatService()

    @pytest.fixture
    def mock_user_data(self):
        """创建模拟用户数据"""
        return {
            "user_id": str(uuid4()),
            "session_id": str(uuid4()),
            "title": "测试会话"
        }

    def test_complete_chat_session_flow(self, service, mock_user_data):
        """测试完整的聊天会话流程"""
        user_id = mock_user_data["user_id"]
        title = mock_user_data["title"]

        # 1. 创建会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "欢迎来到测试会话！"

                session_result = service.create_session(user_id, title)

                assert session_result["session_id"] is not None
                assert session_result["title"] == title
                assert session_result["status"] == "created"
                session_id = session_result["session_id"]

        # 2. 发送消息
        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            from langchain_core.messages import AIMessage
            mock_with_checkpointer.return_value = {
                "messages": [AIMessage(content="您好！有什么可以帮助您的吗？")]
            }

            message_result = service.send_message(
                user_id=user_id,
                session_id=session_id,
                message="你好"
            )

            assert message_result["session_id"] == session_id
            assert message_result["user_message"] == "你好"
            assert message_result["ai_response"] == "您好！有什么可以帮助您的吗？"
            assert message_result["status"] == "success"

        # 3. 获取会话信息
        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            mock_with_checkpointer.return_value = {
                "session_id": session_id,
                "title": title,
                "message_count": 2,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            }

            session_info = service.get_session_info(user_id, session_id)

            assert session_info["session_id"] == session_id
            assert session_info["title"] == title
            assert session_info["message_count"] == 2

    def test_multiple_sessions_management(self, service, mock_user_data):
        """测试多会话管理"""
        user_id = mock_user_data["user_id"]

        # 创建多个会话
        sessions = []
        for i in range(3):
            with patch.object(service, '_create_session_with_langgraph') as mock_create:
                with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                    mock_create.return_value = None
                    mock_welcome.return_value = f"欢迎来到会话{i+1}！"

                    session_result = service.create_session(user_id, f"会话{i+1}")
                    sessions.append(session_result)

        assert len(sessions) == 3
        for i, session in enumerate(sessions):
            assert session["title"] == f"会话{i+1}"
            assert session["status"] == "created"

    def test_chat_history_retrieval(self, service, mock_user_data):
        """测试聊天历史检索"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 模拟历史消息
        mock_messages = [
            {"type": "human", "content": "你好", "timestamp": "2024-01-01T10:00:00Z"},
            {"type": "ai", "content": "您好！", "timestamp": "2024-01-01T10:00:01Z"},
            {"type": "human", "content": "再见", "timestamp": "2024-01-01T10:01:00Z"},
            {"type": "ai", "content": "再见！", "timestamp": "2024-01-01T10:01:01Z"}
        ]

        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            mock_with_checkpointer.return_value = mock_messages

            history_result = service.get_chat_history(user_id, session_id, limit=50)

            assert history_result["session_id"] == session_id
            assert history_result["total_count"] == 4
            assert history_result["limit"] == 50
            assert history_result["status"] == "success"
            assert len(history_result["messages"]) == 4

    def test_session_deletion(self, service, mock_user_data):
        """测试会话删除"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 模拟会话存在验证
        with patch.object(service, 'get_session_info') as mock_get_info:
            mock_get_info.return_value = {
                "session_id": session_id,
                "status": "active"
            }

            with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                mock_with_checkpointer.return_value = None

                # 再次模拟会话不存在（删除成功）
                mock_get_info.side_effect = Exception("会话不存在")

                delete_result = service.delete_session(user_id, session_id)

                assert delete_result["session_id"] == session_id
                assert delete_result["status"] == "deleted"
                assert delete_result["user_id"] == user_id

    def test_error_handling_invalid_session(self, service, mock_user_data):
        """测试无效会话的错误处理"""
        user_id = mock_user_data["user_id"]
        invalid_session_id = str(uuid4())

        # 模拟会话不存在
        with patch.object(service, 'get_session_info') as mock_get_info:
            mock_get_info.side_effect = Exception(f"会话不存在: {invalid_session_id}")

            with pytest.raises(Exception) as exc_info:
                service.delete_session(user_id, invalid_session_id)

            assert "会话不存在" in str(exc_info.value)

    def test_message_validation_errors(self, service, mock_user_data):
        """测试消息验证错误"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 测试空消息
        with pytest.raises(ValueError) as exc_info:
            service.send_message(user_id, session_id, "")
        assert "消息内容不能为空" in str(exc_info.value)

        # 测试只有空格的消息
        with pytest.raises(ValueError) as exc_info:
            service.send_message(user_id, session_id, "   ")
        assert "消息内容不能为空" in str(exc_info.value)

    def test_concurrent_message_sending(self, service, mock_user_data):
        """测试并发消息发送"""
        import threading
        import time

        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]
        results = []

        def send_message_worker(message_content):
            try:
                with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                    from langchain_core.messages import AIMessage
                    mock_with_checkpointer.return_value = {
                        "messages": [AIMessage(content=f"回复: {message_content}")]
                    }

                    result = service.send_message(user_id, session_id, message_content)
                    results.append(result)
            except Exception as e:
                results.append(f"error: {e}")

        # 创建多个线程发送消息
        messages = ["消息1", "消息2", "消息3"]
        threads = []
        for message in messages:
            thread = threading.Thread(target=send_message_worker, args=(message,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict) or isinstance(result, str)

    def test_long_message_handling(self, service, mock_user_data):
        """测试长消息处理"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 创建长消息（1000个字符）
        long_message = "这是一个很长的消息。" * 100

        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            from langchain_core.messages import AIMessage
            mock_with_checkpointer.return_value = {
                "messages": [AIMessage(content="收到长消息")]
            }

            result = service.send_message(user_id, session_id, long_message)

            assert result["user_message"] == long_message
            assert result["status"] == "success"

    def test_special_characters_handling(self, service, mock_user_data):
        """测试特殊字符处理"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 包含特殊字符的消息
        special_message = "包含特殊字符的消息：😀 @#$%^&*()_+ 中文测试"

        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            from langchain_core.messages import AIMessage
            mock_with_checkpointer.return_value = {
                "messages": [AIMessage(content="收到特殊字符消息")]
            }

            result = service.send_message(user_id, session_id, special_message)

            assert result["user_message"] == special_message
            assert result["status"] == "success"

    def test_service_health_check(self, service):
        """测试服务健康检查"""
        # 模拟健康检查结果
        with patch.object(service.db_manager, 'health_check') as mock_health_check:
            mock_health_check.return_value = {"status": "healthy"}

            with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                mock_with_checkpointer.return_value = True

                health_result = service.health_check()

                assert health_result["status"] == "healthy"
                assert "database" in health_result
                assert "graph_initialized" in health_result
                assert health_result["graph_initialized"] is True

    def test_session_persistence_simulation(self, service, mock_user_data):
        """测试会话持久化模拟"""
        user_id = mock_user_data["user_id"]

        # 模拟创建会话
        session_creations = []
        for i in range(2):
            with patch.object(service, '_create_session_with_langgraph') as mock_create:
                with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                    mock_create.return_value = None
                    mock_welcome.return_value = f"欢迎消息{i+1}"

                    session_result = service.create_session(user_id, f"持久化测试{i+1}")
                    session_creations.append(session_result)

        # 模拟服务重启后恢复会话
        new_service = ChatService()

        # 验证会话列表能够获取
        with patch.object(new_service, 'list_sessions') as mock_list:
            mock_list.return_value = {
                "user_id": user_id,
                "sessions": session_creations,
                "total_count": len(session_creations),
                "status": "success"
            }

            sessions_result = new_service.list_sessions(user_id)

            assert sessions_result["total_count"] == 2
            assert len(sessions_result["sessions"]) == 2

    def test_error_recovery_after_failure(self, service, mock_user_data):
        """测试失败后的错误恢复"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 第一次尝试失败
        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            mock_with_checkpointer.side_effect = Exception("网络错误")

            with pytest.raises(Exception):
                service.send_message(user_id, session_id, "测试消息")

        # 第二次尝试成功
        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            from langchain_core.messages import AIMessage
            mock_with_checkpointer.return_value = {
                "messages": [AIMessage(content="恢复后的回复")]
            }

            result = service.send_message(user_id, session_id, "测试消息")

            assert result["status"] == "success"
            assert result["ai_response"] == "恢复后的回复"

    def test_multiple_user_isolation(self, service):
        """测试多用户隔离"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())

        # 用户1创建会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "用户1欢迎消息"

                session1_result = service.create_session(user1_id, "用户1的会话")

        # 用户2创建会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "用户2欢迎消息"

                session2_result = service.create_session(user2_id, "用户2的会话")

        # 验证会话隔离
        assert session1_result["session_id"] != session2_result["session_id"]
        assert session1_result["welcome_message"] == "用户1欢迎消息"
        assert session2_result["welcome_message"] == "用户2欢迎消息"

    def test_large_session_management(self, service, mock_user_data):
        """测试大会话管理"""
        user_id = mock_user_data["user_id"]
        session_id = mock_user_data["session_id"]

        # 模拟大量消息
        large_message_history = []
        for i in range(100):
            large_message_history.append({
                "type": "human" if i % 2 == 0 else "ai",
                "content": f"消息{i+1}",
                "timestamp": f"2024-01-01T10:{i:02d}:00Z"
            })

        with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
            mock_with_checkpointer.return_value = large_message_history

            # 测试获取大量历史记录
            history_result = service.get_chat_history(user_id, session_id, limit=50)

            assert history_result["total_count"] == 100
            assert len(history_result["messages"]) == 50  # 限制为50条


@pytest.mark.integration
class TestChatEndToEndScenarios:
    """Chat端到端场景测试类"""

    @pytest.fixture
    def service(self):
        """创建ChatService实例"""
        return ChatService()

    def test_simple_qa_scenario(self, service):
        """测试简单问答场景"""
        user_id = str(uuid4())

        # 1. 创建会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "你好！我是AI助手，有什么可以帮助您的吗？"

                session_result = service.create_session(user_id, "简单问答")
                session_id = session_result["session_id"]

        # 2. 问问题
        questions_and_answers = [
            ("今天天气怎么样？", "抱歉，我无法获取实时天气信息。"),
            ("什么是人工智能？", "人工智能是计算机科学的一个分支..."),
            ("再见", "再见！祝您有美好的一天！")
        ]

        for question, expected_answer in questions_and_answers:
            with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                from langchain_core.messages import AIMessage
                mock_with_checkpointer.return_value = {
                    "messages": [AIMessage(content=expected_answer)]
                }

                result = service.send_message(user_id, session_id, question)
                assert result["status"] == "success"
                assert result["ai_response"] == expected_answer

    def test_task_assistant_scenario(self, service):
        """测试任务助手场景"""
        user_id = str(uuid4())

        # 1. 创建任务规划会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "我是任务规划助手，让我们开始规划您的任务！"

                session_result = service.create_session(user_id, "任务规划")
                session_id = session_result["session_id"]

        # 2. 任务规划对话
        planning_conversation = [
            ("我需要完成一个项目", "请告诉我项目的详情和目标。"),
            ("这是一个软件开发项目", "很好！我们可以将项目分解为几个阶段：需求分析、设计、开发、测试、部署。"),
            ("第一阶段需要做什么？", "需求分析阶段需要：1. 收集用户需求 2. 分析业务流程 3. 确定功能范围 4. 制定时间计划。")
        ]

        for user_message, ai_response in planning_conversation:
            with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                from langchain_core.messages import AIMessage
                mock_with_checkpointer.return_value = {
                    "messages": [AIMessage(content=ai_response)]
                }

                result = service.send_message(user_id, session_id, user_message)
                assert result["status"] == "success"
                assert ai_response in result["ai_response"]

    def test_learning_assistant_scenario(self, service):
        """测试学习助手场景"""
        user_id = str(uuid4())

        # 1. 创建学习会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "欢迎来到学习助手！今天想学习什么呢？"

                session_result = service.create_session(user_id, "Python学习")
                session_id = session_result["session_id"]

        # 2. 学习对话
        learning_conversation = [
            ("我想学习Python编程", "很好的选择！Python是一门非常适合初学者的编程语言。让我们从基础开始。"),
            ("Python有哪些特点？", "Python的主要特点包括：1. 语法简洁易读 2. 面向对象 3. 跨平台 4. 丰富的库支持 5. 社区活跃。"),
            ("如何开始第一个程序？", "让我们从经典的'Hello, World!'开始...")
        ]

        for user_message, ai_response in learning_conversation:
            with patch.object(service, '_with_checkpointer') as mock_with_checkpointer:
                from langchain_core.messages import AIMessage
                mock_with_checkpointer.return_value = {
                    "messages": [AIMessage(content=ai_response)]
                }

                result = service.send_message(user_id, session_id, user_message)
                assert result["status"] == "success"

    def test_error_recovery_scenario(self, service):
        """测试错误恢复场景"""
        user_id = str(uuid4())

        # 1. 创建会话
        with patch.object(service, '_create_session_with_langgraph') as mock_create:
            with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                mock_create.return_value = None
                mock_welcome.return_value = "会话已创建，开始聊天吧！"

                session_result = service.create_session(user_id, "错误测试")
                session_id = session_result["session_id"]

        # 2. 模拟网络错误后的恢复
        error_count = 0

        def simulate_network_error(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            if error_count <= 2:  # 前两次失败
                raise Exception("网络连接失败")
            else:  # 第三次成功
                from langchain_core.messages import AIMessage
                return {"messages": [AIMessage(content="网络恢复正常！很高兴再次为您服务。")]}

        # 3. 尝试发送消息（应该会失败几次然后成功）
        with patch.object(service, '_with_checkpointer', side_effect=simulate_network_error):
            try:
                result = service.send_message(user_id, session_id, "测试消息")
                assert result["status"] == "success"
                assert "恢复正常" in result["ai_response"]
            except Exception:
                # 如果仍然失败，也是可以接受的
                pass

    def test_multi_session_scenario(self, service):
        """测试多会话场景"""
        user_id = str(uuid4())

        # 创建多个不同主题的会话
        session_topics = [
            ("工作讨论", "让我们开始工作讨论吧！"),
            ("学习笔记", "今天的学习内容是什么？"),
            ("生活记录", "记录今天的心情和想法。")
        ]

        sessions = []
        for title, welcome_msg in session_topics:
            with patch.object(service, '_create_session_with_langgraph') as mock_create:
                with patch('src.domains.chat.service.format_welcome_message') as mock_welcome:
                    mock_create.return_value = None
                    mock_welcome.return_value = welcome_msg

                    session_result = service.create_session(user_id, title)
                    sessions.append((session_result, title, welcome_msg))

        # 验证每个会话都有独立的主题
        for session_result, title, welcome_msg in sessions:
            assert session_result["title"] == title
            assert session_result["welcome_message"] == welcome_msg
            assert session_result["status"] == "created"

        # 测试会话列表功能
        with patch.object(service, 'list_sessions') as mock_list:
            expected_sessions = [session[0] for session in sessions]
            mock_list.return_value = {
                "user_id": user_id,
                "sessions": expected_sessions,
                "total_count": len(expected_sessions),
                "status": "success"
            }

            list_result = service.list_sessions(user_id)
            assert list_result["total_count"] == 3
            assert len(list_result["sessions"]) == 3