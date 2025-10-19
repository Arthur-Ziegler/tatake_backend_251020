"""
奖励系统相关数据模型

本模块定义了奖励系统相关的数据模型，包括：
- Reward: 奖励信息模型，用户可以兑换的各种奖励
- RewardRule: 奖励规则模型，自动发放奖励的规则定义
- UserFragment: 用户碎片模型，记录用户的碎片数量和交易历史
- LotteryRecord: 抽奖记录模型，用户抽奖活动的记录
- PointsTransaction: 积分流水模型，用户积分变化的详细记录

设计原则：
1. 激励导向：通过奖励系统激励用户保持专注和良好习惯
2. 透明记录：所有交易和活动都有详细记录，支持查询和统计
3. 灵活配置：支持多种奖励类型和自定义规则
4. 数据完整：完整的用户资产管理和交易历史

使用示例：
    >>> reward = Reward(name="专注达人", reward_type=RewardType.BADGE, cost_fragments=100)
    >>> user_fragment = UserFragment(user_id="user123", fragment_count=150)
    >>> if user_fragment.can_afford(reward.cost_fragments):
    ...     user_fragment.spend_fragments(reward.cost_fragments)
"""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

# 导入基础模型类和枚举
from src.models.base_model import BaseSQLModel
from src.models.enums import RewardType, RewardStatus, TransactionType

# 避免循环导入的类型检查
if TYPE_CHECKING:
    pass


class Reward(BaseSQLModel, table=True):
    """
    奖励信息模型

    存储用户可以兑换的各种奖励信息，包括徽章、头像框、称号等。
    用户通过消耗碎片来兑换奖励，激励用户完成专注任务。

    Attributes:
        name (str): 奖励名称，必填字段，用户显示
        description (Optional[str]): 奖励描述，详细说明奖励内容和价值
        reward_type (RewardType): 奖励类型，枚举类型标识奖励类别
        cost_fragments (int): 需要的碎片数量，必填字段
        image_url (Optional[str]): 奖励图片URL，可选字段
        is_active (bool): 是否激活，默认True
        user_id (str): 用户ID，外键关联到User表
        user (User): 关联的用户，多对一关系
    """

    __tablename__ = "rewards"

    # 基本信息
    name: str = Field(
        max_length=100,
        description="奖励名称，用户显示和识别"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="奖励描述，详细说明奖励内容和价值"
    )

    # 奖励配置
    reward_type: RewardType = Field(
        description="奖励类型，枚举类型标识奖励类别"
    )

    cost_fragments: int = Field(
        ge=0,
        description="需要的碎片数量，必填字段"
    )

    image_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description="奖励图片URL，支持HTTP/HTTPS协议"
    )

    # 状态字段
    is_active: bool = Field(
        default=True,
        description="是否激活，True表示用户可见"
    )

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识奖励归属"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回奖励的字符串表示

        Returns:
            str: 奖励的基本信息表示

        Example:
            >>> reward = Reward(name="专注达人", reward_type=RewardType.BADGE, cost_fragments=100, user_id="user123")
            >>> print(repr(reward))
            Reward(id=uuid-string)
        """
        return f"Reward(id={self.id})"

    def __str__(self) -> str:
        """
        返回奖励友好的字符串表示

        Returns:
            str: 奖励的名称表示

        Example:
            >>> reward = Reward(name="专注达人", reward_type=RewardType.BADGE, cost_fragments=100, user_id="user123")
            >>> print(str(reward))
            专注达人
        """
        return self.name

    def is_affordable(self, user_fragments: int) -> bool:
        """
        判断用户是否有足够碎片兑换奖励

        Args:
            user_fragments (int): 用户当前拥有的碎片数量

        Returns:
            bool: 如果用户碎片足够返回True，否则返回False

        Example:
            >>> reward = Reward(name="测试奖励", cost_fragments=50, user_id="user123")
            >>> print(reward.is_affordable(100))
            True
            >>> print(reward.is_affordable(30))
            False
        """
        return user_fragments >= self.cost_fragments

    def get_display_cost(self) -> str:
        """
        获取用户友好的成本显示字符串

        Returns:
            str: 格式化的成本显示

        Example:
            >>> reward = Reward(name="测试奖励", cost_fragments=50, user_id="user123")
            >>> print(reward.get_display_cost())
            "50 碎片"
        """
        return f"{self.cost_fragments} 碎片"

    def can_be_equipped(self) -> bool:
        """
        判断奖励是否可以装备

        Returns:
            bool: 如果奖励可以装备返回True，否则返回False

        Example:
            >>> avatar_reward = Reward(reward_type=RewardType.AVATAR_FRAME, user_id="user123")
            >>> print(avatar_reward.can_be_equipped())
            True
            >>> achievement_reward = Reward(reward_type=RewardType.ACHIEVEMENT, user_id="user123")
            >>> print(achievement_reward.can_be_equipped())
            False
        """
        return self.reward_type in [RewardType.AVATAR_FRAME, RewardType.THEME]


class RewardRule(BaseSQLModel, table=True):
    """
    奖励规则模型

    定义自动发放奖励的规则，支持多种条件触发和奖励发放。
    用于激励用户达成特定目标和保持良好习惯。

    Attributes:
        name (str): 规则名称，必填字段
        description (Optional[str]): 规则描述，详细说明规则内容
        condition_type (str): 条件类型，如专注时长、连续天数等
        condition_value (int): 条件值，触发条件的具体数值
        reward_type (str): 奖励类型，如碎片、徽章等
        reward_value (int): 奖励数值，发放的具体数量
        is_active (bool): 是否激活，默认True
        user_id (str): 用户ID，外键关联到User表
        user (User): 关联的用户，多对一关系
    """

    __tablename__ = "reward_rules"

    # 基本信息
    name: str = Field(
        max_length=100,
        description="规则名称，用户显示和识别"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="规则描述，详细说明规则内容和目的"
    )

    # 条件配置
    condition_type: str = Field(
        max_length=50,
        description="条件类型，如专注时长、连续天数等"
    )

    condition_value: int = Field(
        description="条件值，触发条件的具体数值"
    )

    # 奖励配置
    reward_type: str = Field(
        max_length=50,
        description="奖励类型，如碎片、徽章等"
    )

    reward_value: int = Field(
        description="奖励数值，发放的具体数量"
    )

    # 状态字段
    is_active: bool = Field(
        default=True,
        description="是否激活，True表示规则生效"
    )

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表，标识规则归属"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回奖励规则的字符串表示

        Returns:
            str: 奖励规则的基本信息表示
        """
        return f"RewardRule(id={self.id})"

    def __str__(self) -> str:
        """
        返回奖励规则友好的字符串表示

        Returns:
            str: 奖励规则的名称表示
        """
        return self.name

    def check_condition(self, actual_value: int) -> bool:
        """
        检查是否满足触发条件

        Args:
            actual_value (int): 实际达到的数值

        Returns:
            bool: 如果满足条件返回True，否则返回False

        Example:
            >>> rule = RewardRule(
            ...     name="专注新手",
            ...     condition_type="focus_hours",
            ...     condition_value=10,
            ...     user_id="user123"
            ... )
            >>> print(rule.check_condition(15))
            True
            >>> print(rule.check_condition(5))
            False
        """
        return actual_value >= self.condition_value

    def get_reward_description(self) -> str:
        """
        获取奖励描述

        Returns:
            str: 格式化的奖励描述

        Example:
            >>> rule = RewardRule(
            ...     name="专注新手",
            ...     condition_type="focus_hours",
            ...     condition_value=10,
            ...     reward_type="fragments",
            ...     reward_value=50,
            ...     user_id="user123"
            ... )
            >>> print(rule.get_reward_description())
            "获得50个碎片"
        """
        return f"获得{self.reward_value}个{self.reward_type}"


class UserFragment(BaseSQLModel, table=True):
    """
    用户碎片模型

    记录用户的碎片数量和交易历史，支持碎片获取、消费和查询。
    碎片是应用中的虚拟货币，用于兑换奖励。

    Attributes:
        user_id (str): 用户ID，外键关联到User表
        fragment_count (int): 当前碎片数量
        total_earned (int): 总共获得的碎片数量
        total_spent (int): 总共消费的碎片数量
        last_earned_at (Optional[datetime]): 最后获得时间
        user (User): 关联的用户，多对一关系
        transactions (List[PointsTransaction]): 碎片交易记录，一对多关系
    """

    __tablename__ = "user_fragments"

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        unique=True,
        index=True,
        description="用户ID，与User表建立一对一关系"
    )

    # 碎片数量
    fragment_count: int = Field(
        default=0,
        ge=0,
        description="当前碎片数量"
    )

    total_earned: int = Field(
        default=0,
        ge=0,
        description="总共获得的碎片数量"
    )

    total_spent: int = Field(
        default=0,
        ge=0,
        description="总共消费的碎片数量"
    )

    # 时间记录
    last_earned_at: Optional[datetime] = Field(
        default=None,
        description="最后获得碎片的时间"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    # transactions: list["PointsTransaction"] = Relationship(
    #     back_populates="user_fragments",
    #     sa_relationship_kwargs={
    #         "cascade": "all, delete-orphan",
    #         "lazy": "select"
    #     }
    # )

    def __repr__(self) -> str:
        """
        返回用户碎片的字符串表示

        Returns:
            str: 用户碎片的基本信息表示
        """
        return f"UserFragment(id={self.id})"

    def __str__(self) -> str:
        """
        返回用户碎片友好的字符串表示

        Returns:
            str: 用户碎片的数量表示
        """
        return f"User {self.user_id}: {self.fragment_count} fragments"

    def can_afford(self, cost: int) -> bool:
        """
        判断是否有足够碎片支付指定数量

        Args:
            cost (int): 需要的碎片数量

        Returns:
            bool: 如果碎片足够返回True，否则返回False

        Example:
            >>> fragments = UserFragment(user_id="user123", fragment_count=100)
            >>> print(fragments.can_afford(50))
            True
            >>> print(fragments.can_afford(150))
            False
        """
        return self.fragment_count >= cost

    def earn_fragments(self, amount: int) -> None:
        """
        获得碎片

        Args:
            amount (int): 获得的碎片数量

        Example:
            >>> fragments = UserFragment(user_id="user123", fragment_count=50)
            >>> fragments.earn_fragments(25)
            >>> print(fragments.fragment_count)
            75
        """
        if amount > 0:
            self.fragment_count += amount
            self.total_earned += amount
            self.last_earned_at = datetime.now(timezone.utc)

    def spend_fragments(self, amount: int) -> bool:
        """
        消费碎片

        Args:
            amount (int): 消费的碎片数量

        Returns:
            bool: 如果消费成功返回True，否则返回False

        Example:
            >>> fragments = UserFragment(user_id="user123", fragment_count=50)
            >>> success = fragments.spend_fragments(30)
            >>> print(success, fragments.fragment_count)
            True 20
        """
        if amount > 0 and self.can_afford(amount):
            self.fragment_count -= amount
            self.total_spent += amount
            return True
        return False

    def get_spending_rate(self) -> float:
        """
        计算碎片消费率

        Returns:
            float: 消费率，已消费/总获得的百分比

        Example:
            >>> fragments = UserFragment(
            ...     user_id="user123",
            ...     fragment_count=60,
            ...     total_earned=100,
            ...     total_spent=40
            ... )
            >>> print(fragments.get_spending_rate())
            0.4
        """
        if self.total_earned == 0:
            return 0.0
        return self.total_spent / self.total_earned


class LotteryRecord(BaseSQLModel, table=True):
    """
    抽奖记录模型

    记录用户参与抽奖活动的详细信息，包括消费、结果和奖励发放。
    支持多种抽奖类型和概率配置。

    Attributes:
        user_id (str): 用户ID，外键关联到User表
        reward_id (Optional[str]): 中奖奖励ID，外键关联到Reward表
        cost_fragments (int): 消耗的碎片数量
        result_type (str): 抽奖结果类型
        won (bool): 是否中奖
        reward_name (Optional[str]): 中奖奖励名称
        user (User): 关联的用户，多对一关系
        reward (Optional[Reward]): 中奖的奖励，多对一关系
    """

    __tablename__ = "lottery_records"

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表"
    )

    reward_id: Optional[str] = Field(
        default=None,
        foreign_key="rewards.id",
        index=True,
        description="中奖奖励ID，外键关联到Reward表"
    )

    # 抽奖信息
    cost_fragments: int = Field(
        ge=0,
        description="消耗的碎片数量"
    )

    result_type: str = Field(
        max_length=50,
        description="抽奖结果类型，如normal、rare、legendary等"
    )

    # 结果字段
    won: bool = Field(
        default=False,
        description="是否中奖"
    )

    reward_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="中奖奖励名称，用于显示"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    reward: Optional["Reward"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回抽奖记录的字符串表示

        Returns:
            str: 抽奖记录的基本信息表示
        """
        return f"LotteryRecord(id={self.id})"

    def __str__(self) -> str:
        """
        返回抽奖记录友好的字符串表示

        Returns:
            str: 抽奖结果的简要描述
        """
        result = "中奖" if self.won else "未中奖"
        return f"抽奖记录: {result}"


class PointsTransaction(BaseSQLModel, table=True):
    """
    积分流水模型

    记录用户积分变化的详细流水，支持多种交易类型和余额跟踪。
    提供完整的交易历史记录和统计分析功能。

    Attributes:
        user_id (str): 用户ID，外键关联到User表
        transaction_type (TransactionType): 交易类型，枚举类型
        points_change (int): 积分变化数量
        balance_before (int): 交易前余额
        balance_after (int): 交易后余额
        description (Optional[str]): 交易描述，详细说明交易原因
        user (User): 关联的用户，多对一关系
    """

    __tablename__ = "points_transactions"

    # 关联字段
    user_id: str = Field(
        foreign_key="users.id",
        index=True,
        description="用户ID，关联到User表"
    )

    # 交易信息
    transaction_type: TransactionType = Field(
        description="交易类型，枚举类型标识交易性质"
    )

    points_change: int = Field(
        description="积分变化数量，正数表示增加，负数表示减少"
    )

    # 余额信息
    balance_before: int = Field(
        description="交易前余额"
    )

    balance_after: int = Field(
        description="交易后余额"
    )

    # 描述字段
    description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="交易描述，详细说明交易原因"
    )

    # 关系定义
    user: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "select"
        }
    )

    def __repr__(self) -> str:
        """
        返回积分流水的字符串表示

        Returns:
            str: 积分流水的基本信息表示
        """
        return f"PointsTransaction(id={self.id})"

    def __str__(self) -> str:
        """
        返回积分流水友好的字符串表示

        Returns:
            str: 积分变化的简要描述
        """
        change_type = "获得" if self.points_change > 0 else "消费"
        return f"{change_type} {abs(self.points_change)} 积分"

    def is_earning(self) -> bool:
        """
        判断是否为获得积分的交易

        Returns:
            bool: 如果是获得积分返回True，否则返回False
        """
        return self.points_change > 0

    def is_spending(self) -> bool:
        """
        判断是否为消费积分的交易

        Returns:
            bool: 如果是消费积分返回True，否则返回False
        """
        return self.points_change < 0

    def get_formatted_change(self) -> str:
        """
        获取格式化的积分变化显示

        Returns:
            str: 带符号的积分变化显示

        Example:
            >>> transaction = PointsTransaction(points_change=50)
            >>> print(transaction.get_formatted_change())
            "+50"
            >>> transaction = PointsTransaction(points_change=-20)
            >>> print(transaction.get_formatted_change())
            "-20"
        """
        prefix = "+" if self.points_change >= 0 else ""
        return f"{prefix}{self.points_change}"


# 导出所有奖励系统模型
__all__ = [
    "Reward",
    "RewardRule",
    "UserFragment",
    "LotteryRecord",
    "PointsTransaction"
]