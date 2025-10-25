"""
迁移到PostgreSQL Schema分离架构

从现有的单数据库架构迁移到Schema分离架构。
支持数据迁移、Schema创建、索引优化等。

功能特性：
1. 自动创建领域Schema
2. 数据迁移和验证
3. 索引重建和优化
4. 回滚支持
5. 多租户Schema创建

使用方法：
python scripts/migrate_to_schemas.py --action=create_schemas
python scripts/migrate_to_schemas.py --action=migrate_data
python scripts/migrate_to_schemas.py --action=verify_migration
python scripts/migrate_to_schemas.py --action=rollback

作者：TaKeKe团队
版本：v1.0
"""

import argparse
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchemaMigrationManager:
    """Schema迁移管理器"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)

        # 领域配置
        self.domains = {
            'auth': 'auth_domain',
            'task': 'task_domain',
            'reward': 'reward_domain',
            'points': 'points_domain',
            'top3': 'top3_domain',
            'focus': 'focus_domain'
        }

        # 表映射（旧表名 -> 新Schema.表名）
        self.table_mappings = {
            'auth': {
                'auth': 'auth_domain.auth',
                'auth_audit_logs': 'auth_domain.auth_audit_logs'
            },
            'task': {
                'tasks': 'task_domain.tasks'
            },
            'points': {
                'points_transactions': 'points_domain.points_transactions'
            },
            'reward': {
                'rewards': 'reward_domain.rewards',
                'reward_recipes': 'reward_domain.reward_recipes',
                'reward_transactions': 'reward_domain.reward_transactions'
            },
            'top3': {
                'task_top3': 'top3_domain.task_top3'
            },
            'focus': {
                'focus_sessions': 'focus_domain.focus_sessions'
            }
        }

    def create_schemas(self) -> bool:
        """创建所有领域Schema"""
        try:
            with self.engine.connect() as conn:
                # 开始事务
                conn.begin()

                logger.info("开始创建领域Schema...")

                # 创建每个Schema
                for domain, schema_name in self.domains.items():
                    logger.info(f"创建Schema: {schema_name}")
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

                # 提交事务
                conn.commit()
                logger.info("所有Schema创建成功！")
                return True

        except Exception as e:
            logger.error(f"创建Schema失败: {e}")
            return False

    def migrate_data(self, dry_run: bool = False) -> bool:
        """
        迁移数据到Schema分离架构

        Args:
            dry_run: 是否为试运行（不实际执行迁移）

        Returns:
            bool: 迁移是否成功
        """
        try:
            with self.engine.connect() as conn:
                if not dry_run:
                    conn.begin()

                logger.info("开始数据迁移...")

                # 获取现有的表
                inspector = inspect(self.engine)
                existing_tables = inspector.get_table_names()

                # 逐个迁移每个域的表
                for domain, schema_name in self.domains.items():
                    if domain not in self.table_mappings:
                        continue

                    logger.info(f"迁移域: {domain} -> {schema_name}")

                    for old_table, new_table in self.table_mappings[domain].items():
                        if old_table not in existing_tables:
                            logger.warning(f"表 {old_table} 不存在，跳过")
                            continue

                        self._migrate_table(conn, old_table, new_table, dry_run)

                if not dry_run:
                    conn.commit()
                logger.info("数据迁移完成！")
                return True

        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            return False

    def _migrate_table(self, conn, old_table: str, new_table: str, dry_run: bool = False):
        """迁移单个表"""
        logger.info(f"迁移表: {old_table} -> {new_table}")

        # 构建迁移SQL
        schema, table = new_table.split('.')
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {new_table} (LIKE {old_table} INCLUDING ALL)
        """

        insert_sql = f"""
        INSERT INTO {new_table} SELECT * FROM {old_table}
        ON CONFLICT DO NOTHING
        """

        if dry_run:
            logger.info(f"[DRY RUN] 将执行: {create_table_sql}")
            logger.info(f"[DRY RUN] 将执行: {insert_sql}")
        else:
            # 创建新表（如果不存在）
            conn.execute(text(create_table_sql))
            logger.info(f"创建表: {new_table}")

            # 迁移数据
            result = conn.execute(text(insert_sql))
            migrated_rows = result.rowcount
            logger.info(f"迁移了 {migrated_rows} 行数据到 {new_table}")

            # 验证数据迁移
            self._verify_table_migration(conn, old_table, new_table)

    def _verify_table_migration(self, conn, old_table: str, new_table: str):
        """验证表迁移是否成功"""
        # 检查行数
        old_count = conn.execute(text(f"SELECT COUNT(*) FROM {old_table}")).scalar()
        new_count = conn.execute(text(f"SELECT COUNT(*) FROM {new_table}")).scalar()

        if old_count == new_count:
            logger.info(f"✅ {new_table} 数据验证通过 ({new_count} 行)")
        else:
            logger.warning(f"⚠️  {new_table} 数据数量不匹配: 原表={old_count}, 新表={new_count}")

    def create_indexes(self) -> bool:
        """创建Schema特定的索引"""
        try:
            with self.engine.connect() as conn:
                conn.begin()

                logger.info("开始创建Schema索引...")

                # 任务领域索引
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_task_user_id ON task_domain.tasks(user_id);
                    CREATE INDEX IF NOT EXISTS idx_task_status ON task_domain.tasks(status);
                    CREATE INDEX IF NOT EXISTS idx_task_parent_id ON task_domain.tasks(parent_id);
                    CREATE INDEX IF NOT EXISTS idx_task_completion ON task_domain.tasks(completion_percentage);
                    CREATE INDEX IF NOT EXISTS idx_task_last_claimed ON task_domain.tasks(last_claimed_date);
                """))

                # 积分领域索引
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_points_user_id ON points_domain.points_transactions(user_id);
                    CREATE INDEX IF NOT EXISTS idx_points_source_date ON points_domain.points_transactions(source_type, created_at);
                    CREATE INDEX IF NOT EXISTS idx_points_transaction_group ON points_domain.points_transactions(transaction_group);
                """))

                # 奖励领域索引
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_reward_user_time ON reward_domain.reward_transactions(user_id, created_at);
                    CREATE INDEX IF NOT EXISTS idx_reward_transaction ON reward_domain.reward_transactions(reward_id);
                    CREATE INDEX IF NOT EXISTS idx_reward_group ON reward_domain.reward_transactions(transaction_group);
                """))

                # Top3领域索引
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_top3_user_date ON top3_domain.task_top3(user_id, top_date);
                    CREATE INDEX IF NOT EXISTS idx_top3_date ON top3_domain.task_top3(top_date);
                """))

                # 专注领域索引
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_focus_user_time ON focus_domain.focus_sessions(user_id, start_time);
                    CREATE INDEX IF NOT EXISTS idx_focus_task_session ON focus_domain.focus_sessions(task_id, session_type);
                    CREATE INDEX IF NOT EXISTS idx_focus_active ON focus_domain.focus_sessions(user_id, end_time);
                """))

                conn.commit()
                logger.info("索引创建完成！")
                return True

        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return False

    def verify_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        logger.info("开始验证迁移结果...")

        verification_result = {
            "schemas_created": [],
            "tables_migrated": [],
            "data_consistency": {},
            "errors": []
        }

        try:
            with self.engine.connect() as conn:
                # 检查Schema
                inspector = inspect(self.engine)
                all_schemas = inspector.get_schema_names()

                for domain, schema_name in self.domains.items():
                    if schema_name in all_schemas:
                        verification_result["schemas_created"].append(schema_name)
                        logger.info(f"✅ Schema {schema_name} 已创建")
                    else:
                        verification_result["errors"].append(f"Schema {schema_name} 未找到")
                        logger.error(f"❌ Schema {schema_name} 未找到")

                # 检查表和数据一致性
                for domain, schema_name in self.domains.items():
                    if domain not in self.table_mappings:
                        continue

                    for old_table, new_table in self.table_mappings[domain].items():
                        try:
                            # 检查新表是否存在
                            schema, table = new_table.split('.')
                            new_tables = inspector.get_table_names(schema=schema)

                            if table in new_tables:
                                verification_result["tables_migrated"].append(new_table)

                                # 检查数据一致性
                                old_count = conn.execute(text(f"SELECT COUNT(*) FROM {old_table}")).scalar()
                                new_count = conn.execute(text(f"SELECT COUNT(*) FROM {new_table}")).scalar()

                                verification_result["data_consistency"][new_table] = {
                                    "old_count": old_count,
                                    "new_count": new_count,
                                    "consistent": old_count == new_count
                                }

                                if old_count == new_count:
                                    logger.info(f"✅ 表 {new_table} 数据一致 ({new_count} 行)")
                                else:
                                    logger.warning(f"⚠️  表 {new_table} 数据不一致: 原表={old_count}, 新表={new_count}")
                            else:
                                verification_result["errors"].append(f"表 {new_table} 未找到")
                                logger.error(f"❌ 表 {new_table} 未找到")

                        except Exception as e:
                            verification_result["errors"].append(f"验证表 {new_table} 时出错: {e}")
                            logger.error(f"❌ 验证表 {new_table} 时出错: {e}")

        except Exception as e:
            verification_result["errors"].append(f"验证过程出错: {e}")
            logger.error(f"❌ 验证过程出错: {e}")

        return verification_result

    def rollback(self) -> bool:
        """回滚迁移（删除Schema和表）"""
        try:
            with self.engine.connect() as conn:
                conn.begin()

                logger.warning("开始回滚迁移...")
                logger.warning("这将删除所有新创建的Schema和表！")

                # 删除所有Schema（级联删除表）
                for domain, schema_name in self.domains.items():
                    try:
                        conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                        logger.info(f"已删除Schema: {schema_name}")
                    except Exception as e:
                        logger.warning(f"删除Schema {schema_name} 时出错: {e}")

                conn.commit()
                logger.info("回滚完成！")
                return True

        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False

    def create_tenant_schemas(self, tenant_id: str) -> bool:
        """为租户创建Schema"""
        try:
            with self.engine.connect() as conn:
                conn.begin()

                logger.info(f"为租户 {tenant_id} 创建Schema...")

                for domain in self.domains.keys():
                    schema_name = f"{tenant_id}_{domain}_domain"
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                    logger.info(f"创建租户Schema: {schema_name}")

                conn.commit()
                logger.info(f"租户 {tenant_id} Schema创建完成！")
                return True

        except Exception as e:
            logger.error(f"创建租户Schema失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PostgreSQL Schema迁移工具")
    parser.add_argument(
        "--database-url",
        default="postgresql://tatake_app:password@localhost:5432/tatake",
        help="数据库连接URL"
    )
    parser.add_argument(
        "--action",
        choices=[
            "create_schemas",
            "migrate_data",
            "create_indexes",
            "verify_migration",
            "rollback",
            "create_tenant_schemas"
        ],
        required=True,
        help="要执行的操作"
    )
    parser.add_argument(
        "--tenant-id",
        help="租户ID（用于create_tenant_schemas操作）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式（不实际执行操作）"
    )

    args = parser.parse_args()

    # 创建迁移管理器
    migration_manager = SchemaMigrationManager(args.database_url)

    # 执行操作
    if args.action == "create_schemas":
        success = migration_manager.create_schemas()
    elif args.action == "migrate_data":
        success = migration_manager.migrate_data(dry_run=args.dry_run)
    elif args.action == "create_indexes":
        success = migration_manager.create_indexes()
    elif args.action == "verify_migration":
        result = migration_manager.verify_migration()
        print("\n=== 迁移验证结果 ===")
        print(f"成功创建的Schema: {result['schemas_created']}")
        print(f"成功迁移的表: {result['tables_migrated']}")
        print(f"数据一致性: {result['data_consistency']}")
        if result['errors']:
            print(f"错误: {result['errors']}")
        success = len(result['errors']) == 0
    elif args.action == "rollback":
        success = migration_manager.rollback()
    elif args.action == "create_tenant_schemas":
        if not args.tenant_id:
            logger.error("create_tenant_schemas操作需要提供--tenant-id参数")
            success = False
        else:
            success = migration_manager.create_tenant_schemas(args.tenant_id)
    else:
        logger.error(f"未知操作: {args.action}")
        success = False

    # 输出结果
    if success:
        logger.info("✅ 操作完成！")
        exit(0)
    else:
        logger.error("❌ 操作失败！")
        exit(1)


if __name__ == "__main__":
    main()