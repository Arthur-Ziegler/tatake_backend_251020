"""
真实API环境测试

这个脚本会启动实际的API服务器并测试，
而不是使用内存数据库。

运行方式：
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001

然后在另一个终端运行：
uv run python test_live_api.py

这将验证我们的实现在真实环境中的工作情况。
"""

import asyncio
import httpx
from src.api.main import app


async def test_live_api():
    """测试真实API环境"""
    print("🚀 开始真实API环境测试...")
    print("请先启动API服务器：")
    print("uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001")
    print("然后在另一个终端运行：")
    print("uv run python test_live_api.py")

    # 等待用户确认
    # input("按Enter键继续...")  # 注释掉，自动运行

    try:
        # 连接到运行中的API服务器
        async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
            # 测试游客初始化
            print("测试游客初始化...")
            response = await client.post("/auth/guest/init")
            print(f"响应状态：{response.status_code}")
            print(f"响应内容：{response.text[:200]}...")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 游客初始化成功！用户ID：{data.get('data', {}).get('user_id', 'unknown')}")
                access_token = data.get('data', {}).get('access_token', 'unknown')

                # 测试欢迎礼包
                print("测试欢迎礼包...")
                headers = {"Authorization": f"Bearer {access_token}"}
                gift_response = await client.post("/user/welcome-gift/claim", headers=headers)
                print(f"礼包响应状态：{gift_response.status_code}")
                print(f"礼包响应内容：{gift_response.text[:300]}...")

                if gift_response.status_code == 200:
                    print("🎉 欢迎礼包功能在真实环境中正常工作！")
                    return True
                else:
                    print("❌ 欢迎礼包功能失败")
                    return False
            else:
                print("❌ 游客初始化失败")
                return False

    except Exception as e:
        print(f"❌ API测试失败：{e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_live_api())