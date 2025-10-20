"""
认证Repository简单测试

简化的测试，验证新的认证相关Repository能正确创建和基本功能。
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 直接测试导入，避免循环导入问题
def test_import_auth_repositories():
    """测试认证Repository模块导入"""
    try:
        from src.repositories.auth import (
            TokenBlacklistRepository,
            SmsVerificationRepository,
            UserSessionRepository,
            AuthLogRepository
        )
        assert TokenBlacklistRepository is not None
        assert SmsVerificationRepository is not None
        assert UserSessionRepository is not None
        assert AuthLogRepository is not None
        print("✓ 认证Repository导入成功")
    except ImportError as e:
        pytest.fail(f"认证Repository导入失败: {e}")


def test_import_auth_models():
    """测试认证模型导入"""
    try:
        from src.models.auth import (
            TokenBlacklist,
            SmsVerification,
            UserSession,
            AuthLog
        )
        assert TokenBlacklist is not None
        assert SmsVerification is not None
        assert UserSession is not None
        assert AuthLog is not None
        print("✓ 认证模型导入成功")
    except ImportError as e:
        pytest.fail(f"认证模型导入失败: {e}")


def test_service_factory_auth_repositories():
    """测试ServiceFactory能创建认证Repository"""
    try:
        from src.api.dependencies import ServiceFactory

        # 创建ServiceFactory实例
        factory = ServiceFactory()

        # 创建模拟session
        mock_session = AsyncMock()

        # 测试创建认证Repository
        token_repo = factory.get_token_blacklist_repository(mock_session)
        sms_repo = factory.get_sms_verification_repository(mock_session)
        session_repo = factory.get_user_session_repository(mock_session)
        log_repo = factory.get_auth_log_repository(mock_session)

        assert token_repo is not None
        assert sms_repo is not None
        assert session_repo is not None
        assert log_repo is not None

        # 验证缓存机制
        token_repo2 = factory.get_token_blacklist_repository(mock_session)
        assert token_repo is token_repo2

        print("✓ ServiceFactory认证Repository创建成功")

    except ImportError as e:
        pytest.fail(f"ServiceFactory测试失败: {e}")
    except Exception as e:
        pytest.fail(f"ServiceFactory测试异常: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])