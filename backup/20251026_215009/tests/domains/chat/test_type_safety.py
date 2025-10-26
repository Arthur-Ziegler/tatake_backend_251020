"""
类型安全测试套件

设计动机：
这个测试套件是为了解决一个关键的类型安全问题而创建的。

问题背景：
在 ChatService.send_message() 方法中，我们发现了一个难以调试的类型错误：
TypeError: '>' not supported between instances of 'str' and 'int'

经过深入分析，发现问题的根源是：
- LangGraph 内部的某些 channel（特别是 __start__）的版本号会被转换为复杂字符串格式
- 例如：'__start__': '00000000000000000000000000000002.0.243798848838515'
- 当 LangGraph 尝试在 get_new_channel_versions() 中比较这些字符串版本号与整数版本号时，会抛出类型错误
- 这导致 ChatService 的消息发送功能完全失败

测试目标：
1. 确保类型安全修复方案的有效性
2. 验证 checkpoint 的类型一致性
3. 测试 ChatService 的端到端类型安全
4. 防止未来出现类似的类型问题

测试策略：
- 直接测试 checkpoint 的类型一致性
- 端到端测试 ChatService 的完整流程
- 多消息场景的压力测试
- 并发访问的稳定性测试
- 类型安全包装器的功能测试

这些测试对于确保 ChatService 的稳定性和可靠性至关重要。
"""

import pytest
import tempfile
import os
from uuid import uuid4

from src.domains.chat.service import ChatService
from src.domains.chat.database import create_chat_checkpointer, create_memory_store
from src.domains.chat.graph import create_chat_graph
from src.domains.chat.models import create_chat_state
from langchain_core.messages import HumanMessage


class TestTypeSafety:
    """类型安全测试类"""

    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def chat_service_with_temp_db(self, temp_db_path):
        """使用临时数据库的聊天服务"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            service = ChatService()
            yield service
        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_checkpoint_type_consistency(self, temp_db_path):
        """
        测试 checkpoint 类型一致性

        设计动机：
        这是最基础的类型安全测试。我们需要确保 checkpoint 的 channel_versions
        字段中的所有值都是整数类型，避免类型比较错误。

        测试场景：
        1. 创建明确使用整数类型的 checkpoint
        2. 存储 checkpoint 到数据库
        3. 检索 checkpoint 并验证类型保持一致

        为什么重要：
        如果 checkpoint 在存储/检索过程中类型发生变化，就会导致
        ChatService.send_message() 完全失败。这个测试确保了基础的类型安全性。

        Args:
            temp_db_path: 临时数据库路径
        """
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            with create_chat_checkpointer() as checkpointer:
                config = {"configurable": {"thread_id": "test", "checkpoint_ns": ""}}

                # 创建明确使用整数类型的 checkpoint
                checkpoint = {
                    "v": 1,
                    "ts": 0,
                    "id": "test-checkpoint",
                    "channel_values": {"messages": []},
                    "channel_versions": {"messages": 1},  # 明确的整数类型
                    "versions_seen": {},
                    "pending_sends": []
                }

                # 验证原始类型
                assert isinstance(checkpoint["channel_versions"]["messages"], int)

                # 存储 checkpoint
                checkpointer.put(config, checkpoint, {}, {})

                # 检索并验证类型保持一致
                retrieved = checkpointer.get(config)
                assert retrieved is not None, "应该能够检索 checkpoint"
                assert isinstance(retrieved["channel_versions"]["messages"], int), \
                    "检索后的 channel_versions.messages 应该保持整数类型"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_chat_service_end_to_end_type_safety(self, chat_service_with_temp_db):
        """
        测试 ChatService 端到端类型安全

        设计动机：
        这是关键的集成测试。类型错误只在使用 ChatService 完整流程时才会出现，
        单独的组件测试无法发现这个问题。

        测试场景：
        1. 创建会话（这会初始化 checkpoint）
        2. 验证会话创建后的 checkpoint 类型正确性
        3. 发送消息（这会触发 LangGraph 的类型问题）
        4. 验证消息发送后的 checkpoint 类型正确性

        为什么重要：
        这个测试能够复现原始的 bug：
        TypeError: '>' not supported between instances of 'str' and 'int'

        如果这个测试通过，说明我们的类型安全修复方案是有效的。

        Args:
            chat_service_with_temp_db: 使用临时数据库的 ChatService 实例
        """
        user_id = f"test-user-{uuid4()}"

        # 创建会话
        session_result = chat_service_with_temp_db.create_session(user_id, "类型安全测试")
        session_id = session_result['session_id']

        # 验证会话创建后的 checkpoint 类型
        with chat_service_with_temp_db.db_manager.create_checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            checkpoint = checkpointer.get(config)
            assert checkpoint is not None, "会话创建后应该存在 checkpoint"

            if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                channel_versions = checkpoint["channel_versions"]
                assert isinstance(channel_versions, dict), "channel_versions 应该是字典"

                for key, value in channel_versions.items():
                    assert isinstance(value, int), \
                        f"channel_versions.{key} 应该是整数类型，实际是 {type(value)}"

        # 发送消息
        try:
            result = chat_service_with_temp_db.send_message(
                user_id, session_id, "这是一个类型安全测试消息"
            )

            # 验证结果
            assert result['status'] == 'success', "消息发送应该成功"
            assert 'ai_response' in result, "应该包含 AI 回复"

            # 验证消息发送后的 checkpoint 类型
            with chat_service_with_temp_db.db_manager.create_checkpointer() as checkpointer:
                checkpoint = checkpointer.get(config)
                if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                    channel_versions = checkpoint["channel_versions"]
                    for key, value in channel_versions.items():
                        assert isinstance(value, int), \
                            f"消息发送后 channel_versions.{key} 应该保持整数类型，实际是 {type(value)}"

        except Exception as e:
            pytest.fail(f"ChatService 端到端测试失败: {e}")

    def test_multiple_message_type_consistency(self, chat_service_with_temp_db):
        """测试多条消息的类型一致性"""
        user_id = f"test-user-{uuid4()}"

        # 创建会话
        session_result = chat_service_with_temp_db.create_session(user_id, "多消息测试")
        session_id = session_result['session_id']

        # 发送多条消息
        messages = [
            "第一条测试消息",
            "第二条测试消息",
            "第三条测试消息"
        ]

        for i, message in enumerate(messages, 1):
            try:
                result = chat_service_with_temp_db.send_message(user_id, session_id, message)
                assert result['status'] == 'success', f"第 {i} 条消息发送应该成功"

                # 每次发送后检查类型一致性
                with chat_service_with_temp_db.db_manager.create_checkpointer() as checkpointer:
                    config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
                    checkpoint = checkpointer.get(config)

                    if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                        channel_versions = checkpoint["channel_versions"]
                        for key, value in channel_versions.items():
                            assert isinstance(value, int), \
                                f"第 {i} 条消息后 channel_versions.{key} 应该保持整数类型"

            except Exception as e:
                pytest.fail(f"第 {i} 条消息发送失败: {e}")

    def test_graph_direct_invocation_type_safety(self, temp_db_path):
        """测试直接图调用的类型安全"""
        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            with create_chat_checkpointer() as checkpointer:
                store = create_memory_store()
                graph = create_chat_graph(checkpointer, store)

                session_id = f"direct-test-{uuid4()}"
                config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

                # 创建状态
                state = create_chat_state('test-user', session_id, '直接调用测试')
                state['messages'] = [HumanMessage(content='直接调用测试消息')]

                # 调用图
                result = graph.graph.invoke(state, config)
                assert result is not None, "直接图调用应该成功"

                # 检查调用后的类型一致性
                checkpoint = checkpointer.get(config)
                if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                    channel_versions = checkpoint["channel_versions"]
                    for key, value in channel_versions.items():
                        assert isinstance(value, int), \
                            f"直接调用后 channel_versions.{key} 应该保持整数类型"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_type_safe_checkpointer_wrapper(self, temp_db_path):
        """
        测试类型安全 checkpointer 包装器

        设计动机：
        这个测试专门验证我们的类型安全修复方案的核心组件。
        TypeSafeCheckpointer 包装器是解决问题的关键，需要确保它能正确处理各种类型转换。

        测试场景：
        1. 创建包含字符串版本号的问题 checkpoint（模拟 LangGraph 内部行为）
        2. 使用类型安全包装器存储 checkpoint
        3. 验证包装器正确修复了类型问题
        4. 检索并确认类型保持为整数

        测试的关键点：
        - 包装器能否正确识别字符串类型的版本号
        - 能否将复杂字符串（如 UUID）转换为稳定的整数
        - 修复后的类型是否在检索时保持正确

        为什么重要：
        这是我们的防御性修复方案的核心。如果包装器工作不正常，
        ChatService 仍然会遇到类型错误。

        Args:
            temp_db_path: 临时数据库路径
        """
        from src.domains.chat.service import ChatService

        original_env = os.environ.get('CHAT_DB_PATH')
        os.environ['CHAT_DB_PATH'] = temp_db_path

        try:
            service = ChatService()

            # 创建类型安全包装器
            base_checkpointer = service.db_manager.create_checkpointer()
            safe_checkpointer = service._create_type_safe_checkpointer(base_checkpointer)

            with base_checkpointer as cp:
                safe_cp = safe_checkpointer(cp)
                config = {"configurable": {"thread_id": "wrapper-test", "checkpoint_ns": ""}}

                # 测试字符串类型的修复
                problematic_checkpoint = {
                    "v": 1,
                    "ts": 0,
                    "id": "wrapper-test-checkpoint",
                    "channel_values": {"messages": []},
                    "channel_versions": {"messages": "1"},  # 故意使用字符串
                    "versions_seen": {},
                    "pending_sends": []
                }

                # 存储（应该修复类型）
                safe_cp.put(config, problematic_checkpoint, {}, {})

                # 检索（应该保持整数类型）
                retrieved = safe_cp.get(config)
                assert retrieved is not None, "应该能够检索 checkpoint"
                assert isinstance(retrieved["channel_versions"]["messages"], int), \
                    "包装器应该修复类型问题"

        finally:
            if original_env:
                os.environ['CHAT_DB_PATH'] = original_env
            elif 'CHAT_DB_PATH' in os.environ:
                del os.environ['CHAT_DB_PATH']

    def test_concurrent_access_type_safety(self, chat_service_with_temp_db):
        """测试并发访问的类型安全"""
        import threading
        import time

        user_id = f"test-user-{uuid4()}"

        # 创建会话
        session_result = chat_service_with_temp_db.create_session(user_id, "并发测试")
        session_id = session_result['session_id']

        results = []
        errors = []

        def send_message_worker(message_index):
            """发送消息的工作线程"""
            try:
                result = chat_service_with_temp_db.send_message(
                    user_id, session_id, f"并发测试消息 {message_index}"
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时发送消息
        threads = []
        for i in range(3):
            thread = threading.Thread(target=send_message_worker, args=(i,))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发访问不应该有错误，实际错误: {errors}"
        assert len(results) == 3, f"应该有 3 个成功的结果，实际: {len(results)}"

        # 验证最终的类型一致性
        with chat_service_with_temp_db.db_manager.create_checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}
            checkpoint = checkpointer.get(config)

            if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                channel_versions = checkpoint["channel_versions"]
                for key, value in channel_versions.items():
                    assert isinstance(value, int), \
                        f"并发访问后 channel_versions.{key} 应该保持整数类型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])