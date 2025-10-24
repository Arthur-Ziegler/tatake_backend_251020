#!/usr/bin/env python3
"""
批量修复Top3表中的JSON格式问题
"""

import json
import sqlite3

def fix_json_data():
    """修复JSON数据"""
    conn = sqlite3.connect('tatake.db')
    cursor = conn.cursor()

    try:
        # 获取所有记录
        cursor.execute("SELECT user_id, task_ids FROM task_top3")
        rows = cursor.fetchall()

        fixed_count = 0

        for user_id, task_ids in rows:
            if not task_ids:
                continue

            try:
                # 尝试解析JSON
                json.loads(task_ids)
            except json.JSONDecodeError:
                print(f"修复记录: {user_id}")
                print(f"  原始数据: {task_ids[:50]}...")

                # 修复单引号问题
                fixed_json = task_ids.replace("'", '"')

                # 验证修复后的JSON是否有效
                try:
                    json.loads(fixed_json)
                    print(f"  修复成功")

                    # 更新数据库
                    cursor.execute(
                        "UPDATE task_top3 SET task_ids = ? WHERE user_id = ?",
                        (fixed_json, user_id)
                    )
                    fixed_count += 1
                except json.JSONDecodeError as e:
                    print(f"  修复失败: {e}")

        # 提交更改
        conn.commit()
        print(f"\n总共修复了 {fixed_count} 条记录")

    finally:
        conn.close()

if __name__ == "__main__":
    fix_json_data()