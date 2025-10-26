#!/usr/bin/env python3
"""
快速修复is_task_in_today_top3问题
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from datetime import date
from uuid import uuid4

from src.domains.top3.database import get_top3_session
from src.domains.top3.repository import Top3Repository

# 直接测试修复后的代码
def test_fix():
    with get_top3_session() as session:
        repo = Top3Repository(session)

        test_user_id = uuid4()
        test_date = date.today()

        # 创建Top3记录
        task_ids = ["task1", "task2", "task3"]
        top3 = repo.create(test_user_id, test_date, task_ids)

        print(f"创建的Top3: {top3}")
        print(f"task_ids类型: {type(top3.task_ids)}")
        print(f"task_ids值: {top3.task_ids}")

        # 现在查询回去看看能否正确解析
        queried_top3 = repo.get_by_user_and_date(test_user_id, test_date)
        print(f"查询的Top3: {queried_top3}")
        print(f"查询的task_ids类型: {type(queried_top3.task_ids)}")
        print(f"查询的task_ids值: {queried_top3.task_ids}")

        # 测试检查功能
        result = repo.is_task_in_today_top3(test_user_id, "task1")
        print(f"检查结果: {result}")

        # 清理
        session.delete(top3)
        session.commit()

if __name__ == "__main__":
    test_fix()