"""
用户服务模块

该模块实现用户管理相关的业务逻辑，包括用户信息管理、用户设置管理、
用户状态管理等功能。提供完整的用户资料管理、积分系统、用户行为记录等服务。

设计原则：
1. 数据完整性：确保用户信息的准确性和一致性
2. 隐私保护：严格保护用户敏感信息，提供数据脱敏功能
3. 业务规则：实现完整的用户业务规则验证
4. 性能优化：高效的查询和数据更新机制
5. 异常处理：详细的错误信息和处理建议

核心功能：
- 用户基本信息管理
- 用户设置和偏好管理
- 用户状态和权限管理
- 积分和碎片管理
- 用户行为记录
- 数据统计和分析
"""

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
from src.models.user import User


class UserService(BaseService):
    """
    用户服务类

    处理用户管理相关的所有业务逻辑，包括用户信息维护、设置管理、
    状态管理、积分管理等核心功能。

    Attributes:
        _user_repo: 用户数据访问对象
        _task_repo: 任务数据访问对象
        _focus_repo: 专注数据访问对象
        _reward_repo: 奖励数据访问对象
    """

    def __init__(self, user_repo=None, task_repo=None, focus_repo=None, reward_repo=None, chat_repo=None, **kwargs):
        """
        初始化用户服务

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            chat_repo: 聊天数据访问对象
            **kwargs: 其他参数传递给父类
        """
        super().__init__(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            chat_repo=chat_repo,
            **kwargs
        )

    # ==================== 用户基本信息管理 ====================

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户完整资料

        获取用户的完整信息，包括基本资料、统计数据、成就等。
        对敏感信息进行脱敏处理。

        Args:
            user_id: 用户ID

        Returns:
            用户完整资料信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("获取用户完整资料", {"user_id": user_id})

            # 获取用户基本信息
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 获取用户统计数据
            user_stats = self._get_user_statistics(user_id)

            # 构建完整资料
            profile = {
                "basic_info": self._filter_sensitive_data({
                    "id": user.id,
                    "nickname": user.nickname,
                    "avatar": getattr(user, 'avatar', None),
                    "is_guest": user.is_guest,
                    "is_active": user.is_active,
                    "phone": getattr(user, 'phone', None),
                    "email": getattr(user, 'email', None),
                    "wechat_openid": getattr(user, 'wechat_openid', None),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login_at": getattr(user, 'last_login_at', None)
                }),
                "statistics": user_stats
            }

            self._log_info("用户资料获取成功", {"user_id": user_id})

            return profile

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_profile", {"user_id": user_id})

    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户基本信息

        更新用户的基本资料信息，如昵称、头像等。
        进行数据验证和业务规则检查。

        Args:
            user_id: 用户ID
            update_data: 更新数据

        Returns:
            更新后的用户信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当数据无效时
            DuplicateResourceException: 当数据冲突时
        """
        try:
            self._log_info("更新用户基本信息", {
                "user_id": user_id,
                "update_fields": list(update_data.keys())
            })

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 验证更新数据
            validated_data = self._validate_profile_update_data(user, update_data)

            # 更新用户信息
            updated_user = self.get_user_repository().update(user_id, validated_data)

            # 过滤敏感信息返回
            result = self._filter_sensitive_data({
                "id": updated_user.id,
                "nickname": updated_user.nickname,
                "avatar": getattr(updated_user, 'avatar', None),
                "updated_at": updated_user.updated_at.isoformat() if updated_user.updated_at else None
            })

            self._log_info("用户信息更新成功", {
                "user_id": user_id,
                "updated_fields": list(validated_data.keys())
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "update_user_profile", {
                "user_id": user_id,
                "update_data": update_data
            })

    # ==================== 用户积分和碎片管理 ====================

    def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户积分和碎片余额

        获取用户当前的积分和碎片数量，以及近期的变动记录。

        Args:
            user_id: 用户ID

        Returns:
            用户余额信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("获取用户余额", {"user_id": user_id})

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 获取积分变动记录
            recent_transactions = self._get_recent_transactions(user_id, limit=10)

            balance_info = {
                "points": getattr(user, 'points', 0),
                "fragments": getattr(user, 'fragments', 0),
                "recent_transactions": recent_transactions
            }

            self._log_info("用户余额获取成功", {
                "user_id": user_id,
                "points": balance_info["points"],
                "fragments": balance_info["fragments"]
            })

            return balance_info

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_balance", {"user_id": user_id})

    def add_user_points(self, user_id: str, points: int, reason: str, source: str = None) -> Dict[str, Any]:
        """
        增加用户积分

        为用户增加积分，记录积分变动原因。

        Args:
            user_id: 用户ID
            points: 增加的积分数量
            reason: 积分变动原因
            source: 积分来源（可选）

        Returns:
            更新后的余额信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("增加用户积分", {
                "user_id": user_id,
                "points": points,
                "reason": reason
            })

            # 验证参数
            if points <= 0:
                raise ValidationException(
                    message="积分数量必须大于0",
                    details={"points": points}
                )

            if not reason or len(reason.strip()) == 0:
                raise ValidationException(
                    message="积分变动原因不能为空",
                    details={"reason": reason}
                )

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 更新用户积分
            current_points = getattr(user, 'points', 0)
            new_points = current_points + points

            update_data = {
                "points": new_points,
                "updated_at": datetime.now()
            }

            updated_user = self.get_user_repository().update(user_id, update_data)

            # 记录积分变动
            self._record_transaction(
                user_id=user_id,
                transaction_type="points",
                amount=points,
                balance_after=new_points,
                reason=reason,
                source=source
            )

            result = {
                "points": new_points,
                "fragments": getattr(updated_user, 'fragments', 0),
                "points_added": points
            }

            self._log_info("用户积分增加成功", {
                "user_id": user_id,
                "points_added": points,
                "new_balance": new_points
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "add_user_points", {
                "user_id": user_id,
                "points": points,
                "reason": reason
            })

    def consume_user_points(self, user_id: str, points: int, reason: str, source: str = None) -> Dict[str, Any]:
        """
        消费用户积分

        扣除用户积分，需要验证积分余额是否足够。

        Args:
            user_id: 用户ID
            points: 消费的积分数量
            reason: 积分消费原因
            source: 消费项目（可选）

        Returns:
            更新后的余额信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
            InsufficientBalanceException: 当积分不足时
        """
        try:
            self._log_info("消费用户积分", {
                "user_id": user_id,
                "points": points,
                "reason": reason
            })

            # 验证参数
            if points <= 0:
                raise ValidationException(
                    message="积分数量必须大于0",
                    details={"points": points}
                )

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 检查积分余额
            current_points = getattr(user, 'points', 0)
            if current_points < points:
                raise InsufficientBalanceException(
                    current_balance=current_points,
                    required_amount=points,
                    balance_type="积分"
                )

            # 更新用户积分
            new_points = current_points - points

            update_data = {
                "points": new_points,
                "updated_at": datetime.now()
            }

            updated_user = self.get_user_repository().update(user_id, update_data)

            # 记录积分变动
            self._record_transaction(
                user_id=user_id,
                transaction_type="points",
                amount=-points,
                balance_after=new_points,
                reason=reason,
                source=source
            )

            result = {
                "points": new_points,
                "fragments": getattr(updated_user, 'fragments', 0),
                "points_consumed": points
            }

            self._log_info("用户积分消费成功", {
                "user_id": user_id,
                "points_consumed": points,
                "new_balance": new_points
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "consume_user_points", {
                "user_id": user_id,
                "points": points,
                "reason": reason
            })

    def add_user_fragments(self, user_id: str, fragments: int, reason: str, source: str = None) -> Dict[str, Any]:
        """
        增加用户碎片

        为用户增加碎片，记录碎片变动原因。

        Args:
            user_id: 用户ID
            fragments: 增加的碎片数量
            reason: 碎片变动原因
            source: 碎片来源（可选）

        Returns:
            更新后的余额信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("增加用户碎片", {
                "user_id": user_id,
                "fragments": fragments,
                "reason": reason
            })

            # 验证参数
            if fragments <= 0:
                raise ValidationException(
                    message="碎片数量必须大于0",
                    details={"fragments": fragments}
                )

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 更新用户碎片
            current_fragments = getattr(user, 'fragments', 0)
            new_fragments = current_fragments + fragments

            update_data = {
                "fragments": new_fragments,
                "updated_at": datetime.now()
            }

            updated_user = self.get_user_repository().update(user_id, update_data)

            # 记录碎片变动
            self._record_transaction(
                user_id=user_id,
                transaction_type="fragments",
                amount=fragments,
                balance_after=new_fragments,
                reason=reason,
                source=source
            )

            result = {
                "points": getattr(updated_user, 'points', 0),
                "fragments": new_fragments,
                "fragments_added": fragments
            }

            self._log_info("用户碎片增加成功", {
                "user_id": user_id,
                "fragments_added": fragments,
                "new_balance": new_fragments
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "add_user_fragments", {
                "user_id": user_id,
                "fragments": fragments,
                "reason": reason
            })

    # ==================== 用户状态管理 ====================

    def update_user_status(self, user_id: str, is_active: bool, reason: str = None) -> Dict[str, Any]:
        """
        更新用户状态

        启用或禁用用户账号，记录状态变更原因。

        Args:
            user_id: 用户ID
            is_active: 是否激活
            reason: 状态变更原因（可选）

        Returns:
            更新后的用户状态

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("更新用户状态", {
                "user_id": user_id,
                "is_active": is_active,
                "reason": reason
            })

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 更新用户状态
            update_data = {
                "is_active": is_active,
                "updated_at": datetime.now()
            }

            updated_user = self.get_user_repository().update(user_id, update_data)

            # 记录状态变更
            if reason:
                self._log_info("用户状态变更", {
                    "user_id": user_id,
                    "old_status": user.is_active,
                    "new_status": is_active,
                    "reason": reason
                })

            result = {
                "user_id": updated_user.id,
                "is_active": updated_user.is_active,
                "updated_at": updated_user.updated_at.isoformat() if updated_user.updated_at else None
            }

            self._log_info("用户状态更新成功", {
                "user_id": user_id,
                "new_status": is_active
            })

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "update_user_status", {
                "user_id": user_id,
                "is_active": is_active
            })

    def update_last_login(self, user_id: str) -> Dict[str, Any]:
        """
        更新用户最后登录时间

        记录用户的最后登录时间，用于用户活跃度统计。

        Args:
            user_id: 用户ID

        Returns:
            更新结果

        Raises:
            ResourceNotFoundException: 当用户不存在时
        """
        try:
            self._log_info("更新用户最后登录时间", {"user_id": user_id})

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 更新最后登录时间
            update_data = {
                "last_login_at": datetime.now(),
                "updated_at": datetime.now()
            }

            updated_user = self.get_user_repository().update(user_id, update_data)

            result = {
                "user_id": updated_user.id,
                "last_login_at": updated_user.last_login_at.isoformat() if updated_user.last_login_at else None
            }

            self._log_info("最后登录时间更新成功", {"user_id": user_id})

            return result

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "update_last_login", {"user_id": user_id})

    # ==================== 用户统计信息 ====================

    def get_user_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取用户统计信息

        获取用户在指定时间范围内的活动统计数据。

        Args:
            user_id: 用户ID
            days: 统计天数，默认30天

        Returns:
            用户统计信息

        Raises:
            ResourceNotFoundException: 当用户不存在时
            ValidationException: 当参数无效时
        """
        try:
            self._log_info("获取用户统计信息", {
                "user_id": user_id,
                "days": days
            })

            # 验证参数
            if days <= 0 or days > 365:
                raise ValidationException(
                    message="统计天数必须在1-365之间",
                    details={"days": days}
                )

            # 验证用户存在
            user = self._check_resource_exists(
                self.get_user_repository(),
                user_id,
                "用户"
            )

            # 计算统计时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 获取各模块统计数据
            stats = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "tasks": self._get_task_statistics(user_id, start_date, end_date),
                "focus": self._get_focus_statistics(user_id, start_date, end_date),
                "rewards": self._get_reward_statistics(user_id, start_date, end_date),
                "balance": {
                    "current_points": getattr(user, 'points', 0),
                    "current_fragments": getattr(user, 'fragments', 0)
                }
            }

            self._log_info("用户统计信息获取成功", {
                "user_id": user_id,
                "period_days": days
            })

            return stats

        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, "get_user_statistics", {
                "user_id": user_id,
                "days": days
            })

    # ==================== 私有方法 ====================

    def _validate_profile_update_data(self, user: User, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证用户资料更新数据

        Args:
            user: 用户对象
            update_data: 更新数据

        Returns:
            验证后的更新数据

        Raises:
            ValidationException: 当数据无效时
            DuplicateResourceException: 当数据冲突时
        """
        validated_data = {}
        current_time = datetime.now()

        # 验证昵称
        if "nickname" in update_data:
            nickname = update_data["nickname"]
            if not nickname or len(nickname.strip()) == 0:
                raise ValidationException(
                    message="昵称不能为空",
                    details={"nickname": nickname}
                )
            if len(nickname) > 50:
                raise ValidationException(
                    message="昵称长度不能超过50个字符",
                    details={"nickname": nickname, "length": len(nickname)}
                )
            validated_data["nickname"] = nickname.strip()

        # 验证头像
        if "avatar" in update_data:
            avatar = update_data["avatar"]
            if avatar and (len(avatar) > 255 or not self._validate_url_format(avatar)):
                raise ValidationException(
                    message="头像URL格式无效",
                    details={"avatar": avatar}
                )
            validated_data["avatar"] = avatar

        # 验证手机号
        if "phone" in update_data:
            phone = update_data["phone"]
            if phone and not self._validate_phone_format(phone):
                raise ValidationException(
                    message="手机号格式错误",
                    details={"phone": phone}
                )
            # 检查手机号是否已被其他用户使用
            if phone and phone != getattr(user, 'phone', None):
                if self.get_user_repository().phone_exists(phone):
                    raise DuplicateResourceException(
                        resource_type="User",
                        conflict_field="phone",
                        conflict_value=phone,
                        user_message="该手机号已被使用"
                    )
            validated_data["phone"] = phone

        # 验证邮箱
        if "email" in update_data:
            email = update_data["email"]
            if email and not self._validate_email_format(email):
                raise ValidationException(
                    message="邮箱格式错误",
                    details={"email": email}
                )
            # 检查邮箱是否已被其他用户使用
            if email and email != getattr(user, 'email', None):
                if self.get_user_repository().email_exists(email):
                    raise DuplicateResourceException(
                        resource_type="User",
                        conflict_field="email",
                        conflict_value=email,
                        user_message="该邮箱已被使用"
                    )
            validated_data["email"] = email

        # 添加更新时间
        validated_data["updated_at"] = current_time

        return validated_data

    def _get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户基础统计信息

        Args:
            user_id: 用户ID

        Returns:
            用户统计信息
        """
        # 这里需要调用其他服务的统计方法
        # 目前返回基础信息
        return {
            "total_tasks": 0,
            "completed_tasks": 0,
            "total_focus_time": 0,
            "focus_sessions": 0,
            "rewards_earned": 0
        }

    def _get_task_statistics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取任务统计数据"""
        if not self._task_repo:
            return {"total": 0, "completed": 0, "completion_rate": 0.0}

        # TODO: 实现任务统计逻辑
        return {"total": 0, "completed": 0, "completion_rate": 0.0}

    def _get_focus_statistics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取专注统计数据"""
        if not self._focus_repo:
            return {"total_sessions": 0, "total_minutes": 0, "average_minutes": 0.0}

        # TODO: 实现专注统计逻辑
        return {"total_sessions": 0, "total_minutes": 0, "average_minutes": 0.0}

    def _get_reward_statistics(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取奖励统计数据"""
        if not self._reward_repo:
            return {"rewards_redeemed": 0, "lottery_participations": 0, "lottery_wins": 0}

        # TODO: 实现奖励统计逻辑
        return {"rewards_redeemed": 0, "lottery_participations": 0, "lottery_wins": 0}

    def _record_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: int,
        balance_after: int,
        reason: str,
        source: str = None
    ) -> None:
        """
        记录用户积分/碎片变动

        Args:
            user_id: 用户ID
            transaction_type: 交易类型（points/fragments）
            amount: 变动数量
            balance_after: 变动后余额
            reason: 变动原因
            source: 来源（可选）
        """
        if not self._reward_repo:
            return

        # TODO: 实现交易记录逻辑
        # 这里需要调用reward repository记录交易
        pass

    def _get_recent_transactions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近交易记录

        Args:
            user_id: 用户ID
            limit: 记录数量限制

        Returns:
            交易记录列表
        """
        if not self._reward_repo:
            return []

        # TODO: 实现交易记录查询逻辑
        return []

    # ==================== 工具方法 ====================

    def _validate_url_format(self, url: str) -> bool:
        """验证URL格式"""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))

    def _validate_phone_format(self, phone: str) -> bool:
        """验证手机号格式"""
        import re
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))

    def _validate_email_format(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))