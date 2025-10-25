#!/usr/bin/env python3
"""
检查数据库中的checkpoint数据，查找类型不一致问题
"""

import sqlite3
import msgpack
from pathlib import Path

def check_checkpoint_data():
    """检查checkpoint数据中的类型问题"""
    db_path = Path("./data/chat.db")

    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return

    print("🔍 检查数据库中的checkpoint数据...")
    print("=" * 50)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取所有checkpoint记录
        cursor.execute("""
            SELECT thread_id, checkpoint_id, checkpoint, metadata
            FROM checkpoints
            ORDER BY rowid DESC
        """)

        records = cursor.fetchall()

        for i, (thread_id, checkpoint_id, checkpoint_blob, metadata_blob) in enumerate(records, 1):
            print(f"\n📋 Checkpoint #{i}")
            print(f"Thread ID: {thread_id}")
            print(f"Checkpoint ID: {checkpoint_id}")

            # 如果有问题的checkpoint，只显示前10个
            if i > 10:
                print("  ... (显示前10个checkpoint)")
                break

            # 解析checkpoint数据
            if checkpoint_blob:
                try:
                    checkpoint_data = msgpack.unpackb(checkpoint_blob, raw=False)

                    if 'channel_versions' in checkpoint_data:
                        print("🔧 Channel Versions:")
                        channel_versions = checkpoint_data['channel_versions']

                        for key, value in channel_versions.items():
                            value_type = type(value).__name__
                            print(f"  {key}: {value} ({value_type})")

                            # 检查是否有类型问题
                            if isinstance(value, str) and any(char.isdigit() for char in value):
                                print(f"    ⚠️  发现字符串类型的版本号: {value}")

                            # 检查LangGraph特有的UUID格式
                            if isinstance(value, str) and '.' in value and len(value) > 20:
                                print(f"    🚨 发现LangGraph UUID格式: {value}")

                    else:
                        print("  ℹ️  没有channel_versions字段")

                except Exception as e:
                    print(f"  ❌ 解析checkpoint数据失败: {e}")

            print("-" * 40)

    finally:
        conn.close()

    print("\n✅ 检查完成")

if __name__ == "__main__":
    check_checkpoint_data()