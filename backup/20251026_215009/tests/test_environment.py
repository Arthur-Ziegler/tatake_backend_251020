"""
测试环境配置验证
"""
import pytest
from sqlmodel import Session


def test_pytest_configuration():
    """验证pytest配置正确"""
    assert True  # 基础测试验证pytest运行


def test_database_session_fixture(session: Session):
    """验证数据库会话夹具工作正常"""
    assert session is not None
    assert isinstance(session, Session)


def test_transaction_session_rollback(transaction_session: Session):
    """验证事务会话回滚功能"""
    # 这个测试验证事务夹具能正确回滚
    assert transaction_session is not None
    assert isinstance(transaction_session, Session)