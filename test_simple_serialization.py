#!/usr/bin/env python3
"""
简单的LangGraph序列化测试

测试基本的SqliteSaver功能，隔离序列化问题。
"""

import uuid
import os
import tempfile
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

def test_basic_sqlite_saver():
    """测试基本的SqliteSaver功能"""
    print("=== 基本SqliteSaver测试 ===")

    # 使用项目目录下的数据库文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "data", "test_chat.db")

    try:
        print(f"数据库路径: {db_path}")

        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 如果数据库文件存在，先删除
        if os.path.exists(db_path):
            os.remove(db_path)

        # 创建检查点器
        checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")

        # 测试基本配置
        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4())
            }
        }

        # 创建一个简单的检查点
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

            # 读取检查点
            print("读取检查点...")
            saved_checkpoint = cp.get_tuple(config)
            if saved_checkpoint:
                print(f"检查点ID: {saved_checkpoint.checkpoint['id']}")
                print(f"检查点数据: {type(saved_checkpoint.checkpoint)}")
                print("✅ 检查点读取成功")
            else:
                print("❌ 检查点读取失败")

        print("✅ 基本SqliteSaver测试通过")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"已清理测试文件: {db_path}")

if __name__ == "__main__":
    test_basic_sqlite_saver()