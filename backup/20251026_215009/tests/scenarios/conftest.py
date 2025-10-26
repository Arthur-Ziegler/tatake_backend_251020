"""
API场景测试共享fixtures

提供场景测试所需的共享fixtures和测试工具函数。
每个测试文件将获得独立的测试用户，确保测试之间的隔离。

测试策略:
- 每个文件(module scope)共享一个测试用户
- 使用API客户端进行真实HTTP调用
- 测试结束后自动清理创建的数据

作者：TaKeKe团队
版本：1.0.0
"""

import pytest
import httpx
from typing import Generator, Dict, Any
from uuid import uuid4
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# from src.domains.auth.schemas import WeChatRegisterRequest  # 暂时注释掉，避免导入问题


@pytest.fixture(scope="module")
def api_client() -> Generator[httpx.Client, None, None]:
    """
    API客户端fixture

    提供用于场景测试的httpx客户端，连接到运行在8001端口的后端服务。
    """
    base_url = "http://localhost:8001"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="module")
def test_user(api_client: httpx.Client) -> Generator[Dict[str, Any], None, None]:
    """
    测试用户fixture

    为每个测试文件创建一个独立的测试用户，通过微信注册获得认证token。
    测试结束后自动清理用户数据。
    """
    # 生成唯一的微信OpenID确保用户不重复
    unique_openid = f"test_scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

    # 注册测试用户
    register_data = {
        "wechat_openid": unique_openid
    }

    response = api_client.post("/auth/register", json=register_data)
    assert response.status_code == 200, f"注册测试用户失败: {response.text}"

    register_result = response.json()
    assert register_result["code"] == 200, f"注册响应格式错误: {register_result}"

    access_token = register_result["data"]["access_token"]
    refresh_token = register_result["data"]["refresh_token"]
    user_id = register_result["data"]["user_id"]

    # 返回测试用户信息
    user_info = {
        "id": user_id,
        "wechat_openid": unique_openid,
        "nickname": f"场景测试用户_{unique_openid[-8:]}",
        "access_token": access_token,
        "refresh_token": refresh_token
    }

    yield user_info

    # 清理：删除测试用户（通过删除所有相关数据）
    try:
        # 使用删除API端点清理数据（如果有的话）
        # 或者直接删除数据库中的用户记录
        headers = {"Authorization": f"Bearer {access_token}"}

        # 尝试删除用户创建的各种数据
        _cleanup_user_data(api_client, headers, user_id)

    except Exception as e:
        print(f"清理测试用户数据时出错: {e}")
        # 继续执行，不让清理错误影响测试结果


@pytest.fixture(scope="module")
def authenticated_client(api_client: httpx.Client, test_user: Dict[str, Any]) -> Generator[httpx.Client, None, None]:
    """
    认证客户端fixture

    提供带有认证头的API客户端，可以直接调用需要认证的API。
    """
    # 创建带有认证头的客户端副本
    headers = {
        "Authorization": f"Bearer {test_user['access_token']}",
        "Content-Type": "application/json"
    }

    # 使用默认headers创建客户端
    client = httpx.Client(
        base_url="http://localhost:8001",
        headers=headers,
        timeout=30.0
    )

    try:
        yield client
    finally:
        client.close()


def _cleanup_user_data(api_client: httpx.Client, headers: Dict[str, str], user_id: str):
    """
    清理用户创建的所有数据

    Args:
        api_client: API客户端
        headers: 认证头
        user_id: 用户ID
    """
    # 清理任务数据
    try:
        # 获取所有任务
        tasks_response = api_client.get("/tasks/", headers=headers)
        if tasks_response.status_code == 200:
            tasks = tasks_response.json().get("data", {}).get("items", [])
            for task in tasks:
                # 删除任务
                delete_response = api_client.delete(f"/tasks/{task['id']}", headers=headers)
                if delete_response.status_code not in [200, 404]:
                    print(f"删除任务 {task['id']} 失败: {delete_response.status_code}")
    except Exception as e:
        print(f"清理任务数据时出错: {e}")

    # 注意：Top3和Focus会话通常不需要手动清理，因为它们有日期限制
    # 如果需要清理，可以在具体测试中实现

    # 其他数据的清理可以在这里添加...


# 场景测试标记
pytest.mark.scenario = pytest.mark.scenario
pytest.mark.task_flow = pytest.mark.task_flow
pytest.mark.top3_flow = pytest.mark.top3_flow
pytest.mark.combined_flow = pytest.mark.combined_flow
pytest.mark.focus_flow = pytest.mark.focus_flow