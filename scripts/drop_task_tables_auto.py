#!/usr/bin/env python3
"""
自动删除Task相关数据表的迁移脚本

根据Task微服务迁移需求，删除以下数据表：
- tasks 表
- task_top3 表

此脚本自动执行，无需用户确认。
"""

import sqlite3
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_database_path():
    """获取数据库文件路径"""
    db_path = 'tatake.db'  # 使用默认路径
    return project_root / db_path

def backup_database(db_path: Path) -> Path:
    """备份数据库文件"""
    backup_path = db_path.parent / f"{db_path.stem}_backup_before_microservice_migration.db"

    print(f"正在备份数据库到: {backup_path}")

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"数据库备份成功: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"数据库备份失败: {e}")
        raise

def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """检查表是否存在"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def get_table_row_count(cursor: sqlite3.Cursor, table_name: str) -> int:
    """获取表的行数"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0

def drop_task_tables():
    """删除Task相关数据表"""
    db_path = get_database_path()

    print(f"数据库路径: {db_path}")

    # 检查数据库文件是否存在
    if not db_path.exists():
        print(f"警告: 数据库文件不存在: {db_path}")
        print("跳过数据表删除")
        return True

    # 备份数据库
    try:
        backup_path = backup_database(db_path)
    except Exception as e:
        print(f"备份数据库失败，但继续执行删除: {e}")
        backup_path = None

    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查并显示要删除的表信息
        tables_to_drop = ['tasks', 'task_top3']

        print("\n检查数据表:")
        for table_name in tables_to_drop:
            if check_table_exists(cursor, table_name):
                row_count = get_table_row_count(cursor, table_name)
                print(f"  ✓ {table_name} 表存在，包含 {row_count} 行数据")
            else:
                print(f"  ✗ {table_name} 表不存在")

        print(f"\n自动删除数据表: {', '.join(tables_to_drop)}")

        # 删除数据表
        deleted_tables = []
        for table_name in tables_to_drop:
            if check_table_exists(cursor, table_name):
                print(f"正在删除表: {table_name}")
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                deleted_tables.append(table_name)
                print(f"✓ 表 {table_name} 删除成功")
            else:
                print(f"✗ 表 {table_name} 不存在，跳过")

        # 提交事务
        conn.commit()

        # 验证删除结果
        print("\n验证删除结果:")
        all_deleted = True
        for table_name in tables_to_drop:
            if check_table_exists(cursor, table_name):
                print(f"✗ 表 {table_name} 仍然存在")
                all_deleted = False
            else:
                print(f"✓ 表 {table_name} 已成功删除")

        if all_deleted and deleted_tables:
            print("\n✅ 数据表删除成功！")
            if backup_path:
                print(f"数据库备份保存在: {backup_path}")
            return True
        elif not deleted_tables:
            print("\n✅ 没有找到需要删除的表，操作完成")
            return True
        else:
            print("\n❌ 部分数据表删除失败")
            return False

    except Exception as e:
        print(f"删除数据表时发生错误: {e}")
        return False

    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("Task微服务迁移 - 自动删除数据表脚本")
    print("=" * 60)

    # 执行删除
    success = drop_task_tables()

    if success:
        print("\n✅ Phase 3完成：数据表删除成功！")
        print("Task微服务迁移的数据库清理步骤已完成。")
    else:
        print("\n❌ 数据表删除失败！")
        print("请检查错误信息并手动处理。")
        sys.exit(1)

if __name__ == "__main__":
    main()