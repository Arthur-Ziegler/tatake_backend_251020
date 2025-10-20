"""
积分购买系统服务层

实现积分购买的核心业务逻辑，包括：
1. 积分套餐管理
2. 订单创建和管理
3. Mock支付系统
4. 积分到账处理
5. 支付状态跟踪

设计原则：
1. 完整的订单状态流转
2. Mock支付系统模拟真实支付流程
3. 积分变动的原子性操作
4. 支付安全和权限验证
5. 详细的操作日志记录
"""

import uuid
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..models.points import (
    PointsPackage, PurchaseOrder, PaymentRecord,
    UserPoints, PointsTransaction
)
from ..models.reward import Reward
# 暂时注释掉不存在的模型
# from ..models.base import UserFragment, RedemptionRecord
from ..models.user import User
from .exceptions import BusinessException, ValidationException, ResourceNotFoundException


class PointsService:
    """积分购买系统服务类"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_available_packages(self) -> List[Dict]:
        """
        获取可用的积分套餐列表

        Returns:
            List[Dict]: 积分套餐列表
        """
        try:
            # 查询所有激活的积分套餐
            query = select(PointsPackage).where(
                and_(
                    PointsPackage.is_active == True,
                    or_(
                        PointsPackage.valid_until.is_(None),
                        PointsPackage.valid_until > datetime.now(timezone.utc)
                    )
                )
            ).order_by(PointsPackage.sort_order, PointsPackage.price)

            result = await self.session.execute(query)
            packages = result.scalars().all()

            # 转换为字典格式
            return [
                {
                    "id": str(package.id),
                    "name": package.name,
                    "description": package.description,
                    "points_amount": package.points_amount,
                    "price": float(package.price),
                    "currency": package.currency,
                    "bonus_points": package.bonus_points,
                    "discount_percentage": package.discount_percentage,
                    "valid_until": package.valid_until.isoformat() if package.valid_until else None
                }
                for package in packages
            ]

        except Exception as e:
            raise BusinessException(f"获取积分套餐失败: {str(e)}")

    async def create_purchase_order(
        self,
        user_id: str,
        package_id: str
    ) -> Dict:
        """
        创建购买订单

        Args:
            user_id: 用户ID
            package_id: 套餐ID

        Returns:
            Dict: 订单信息和支付信息
        """
        try:
            # 验证套餐存在且有效
            package = await self._get_valid_package(package_id)
            if not package:
                raise ResourceNotFoundException("积分套餐不存在或已过期")

            # 生成订单ID
            order_id = str(uuid.uuid4())

            # 设置订单过期时间（30分钟）
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

            # 创建订单
            order = PurchaseOrder(
                id=order_id,
                user_id=user_id,
                package_id=package_id,
                package_name=package.name,
                points_amount=package.points_amount + package.bonus_points,
                price=package.price,
                currency=package.currency,
                order_status="pending",
                expires_at=expires_at,
                payment_info={}
            )

            self.session.add(order)
            await self.session.flush()  # 获取订单ID

            # 生成Mock支付信息
            payment_info = self._generate_mock_payment_info(order_id, package.price)

            # 更新订单支付信息
            order.payment_info = payment_info

            await self.session.commit()

            return {
                "order_info": {
                    "order_id": order_id,
                    "package_name": package.name,
                    "points_amount": order.points_amount,
                    "price": float(package.price),
                    "currency": package.currency
                },
                "payment_info": payment_info,
                "order_status": "pending"
            }

        except Exception as e:
            await self.session.rollback()
            raise BusinessException(f"创建购买订单失败: {str(e)}")

    async def get_purchase_details(self, user_id: str, order_id: str) -> Dict:
        """
        获取购买订单详情

        Args:
            user_id: 用户ID
            order_id: 订单ID

        Returns:
            Dict: 订单详情和支付状态
        """
        try:
            # 查询订单信息
            query = select(PurchaseOrder).where(
                and_(
                    PurchaseOrder.id == order_id,
                    PurchaseOrder.user_id == user_id
                )
            )
            result = await self.session.execute(query)
            order = result.scalar_one_or_none()

            if not order:
                raise ResourceNotFoundException("订单不存在")

            # 检查订单是否过期
            if order.order_status == "pending" and datetime.now(timezone.utc) > order.expires_at:
                order.order_status = "expired"
                await self.session.commit()

            # 查询支付记录
            payment_query = select(PaymentRecord).where(
                PaymentRecord.order_id == order_id
            )
            payment_result = await self.session.execute(payment_query)
            payment_record = payment_result.scalar_one_or_none()

            payment_details = None
            if payment_record:
                payment_details = {
                    "payment_method": payment_record.payment_method,
                    "transaction_id": payment_record.transaction_id,
                    "paid_amount": float(payment_record.paid_amount),
                    "currency": payment_record.currency,
                    "payment_status": payment_record.payment_status,
                    "payment_details": payment_record.payment_details,
                    "paid_at": payment_record.paid_at.isoformat() if payment_record.paid_at else None
                }

            return {
                "order_info": {
                    "order_id": order_id,
                    "package_name": order.package_name,
                    "points_amount": order.points_amount,
                    "price": float(order.price),
                    "currency": order.currency,
                    "created_at": order.created_at.isoformat(),
                    "paid_at": payment_record.paid_at.isoformat() if payment_record and payment_record.paid_at else None,
                    "expires_at": order.expires_at.isoformat()
                },
                "order_status": order.order_status,
                "payment_details": payment_details
            }

        except Exception as e:
            raise BusinessException(f"获取订单详情失败: {str(e)}")

    async def process_mock_payment(self, order_id: str) -> bool:
        """
        处理Mock支付（用于测试）

        Args:
            order_id: 订单ID

        Returns:
            bool: 支付是否成功
        """
        try:
            # 查询订单
            query = select(PurchaseOrder).where(
                and_(
                    PurchaseOrder.id == order_id,
                    PurchaseOrder.order_status == "pending",
                    PurchaseOrder.expires_at > datetime.now(timezone.utc)
                )
            )
            result = await self.session.execute(query)
            order = result.scalar_one_or_none()

            if not order:
                return False

            # 模拟支付处理
            payment_success = self._simulate_payment_process()

            if payment_success:
                # 创建支付记录
                payment_record = PaymentRecord(
                    id=str(uuid.uuid4()),
                    order_id=order_id,
                    payment_method="mock",
                    transaction_id=f"mock_tx_{int(time.time())}",
                    paid_amount=order.price,
                    currency=order.currency,
                    payment_status="success",
                    payment_details={
                        "mock_payment": True,
                        "processed_at": datetime.now(timezone.utc).isoformat()
                    },
                    paid_at=datetime.now(timezone.utc)
                )

                self.session.add(payment_record)

                # 更新订单状态
                order.order_status = "paid"

                # 积分到账
                await self._credit_points_to_user(
                    order.user_id,
                    order.points_amount,
                    "purchase",
                    order_id
                )

                await self.session.commit()
                return True
            else:
                # 支付失败
                order.order_status = "failed"
                await self.session.commit()
                return False

        except Exception as e:
            await self.session.rollback()
            raise BusinessException(f"处理支付失败: {str(e)}")

    async def _get_valid_package(self, package_id: str) -> Optional[PointsPackage]:
        """获取有效的积分套餐"""
        query = select(PointsPackage).where(
            and_(
                PointsPackage.id == package_id,
                PointsPackage.is_active == True,
                or_(
                    PointsPackage.valid_until.is_(None),
                    PointsPackage.valid_until > datetime.now(timezone.utc)
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def _generate_mock_payment_info(self, order_id: str, amount: float) -> Dict:
        """生成Mock支付信息"""
        return {
            "qrcode_url": f"https://mock-payment.example.com/qr/{order_id}",
            "qrcode_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            "payment_methods": ["alipay", "wechat", "mock"],
            "mock_payment_id": f"mock_{order_id}"
        }

    def _simulate_payment_process(self) -> bool:
        """模拟支付处理过程（90%成功率）"""
        import random
        return random.random() < 0.9

    async def _credit_points_to_user(
        self,
        user_id: str,
        amount: int,
        source: str,
        related_id: str
    ) -> None:
        """积分到账处理"""
        try:
            # 获取或创建用户积分账户
            user_points_query = select(UserPoints).where(
                UserPoints.user_id == user_id
            )
            result = await self.session.execute(user_points_query)
            user_points = result.scalar_one_or_none()

            if not user_points:
                # 创建积分账户
                user_points = UserPoints(
                    user_id=user_id,
                    current_balance=0,
                    total_earned=0,
                    total_spent=0
                )
                self.session.add(user_points)
                await self.session.flush()

            # 记录变动前余额
            balance_before = user_points.current_balance

            # 更新积分账户
            user_points.current_balance += amount
            user_points.total_earned += amount
            user_points.last_earned_at = datetime.now(timezone.utc)

            # 创建积分交易记录
            transaction = PointsTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type="earn",
                amount=amount,
                source=source,
                description=f"积分购买获得 {amount} 积分",
                related_id=related_id,
                balance_before=balance_before,
                balance_after=user_points.current_balance
            )

            self.session.add(transaction)

        except Exception as e:
            raise BusinessException(f"积分到账处理失败: {str(e)}")

    async def get_user_fragments_collection(self, user_id: str) -> Dict:
        """
        获取用户碎片收集状态

        Args:
            user_id: 用户ID

        Returns:
            Dict: 碎片收集状态信息
        """
        try:
            # 查询所有可收集的奖励
            rewards_query = select(Reward).where(Reward.is_available == True)
            rewards_result = await self.session.execute(rewards_query)
            all_rewards = rewards_result.scalars().all()

            # 查询用户拥有的碎片 - TODO: 实现UserFragment模型
            # fragments_query = select(UserFragment).where(UserFragment.user_id == user_id)
            # fragments_result = await self.session.execute(fragments_query)
            # user_fragments = fragments_result.scalars().all()
            user_fragments = []  # 临时空列表，等模型创建后再实现

            # 统计用户碎片
            user_fragment_counts = {}
            for fragment in user_fragments:
                reward_id = str(fragment.reward_id)
                user_fragment_counts[reward_id] = user_fragment_counts.get(reward_id, 0) + 1

            # 构建碎片列表和收集状态
            fragments = []
            completed_collections = 0
            in_progress_collections = 0
            total_points_value = 0

            for reward in all_rewards:
                reward_id = str(reward.id)
                user_count = user_fragment_counts.get(reward_id, 0)
                required_count = reward.amount_to_collect or 1
                is_completed = user_count >= required_count

                if is_completed:
                    completed_collections += 1
                elif user_count > 0:
                    in_progress_collections += 1

                # 计算积分价值
                points_value = user_count * (reward.points_value or 0)
                total_points_value += points_value

                fragments.append({
                    "id": reward_id,
                    "name": reward.name,
                    "description": reward.description,
                    "icon": reward.icon,
                    "category": reward.category,
                    "collected_count": user_count,
                    "required_count": required_count,
                    "completion_percentage": min(user_count / required_count * 100, 100) if required_count > 0 else 0,
                    "is_completed": is_completed,
                    "can_redeem": is_completed,
                    "points_value": reward.points_value,
                    "total_points_value": points_value
                })

            # 构建收集摘要
            total_fragment_types = len(all_rewards)
            completion_rate = (completed_collections / total_fragment_types * 100) if total_fragment_types > 0 else 0

            collection_summary = {
                "total_fragment_types": total_fragment_types,
                "completed_collections": completed_collections,
                "in_progress_collections": in_progress_collections,
                "not_started_collections": total_fragment_types - completed_collections - in_progress_collections,
                "completion_rate": round(completion_rate, 2),
                "total_points_value": total_points_value
            }

            return {
                "fragments": fragments,
                "collection_summary": collection_summary
            }

        except Exception as e:
            raise BusinessException(f"获取碎片收集状态失败: {str(e)}")

    async def redeem_reward(
        self,
        user_id: str,
        reward_ids: List[str],
        redemption_type: str
    ) -> Dict:
        """
        兑换奖励

        Args:
            user_id: 用户ID
            reward_ids: 奖励ID列表
            redemption_type: 兑换类型

        Returns:
            Dict: 兑换结果
        """
        try:
            if redemption_type == "fragment_to_points":
                # 碎片兑换积分
                return await self._redeem_fragments_to_points(user_id, reward_ids)
            elif redemption_type == "fragment_to_reward":
                # 碎片兑换奖品
                return await self._redeem_fragments_to_reward(user_id, reward_ids)
            else:
                raise ValidationException("无效的兑换类型")

        except Exception as e:
            raise BusinessException(f"兑换奖励失败: {str(e)}")

    async def _redeem_fragments_to_points(self, user_id: str, reward_ids: List[str]) -> Dict:
        """碎片兑换积分"""
        total_points = 0
        redeemed_fragments = []

        for reward_id in reward_ids:
            # 查询奖励信息
            reward_query = select(Reward).where(Reward.id == reward_id)
            reward_result = await self.session.execute(reward_query)
            reward = reward_result.scalar_one_or_none()

            if not reward or not reward.points_value:
                continue

            # 查询用户拥有的碎片 - TODO: 实现UserFragment模型
            # fragment_query = select(UserFragment).where(
            #     and_(
            #         UserFragment.user_id == user_id,
            #         UserFragment.reward_id == reward_id
            #     )
            # ).limit(1)
            # fragment_result = await self.session.execute(fragment_query)
            # fragment = fragment_result.scalar_one_or_none()

            # if fragment:
            #     # 删除碎片
            #     await self.session.delete(fragment)
            #     total_points += reward.points_value
            #     redeemed_fragments.append({
            #         "reward_id": reward_id,
            #         "reward_name": reward.name,
            #         "points_gained": reward.points_value
            #     })

            # 临时跳过碎片兑换逻辑
            continue

        # 积分到账
        if total_points > 0:
            await self._credit_points_to_user(
                user_id,
                total_points,
                "redemption",
                f"fragment_to_points_{int(time.time())}"
            )

        # 创建兑换记录 - TODO: 实现RedemptionRecord模型
        # redemption_record = RedemptionRecord(
        #     id=str(uuid.uuid4()),
        #     user_id=user_id,
        #     type="fragment_to_points",
        #     fragment_ids=reward_ids,
        #     points_gained=total_points
        # )
        # self.session.add(redemption_record)

        # 临时跳过兑换记录创建
        pass

        await self.session.commit()

        return {
            "redemption_type": "fragment_to_points",
            "total_points_gained": total_points,
            "redeemed_fragments": redeemed_fragments,
            "messages": [f"成功兑换 {total_points} 积分"]
        }

    async def _redeem_fragments_to_reward(self, user_id: str, reward_ids: List[str]) -> Dict:
        """碎片兑换奖品"""
        # TODO: 实现碎片兑换奖品逻辑
        raise BusinessException("碎片兑换奖品功能正在开发中")


class MockPaymentService:
    """Mock支付服务"""

    @staticmethod
    def generate_qr_code(order_id: str, amount: float) -> str:
        """生成支付二维码URL"""
        return f"https://mock-payment.example.com/qr/{order_id}?amount={amount}"

    @staticmethod
    def simulate_payment_scan(qr_data: str) -> Dict:
        """模拟扫码支付"""
        return {
            "scanned": True,
            "payment_id": f"mock_payment_{int(time.time())}",
            "amount": float(qr_data.split("amount=")[1]) if "amount=" in qr_data else 0.0,
            "status": "processing"
        }

    @staticmethod
    def check_payment_status(payment_id: str) -> Dict:
        """检查支付状态"""
        import random

        # 模拟支付状态检查
        statuses = ["processing", "success", "failed"]
        weights = [0.1, 0.8, 0.1]  # 80%成功率

        status = random.choices(statuses, weights=weights)[0]

        return {
            "payment_id": payment_id,
            "status": status,
            "paid_at": datetime.now(timezone.utc).isoformat() if status == "success" else None,
            "transaction_id": f"tx_{payment_id}" if status == "success" else None
        }