"""
积分和奖励系统数据模型

包含积分购买、支付管理、奖励兑换等相关数据模型。
严格按照参考文档设计的数据结构。
"""

from sqlalchemy import Column, String, Integer, DECIMAL, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import BaseModel


class PointsPackage(BaseModel):
    """
    积分套餐模型

    定义积分购买的套餐信息，包括价格、积分数量、优惠等。
    """
    __tablename__ = "points_packages"

    name = Column(String(100), nullable=False, comment="套餐名称")
    description = Column(Text, comment="套餐描述")
    points_amount = Column(Integer, nullable=False, comment="积分数量")
    price = Column(DECIMAL(10, 2), nullable=False, comment="价格（元）")
    currency = Column(String(3), default="CNY", comment="计价货币")
    bonus_points = Column(Integer, default=0, comment="赠送积分")
    discount_percentage = Column(Integer, default=0, comment="折扣百分比")
    valid_until = Column(DateTime(timezone=True), comment="有效期至")
    is_active = Column(Boolean, default=True, comment="是否激活")
    sort_order = Column(Integer, default=0, comment="排序顺序")

    # 关系
    purchase_orders = relationship("PurchaseOrder", back_populates="package")

    # 索引
    __table_args__ = (
        Index('idx_points_packages_active_sort', 'is_active', 'sort_order'),
    )


class PurchaseOrder(BaseModel):
    """
    购买订单模型

    定义用户购买积分的订单信息，包括订单状态、支付信息等。
    """
    __tablename__ = "purchase_orders"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    package_id = Column(UUID(as_uuid=True), ForeignKey("points_packages.id"), nullable=False, comment="套餐ID")
    package_name = Column(String(100), nullable=False, comment="套餐名称（冗余存储）")
    points_amount = Column(Integer, nullable=False, comment="积分数量")
    price = Column(DECIMAL(10, 2), nullable=False, comment="价格")
    currency = Column(String(3), default="CNY", comment="货币")
    order_status = Column(String(20), nullable=False, default="pending", comment="订单状态")
    payment_method = Column(String(50), comment="支付方式")
    payment_info = Column(JSON, comment="支付信息（二维码、交易ID等）")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="订单过期时间")

    # 关系
    user = relationship("User", back_populates="purchase_orders")
    package = relationship("PointsPackage", back_populates="purchase_orders")
    payment_record = relationship("PaymentRecord", back_populates="order", uselist=False)

    # 索引
    __table_args__ = (
        Index('idx_purchase_orders_user_id', 'user_id'),
        Index('idx_purchase_orders_status', 'order_status'),
        Index('idx_purchase_orders_created_at', 'created_at'),
        Index('idx_purchase_orders_expires_at', 'expires_at'),
    )


class PaymentRecord(BaseModel):
    """
    支付记录模型

    定义订单的支付详细信息，包括支付方式、交易ID、支付时间等。
    """
    __tablename__ = "payment_records"

    order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, comment="订单ID")
    payment_method = Column(String(50), nullable=False, comment="支付方式（alipay, wechat, mock）")
    transaction_id = Column(String(100), comment="第三方交易ID")
    paid_amount = Column(DECIMAL(10, 2), nullable=False, comment="实付金额")
    currency = Column(String(3), default="CNY", comment="货币")
    payment_status = Column(String(20), nullable=False, comment="支付状态")
    payment_details = Column(JSON, comment="支付详情")
    paid_at = Column(DateTime(timezone=True), comment="支付时间")

    # 关系
    order = relationship("PurchaseOrder", back_populates="payment_record")

    # 索引
    __table_args__ = (
        Index('idx_payment_records_order_id', 'order_id'),
        Index('idx_payment_records_transaction_id', 'transaction_id'),
        Index('idx_payment_records_paid_at', 'paid_at'),
    )


class UserPoints(BaseModel):
    """
    用户积分账户模型

    定义用户的积分账户信息，包括当前余额、获得消费统计等。
    """
    __tablename__ = "user_points"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, comment="用户ID")
    current_balance = Column(Integer, default=0, comment="当前余额")
    total_earned = Column(Integer, default=0, comment="总获得")
    total_spent = Column(Integer, default=0, comment="总消费")
    last_earned_at = Column(DateTime(timezone=True), comment="最后获得时间")
    last_spent_at = Column(DateTime(timezone=True), comment="最后消费时间")

    # 关系
    user = relationship("User", back_populates="points_account")


class PointsTransaction(BaseModel):
    """
    积分交易流水模型

    定义用户积分的变动记录，包括获得、消费、类型、来源等。
    """
    __tablename__ = "points_transactions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    transaction_type = Column(String(20), nullable=False, comment="交易类型（earn/spend）")
    amount = Column(Integer, nullable=False, comment="积分数量")
    source = Column(String(50), comment="来源（task_complete/purchase/redemption）")
    description = Column(String(200), comment="描述")
    related_id = Column(UUID(as_uuid=True), comment="关联ID（订单ID、任务ID等）")
    balance_before = Column(Integer, comment="变动前余额")
    balance_after = Column(Integer, comment="变动后余额")

    # 关系
    user = relationship("User", back_populates="points_transactions")

    # 索引
    __table_args__ = (
        Index('idx_points_transactions_user_id', 'user_id'),
        Index('idx_points_transactions_type', 'transaction_type'),
        Index('idx_points_transactions_created_at', 'created_at'),
        Index('idx_points_transactions_source', 'source'),
    )


class Reward(BaseModel):
    """
    奖励模型

    定义可兑换的奖励信息，包括名称、描述、所需碎片等。
    """
    __tablename__ = "rewards"

    name = Column(String(100), nullable=False, comment="奖励名称")
    description = Column(Text, comment="奖励描述")
    icon = Column(String(500), comment="图标URL")
    points_value = Column(Integer, comment="积分价值")
    amount_to_collect = Column(Integer, comment="所需碎片数")
    category = Column(String(50), comment="奖励分类")
    is_available = Column(Boolean, default=True, comment="是否可用")
    sort_order = Column(Integer, default=0, comment="排序顺序")

    # 关系
    user_fragments = relationship("UserFragment", back_populates="reward")
    redemption_records = relationship("RedemptionRecord", back_populates="reward")


class UserFragment(BaseModel):
    """
    用户碎片模型

    定义用户获得的碎片记录。
    """
    __tablename__ = "user_fragments"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    reward_id = Column(UUID(as_uuid=True), ForeignKey("rewards.id"), nullable=False, comment="奖励ID")
    obtained_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), comment="获得时间")
    source_type = Column(String(50), comment="获得来源类型")
    source_id = Column(UUID(as_uuid=True), comment="获得来源ID")

    # 关系
    user = relationship("User", back_populates="user_fragments")
    reward = relationship("Reward", back_populates="user_fragments")

    # 索引
    __table_args__ = (
        Index('idx_user_fragments_user_id', 'user_id'),
        Index('idx_user_fragments_reward_id', 'reward_id'),
        Index('idx_user_fragments_obtained_at', 'obtained_at'),
    )


class RedemptionRecord(BaseModel):
    """
    兑换记录模型

    定义用户的奖励兑换记录。
    """
    __tablename__ = "redemption_records"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    type = Column(String(50), nullable=False, comment="兑换类型")
    fragment_ids = Column(JSON, comment="兑换的碎片ID列表")
    reward_id = Column(UUID(as_uuid=True), ForeignKey("rewards.id"), comment="兑换的奖品ID")
    points_gained = Column(Integer, comment="获得积分数")

    # 关系
    user = relationship("User", back_populates="redemption_records")
    reward = relationship("Reward", back_populates="redemption_records")

    # 索引
    __table_args__ = (
        Index('idx_redemption_records_user_id', 'user_id'),
        Index('idx_redemption_records_type', 'type'),
        Index('idx_redemption_records_created_at', 'created_at'),
    )


class LotteryRecord(BaseModel):
    """
    抽奖记录模型

    定义用户的抽奖记录，包括抽奖结果、获得奖励等。
    """
    __tablename__ = "lottery_records"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), comment="关联任务ID")
    reward_type = Column(String(20), nullable=False, comment="奖励类型")
    points_amount = Column(Integer, comment="获得积分数")
    fragment_id = Column(UUID(as_uuid=True), ForeignKey("rewards.id"), comment="获得碎片ID")
    fragment_name = Column(String(100), comment="碎片名称")
    mood_feedback = Column(JSON, comment="心情反馈")
    lottery_pool_type = Column(String(50), comment="奖池类型")

    # 关系
    user = relationship("User", back_populates="lottery_records")
    task = relationship("Task", back_populates="lottery_records")
    fragment = relationship("Reward")

    # 索引
    __table_args__ = (
        Index('idx_lottery_records_user_id', 'user_id'),
        Index('idx_lottery_records_task_id', 'task_id'),
        Index('idx_lottery_records_created_at', 'created_at'),
        Index('idx_lottery_records_reward_type', 'reward_type'),
    )