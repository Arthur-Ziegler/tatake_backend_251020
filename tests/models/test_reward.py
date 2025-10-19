"""
测试奖励系统模型
验证奖励相关模型的字段定义、数据验证、关系处理和业务逻辑功能
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

# 导入奖励系统模型
from src.models.reward import Reward, RewardRule, UserFragment, LotteryRecord, PointsTransaction
from src.models.user import User
from src.models.base_model import BaseSQLModel
from src.models.enums import RewardType, RewardStatus, TransactionType


class TestRewardModel:
    """奖励模型测试类"""

    def test_reward_model_exists(self):
        """验证Reward模型存在且可导入"""
        assert Reward is not None
        assert issubclass(Reward, BaseSQLModel)
        assert hasattr(Reward, '__tablename__')
        assert Reward.__tablename__ == "rewards"

    def test_reward_table_name(self):
        """验证奖励表名定义"""
        assert Reward.__tablename__ == "rewards"

    def test_reward_basic_fields(self):
        """测试奖励基本字段定义"""
        # 验证所有必需字段都存在
        required_fields = [
            'name',           # 奖励名称
            'description',    # 奖励描述
            'reward_type',    # 奖励类型
            'cost_fragments', # 需要碎片数量
            'image_url',      # 奖励图片URL
            'is_active',      # 是否激活
            'user_id'         # 用户ID
        ]

        for field in required_fields:
            assert hasattr(Reward, field), f"Reward模型缺少字段: {field}"

    def test_reward_inherits_from_base_model(self):
        """验证Reward模型继承自BaseSQLModel"""
        reward = Reward(
            name="测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )

        assert hasattr(reward, 'id')
        assert hasattr(reward, 'created_at')
        assert hasattr(reward, 'updated_at')

        # 验证基础字段类型
        assert reward.id is not None
        assert isinstance(reward.created_at, datetime)
        assert isinstance(reward.updated_at, datetime)

    def test_reward_reward_type_field(self):
        """测试奖励类型字段"""
        # 测试徽章类型
        badge_reward = Reward(
            name="专注达人",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )
        assert badge_reward.reward_type == RewardType.BADGE

        # 测试头像框类型
        avatar_reward = Reward(
            name="金边头像框",
            reward_type=RewardType.AVATAR_FRAME,
            cost_fragments=200,
            user_id="user123"
        )
        assert avatar_reward.reward_type == RewardType.AVATAR_FRAME

    def test_reward_optional_fields(self):
        """测试奖励可选字段"""
        reward = Reward(
            name="测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )

        # 验证可选字段默认值
        assert reward.description is None
        assert reward.image_url is None
        assert reward.is_active is True  # 默认激活

    def test_reward_field_types(self):
        """测试奖励字段类型"""
        reward = Reward(
            name="完整奖励",
            description="这是一个完整的奖励描述",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            image_url="https://example.com/reward.png",
            is_active=True,
            user_id="user123"
        )

        # 验证字段类型
        assert isinstance(reward.name, str)
        assert isinstance(reward.description, str) or reward.description is None
        assert isinstance(reward.reward_type, str)
        assert isinstance(reward.cost_fragments, int)
        assert isinstance(reward.image_url, str) or reward.image_url is None
        assert isinstance(reward.is_active, bool)
        assert isinstance(reward.user_id, str)

    def test_reward_cost_validation(self):
        """测试奖励碎片成本验证"""
        # 测试正数成本
        reward = Reward(
            name="正数成本奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )
        assert reward.cost_fragments == 100

        # 测试零成本奖励
        free_reward = Reward(
            name="免费奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=0,
            user_id="user123"
        )
        assert free_reward.cost_fragments == 0

    def test_reward_database_creation(self, session: Session):
        """测试奖励数据库创建"""
        user = User(nickname="奖励测试用户", email=f"reward_test_{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        reward = Reward(
            name="数据库测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=150,
            user_id=user.id
        )

        # 保存到数据库
        session.add(reward)
        session.commit()
        session.refresh(reward)

        # 验证数据库保存成功
        assert reward.id is not None
        assert len(reward.id) > 0

        # 验证时间戳自动设置
        assert reward.created_at is not None
        assert reward.updated_at is not None
        assert isinstance(reward.created_at, datetime)
        assert isinstance(reward.updated_at, datetime)

    def test_reward_database_query(self, session: Session):
        """测试奖励数据库查询"""
        user = User(nickname="查询测试用户", email=f"reward_query_{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        reward = Reward(
            name="查询测试奖励",
            reward_type=RewardType.AVATAR_FRAME,
            cost_fragments=200,
            user_id=user.id
        )
        session.add(reward)
        session.commit()
        session.refresh(reward)

        # 通过ID查询
        statement = select(Reward).where(Reward.id == reward.id)
        found_reward = session.exec(statement).first()

        assert found_reward is not None
        assert found_reward.name == "查询测试奖励"
        assert found_reward.reward_type == RewardType.AVATAR_FRAME

    def test_reward_user_foreign_key(self, session: Session):
        """测试奖励用户外键关系"""
        user = User(nickname="外键测试用户", email=f"fk_test_{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        reward = Reward(
            name="外键测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id=user.id
        )
        session.add(reward)
        session.commit()
        session.refresh(reward)

        # 验证外键关系
        assert reward.user_id == user.id

    def test_reward_is_active_default(self, session: Session):
        """测试奖励激活状态默认值"""
        user = User(nickname="默认状态用户", email=f"default_{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        reward = Reward(
            name="默认激活奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id=user.id
        )
        session.add(reward)
        session.commit()
        session.refresh(reward)

        # 验证默认激活状态为True
        assert reward.is_active is True

    def test_reward_model_repr(self, session: Session):
        """测试奖励模型字符串表示"""
        user = User(nickname="字符串测试用户", email=f"repr_test_{uuid.uuid4().hex[:8]}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        reward = Reward(
            name="字符串测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id=user.id
        )
        session.add(reward)
        session.commit()
        session.refresh(reward)

        # 验证__repr__方法
        repr_str = repr(reward)
        assert "Reward" in repr_str
        assert reward.id in repr_str

    def test_reward_model_str(self):
        """测试奖励模型字符串转换"""
        reward = Reward(
            name="字符串转换奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )

        # 验证__str__方法
        str_value = str(reward)
        assert "字符串转换奖励" in str_value

    def test_reward_business_logic_methods(self):
        """测试奖励业务逻辑方法"""
        reward = Reward(
            name="业务逻辑测试奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=100,
            user_id="user123"
        )

        # 测试is_affordable方法
        assert reward.is_affordable(150) is True
        assert reward.is_affordable(50) is False

        # 测试get_display_cost方法
        cost_display = reward.get_display_cost()
        assert "100" in cost_display
        assert "碎片" in cost_display

        # 测试can_be_equipped方法
        avatar_reward = Reward(
            name="头像框奖励",
            reward_type=RewardType.AVATAR_FRAME,
            cost_fragments=200,
            user_id="user123"
        )
        assert avatar_reward.can_be_equipped() is True

        badge_reward = Reward(
            name="徽章奖励",
            reward_type=RewardType.BADGE,
            cost_fragments=150,
            user_id="user123"
        )
        assert badge_reward.can_be_equipped() is False

        theme_reward = Reward(
            name="主题奖励",
            reward_type=RewardType.THEME,
            cost_fragments=300,
            user_id="user123"
        )
        assert theme_reward.can_be_equipped() is True


class TestRewardRuleModel:
    """奖励规则模型测试类"""

    def test_reward_rule_model_exists(self):
        """验证RewardRule模型存在且可导入"""
        assert RewardRule is not None
        assert issubclass(RewardRule, BaseSQLModel)
        assert hasattr(RewardRule, '__tablename__')
        assert RewardRule.__tablename__ == "reward_rules"

    def test_reward_rule_basic_fields(self):
        """测试RewardRule基本字段"""
        required_fields = [
            'name',              # 规则名称
            'description',       # 规则描述
            'condition_type',    # 条件类型
            'condition_value',   # 条件值
            'reward_type',       # 奖励类型
            'reward_value',      # 奖励值
            'is_active',         # 是否激活
            'user_id'            # 用户ID
        ]

        for field in required_fields:
            assert hasattr(RewardRule, field), f"RewardRule模型缺少字段: {field}"

    def test_reward_rule_inherits_from_base_model(self):
        """验证RewardRule模型继承自BaseSQLModel"""
        rule = RewardRule(
            name="测试规则",
            condition_type="focus_hours",
            condition_value=10,
            reward_type="fragments",
            reward_value=50,
            user_id="user123"
        )

        assert hasattr(rule, 'id')
        assert hasattr(rule, 'created_at')
        assert hasattr(rule, 'updated_at')

        # 验证基础字段类型
        assert rule.id is not None
        assert isinstance(rule.created_at, datetime)
        assert isinstance(rule.updated_at, datetime)

    def test_reward_rule_business_logic_methods(self):
        """测试奖励规则业务逻辑方法"""
        rule = RewardRule(
            name="专注新手规则",
            description="完成专注10小时获得50个碎片",
            condition_type="focus_hours",
            condition_value=10,
            reward_type="fragments",
            reward_value=50,
            user_id="user123"
        )

        # 测试check_condition方法
        assert rule.check_condition(15) is True
        assert rule.check_condition(5) is False
        assert rule.check_condition(10) is True

        # 测试get_reward_description方法
        reward_desc = rule.get_reward_description()
        assert "50" in reward_desc
        assert "fragments" in reward_desc

        # 测试__str__方法
        str_value = str(rule)
        assert "专注新手规则" in str_value


class TestUserFragmentModel:
    """用户碎片模型测试类"""

    def test_user_fragment_model_exists(self):
        """验证UserFragment模型存在且可导入"""
        assert UserFragment is not None
        assert issubclass(UserFragment, BaseSQLModel)
        assert hasattr(UserFragment, '__tablename__')
        assert UserFragment.__tablename__ == "user_fragments"

    def test_user_fragment_basic_fields(self):
        """测试UserFragment基本字段"""
        required_fields = [
            'user_id',           # 用户ID
            'fragment_count',    # 碎片数量
            'total_earned',      # 总共获得
            'total_spent',       # 总共消费
            'last_earned_at',    # 最后获得时间
        ]

        for field in required_fields:
            assert hasattr(UserFragment, field), f"UserFragment模型缺少字段: {field}"

    def test_user_fragment_inherits_from_base_model(self):
        """验证UserFragment模型继承自BaseSQLModel"""
        user_fragment = UserFragment(
            user_id="user123",
            fragment_count=50
        )

        assert hasattr(user_fragment, 'id')
        assert hasattr(user_fragment, 'created_at')
        assert hasattr(user_fragment, 'updated_at')

        # 验证基础字段类型
        assert user_fragment.id is not None
        assert isinstance(user_fragment.created_at, datetime)
        assert isinstance(user_fragment.updated_at, datetime)

    def test_user_fragment_business_logic_methods(self):
        """测试用户碎片业务逻辑方法"""
        user_fragment = UserFragment(
            user_id="user123",
            fragment_count=100,
            total_earned=200,
            total_spent=100
        )

        # 测试can_afford方法
        assert user_fragment.can_afford(50) is True
        assert user_fragment.can_afford(150) is False
        assert user_fragment.can_afford(100) is True

        # 测试earn_fragments方法
        user_fragment.earn_fragments(25)
        assert user_fragment.fragment_count == 125
        assert user_fragment.total_earned == 225
        assert user_fragment.last_earned_at is not None

        # 测试spend_fragments方法
        success = user_fragment.spend_fragments(75)
        assert success is True
        assert user_fragment.fragment_count == 50
        assert user_fragment.total_spent == 175

        # 测试spend_fragments失败情况
        fail_success = user_fragment.spend_fragments(100)
        assert fail_success is False
        assert user_fragment.fragment_count == 50  # 数量不变

        # 测试get_spending_rate方法
        rate = user_fragment.get_spending_rate()
        expected_rate = 175 / 225  # total_spent / total_earned
        assert abs(rate - expected_rate) < 0.001

        # 测试零收入情况
        zero_fragment = UserFragment(
            user_id="user456",
            fragment_count=0,
            total_earned=0,
            total_spent=0
        )
        zero_rate = zero_fragment.get_spending_rate()
        assert zero_rate == 0.0

        # 测试__str__方法
        str_value = str(user_fragment)
        assert "user123" in str_value
        assert "50" in str_value
        assert "fragments" in str_value


class TestLotteryRecordModel:
    """抽奖记录模型测试类"""

    def test_lottery_record_model_exists(self):
        """验证LotteryRecord模型存在且可导入"""
        assert LotteryRecord is not None
        assert issubclass(LotteryRecord, BaseSQLModel)
        assert hasattr(LotteryRecord, '__tablename__')
        assert LotteryRecord.__tablename__ == "lottery_records"

    def test_lottery_record_basic_fields(self):
        """测试LotteryRecord基本字段"""
        required_fields = [
            'user_id',        # 用户ID
            'reward_id',      # 奖励ID
            'cost_fragments', # 消耗碎片
            'result_type',    # 抽奖结果类型
            'won',           # 是否中奖
        ]

        for field in required_fields:
            assert hasattr(LotteryRecord, field), f"LotteryRecord模型缺少字段: {field}"

    def test_lottery_record_inherits_from_base_model(self):
        """验证LotteryRecord模型继承自BaseSQLModel"""
        record = LotteryRecord(
            user_id="user123",
            reward_id="reward123",
            cost_fragments=50,
            result_type="normal",
            won=True
        )

        assert hasattr(record, 'id')
        assert hasattr(record, 'created_at')
        assert hasattr(record, 'updated_at')

        # 验证基础字段类型
        assert record.id is not None
        assert isinstance(record.created_at, datetime)
        assert isinstance(record.updated_at, datetime)

    def test_lottery_record_business_logic_methods(self):
        """测试抽奖记录业务逻辑方法"""
        # 测试中奖记录
        win_record = LotteryRecord(
            user_id="user123",
            reward_id="reward123",
            cost_fragments=50,
            result_type="rare",
            won=True,
            reward_name="稀有徽章"
        )

        # 测试__str__方法（中奖）
        win_str = str(win_record)
        assert "中奖" in win_str

        # 测试未中奖记录
        lose_record = LotteryRecord(
            user_id="user123",
            reward_id=None,
            cost_fragments=50,
            result_type="normal",
            won=False,
            reward_name=None
        )

        # 测试__str__方法（未中奖）
        lose_str = str(lose_record)
        assert "未中奖" in lose_str

        # 测试__repr__方法
        repr_str = repr(win_record)
        assert "LotteryRecord" in repr_str
        assert win_record.id in repr_str


class TestPointsTransactionModel:
    """积分流水模型测试类"""

    def test_points_transaction_model_exists(self):
        """验证PointsTransaction模型存在且可导入"""
        assert PointsTransaction is not None
        assert issubclass(PointsTransaction, BaseSQLModel)
        assert hasattr(PointsTransaction, '__tablename__')
        assert PointsTransaction.__tablename__ == "points_transactions"

    def test_points_transaction_basic_fields(self):
        """测试PointsTransaction基本字段"""
        required_fields = [
            'user_id',          # 用户ID
            'transaction_type', # 交易类型
            'points_change',    # 积分变化
            'balance_before',   # 交易前余额
            'balance_after',    # 交易后余额
            'description',      # 交易描述
        ]

        for field in required_fields:
            assert hasattr(PointsTransaction, field), f"PointsTransaction模型缺少字段: {field}"

    def test_points_transaction_inherits_from_base_model(self):
        """验证PointsTransaction模型继承自BaseSQLModel"""
        transaction = PointsTransaction(
            user_id="user123",
            transaction_type="earn",
            points_change=10,
            balance_before=100,
            balance_after=110,
            description="专注奖励"
        )

        assert hasattr(transaction, 'id')
        assert hasattr(transaction, 'created_at')
        assert hasattr(transaction, 'updated_at')

        # 验证基础字段类型
        assert transaction.id is not None
        assert isinstance(transaction.created_at, datetime)
        assert isinstance(transaction.updated_at, datetime)

    def test_points_transaction_business_logic_methods(self):
        """测试积分流水业务逻辑方法"""
        # 测试获得积分交易
        earn_transaction = PointsTransaction(
            user_id="user123",
            transaction_type=TransactionType.EARN,
            points_change=50,
            balance_before=100,
            balance_after=150,
            description="专注奖励"
        )

        # 测试is_earning方法
        assert earn_transaction.is_earning() is True
        assert earn_transaction.is_spending() is False

        # 测试get_formatted_change方法（正数）
        earn_formatted = earn_transaction.get_formatted_change()
        assert earn_formatted == "+50"

        # 测试消费积分交易
        spend_transaction = PointsTransaction(
            user_id="user123",
            transaction_type=TransactionType.SPEND,
            points_change=-30,
            balance_before=150,
            balance_after=120,
            description="兑换奖励"
        )

        # 测试is_spending方法
        assert spend_transaction.is_spending() is True
        assert spend_transaction.is_earning() is False

        # 测试get_formatted_change方法（负数）
        spend_formatted = spend_transaction.get_formatted_change()
        assert spend_formatted == "-30"

        # 测试__str__方法
        earn_str = str(earn_transaction)
        assert "获得" in earn_str
        assert "50" in earn_str
        assert "积分" in earn_str

        spend_str = str(spend_transaction)
        assert "消费" in spend_str
        assert "30" in spend_str
        assert "积分" in spend_str

        # 测试__repr__方法
        repr_str = repr(earn_transaction)
        assert "PointsTransaction" in repr_str
        assert earn_transaction.id in repr_str

        # 测试零变化交易
        zero_transaction = PointsTransaction(
            user_id="user123",
            transaction_type=TransactionType.BONUS,
            points_change=0,
            balance_before=120,
            balance_after=120,
            description="平衡调整"
        )

        zero_formatted = zero_transaction.get_formatted_change()
        assert zero_formatted == "+0"