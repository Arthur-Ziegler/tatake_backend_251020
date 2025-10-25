#!/usr/bin/env python3
"""
深度调试：为什么第一次成功，第二次失败

专门分析LangGraph checkpoint机制导致的类型错误
"""

import uuid
import logging
import traceback
from contextlib import contextmanager

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_checkpoint_flow():
    """调试checkpoint流程"""
    print("🔍 深度调试：checkpoint流程分析")
    print("=" * 60)

    try:
        from src.domains.chat.service import ChatService

        # 创建ChatService实例
        chat_service = ChatService()

        # 生成测试UUID
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        print(f"📋 测试参数:")
        print(f"  user_id: {user_id}")
        print(f"  session_id: {session_id}")
        print()

        # 第一次调用
        print("🎯 第一次调用（预期成功）:")
        try:
            result1 = chat_service.send_message(user_id, session_id, "第一次测试消息")
            print("✅ 第一次调用成功")
        except Exception as e:
            print(f"❌ 第一次调用失败: {e}")
            return False

        # 第二次调用
        print("\n🎯 第二次调用（预期失败）:")
        try:
            result2 = chat_service.send_message(user_id, session_id, "第二次测试消息")
            print("✅ 第二次调用成功 - 意味着修复有效！")
            return True
        except Exception as e:
            error_str = str(e)
            print(f"❌ 第二次调用失败: {e}")
            print(f"   错误类型: {type(e)}")

            if "'>' not supported between instances of 'str' and 'int'" in error_str:
                print("🚨 确认是LangGraph类型错误！")
                print("📝 分析原因:")
                print("   - 第一次调用成功，说明ChatState简化有效")
                print("   - 第二次调用失败，说明checkpoint机制产生了问题")
                print("   - 可能原因：checkpoint存储的数据格式问题")
                print("   - 可能原因：版本号在序列化/反序列化过程中损坏")
                return False
            else:
                print("📝 其他类型错误")
                return False

    except Exception as e:
        print(f"❌ 调试测试失败: {e}")
        traceback.print_exc()
        return False

def debug_database_content():
    """调试数据库内容"""
    print("\n🔍 调试：分析checkpoint数据库内容")
    print("=" * 60)

    try:
        import sqlite3
        from src.domains.chat.database import get_chat_database_path

        db_path = get_chat_database_path()
        print(f"📁 数据库路径: {db_path}")

        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 数据库表: {[t[0] for t in tables]}")

        # 查看checkpoints表内容
        if 'checkpoints' in [t[0] for t in tables]:
            cursor.execute("SELECT * FROM checkpoints LIMIT 5;")
            checkpoints = cursor.fetchall()
            print(f"📋 Checkpoint记录数: {len(checkpoints)}")

            # 获取列名
            cursor.execute("PRAGMA table_info(checkpoints);")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"📋 列名: {column_names}")

            # 显示第一条记录的详细信息
            if checkpoints:
                print("\n📋 第一条checkpoint记录:")
                for i, value in enumerate(checkpoints[0]):
                    if i < len(column_names):
                        col_name = column_names[i]
                        print(f"   {col_name}: {value} (类型: {type(value)})")

                        # 如果是版本号相关的列，详细分析
                        if 'version' in col_name.lower() and isinstance(value, str):
                            print(f"      🔍 版本号分析: {value}")
                            if '.' in value:
                                parts = value.split('.')
                                print(f"      🔍 分割结果: {parts}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库调试失败: {e}")
        traceback.print_exc()
        return False

def test_clean_start():
    """测试完全干净的启动"""
    print("\n🔍 测试：完全干净的启动")
    print("=" * 60)

    try:
        import os
        import sqlite3
        from src.domains.chat.database import get_chat_database_path

        # 备份数据库
        db_path = get_chat_database_path()
        backup_path = db_path + ".backup"
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"📁 数据库已备份到: {backup_path}")

        # 删除数据库，强制干净启动
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  已删除旧数据库: {db_path}")

        # 现在测试ChatService
        from src.domains.chat.service import ChatService

        chat_service = ChatService()

        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # 测试多次调用
        for i in range(3):
            try:
                message = f"干净启动测试消息 {i+1}"
                result = chat_service.send_message(user_id, session_id, message)
                print(f"✅ 消息 {i+1} 发送成功")
            except Exception as e:
                error_str = str(e)
                print(f"❌ 消息 {i+1} 发送失败: {e}")

                if "'>' not supported between instances of 'str' and 'int'" in error_str:
                    print(f"🚨 在干净启动情况下仍然出现LangGraph类型错误！")
                    print("📝 这说明问题不在checkpoint数据，而在LangGraph内部处理")
                    return False

        print("✅ 干净启动测试全部通过")
        return True

    except Exception as e:
        print(f"❌ 干净启动测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主调试函数"""
    print("🚀 深度调试：LangGraph checkpoint类型错误")
    print("=" * 60)
    print("分析为什么第一次成功，第二次失败...")
    print()

    # 执行调试测试
    print("1. 基础checkpoint流程分析")
    checkpoint_test = debug_checkpoint_flow()

    print("\n2. 数据库内容分析")
    db_test = debug_database_content()

    print("\n3. 干净启动测试")
    clean_test = test_clean_start()

    print("\n" + "=" * 60)
    print("🎯 调试结果总结")
    print("=" * 60)
    print(f"checkpoint流程分析: {'✅ 完成' if checkpoint_test else '❌ 失败'}")
    print(f"数据库内容分析: {'✅ 完成' if db_test else '❌ 失败'}")
    print(f"干净启动测试: {'✅ 通过' if clean_test else '❌ 失败'}")

    if clean_test:
        print("\n💡 结论:")
        print("   干净启动测试通过，说明问题在于checkpoint数据的序列化/反序列化")
        print("   需要进一步优化TypeSafeCheckperator的类型修复逻辑")
    else:
        print("\n💡 结论:")
        print("   即使在干净启动情况下也出现错误，说明问题更深层")
        print("   需要重新审视LangGraph的使用方式")

    print("\n🎯 调试完成！")

if __name__ == "__main__":
    main()