"""
数据库迁移脚本：添加phone字段到auth表

这个迁移脚本解决SMS认证功能中缺失phone字段的问题。
在add-phone-sms-auth提案中，Auth模型被扩展支持手机号认证，
但现有数据库表结构没有同步更新。

迁移内容：
1. 检查auth表是否有phone字段
2. 如果没有，添加phone字段（可选，唯一索引）
3. 更新现有记录（如果需要）
4. 创建phone字段的索引

作者：TaKeKe团队
版本：1.0.0 - SMS支持迁移
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# 使用与database.py相同的配置
AUTH_DATABASE_URL = os.getenv(
    "AUTH_DATABASE_URL",
    "sqlite:///./data/auth.db"
)

def add_phone_column():
    """
    添加phone字段到auth表

    Returns:
        bool: 迁移是否成功
    """
    try:
        engine = create_engine(
            AUTH_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            # 检查phone字段是否已存在
            result = conn.execute(text("PRAGMA table_info(auth)"))
            columns = [row[1] for row in result.fetchall()]

            if 'phone' in columns:
                print("✅ phone字段已存在，无需迁移")
                return True

            print("📝 开始添加phone字段到auth表...")

            # 添加phone字段
            conn.execute(text("""
                ALTER TABLE auth
                ADD COLUMN phone TEXT
            """))

            # 添加phone字段的唯一索引
            conn.execute(text("""
                CREATE UNIQUE INDEX idx_auth_phone
                ON auth(phone)
                WHERE phone IS NOT NULL
            """))

            # 提交更改
            conn.commit()

            print("✅ phone字段添加成功")
            print("✅ phone字段唯一索引创建成功")

            # 验证迁移结果
            result = conn.execute(text("PRAGMA table_info(auth)"))
            updated_columns = [row[1] for row in result.fetchall()]

            if 'phone' in updated_columns:
                print("✅ 迁移验证成功：phone字段已存在")
                return True
            else:
                print("❌ 迁移验证失败：phone字段未找到")
                return False

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False

def check_migration_needed():
    """
    检查是否需要迁移

    Returns:
        bool: 是否需要迁移
    """
    try:
        engine = create_engine(
            AUTH_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(auth)"))
            columns = [row[1] for row in result.fetchall()]

            has_phone = 'phone' in columns

            print(f"📋 当前auth表字段: {sorted(columns)}")
            print(f"📋 是否包含phone字段: {has_phone}")

            return not has_phone

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def get_current_auth_structure():
    """
    获取当前auth表结构信息

    Returns:
        dict: 表结构信息
    """
    try:
        engine = create_engine(
            AUTH_DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            # 获取表结构
            result = conn.execute(text("PRAGMA table_info(auth)"))
            columns_info = result.fetchall()

            # 获取索引信息
            result = conn.execute(text("PRAGMA index_list(auth)"))
            indexes_info = result.fetchall()

            columns = []
            for col in columns_info:
                columns.append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'primary_key': bool(col[5])
                })

            indexes = []
            for idx in indexes_info:
                if not idx[2]:  # 不是自动创建的主键索引
                    index_name = idx[1]
                    result = conn.execute(text(f"PRAGMA index_info({index_name})"))
                    index_columns = [row[2] for row in result.fetchall()]
                    indexes.append({
                        'name': index_name,
                        'unique': bool(idx[2]),
                        'columns': index_columns
                    })

            return {
                'table': 'auth',
                'columns': columns,
                'indexes': indexes,
                'column_names': [col['name'] for col in columns]
            }

    except Exception as e:
        print(f"❌ 获取表结构失败: {e}")
        return {}

if __name__ == "__main__":
    print("🔍 Auth表phone字段迁移工具")
    print("=" * 50)

    # 检查当前状态
    print("\n📋 检查当前表结构...")
    structure = get_current_auth_structure()

    if structure:
        print(f"当前字段: {structure['column_names']}")
        print(f"索引数量: {len(structure['indexes'])}")

    # 检查是否需要迁移
    print("\n🔍 检查是否需要迁移...")
    migration_needed = check_migration_needed()

    if migration_needed:
        print("\n🚀 开始执行迁移...")
        success = add_phone_column()

        if success:
            print("\n✅ 迁移完成！")

            # 再次检查表结构
            print("\n📋 迁移后表结构:")
            new_structure = get_current_auth_structure()
            if new_structure:
                print(f"更新后字段: {new_structure['column_names']}")
        else:
            print("\n❌ 迁移失败！请检查错误信息。")
    else:
        print("\n✅ 无需迁移，表结构已是最新。")