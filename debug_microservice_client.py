#!/usr/bin/env python3
"""
调试微服务客户端路径映射问题
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.enhanced_task_microservice_client import get_enhanced_task_microservice_client

async def debug_path_mapping():
    """调试路径映射问题"""
    print("🔍 开始调试微服务客户端路径映射...")

    client = get_enhanced_task_microservice_client()

    # 测试参数
    method = "POST"
    path = "tasks/query"
    user_id = "33bae3f6-72f3-4662-b97a-86c59af11af3"
    data = {"page": 1, "page_size": 20}

    print(f"📋 测试参数:")
    print(f"   method: {method}")
    print(f"   path: {path}")
    print(f"   user_id: {user_id}")
    print(f"   data: {data}")
    print(f"   base_url: {client.base_url}")

    try:
        print(f"\n🚀 开始调用微服务...")
        result = await client.call_microservice(
            method=method,
            path=path,
            user_id=user_id,
            data=data
        )
        print(f"✅ 调用成功: {result}")
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_path_mapping())