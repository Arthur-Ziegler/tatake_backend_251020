"""
简单API测试验证

测试基本的测试框架是否能正常工作
"""

import asyncio
import httpx
from httpx import ASGITransport
from src.api.main import app


async def test_basic_coverage():
    """测试基本覆盖率功能"""
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            print("1. 测试认证功能...")
            # 测试游客初始化
            auth_response = await client.post("/auth/guest/init")
            assert auth_response.status_code == 200
            print(f"   ✅ 游客初始化成功")

            # 测试欢迎礼包
            access_token = auth_response.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            gift_response = await client.post("/user/welcome-gift/claim", headers=headers)
            assert gift_response.status_code == 200
            print(f"   ✅ 欢迎礼包领取成功")

            # 测试任务创建
            task_data = {
                "title": "测试任务",
                "description": "基础测试任务"
            }
            task_response = await client.post("/tasks/", json=task_data, headers=headers)
            assert task_response.status_code in [200, 201]  # 接受200或201状态码
            print(f"   ✅ 任务创建成功")

            print("✅ 基本测试覆盖功能正常工作")
            return True

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False


if __name__ == "__main__":
    print("开始运行基础API测试...")
    result = asyncio.run(test_basic_coverage())
    if result:
        print("🎉 所有基础测试通过！")
    else:
        print("💥 测试失败，请检查实现")