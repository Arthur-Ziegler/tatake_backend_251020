#!/usr/bin/env python3
"""
调试Top3的task_ids格式问题
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from datetime import date
from uuid import uuid4
import json

from src.domains.top3.database import get_top3_session
from src.domains.top3.repository import Top3Repository

def debug_task_ids():
    """调试task_ids格式问题"""
    print("🔍 调试task_ids格式问题...")

    try:
        with get_top3_session() as session:
            repo = Top3Repository(session)

            test_user_id = uuid4()
            test_date = date.today()

            # 创建Top3记录
            task_ids = ["task1", "task2", "task3"]
            top3 = repo.create(test_user_id, test_date, task_ids)

            print(f"✅ 创建的Top3记录:")
            print(f"   - ID: {top3.id}")
            print(f"   - task_ids类型: {type(top3.task_ids)}")
            print(f"   - task_ids值: {top3.task_ids}")

            # 检查第一个元素的类型
            if top3.task_ids:
                first_item = top3.task_ids[0]
                print(f"   - 第一个元素类型: {type(first_item)}")
                print(f"   - 第一个元素值: {first_item}")

                # 检查是否是字典
                if isinstance(first_item, dict):
                    print(f"   - 第一个元素的task_id: {first_item.get('task_id')}")

            # 测试检查功能
            is_in_top3 = repo.is_task_in_today_top3(test_user_id, "task1")
            print(f"   - 检查task1是否在Top3中: {is_in_top3}")

            # 手动检查逻辑
            print("\n🔍 手动检查逻辑:")
            task_ids = top3.task_ids
            print(f"task_ids: {task_ids}")
            print(f"task_ids[0]: {task_ids[0]}")
            print(f"isinstance(task_ids[0], dict): {isinstance(task_ids[0], dict)}")

            if isinstance(task_ids[0], dict):
                print("使用新格式检查")
                result = any(item.get('task_id') == "task1" for item in task_ids)
                print(f"新格式检查结果: {result}")
            else:
                print("使用旧格式检查")
                result = "task1" in task_ids
                print(f"旧格式检查结果: {result}")

            # 清理测试数据
            session.delete(top3)
            session.commit()

            return True

    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始调试...")
    print("=" * 40)

    debug_task_ids()

    print("\n" + "=" * 40)
    print("🔍 调试完成")