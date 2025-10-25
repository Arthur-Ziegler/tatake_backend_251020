"""
PostgreSQL Schema分离的领域数据库管理器

基于SQLAlchemy的schema_translate_map功能实现多租户和领域隔离。
支持动态schema切换、跨领域事务、连接池管理。

核心特性：
1. Schema按领域分离：auth_domain, task_domain, reward_domain等
2. 动态schema翻译：支持运行时切换schema
3. 跨领域事务：支持多个schema的原子操作
4. 连接池优化：共享连接池，提高性能
5. 多租户支持：通过schema_translate_map实现租户隔离

作者：TaKeKe团队
版本：v1.0
"""

import os
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from pydantic_settings import BaseSettings


class SchemaDatabaseSettings(BaseSettings):
    """Schema数据库配置"""

    # 数据库连接配置
    database_url: str = "postgresql://tatake_app:password@localhost:5432/tatake"
    debug: bool = False

    # Schema配置
    schemas: Dict[str, str] = {
        'auth': 'auth_domain',
        'task': 'task_domain',
        'reward': 'reward_domain',
        'points': 'points_domain',
        'top3': 'top3_domain',
        'focus': 'focus_domain'
    }

    # 连接池配置
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600

    # 多租户配置
    multi_tenant_enabled: bool = False
    tenant_schema_pattern: str = "{tenant}_domain"

    class Config:
        env_file = ".env"


class SchemaDatabaseManager:
    """PostgreSQL Schema数据库管理器"""

    def __init__(self, settings: Optional[SchemaDatabaseSettings] = None):
        self.settings = settings or SchemaDatabaseSettings()
        self.engines: Dict[str, Engine] = {}
        self.session_factories: Dict[str, sessionmaker] = {}

        # 创建主引擎（共享连接池）
        self._create_main_engine()

    def _create_main_engine(self):
        """创建主数据库引擎"""
        self.main_engine = create_engine(
            self.settings.database_url,
            echo=self.settings.debug,
            poolclass=QueuePool,
            pool_size=self.settings.pool_size,
            max_overflow=self.settings.max_overflow,
            pool_timeout=self.settings.pool_timeout,
            pool_recycle=self.settings.pool_recycle,
            # PostgreSQL优化参数
            connect_args={
                "application_name": "tatake_backend",
                "connect_timeout": 10,
                "options": "-cdefault_transaction_isolation=read_committed"
            }
        )

    def get_schema_session(self, domain: str, tenant_id: Optional[str] = None) -> Session:
        """
        获取特定领域的数据库会话

        Args:
            domain: 领域名称（auth, task, reward等）
            tenant_id: 租户ID（多租户模式下使用）

        Returns:
            Session: 配置了schema翻译的数据库会话
        """
        if domain not in self.settings.schemas:
            raise ValueError(f"Unknown domain: {domain}")

        # 构建schema翻译映射
        schema_translate_map = self._build_schema_translate_map(domain, tenant_id)

        # 创建会话工厂
        if domain not in self.session_factories:
            self.session_factories[domain] = sessionmaker(
                bind=self.main_engine,
                autocommit=False,
                autoflush=False
            )

        # 获取会话并应用schema翻译
        session = self.session_factories[domain]()

        # 应用schema翻译映射
        if schema_translate_map:
            session = session.execution_options(
                schema_translate_map=schema_translate_map
            )

        return session

    def _build_schema_translate_map(self, domain: str, tenant_id: Optional[str] = None) -> Dict[str, str]:
        """构建schema翻译映射"""
        if not self.settings.multi_tenant_enabled or not tenant_id:
            # 单租户模式：直接使用预定义schema
            schema_name = self.settings.schemas[domain]
            return {None: schema_name}

        # 多租户模式：动态生成schema名称
        tenant_schema = self.settings.tenant_schema_pattern.format(tenant=tenant_id)
        return {None: tenant_schema}

    @contextmanager
    def get_domain_session(self, domain: str, tenant_id: Optional[str] = None):
        """
        获取领域会话的上下文管理器

        Args:
            domain: 领域名称
            tenant_id: 租户ID（可选）

        Yields:
            Session: 数据库会话
        """
        session = None
        try:
            session = self.get_schema_session(domain, tenant_id)
            yield session
            session.commit()
        except Exception:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()

    @contextmanager
    def cross_domain_transaction(self, domains: list[str], tenant_id: Optional[str] = None):
        """
        跨领域事务管理器

        Args:
            domains: 需要参与事务的领域列表
            tenant_id: 租户ID（可选）

        Yields:
            Dict[str, Session]: 各领域的会话字典
        """
        sessions = {}
        try:
            # 为每个领域创建会话
            for domain in domains:
                sessions[domain] = self.get_schema_session(domain, tenant_id)

            # 开始事务
            for session in sessions.values():
                session.begin()

            yield sessions

            # 提交所有会话
            for session in sessions.values():
                session.commit()

        except Exception:
            # 回滚所有会话
            for session in sessions.values():
                try:
                    session.rollback()
                except Exception:
                    pass  # 忽略回滚时的错误
            raise
        finally:
            # 关闭所有会话
            for session in sessions.values():
                try:
                    session.close()
                except Exception:
                    pass

    def create_tenant_schemas(self, tenant_id: str) -> bool:
        """
        为新租户创建Schema（多租户模式）

        Args:
            tenant_id: 租户ID

        Returns:
            bool: 创建是否成功
        """
        if not self.settings.multi_tenant_enabled:
            return False

        try:
            with self.main_engine.connect() as conn:
                for domain in self.settings.schemas.keys():
                    schema_name = self.settings.tenant_schema_pattern.format(tenant=tenant_id)
                    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                conn.commit()
            return True
        except Exception:
            return False

    def get_tenant_schemas(self, tenant_id: str) -> Dict[str, str]:
        """
        获取租户的Schema映射（多租户模式）

        Args:
            tenant_id: 租户ID

        Returns:
            Dict[str, str]: 领域到Schema的映射
        """
        if not self.settings.multi_tenant_enabled:
            return self.settings.schemas

        return {
            domain: self.settings.tenant_schema_pattern.format(tenant=tenant_id)
            for domain in self.settings.schemas.keys()
        }

    def inspect_schema(self, domain: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        检查Schema的表结构信息

        Args:
            domain: 领域名称
            tenant_id: 租户ID（可选）

        Returns:
            Dict[str, Any]: Schema信息
        """
        schema_name = self._build_schema_translate_map(domain, tenant_id).get(None)

        if not schema_name:
            return {}

        try:
            with self.main_engine.connect() as conn:
                # 获取表列表
                tables_result = conn.execute(
                    f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema_name}'"
                )
                tables = [row[0] for row in tables_result.fetchall()]

                # 获取表数量统计
                table_count_result = conn.execute(
                    f"SELECT COUNT(*) FROM pg_tables WHERE schemaname = '{schema_name}'"
                )
                table_count = table_count_result.scalar()

                return {
                    "schema_name": schema_name,
                    "table_count": table_count,
                    "tables": tables
                }
        except Exception as e:
            return {"error": str(e)}

    def close(self):
        """关闭所有连接和引擎"""
        for engine in self.engines.values():
            engine.dispose()
        self.main_engine.dispose()


# 全局数据库管理器实例
db_manager = SchemaDatabaseManager()


# 便捷函数
def get_domain_session(domain: str, tenant_id: Optional[str] = None) -> Session:
    """获取领域会话的便捷函数"""
    return db_manager.get_schema_session(domain, tenant_id)


@contextmanager
def domain_session(domain: str, tenant_id: Optional[str] = None):
    """领域会话上下文管理器的便捷函数"""
    with db_manager.get_domain_session(domain, tenant_id) as session:
        yield session


@contextmanager
def cross_domains(domains: list[str], tenant_id: Optional[str] = None):
    """跨领域事务上下文管理器的便捷函数"""
    with db_manager.cross_domain_transaction(domains, tenant_id) as sessions:
        yield sessions