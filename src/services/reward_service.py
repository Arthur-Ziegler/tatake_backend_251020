"""
奖励服务模块

该模块实现奖励系统相关的业务逻辑，包括奖励目录管理、碎片收集、
积分系统、抽奖机制等功能。提供完整的游戏化激励体验。

设计原则：
1. 游戏化体验：碎片收集、抽奖、兑换等激励机制
2. 数据完整性：严格的积分和碎片管理
3. 业务规则：完整的兑换和抽奖规则验证
4. 用户体验：流畅的兑换流程和丰富的奖励内容
5. 安全机制：防作弊和异常检测

核心功能：
- 奖励目录管理
- 碎片收集和兑换
- 积分系统和套餐
- 抽奖机制
- 奖励兑换记录
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .base import BaseService
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    InsufficientBalanceException
)
from src.models.reward import Reward
from src.models.enums import RewardType, RewardStatus, TransactionType


class RewardService(BaseService):
    """
    奖励服务类

    处理奖励系统相关的所有业务逻辑，包括奖励管理、碎片收集、
    积分系统、抽奖机制等核心功能。

    Attributes:
        _user_repo: 用户数据访问对象
        _task_repo: 任务数据访问对象
        _focus_repo: 专注数据访问对象
        _reward_repo: 奖励数据访问对象
    """

    def __init__(self, user_repo, task_repo=None, focus_repo=None, reward_repo=None, **kwargs):
        """
        初始化奖励服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            **kwargs
        )

        # 抽奖配置
        self.lottery_config = {
            "fragment_cost": 5,      # 抽奖消耗碎片数
            "common_probability": 0.7,  # 普通奖品概率
            "rare_probability": 0.25,  # 稀有奖品概率
            "epic_probability": 0.04,  # 史诗奖品概率
            "legendary_probability": 0.01  # 传说奖品概率
        }

    # ==================== 奖励目录管理 ====================

    def get_rewards_catalog(
        self,
        category: Optional[str] = None,
        reward_type: Optional[str] = None,
        min_points: Optional[int] = None,
        max_points: Optional[int] = None,
        available_only: bool = True
    ) -> Dict[str, Any]:
        """
        获取可兑换奖品目录

        获取奖励目录，支持按分类、类型、积分范围等条件筛选。

        Args:
            category: 奖励分类（可选）
            reward_type: 奖励类型（可选）
            min_points: 最小积分要求（可选）
            max_points: 最大积分要求（可选）
            available_only: 只显示可用奖励（默认True）

        Returns:
            奖励目录列表

        Raises:
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("获取奖励目录", {
                "category": category,
                "reward_type": reward_type,
                "min_points": min_points,
                "max_points": max_points,
                "available_only": available_only
            })

            # 验证参数
            if min_points is not None and min_points < 0:
                raise ValidationException(
                    message="最小积分不能为负数",
                    details={"min_points": min_points}
                )

            if max_points is not None and max_points < 0:
                raise ValidationException(
                    message="最大积分不能为负数",
                    details={"max_points": max_points}
                )

            if min_points and max_points and min_points > max_points:
                raise ValidationException(
                    message="最小积分不能大于最大积分",
                    details={"min_points": min_points, "max_points": max_points}
                )

            # 构建筛选条件
            filters = {}
            if available_only:
                filters["is_available"] = True
            if category:
                filters["category"] = category
            if reward_type:
                filters["reward_type"] = reward_type

            # 查询奖励目录
            rewards = self.get_reward_repository().find_available_rewards(**filters)

            # 按积分范围筛选
            filtered_rewards = []
            for reward in rewards:
                if min_points and reward.required_points < min_points:
                    continue
                if max_points and reward.required_points > max_points:
                    continue
                filtered_rewards.append(reward)

            # 转换为字典格式
            reward_list = [self._reward_to_dict(reward) for reward in filtered_rewards]

            # 按分类统计
            category_stats = {}
            for reward in reward_list:
                cat = reward.get("category", "default")
                category_stats[cat] = category_stats.get(cat, 0) + 1

            result = {
                "rewards": reward_list,
                "categories": list(category_stats.keys()),
                "category_statistics": category_stats,
                "filter_info": {
                    "category": category,
                    "reward_type": reward_type,
                    "min_points": min_points,
                    "max_points": max_points,
                    "available_only": available_only
                },
                "total_count": len(reward_list)
            }

            self._log_info("奖励目录获取成功", {
                "total_rewards": len(reward_list),
                "categories": list(category_stats.keys())
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_rewards_catalog", {
                "category": category,
                "reward_type": reward_type
            })

    def get_reward_details(self, reward_id: str) -> Dict[str, Any]:
        """
        获取奖励详情

        获取指定奖励的详细信息，包括描述、兑换要求等。

        Args:
            reward_id: 奖励ID

        Returns:
            奖励详细信息

        Raises:
            ResourceNotFoundException: 当奖励不存在时
        """
        try:
            self._log_info("获取奖励详情", {"reward_id": reward_id})

            # 获取奖励信息
            reward = self._check_resource_exists(
                self.get_reward_repository(),
                reward_id,
                "奖励"
            )

            result = self._reward_to_dict(reward)

            self._log_info("奖励详情获取成功", {"reward_id": reward_id})

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_reward_details", {"reward_id": reward_id})

    # ==================== 碎片收集管理 ====================

    def get_user_fragments_collection(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户碎片收集状态

        获取用户已收集的碎片信息，包括收集进度、可兑换的奖励等。

        Args:
            user_id: 用户ID

        Returns:
            用户碎片收集状态

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("获取用户碎片收集状态", {"user_id": user_id})

            # 验证用户存在
            self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 获取用户的碎片收集记录
            fragments = self.get_reward_repository().find_user_fragments(user_id)

            # 按奖励ID分组统计
            fragment_counts = {}
            for fragment in fragments:
                reward_id = fragment.reward_id
                fragment_counts[reward_id] = fragment_counts.get(reward_id, 0) + 1

            # 获取相关奖励信息
            rewards_info = {}
            total_fragments = 0

            for reward_id, count in fragment_counts.items():
                try:
                    reward = self.get_reward_repository().get_by_id(reward_id)
                    rewards_info[reward_id] = {
                        "reward": self._reward_to_dict(reward),
                        "collected_fragments": count,
                        "required_fragments": getattr(reward, 'required_fragments', 1),
                        "can_redeem": count >= getattr(reward, 'required_fragments', 1),
                        "completion_rate": count / getattr(reward, 'required_fragments', 1) * 100
                    }
                    total_fragments += count
                except ResourceNotFoundError:
                    # 奖励可能已被删除，跳过
                    continue

            # 计算统计信息
            redeemable_count = sum(1 for info in rewards_info.values() if info["can_redeem"])
            completion_rates = [info["completion_rate"] for info in rewards_info.values()]

            result = {
                "user_id": user_id,
                "total_fragments": total_fragments,
                "rewards": rewards_info,
                "statistics": {
                    "total_reward_types": len(rewards_info),
                    "redeemable_rewards": redeemable_count,
                    "average_completion_rate": sum(completion_rates) / len(completion_rates) if completion_rates else 0.0,
                    "collection_updated_at": datetime.now().isoformat()
                }
            }

            self._log_info("用户碎片收集状态获取成功", {
                "user_id": user_id,
                "total_fragments": total_fragments,
                "redeemable_rewards": redeemable_count
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_fragments_collection", {"user_id": user_id})

    # ==================== 奖励兑换 ====================

    def redeem_reward(
        self,
        user_id: str,
        reward_id: str,
        redemption_type: str = "fragments"
    ) -> Dict[str, Any]:
        """
        兑换奖励

        使用碎片或积分兑换奖励。支持碎片兑换实体奖品，积分兑换虚拟奖励。

        Args:
            user_id: 用户ID
            reward_id: 奖励ID
            redemption_type: 兑换类型（fragments/points）

        Returns:
            兑换结果

        Raises:
            ResourceNotFoundException: 当用户或奖励不存在时
            ValidationException: 当参数无效时
            InsufficientBalanceException: 当碎片或积分不足时
        """
        try:
            self._log_info("兑换奖励", {
                "user_id": user_id,
                "reward_id": reward_id,
                "redemption_type": redemption_type
            })

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 获取奖励信息
            reward = self._check_resource_exists(
                self.get_reward_repository(),
                reward_id,
                "奖励"
            )

            # 验证奖励可用性
            if not reward.is_available:
                raise ValidationException(
                    message="该奖励暂时不可用",
                    details={"reward_id": reward_id}
                )

            # 验证兑换类型
            if redemption_type not in ["fragments", "points"]:
                raise ValidationException(
                    message="无效的兑换类型",
                    details={"redemption_type": redemption_type, "valid_types": ["fragments", "points"]}
                )

            # 检查库存
            if reward.stock_quantity is not None and reward.stock_quantity <= 0:
                raise ValidationException(
                    message="奖励库存不足",
                    details={"reward_id": reward_id, "stock_quantity": reward.stock_quantity}
                )

            # 根据兑换类型执行不同的兑换逻辑
            if redemption_type == "fragments":
                result = self._redeem_with_fragments(user_id, reward)
            else:
                result = self._redeem_with_points(user_id, reward)

            self._log_info("奖励兑换成功", {
                "user_id": user_id,
                "reward_id": reward_id,
                "redemption_type": redemption_type
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "redeem_reward", {
                "user_id": user_id,
                "reward_id": reward_id,
                "redemption_type": redemption_type
            })

    def _redeem_with_fragments(self, user_id: str, reward: Reward) -> Dict[str, Any]:
        """
        使用碎片兑换奖励

        Args:
            user_id: 用户ID
            reward: 奖励对象

        Returns:
            兑换结果

        Raises:
            InsufficientBalanceException: 当碎片不足时
        """
        required_fragments = getattr(reward, 'required_fragments', 1)

        # 检查用户碎片数量
        user_fragments = getattr(user, 'fragments', 0)
        if user_fragments < required_fragments:
            raise InsufficientBalanceException(
                current_balance=user_fragments,
                required_amount=required_fragments,
                balance_type="碎片"
            )

        # 获取用户碎片收集记录
        user_fragments_list = self.get_reward_repository().find_user_fragments(user_id)
        fragment_count = sum(1 for f in user_fragments_list if f.reward_id == reward.id)

        if fragment_count < required_fragments:
            raise InsufficientBalanceException(
                current_balance=fragment_count,
                required_amount=required_fragments,
                balance_type="碎片"
            )

        # TODO: 调用UserService的方法消耗碎片
        # self.user_service.consume_user_fragments(user_id, required_fragments, f"兑换奖励 {reward.name}")

        # 创建兑换记录
        redemption_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "reward_id": reward.id,
            "redemption_type": "fragments",
            "redemption_cost": required_fragments,
            "status": "completed",
            "redeemed_at": datetime.now(),
            "created_at": datetime.now()
        }

        # TODO: 保存兑换记录
        # self.get_reward_repository().create_redemption_record(redemption_record)

        # 更新奖励库存
        if reward.stock_quantity is not None:
            update_data = {"stock_quantity": reward.stock_quantity - 1}
            self.get_reward_repository().update(reward.id, update_data)

        # 删除用户已使用的碎片记录
        # self._delete_user_fragments(user_id, reward.id, required_fragments)

        return {
            "success": True,
            "redemption_id": redemption_record["id"],
            "reward": self._reward_to_dict(reward),
            "redemption_cost": required_fragments,
            "redemption_type": "fragments",
            "redeemed_at": redemption_record["redeemed_at"].isoformat()
        }

    def _redeem_with_points(self, user_id: str, reward: Reward) -> Dict[str, Any]:
        """
        使用积分兑换奖励

        Args:
            user_id: 用户ID
            reward: 奖励对象

        Returns:
            兑换结果

        Raises:
            InsufficientBalanceException: 当积分不足时
        """
        required_points = reward.required_points

        # 检查用户积分数量
        user_points = getattr(user, 'points', 0)
        if user_points < required_points:
            raise InsufficientBalanceException(
                current_balance=user_points,
                required_amount=required_points,
                balance_type="积分"
            )

        # TODO: 调用UserService的方法消耗积分
        # self.user_service.consume_user_points(user_id, required_points, f"兑换奖励 {reward.name}")

        # 创建兑换记录
        redemption_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "reward_id": reward.id,
            "redemption_type": "points",
            "redemption_cost": required_points,
            "status": "completed",
            "redeemed_at": datetime.now(),
            "created_at": datetime.now()
        }

        # TODO: 保存兑换记录
        # self.get_reward_repository().create_redemption_record(redemption_record)

        # 更新奖励库存
        if reward.stock_quantity is not None:
            update_data = {"stock_quantity": reward.stock_quantity - 1}
            self.get_reward_repository().update(reward.id, update_data)

        return {
            "success": True,
            "redemption_id": redemption_record["id"],
            "reward": self._reward_to_dict(reward),
            "redemption_cost": required_points,
            "redemption_type": "points",
            "redeemed_at": redemption_record["redeemed_at"].isoformat()
        }

    # ==================== 抽奖机制 ====================

    def draw_lottery(self, user_id: str) -> Dict[str, Any]:
        """
        执行抽奖

        用户消耗碎片进行抽奖，随机获得奖励。

        Args:
            user_id: 用户ID

        Returns:
            抽奖结果

        Raises:
            ResourceNotFoundException: 当用户不存在时
            InsufficientBalanceException: 当碎片不足时
        """
        try:
            self._log_info("执行抽奖", {"user_id": user_id})

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 检查碎片数量
            user_fragments = getattr(user, 'fragments', 0)
            if user_fragments < self.lottery_config["fragment_cost"]:
                raise InsufficientBalanceException(
                    current_balance=user_fragments,
                    required_amount=self.lottery_config["fragment_cost"],
                    balance_type="碎片"
                )

            # 消耗抽奖碎片
            # TODO: 调用UserService的方法消耗碎片
            # self.user_service.consume_user_fragments(user_id, self.lottery_config["fragment_cost"], "抽奖消费")

            # 执行抽奖逻辑
            lottery_result = self._execute_lottery_logic()

            # 如果抽中实体奖励，创建碎片记录
            if lottery_result["reward_type"] == "physical" and lottery_result["reward_id"]:
                self._create_lottery_fragments(user_id, lottery_result["reward_id"], lottery_result["fragment_count"])

            # 创建抽奖记录
            lottery_record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "reward_id": lottery_result.get("reward_id"),
                "reward_type": lottery_result["reward_type"],
                "reward_name": lottery_result["reward_name"],
                "reward_description": lottery_result.get("reward_description"),
                "fragment_count": lottery_result.get("fragment_count", 0),
                "rarity": lottery_result["rarity"],
                "cost_fragments": self.lottery_config["fragment_cost"],
                "status": "completed",
                "drawn_at": datetime.now(),
                "created_at": datetime.now()
            }

            # TODO: 保存抽奖记录
            # self.get_reward_repository().create_lottery_record(lottery_record)

            result = {
                "success": True,
                "lottery_id": lottery_record["id"],
                "lottery_result": lottery_result,
                "cost_fragments": self.lottery_config["fragment_cost"],
                "drawn_at": lottery_record["drawn_at"].isoformat()
            }

            self._log_info("抽奖执行成功", {
                "user_id": user_id,
                "reward_type": lottery_result["reward_type"],
                "reward_name": lottery_result["reward_name"]
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "draw_lottery", {"user_id": user_id})

    def _execute_lottery_logic(self) -> Dict[str, Any]:
        """
        执行抽奖逻辑

        Returns:
            抽奖结果
        """
        # 生成随机数
        rand = random.random()

        # 确定稀有度
        cumulative_probability = 0
        probabilities = [
            ("common", self.lottery_config["common_probability"]),
            ("rare", self.lottery_config["rare_probability"]),
            ("epic", self.lottery_config["epic_probability"]),
            ("legendary", self.lottery_config["legendary_probability"])
        ]

        rarity = "common"
        for r, prob in probabilities:
            cumulative_probability += prob
            if rand <= cumulative_probability:
                rarity = r
                break

        # 根据稀有度生成奖励
        if rarity == "common":
            # 普通奖励：少量积分
            return {
                "reward_type": "points",
                "reward_name": "积分奖励",
                "reward_description": f"恭喜获得 {random.randint(5, 20)}个积分！",
                "points": random.randint(5, 20),
                "rarity": rarity
            }
        elif rarity == "rare":
            # 稀有奖励：较多积分或1个碎片
            if random.random() < 0.6:
                return {
                    "reward_type": "points",
                    "reward_name": "积分大奖",
                    "reward_description": f"恭喜获得 {random.randint(20, 50)}个积分！",
                    "points": random.randint(20, 50),
                    "rarity": rarity
                }
            else:
                return {
                    "reward_type": "fragment",
                    "reward_name": "碎片奖励",
                    "reward_description": "恭喜获得1个稀有碎片！",
                    "fragment_count": 1,
                    "rarity": rarity
                }
        elif rarity == "epic":
            # 史诗奖励：大量积分或2-3个碎片
            if random.random() < 0.7:
                return {
                    "reward_type": "points",
                    "reward_name": "史诗积分",
                    "reward_description": f"恭喜获得 {random.randint(50, 100)}个积分！",
                    "points": random.randint(50, 100),
                    "rarity": rarity
                }
            else:
                return {
                    "reward_type": "fragment",
                    "reward_name": "史诗碎片",
                    "reward_description": f"恭喜获得{random.randint(2, 3)}个史诗碎片！",
                    "fragment_count": random.randint(2, 3),
                    "rarity": rarity
                }
        else:
            # 传说奖励：大量积分、碎片或实体奖励
            rand_choice = random.random()
            if rand_choice < 0.4:
                return {
                    "reward_type": "points",
                    "reward_name": "传说积分",
                    "reward_description": f"恭喜获得 {random.randint(100, 200)}个积分！",
                    "points": random.randint(100, 200),
                    "rarity": rarity
                }
            elif rand_choice < 0.8:
                return {
                    "reward_type": "fragment",
                    "reward_name": "传说碎片",
                    "reward_description": f"恭喜获得{random.randint(3, 5)}个传说碎片！",
                    "fragment_count": random.randint(3, 5),
                    "rarity": rarity
                }
            else:
                # 返回虚拟实体奖励
                return {
                    "reward_type": "virtual",
                    "reward_name": "虚拟奖品",
                    "reward_description": "恭喜获得稀有虚拟奖品！",
                    "rarity": rarity
                }

    def _create_lottery_fragments(self, user_id: str, reward_id: str, fragment_count: int) -> None:
        """
        创建抽奖获得的碎片记录

        Args:
            user_id: 用户ID
            reward_id: 奖励ID
            fragment_count: 碎片数量
        """
        # TODO: 创建碎片记录
        for i in range(fragment_count):
            fragment_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "reward_id": reward_id,
                "fragment_type": "lottery",
                "obtained_at": datetime.now(),
                "created_at": datetime.now()
            }
            # self.get_reward_repository().create_fragment(fragment_data)

    # ==================== 私有方法 ====================

    def _reward_to_dict(self, reward: Reward) -> Dict[str, Any]:
        """将奖励对象转换为字典"""
        return {
            "id": reward.id,
            "name": reward.name,
            "description": reward.description,
            "reward_type": reward.reward_type.value,
            "category": getattr(reward, 'category', 'default'),
            "required_points": reward.required_points,
            "required_fragments": getattr(reward, 'required_fragments', 0),
            "image_url": getattr(reward, 'image_url', None),
            "is_available": reward.is_available,
            "stock_quantity": getattr(reward, 'stock_quantity', None),
            "created_at": reward.created_at.isoformat() if reward.created_at else None,
            "updated_at": reward.updated_at.isoformat() if reward.updated_at else None
        }