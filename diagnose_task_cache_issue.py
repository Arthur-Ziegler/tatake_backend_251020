#!/usr/bin/env python3
"""
任务缓存问题诊断脚本

深入分析：
1. 任务更新后数据延迟问题的根本原因
2. SQLAlchemy事务隔离级别和缓存问题
3. FastAPI Session管理问题
"""

import requests
import uuid
import sqlite3
import os
from datetime import datetime, timezone

BASE_URL = "http://localhost:8001"
DATABASE_PATH = "tatake.db"

def diagnose_task_cache_issue():
    """诊断任务缓存问题"""
    print("🔍 开始诊断任务缓存问题...")

    # 1. 注册测试用户
    print("\n1. 注册测试用户...")
    register_data = {
        "wechat_openid": f"cache_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ 注册失败: {response.status_code} - {response.text}")
        return False

    auth_data = response.json()["data"]
    user_id = auth_data["user_id"]
    token = auth_data["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"✅ 用户注册成功: {user_id}")

    # 2. 创建测试任务
    print("\n2. 创建测试任务...")
    task_data = {
        "title": "缓存诊断任务",
        "description": "用于诊断任务缓存问题",
        "status": "pending",
        "priority": "high"
    }

    response = requests.post(f"{BASE_URL}/tasks/", json=task_data, headers=headers)
    if response.status_code not in [200, 201]:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return False

    created_task = response.json()["data"]
    task_id = created_task["id"]
    print(f"✅ 任务创建成功: {task_id}")

    # 3. 初始状态检查
    print("\n3. 初始状态检查...")

    # API状态
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取任务详情失败: {response.status_code}")
        return False

    resp_json = response.json()
    print(f"   API响应结构: {resp_json}")

    if "data" in resp_json:
        api_data = resp_json["data"]
        print(f"   API data结构: {api_data}")
        api_task = api_data if isinstance(api_data, dict) and "status" in api_data else None
    else:
        api_task = resp_json if isinstance(resp_json, dict) and "status" in resp_json else None

    if api_task:
        print(f"   API任务状态: {api_task['status']}")
        print(f"   API任务标题: {api_task['title']}")
    else:
        print("   ❌ 无法解析API任务数据")
        return False

    # 直接数据库状态
    db_task = query_task_from_database(task_id, user_id)
    if db_task:
        print(f"   数据库状态: {db_task['status']}")
        print(f"   数据库标题: {db_task['title']}")
        print(f"   数据库updated_at: {db_task['updated_at']}")

    # 4. 更新任务
    print("\n4. 更新任务...")
    update_data = {
        "title": "缓存诊断任务-已更新",
        "description": "任务已被更新",
        "status": "in_progress"
    }

    response = requests.put(f"{BASE_URL}/tasks/{task_id}", json=update_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ 更新任务失败: {response.status_code} - {response.text}")
        return False

    updated_resp_json = response.json()
    print(f"   更新响应结构: {updated_resp_json}")

    if "data" in updated_resp_json:
        updated_data = updated_resp_json["data"]
        updated_task = updated_data if isinstance(updated_data, dict) and "status" in updated_data else None
    else:
        updated_task = updated_resp_json if isinstance(updated_resp_json, dict) and "status" in updated_resp_json else None

    if updated_task:
        print(f"✅ 任务更新成功")
        print(f"   更新后API状态: {updated_task['status']}")
        print(f"   更新后API标题: {updated_task['title']}")
        print(f"   更新后API updated_at: {updated_task['updated_at']}")
    else:
        print("   ❌ 无法解析更新后的任务数据")
        return False

    # 5. 立即检查数据一致性（关键测试）
    print("\n5. 立即检查数据一致性...")

    # 5.1 API详情检查
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取任务详情失败: {response.status_code}")
        return False

    detail_resp_json = response.json()
    if "data" in detail_resp_json:
        detail_data = detail_resp_json["data"]
        api_task_after = detail_data if isinstance(detail_data, dict) and "status" in detail_data else None
    else:
        api_task_after = detail_resp_json if isinstance(detail_resp_json, dict) and "status" in detail_resp_json else None

    if api_task_after:
        print(f"   API详情状态: {api_task_after['status']}")
        print(f"   API详情标题: {api_task_after['title']}")
        print(f"   API详情updated_at: {api_task_after['updated_at']}")
    else:
        print("   ❌ 无法解析API详情数据")
        return False

    # 5.2 API列表检查
    response = requests.get(f"{BASE_URL}/tasks/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取任务列表失败: {response.status_code}")
        return False

    list_resp_json = response.json()
    print(f"   列表响应结构: {list_resp_json}")

    if "data" in list_resp_json:
        list_data = list_resp_json["data"]
        if isinstance(list_data, dict) and "items" in list_data:
            tasks_list = list_data["items"]
        elif isinstance(list_data, list):
            tasks_list = list_data
        else:
            tasks_list = []
    else:
        tasks_list = []
    task_from_list = None
    for task in tasks_list:
        if task["id"] == task_id:
            task_from_list = task
            break

    if task_from_list:
        print(f"   API列表状态: {task_from_list['status']}")
        print(f"   API列表标题: {task_from_list['title']}")
        print(f"   API列表updated_at: {task_from_list['updated_at']}")
    else:
        print("   ❌ 在列表中找不到任务")

    # 5.3 直接数据库检查
    db_task_after = query_task_from_database(task_id, user_id)
    if db_task_after:
        print(f"   数据库状态: {db_task_after['status']}")
        print(f"   数据库标题: {db_task_after['title']}")
        print(f"   数据库updated_at: {db_task_after['updated_at']}")

    # 6. 数据一致性分析
    print("\n6. 数据一致性分析...")

    consistency_issues = []

    # 检查标题一致性
    if api_task_after['title'] != update_data['title']:
        consistency_issues.append("API详情标题与更新数据不一致")

    if task_from_list and task_from_list['title'] != update_data['title']:
        consistency_issues.append("API列表标题与更新数据不一致")

    if db_task_after and db_task_after['title'] != update_data['title']:
        consistency_issues.append("数据库标题与更新数据不一致")

    # 检查状态一致性
    if api_task_after['status'] != update_data['status']:
        consistency_issues.append("API详情状态与更新数据不一致")

    if task_from_list and task_from_list['status'] != update_data['status']:
        consistency_issues.append("API列表状态与更新数据不一致")

    if db_task_after and db_task_after['status'] != update_data['status']:
        consistency_issues.append("数据库状态与更新数据不一致")

    # 检查时间戳一致性
    if api_task_after['updated_at'] == updated_task['updated_at']:
        print("   ✅ API详情时间戳正确更新")
    else:
        consistency_issues.append("API详情时间戳未更新")

    if task_from_list and task_from_list['updated_at'] == updated_task['updated_at']:
        print("   ✅ API列表时间戳正确更新")
    else:
        consistency_issues.append("API列表时间戳未更新")

    # 7. 诊断结论
    print("\n7. 诊断结论...")

    if consistency_issues:
        print("   ❌ 发现数据一致性问题:")
        for i, issue in enumerate(consistency_issues, 1):
            print(f"      {i}. {issue}")

        print("\n   🔍 可能的原因:")
        print("      1. SQLAlchemy Session缓存问题")
        print("      2. 事务隔离级别问题")
        print("      3. 数据库连接池问题")
        print("      4. API路由间的Session复用问题")

        return False
    else:
        print("   ✅ 数据一致性检查通过")
        return True

def query_task_from_database(task_id, user_id):
    """直接从数据库查询任务"""
    try:
        if not os.path.exists(DATABASE_PATH):
            print(f"   ❌ 数据库文件不存在: {DATABASE_PATH}")
            return None

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, title, status, description, updated_at FROM tasks WHERE id = ? AND user_id = ?",
            (str(task_id), str(user_id))
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        print(f"   ❌ 数据库查询失败: {e}")
        return None

if __name__ == "__main__":
    diagnose_task_cache_issue()