#!/usr/bin/env python3
"""
调试数据库内容

查看数据库中的实际记录，诊断为什么list_sessions只返回一个会话。
"""

import sqlite3
import json
from src.domains.chat.database import get_chat_database_path

def debug_database():
    """调试数据库内容"""
    print("=== 数据库内容调试 ===")

    db_path = get_chat_database_path()
    print(f"数据库路径: {db_path}")

    import os
    if not os.path.exists(db_path):
        print("数据库文件不存在!")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 检查表结构
        print("\n1. 检查表是否存在...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库中的表: {[table['name'] for table in tables]}")

        # 检查checkpoints表
        if any('checkpoint' in table['name'] for table in tables):
            print("\n2. 检查checkpoints表结构...")
            cursor.execute("PRAGMA table_info(checkpoints)")
            columns = cursor.fetchall()
            print(f"checkpoints表列: {[col['name'] for col in columns]}")

            # 查看所有记录
            print("\n3. 查看所有checkpoint记录...")
            cursor.execute("SELECT * FROM checkpoints ORDER BY thread_id, checkpoint_id")
            records = cursor.fetchall()
            print(f"总记录数: {len(records)}")

            for i, record in enumerate(records):
                print(f"\n记录 {i+1}:")
                print(f"  thread_id: {record['thread_id']}")
                print(f"  checkpoint_id: {record['checkpoint_id']}")
                print(f"  metadata: {record['metadata'][:100]}..." if record['metadata'] and len(record['metadata']) > 100 else f"  metadata: {record['metadata']}")

                # 解析checkpoint数据
                if record['checkpoint']:
                    try:
                        checkpoint_data = json.loads(record['checkpoint'])
                        channel_values = checkpoint_data.get('channel_values', {})
                        print(f"  user_id: {channel_values.get('user_id')}")
                        print(f"  session_id: {channel_values.get('session_id')}")
                        print(f"  session_title: {channel_values.get('session_title')}")
                        print(f"  messages数量: {len(channel_values.get('messages', []))}")
                    except json.JSONDecodeError as e:
                        print(f"  checkpoint数据解析失败: {e}")

            # 测试list_sessions的查询
            print("\n4. 测试list_sessions查询...")
            query = """
            SELECT
                thread_id,
                checkpoint_id,
                checkpoint,
                metadata
            FROM checkpoints
            WHERE (thread_id, checkpoint_id) IN (
                SELECT
                    thread_id,
                    MAX(checkpoint_id) as checkpoint_id
                FROM checkpoints
                GROUP BY thread_id
            )
            ORDER BY thread_id DESC
            LIMIT ?
            """

            cursor.execute(query, (20,))
            results = cursor.fetchall()
            print(f"list_sessions查询结果数: {len(results)}")

            for i, result in enumerate(results):
                metadata = json.loads(result['metadata']) if result['metadata'] else {}
                print(f"  结果 {i+1}: thread_id={result['thread_id'][:8]}..., title={metadata.get('title', 'N/A')}")

        else:
            print("checkpoints表不存在!")

        conn.close()

    except Exception as e:
        print(f"数据库操作失败: {e}")

    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_database()