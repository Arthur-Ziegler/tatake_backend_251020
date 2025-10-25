#!/usr/bin/env python3
"""
修复channel_versions类型问题的完整解决方案

通过确保所有checkpoint操作都使用整数版本号来解决类型不匹配问题。
"""

import sys
import os
sys.path.append('.')

def create_type_safe_checkpointer():
    """创建类型安全的checkpointer包装器"""

    class TypeSafeCheckpointer:
        """类型安全的checkpointer包装器"""

        def __init__(self, base_checkpointer):
            self.base_checkpointer = base_checkpointer

        def put(self, config, checkpoint, metadata, new_versions):
            """确保checkpoint中的channel_versions都是整数类型"""
            if isinstance(checkpoint, dict) and "channel_versions" in checkpoint:
                channel_versions = checkpoint["channel_versions"]
                if isinstance(channel_versions, dict):
                    # 确保所有版本号都是整数
                    for key, value in channel_versions.items():
                        if isinstance(value, str):
                            # 尝试将字符串转换为整数
                            try:
                                channel_versions[key] = int(value)
                                print(f"🔧 修复类型: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                            except ValueError:
                                # 如果无法转换，设置为默认值1
                                channel_versions[key] = 1
                                print(f"🔧 重置类型: {key} 无法转换，设置为默认值 1")
                        elif not isinstance(value, int):
                            # 其他类型，设置为整数
                            channel_versions[key] = int(value)
                            print(f"🔧 强制转换: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")

            return self.base_checkpointer.put(config, checkpoint, metadata, new_versions)

        def get(self, config):
            """确保检索到的checkpoint中的channel_versions都是整数类型"""
            result = self.base_checkpointer.get(config)

            if result and isinstance(result, dict) and "channel_versions" in result:
                channel_versions = result["channel_versions"]
                if isinstance(channel_versions, dict):
                    # 确保所有版本号都是整数
                    for key, value in channel_versions.items():
                        if isinstance(value, str):
                            try:
                                channel_versions[key] = int(value)
                                print(f"🔧 检索时修复类型: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")
                            except ValueError:
                                channel_versions[key] = 1
                                print(f"🔧 检索时重置类型: {key} 无法转换，设置为默认值 1")
                        elif not isinstance(value, int):
                            channel_versions[key] = int(value)
                            print(f"🔧 检索时强制转换: {key} 从 {value} ({type(value)}) 转换为 {channel_versions[key]} (int)")

            return result

        def __getattr__(self, name):
            """代理其他方法到基础checkpointer"""
            return getattr(self.base_checkpointer, name)

        def __enter__(self):
            self.base_checkpointer.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self.base_checkpointer.__exit__(exc_type, exc_val, exc_tb)

    return TypeSafeCheckpointer

def test_type_safe_fix():
    """测试类型安全修复"""
    print("🧪 测试类型安全修复...")

    from src.domains.chat.database import create_chat_checkpointer, create_memory_store
    from src.domains.chat.graph import create_chat_graph
    from src.domains.chat.models import create_chat_state
    from langchain_core.messages import HumanMessage

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 创建类型安全的checkpointer包装器
    TypeSafeCheckpointer = create_type_safe_checkpointer()

    # 测试手动创建有问题的checkpoint
    print("1️⃣ 测试手动修复问题checkpoint...")
    with create_chat_checkpointer() as base_checkpointer:
        checkpointer = TypeSafeCheckpointer(base_checkpointer)
        config = {"configurable": {"thread_id": "fix-test", "checkpoint_ns": ""}}

        # 创建有问题的checkpoint（字符串版本号）
        problematic_checkpoint = {
            "v": 1,
            "ts": 0,
            "id": "problematic-checkpoint",
            "channel_values": {"messages": []},
            "channel_versions": {"messages": "1"},  # 故意使用字符串
            "versions_seen": {},
            "pending_sends": []
        }

        checkpointer.put(config, problematic_checkpoint, {}, {})

        # 检查是否被修复
        retrieved = checkpointer.get(config)
        if retrieved and isinstance(retrieved, dict):
            if "channel_versions" in retrieved:
                cv = retrieved["channel_versions"]
                print(f"修复后的channel_versions: {cv}")
                for k, v in cv.items():
                    print(f"  {k}: {v} (类型: {type(v)})")

    # 测试完整的图调用
    print("2️⃣ 测试完整的图调用...")
    try:
        with create_chat_checkpointer() as base_checkpointer:
            checkpointer = TypeSafeCheckpointer(base_checkpointer)
            store = create_memory_store()
            graph = create_chat_graph(checkpointer, store)

            session_id = "safe-test"
            config = {"configurable": {"thread_id": session_id, "checkpoint_ns": ""}}

            state = create_chat_state('test-user', session_id, '安全测试')
            state['messages'] = [HumanMessage(content='安全测试消息')]

            result = graph.graph.invoke(state, config)
            print("✅ 类型安全修复成功")

    except Exception as e:
        print(f"❌ 类型安全修复失败: {e}")

def integrate_with_chat_service():
    """集成到ChatService中"""
    print(f"\n🔧 集成到ChatService...")

    # 修改ChatService以使用类型安全的checkpointer
    from src.domains.chat.service import ChatService

    # 删除数据库文件
    db_path = 'data/chat.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    # 创建ChatService实例
    service = ChatService()

    # 创建类型安全的checkpointer包装器
    TypeSafeCheckpointer = create_type_safe_checkpointer()

    # 修复_with_checkpointer方法
    original_with_checkpointer = service._with_checkpointer

    def safe_with_checkpointer(func):
        """类型安全的_with_checkpointer"""
        with service.db_manager.create_checkpointer() as base_checkpointer:
            checkpointer = TypeSafeCheckpointer(base_checkpointer)
            return func(checkpointer)

    # 临时替换方法
    service._with_checkpointer = safe_with_checkpointer

    try:
        # 创建会话
        session_result = service.create_session('test-user', '安全集成测试')
        session_id = session_result['session_id']
        print(f"会话创建成功: {session_id}")

        # 发送消息
        result = service.send_message('test-user', session_id, '安全集成测试消息')
        print("✅ ChatService集成成功")
        print(f"AI回复: {result.get('ai_response', '无回复')[:100]}...")

    except Exception as e:
        print(f"❌ ChatService集成失败: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 修复channel_versions类型问题的完整解决方案")
    print("=" * 60)

    test_type_safe_fix()
    integrate_with_chat_service()

    print("\n" + "=" * 60)
    print("🎯 修复方案总结:")
    print("1. 创建类型安全的checkpointer包装器")
    print("2. 自动修复所有checkpoint中的类型问题")
    print("3. 集成到ChatService中确保类型一致性")
    print("4. 提供防御性的类型转换机制")
    print("=" * 60)