"""
测试PointsService功能

测试积分流水管理和余额计算功能。

测试覆盖：
1. 积分余额计算准确性
2. 积分流水记录创建功能
3. 积分统计查询功能
4. 事务管理正确性
5. 异常处理完整性

作者：TaKeKe团队
版本：1.0.0（Phase 1 Day 2）
"""

import pytest
from datetime import datetime, timezone, date, timedelta
from uuid import uuid4, UUID
from decimal import Decimal

from sqlmodel import Session, select, text
from sqlalchemy.exc import SQLAlchemyError

from src.domains.points.models import PointsTransaction
from src.domains.points.service import PointsService


class TestPointsService:
    """测试PointsService功能"""

    def test_calculate_balance_zero_points(self, test_db_session: Session):
        """测试零积分余额计算"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        balance = service.calculate_balance(user_id)

        assert balance == 0, f"Expected balance 0, got {balance}"

    def test_calculate_balance_with_transactions(self, test_db_session: Session):
        """测试有积分记录时的余额计算"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加一些积分记录
        service.add_points(user_id, 100, "task_complete", uuid4())
        service.add_points(user_id, -20, "redemption", uuid4())
        service.add_points(user_id, 50, "lottery", uuid4())

        balance = service.calculate_balance(user_id)

        expected_balance = 100 - 20 + 50  # 100 - 20 + 50 = 130

        assert balance == expected_balance, f"Expected balance {expected_balance}, got {balance}"

    def test_add_points(self, test_db_session: Session):
        """测试添加积分记录功能"""
        user_id = uuid4()
        amount = 25
        source_type = "test_reward"
        source_id = uuid4()

        service = PointsService(test_db_session)

        # 验证添加前余额
        balance_before = service.calculate_balance(user_id)

        # 添加积分记录
        transaction = service.add_points(user_id, amount, source_type, source_id)

        # 验证添加后余额
        balance_after = service.calculate_balance(user_id)

        # 验证交易记录
        assert transaction.user_id == str(user_id)
        assert transaction.amount == amount
        assert transaction.source_type == source_type
        assert transaction.source_id == str(source_id)
        assert transaction.created_at is not None

        # 验证余额变化
        assert balance_after == balance_before + amount, f"Balance after {balance_after} != before {balance_before} + {amount}"

    def test_add_points_with_negative_amount(self, test_db_session: Session):
        """测试添加负数积分记录应该成功（消费）"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加负数积分应该成功（代表消费）
        transaction = service.add_points(user_id, -10, "test_negative", uuid4())

        # 验证交易记录
        assert transaction.amount == -10
        assert transaction.source_type == "test_negative"
        assert transaction.user_id == str(user_id)

    def test_get_statistics_empty_data(self, test_db_session: Session):
        """测试空数据的积分统计查询"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 测试没有数据的统计查询
        end_date = date.today()
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()

        stats = service.get_statistics(user_id, start_date, end_date)

        # 空数据应该返回空列表
        assert stats == [], f"Expected empty list, got {stats}"

    def test_get_statistics_with_data(self, test_db_session: Session):
        """测试有数据的积分统计查询"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加测试数据
        service.add_points(user_id, 100, "task_complete", uuid4())
        service.add_points(user_id, -20, "redemption", uuid4())
        service.add_points(user_id, 50, "lottery", uuid4())

        # 测试统计查询
        end_date = date.today()
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).date()

        stats = service.get_statistics(user_id, start_date, end_date)

        # 验证统计结果
        assert stats is not None, "Statistics should not be None"
        assert isinstance(stats, list), "Statistics should be a list"

        # 验证统计数据结构
        for stat in stats:
            assert "source_type" in stat, "Stat should have source_type"
            assert "income" in stat, "Stat should have income"
            assert "expense" in stat, "Stat should have expense"
            assert "net_change" in stat, "Stat should have net_change"

        # 验证task_complete统计
        task_complete_stats = next((s for s in stats if s["source_type"] == "task_complete"), None)
        assert task_complete_stats["income"] == 100, "Task complete income should be 100"
        assert task_complete_stats["expense"] == 0, "Task complete expense should be 0"
        assert task_complete_stats["net_change"] == 100, "Task complete net change should be 100"

        # 验证redemption统计
        redemption_stats = next((s for s in stats if s["source_type"] == "redemption"), None)
        assert redemption_stats["income"] == 0, "Redemption income should be 0"
        assert redemption_stats["expense"] == 20, "Redemption expense should be 20"
        assert redemption_stats["net_change"] == -20, "Redemption net change should be -20"

        # 验证lottery统计
        lottery_stats = next((s for s in stats if s["source_type"] == "lottery"), None)
        assert lottery_stats["income"] == 50, "Lottery income should be 50"
        assert lottery_stats["expense"] == 0, "Lottery expense should be 0"
        assert lottery_stats["net_change"] == 50, "Lottery net change should be 50"

    def test_get_transactions(self, test_db_session: Session):
        """测试获取积分流水记录功能"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加测试数据
        service.add_points(user_id, 25, "test_transaction", uuid4())
        service.add_points(user_id, -10, "test_refund", uuid4())

        # 获取所有交易记录
        transactions = service.get_transactions(user_id, limit=10, offset=0)

        # 验证结果
        assert len(transactions) == 2, f"Expected 2 transactions, got {len(transactions)}"

        # 验证交易按创建时间降序排列
        for i in range(len(transactions) - 1):
            if i > 0:
                assert transactions[i]['created_at'] <= transactions[i-1]['created_at'], f"Transaction {i} should be newer than {i-1}"

        # 验证有正负交易
        amounts = [t['amount'] for t in transactions]
        assert 25 in amounts, "Should have transaction with amount 25"
        assert -10 in amounts, "Should have transaction with amount -10"
        assert len(set(t['source_type'] for t in transactions)) == 2, "Should have two different source types"

    def test_get_transactions_pagination(self, test_db_session: Session):
        """测试积分流水记录的分页功能"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        # 添加20个测试交易
        for i in range(20):
            service.add_points(user_id, 1, f"test_pagination_{i}", uuid4())

        # 测试分页：第一页（offset=0, limit=10）
        page1 = service.get_transactions(user_id, limit=10, offset=0)
        assert len(page1) == 10, "First page should have 10 transactions"

        # 测试分页：第二页（offset=10, limit=10）
        page2 = service.get_transactions(user_id, limit=10, offset=10)
        assert len(page2) == 10, "Second page should have 10 transactions"

        # 测试分页：请求超出范围
        page3 = service.get_transactions(user_id, limit=10, offset=30)
        assert len(page3) == 0, "Third page should be empty when requesting beyond available data"

    def test_transaction_scope_success(self, test_db_session: Session):
        """测试事务管理器功能"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        with service.transaction_scope():
            # 在事务中添加多个积分记录
            service.add_points(user_id, 10, "test_scope_1", uuid4())
            service.add_points(user_id, 5, "test_scope_2", uuid4())

        # 验证事务外查询应该看不到未提交的记录
        balance_in_transaction = service.calculate_balance(user_id)

        # 事务内的余额应该包含未提交的记录
        assert balance_in_transaction == 15, f"Balance in transaction should be 15"

        # 事务提交后记录应该可见
        balance_after_commit = service.calculate_balance(user_id)

        # 事务外查询应该看到所有记录
        assert balance_after_commit == 15, f"Balance after commit should be 15"

    def test_transaction_scope_rollback(self, test_db_session: Session):
        """测试事务管理器回滚功能"""
        user_id = uuid4()
        service = PointsService(test_db_session)

        try:
            with service.transaction_scope():
                # 添加积分记录
                service.add_points(user_id, 5, "test_rollback", uuid4())

                # 模拟异常，触发回滚
                raise ValueError("Simulated error for rollback testing")

            assert False, "Transaction should have been rolled back"

        except ValueError:
            # 验证回滚后余额保持不变
            balance_after_rollback = service.calculate_balance(user_id)
            # 回滚应该导致积分记录被丢弃
            assert balance_after_rollback == 0, f"Balance after rollback should be 0"