#!/usr/bin/env python3
"""
专门测试用户报告的Chat接口错误的脚本

用户报告的具体错误：
- 接口: /chat/sessions/{session_id}/send
- 错误: "'>' not supported between instances of 'str' and 'int'"
- 位置: src/domains/chat/service.py:send_message

这个脚本专门模拟API调用，尝试重现这个特定错误。
"""

import os
import sys
import logging
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_simulation():
    """模拟API调用重现错误"""
    try:
        print("🔍 模拟API调用重现Chat接口错误...")

        # 设置环境变量
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        os.environ.setdefault("CHAT_DB_PATH", "data/test_chat_api.db")

        # 直接导入并使用API路由逻辑
        from src.domains.chat.router import send_chat_message
        from src.domains.chat.schemas import ChatMessageRequest

        print("✅ 成功导入API路由模块")

        # 模拟API请求参数
        test_session_id = "test-session-api"
        test_request = ChatMessageRequest(message="测试API调用消息")

        print(f"📤 模拟API请求: session_id={test_session_id}, message={test_request.message}")

        # 这里需要模拟依赖注入的参数
        # user_id, session_id, request, session
        # 但直接调用会很复杂，所以我们用另一种方法

    except Exception as e:
        print(f"❌ API模拟失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_direct_service_stress():
    """直接压力测试Chat服务，尝试触发边界情况"""
    try:
        print("🔍 直接压力测试Chat服务...")

        from src.domains.chat.service import ChatService
        import uuid

        # 设置环境变量
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        os.environ.setdefault("CHAT_DB_PATH", "data/test_chat_stress.db")

        chat_service = ChatService()

        # 测试多种场景
        test_scenarios = [
            ("正常消息", "你好"),
            ("空消息", ""),
            ("长消息", "这是一个很长的消息" * 100),
            ("特殊字符", "!@#$%^&*()_+-=[]{}|;':\",./<>?"),
            ("Unicode", "测试中文🚀 emoji 🔧"),
        ]

        for i, (scenario_name, message) in enumerate(test_scenarios):
            try:
                print(f"📋 测试场景 {i+1}: {scenario_name}")

                test_user_id = f"stress-test-user-{i}"
                test_session_id = f"stress-test-session-{uuid.uuid4()}"

                result = chat_service.send_message(
                    user_id=test_user_id,
                    session_id=test_session_id,
                    message=message
                )

                print(f"✅ 场景 {i+1} 成功: {result.get('status', 'unknown')}")

            except Exception as e:
                print(f"❌ 场景 {i+1} 失败: {type(e).__name__}: {e}")
                if "'>' not supported between instances of 'str' and 'int'" in str(e):
                    print("🎯 重现了用户报告的错误！")
                    traceback.print_exc()
                    return True  # 找到了错误

        print("所有压力测试场景都通过了，未发现错误")
        return False

    except Exception as e:
        print(f"❌ 压力测试设置失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_concurrent_sessions():
    """测试并发会话，可能触发版本号冲突"""
    try:
        print("🔍 测试并发会话场景...")

        from src.domains.chat.service import ChatService
        import threading
        import time

        # 设置环境变量
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        os.environ.setdefault("CHAT_DB_PATH", "data/test_chat_concurrent.db")

        chat_service = ChatService()
        errors = []

        def worker_thread(thread_id):
            try:
                test_user_id = f"concurrent-user-{thread_id}"
                test_session_id = f"concurrent-session-{thread_id}"

                for i in range(3):
                    result = chat_service.send_message(
                        user_id=test_user_id,
                        session_id=test_session_id,
                        message=f"线程 {thread_id} 消息 {i+1}"
                    )
                    time.sleep(0.1)  # 短暂延迟

            except Exception as e:
                errors.append(f"线程 {thread_id}: {type(e).__name__}: {e}")
                if "'>' not supported between instances of 'str' and 'int'" in str(e):
                    errors.append(f"🎯 线程 {thread_id} 重现了用户报告的错误!")

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        if errors:
            print("并发测试发现错误:")
            for error in errors:
                print(f"  {error}")
            return True
        else:
            print("并发测试通过，未发现错误")
            return False

    except Exception as e:
        print(f"❌ 并发测试设置失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

def test_database_corruption():
    """测试数据库损坏情况，可能产生不一致的数据类型"""
    try:
        print("🔍 测试数据库不一致情况...")

        from src.domains.chat.database import create_chat_checkpointer
        from langchain_core.messages import HumanMessage
        import uuid

        # 尝试手动创建不一致的checkpoint数据
        with create_chat_checkpointer() as checkpointer:
            config = {
                "configurable": {
                    "thread_id": f"corruption-test-{uuid.uuid4()}",
                    "user_id": "test-user"
                }
            }

            # 创建包含不一致类型的checkpoint
            corrupted_checkpoint = {
                "v": 1,
                "id": str(uuid.uuid4()),
                "ts": "2024-01-01T00:00:00.000000+00:00",
                "channel_values": {
                    "messages": [HumanMessage(content="测试消息")]
                },
                # 故意创建不一致的channel_versions
                "channel_versions": {
                    "__start__": "00000000000000000000000000000002.0.243798848838515",  # 字符串
                    "messages": 1,  # 整数
                    "another_channel": "2.5",  # 浮点数字符串
                    "bad_channel": "not-a-number"  # 无法转换的字符串
                },
                "versions_seen": {},
                "pending_sends": []
            }

            # 尝试保存这个不一致的checkpoint
            try:
                checkpointer.put(config, corrupted_checkpoint, {}, {})
                print("✅ 成功保存不一致的checkpoint（应该被修复）")

                # 尝试读取，看是否触发错误
                retrieved = checkpointer.get(config)
                print("✅ 成功读取checkpoint，修复机制工作正常")

            except Exception as e:
                print(f"❌ Checkpoint操作失败: {type(e).__name__}: {e}")
                if "'>' not supported between instances of 'str' and 'int'" in str(e):
                    print("🎯 重现了用户报告的错误!")
                    traceback.print_exc()
                    return True

        return False

    except Exception as e:
        print(f"❌ 数据库损坏测试失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始专门测试Chat接口错误...")
    print("=" * 60)

    found_error = False

    # 测试1: 直接压力测试
    print("\n📋 测试1: 直接压力测试Chat服务")
    if test_direct_service_stress():
        found_error = True

    print("\n" + "-" * 40)

    # 测试2: 并发会话测试
    print("\n📋 测试2: 并发会话测试")
    if test_concurrent_sessions():
        found_error = True

    print("\n" + "-" * 40)

    # 测试3: 数据库不一致测试
    print("\n📋 测试3: 数据库不一致测试")
    if test_database_corruption():
        found_error = True

    print("\n" + "=" * 60)
    if found_error:
        print("🎯 成功重现了用户报告的错误!")
    else:
        print("❌ 未能重现用户报告的错误，可能需要更特定的条件")
    print("🏁 测试完成")