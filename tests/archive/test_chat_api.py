#!/usr/bin/env python3
"""
AI聊天API功能测试

测试AI聊天API的基本功能，包括：
1. 会话创建
2. 消息发送
3. 会话列表获取
4. 会话详情获取
5. 消息历史获取
"""

import asyncio
import sys
import json
from uuid import uuid4

sys.path.append('.')

from src.api.main import app
from src.services.simple_chat_service import SimpleChatService
from src.repositories.chat import ChatRepository
from src.models.enums import ChatMode, SessionStatus, MessageRole
from src.api.dependencies import get_db_session, initialize_dependencies, service_factory


async def test_chat_api():
    """测试聊天API功能"""
    print("🚀 开始AI聊天API功能测试")

    try:
        # 初始化依赖
        print("🔧 初始化依赖注入系统...")
        await initialize_dependencies()
        print("✅ 依赖注入系统初始化成功")
        # 获取数据库会话
        async for session in get_db_session():
            print("✅ 数据库连接成功")

            # 初始化Repository和Service
            chat_repo = ChatRepository(session)
            chat_service = SimpleChatService(chat_repo=chat_repo)
            print("✅ 聊天服务初始化成功")

            # 测试用户ID
            test_user_id = str(uuid4())
            print(f"📝 使用测试用户ID: {test_user_id}")

            # 1. 测试创建聊天会话
            print("\n📌 测试1: 创建聊天会话")
            session_data = await chat_service.create_session(
                user_id=test_user_id,
                title="测试会话",
                chat_mode="general",
                initial_message="你好，这是一个测试消息"
            )
            print(f"✅ 会话创建成功: {session_data['id']}")
            session_id = session_data['id']

            # 2. 测试获取会话详情
            print("\n📌 测试2: 获取会话详情")
            session_detail = await chat_service.get_session(session_id, test_user_id)
            print(f"✅ 会话详情获取成功: {session_detail['title']}")
            print(f"   消息数量: {session_detail['message_count']}")
            print(f"   聊天模式: {session_detail['chat_mode']}")

            # 3. 测试发送消息
            print("\n📌 测试3: 发送聊天消息")
            message_response = await chat_service.send_message(
                session_id=session_id,
                user_id=test_user_id,
                content="请介绍一下你的功能",
                message_type="text"
            )
            print(f"✅ 消息发送成功")
            print(f"   AI回复: {message_response['content'][:50]}...")
            print(f"   处理时间: {message_response['metadata']['processing_time_ms']:.2f}ms")

            # 4. 测试获取会话列表
            print("\n📌 测试4: 获取会话列表")
            sessions_list = await chat_service.get_sessions(
                user_id=test_user_id,
                page=1,
                limit=10
            )
            print(f"✅ 会话列表获取成功: {sessions_list['total']}个会话")
            for session in sessions_list['items']:
                print(f"   - {session['title']} ({session['message_count']}条消息)")

            # 5. 测试获取消息历史
            print("\n📌 测试5: 获取消息历史")
            message_history = await chat_service.get_message_history(
                session_id=session_id,
                user_id=test_user_id,
                limit=10
            )
            print(f"✅ 消息历史获取成功: {message_history['total']}条消息")
            for message in message_history['messages']:
                role = "用户" if message['role'] == 'user' else "助手"
                content = message['content'][:30] + "..." if len(message['content']) > 30 else message['content']
                print(f"   - {role}: {content}")

            # 6. 测试更新会话
            print("\n📌 测试6: 更新会话")
            updated_session = await chat_service.update_session(
                session_id=session_id,
                user_id=test_user_id,
                title="更新后的测试会话",
                tags=["测试", "API"]
            )
            print(f"✅ 会话更新成功: {updated_session['title']}")
            print(f"   标签: {updated_session['metadata'].get('tags', [])}")

            # 7. 测试聊天统计
            print("\n📌 测试7: 获取聊天统计")
            statistics = await chat_service.get_chat_statistics(test_user_id, "week")
            print(f"✅ 统计信息获取成功:")
            print(f"   - 总会话数: {statistics['total_sessions']}")
            print(f"   - 活跃会话: {statistics['active_sessions']}")
            print(f"   - 总消息数: {statistics['total_messages']}")
            print(f"   - 用户消息: {statistics['user_messages']}")
            print(f"   - AI消息: {statistics['ai_messages']}")

            # 8. 测试会话摘要
            print("\n📌 测试8: 生成会话摘要")
            summary = await chat_service.summarize_session(session_id, test_user_id)
            print(f"✅ 会话摘要生成成功:")
            print(f"   摘要: {summary['summary']}")
            print(f"   关键点: {', '.join(summary['key_points'])}")
            print(f"   行动项: {', '.join(summary['action_items'])}")

            # 9. 测试会话导出
            print("\n📌 测试9: 导出会话")
            export_result = await chat_service.export_session(session_id, test_user_id, "markdown")
            print(f"✅ 会话导出成功:")
            print(f"   格式: {export_result['format']}")
            print(f"   消息数量: {export_result['message_count']}")
            print(f"   内容长度: {export_result['content_length']}字符")

            # 10. 测试删除会话
            print("\n📌 测试10: 删除会话")
            delete_success = await chat_service.delete_session(session_id, test_user_id)
            print(f"✅ 会话删除{'成功' if delete_success else '失败'}")

            print("\n🎉 所有测试完成！AI聊天API功能正常")
            break  # 退出数据库会话循环

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """主函数"""
    print("=" * 60)
    print("AI聊天API功能测试")
    print("=" * 60)

    success = await test_chat_api()

    print("=" * 60)
    if success:
        print("✅ 测试结果: 通过")
        exit(0)
    else:
        print("❌ 测试结果: 失败")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())