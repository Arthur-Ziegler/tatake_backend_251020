#!/usr/bin/env python3
"""
TaKeKe数据库表初始化脚本

本脚本用于创建TaKeKe项目所需的所有数据库表，包括：
1. 用户管理相关表
2. 任务管理相关表
3. 专注会话相关表
4. 奖励系统相关表
5. 积分系统相关表
6. AI对话相关表
7. 认证系统相关表

使用方法：
    uv run python init_database.py

注意事项：
- 本脚本会删除现有表并重新创建
- 仅用于开发环境测试
- 生产环境请使用数据库迁移工具
"""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.append('.')

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

from src.models.base_model import BaseSQLModel
from src.models.user import User
from src.models.auth import TokenBlacklist, SmsVerification
from src.models.task import Task, TaskTop3
from src.models.focus import FocusSession
from src.models.chat import ChatSession, ChatMessage


class DatabaseInitializer:
    """
    数据库初始化器

    负责创建所有数据库表并插入初始测试数据。
    """

    def __init__(self):
        """初始化数据库连接"""
        # 使用同步SQLite引擎
        self.engine = create_engine("sqlite:///tatake.db")

    def create_all_tables(self):
        """
        创建所有数据库表

        按照依赖关系顺序创建表结构。
        """
        print("🔧 开始创建数据库表...")

        try:
            # 创建所有表
            BaseSQLModel.metadata.create_all(self.engine)

            print("✅ 所有数据库表创建成功")

        except Exception as e:
            print(f"❌ 创建数据库表失败: {str(e)}")
            raise

    def insert_initial_data(self):
        """
        插入初始测试数据

        为各个模块插入必要的初始数据。
        """
        print("📝 开始插入初始数据...")

        with Session(self.engine) as session:
            try:
                # 1. 插入测试用户数据
                self._insert_test_users(session)

                session.commit()
                print("✅ 初始数据插入成功")

            except Exception as e:
                session.rollback()
                print(f"❌ 插入初始数据失败: {str(e)}")
                raise

    def _insert_test_users(self, session: Session):
        """
        插入测试用户数据

        创建用于测试的示例用户。
        """
        print("👤 插入测试用户数据...")

        test_users = [
            User(
                nickname="测试用户1",
                phone="13800138001",
                is_guest=False
            ),
            User(
                nickname="测试用户2",
                email="test2@example.com",
                is_guest=False
            ),
            User(
                nickname="游客用户",
                is_guest=True
            )
        ]

        for user in test_users:
            session.add(user)

        print(f"   ✅ 插入 {len(test_users)} 个测试用户")

    def verify_tables(self):
        """
        验证表创建情况

        检查所有表是否正确创建。
        """
        print("🔍 验证数据库表...")

        with Session(self.engine) as session:
            result = session.exec(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            existing_tables = [row[0] for row in result.fetchall()]

        print(f"📋 数据库表统计:")
        print(f"   实际表数: {len(existing_tables)}")
        print(f"   表列表: {sorted(existing_tables)}")

        return len(existing_tables) > 0

    def close(self):
        """关闭数据库连接"""
        # SQLite不需要显式关闭
        pass


def main():
    """
    主函数

    执行完整的数据库初始化流程。
    """
    print("=" * 60)
    print("TaKeKe数据库表初始化脚本")
    print("=" * 60)

    initializer = DatabaseInitializer()

    try:
        # 1. 创建所有表
        initializer.create_all_tables()

        # 2. 插入初始数据
        initializer.insert_initial_data()

        # 3. 验证表创建情况
        success = initializer.verify_tables()

        print("\n" + "=" * 60)
        if success:
            print("🎉 数据库初始化完成！")
            print("✅ 所有表已创建")
            print("✅ 初始数据已插入")
            print("✅ 系统可以开始使用")
        else:
            print("❌ 数据库初始化失败")
            print("💡 请检查错误信息并重试")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 数据库初始化过程中发生错误:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)

    finally:
        initializer.close()


if __name__ == "__main__":
    main()