#!/usr/bin/env python3
"""
简单的认证测试脚本
"""

import asyncio
import httpx
from httpx import ASGITransport
from src.api.main import app


async def test_auth():
    """测试认证功能"""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. 尝试创建用户
            print("1. 创建用户...")
            auth_response = await client.post("/auth/guest-init")
            print(f"Auth response status: {auth_response.status_code}")
            print(f"Auth response text: {auth_response.text}")

            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                print(f"用户创建成功: {auth_data}")
            else:
                print(f"用户创建失败: {auth_response.status_code}")

        except Exception as e:
            print(f"测试过程中出现错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_auth())