"""
API场景测试工具函数

提供场景测试中常用的辅助函数，包括断言工具、数据创建和清理函数等。

作者：TaTakeKe团队
版本：1.0.0
"""

import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from uuid import uuid4, UUID
import time
import httpx


def assert_api_success(response: httpx.Response, message: str = "API调用失败"):
    """
    断言API响应成功

    Args:
        response: HTTP响应对象
        message: 失败时的错误消息
    """
    # 允许200或201状态码
    assert response.status_code in [200, 201], f"{message}: HTTP {response.status_code}"

    try:
        data = response.json()
    except json.JSONDecodeError:
        assert False, f"{message}: 响应不是有效的JSON格式"

    assert data.get("code") in [200, 201], f"{message}: API响应码 {data.get('code')}"
    assert "data" in data, f"{message}: 响应缺少data字段"


def assert_api_error(response: httpx.Response, expected_status: int, message: str = "API应该返回错误"):
    """
    断言API响应错误

    Args:
        response: HTTP响应对象
        expected_status: 期望的HTTP状态码
        message: 失败时的错误消息
    """
    assert response.status_code == expected_status, f"{message}: 期望HTTP {expected_status}, 实际 {response.status_code}"


def assert_contains_fields(data: Dict[str, Any], required_fields: List[str], message: str = "数据缺少必需字段"):
    """
    断言数据包含指定的所有字段

    Args:
        data: 要检查的数据字典
        required_fields: 必需字段列表
        message: 失败时的错误消息
    """
    for field in required_fields:
        assert field in data, f"{message}: 缺少字段 '{field}'"


def assert_points_change(before: int, after: int, expected_change: int, message: str = "积分变化不符合预期"):
    """
    断言积分变化符合预期

    Args:
        before: 变化前积分
        after: 变化后积分
        expected_change: 期望的变化值
        message: 失败时的错误消息
    """
    actual_change = after - before
    assert actual_change == expected_change, f"{message}: 期望变化 {expected_change}, 实际变化 {actual_change}"


def create_sample_task(title: str = None, description: str = None, priority: str = "medium") -> Dict[str, Any]:
    """
    创建示例任务数据

    Args:
        title: 任务标题
        description: 任务描述
        priority: 任务优先级

    Returns:
        任务数据字典
    """
    timestamp = int(time.time())
    return {
        "title": title or f"测试任务_{timestamp}",
        "description": description or f"这是一个测试任务，创建于 {timestamp}",
        "priority": priority,
        "status": "pending",
        "tags": ["测试", "场景"],
        "parent_id": None,
        "due_date": None,
        "planned_start_time": None,
        "planned_end_time": None
    }


def create_sample_top3(title: str = None, reward_points: int = 50) -> Dict[str, Any]:
    """
    创建示例Top3数据

    Args:
        title: Top3标题
        reward_points: 奖励积分

    Returns:
        Top3数据字典
    """
    timestamp = int(time.time())
    return {
        "title": title or f"今日Top3_{timestamp}",
        "description": f"今日最重要的三件事，创建于 {timestamp}",
        "reward_points": reward_points,
        "tasks": []
    }


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1, message: str = "等待条件满足超时"):
    """
    等待条件满足

    Args:
        condition_func: 条件函数，返回True表示条件满足
        timeout: 超时时间（秒）
        interval: 检查间隔（秒）
        message: 超时时的错误消息
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return
        time.sleep(interval)

    assert False, f"{message}: 超时 {timeout} 秒"


def get_user_points(client: httpx.Client, user_id: str = None) -> int:
    """
    获取用户当前积分

    Args:
        client: 认证的HTTP客户端
        user_id: 用户ID（如果为None则使用dummy值）

    Returns:
        用户积分数量
    """
    # 从认证头中提取token，解码获取用户ID
    if user_id is None:
        # 如果没有提供user_id，使用一个默认值
        user_id_param = "dummy"
    else:
        user_id_param = user_id

    response = client.get(f"/points/my-points?user_id={user_id_param}")
    assert_api_success(response, "获取用户积分失败")

    data = response.json()
    return data["data"].get("current_balance", 0)


def get_user_points_balance(client: httpx.Client, user_id: str = None) -> int:
    """
    获取用户积分余额（简化版本）

    Args:
        client: 认证的HTTP客户端
        user_id: 用户ID（可选，如果不提供则从JWT token解码）

    Returns:
        用户积分余额
    """
    import base64
    import json

    # 如果没有提供用户ID，从JWT token中解码获取
    if user_id is None:
        auth_header = client.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # 去掉 "Bearer " 前缀
            try:
                # 解码JWT token的payload部分
                parts = token.split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    # 添加padding如果需要
                    padding = '=' * (4 - len(payload) % 4)
                    payload += padding
                    decoded = base64.urlsafe_b64decode(payload)
                    payload_data = json.loads(decoded.decode())
                    user_id = payload_data.get("sub", "dummy")
                else:
                    user_id = "dummy"
            except Exception as e:
                print(f"解码JWT token失败: {e}")
                user_id = "dummy"
        else:
            user_id = "dummy"

    response = client.get(f"/points/my-points?user_id={user_id}")
    assert_api_success(response, "获取用户积分余额失败")

    data = response.json()
    return data["data"]["current_balance"]


def get_user_rewards(client: httpx.Client) -> List[Dict[str, Any]]:
    """
    获取用户奖励列表

    Args:
        client: 认证的HTTP客户端

    Returns:
        奖励列表
    """
    response = client.get("/rewards/my-rewards?user_id=dummy")
    assert_api_success(response, "获取用户奖励失败")

    data = response.json()
    return data["data"].get("items", [])


def create_task_with_validation(client: httpx.Client, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建任务并进行验证

    Args:
        client: 认证的HTTP客户端
        task_data: 任务数据

    Returns:
        创建的任务数据
    """
    response = client.post("/tasks/", json=task_data)
    assert_api_success(response, f"创建任务失败: {task_data['title']}")

    result = response.json()
    task = result["data"]

    # 验证必需字段
    assert_contains_fields(task, ["id", "title", "status", "created_at"], "创建的任务数据不完整")
    assert task["title"] == task_data["title"], "任务标题不匹配"

    return task


def complete_task_with_validation(client: httpx.Client, task_id: str) -> Dict[str, Any]:
    """
    完成任务并进行验证

    Args:
        client: 认证的HTTP客户端
        task_id: 任务ID

    Returns:
        完成后的任务数据
    """
    # CompleteTaskRequest是一个空对象，所以传递空的JSON请求体
    response = client.post(f"/tasks/{task_id}/complete", json={})
    assert_api_success(response, f"完成任务失败: {task_id}")

    result = response.json()

    # 检查响应结构是否符合预期
    assert "data" in result, f"响应缺少data字段: {result}"
    assert "completion_result" in result["data"], f"响应缺少completion_result字段: {result}"

    # 验证任务状态更新
    assert result["data"]["task"]["status"] == "completed", f"任务状态应为completed，实际为 {result['data']['task']['status']}"

    # 验证积分发放（普通任务和Top3任务都应该获得2积分）
    assert result["data"]["completion_result"]["points_awarded"] == 2, f"任务应获得2积分，实际获得: {result['data']['completion_result']['points_awarded']}"
    # 奖励类型可能是task_complete（普通任务）或task_complete_top3（Top3任务）
    reward_type = result["data"]["completion_result"]["reward_type"]
    assert reward_type in ["task_complete", "task_complete_top3"], f"奖励类型应为task_complete或task_complete_top3: {reward_type}"

    # 普通任务不应该触发抽奖
    assert result["data"].get("lottery_result") is None, f"普通任务不应触发抽奖: {result['data'].get('lottery_result')}"

    return result


def complete_top3_task_with_validation(client: httpx.Client, task_id: str) -> Dict[str, Any]:
    """
    完成Top3任务并进行验证

    Args:
        client: 认证的HTTP客户端
        task_id: 任务ID

    Returns:
        完成后的任务数据
    """
    # CompleteTaskRequest是一个空对象，所以传递空的JSON请求体
    response = client.post(f"/tasks/{task_id}/complete", json={})

    # 添加调试信息
    print(f"完成任务响应状态码: {response.status_code}")
    print(f"完成任务响应内容: {response.text}")

    assert_api_success(response, f"完成Top3任务失败: {task_id}")

    result = response.json()

    # 检查响应结构是否符合预期
    assert "data" in result, f"响应缺少data字段: {result}"
    assert "completion_result" in result["data"], f"响应缺少completion_result字段: {result}"

    # 验证任务状态更新
    assert result["data"]["task"]["status"] == "completed", f"任务状态应为completed，实际为 {result['data']['task']['status']}"

    # 验证积分发放（Top3任务应该获得2积分基础奖励）
    assert result["data"]["completion_result"]["points_awarded"] == 2, f"Top3任务应获得2积分，实际获得: {result['data']['completion_result']['points_awarded']}"
    assert result["data"]["completion_result"]["reward_type"] == "task_complete_top3", f"Top3任务奖励类型应为task_complete_top3: {result['data']['completion_result']['reward_type']}"

    # Top3任务应该触发抽奖
    lottery_result = result["data"].get("lottery_result")
    assert lottery_result is not None, f"Top3任务应触发抽奖: {result['data']}"

    return result


def setup_top3_task(client: httpx.Client, task_id: str) -> None:
    """
    直接在数据库中设置任务为Top3（用于测试）

    Args:
        client: 认证的HTTP客户端
        task_id: 任务ID
    """
    import base64
    import json
    from src.database import get_db_session
    from src.domains.top3.models import TaskTop3
    from datetime import date
    from uuid import uuid4
    from sqlalchemy import text
    import logging

    logger = logging.getLogger(__name__)

    # 从JWT token中获取用户ID
    auth_header = client.headers.get("Authorization", "")
    user_id = "dummy"
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            parts = token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                padding = '=' * (4 - len(payload) % 4)
                payload += padding
                decoded = base64.urlsafe_b64decode(payload)
                payload_data = json.loads(decoded.decode())
                user_id = payload_data.get("sub", "dummy")
        except Exception:
            pass

    # 直接在数据库中创建Top3记录
    session = next(get_db_session())
    try:
        # 检查是否已有今日Top3记录
        today = date.today()
        existing_top3 = session.execute(
            text("SELECT id FROM task_top3 WHERE user_id = :user_id AND top_date = :today"),
            {"user_id": user_id, "today": today.isoformat()}
        ).scalar_one_or_none()

        if existing_top3:
            # 更新现有记录，添加任务ID
            current_task_ids = session.execute(
                text("SELECT task_ids FROM task_top3 WHERE id = :id"),
                {"id": existing_top3}
            ).scalar_one()
            task_ids = eval(current_task_ids) if current_task_ids else []
            if task_id not in task_ids:
                task_ids.append(task_id)
                session.execute(
                    text("UPDATE task_top3 SET task_ids = :task_ids WHERE id = :id"),
                    {"task_ids": str(task_ids), "id": existing_top3}
                )
        else:
            # 创建新的Top3记录
            top3_record = TaskTop3(
                id=str(uuid4()),
                user_id=user_id,
                top_date=today,
                task_ids=[task_id],
                points_consumed=0  # 测试时不消耗积分
            )
            session.add(top3_record)

        session.commit()
        session.flush()
        logger.info(f"成功设置任务 {task_id} 为Top3任务")

    except Exception as e:
        session.rollback()
        logger.error(f"设置Top3任务失败: {e}")
        raise
    finally:
        session.close()


def create_top3_with_validation(client: httpx.Client, top3_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建Top3并进行验证

    Args:
        client: 认证的HTTP客户端
        top3_data: Top3数据

    Returns:
        创建的Top3数据
    """
    response = client.post("/tasks/special/top3", json=top3_data)
    assert_api_success(response, f"创建Top3失败: {top3_data['title']}")

    result = response.json()
    top3 = result["data"]

    # 验证必需字段
    assert_contains_fields(top3, ["id", "title", "status", "created_at"], "创建的Top3数据不完整")
    assert top3["title"] == top3_data["title"], "Top3标题不匹配"

    return top3


def start_focus_session_with_validation(client: httpx.Client, duration: int = 25) -> Dict[str, Any]:
    """
    开始Focus会话并进行验证

    Args:
        client: 认证的HTTP客户端
        duration: 专注时长（分钟）

    Returns:
        创建的Focus会话数据
    """
    focus_data = {
        "duration_minutes": duration,
        "task_type": "work"
    }

    response = client.post("/focus/sessions", json=focus_data)
    assert_api_success(response, "开始Focus会话失败")

    result = response.json()
    session = result["data"]

    # 验证必需字段
    assert_contains_fields(session, ["id", "status", "duration_minutes", "started_at"], "创建的Focus会话数据不完整")
    assert session["status"] == "active", f"Focus会话状态应为active，实际为 {session['status']}"

    return session


def print_test_header(test_name: str):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"🧪 场景测试: {test_name}")
    print(f"{'='*60}")


def print_test_step(step: str):
    """打印测试步骤"""
    print(f"📝 {step}")


def print_test_success(message: str):
    """打印测试成功信息"""
    print(f"✅ {message}")


def print_test_error(message: str):
    """打印测试错误信息"""
    print(f"❌ {message}")


def create_test_client() -> httpx.Client:
    """
    创建测试用的HTTP客户端

    Returns:
        httpx.Client: 配置好的HTTP客户端
    """
    # 设置基础URL和超时
    base_url = "http://localhost:8001"
    timeout = httpx.Timeout(30.0)

    return httpx.Client(
        base_url=base_url,
        timeout=timeout,
        headers={"Content-Type": "application/json"}
    )


def create_authenticated_user() -> Dict[str, Any]:
    """
    创建完整的认证用户（注册+登录）

    Returns:
        dict: 包含用户信息和认证令牌的字典
    """
    client = create_test_client()

    # 1. 游客账号初始化
    guest_response = client.post("/auth/guest/init", json={})
    if not _is_api_success(guest_response):
        raise RuntimeError("游客账号初始化失败")

    # 2. 微信注册
    wechat_openid = f"test_openid_{uuid4().hex[:8]}"

    register_response = client.post("/auth/register", json={
        "wechat_openid": wechat_openid
    })
    if not _is_api_success(register_response):
        raise RuntimeError("微信注册失败")

    register_data = register_response.json()["data"]

    # 3. 微信登录
    login_response = client.post("/auth/login", json={
        "wechat_openid": wechat_openid
    })
    if not _is_api_success(login_response):
        raise RuntimeError("微信登录失败")

    login_data = login_response.json()["data"]

    return {
        "user_id": register_data["user_id"],
        "openid": wechat_openid,
        "access_token": login_data["access_token"],
        "refresh_token": login_data["refresh_token"]
    }


def assert_reward_earned(reward_data: Dict[str, Any], expected_type: str, min_amount: int = 1, message: str = "奖励验证失败"):
    """
    断言奖励信息符合预期

    Args:
        reward_data: 奖励数据
        expected_type: 期望的奖励类型
        min_amount: 最小奖励数量
        message: 失败时的错误消息
    """
    assert "type" in reward_data, f"{message}: 缺少奖励类型"
    assert reward_data["type"] == expected_type, f"{message}: 期望奖励类型 {expected_type}, 实际 {reward_data['type']}"

    assert "amount" in reward_data, f"{message}: 缺少奖励数量"
    assert reward_data["amount"] >= min_amount, f"{message}: 奖励数量太少: {reward_data['amount']} < {min_amount}"

    if "transaction_id" in reward_data:
        assert reward_data["transaction_id"], f"{message}: 交易ID不能为空"


def cleanup_user_data(client: httpx.Client, user_id: str, task_ids: List[str] = None) -> bool:
    """
    清理用户测试数据

    Args:
        client: HTTP客户端
        user_id: 用户ID
        task_ids: 要清理的任务ID列表

    Returns:
        bool: 清理是否成功
    """
    cleanup_success = True

    # 清理任务
    if task_ids:
        for task_id in task_ids:
            try:
                # 尝试软删除任务（如果API支持）
                response = client.delete(f"/tasks/{task_id}")
                if response.status_code not in [200, 204, 404]:
                    print(f"⚠️ 任务删除失败: {task_id}, 状态码: {response.status_code}")
                    cleanup_success = False
            except Exception as e:
                print(f"⚠️ 清理任务时发生异常: {e}")
                cleanup_success = False

    return cleanup_success


def _is_api_success(response: httpx.Response) -> bool:
    """
    检查API响应是否成功

    Args:
        response: HTTP响应

    Returns:
        bool: 是否成功
    """
    if response.status_code not in [200, 201]:
        return False

    try:
        data = response.json()
        return data.get("code") in [200, 201]
    except (json.JSONDecodeError, KeyError):
        return False


def get_user_transactions(client: httpx.Client, source_type: str = None) -> List[Dict[str, Any]]:
    """
    获取用户积分流水记录

    Args:
        client: HTTP客户端
        source_type: 流水类型过滤

    Returns:
        List[Dict]: 流水记录列表
    """
    url = "/points/transactions?page=1&page_size=20"
    if source_type:
        url += f"&source_type={source_type}"

    response = client.get(url)

    # 直接检查状态码，因为积分流水API返回直接的JSON对象
    assert response.status_code == 200, f"获取积分流水失败: HTTP {response.status_code}"

    data = response.json()
    return data.get("transactions", [])


def validate_user_session(client: httpx.Client) -> bool:
    """
    验证用户会话是否有效

    Args:
        client: HTTP客户端

    Returns:
        bool: 会话是否有效
    """
    # 尝试访问用户资源
    response = client.get("/points/my-points")

    if response.status_code == 200:
        return True
    elif response.status_code == 401:
        # 尝试刷新令牌
        try:
            refresh_response = client.post("/auth/refresh", json={
                "refresh_token": "dummy_refresh_token"  # 这里应该是真实的refresh_token
            })
            return _is_api_success(refresh_response)
        except:
            return False
    else:
        return False


def create_batch_tasks(client: httpx.Client, count: int, base_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    批量创建任务

    Args:
        client: HTTP客户端
        count: 任务数量
        base_data: 基础任务数据

    Returns:
        List[Dict]: 创建的任务列表
    """
    tasks = []

    for i in range(count):
        task_data = {
            "title": f"批量任务 {i+1}",
            "description": f"第{i+1}个批量创建的任务",
            "priority": "medium",
            "tags": ["批量测试"]
        }

        # 合并基础数据
        if base_data:
            task_data.update({k: v for k, v in base_data.items() if k != "title"})

        task = create_task_with_validation(client, task_data)
        tasks.append(task)

    return tasks


def measure_api_performance(func, *args, **kwargs) -> tuple:
    """
    测量API调用性能

    Args:
        func: 要测量的函数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        tuple: (执行结果, 执行时间)
    """
    start_time = time.time()

    try:
        result = func(*args, **kwargs)
        success = True
    except Exception as e:
        result = e
        success = False

    execution_time = time.time() - start_time

    return (result, execution_time, success)


def create_test_database_session():
    """
    创建测试数据库会话（如果需要独立数据库测试）

    Returns:
        数据库会话或None
    """
    # 这里可以添加测试数据库连接逻辑
    # 目前使用共享数据库，返回None
    return None


def assert_transaction_consistency(transactions: List[Dict[str, Any]], expected_total: int, message: str = "事务一致性检查失败"):
    """
    检查事务记录的一致性

    Args:
        transactions: 事务记录列表
        expected_total: 期望的事务总数
        message: 失败时的错误消息
    """
    actual_total = len(transactions)
    assert actual_total == expected_total, f"{message}: 期望{expected_total}条记录, 实际{actual_total}条"

    # 检查必需字段
    for i, transaction in enumerate(transactions):
        assert "id" in transaction, f"{message}: 第{i+1}条记录缺少ID字段"
        assert "amount" in transaction, f"{message}: 第{i+1}条记录缺少amount字段"
        assert "source_type" in transaction, f"{message}: 第{i+1}条记录缺少source_type字段"
        assert "created_at" in transaction, f"{message}: 第{i+1}条记录缺少created_at字段"


def simulate_real_user_behavior():
    """
    模拟真实用户行为模式

    Returns:
        dict: 用户行为配置
    """
    return {
        "task_creation_frequency": "medium",  # low, medium, high
        "task_completion_rate": 0.85,  # 任务完成率
        "preferred_task_types": ["work", "learning", "personal"],
        "typical_work_duration": 45,  # 分钟
        "break_frequency": 90,  # 分钟
        "top3_usage_pattern": "daily",  # daily, weekly, occasional
    }