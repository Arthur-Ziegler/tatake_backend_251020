#!/usr/bin/env python3
"""
TaKeKe API 系统测试
基于docs/文档标准的完整测试
"""
import httpx
import time
from datetime import datetime, date

# 测试配置
BASE_URL = "http://localhost:8001"
PROXY = "http://127.0.0.1:7897"

# 测试计数
total_tests = 0
passed_tests = 0
failed_tests = 0

def log_test(name: str, success: bool, status_code: int, expected: int = None, error: str = None):
    """记录测试结果"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1

    if success:
        passed_tests += 1
        print(f"✅ {name} (HTTP {status_code})")
    else:
        failed_tests += 1
        expected_str = f"期望: {expected}, " if expected else ""
        error_str = f" - {error}" if error else ""
        print(f"❌ {name} ({expected_str}实际: {status_code}){error_str}")


def test_health():
    """测试健康检查"""
    print("\n=== 系统接口测试 ===")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5)
        log_test("GET /health", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /health", False, 0, 200, str(e))


def test_auth():
    """测试认证系统"""
    print("\n=== 认证系统测试 ===")

    # 1. 微信登录（自动注册）
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/wechat/login",
            json={"wechat_openid": f"test_{int(time.time())}"},
            timeout=10
        )
        log_test("POST /auth/wechat/login", response.status_code == 200, response.status_code)

        # 保存token供后续测试使用
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("access_token")
    except Exception as e:
        log_test("POST /auth/wechat/login", False, 0, 200, str(e))

    return None


def test_user(token: str = None):
    """测试用户管理"""
    print("\n=== 用户管理测试 ===")

    if not token:
        print("⚠️  跳过用户测试（无token）")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. 获取用户信息
    try:
        response = httpx.get(f"{BASE_URL}/user/profile", headers=headers, timeout=5)
        log_test("GET /user/profile", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /user/profile", False, 0, 200, str(e))


def test_tasks(token: str = None):
    """测试任务管理"""
    print("\n=== 任务管理测试 ===")

    if not token:
        print("⚠️  跳过任务测试（无token）")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    task_id = None

    # 1. 创建任务
    try:
        response = httpx.post(
            f"{BASE_URL}/tasks/",
            headers=headers,
            json={
                "title": f"系统测试任务_{datetime.now().strftime('%H%M%S')}",
                "description": "系统测试",
                "priority": "medium",
                "due_date": date.today().isoformat()  # date格式
            },
            timeout=10
        )
        log_test("POST /tasks/", response.status_code == 200, response.status_code)

        if response.status_code == 200:
            data = response.json()
            data_obj = data.get("data")
            if data_obj and isinstance(data_obj, dict):
                task_id = data_obj.get("id")
    except Exception as e:
        log_test("POST /tasks/", False, 0, 200, str(e))

    # 2. GET获取任务列表（新增）
    try:
        response = httpx.get(
            f"{BASE_URL}/tasks/",
            headers=headers,
            params={"page": 1, "page_size": 20},
            timeout=10
        )
        log_test("GET /tasks/", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /tasks/", False, 0, 200, str(e))

    # 3. POST查询任务列表
    try:
        response = httpx.post(
            f"{BASE_URL}/tasks/query",
            headers=headers,
            json={"page": 1, "page_size": 20},
            timeout=10
        )
        log_test("POST /tasks/query", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("POST /tasks/query", False, 0, 200, str(e))

    # 4. 更新任务（如果创建成功）
    if task_id:
        try:
            response = httpx.put(
                f"{BASE_URL}/tasks/{task_id}",
                headers=headers,
                json={"title": "更新后的任务标题"},
                timeout=10
            )
            log_test(f"PUT /tasks/{task_id}", response.status_code == 200, response.status_code)
        except Exception as e:
            log_test(f"PUT /tasks/{task_id}", False, 0, 200, str(e))

        # 5. 完成任务
        try:
            response = httpx.post(
                f"{BASE_URL}/tasks/{task_id}/complete",
                headers=headers,
                json={},
                timeout=10
            )
            log_test(f"POST /tasks/{task_id}/complete", response.status_code == 200, response.status_code)
        except Exception as e:
            log_test(f"POST /tasks/{task_id}/complete", False, 0, 200, str(e))

        # 6. 删除任务
        try:
            response = httpx.delete(
                f"{BASE_URL}/tasks/{task_id}",
                headers=headers,
                timeout=10
            )
            log_test(f"DELETE /tasks/{task_id}", response.status_code == 200, response.status_code)
        except Exception as e:
            log_test(f"DELETE /tasks/{task_id}", False, 0, 200, str(e))

    return task_id


def test_top3(token: str = None):
    """测试Top3管理"""
    print("\n=== Top3管理测试 ===")

    if not token:
        print("⚠️  跳过Top3测试（无token）")
        return

    headers = {"Authorization": f"Bearer {token}"}
    today = date.today().isoformat()

    # 1. 查询Top3
    try:
        response = httpx.get(
            f"{BASE_URL}/tasks/special/top3/{today}",
            headers=headers,
            timeout=10
        )
        log_test(f"GET /tasks/special/top3/{today}", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test(f"GET /tasks/special/top3/{today}", False, 0, 200, str(e))


def test_rewards(token: str = None):
    """测试奖励系统"""
    print("\n=== 奖励系统测试 ===")

    if not token:
        print("⚠️  跳过奖励测试（无token）")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. 查看奖品
    try:
        response = httpx.get(f"{BASE_URL}/rewards/prizes", headers=headers, timeout=10)
        log_test("GET /rewards/prizes", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /rewards/prizes", False, 0, 200, str(e))

    # 2. 查看积分
    try:
        response = httpx.get(f"{BASE_URL}/rewards/points", headers=headers, timeout=10)
        log_test("GET /rewards/points", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /rewards/points", False, 0, 200, str(e))


def test_chat(token: str = None):
    """测试聊天系统"""
    print("\n=== 聊天系统测试 ===")

    if not token:
        print("⚠️  跳过聊天测试（无token）")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. 查询会话列表
    try:
        response = httpx.get(f"{BASE_URL}/chat/sessions", headers=headers, timeout=10)
        log_test("GET /chat/sessions", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /chat/sessions", False, 0, 200, str(e))


def test_focus(token: str = None):
    """测试专注系统"""
    print("\n=== 专注系统测试 ===")

    if not token:
        print("⚠️  跳过专注测试（无token）")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. 记录专注状态
    try:
        response = httpx.post(
            f"{BASE_URL}/tasks/focus-status",
            headers=headers,
            json={
                "focus_status": "focused",
                "duration_minutes": 25
            },
            timeout=10
        )
        log_test("POST /tasks/focus-status", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("POST /tasks/focus-status", False, 0, 200, str(e))

    # 2. 获取番茄钟计数
    try:
        response = httpx.get(
            f"{BASE_URL}/tasks/pomodoro-count",
            headers=headers,
            params={"date_filter": "today"},
            timeout=10
        )
        log_test("GET /tasks/pomodoro-count", response.status_code == 200, response.status_code)
    except Exception as e:
        log_test("GET /tasks/pomodoro-count", False, 0, 200, str(e))


def main():
    """主测试流程"""
    print("=" * 60)
    print("TaKeKe API 系统测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标服务: {BASE_URL}")
    print("=" * 60)

    # 1. 健康检查
    test_health()

    # 2. 认证测试（获取token）
    token = test_auth()

    # 3. 用户管理
    test_user(token)

    # 4. 任务管理
    test_tasks(token)

    # 5. Top3管理
    test_top3(token)

    # 6. 奖励系统
    test_rewards(token)

    # 7. 聊天系统
    test_chat(token)

    # 8. 专注系统
    test_focus(token)

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)" if total_tests > 0 else "通过: 0")
    print(f"失败: {failed_tests}")

    # 生成报告文件
    report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"TaKeKe API 测试报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H时%M分%S秒')}\n")
        f.write(f"API服务器: {BASE_URL}\n")
        f.write("=" * 60 + "\n")
        f.write(f"总测试数: {total_tests}\n")
        f.write(f"通过: {passed_tests}\n")
        f.write(f"失败: {failed_tests}\n")

    print(f"\n✅ 测试报告已生成: {report_file}")

    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    exit(main())
