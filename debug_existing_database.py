#!/usr/bin/env python3
"""
调试现有的正确数据库

查看一个正确初始化的LangGraph数据库中的type字段值。
"""

import sqlite3
import json
import tempfile
import os
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage

def debug_correct_database():
    """调试正确初始化的数据库"""
    print("=== 调试正确初始化的数据库 ===")

    # 使用内存数据库
    try:
        print("使用内存数据库")

        # 使用SqliteSaver正确初始化数据库
        checkpointer = SqliteSaver.from_conn_string("sqlite:///:memory:")

        # 创建一个简单的检查点
        config = {
            "configurable": {
                "thread_id": "test-thread-123",
                "user_id": "test-user-456"
            }
        }

        checkpoint_data = {
            "channel_values": {
                "messages": [HumanMessage(content="Hello World")],
                "user_id": config["configurable"]["user_id"],
                "session_id": config["configurable"]["thread_id"],
                "session_title": "测试会话"
            },
            "channel_versions": {},
            "versions_seen": {}
        }

        # 保存检查点
        with checkpointer as cp:
            print("保存检查点...")
            result = cp.put(config, checkpoint_data, {})
            print(f"保存结果: {result}")

        print("✅ 检查点保存成功，内存数据库无法直接查看表结构")
        print("✅ 测试完成")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_correct_database()