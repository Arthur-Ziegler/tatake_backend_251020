"""
Task领域数据库配置

提供Task领域的数据库操作相关功能，包括：
1. 数据库表创建和管理
2. 数据库连接检查
3. 测试数据初始化
4. 数据库迁移支持

设计原则：
1. 复用现有数据库连接配置
2. 保持与auth领域的数据库配置一致
3. 支持开发和生产环境
4. 提供完整的错误处理

功能特性：
- 自动创建tasks表
- 数据库连接健康检查
- 支持测试数据初始化
- 数据库信息查询

作者：TaKeKe团队
版本：1.0.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import text, inspect
from sqlmodel import SQLModel

# 导入数据库连接
from src.database.connection import get_engine, get_session
from .models import Task

# 配置日志
logger = logging.getLogger(__name__)


def create_tables() -> bool:
    """
    创建Task领域相关的数据库表

    创建Task模型对应的数据表，包括所有索引和约束。
    如果表已存在，不会重复创建。

    Returns:
        bool: 创建成功返回True，失败返回False

    Raises:
        Exception: 数据库操作异常
    """
    try:
        engine = get_engine()

        # 创建所有表
        SQLModel.metadata.create_all(engine)

        logger.info("Task领域数据库表创建成功")
        return True

    except Exception as e:
        logger.error(f"创建Task领域数据库表失败: {e}")
        raise


def check_connection() -> bool:
    """
    检查数据库连接状态

    执行简单的查询来验证数据库连接是否正常。

    Returns:
        bool: 连接正常返回True，否则返回False
    """
    try:
        engine = get_engine()

        with engine.connect() as connection:
            # 执行简单查询测试连接
            result = connection.execute(text("SELECT 1"))
            result.fetchone()

        return True

    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False


def get_database_info() -> Dict[str, Any]:
    """
    获取Task领域数据库信息

    返回Task领域相关的数据库状态和统计信息。

    Returns:
        Dict[str, Any]: 数据库信息字典
    """
    try:
        engine = get_engine()

        with engine.connect() as connection:
            # 检查表是否存在
            inspector = inspect(engine)
            table_exists = inspector.has_table('tasks')

            if not table_exists:
                return {
                    "status": "no_tables",
                    "tasks_table_exists": False,
                    "connection_status": "connected",
                    "message": "tasks表不存在，需要运行数据库迁移"
                }

            # 获取表的统计信息
            result = connection.execute(text("""
                SELECT
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN is_deleted = false THEN 1 END) as active_tasks,
                    COUNT(CASE WHEN is_deleted = true THEN 1 END) as deleted_tasks,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks
                FROM tasks
            """))

            stats = result.fetchone()._asdict()

            # 获取索引信息
            indexes = inspector.get_indexes('tasks')
            index_names = [idx['name'] for idx in indexes]

            # 获取外键信息
            foreign_keys = inspector.get_foreign_keys('tasks')
            fk_names = [fk['constrained_columns'] for fk in foreign_keys]

            return {
                "status": "healthy",
                "tasks_table_exists": True,
                "connection_status": "connected",
                "statistics": {
                    "total_tasks": stats['total_tasks'],
                    "active_tasks": stats['active_tasks'],
                    "deleted_tasks": stats['deleted_tasks'],
                    "pending_tasks": stats['pending_tasks'],
                    "in_progress_tasks": stats['in_progress_tasks'],
                    "completed_tasks": stats['completed_tasks']
                },
                "schema": {
                    "table_name": "tasks",
                    "indexes": index_names,
                    "foreign_keys": fk_names
                }
            }

    except Exception as e:
        logger.error(f"获取数据库信息失败: {e}")
        return {
            "status": "error",
            "tasks_table_exists": False,
            "connection_status": "disconnected",
            "error": str(e),
            "message": "无法获取数据库信息"
        }


def initialize_test_data(user_id: str, num_tasks: int = 10) -> bool:
    """
    初始化测试数据

    为指定用户创建测试任务数据。仅在开发环境中使用。

    Args:
        user_id (str): 用户ID
        num_tasks (int): 要创建的任务数量，默认10个

    Returns:
        bool: 初始化成功返回True，失败返回False

    Raises:
        Exception: 数据库操作异常
    """
    try:
        from uuid import UUID
        from datetime import datetime, timezone, timedelta
        import random

        # 检查是否为开发环境
        from src.api.config import config
        if not config.debug:
            logger.warning("测试数据初始化仅在开发环境中允许")
            return False

        user_uuid = UUID(user_id)

        with get_session() as session:
            # 检查是否已有测试数据
            existing_count = session.execute(
                text("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id"),
                {"user_id": str(user_uuid)}
            ).scalar()

            if existing_count > 0:
                logger.info(f"用户 {user_id} 已有 {existing_count} 个任务，跳过测试数据初始化")
                return True

            # 创建测试任务
            sample_titles = [
                "完成项目文档",
                "代码审查",
                "团队会议",
                "修复Bug",
                "功能开发",
                "性能优化",
                "单元测试",
                "部署准备",
                "客户沟通",
                "需求分析"
            ]

            sample_descriptions = [
                "这是任务的详细描述，包含具体的执行步骤和要求。",
                "需要仔细检查每个细节，确保质量符合标准。",
                "与团队成员协作，共同完成这个任务。",
                "遵循最佳实践，确保代码的可维护性。"
            ]

            sample_tags = [
                ["重要", "紧急"],
                ["开发", "技术"],
                ["文档", "编写"],
                ["测试", "质量"],
                ["会议", "沟通"],
                ["优化", "性能"],
                ["设计", "架构"]
            ]

            created_tasks = []

            for i in range(num_tasks):
                # 随机选择数据
                title = random.choice(sample_titles) + f" #{i+1}"
                description = random.choice(sample_descriptions)
                tags = random.choice(sample_tags)

                # 随机生成时间
                base_time = datetime.now(timezone.utc)
                created_at = base_time - timedelta(hours=random.randint(1, 24))
                updated_at = created_at + timedelta(minutes=random.randint(5, 60))

                due_date = base_time + timedelta(days=random.randint(1, 30))
                planned_start = base_time + timedelta(hours=random.randint(1, 12))
                planned_end = planned_start + timedelta(hours=random.randint(1, 8))

                # 创建任务
                task = Task(
                    user_id=user_uuid,
                    title=title,
                    description=description,
                    status=random.choice(list(TaskStatus)),
                    priority=random.choice(list(TaskPriority)),
                    tags=tags,
                    due_date=due_date,
                    planned_start_time=planned_start,
                    planned_end_time=planned_end,
                    created_at=created_at,
                    updated_at=updated_at
                )

                session.add(task)
                created_tasks.append(task)

            # 提交事务
            session.commit()

            logger.info(f"为用户 {user_id} 成功创建 {len(created_tasks)} 个测试任务")
            return True

    except Exception as e:
        logger.error(f"初始化测试数据失败: {e}")
        raise


def cleanup_test_data(user_id: str) -> bool:
    """
    清理测试数据

    删除指定用户的所有任务数据。仅在开发环境中使用。

    Args:
        user_id (str): 用户ID

    Returns:
        bool: 清理成功返回True，失败返回False
    """
    try:
        from uuid import UUID

        # 检查是否为开发环境
        from src.api.config import config
        if not config.debug:
            logger.warning("测试数据清理仅在开发环境中允许")
            return False

        user_uuid = UUID(user_id)

        with get_session() as session:
            # 软删除所有任务
            result = session.execute(
                text("UPDATE tasks SET is_deleted = true WHERE user_id = :user_id"),
                {"user_id": str(user_uuid)}
            )

            deleted_count = result.rowcount
            session.commit()

            logger.info(f"为用户 {user_id} 软删除了 {deleted_count} 个任务")
            return True

    except Exception as e:
        logger.error(f"清理测试数据失败: {e}")
        return False


def get_task_statistics(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    获取任务统计信息

    返回任务的详细统计数据，支持按用户筛选。

    Args:
        user_id (Optional[str]): 用户ID，如果提供则只统计该用户的任务

    Returns:
        Dict[str, Any]: 统计信息字典
    """
    try:
        with get_session() as session:
            # 构建查询条件
            where_clause = ""
            params = {}

            if user_id:
                where_clause = "WHERE user_id = :user_id AND is_deleted = false"
                params["user_id"] = user_id
            else:
                where_clause = "WHERE is_deleted = false"

            # 获取基础统计
            result = session.execute(text(f"""
                SELECT
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_priority_count,
                    COUNT(CASE WHEN priority = 'medium' THEN 1 END) as medium_priority_count,
                    COUNT(CASE WHEN priority = 'low' THEN 1 END) as low_priority_count,
                    COUNT(CASE WHEN due_date < NOW() AND status != 'completed' THEN 1 END) as overdue_count,
                    COUNT(CASE WHEN parent_id IS NULL THEN 1 END) as parent_task_count,
                    COUNT(CASE WHEN parent_id IS NOT NULL THEN 1 END) as subtask_count
                FROM tasks
                {where_clause}
            """), params)

            stats = result.fetchone()._asdict()

            # 获取最近活动统计
            recent_result = session.execute(text(f"""
                SELECT
                    COUNT(*) as tasks_created_today,
                    COUNT(*) as tasks_updated_today
                FROM tasks
                {where_clause}
                AND DATE(created_at) = CURRENT_DATE
            """), params)

            recent_stats = recent_result.fetchone()._asdict()

            return {
                "basic_statistics": stats,
                "recent_activity": recent_stats,
                "user_id": user_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

    except Exception as e:
        logger.error(f"获取任务统计信息失败: {e}")
        return {
            "error": str(e),
            "user_id": user_id,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# 数据库依赖函数，用于FastAPI
def get_task_session():
    """
    获取Task领域数据库会话

    用于FastAPI的依赖注入，提供数据库会话。

    Yields:
        Session: 数据库会话
    """
    with get_session() as session:
        yield session


# 初始化函数
def initialize_task_database():
    """
    初始化Task领域数据库

    在应用启动时调用，确保数据库表已创建。
    """
    try:
        if check_connection():
            create_tables()
            logger.info("Task领域数据库初始化完成")
        else:
            logger.error("Task领域数据库连接失败")
    except Exception as e:
        logger.error(f"Task领域数据库初始化失败: {e}")
        raise