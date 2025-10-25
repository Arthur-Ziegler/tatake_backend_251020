#!/usr/bin/env python3
"""
调试Chat接口字符串比较错误的测试脚本

根据错误信息 "'>' not supported between instances of 'str' and 'int'"
和代码注释中的线索，问题出现在LangGraph的checkpoint版本号比较中。

这个脚本用于重现和分析这个错误。
"""

import os
import sys
import logging
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

def test_chat_service_error():
    """测试Chat服务错误重现"""
    try:
        # 设置环境变量
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        os.environ.setdefault("CHAT_DB_PATH", "data/test_chat.db")

        # 导入Chat服务
        from src.domains.chat.service import ChatService

        print("🔍 开始测试Chat服务错误重现...")

        # 创建Chat服务实例
        chat_service = ChatService()

        # 尝试发送消息 - 这应该会触发错误
        test_user_id = "test-user-123"
        test_session_id = "test-session-123"
        test_message = "测试消息"

        print(f"📤 发送测试消息: user_id={test_user_id}, session_id={test_session_id}")

        result = chat_service.send_message(
            user_id=test_user_id,
            session_id=test_session_id,
            message=test_message
        )

        print("✅ 消息发送成功:", result)

    except Exception as e:
        print(f"❌ 错误重现: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def test_graph_creation():
    """测试图创建过程"""
    try:
        print("🔍 测试图创建过程...")

        from src.domains.chat.database import create_chat_checkpointer, create_memory_store
        from src.domains.chat.graph import create_chat_graph

        # 创建checkpointer和store
        with create_chat_checkpointer() as checkpointer:
            store = create_memory_store()

            # 创建图 - 这可能触发版本号比较错误
            graph = create_chat_graph(checkpointer, store)
            print("✅ 图创建成功")

    except Exception as e:
        print(f"❌ 图创建失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def analyze_langgraph_checkpoint():
    """分析LangGraph checkpoint中的版本号问题"""
    try:
        print("🔍 分析LangGraph checkpoint版本号问题...")

        from src.domains.chat.database import create_chat_checkpointer
        from langchain_core.messages import HumanMessage
        from uuid import uuid4

        # 创建checkpointer
        with create_chat_checkpointer() as checkpointer:
            # 创建测试配置
            config = {
                "configurable": {
                    "thread_id": f"test-thread-{uuid4()}",
                    "user_id": "test-user"
                }
            }

            # 创建测试checkpoint
            checkpoint = {
                "v": 1,  # 版本号
                "id": str(uuid4()),
                "ts": "2024-01-01T00:00:00.000000+00:00",
                "channel_values": {
                    "messages": [HumanMessage(content="测试消息")]
                },
                "channel_versions": {
                    "__start__": "00000000000000000000000000000002.0.243798848838515",  # 字符串版本号！
                    "messages": 1
                }
            }

            # 尝试保存checkpoint - 这可能触发版本号比较错误
            try:
                checkpointer.put(config, checkpoint, {}, {})
                print("✅ Checkpoint保存成功")
            except Exception as e:
                print(f"❌ Checkpoint保存失败: {type(e).__name__}: {e}")
                print("这很可能就是版本号比较错误的源头！")
                return False

    except Exception as e:
        print(f"❌ Checkpoint分析失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    print("🚀 开始Chat接口错误调试...")
    print("=" * 60)

    # 测试1: 分析checkpoint版本号问题
    print("\n📋 测试1: 分析checkpoint版本号问题")
    analyze_langgraph_checkpoint()

    print("\n" + "-" * 40)

    # 测试2: 测试图创建
    print("\n📋 测试2: 测试图创建")
    test_graph_creation()

    print("\n" + "-" * 40)

    # 测试3: 测试完整的Chat服务
    print("\n📋 测试3: 测试完整的Chat服务")
    test_chat_service_error()

    print("\n" + "=" * 60)
    print("🏁 调试完成")