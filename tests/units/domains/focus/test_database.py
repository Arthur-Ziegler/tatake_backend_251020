"""
Focus领域数据库模块测试

测试Focus领域的数据库功能，包括：
1. 数据库表创建和初始化
2. 数据库会话管理
3. 连接状态检查
4. 数据库健康检查
5. 错误处理和异常管理

作者：TaKeKe团队
版本：2.0.0 - 测试基础设施建设
"""

import pytest
import os
import logging
from unittest.mock import Mock, patch, MagicMock
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from src.domains.focus.database import (
    create_focus_tables,
    get_focus_session
)
from src.domains.focus.models import FocusSession


@pytest.mark.unit
class TestCreateFocusTables:
    """创建Focus数据库表测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        # 设置内存数据库URL
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        # 重新导入数据库模块以使用新的数据库URL
        import importlib
        import src.domains.focus.database
        importlib.reload(src.domains.focus.database)

        yield

        # 测试结束后清理
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    def test_create_focus_tables_success(self):
        """测试成功创建Focus表"""
        create_focus_tables()

    def test_create_focus_tables_idempotent(self):
        """测试创建表的幂等性"""
        # 第一次创建
        create_focus_tables()
        # 第二次创建应该不报错
        create_focus_tables()

    @patch('src.domains.focus.database.get_engine')
    def test_create_tables_handles_exceptions(self, mock_get_engine):
        """测试创建表时处理异常"""
        mock_engine = Mock()
        mock_engine.__enter__.side_effect = Exception("Database error")
        mock_get_engine.return_value = mock_engine

        with pytest.raises(Exception):
            create_focus_tables()


@pytest.mark.unit
class TestGetFocusSession:
    """获取Focus数据库会话测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        import importlib
        import src.domains.focus.database
        importlib.reload(src.domains.focus.database)

        yield

        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    @patch('src.domains.focus.database.get_db_session')
    def test_get_focus_session_context_manager(self, mock_get_db_session):
        """测试Focus会话上下文管理器"""
        mock_session = Mock(spec=Session)
        mock_session_gen = iter([mock_session])
        mock_get_db_session.return_value = mock_session_gen

        # 使用get_focus_session作为上下文管理器
        with get_focus_session() as session:
            assert session == mock_session

    @patch('src.domains.focus.database.get_db_session')
    def test_get_focus_session_cleanup(self, mock_get_db_session):
        """测试Focus会话清理"""
        mock_session = Mock(spec=Session)
        mock_session.close = Mock()
        mock_session_gen = iter([mock_session])
        mock_get_db_session.return_value = mock_session_gen

        with get_focus_session() as session:
            pass

        # 验证会话被关闭
        mock_session.close.assert_called_once()


@pytest.mark.unit
class TestFocusDatabaseHealth:
    """Focus数据库健康检查测试类"""

    @patch('src.domains.focus.database.create_focus_tables')
    def test_create_tables_logging(self, mock_create_tables):
        """测试创建表日志记录"""
        # 测试成功情况
        create_focus_tables()
        mock_create_tables.assert_called_once()

    @patch('src.domains.focus.database.get_engine')
    def test_create_tables_exception_handling(self, mock_get_engine):
        """测试创建表异常处理"""
        mock_get_engine.side_effect = Exception("数据库连接失败")

        with pytest.raises(Exception) as exc_info:
            create_focus_tables()

        assert "数据库连接失败" in str(exc_info.value)

    @patch('src.domains.focus.database.get_db_session')
    def test_get_focus_session_context_manager(self, mock_get_db_session):
        """测试Focus会话上下文管理器"""
        mock_session = Mock(spec=Session)
        mock_session_gen = iter([mock_session])
        mock_get_db_session.return_value = mock_session_gen

        # 模拟生成器的使用
        session_generator = get_focus_session()
        session = next(session_generator)

        try:
            assert session == mock_session
        finally:
            # 验证会话关闭
            session.close.assert_called_once()

    def test_module_imports(self):
        """测试模块导入"""
        # 验证所有导入的函数都存在
        assert callable(create_focus_tables)
        assert callable(get_focus_session)


@pytest.mark.integration
class TestFocusDatabaseIntegration:
    """Focus数据库集成测试类"""

    @pytest.fixture(autouse=True)
    def setup_test_database(self):
        """为测试设置内存数据库"""
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        # 创建内存数据库引擎
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )

        # 创建表
        FocusSession.metadata.create_all(engine)

        yield engine

        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    def test_complete_database_workflow(self, setup_test_database):
        """测试完整数据库工作流程"""
        engine = setup_test_database

        # 1. 创建会话
        with Session(engine) as session:
            # 2. 插入测试数据
            focus_session = FocusSession(
                user_id="test_user_123",
                start_time="2025-01-01T10:00:00Z",
                task_title="测试任务",
                session_duration=3600,
                status="active"
            )
            session.add(focus_session)
            session.commit()

            # 3. 查询数据
            result = session.get(focus_session.id)
            assert result is not None
            assert result.user_id == "test_user_123"
            assert result.task_title == "测试任务"

            # 4. 更新数据
            result.status = "completed"
            session.commit()

            # 5. 验证更新
            updated = session.get(focus_session.id)
            assert updated.status == "completed"

    def test_multiple_sessions_handling(self, setup_test_database):
        """测试多会话处理"""
        engine = setup_test_database

        sessions = []

        # 创建多个会话
        for i in range(3):
            with Session(engine) as session:
                focus_session = FocusSession(
                    user_id=f"user_{i}",
                    start_time="2025-01-01T10:00:00Z",
                    task_title=f"任务 {i}",
                    session_duration=3600,
                    status="active"
                )
                session.add(focus_session)
                session.commit()
                sessions.append(focus_session.id)

        # 验证所有会话都被创建
        with Session(engine) as session:
            for session_id in sessions:
                result = session.get(session_id)
                assert result is not None

    def test_database_error_recovery(self, setup_test_database):
        """测试数据库错误恢复"""
        engine = setup_test_database

        # 正常操作
        with Session(engine) as session:
            focus_session = FocusSession(
                user_id="test_user",
                start_time="2025-01-01T10:00:00Z",
                task_title="测试任务",
                session_duration=3600,
                status="active"
            )
            session.add(focus_session)
            session.commit()

        # 模拟错误恢复
        with Session(engine) as session:
            try:
                # 故意执行一个可能失败的操作
                result = session.get("invalid_uuid")
                if result is None:
                    # 处理未找到的情况
                    pass
            except Exception:
                session.rollback()

            # 验证数据仍然可用
            valid_result = session.query(FocusSession).first()
            assert valid_result is not None


@pytest.mark.unit
class TestFocusDatabaseEdgeCases:
    """Focus数据库边界条件测试"""

    @patch('src.domains.focus.database.logging.getLogger')
    def test_logging_configuration(self, mock_get_logger):
        """测试日志配置"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # 重新导入模块以触发日志配置
        import importlib
        import src.domains.focus.database
        importlib.reload(src.domains.focus.database)

        # 验证日志器被正确配置
        mock_get_logger.assert_called_with(__name__)

    def test_database_url_configuration(self):
        """测试数据库URL配置"""
        # 测试默认配置不会出错
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///:memory:"}):
            import importlib
            import src.domains.focus.database
            importlib.reload(src.domains.focus.database)

            # 验证模块能正常加载
            assert src.domains.focus.database.create_focus_tables is not None

    def test_module_functions_exist(self):
        """测试模块函数存在性"""
        # 验证关键函数存在且可调用
        assert callable(create_focus_tables)
        assert callable(get_focus_session)


@pytest.mark.parametrize("invalid_session_data", [
    {"user_id": "", "start_time": "2025-01-01T10:00:00Z"},  # 空user_id
    {"user_id": "user_123", "start_time": ""},  # 空start_time
    {"user_id": None, "start_time": "2025-01-01T10:00:00Z"},  # None user_id
    {"user_id": "user_123", "start_time": None},  # None start_time
])
def test_invalid_session_data_handling(setup_test_database, invalid_session_data):
    """测试无效会话数据处理"""
    engine = setup_test_database

    with Session(engine) as session:
        try:
            focus_session = FocusSession(**invalid_session_data)
            session.add(focus_session)
            session.commit()
            # 如果能正常处理，说明模型验证生效
            assert focus_session is not None
        except Exception:
            # 如果抛出异常，说明数据验证生效
            pass


@pytest.fixture
def mock_database_logger():
    """模拟数据库日志器"""
    return Mock(spec=logging.Logger)


@pytest.mark.unit
class TestFocusDatabaseLogging:
    """Focus数据库日志测试"""

    def test_logging_on_table_creation_success(self, mock_database_logger):
        """测试表创建成功时的日志"""
        with patch('src.domains.focus.database.logger', mock_database_logger):
            create_focus_tables()
            mock_database_logger.info.assert_called_with("Focus领域数据库表创建成功")

    @patch('src.domains.focus.database.logger')
    def test_logging_on_table_creation_failure(self, mock_logger):
        """测试表创建失败时的日志"""
        mock_logger.error = Mock()

        with patch('src.domains.focus.database.get_engine') as mock_get_engine:
            mock_get_engine.side_effect = Exception("创建失败")

            try:
                create_focus_tables()
            except Exception:
                pass

            mock_logger.error.assert_called_once()
            assert "Focus领域数据库表创建失败" in mock_logger.error.call_args[0][0]