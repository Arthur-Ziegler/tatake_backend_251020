#!/usr/bin/env python3
"""
快速微服务端点测试脚本

验证所有9个核心任务微服务端点的可用性
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_OPENID = "test_user_quick_test"

async def test_wechat_login(session):
    """测试微信登录获取token"""
    print("🔐 测试微信登录...")

    async with session.post(
        f"{BASE_URL}/auth/wechat/login",
        json={"wechat_openid": TEST_USER_OPENID}
    ) as response:
        data = await response.json()
        if data.get("code") == 200:
            token = data["data"]["access_token"]
            user_id = data["data"]["user_id"]
            print(f"✅ 登录成功，用户ID: {user_id}")
            return token, user_id
        else:
            print(f"❌ 登录失败: {data}")
            return None, None

async def test_endpoint(session, method, path, data=None, params=None, token=None, description=""):
    """测试单个端点"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{BASE_URL}{path}"

    try:
        async with session.request(method, url, json=data, params=params, headers=headers) as response:
            resp_data = await response.json()
            success = response.status == 200 and resp_data.get("code") == 200

            if success:
                print(f"✅ {description} - 成功")
                if resp_data.get("data"):
                    print(f"   数据: {json.dumps(resp_data['data'], ensure_ascii=False, indent=2)[:200]}...")
            else:
                print(f"❌ {description} - 失败 (状态码: {response.status})")
                print(f"   响应: {json.dumps(resp_data, ensure_ascii=False, indent=2)}")

            return success

    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始快速微服务端点测试")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 1. 登录获取token
        token, user_id = await test_wechat_login(session)
        if not token:
            print("❌ 无法获取token，测试终止")
            return

        print(f"\n📋 使用用户ID进行测试: {user_id}")
        print("=" * 60)

        # 2. 测试所有任务端点
        test_cases = [
            # 任务管理
            ("POST", "/tasks/", {"title": "测试任务", "description": "快速测试"}, None, "创建任务"),
            ("GET", "/tasks/", None, None, "获取任务列表"),

            # Top3管理
            ("POST", "/tasks/special/top3", {"date": "2025-11-01", "task_ids": []}, None, "设置Top3"),
            ("GET", "/tasks/special/top3/2025-11-01", None, None, "获取Top3"),

            # 专注状态
            ("POST", "/tasks/focus-status", {"focus_status": "start"}, None, "发送专注状态"),

            # 番茄钟计数
            ("GET", "/tasks/pomodoro-count", None, None, "获取番茄钟计数"),
        ]

        success_count = 0
        total_count = len(test_cases)

        for method, path, data, params, description in test_cases:
            if await test_endpoint(session, method, path, data, params, token, description):
                success_count += 1

        # 3. 测试需要任务ID的端点
        print("\n🔍 测试任务相关端点（需要先创建任务）...")

        # 创建一个专门用于测试的任务
        create_resp = await session.post(
            f"{BASE_URL}/tasks/",
            json={"title": "专用测试任务", "description": "用于完成/更新/删除测试"},
            headers={"Authorization": f"Bearer {token}"}
        )
        create_data = await create_resp.json()

        if create_data.get("code") == 200 and create_data.get("data"):
            task_id = create_data["data"].get("id") or create_data["data"].get("task_id")
            if task_id:
                print(f"✅ 创建测试任务成功，ID: {task_id}")

                # 测试更新任务
                if await test_endpoint(session, "PUT", f"/tasks/{task_id}",
                                     {"title": "更新的任务标题"}, None, token, "更新任务"):
                    success_count += 1
                else:
                    total_count += 1

                # 测试完成任务
                if await test_endpoint(session, "POST", f"/tasks/{task_id}/complete",
                                     {}, None, token, "完成任务"):
                    success_count += 1
                else:
                    total_count += 1

                # 测试删除任务
                if await test_endpoint(session, "DELETE", f"/tasks/{task_id}",
                                     None, None, token, "删除任务"):
                    success_count += 1
                else:
                    total_count += 1
            else:
                print("❌ 无法从创建响应中获取任务ID")
                total_count += 3  # 预外的3个测试
        else:
            print("❌ 创建测试任务失败")
            total_count += 3  # 额外的3个测试

        # 4. 总结
        print("\n" + "=" * 60)
        print(f"📊 测试完成！")
        print(f"✅ 成功: {success_count}/{total_count}")
        print(f"❌ 失败: {total_count - success_count}/{total_count}")
        print(f"📈 成功率: {(success_count/total_count)*100:.1f}%")

        if success_count == total_count:
            print("🎉 所有微服务端点测试通过！")
        else:
            print("⚠️ 部分端点测试失败，请检查日志")

if __name__ == "__main__":
    asyncio.run(main())