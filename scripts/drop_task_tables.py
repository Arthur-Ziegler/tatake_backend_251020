#!/usr/bin/env python3
"""
删除Task相关数据表的迁移脚本

根据Task微服务迁移需求，删除以下数据表：
- tasks 表
- top3_tasks 表（task_top3表）

注意：
1. 此脚本不可逆，请确保已备份重要数据
2. 运行前请确保应用已停止
3. 确保微服务已正常运行并包含所需数据

作者：TaKeKe团队
版本：1.0.0（Task微服务迁移）
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
    # 尝试从配置中读取数据库路径
    db_path = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./tatake.db')

    # 如果是SQLite URL，提取文件路径
    if db_path.startswith('sqlite+aiosqlite:///'):
        db_path = db_path.replace('sqlite+aiosqlite:///', '')

    # 转换为绝对路径
    if not os.path.isabs(db_path):
        db_path = project_root / db_path

    return db_path

def backup_database(db_path: Path) -> Path:
    """备份数据库文件"""
    backup_path = db_path.parent / f"{db_path.stem}_backup_{int(Path().cwd().stat().st_mtime)}.db"

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
    db_path = Path(db_path)

    print(f"数据库路径: {db_path}")

    # 检查数据库文件是否存在
    if not db_path.exists():
        print(f"错误: 数据库文件不存在: {db_path}")
        return False

    # 备份数据库
    backup_path = backup_database(db_path)

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

        # 确认删除
        print(f"\n警告: 即将删除以下数据表: {', '.join(tables_to_drop)}")
        print("此操作不可逆，请确认已备份重要数据！")

        # 删除数据表
        for table_name in tables_to_drop:
            if check_table_exists(cursor, table_name):
                print(f"正在删除表: {table_name}")
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"✓ 表 {table_name} 删除成功")
            else:
                print(f"✗ 表 {table_name} 不存在，跳过")

        # 提交事务
        conn.commit()

        # 验证删除结果
        print("\n验证删除结果:")
        for table_name in tables_to_drop:
            if check_table_exists(cursor, table_name):
                print(f"✗ 表 {table_name} 仍然存在")
                return False
            else:
                print(f"✓ 表 {table_name} 已成功删除")

        print("\n数据表删除完成！")
        print(f"数据库备份保存在: {backup_path}")

        return True

    except Exception as e:
        print(f"删除数据表时发生错误: {e}")
        # 尝试恢复备份
        try:
            print("正在恢复数据库备份...")
            conn.close()
            import shutil
            shutil.copy2(backup_path, db_path)
            print("数据库已恢复到删除前状态")
        except Exception as restore_error:
            print(f"恢复备份失败: {restore_error}")
            print("请手动从备份文件恢复数据库")

        return False

    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("Task微服务迁移 - 删除数据表脚本")
    print("=" * 60)

    # 环境检查
    env = os.environ.get('ENVIRONMENT', 'development')
    if env == 'production':
        print("警告: 当前处于生产环境！")
        print("请确保已备份数据库并且微服务已正常运行。")

        response = input("确认继续删除数据表? (yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return
    else:
        print("当前环境: 开发环境")
        response = input("确认删除tasks和task_top3数据表? (y/n): ")
        if response.lower() != 'y':
            print("操作已取消")
            return

    # 执行删除
    success = drop_task_tables()

    if success:
        print("\n✅ 数据表删除成功！")
        print("Task微服务迁移Phase 3完成。")
    else:
        print("\n❌ 数据表删除失败！")
        print("请检查错误信息并手动处理。")
        sys.exit(1)

if __name__ == "__main__":
    main()