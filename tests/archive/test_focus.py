"""
测试专注系统模型
验证专注会话模型的字段定义、数据验证、关系处理和业务逻辑功能
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

# 导入专注系统模型
from src.models.focus import FocusSession, FocusSessionBreak, FocusSessionTemplate
from src.models.user import User
from src.models.task import Task
from src.models.base_model import BaseSQLModel
from src.models.enums import SessionType


class TestFocusSessionModel:
    """专注会话模型测试类"""

    def test_focus_session_model_exists(self):
        """验证FocusSession模型存在且可导入"""
        assert FocusSession is not None
        assert issubclass(FocusSession, BaseSQLModel)
        assert hasattr(FocusSession, '__tablename__')
        assert FocusSession.__tablename__ == "focus_sessions"

    def test_focus_session_table_name(self):
        """验证专注会话表名定义"""
        assert FocusSession.__tablename__ == "focus_sessions"

    def test_focus_session_basic_fields(self):
        """测试专注会话基本字段定义"""
        # 验证所有必需字段都存在
        required_fields = [
            'session_type',    # 会话类型
            'started_at',      # 开始时间
            'ended_at',        # 结束时间
            'duration_minutes', # 持续时间（分钟）
            'is_completed',    # 是否完成
            'user_id',         # 用户ID
            'task_id'          # 关联任务ID（可选）
        ]

        for field in required_fields:
            assert hasattr(FocusSession, field), f"FocusSession模型缺少字段: {field}"

    def test_focus_session_inherits_from_base_model(self):
        """验证FocusSession模型继承自BaseSQLModel"""
        # 验证基础字段继承
        session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id="user123"
        )

        assert hasattr(session, 'id')
        assert hasattr(session, 'created_at')
        assert hasattr(session, 'updated_at')

        # 验证基础字段类型
        assert session.id is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_focus_session_session_type_field(self):
        """测试会话类型字段"""
        # 测试FOCUS类型
        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id="user123"
        )
        assert focus_session.session_type == SessionType.FOCUS

        # 测试其他类型
        break_session = FocusSession(
            session_type=SessionType.BREAK,
            user_id="user123"
        )
        assert break_session.session_type == SessionType.BREAK

    def test_focus_session_optional_fields(self):
        """测试专注会话可选字段"""
        session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id="user123"
        )

        # 验证可选字段默认值
        assert session.ended_at is None
        assert session.duration_minutes is None
        assert session.task_id is None
        assert session.is_completed is False

    def test_focus_session_field_types(self):
        """测试专注会话字段类型"""
        now = datetime.now(timezone.utc)

        session = FocusSession(
            session_type=SessionType.FOCUS,
            started_at=now,
            ended_at=now + timedelta(minutes=25),
            duration_minutes=25,
            is_completed=True,
            user_id="user123",
            task_id="task123"
        )

        # 验证字段类型
        assert isinstance(session.session_type, str)
        assert isinstance(session.started_at, datetime) or session.started_at is None
        assert isinstance(session.ended_at, datetime) or session.ended_at is None
        assert isinstance(session.duration_minutes, int) or session.duration_minutes is None
        assert isinstance(session.is_completed, bool)
        assert isinstance(session.user_id, str)
        assert isinstance(session.task_id, str) or session.task_id is None

    def test_focus_session_database_creation(self, session: Session):
        """测试专注会话数据库创建"""
        user = User(nickname="专注测试用户", email="focus_test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id,
            duration_minutes=25
        )

        # 保存到数据库
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证数据库保存成功
        assert focus_session.id is not None
        assert len(focus_session.id) > 0

        # 验证时间戳自动设置
        assert focus_session.created_at is not None
        assert focus_session.updated_at is not None
        assert isinstance(focus_session.created_at, datetime)
        assert isinstance(focus_session.updated_at, datetime)

    def test_focus_session_database_query(self, session: Session):
        """测试专注会话数据库查询"""
        user = User(nickname="查询测试用户", email="focus_query@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 通过ID查询
        statement = select(FocusSession).where(FocusSession.id == focus_session.id)
        found_session = session.exec(statement).first()

        assert found_session is not None
        assert found_session.session_type == SessionType.FOCUS
        assert found_session.user_id == user.id

    def test_focus_session_user_foreign_key(self, session: Session):
        """测试专注会话用户外键关系"""
        user = User(nickname="外键测试用户", email="fk_test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证外键关系
        assert focus_session.user_id == user.id

    def test_focus_session_task_foreign_key(self, session: Session):
        """测试专注会话任务外键关系"""
        user = User(nickname="任务关联用户", email="task_fk@example.com")
        task = Task(title="专注任务", user_id=user.id)
        session.add(user)
        session.add(task)
        session.commit()
        session.refresh(user)
        session.refresh(task)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id,
            task_id=task.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证任务外键关系
        assert focus_session.task_id == task.id

    def test_focus_session_completed_default(self, session: Session):
        """测试专注会话完成状态默认值"""
        user = User(nickname="默认状态用户", email="default@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证默认完成状态为False
        assert focus_session.is_completed is False

    def test_focus_session_duration_calculation(self, session: Session):
        """测试专注会话持续时间计算"""
        user = User(nickname="持续时间测试用户", email="duration@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=25)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            started_at=start_time,
            ended_at=end_time,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证时间设置（考虑时区一致性）
        assert focus_session.started_at is not None
        assert focus_session.ended_at is not None
        # 验证时间差约为25分钟（允许1秒误差）
        time_diff = focus_session.ended_at - focus_session.started_at
        expected_duration = timedelta(minutes=25)
        assert abs(time_diff - expected_duration) < timedelta(seconds=1)

    def test_focus_session_session_types(self, session: Session):
        """测试不同类型的专注会话"""
        user = User(nickname="多类型用户", email="multi_type@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 测试FOCUS会话
        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)

        # 测试BREAK会话
        break_session = FocusSession(
            session_type=SessionType.BREAK,
            user_id=user.id
        )
        session.add(break_session)

        # 测试LONG_BREAK会话
        long_break_session = FocusSession(
            session_type=SessionType.LONG_BREAK,
            user_id=user.id
        )
        session.add(long_break_session)

        session.commit()

        # 验证所有会话类型都正确保存
        assert focus_session.session_type == SessionType.FOCUS
        assert break_session.session_type == SessionType.BREAK
        assert long_break_session.session_type == SessionType.LONG_BREAK

    def test_focus_session_model_repr(self, session: Session):
        """测试专注会话模型字符串表示"""
        user = User(nickname="字符串测试用户", email="repr_test@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 验证__repr__方法
        repr_str = repr(focus_session)
        assert "FocusSession" in repr_str
        assert focus_session.id in repr_str

    def test_focus_session_model_str(self):
        """测试专注会话模型字符串转换"""
        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id="user123"
        )

        # 验证__str__方法（如果实现了）
        if hasattr(focus_session, '__str__'):
            str_value = str(focus_session)
            assert "focus" in str_value.lower() or "FOCUS" in str_value


class TestFocusSessionBreakModel:
    """专注会话休息模型测试类"""

    def test_focus_session_break_model_exists(self):
        """验证FocusSessionBreak模型存在且可导入"""
        assert FocusSessionBreak is not None
        assert issubclass(FocusSessionBreak, BaseSQLModel)
        assert hasattr(FocusSessionBreak, '__tablename__')
        assert FocusSessionBreak.__tablename__ == "focus_session_breaks"

    def test_focus_session_break_basic_fields(self):
        """测试FocusSessionBreak基本字段"""
        required_fields = [
            'focus_session_id',  # 关联的专注会话ID
            'break_type',        # 休息类型
            'started_at',        # 开始时间
            'ended_at',          # 结束时间
            'duration_minutes',  # 持续时间
            'is_skipped'         # 是否跳过
        ]

        for field in required_fields:
            assert hasattr(FocusSessionBreak, field), f"FocusSessionBreak模型缺少字段: {field}"

    def test_focus_session_break_inherits_from_base_model(self):
        """验证FocusSessionBreak模型继承自BaseSQLModel"""
        break_session = FocusSessionBreak(
            focus_session_id="session123",
            break_type=SessionType.BREAK
        )

        assert hasattr(break_session, 'id')
        assert hasattr(break_session, 'created_at')
        assert hasattr(break_session, 'updated_at')

        # 验证基础字段类型
        assert break_session.id is not None
        assert isinstance(break_session.created_at, datetime)
        assert isinstance(break_session.updated_at, datetime)


class TestFocusSessionTemplateModel:
    """专注会话模板模型测试类"""

    def test_focus_session_template_model_exists(self):
        """验证FocusSessionTemplate模型存在且可导入"""
        assert FocusSessionTemplate is not None
        assert issubclass(FocusSessionTemplate, BaseSQLModel)
        assert hasattr(FocusSessionTemplate, '__tablename__')
        assert FocusSessionTemplate.__tablename__ == "focus_session_templates"

    def test_focus_session_template_basic_fields(self):
        """测试FocusSessionTemplate基本字段"""
        required_fields = [
            'name',              # 模板名称
            'description',       # 模板描述
            'focus_duration',    # 专注时长
            'break_duration',    # 休息时长
            'long_break_duration', # 长休息时长
            'sessions_until_long_break', # 长休息前的专注次数
            'user_id'            # 用户ID
        ]

        for field in required_fields:
            assert hasattr(FocusSessionTemplate, field), f"FocusSessionTemplate模型缺少字段: {field}"

    def test_focus_session_template_inherits_from_base_model(self):
        """验证FocusSessionTemplate模型继承自BaseSQLModel"""
        template = FocusSessionTemplate(
            name="番茄钟模板",
            focus_duration=25,
            break_duration=5,
            long_break_duration=15,
            sessions_until_long_break=4,
            user_id="user123"
        )

        assert hasattr(template, 'id')
        assert hasattr(template, 'created_at')
        assert hasattr(template, 'updated_at')

        # 验证基础字段类型
        assert template.id is not None
        assert isinstance(template.created_at, datetime)
        assert isinstance(template.updated_at, datetime)


class TestFocusSessionModelMethods:
    """FocusSession模型方法功能测试类"""

    def test_focus_session_start_session_method(self, session: Session):
        """测试start_session方法"""
        user = User(nickname="开始会话用户", email="start_session@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 初始状态下没有开始时间
        assert focus_session.started_at is None

        # 调用开始方法
        focus_session.start_session()
        session.commit()
        session.refresh(focus_session)

        # 验证开始时间已设置
        assert focus_session.started_at is not None
        assert isinstance(focus_session.started_at, datetime)
        # 注意：数据库中的时间可能没有时区信息，这是正常的

    def test_focus_session_complete_session_method(self, session: Session):
        """测试complete_session方法"""
        user = User(nickname="完成会话用户", email="complete_session@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 初始状态
        assert not focus_session.is_completed
        assert focus_session.ended_at is None
        assert focus_session.duration_minutes is None

        # 先开始会话
        focus_session.start_session()
        session.commit()

        # 等待一小段时间确保有持续时间
        import time
        time.sleep(0.01)

        # 完成会话
        focus_session.complete_session()
        session.commit()
        session.refresh(focus_session)

        # 验证完成状态
        assert focus_session.is_completed
        assert focus_session.ended_at is not None
        assert focus_session.duration_minutes is not None
        assert focus_session.duration_minutes >= 0

    def test_focus_session_get_actual_duration_method(self, session: Session):
        """测试get_actual_duration方法"""
        user = User(nickname="实际时长用户", email="actual_duration@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 没有时间信息时返回None
        assert focus_session.get_actual_duration() is None

        # 设置开始时间但没有结束时间
        focus_session.started_at = datetime.now(timezone.utc)
        session.commit()
        assert focus_session.get_actual_duration() is None

        # 设置结束时间
        focus_session.ended_at = focus_session.started_at + timedelta(minutes=25)
        session.commit()

        # 验证实际持续时间
        actual_duration = focus_session.get_actual_duration()
        assert actual_duration == 25

    def test_focus_session_is_active_method(self, session: Session):
        """测试is_active方法"""
        user = User(nickname="活跃状态用户", email="is_active@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 初始状态不活跃
        assert not focus_session.is_active()

        # 开始会话后活跃
        focus_session.start_session()
        session.commit()
        assert focus_session.is_active()

        # 完成会话后不活跃
        focus_session.complete_session()
        session.commit()
        session.refresh(focus_session)
        assert not focus_session.is_active()

    def test_focus_session_is_focus_session_method(self, session: Session):
        """测试is_focus_session方法"""
        user = User(nickname="专注类型用户", email="focus_type@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 专注会话
        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        assert focus_session.is_focus_session()

        # 休息会话
        break_session = FocusSession(
            session_type=SessionType.BREAK,
            user_id=user.id
        )
        session.add(break_session)
        session.commit()
        assert not break_session.is_focus_session()

    def test_focus_session_is_break_session_method(self, session: Session):
        """测试is_break_session方法"""
        user = User(nickname="休息类型用户", email="break_type@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 专注会话不是休息会话
        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        assert not focus_session.is_break_session()

        # 短休息会话
        break_session = FocusSession(
            session_type=SessionType.BREAK,
            user_id=user.id
        )
        session.add(break_session)
        session.commit()
        assert break_session.is_break_session()

        # 长休息会话
        long_break_session = FocusSession(
            session_type=SessionType.LONG_BREAK,
            user_id=user.id
        )
        session.add(long_break_session)
        session.commit()
        assert long_break_session.is_break_session()

    def test_focus_session_get_efficiency_score_method(self, session: Session):
        """测试get_efficiency_score方法"""
        user = User(nickname="效率评分用户", email="efficiency@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 未完成的会话效率为0
        assert focus_session.get_efficiency_score() == 0.0

        # 完成标准时长（25分钟）的会话效率为1.0
        focus_session.start_session()
        focus_session.duration_minutes = 25
        focus_session.is_completed = True  # 直接标记为完成
        session.commit()
        session.refresh(focus_session)

        score = focus_session.get_efficiency_score()
        assert score == 1.0

    def test_focus_session_break_methods(self, session: Session):
        """测试FocusSessionBreak的方法"""
        user = User(nickname="休息方法用户", email="break_methods@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        focus_session = FocusSession(
            session_type=SessionType.FOCUS,
            user_id=user.id
        )
        session.add(focus_session)
        session.commit()
        session.refresh(focus_session)

        # 创建休息记录
        break_record = FocusSessionBreak(
            focus_session_id=focus_session.id,
            break_type=SessionType.BREAK
        )
        session.add(break_record)
        session.commit()
        session.refresh(break_record)

        # 测试开始休息
        assert break_record.started_at is None
        break_record.start_break()
        session.commit()
        session.refresh(break_record)
        assert break_record.started_at is not None

        # 测试结束休息
        import time
        time.sleep(0.01)  # 确保有持续时间
        break_record.end_break()
        session.commit()
        session.refresh(break_record)
        assert break_record.ended_at is not None
        assert break_record.duration_minutes is not None
        assert break_record.duration_minutes >= 0

        # 测试跳过休息
        skipped_break = FocusSessionBreak(
            focus_session_id=focus_session.id,
            break_type=SessionType.BREAK
        )
        session.add(skipped_break)
        session.commit()
        session.refresh(skipped_break)

        assert not skipped_break.is_skipped
        skipped_break.skip_break()
        session.commit()
        session.refresh(skipped_break)
        assert skipped_break.is_skipped
        assert skipped_break.ended_at is not None

    def test_focus_session_template_methods(self, session: Session):
        """测试FocusSessionTemplate的方法"""
        user = User(nickname="模板方法用户", email="template_methods@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # 测试标准番茄钟模板
        pomodoro_template = FocusSessionTemplate(
            name="番茄钟",
            focus_duration=25,
            break_duration=5,
            long_break_duration=15,
            sessions_until_long_break=4,
            user_id=user.id
        )
        session.add(pomodoro_template)
        session.commit()
        session.refresh(pomodoro_template)

        # 测试番茄钟识别
        assert pomodoro_template.is_pomodoro_template()

        # 测试非番茄钟模板
        custom_template = FocusSessionTemplate(
            name="自定义模板",
            focus_duration=30,
            break_duration=10,
            long_break_duration=20,
            sessions_until_long_break=3,
            user_id=user.id
        )
        session.add(custom_template)
        session.commit()
        assert not custom_template.is_pomodoro_template()

        # 测试周期时间计算
        assert pomodoro_template.get_total_cycle_time() == 30  # 25 + 5
        assert custom_template.get_total_cycle_time() == 40  # 30 + 10

        # 测试每日专注时间计算
        assert pomodoro_template.get_daily_focus_time(8) == 200  # 8 * 25
        assert pomodoro_template.get_daily_focus_time() == 200  # 默认8次

        # 测试重置为番茄钟默认值
        reset_template = FocusSessionTemplate(
            name="重置模板",
            focus_duration=50,
            break_duration=15,
            user_id=user.id
        )
        session.add(reset_template)
        session.commit()

        assert not reset_template.is_pomodoro_template()
        reset_template.reset_to_pomodoro_defaults()
        session.commit()
        session.refresh(reset_template)
        assert reset_template.is_pomodoro_template()

    def test_focus_session_template_repr_and_str(self, session: Session):
        """测试FocusSessionTemplate的字符串表示"""
        user = User(nickname="字符串模板用户", email="template_str@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        template = FocusSessionTemplate(
            name="测试模板",
            user_id=user.id
        )
        session.add(template)
        session.commit()
        session.refresh(template)

        # 测试__repr__方法
        repr_str = repr(template)
        assert "FocusSessionTemplate" in repr_str
        assert template.id in repr_str

        # 测试__str__方法
        str_value = str(template)
        assert str_value == "测试模板"