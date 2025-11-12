#!/usr/bin/env python3
"""
简化的API测试脚本（使用Python标准库）

目的：快速测试所有API端点，无需额外依赖

运行方式：
    python3 tests/integration/test_apis_simple.py

作者：TaKeKe团队
版本：1.0.0
日期：2025-11-11
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from datetime import datetime, date


# ==================== 配置 ====================

BASE_URL = "http://api.aitodo.it"
TEST_WECHAT_OPENID = "test_user_" + datetime.now().strftime("%Y%m%d%H%M%S")


# ==================== API测试类 ====================

class SimpleAPITester:
    """简单的API测试器"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test_api(
        self,
        name: str,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = True
    ) -> Dict[str, Any]:
        """测试单个API"""
        print(f"\n{'='*80}")
        print(f"🧪 测试: {name}")
        print(f"{'='*80}")
        print(f"📍 {method} {path}")

        try:
            # 构建URL
            url = self.base_url + path
            if params:
                param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
                url += f"?{param_str}"

            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if require_auth and self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            # 准备请求体
            body = None
            if data:
                body = json.dumps(data).encode('utf-8')
                print(f"📦 请求体: {data}")

            # 发起请求
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method=method
            )

            # 执行请求
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ 测试通过 (状态码: {response.status})")
                print(f"📄 响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
                self.passed += 1
                return result

        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode('utf-8'))
            except:
                error_body = {"error": str(e)}

            print(f"❌ 测试失败 (状态码: {e.code})")
            print(f"📄 响应: {json.dumps(error_body, indent=2, ensure_ascii=False)}")
            self.failed += 1
            self.errors.append({
                "test": name,
                "status": e.code,
                "error": error_body
            })
            return error_body

        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            self.failed += 1
            self.errors.append({
                "test": name,
                "error": str(e)
            })
            return {"error": str(e)}

    def print_summary(self):
        """打印测试总结"""
        total = self.passed + self.failed
        print(f"\n{'='*80}")
        print(f"📊 测试总结")
        print(f"{'='*80}")
        print(f"总测试数: {total}")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        if total > 0:
            print(f"通过率: {self.passed/total*100:.1f}%")

        if self.errors:
            print(f"\n❌ 失败详情:")
            for i, error in enumerate(self.errors, 1):
                print(f"\n{i}. {error['test']}")
                if 'status' in error:
                    print(f"   状态码: {error['status']}")
                if 'error' in error:
                    err = error['error']
                    if isinstance(err, dict):
                        print(f"   错误: {json.dumps(err, ensure_ascii=False)}")
                    else:
                        print(f"   错误: {err}")


# ==================== 测试主流程 ====================

def main():
    """主测试流程"""
    tester = SimpleAPITester(BASE_URL)

    print(f"\n🚀 开始API测试")
    print(f"📍 基础URL: {BASE_URL}")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ==================== 1. 认证测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第1部分：认证系统测试")
    print(f"{'#'*80}")

    # 1.1 微信登录
    login_result = tester.test_api(
        name="微信登录",
        method="POST",
        path="/auth/wechat/login",
        data={"wechat_openid": TEST_WECHAT_OPENID},
        require_auth=False
    )

    # 提取token
    if login_result.get("code") == 200:
        data = login_result.get("data", {})
        tester.access_token = data.get("access_token")
        tester.user_id = data.get("user_id")
        print(f"\n🔑 Token: {tester.access_token[:50] if tester.access_token else 'None'}...")
        print(f"👤 User ID: {tester.user_id}")
    else:
        print(f"\n⚠️  警告：无法获取token，后续测试将失败")

    # 1.2 获取用户信息
    tester.test_api(
        name="获取用户信息",
        method="GET",
        path="/user/profile"
    )

    # ==================== 2. 任务管理测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第2部分：任务管理测试")
    print(f"{'#'*80}")

    # 2.1 查询任务列表
    tester.test_api(
        name="查询任务列表",
        method="POST",
        path="/tasks/query",
        data={"page": 1, "page_size": 20}
    )

    # 2.2 创建任务
    create_result = tester.test_api(
        name="创建任务",
        method="POST",
        path="/tasks/",
        data={
            "title": f"测试任务_{datetime.now().strftime('%H%M%S')}",
            "description": "API测试任务",
            "status": "pending",
            "priority": "high"
        }
    )

    # 提取任务ID
    task_id = None
    if create_result.get("code") == 200:
        task_data = create_result.get("data", {})
        task_id = task_data.get("id") or task_data.get("task_id")
        if task_id:
            print(f"\n📝 任务ID: {task_id}")

            # 2.3 更新任务
            tester.test_api(
                name="更新任务",
                method="PUT",
                path=f"/tasks/{task_id}",
                data={"title": "更新后的标题", "status": "in_progress"}
            )

            # 2.4 完成任务
            tester.test_api(
                name="完成任务",
                method="POST",
                path=f"/tasks/{task_id}/complete",
                data={}
            )

            # 2.5 删除任务
            tester.test_api(
                name="删除任务",
                method="DELETE",
                path=f"/tasks/{task_id}"
            )

    # ==================== 3. Top3测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第3部分：Top3管理测试")
    print(f"{'#'*80}")

    today = date.today().strftime("%Y-%m-%d")

    # 3.1 获取Top3
    tester.test_api(
        name="获取今天的Top3",
        method="GET",
        path=f"/tasks/special/top3/{today}"
    )

    # 3.2 设置Top3
    tester.test_api(
        name="设置Top3",
        method="POST",
        path="/tasks/special/top3",
        data={"date": today, "task_ids": []}
    )

    # ==================== 4. 奖励系统测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第4部分：奖励系统测试")
    print(f"{'#'*80}")

    # 4.1 获取积分
    tester.test_api(
        name="获取用户积分",
        method="GET",
        path="/rewards/points"
    )

    # 4.2 获取奖品列表
    tester.test_api(
        name="获取奖品列表",
        method="GET",
        path="/rewards/prizes"
    )

    # ==================== 5. 聊天系统测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第5部分：聊天系统测试")
    print(f"{'#'*80}")

    # 5.1 获取聊天会话列表
    sessions_result = tester.test_api(
        name="获取聊天会话列表",
        method="GET",
        path="/chat/sessions"
    )

    # 提取会话ID
    session_id = None
    if sessions_result.get("code") == 200:
        data = sessions_result.get("data")
        # data可能直接是list，也可能是dict
        if isinstance(data, list):
            sessions = data
        elif isinstance(data, dict):
            sessions = data.get("sessions", [])
        else:
            sessions = []

        if sessions:
            session_id = sessions[0].get("id")
            print(f"\n💬 会话ID: {session_id}")

            # 5.2 获取会话消息
            tester.test_api(
                name="获取会话消息",
                method="GET",
                path=f"/chat/sessions/{session_id}/messages"
            )

    # ==================== 6. 专注系统测试 ====================

    print(f"\n{'#'*80}")
    print(f"# 第6部分：专注系统测试")
    print(f"{'#'*80}")

    # 6.1 获取番茄钟统计
    tester.test_api(
        name="获取番茄钟统计",
        method="GET",
        path="/tasks/pomodoro-count"
    )

    # ==================== 打印总结 ====================

    tester.print_summary()


if __name__ == "__main__":
    main()
