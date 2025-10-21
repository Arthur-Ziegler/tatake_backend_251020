#!/usr/bin/env python3
"""
调试聊天工具调用流程
"""

import os
import sys
import uuid
import logging
from dotenv import load_dotenv

# 设置路径
sys.path.append('src')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from domains.chat.database import create_chat_checkpointer, create_memory_store
from domains.chat.graph import create_chat_graph
from domains.chat.models import ChatState

def test_graph_workflow():
    """测试完整的图工作流程"""
    print("🚀 开始测试聊天图工作流程...")

    # 创建检查点和存储（使用与实际相同的配置）
    checkpointer = create_chat_checkpointer()
    store = create_memory_store()

    # 创建图
    graph = create_chat_graph(checkpointer, store)

    # 模拟用户和会话
    user_id = "test-user-123"
    session_id = str(uuid.uuid4())

    # 创建配置
    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id
        }
    }

    # 创建初始状态
    initial_state = {
        "user_id": user_id,
        "session_id": session_id,
        "session_title": "测试会话",
        "messages": [HumanMessage(content="快使用芝麻开门工具")]
    }

    print(f"👤 用户ID: {user_id}")
    print(f"🆔 会话ID: {session_id}")
    print(f"💬 消息: 快使用芝麻开门工具")

    try:
        # 运行图
        result = graph.invoke(initial_state, config)

        print("\n✅ 图执行成功!")
        print(f"📝 最终状态消息数量: {len(result.get('messages', []))}")

        # 分析消息
        messages = result.get('messages', [])
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            content = msg.content if hasattr(msg, 'content') else str(msg)
            tool_calls = getattr(msg, 'tool_calls', None)

            print(f"\n📨 消息 {i+1}:")
            print(f"   类型: {msg_type}")
            print(f"   内容: {content[:100]}..." if len(content) > 100 else f"   内容: {content}")
            if tool_calls:
                print(f"   工具调用: {tool_calls}")

        return True

    except Exception as e:
        print(f"\n❌ 图执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_tool_call():
    """测试简单的工具调用"""
    print("\n🔧 测试简单工具调用...")

    from domains.chat.tools.password_opener import sesame_opener
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    model = ChatOpenAI(
        model='gpt-3.5-turbo',
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL'),
        temperature=0.7
    )

    model_with_tools = model.bind_tools([sesame_opener])

    messages = [HumanMessage(content="请使用芝麻开门工具")]
    response = model_with_tools.invoke(messages)

    print(f"🤖 AI响应: {response.content}")
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"✅ 工具调用: {response.tool_calls}")

        # 执行工具
        for tool_call in response.tool_calls:
            result = sesame_opener.invoke(tool_call['args'])
            print(f"🔧 工具结果: {result}")
    else:
        print("❌ 无工具调用")

if __name__ == "__main__":
    print("=" * 60)
    print("聊天工具调用调试")
    print("=" * 60)

    # 测试简单工具调用
    test_simple_tool_call()

    # 测试完整图工作流
    success = test_graph_workflow()

    print("\n" + "=" * 60)
    if success:
        print("✅ 测试完成")
    else:
        print("❌ 测试失败")
    print("=" * 60)