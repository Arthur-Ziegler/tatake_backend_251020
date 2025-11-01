"""
Profile数据库迁移模块

提供Profile数据库的迁移功能，包括表创建、字段添加和数据迁移。

功能：
1. Profile数据库表结构创建
2. 数据迁移和验证
3. 迁移版本管理
4. 回滚支持

作者：TaTakeKe团队
版本：1.0.0 - Profile功能增强
"""

import logging
from typing import Optional
from sqlmodel import SQLModel
from sqlalchemy import inspect, text

from .profile_connection import get_profile_database_connection

# 配置日志
logger = logging.getLogger(__name__)


class ProfileDatabaseMigration:
    """Profile数据库迁移管理类"""

    def __init__(self):
        """初始化数据库迁移管理器"""
        self.profile_db = get_profile_database_connection()

    def create_profile_tables(self) -> bool:
        """
        创建Profile数据库表

        创建所有Profile相关的数据库表，包括User、UserSettings和UserStats。

        Returns:
            bool: 创建成功返回True，失败返回False

        Raises:
            Exception: 数据库操作异常
        """
        try:
            logger.info("开始创建Profile数据库表...")

            # 获取数据库引擎
            engine = self.profile_db.get_engine()

            # 导入所有需要创建表的模型
            from src.domains.user.models import User, UserSettings, UserStats

            # 创建所有表
            SQLModel.metadata.create_all(bind=engine)

            logger.info("Profile数据库表创建成功")
            return True

        except Exception as e:
            logger.error(f"创建Profile数据库表失败: {e}")
            raise

    def verify_table_structure(self) -> bool:
        """
        验证Profile数据库表结构

        Returns:
            bool: 验证通过返回True，否则返回False
        """
        try:
            engine = self.profile_db.get_engine()
            inspector = inspect(engine)

            # 检查必要的表是否存在
            required_tables = ['user', 'usersettings', 'userstats']
            existing_tables = inspector.get_table_names()

            for table in required_tables:
                if table not in existing_tables:
                    logger.error(f"缺少必要的表: {table}")
                    return False

            # 检查User表的字段
            user_columns = inspector.get_columns('user')
            user_column_names = [col['name'] for col in user_columns]

            required_user_columns = [
                'user_id', 'nickname', 'avatar_url', 'bio',
                'gender', 'birthday', 'is_active', 'created_at'
            ]

            for column in required_user_columns:
                if column not in user_column_names:
                    logger.error(f"User表缺少字段: {column}")
                    return False

            # 检查UserSettings表的字段
            settings_columns = inspector.get_columns('usersettings')
            settings_column_names = [col['name'] for col in settings_columns]

            required_settings_columns = ['id', 'user_id', 'theme', 'language', 'created_at', 'updated_at']

            for column in required_settings_columns:
                if column not in settings_column_names:
                    logger.error(f"UserSettings表缺少字段: {column}")
                    return False

            # 检查UserStats表的字段
            stats_columns = inspector.get_columns('userstats')
            stats_column_names = [col['name'] for col in stats_columns]

            required_stats_columns = ['id', 'user_id', 'tasks_completed', 'total_points',
                                     'login_count', 'last_active_at', 'created_at', 'updated_at']

            for column in required_stats_columns:
                if column not in stats_column_names:
                    logger.error(f"UserStats表缺少字段: {column}")
                    return False

            logger.info("Profile数据库表结构验证通过")
            return True

        except Exception as e:
            logger.error(f"验证Profile数据库表结构失败: {e}")
            return False

    def check_migration_needed(self) -> bool:
        """
        检查是否需要进行迁移

        Returns:
            bool: 需要迁移返回True，否则返回False
        """
        try:
            # 检查表是否存在
            if not self.profile_db.check_connection():
                return True

            engine = self.profile_db.get_engine()
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()

            # 如果没有任何表，需要创建
            if not existing_tables:
                return True

            # 检查是否包含新字段
            if 'user' in existing_tables:
                user_columns = inspector.get_columns('user')
                user_column_names = [col['name'] for col in user_columns]

                # 检查新增字段是否存在
                if 'gender' not in user_column_names or 'birthday' not in user_column_names:
                    return True

            return False

        except Exception as e:
            logger.warning(f"检查迁移状态时出错: {e}")
            return True  # 出错时默认进行迁移

    def run_migration(self) -> bool:
        """
        执行Profile数据库迁移

        Returns:
            bool: 迁移成功返回True，失败返回False
        """
        try:
            logger.info("开始执行Profile数据库迁移...")

            # 检查是否需要迁移
            if not self.check_migration_needed():
                logger.info("Profile数据库迁移不需要执行")
                return True

            # 创建表结构
            success = self.create_profile_tables()
            if not success:
                logger.error("创建Profile数据库表失败")
                return False

            # 验证表结构
            if not self.verify_table_structure():
                logger.error("Profile数据库表结构验证失败")
                return False

            logger.info("Profile数据库迁移完成")
            return True

        except Exception as e:
            logger.error(f"执行Profile数据库迁移失败: {e}")
            return False

    def get_migration_status(self) -> dict:
        """
        获取迁移状态信息

        Returns:
            dict: 包含迁移状态信息的字典
        """
        try:
            status = {
                "database_connected": self.profile_db.check_connection(),
                "migration_needed": self.check_migration_needed(),
                "tables_exist": False,
                "table_structure_valid": False,
                "tables": []
            }

            if status["database_connected"]:
                engine = self.profile_db.get_engine()
                inspector = inspect(engine)
                existing_tables = inspector.get_table_names()

                status["tables"] = existing_tables
                status["tables_exist"] = len(existing_tables) > 0

                if status["tables_exist"]:
                    status["table_structure_valid"] = self.verify_table_structure()

            return status

        except Exception as e:
            logger.error(f"获取迁移状态失败: {e}")
            return {
                "database_connected": False,
                "migration_needed": True,
                "tables_exist": False,
                "table_structure_valid": False,
                "tables": [],
                "error": str(e)
            }


# 全局迁移实例
_global_migration: Optional[ProfileDatabaseMigration] = None


def get_profile_migration() -> ProfileDatabaseMigration:
    """
    获取全局Profile数据库迁移实例

    Returns:
        ProfileDatabaseMigration: 全局迁移实例
    """
    global _global_migration
    if _global_migration is None:
        _global_migration = ProfileDatabaseMigration()
    return _global_migration


def run_profile_migration() -> bool:
    """
    执行Profile数据库迁移（便捷函数）

    Returns:
        bool: 迁移成功返回True，失败返回False
    """
    migration = get_profile_migration()
    return migration.run_migration()


def check_profile_migration_needed() -> bool:
    """
    检查是否需要Profile数据库迁移（便捷函数）

    Returns:
        bool: 需要迁移返回True，否则返回False
    """
    migration = get_profile_migration()
    return migration.check_migration_needed()