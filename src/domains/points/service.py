"""
Points领域Service层

提供积分流水管理和余额计算的核心业务逻辑。

核心功能：
1. 积分余额计算：基于纯SQL聚合查询
2. 积分流水记录：创建和管理积分交易记录
3. 积分统计：按来源类型和时间范围统计
4. 事务管理：确保操作的原子性

设计原则：
1. 纯SQL聚合：不使用缓存或优化，保持简单实现
2. 直接数据库访问：不使用额外Repository层
3. 事务边界管理：关键操作使用事务，普通查询不需要
4. 详细错误处理：提供足够的错误信息用于问题定位

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import logging
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from contextlib import contextmanager

from sqlmodel import Session, text, select
from sqlalchemy.exc import SQLAlchemyError

from .models import PointsTransaction


class PointsService:
    """
    积分系统服务层

    提供积分流水管理和余额计算功能，基于纯SQL聚合查询实现。
    所有积分变动都通过points_transactions表记录，支持完整的积分追踪。
    """

    def __init__(self, session: Session):
        """
        初始化积分服务

        Args:
            session (Session): 数据库会话
        """
        self.session = session
        self.logger = logging.getLogger(__name__)

    def calculate_balance(self, user_id) -> int:
        """
        计算用户积分余额

        使用纯SQL聚合查询计算用户总积分余额：
        SELECT COALESCE(SUM(amount), 0)
        FROM points_transactions
        WHERE user_id = :user_id

        Args:
            user_id (str): 用户ID

        Returns:
            int: 积分余额
        """
        self.logger.info(f"Calculating balance for user {user_id}")

        try:
            result = self.session.execute(
                text("SELECT COALESCE(SUM(amount), 0) FROM points_transactions WHERE user_id = :user_id"),
                {"user_id": str(user_id)}
            ).scalar()

            balance = result or 0
            self.logger.info(f"Balance calculated for user {user_id}: {balance}")

            return balance

        except SQLAlchemyError as e:
            self.logger.error(f"Database error calculating balance for user {user_id}: {e}")
            raise

    def get_balance(self, user_id) -> int:
        """
        获取用户积分余额 (别名方法)

        Args:
            user_id (str): 用户ID

        Returns:
            int: 积分余额
        """
        return self.calculate_balance(user_id)

    def add_points(
        self,
        user_id,
        amount: int,
        source_type: str,
        source_id: Optional[str] = None,
        transaction_group: Optional[str] = None
    ):
        """
        添加积分流水记录

        为用户的积分变动创建记录，支持不同来源类型和事务组。

        Args:
            user_id (str): 用户ID
            amount (int): 积分数量，正数表示获得，负数表示消费
            source_type (str): 来源类型，如task_complete, top3_cost, lottery_points等
            source_id (Optional[UUID]): 来源对象ID，如任务ID、配方ID等
            transaction_group (Optional[str]): 事务组ID，用于关联同一操作的多个记录

        Returns:
            PointsTransaction: 创建的积分记录
        """
        self.logger.info(f"Adding {amount} points for user {user_id}, source_type: {source_type}")

        # 不限制积分数量，允许正数（获得）和负数（消费）

        try:
            transaction = PointsTransaction(
                user_id=str(user_id),
                amount=amount,
                source_type=source_type,
                source_id=str(source_id) if source_id else None,
                transaction_group=transaction_group,
                created_at=datetime.now(timezone.utc)
            )

            self.session.add(transaction)
            self.session.flush()  # 获取ID
            self.session.commit()  # 立即提交事务确保积分记录持久化

            self.logger.info(f"Added {amount} points transaction for user {user_id}, transaction ID: {transaction.id}")

            return transaction

        except SQLAlchemyError as e:
            self.logger.error(f"Database error adding points for user {user_id}: {e}")
            self.session.rollback()
            raise

    def get_statistics(self, user_id, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        获取用户积分统计

        使用纯SQL聚合查询计算按来源类型和日期范围的积分统计：
        SELECT
            source_type,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
            SUM(amount) as net_change
        FROM points_transactions
        WHERE user_id = :user_id
        AND DATE(created_at) BETWEEN :start_date AND :end_date
        GROUP BY source_type

        Args:
            user_id (str): 用户ID
            start_date (Optional[date]): 开始日期
            end_date (Optional[date]): 结束日期

        Returns:
            List[Dict[str, Any]]: 统计结果
        """
        self.logger.info(f"Getting points statistics for user {user_id}, from {start_date} to {end_date}")

        try:
            query_params = {
                "user_id": str(user_id),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }

            # 如果没有指定日期范围，默认查询最近30天
            if not start_date or not end_date:
                thirty_days_ago = (datetime.now(timezone.utc) - datetime.timedelta(days=30)).date().isoformat()
                query_params["start_date"] = thirty_days_ago

            result = self.session.execute(
                text("""
                    SELECT
                        source_type,
                        SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
                        SUM(amount) as net_change
                    FROM points_transactions
                    WHERE user_id = :user_id
                    AND DATE(created_at) BETWEEN COALESCE(:start_date, DATE('now', '-30 days')) AND COALESCE(:end_date, DATE('now'))
                    GROUP BY source_type
                    ORDER BY net_change DESC
                """),
                query_params
            ).fetchall()

            statistics = [
                {
                    "source_type": row[0],
                    "income": row[1],
                    "expense": row[2],
                    "net_change": row[3]
                }
                for row in result
            ]

            self.logger.info(f"Retrieved {len(statistics)} statistics entries for user {user_id}")

            return statistics

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting statistics for user {user_id}: {e}")
            raise

    def get_transactions(self, user_id, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户积分流水记录

        Args:
            user_id (str): 用户ID
            limit (int): 限制数量
            offset (int): 偏移数量

        Returns:
            List[Dict[str, Any]]: 积分交易记录字典列表
        """
        self.logger.info(f"Getting transactions for user {user_id}, limit: {limit}, offset: {offset}")

        try:
            statement = (
                select(PointsTransaction)
                .where(PointsTransaction.user_id == str(user_id))
                .order_by(PointsTransaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = list(self.session.execute(statement).scalars().all())

            # 转换为字典列表
            transactions = []
            for transaction in result:
                transactions.append({
                    "id": str(transaction.id),
                    "user_id": str(transaction.user_id),
                    "amount": transaction.amount,
                    "source_type": transaction.source_type,
                    "source_id": transaction.source_id,
                    "created_at": transaction.created_at
                })

            self.logger.info(f"Retrieved {len(transactions)} transactions for user {user_id}")

            return transactions

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting transactions for user {user_id}: {e}")
            raise

    @contextmanager
    def transaction_scope(self):
        """
        简化的事务管理器

        使用上下文管理器确保关键操作的原子性。
        仅在需要保证一致性的操作中使用。
        """
        self.logger.debug("Starting transaction scope")

        try:
            with self.session.begin():
                yield self.session
                self.logger.debug("Transaction committed successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Transaction failed: {e}")
            self.session.rollback()
            raise
        finally:
            self.logger.debug("Transaction scope ended")