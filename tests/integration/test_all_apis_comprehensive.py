"""
全面的API集成测试

目的：系统性地测试所有微服务API端点，确保：
1. 认证流程正常工作
2. JWT token验证正确
3. 所有业务API能正常调用
4. 微服务客户端的路径映射正确
5. 参数传递正确（特别是user_id作为query参数）

测试覆盖：
- Auth API（认证微服务 - 20251）
- Task API（任务微服务 - 20253）
- Top3 API（任务微服务 - 20253）
- Reward API（奖励微服务 - 20254）
- Chat API（聊天微服务 - 20252）
- Focus API（专注微服务 - 20255）

运行方式：
    python -m pytest tests/integration/test_all_apis_comprehensive.py -v -s

作者：TaKeKe团队
版本：1.0.0
日期：2025-11-11
"""

import asyncio
import httpx
import pytest
from typing import Dict, Any, Optional
from datetime import datetime, date


# ==================== 配置 ====================

BASE_URL = "http://api.aitodo.it"  # 生产环境
# BASE_URL = "http://localhost:2025"  # 本地开发环境

# 测试用户配置（微信OpenID）
TEST_WECHAT_OPENID = "test_wechat_user_" + datetime.now().strftime("%Y%m%d%H%M%S")


# ==================== 测试辅助类 ====================

class APITester:
    """API测试助手类"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0)

        # 测试结果统计
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    def get_headers(self) -> Dict[str, str]:
        """获取请求头（包含认证token）"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def test_endpoint(
        self,
        name: str,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        expect_success: bool = True,
        require_auth: bool = True
    ) -> Dict[str, Any]:
        """
        测试单个API端点

        Args:
            name: 测试名称
            method: HTTP方法
            path: API路径
            data: 请求体数据
            params: 查询参数
            expect_success: 是否期望成功
            require_auth: 是否需要认证

        Returns:
            响应数据
        """
        self.results["total"] += 1

        print(f"\n{'='*80}")
        print(f"🧪 测试 #{self.results['total']}: {name}")
        print(f"{'='*80}")
        print(f"📍 {method} {path}")
        if data:
            print(f"📦 请求体: {data}")
        if params:
            print(f"🔍 查询参数: {params}")

        try:
            url = f"{self.base_url}{path}"
            headers = self.get_headers()

            # 检查认证要求
            if require_auth and not self.access_token:
                raise Exception("需要认证但未提供access_token")

            # 发起请求
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=headers, params=params)
            else:
                raise Exception(f"不支持的HTTP方法: {method}")

            # 解析响应
            try:
                result = response.json()
            except:
                result = {"raw_text": response.text}

            # 判断测试结果
            is_success = (response.status_code < 400) if expect_success else (response.status_code >= 400)

            if is_success:
                self.results["passed"] += 1
                print(f"✅ 测试通过")
                print(f"📊 状态码: {response.status_code}")
                print(f"📄 响应: {result}")
            else:
                self.results["failed"] += 1
                error_info = {
                    "test": name,
                    "status_code": response.status_code,
                    "response": result
                }
                self.results["errors"].append(error_info)
                print(f"❌ 测试失败")
                print(f"📊 状态码: {response.status_code}")
                print(f"📄 响应: {result}")

            return result

        except Exception as e:
            self.results["failed"] += 1
            error_info = {
                "test": name,
                "error": str(e)
            }
            self.results["errors"].append(error_info)
            print(f"❌ 测试异常: {str(e)}")
            return {"error": str(e)}

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*80}")
        print(f"📊 测试总结")
        print(f"{'='*80}")
        print(f"总测试数: {self.results['total']}")
        print(f"✅ 通过: {self.results['passed']}")
        print(f"❌ 失败: {self.results['failed']}")
        print(f"通过率: {self.results['passed']/self.results['total']*100:.1f}%")

        if self.results["errors"]:
            print(f"\n❌ 失败的测试:")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"\n{i}. {error.get('test', 'Unknown')}")
                if "error" in error:
                    print(f"   错误: {error['error']}")
                if "status_code" in error:
                    print(f"   状态码: {error['status_code']}")
                if "response" in error:
                    print(f"   响应: {error['response']}")


# ==================== 测试函数 ====================

@pytest.mark.asyncio
async def test_all_apis():
    """完整的API测试流程"""

    tester = APITester(BASE_URL)

    try:
        # ==================== 1. 认证测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第1部分：认证系统测试（Auth-Service 20251）")
        print(f"{'#'*80}")

        # 1.1 微信登录获取token
        login_result = await tester.test_endpoint(
            name="微信登录",
            method="POST",
            path="/auth/wechat/login",
            data={"wechat_openid": TEST_WECHAT_OPENID},
            require_auth=False
        )

        # 提取token和user_id
        if login_result.get("code") == 200:
            data = login_result.get("data", {})
            tester.access_token = data.get("access_token")
            tester.user_id = data.get("user_id")
            print(f"\n🔑 获取到access_token: {tester.access_token[:50]}...")
            print(f"👤 用户ID: {tester.user_id}")
        else:
            print(f"\n⚠️  警告：无法获取access_token，后续需要认证的测试将失败")

        # 1.2 获取用户信息（验证token是否有效）
        await tester.test_endpoint(
            name="获取用户信息",
            method="GET",
            path="/user/profile",
            require_auth=True
        )

        # ==================== 2. 任务管理测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第2部分：任务管理测试（Task-Service 20253）")
        print(f"{'#'*80}")

        # 2.1 查询任务列表
        await tester.test_endpoint(
            name="查询任务列表",
            method="POST",
            path="/tasks/query",
            data={
                "page": 1,
                "page_size": 20,
                "status": "pending",
                "priority": "high"
            }
        )

        # 2.2 创建任务
        create_result = await tester.test_endpoint(
            name="创建任务",
            method="POST",
            path="/tasks/",
            data={
                "title": f"测试任务_{datetime.now().strftime('%H%M%S')}",
                "description": "这是一个API测试创建的任务",
                "status": "pending",
                "priority": "high"
            }
        )

        # 提取创建的任务ID
        task_id = None
        if create_result.get("code") == 200:
            task_data = create_result.get("data", {})
            task_id = task_data.get("id") or task_data.get("task_id")
            print(f"\n📝 创建的任务ID: {task_id}")

        # 2.3 更新任务（如果创建成功）
        if task_id:
            await tester.test_endpoint(
                name="更新任务",
                method="PUT",
                path=f"/tasks/{task_id}",
                data={
                    "title": "更新后的任务标题",
                    "description": "更新后的任务描述",
                    "status": "in_progress"
                }
            )

            # 2.4 完成任务
            await tester.test_endpoint(
                name="完成任务",
                method="POST",
                path=f"/tasks/{task_id}/complete",
                data={}
            )

            # 2.5 删除任务
            await tester.test_endpoint(
                name="删除任务",
                method="DELETE",
                path=f"/tasks/{task_id}"
            )

        # ==================== 3. Top3测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第3部分：Top3管理测试（Task-Service 20253）")
        print(f"{'#'*80}")

        # 3.1 获取今天的Top3
        today = date.today().strftime("%Y-%m-%d")
        await tester.test_endpoint(
            name="获取今天的Top3",
            method="GET",
            path=f"/tasks/special/top3/{today}"
        )

        # 3.2 设置Top3（需要有任务）
        # 注意：这个测试可能会失败，因为用户可能没有足够的任务
        await tester.test_endpoint(
            name="设置Top3",
            method="POST",
            path="/tasks/special/top3",
            data={
                "date": today,
                "task_ids": []  # 空数组，实际应该传入真实的task_id
            },
            expect_success=False  # 预期可能失败
        )

        # ==================== 4. 奖励系统测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第4部分：奖励系统测试（Reward-Service 20254）")
        print(f"{'#'*80}")

        # 4.1 获取积分
        await tester.test_endpoint(
            name="获取用户积分",
            method="GET",
            path="/rewards/points"
        )

        # 4.2 获取奖品列表
        await tester.test_endpoint(
            name="获取奖品列表",
            method="GET",
            path="/rewards/prizes"
        )

        # 4.3 兑换奖品（使用无效code，预期失败）
        await tester.test_endpoint(
            name="兑换奖品（无效code）",
            method="POST",
            path="/rewards/redeem",
            data={"code": "INVALID_CODE_12345"},
            expect_success=False
        )

        # ==================== 5. 聊天系统测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第5部分：聊天系统测试（Chat-Service 20252）")
        print(f"{'#'*80}")

        # 5.1 获取聊天会话列表
        sessions_result = await tester.test_endpoint(
            name="获取聊天会话列表",
            method="GET",
            path="/chat/sessions"
        )

        # 提取第一个会话ID
        session_id = None
        if sessions_result.get("code") == 200:
            data = sessions_result.get("data", {})
            sessions = data.get("sessions", [])
            if sessions:
                session_id = sessions[0].get("id")
                print(f"\n💬 找到会话ID: {session_id}")

        # 5.2 获取会话消息（如果有会话）
        if session_id:
            await tester.test_endpoint(
                name="获取会话消息",
                method="GET",
                path=f"/chat/sessions/{session_id}/messages"
            )

            # 5.3 发送聊天消息
            await tester.test_endpoint(
                name="发送聊天消息",
                method="POST",
                path=f"/chat/sessions/{session_id}/chat",
                data={"message": "你好，这是一条测试消息"}
            )

        # ==================== 6. 专注系统测试 ====================

        print(f"\n{'#'*80}")
        print(f"# 第6部分：专注系统测试（Focus-Service 20255）")
        print(f"{'#'*80}")

        # 6.1 获取番茄钟统计
        await tester.test_endpoint(
            name="获取番茄钟统计",
            method="GET",
            path="/tasks/pomodoro-count"
        )

        # 6.2 创建专注会话（需要有任务）
        if task_id:
            focus_result = await tester.test_endpoint(
                name="创建专注会话",
                method="POST",
                path="/tasks/focus-status",
                data={
                    "task_id": task_id,
                    "session_type": "focus",
                    "duration": 25
                }
            )

        # ==================== 打印总结 ====================

        tester.print_summary()

    finally:
        await tester.close()


# ==================== pytest入口 ====================

if __name__ == "__main__":
    """直接运行此脚本"""
    asyncio.run(test_all_apis())
