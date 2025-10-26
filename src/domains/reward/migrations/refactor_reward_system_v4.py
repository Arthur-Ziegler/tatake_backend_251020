"""
数据库迁移脚本：重构奖励系统至v4规范

这个迁移脚本实现了refactor-reward-system-v4提案中的数据库变更：
1. 删除rewards表的stock_quantity字段（采用纯流水记录架构）
2. 删除rewards表的cost_type和cost_value字段（已被积分兑换替代）
3. 验证reward_transactions表完整性（确保所有变动可追溯）

迁移目标：
- 实现v4规范的纯流水记录架构
- 所有奖品无限供应
- 简化奖励系统设计
- 保持数据完整性

作者：TaKeKe团队
版本：v4.0 - 奖励系统重构
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# 使用与database.py相同的配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tatake.db"
)

def check_fields_exist():
    """
    检查需要删除的字段是否存在

    Returns:
        dict: 字段存在性检查结果
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            # 检查rewards表结构
            result = conn.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            return {
                'stock_quantity': 'stock_quantity' in columns,
                'cost_type': 'cost_type' in columns,
                'cost_value': 'cost_value' in columns,
                'all_columns': columns
            }

    except Exception as e:
        print(f"❌ 字段检查失败: {e}")
        return {
            'stock_quantity': False,
            'cost_type': False,
            'cost_value': False,
            'all_columns': [],
            'error': str(e)
        }

def backup_rewards_data():
    """
    备份rewards表数据

    Returns:
        bool: 备份是否成功
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("📝 开始备份rewards表数据...")

            # 创建备份表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rewards_backup_v4 AS
                SELECT * FROM rewards
            """))

            # 获取数据统计
            result = conn.execute(text("SELECT COUNT(*) FROM rewards"))
            count = result.scalar()

            # 检查备份表数据
            result = conn.execute(text("SELECT COUNT(*) FROM rewards_backup_v4"))
            backup_count = result.scalar()

            conn.commit()

            print(f"✅ rewards表数据备份成功：{count}条记录")
            print(f"✅ rewards_backup_v4表验证：{backup_count}条记录")

            return count == backup_count

    except Exception as e:
        print(f"❌ 数据备份失败: {e}")
        return False

def verify_reward_transactions_integrity():
    """
    验证reward_transactions表的完整性

    Returns:
        dict: 完整性验证结果
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("📋 验证reward_transactions表完整性...")

            # 检查表是否存在
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='reward_transactions'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                return {
                    'table_exists': False,
                    'error': 'reward_transactions表不存在'
                }

            # 获取基础统计
            result = conn.execute(text("SELECT COUNT(*) FROM reward_transactions"))
            total_transactions = result.scalar()

            # 检查字段完整性
            result = conn.execute(text("PRAGMA table_info(reward_transactions)"))
            transaction_columns = [row[1] for row in result.fetchall()]

            required_columns = ['id', 'user_id', 'reward_id', 'source_type', 'quantity', 'created_at']
            missing_columns = [col for col in required_columns if col not in transaction_columns]

            # 检查数据完整性
            result = conn.execute(text("""
                SELECT COUNT(*) FROM reward_transactions
                WHERE user_id IS NULL OR reward_id IS NULL OR quantity IS NULL
            """))
            invalid_records = result.scalar()

            print(f"✅ reward_transactions表存在: {table_exists}")
            print(f"✅ 总交易记录数: {total_transactions}")
            print(f"✅ 缺失字段: {missing_columns if missing_columns else '无'}")
            print(f"✅ 无效记录数: {invalid_records}")

            return {
                'table_exists': table_exists,
                'total_transactions': total_transactions,
                'missing_columns': missing_columns,
                'invalid_records': invalid_records,
                'all_columns': transaction_columns
            }

    except Exception as e:
        print(f"❌ 完整性验证失败: {e}")
        return {
            'table_exists': False,
            'error': str(e)
        }

def remove_stock_quantity_field():
    """
    删除stock_quantity字段

    Returns:
        bool: 删除是否成功
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("🗑️ 开始删除stock_quantity字段...")

            # SQLite不支持直接删除列，需要重建表
            # 1. 创建临时表
            conn.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at
                FROM rewards
            """))

            # 2. 删除原表
            conn.execute(text("DROP TABLE rewards"))

            # 3. 重命名临时表
            conn.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))

            # 4. 重新创建索引
            conn.execute(text("""
                CREATE INDEX idx_reward_name
                ON rewards(name)
            """))

            conn.commit()

            print("✅ stock_quantity字段删除成功")
            return True

    except Exception as e:
        print(f"❌ 删除stock_quantity字段失败: {e}")
        return False

def remove_cost_fields():
    """
    删除cost_type和cost_value字段

    Returns:
        bool: 删除是否成功
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("🗑️ 开始删除cost_type和cost_value字段...")

            # 检查字段是否还存在
            result = conn.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            has_cost_type = 'cost_type' in columns
            has_cost_value = 'cost_value' in columns

            if not has_cost_type and not has_cost_value:
                print("✅ cost_type和cost_value字段已不存在，无需删除")
                return True

            # SQLite不支持直接删除列，需要重建表
            # 1. 创建临时表（只保留需要的字段）
            if has_cost_type and has_cost_value:
                conn.execute(text("""
                    CREATE TABLE rewards_temp AS
                    SELECT id, name, description, points_value, image_url,
                           category, is_active, created_at, updated_at
                    FROM rewards
                """))
            elif has_cost_type:
                conn.execute(text("""
                    CREATE TABLE rewards_temp AS
                    SELECT id, name, description, points_value, image_url,
                           cost_value, category, is_active, created_at, updated_at
                    FROM rewards
                """))
            elif has_cost_value:
                conn.execute(text("""
                    CREATE TABLE rewards_temp AS
                    SELECT id, name, description, points_value, image_url,
                           cost_type, category, is_active, created_at, updated_at
                    FROM rewards
                """))

            # 2. 删除原表
            conn.execute(text("DROP TABLE rewards"))

            # 3. 重命名临时表
            conn.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))

            # 4. 重新创建索引
            conn.execute(text("""
                CREATE INDEX idx_reward_name
                ON rewards(name)
            """))

            conn.commit()

            print("✅ cost_type和cost_value字段删除成功")
            return True

    except Exception as e:
        print(f"❌ 删除cost字段失败: {e}")
        return False

def verify_migration_success():
    """
    验证迁移是否成功

    Returns:
        dict: 验证结果
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("🔍 验证迁移结果...")

            # 检查rewards表结构
            result = conn.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            # 检查数据完整性
            result = conn.execute(text("SELECT COUNT(*) FROM rewards"))
            rewards_count = result.scalar()

            # 检查备份表
            result = conn.execute(text("SELECT COUNT(*) FROM rewards_backup_v4"))
            backup_count = result.scalar() if 'rewards_backup_v4' in [t[0] for t in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()] else 0

            # 验证reward_transactions表
            transaction_integrity = verify_reward_transactions_integrity()

            removed_fields = {
                'stock_quantity': 'stock_quantity' not in columns,
                'cost_type': 'cost_type' not in columns,
                'cost_value': 'cost_value' not in columns
            }

            success = all(removed_fields.values()) and rewards_count > 0

            print(f"✅ 字段删除验证: {removed_fields}")
            print(f"✅ rewards表记录数: {rewards_count}")
            print(f"✅ 备份表记录数: {backup_count}")
            print(f"✅ 数据完整性: {success}")

            return {
                'success': success,
                'removed_fields': removed_fields,
                'rewards_count': rewards_count,
                'backup_count': backup_count,
                'current_columns': columns,
                'transaction_integrity': transaction_integrity
            }

    except Exception as e:
        print(f"❌ 迁移验证失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def migrate_reward_system_v4():
    """
    执行完整的奖励系统v4迁移

    Returns:
        bool: 迁移是否成功
    """
    print("🚀 开始奖励系统v4重构迁移...")
    print("=" * 60)

    # 1. 检查当前状态
    print("\n📋 1. 检查当前数据库状态...")
    field_check = check_fields_exist()

    if 'error' in field_check:
        print(f"❌ 数据库检查失败: {field_check['error']}")
        return False

    print(f"当前rewards表字段: {field_check['all_columns']}")
    print(f"需要删除的字段: {[k for k, v in field_check.items() if v and k != 'all_columns']}")

    # 2. 验证reward_transactions表完整性
    print("\n🔍 2. 验证reward_transactions表完整性...")
    transaction_check = verify_reward_transactions_integrity()

    if not transaction_check.get('table_exists'):
        print(f"❌ reward_transactions表不存在: {transaction_check.get('error')}")
        return False

    if transaction_check.get('missing_columns'):
        print(f"❌ reward_transactions表缺少必要字段: {transaction_check['missing_columns']}")
        return False

    # 3. 备份数据
    print("\n💾 3. 备份rewards表数据...")
    backup_success = backup_rewards_data()

    if not backup_success:
        print("❌ 数据备份失败，终止迁移")
        return False

    # 4. 删除字段
    print("\n🗑️ 4. 删除不需要的字段...")

    # 删除stock_quantity字段
    if field_check['stock_quantity']:
        stock_success = remove_stock_quantity_field()
        if not stock_success:
            print("❌ 删除stock_quantity字段失败")
            return False

    # 删除cost_type和cost_value字段
    if field_check['cost_type'] or field_check['cost_value']:
        cost_success = remove_cost_fields()
        if not cost_success:
            print("❌ 删除cost字段失败")
            return False

    # 5. 验证迁移结果
    print("\n✅ 5. 验证迁移结果...")
    migration_result = verify_migration_success()

    if migration_result['success']:
        print("\n🎉 奖励系统v4迁移完成！")
        print("✅ 已删除stock_quantity字段（采用纯流水记录）")
        print("✅ 已删除cost_type和cost_value字段（积分兑换替代）")
        print("✅ 所有奖品现在无限供应")
        print("✅ 数据完整性保持不变")
        print(f"✅ rewards表现有字段: {migration_result['current_columns']}")
        return True
    else:
        print(f"\n❌ 迁移验证失败: {migration_result.get('error')}")
        return False

def rollback_migration():
    """
    回滚迁移（从备份恢复）

    Returns:
        bool: 回滚是否成功
    """
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        with engine.connect() as conn:
            print("🔄 开始回滚迁移...")

            # 检查备份表是否存在
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='rewards_backup_v4'
            """))
            backup_exists = result.fetchone() is not None

            if not backup_exists:
                print("❌ 备份表不存在，无法回滚")
                return False

            # 删除当前表
            conn.execute(text("DROP TABLE rewards"))

            # 从备份恢复
            conn.execute(text("""
                CREATE TABLE rewards AS
                SELECT * FROM rewards_backup_v4
            """))

            # 重建索引
            conn.execute(text("""
                CREATE INDEX idx_reward_name
                ON rewards(name)
            """))

            conn.commit()

            print("✅ 迁移回滚成功")
            return True

    except Exception as e:
        print(f"❌ 回滚失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 奖励系统v4重构迁移工具")
    print("=" * 60)

    # 执行迁移
    success = migrate_reward_system_v4()

    if success:
        print("\n🎉 迁移成功完成！")
        print("\n📋 迁移后操作检查清单:")
        print("□ 确认所有测试通过")
        print("□ 验证API响应格式正确")
        print("□ 检查前端兼容性")
        print("□ 更新API文档")
        print("□ 部署到生产环境前进行完整测试")
    else:
        print("\n❌ 迁移失败！")
        print("💡 提示：可以使用 rollback_migration() 函数回滚更改")

        # 提供回滚选项
        response = input("\n是否要回滚迁移？(y/N): ")
        if response.lower() == 'y':
            rollback_success = rollback_migration()
            if rollback_success:
                print("✅ 已成功回滚迁移")
            else:
                print("❌ 回滚也失败了，请手动检查数据库状态")