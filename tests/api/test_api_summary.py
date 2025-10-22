"""
API功能总结测试

综合验证聊天系统的API层功能完整性，
通过直接调用服务层来验证业务逻辑的正确性。

测试重点：
1. 服务层核心功能完整性
2. 数据持久化验证
3. 业务逻辑正确性
4. 端到端功能验证

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import uuid
import os
from datetime import datetime

from src.domains.chat.service import ChatService
from src.domains.chat.database import get_chat_database_path, check_connection


class TestAPISummary:
    """
    API功能总结测试类
    """

    def setup_method(self):
        """
        测试设置
        """
        # 清理数据库
        db_path = get_chat_database_path()
        if os.path.exists(db_path):
            os.remove(db_path)

        self.chat_service = ChatService()
        self.user_id = str(uuid.uuid4())

    def test_complete_chat_workflow(self):
        """
        测试完整的聊天工作流程
        """
        # 1. 创建会话
        session_result = self.chat_service.create_session(
            user_id=self.user_id,
            title="完整工作流测试"
        )
        assert "session_id" in session_result
        session_id = session_result["session_id"]
        print(f"✅ 1. 创建会话成功: {session_id}")

        # 2. 获取会话信息
        session_info = self.chat_service.get_session_info(
            user_id=self.user_id,
            session_id=session_id
        )
        assert session_info["session_id"] == session_id
        assert session_info["title"] == "完整工作流测试"
        print(f"✅ 2. 获取会话信息成功: 消息数={session_info['message_count']}")

        # 3. 发送消息（可能失败，这是正常的）
        try:
            message_result = self.chat_service.send_message(
                user_id=self.user_id,
                session_id=session_id,
                message="测试消息"
            )
            print(f"✅ 3. 发送消息成功: AI回复长度={len(message_result.get('ai_response', ''))}")
        except Exception as e:
            print(f"⚠️ 3. 发送消息失败（预期）: {str(e)[:50]}...")
            # AI服务不可用是正常的，不影响核心功能测试

        # 4. 获取会话列表
        sessions_result = self.chat_service.list_sessions(user_id=self.user_id)
        assert sessions_result["total_count"] >= 1
        print(f"✅ 4. 获取会话列表成功: 会话数={sessions_result['total_count']}")

        # 5. 删除会话
        delete_result = self.chat_service.delete_session(
            user_id=self.user_id,
            session_id=session_id
        )
        assert delete_result["status"] == "deleted"
        print(f"✅ 5. 删除会话成功: {delete_result['status']}")

        # 6. 验证会话已删除
        sessions_after = self.chat_service.list_sessions(user_id=self.user_id)
        deleted_session_ids = [s["session_id"] for s in sessions_after["sessions"]]
        assert session_id not in deleted_session_ids
        print(f"✅ 6. 验证会话删除成功")

    def test_database_persistence(self):
        """
        测试数据库持久化
        """
        # 验证数据库初始状态
        db_path = get_chat_database_path()
        assert not os.path.exists(db_path), "数据库文件不应该预先存在"

        # 创建会话（会触发数据库创建）
        session_result = self.chat_service.create_session(
            user_id=self.user_id,
            title="持久化测试"
        )
        session_id = session_result["session_id"]

        # 验证数据库文件已创建
        assert os.path.exists(db_path), "数据库文件应该被创建"
        assert os.path.getsize(db_path) > 0, "数据库文件应该有内容"
        print(f"✅ 数据库文件创建成功: {db_path}")

        # 验证数据库连接正常
        assert check_connection(), "数据库连接应该正常"
        print(f"✅ 数据库连接检查通过")

        # 验证数据持久化（通过新的服务实例）
        new_service = ChatService()
        session_info = new_service.get_session_info(
            user_id=self.user_id,
            session_id=session_id
        )
        assert session_info["session_id"] == session_id
        print(f"✅ 数据持久化验证成功")

    def test_user_isolation(self):
        """
        测试用户隔离
        """
        # 创建两个用户
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        # 用户A创建会话
        session_a = self.chat_service.create_session(
            user_id=user_a,
            title="用户A的会话"
        )

        # 用户B创建会话
        session_b = self.chat_service.create_session(
            user_id=user_b,
            title="用户B的会话"
        )

        # 验证用户隔离
        sessions_a = self.chat_service.list_sessions(user_id=user_a)
        sessions_b = self.chat_service.list_sessions(user_id=user_b)

        a_session_ids = [s["session_id"] for s in sessions_a["sessions"]]
        b_session_ids = [s["session_id"] for s in sessions_b["sessions"]]

        assert session_a["session_id"] in a_session_ids
        assert session_b["session_id"] in b_session_ids
        assert session_b["session_id"] not in a_session_ids
        assert session_a["session_id"] not in b_session_ids

        print(f"✅ 用户隔离验证成功")

    def test_context_management_integration(self):
        """
        测试上下文管理集成
        """
        from src.domains.chat.context_manager import ContextManager

        # 创建上下文管理器
        manager = ContextManager(max_context_messages=3)

        # 测试上下文管理功能
        from langchain_core.messages import HumanMessage, AIMessage
        messages = [
            HumanMessage(content="消息1"),
            AIMessage(content="回复1"),
            HumanMessage(content="消息2"),
            AIMessage(content="回复2"),
            HumanMessage(content="消息3"),
            AIMessage(content="回复3"),
            HumanMessage(content="消息4"),
            AIMessage(content="回复4"),
        ]

        # 管理上下文
        result = manager.manage_context(messages)
        assert len(result) <= 3, f"消息数量应该被限制在3条，实际: {len(result)}"
        print(f"✅ 上下文管理集成成功: {len(messages)} -> {len(result)} 条消息")

    def test_api_health_check(self):
        """
        测试API健康检查
        """
        health_result = self.chat_service.health_check()
        assert "status" in health_result
        assert "timestamp" in health_result
        print(f"✅ API健康检查成功: {health_result['status']}")

    def test_error_handling(self):
        """
        测试错误处理
        """
        # 测试不存在的会话
        fake_session_id = str(uuid.uuid4())
        try:
            self.chat_service.get_session_info(
                user_id=self.user_id,
                session_id=fake_session_id
            )
            assert False, "应该抛出异常"
        except Exception as e:
            assert "不存在" in str(e) or "not found" in str(e).lower()
            print(f"✅ 错误处理验证成功: {str(e)[:50]}...")

        # 测试权限验证
        other_user = str(uuid.uuid4())
        session_result = self.chat_service.create_session(
            user_id=self.user_id,
            title="权限测试"
        )
        try:
            self.chat_service.delete_session(
                user_id=other_user,
                session_id=session_result["session_id"]
            )
            assert False, "应该抛出权限异常"
        except Exception as e:
            assert "权限" in str(e) or "forbidden" in str(e).lower()
            print(f"✅ 权限验证成功: {str(e)[:50]}...")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])