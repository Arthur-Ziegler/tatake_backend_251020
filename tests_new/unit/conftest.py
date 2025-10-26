"""
单元测试配置文件

提供单元测试专用的fixtures和配置。
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any

@pytest.fixture(scope="function")
def mock_session():
    """模拟数据库会话"""
    session = Mock()
    session.add = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.exec = Mock()
    session.query = Mock()
    session.refresh = Mock()
    session.delete = Mock()
    return session

@pytest.fixture(scope="function")
def sample_user_id():
    """示例用户ID"""
    return str(uuid4())

@pytest.fixture(scope="function")
def current_datetime():
    """当前时间"""
    return datetime.now(timezone.utc)

@pytest.fixture(scope="function")
def mock_repository():
    """模拟基础仓储"""
    repo = Mock()
    repo.create = Mock(return_value=Mock())
    repo.get_by_id = Mock(return_value=None)
    repo.update = Mock(return_value=Mock())
    repo.delete = Mock(return_value=True)
    repo.list = Mock(return_value=[])
    return repo

@pytest.fixture(scope="function")
def mock_service():
    """模拟基础服务"""
    service = Mock()
    service.create = Mock(return_value=Mock())
    service.get = Mock(return_value=None)
    service.update = Mock(return_value=Mock())
    service.delete = Mock(return_value=True)
    service.list = Mock(return_value=[])
    return service