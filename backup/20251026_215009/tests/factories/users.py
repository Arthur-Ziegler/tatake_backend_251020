"""
零Bug测试体系 - 用户测试数据工厂

提供用户相关的测试数据生成，包括普通用户、游客用户、认证日志等。

设计原则：
1. 覆盖所有用户类型（游客、注册用户、VIP用户等）
2. 确保用户数据唯一性和一致性
3. 支持不同场景的用户状态
4. 自动生成关联的认证数据
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseFactory, register_factory


@register_factory("user")
class UserFactory(BaseFactory):
    """用户测试数据工厂

    生成符合业务需求的用户测试数据，包括基本信息、状态、设置等。
    """

    # 用户默认数据
    DEFAULTS = {
        "wechat_openid": "",  # 微信OpenID，必须唯一
        "username": "",      # 用户名
        "email": "",         # 邮箱
        "phone": "",         # 手机号
        "nickname": "",      # 昵称
        "avatar_url": "",    # 头像URL
        "is_guest": False,   # 是否游客
        "is_active": True,   # 是否激活
        "is_verified": False, # 是否验证
        "is_vip": False,     # 是否VIP
        "level": 1,          # 用户等级
        "points": 0,         # 积分
        "total_points_earned": 0,  # 总获得积分
        "created_at": None,  # 创建时间
        "updated_at": None,  # 更新时间
        "last_login_at": None, # 最后登录时间
        "settings": {},      # 用户设置
    }

    # 必填字段
    REQUIRED_FIELDS = ["wechat_openid", "username"]

    # 关联的模型类（如果有的话）
    model_class = None

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建用户数据

        Args:
            **overrides: 覆盖字段

        Returns:
            用户数据字典
        """
        # 生成唯一标识
        user_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # 生成唯一的基本信息
        wechat_openid = f"test_wx_{user_id[:8]}"
        username = f"test_user_{user_id[:8]}"
        email = f"test_{user_id[:8]}@test.com"
        phone = f"138{user_id[:8]}"

        # 构建默认数据
        defaults = cls._merge_data(cls.DEFAULTS, {
            "wechat_openid": cls._ensure_unique("wechat_openid", wechat_openid),
            "username": cls._ensure_unique("username", username),
            "email": email,
            "phone": phone,
            "nickname": f"测试用户_{user_id[:6]}",
            "avatar_url": f"https://avatar.test.com/{user_id[:12]}.jpg",
            "created_at": timestamp,
            "updated_at": timestamp,
            "last_login_at": timestamp,
            "settings": {
                "theme": "light",
                "notifications": True,
                "language": "zh-CN",
                "privacy": "public"
            }
        })

        # 应用覆盖数据
        user_data = cls._merge_data(defaults, overrides)

        # 数据验证
        cls.validate_data(user_data)

        return user_data

    @classmethod
    def create_guest(cls, **overrides: Any) -> Dict[str, Any]:
        """创建游客用户

        Args:
            **overrides: 覆盖字段

        Returns:
            游客用户数据
        """
        return cls.create(
            is_guest=True,
            is_verified=False,
            is_vip=False,
            level=0,
            **overrides
        )

    @classmethod
    def create_registered(cls, **overrides: Any) -> Dict[str, Any]:
        """创建注册用户

        Args:
            **overrides: 覆盖字段

        Returns:
            注册用户数据
        """
        return cls.create(
            is_guest=False,
            is_verified=True,
            is_active=True,
            level=cls._generate_int(1, 10),
            points=cls._generate_int(0, 1000),
            **overrides
        )

    @classmethod
    def create_vip(cls, **overrides: Any) -> Dict[str, Any]:
        """创建VIP用户

        Args:
            **overrides: 覆盖字段

        Returns:
            VIP用户数据
        """
        return cls.create(
            is_guest=False,
            is_verified=True,
            is_active=True,
            is_vip=True,
            level=cls._generate_int(5, 10),
            points=cls._generate_int(500, 5000),
            **overrides
        )

    @classmethod
    def create_inactive(cls, **overrides: Any) -> Dict[str, Any]:
        """创建非激活用户

        Args:
            **overrides: 覆盖字段

        Returns:
            非激活用户数据
        """
        return cls.create(
            is_active=False,
            is_verified=False,
            **overrides
        )

    @classmethod
    def create_with_points(cls, points: int, **overrides: Any) -> Dict[str, Any]:
        """创建带指定积分的用户

        Args:
            points: 积分数量
            **overrides: 覆盖字段

        Returns:
            用户数据
        """
        return cls.create(
            points=points,
            total_points_earned=points,
            **overrides
        )

    @classmethod
    def create_batch_with_levels(cls, count: int, **overrides: Any) -> List[Dict[str, Any]]:
        """创建不同等级的用户批次

        Args:
            count: 创建数量
            **overrides: 覆盖字段

        Returns:
            用户数据列表
        """
        users = []
        for i in range(count):
            level = (i % 10) + 1  # 1-10等级循环
            points = level * 100
            user = cls.create(
                level=level,
                points=points,
                total_points_earned=points,
                **overrides
            )
            users.append(user)
        return users


@register_factory("auth_log")
class AuthLogFactory(BaseFactory):
    """认证日志测试数据工厂

    生成用户认证操作日志，包括登录、注册、登出等。
    """

    # 认证日志默认数据
    DEFAULTS = {
        "user_id": "",          # 用户ID
        "action": "",           # 操作类型
        "ip_address": "",       # IP地址
        "user_agent": "",       # 用户代理
        "device_id": "",        # 设备ID
        "location": "",         # 地理位置
        "success": True,        # 是否成功
        "error_message": "",    # 错误信息
        "created_at": None,     # 创建时间
    }

    # 必填字段
    REQUIRED_FIELDS = ["user_id", "action"]

    # 支持的认证操作类型
    ACTIONS = [
        "login", "register", "logout", "refresh_token",
        "verify_phone", "verify_email", "reset_password",
        "bind_wechat", "unbind_wechat", "upgrade_account"
    ]

    @classmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建认证日志数据

        Args:
            **overrides: 覆盖字段

        Returns:
            认证日志数据
        """
        # 生成基础数据
        log_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # 构建默认数据
        defaults = cls._merge_data(cls.DEFAULTS, {
            "user_id": overrides.get("user_id", str(uuid.uuid4())),
            "action": cls._generate_choice(cls.ACTIONS),
            "ip_address": f"192.168.{cls._generate_int(1, 255)}.{cls._generate_int(1, 255)}",
            "user_agent": f"TestAgent/{cls._generate_int(1, 10)}",
            "device_id": f"device_{log_id[:8]}",
            "location": f"测试城市_{cls._generate_int(1, 10)}",
            "success": cls._generate_boolean(0.9),  # 90%成功率
            "error_message": "",
            "created_at": timestamp,
        })

        # 如果失败，生成错误信息
        if not defaults["success"]:
            error_messages = [
                "密码错误", "用户不存在", "验证码错误", "账户已锁定",
                "Token已过期", "网络错误", "服务器错误"
            ]
            defaults["error_message"] = cls._generate_choice(error_messages)

        # 应用覆盖数据
        log_data = cls._merge_data(defaults, overrides)

        # 数据验证
        cls.validate_data(log_data)

        return log_data

    @classmethod
    def create_login_log(cls, user_id: str, success: bool = True, **overrides: Any) -> Dict[str, Any]:
        """创建登录日志

        Args:
            user_id: 用户ID
            success: 是否登录成功
            **overrides: 覆盖字段

        Returns:
            登录日志数据
        """
        return cls.create(
            user_id=user_id,
            action="login",
            success=success,
            **overrides
        )

    @classmethod
    def create_register_log(cls, user_id: str, **overrides: Any) -> Dict[str, Any]:
        """创建注册日志

        Args:
            user_id: 用户ID
            **overrides: 覆盖字段

        Returns:
            注册日志数据
        """
        return cls.create(
            user_id=user_id,
            action="register",
            success=True,
            **overrides
        )

    @classmethod
    def create_batch_for_user(cls, user_id: str, count: int = 5, **overrides: Any) -> List[Dict[str, Any]]:
        """为指定用户创建一批认证日志

        Args:
            user_id: 用户ID
            count: 日志数量
            **overrides: 覆盖字段

        Returns:
            认证日志列表
        """
        logs = []
        for i in range(count):
            # 生成不同的操作类型
            action_index = i % len(cls.ACTIONS)
            log = cls.create(
                user_id=user_id,
                action=cls.ACTIONS[action_index],
                **overrides
            )
            logs.append(log)
        return logs


class UserFactoryManager:
    """用户工厂管理器

    提供高级的用户数据创建和管理功能。
    """

    @staticmethod
    def create_user_hierarchy():
        """创建用户层级数据（游客、普通用户、VIP）

        Returns:
            包含不同类型用户的字典
        """
        guest = UserFactory.create_guest()
        regular = UserFactory.create_registered()
        vip = UserFactory.create_vip()

        return {
            "guest": guest,
            "regular": regular,
            "vip": vip
        }

    @staticmethod
    def create_user_with_auth_history(num_logs: int = 10):
        """创建带认证历史的用户

        Args:
            num_logs: 认证日志数量

        Returns:
            用户数据和认证日志列表
        """
        user = UserFactory.create_registered()
        logs = AuthLogFactory.create_batch_for_user(
            user_id=user["wechat_openid"],
            count=num_logs
        )

        return {
            "user": user,
            "auth_logs": logs
        }

    @staticmethod
    def create_realistic_user_community(size: int = 100):
        """创建真实用户社区数据

        Args:
            size: 社区大小

        Returns:
            用户社区数据
        """
        users = []

        # 分布：60%注册用户，30%游客，10%VIP
        registered_count = int(size * 0.6)
        guest_count = int(size * 0.3)
        vip_count = size - registered_count - guest_count

        # 创建注册用户
        users.extend(UserFactory.create_batch(registered_count))
        for user in users[-registered_count:]:
            user.update(UserFactory.create_registered())

        # 创建游客用户
        users.extend(UserFactory.create_batch(guest_count))
        for user in users[-guest_count:]:
            user.update(UserFactory.create_guest())

        # 创建VIP用户
        users.extend(UserFactory.create_batch(vip_count))
        for user in users[-vip_count:]:
            user.update(UserFactory.create_vip())

        return users