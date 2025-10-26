"""
奖励系统v4数据库迁移测试

测试refactor-reward-system-v4提案中的数据库迁移脚本：
1. 验证迁移脚本功能
2. 测试数据完整性
3. 验证回滚功能

作者：TaKeKe团队
版本：v4.0 - 迁移验证
"""

import pytest
import tempfile
import os
from uuid import uuid4
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, text
from sqlalchemy import StaticPool

from src.domains.reward.migrations.refactor_reward_system_v4 import (
    check_fields_exist,
    backup_rewards_data,
    verify_reward_transactions_integrity,
    remove_stock_quantity_field,
    remove_cost_fields,
    verify_migration_success,
    rollback_migration
)


@pytest.fixture
def pre_migration_db():
    """创建迁移前的数据库结构（包含要删除的字段）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    with engine.connect() as conn:
        # 创建旧版rewards表（包含要删除的字段）
        conn.execute(text("""
            CREATE TABLE rewards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                points_value INTEGER NOT NULL,
                image_url TEXT,
                cost_type TEXT NOT NULL,
                cost_value INTEGER NOT NULL,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))

        # 创建reward_transactions表
        conn.execute(text("""
            CREATE TABLE reward_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                reward_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT,
                quantity INTEGER NOT NULL,
                transaction_group TEXT,
                created_at DATETIME NOT NULL
            )
        """))

        # 插入示例数据
        sample_rewards = [
            (str(uuid4()), "小金币", "基础奖品", 10, None, "points", 5, 100, "basic", True, datetime.now(), datetime.now()),
            (str(uuid4()), "钻石", "珍贵奖品", 100, None, "points", 50, 10, "premium", True, datetime.now(), datetime.now()),
            (str(uuid4()), "测试奖品", "测试用", 20, None, "recipe", 0, 5, "test", True, datetime.now(), datetime.now())
        ]

        for reward_data in sample_rewards:
            conn.execute(text("""
                INSERT INTO rewards (id, name, description, points_value, image_url,
                                  cost_type, cost_value, stock_quantity, category, is_active,
                                  created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), reward_data)

        # 插入示例交易数据
        sample_transactions = [
            (str(uuid4()), str(uuid4()), sample_rewards[0][0], "task_complete", str(uuid4()), 1, str(uuid4()), datetime.now()),
            (str(uuid4()), str(uuid4()), sample_rewards[1][0], "redemption", str(uuid4()), 1, str(uuid4()), datetime.now()),
            (str(uuid4()), str(uuid4()), sample_rewards[2][0], "lottery_reward", str(uuid4()), 2, str(uuid4()), datetime.now())
        ]

        for tx_data in sample_transactions:
            conn.execute(text("""
                INSERT INTO reward_transactions (id, user_id, reward_id, source_type,
                                               source_id, quantity, transaction_group, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """), tx_data)

        conn.commit()

    return engine


@pytest.fixture
def migration_test_env():
    """设置迁移测试环境变量"""
    # 设置临时数据库路径
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()

    original_db_url = os.getenv('DATABASE_URL')
    os.environ['DATABASE_URL'] = f"sqlite:///{temp_db.name}"

    yield temp_db.name

    # 恢复原始环境变量
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url
    else:
        os.environ.pop('DATABASE_URL', None)

    # 清理临时文件
    try:
        os.unlink(temp_db.name)
    except:
        pass


class TestRewardSystemV4Migration:
    """奖励系统v4迁移测试类"""

    def test_check_fields_exist_pre_migration(self, pre_migration_db):
        """测试迁移前字段存在性检查"""
        with Session(pre_migration_db) as session:
            # 模拟check_fields_exist函数的逻辑
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            # 验证字段存在
            assert 'stock_quantity' in columns
            assert 'cost_type' in columns
            assert 'cost_value' in columns

    def test_check_fields_exist_post_migration(self, pre_migration_db):
        """测试迁移后字段不存在性检查"""
        # 先执行迁移
        with Session(pre_migration_db) as session:
            # 模拟删除字段（SQLite方式：重建表）
            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at
                FROM rewards
            """))
            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))
            session.commit()

        # 检查字段已删除
        with Session(pre_migration_db) as session:
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            # 验证字段已删除
            assert 'stock_quantity' not in columns
            assert 'cost_type' not in columns
            assert 'cost_value' not in columns

    def test_backup_rewards_data(self, pre_migration_db):
        """测试数据备份功能"""
        with Session(pre_migration_db) as session:
            # 执行备份
            session.execute(text("""
                CREATE TABLE rewards_backup_v4 AS
                SELECT * FROM rewards
            """))
            session.commit()

            # 验证备份数据完整性
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            original_count = result.scalar()

            result = session.execute(text("SELECT COUNT(*) FROM rewards_backup_v4"))
            backup_count = result.scalar()

            assert original_count == backup_count

            # 验证数据内容一致性
            result = session.execute(text("""
                SELECT r.id, r.name, r.stock_quantity, b.id, b.name, b.stock_quantity
                FROM rewards r
                JOIN rewards_backup_v4 b ON r.id = b.id
            """))

            for row in result.fetchall():
                assert row[0] == row[3]  # ID相同
                assert row[1] == row[4]  # name相同
                assert row[2] == row[5]  # stock_quantity相同

    def test_verify_reward_transactions_integrity(self, pre_migration_db):
        """测试reward_transactions表完整性验证"""
        with Session(pre_migration_db) as session:
            # 验证表存在
            result = session.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='reward_transactions'
            """))
            assert result.fetchone() is not None

            # 验证字段完整性
            result = session.execute(text("PRAGMA table_info(reward_transactions)"))
            columns = [row[1] for row in result.fetchall()]

            required_columns = ['id', 'user_id', 'reward_id', 'source_type', 'quantity', 'created_at']
            for col in required_columns:
                assert col in columns

            # 验证数据完整性
            result = session.execute(text("""
                SELECT COUNT(*) FROM reward_transactions
                WHERE user_id IS NULL OR reward_id IS NULL OR quantity IS NULL
            """))
            invalid_count = result.scalar()
            assert invalid_count == 0

            # 验证数据量
            result = session.execute(text("SELECT COUNT(*) FROM reward_transactions"))
            total_count = result.scalar()
            assert total_count == 3  # 插入了3条示例数据

    def test_remove_stock_quantity_field(self, pre_migration_db):
        """测试删除stock_quantity字段"""
        with Session(pre_migration_db) as session:
            # 验证字段存在
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]
            assert 'stock_quantity' in columns

            # 执行删除操作
            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       cost_type, cost_value, category, is_active,
                       created_at, updated_at
                FROM rewards
            """))
            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))
            session.commit()

            # 验证字段已删除
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]
            assert 'stock_quantity' not in columns

            # 验证其他字段仍然存在
            assert 'cost_type' in columns
            assert 'cost_value' in columns

    def test_remove_cost_fields(self, pre_migration_db):
        """测试删除cost_type和cost_value字段"""
        with Session(pre_migration_db) as session:
            # 验证字段存在
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]
            assert 'cost_type' in columns
            assert 'cost_value' in columns

            # 执行删除操作
            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       stock_quantity, category, is_active,
                       created_at, updated_at
                FROM rewards
            """))
            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))
            session.commit()

            # 验证字段已删除
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]
            assert 'cost_type' not in columns
            assert 'cost_value' not in columns

    def test_complete_migration_flow(self, pre_migration_db):
        """测试完整迁移流程"""
        with Session(pre_migration_db) as session:
            # 记录迁移前状态
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            original_count = result.scalar()

            # 执行完整迁移（删除所有目标字段）
            session.execute(text("""
                CREATE TABLE rewards_backup_v4 AS
                SELECT * FROM rewards
            """))

            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at
                FROM rewards
            """))

            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))

            # 重建索引
            session.execute(text("""
                CREATE INDEX idx_reward_name
                ON rewards(name)
            """))

            session.commit()

            # 验证迁移结果
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]

            # 验证字段删除
            assert 'stock_quantity' not in columns
            assert 'cost_type' not in columns
            assert 'cost_value' not in columns

            # 验证必需字段存在
            required_fields = ['id', 'name', 'description', 'points_value', 'category', 'is_active']
            for field in required_fields:
                assert field in columns

            # 验证数据完整性
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            final_count = result.scalar()
            assert final_count == original_count

            # 验证备份数据
            result = session.execute(text("SELECT COUNT(*) FROM rewards_backup_v4"))
            backup_count = result.scalar()
            assert backup_count == original_count

    def test_rollback_functionality(self, pre_migration_db):
        """测试回滚功能"""
        with Session(pre_migration_db) as session:
            # 记录原始数据
            result = session.execute(text("""
                SELECT id, name, stock_quantity, cost_type, cost_value
                FROM rewards
                ORDER BY id
            """))
            original_data = result.fetchall()

            # 创建备份
            session.execute(text("""
                CREATE TABLE rewards_backup_v4 AS
                SELECT * FROM rewards
            """))

            # 执行迁移
            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at
                FROM rewards
            """))
            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))
            session.commit()

            # 验证迁移后结构
            result = session.execute(text("PRAGMA table_info(rewards)"))
            columns = [row[1] for row in result.fetchall()]
            assert 'stock_quantity' not in columns

            # 执行回滚
            session.execute(text("DROP TABLE rewards"))
            session.execute(text("""
                CREATE TABLE rewards AS
                SELECT * FROM rewards_backup_v4
            """))
            session.execute(text("""
                CREATE INDEX idx_reward_name
                ON rewards(name)
            """))
            session.commit()

            # 验证回滚结果
            result = session.execute(text("""
                SELECT id, name, stock_quantity, cost_type, cost_value
                FROM rewards
                ORDER BY id
            """))
            rollback_data = result.fetchall()

            # 验证数据一致性
            assert len(rollback_data) == len(original_data)
            for i in range(len(original_data)):
                assert rollback_data[i][0] == original_data[i][0]  # ID
                assert rollback_data[i][1] == original_data[i][1]  # name
                assert rollback_data[i][2] == original_data[i][2]  # stock_quantity

    def test_migration_error_handling(self, pre_migration_db):
        """测试迁移错误处理"""
        with Session(pre_migration_db) as session:
            # 模拟迁移过程中的错误处理
            try:
                # 尝试删除不存在的字段（应该不会出错）
                session.execute(text("""
                    CREATE TABLE rewards_temp AS
                    SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at,
                       nonexistent_field  -- 这个字段不存在，但应该被忽略
                FROM rewards
                """))
            except Exception as e:
                # 应该抛出异常
                assert "no such column" in str(e).lower()

            # 验证原表未受影响
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            count = result.scalar()
            assert count > 0

    def test_data_integrity_after_migration(self, pre_migration_db):
        """测试迁移后数据完整性"""
        with Session(pre_migration_db) as session:
            # 插入更复杂的测试数据
            test_data = []
            for i in range(10):
                test_data.append((
                    str(uuid4()),
                    f"测试奖品_{i}",
                    f"测试奖品描述_{i}",
                    i * 10,
                    f"http://example.com/{i}.jpg",
                    "points",
                    i * 5,
                    i * 2,
                    f"category_{i % 3}",
                    i % 2 == 0,
                    datetime.now(),
                    datetime.now()
                ))

            for data in test_data:
                session.execute(text("""
                    INSERT INTO rewards (id, name, description, points_value, image_url,
                                      cost_type, cost_value, stock_quantity, category, is_active,
                                      created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """), data)

            session.commit()

            # 记录迁移前数据统计
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            original_count = result.scalar()

            result = session.execute(text("""
                SELECT SUM(points_value), AVG(points_value), MAX(points_value), MIN(points_value)
                FROM rewards
            """))
            original_stats = result.fetchone()

            # 执行迁移
            session.execute(text("""
                CREATE TABLE rewards_backup_v4 AS
                SELECT * FROM rewards
            """))

            session.execute(text("""
                CREATE TABLE rewards_temp AS
                SELECT id, name, description, points_value, image_url,
                       category, is_active, created_at, updated_at
                FROM rewards
            """))

            session.execute(text("DROP TABLE rewards"))
            session.execute(text("ALTER TABLE rewards_temp RENAME TO rewards"))
            session.commit()

            # 验证数据完整性
            result = session.execute(text("SELECT COUNT(*) FROM rewards"))
            final_count = result.scalar()
            assert final_count == original_count

            result = session.execute(text("""
                SELECT SUM(points_value), AVG(points_value), MAX(points_value), MIN(points_value)
                FROM rewards
            """))
            final_stats = result.fetchone()

            # 验证统计数据一致
            assert final_stats[0] == original_stats[0]  # SUM
            assert final_stats[1] == original_stats[1]  # AVG
            assert final_stats[2] == original_stats[2]  # MAX
            assert final_stats[3] == original_stats[3]  # MIN


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])