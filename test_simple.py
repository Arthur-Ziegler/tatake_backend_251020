#!/usr/bin/env python3
"""
简单的测试脚本，用于验证欢迎礼包功能
"""

import asyncio
import httpx
from httpx import ASGITransport
from src.api.main import app


async def test_welcome_gift():
    """测试欢迎礼包功能"""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            # 1. 创建用户
            print("1. 创建用户...")
            auth_response = await client.post("/auth/guest/init")
            print(f"Auth response: {auth_response.status_code}")

            if auth_response.status_code != 200:
                print(f"用户创建失败: {auth_response.text}")
                return

            auth_data = auth_response.json()
            access_token = auth_data["data"]["access_token"]
            print(f"用户创建成功，token: {access_token[:20]}...")

            # 2. 尝试领取欢迎礼包
            print("\n2. 领取欢迎礼包...")
            headers = {"Authorization": f"Bearer {access_token}"}
            gift_response = await client.post("/user/welcome-gift/claim", headers=headers)
            print(f"Gift response status: {gift_response.status_code}")

            if gift_response.status_code == 200:
                gift_data = gift_response.json()
                print(f"礼包领取成功: {gift_data}")
            else:
                print(f"礼包领取失败: {gift_response.text}")

        except Exception as e:
            print(f"测试过程中出现错误: {e}")


if __name__ == "__main__":
    asyncio.run(test_welcome_gift())