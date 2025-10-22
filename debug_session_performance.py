#!/usr/bin/env python3
"""
诊断会话管理性能问题

测试会话创建和查询的性能，不涉及AI服务调用。
"""

import uuid
import time
import os
from src.domains.chat.service import ChatService
from src.domains.chat.database import get_chat_database_path

def diagnose_session_performance():
    """诊断会话性能问题"""
    print("=== 会话管理性能诊断 ===")

    # 清理数据库
    db_path = get_chat_database_path()
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已清理数据库: {db_path}")

    chat_service = ChatService()
    user_id = str(uuid.uuid4())

    # 测试少量会话创建
    print("\n1. 测试10个会话创建...")
    session_count = 10
    start_time = time.time()
    session_ids = []

    for i in range(session_count):
        try:
            result = chat_service.create_session(
                user_id=user_id,
                title=f"诊断测试会话 {i+1}"
            )
            session_ids.append(result["session_id"])
            print(f"   会话 {i+1} 创建成功: {result['session_id'][:8]}...")
        except Exception as e:
            print(f"   会话 {i+1} 创建失败: {e}")

    creation_time = time.time() - start_time
    print(f"创建{len(session_ids)}个会话耗时: {creation_time:.2f}秒")

    # 测试列表查询
    print("\n2. 测试会话列表查询...")
    start_time = time.time()

    try:
        result = chat_service.list_sessions(user_id=user_id)
        query_time = time.time() - start_time

        print(f"查询耗时: {query_time:.2f}秒")
        print(f"返回会话数: {len(result.get('sessions', []))}")
        print(f"总会话数: {result.get('total_count', 0)}")

        # 显示前几个会话
        for i, session in enumerate(result.get('sessions', [])[:3]):
            print(f"   会话{i+1}: {session['title']} ({session['session_id'][:8]}...)")

    except Exception as e:
        print(f"查询失败: {e}")
        query_time = time.time() - start_time
        print(f"查询耗时: {query_time:.2f}秒")

    # 测试数据库文件大小
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path)
        print(f"\n3. 数据库文件大小: {file_size} 字节")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    diagnose_session_performance()