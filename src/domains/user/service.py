"""
User领域Service层 - UUID类型安全实现

提供用户业务逻辑服务，实现UUID类型安全。
Service层只处理UUID对象，UUID转换委托给Repository层。

Service职责:
- 用户资料管理
- 欢迎礼包管理
- 业务逻辑验证
- 与其他领域的UUID传递

设计原则:
- UUID类型安全：所有方法使用UUID参数
- 依赖注入：通过构造函数注入Repository
- 错误处理：提供详细的错误信息
- 业务验证：验证用户权限和数据完整性

作者：TaKeKe团队
版本：2.0.0 - UUID架构统一版
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from .repository import UserRepository
from .schemas import UserProfileResponse, UpdateProfileRequest, UpdateProfileResponse
from src.domains.points.service import PointsService
from src.domains.reward.welcome_gift_service import WelcomeGiftService
from src.utils.uuid_helpers import uuid_converter, validate_uuid_string

logger = logging.getLogger(__name__)


class UserService:
    """
    用户Service类

    提供用户相关的业务逻辑服务，实现UUID类型安全。
    Service层只处理UUID对象，UUID转换委托给Repository层。
    """

    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository
        self.logger = logger

    def get_user_profile(self, user_id: UUID) -> Dict[str, Any]:
        """
        获取用户资料

        注意：Service层使用UUID参数，Repository层处理转换。

        Args:
            user_id (UUID): 用户ID

        Returns:
            Dict[str, Any]: 用户资料数据

        Raises:
            ValueError: UUID格式无效
            Exception: 获取用户资料失败
        """
        try:
            # UUID类型验证
            if not isinstance(user_id, UUID):
                raise ValueError(f"user_id必须是UUID对象，收到类型: {type(user_id)}")

            self.logger.info(f"获取用户资料: {user_id}")

            # 通过Repository获取用户
            user = self.user_repo.get_by_id(user_id)

            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "code": 404
                }

            # 构造用户资料数据（只使用Auth模型中存在的字段）
            user_profile = {
                "id": str(user.id),
                "nickname": f"用户_{user.id[:8]}",  # 生成默认昵称
                "avatar": None,  # Auth模型中没有avatar字段
                "wechat_openid": user.wechat_openid,
                "is_guest": user.is_guest,
                "created_at": user.created_at.isoformat(),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            }

            return {
                "success": True,
                "data": user_profile,
                "message": "获取用户资料成功"
            }

        except ValueError as e:
            self.logger.error(f"UUID格式验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": 400
            }

        except Exception as e:
            self.logger.error(f"获取用户资料失败: {e}")
            return {
                "success": False,
                "error": "获取用户资料失败",
                "code": 500
            }

    def update_user_profile(self, user_id: UUID, request: UpdateProfileRequest) -> Dict[str, Any]:
        """
        更新用户资料

        注意：Service层使用UUID参数，Repository层处理转换。
        由于Auth模型限制，某些字段暂时无法更新。

        Args:
            user_id (UUID): 用户ID
            request (UpdateProfileRequest): 更新请求数据

        Returns:
            Dict[str, Any]: 更新结果

        Raises:
            ValueError: UUID格式无效
            Exception: 更新用户资料失败
        """
        try:
            # UUID类型验证
            if not isinstance(user_id, UUID):
                raise ValueError(f"user_id必须是UUID对象，收到类型: {type(user_id)}")

            self.logger.info(f"更新用户资料: {user_id}")

            # 验证用户存在
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "code": 404
                }

            # 注意：Auth模型中没有nickname字段，暂时返回默认昵称
            # 在未来的版本中可以考虑扩展Auth模型或创建独立的User模型
            updated_fields = []
            if request.nickname:
                # 暂时无法更新昵称，因为Auth模型中没有该字段
                # 这里可以记录日志或在未来版本中实现
                self.logger.info(f"User requested nickname update to '{request.nickname}', but Auth model doesn't support nickname field")
                updated_fields.append("nickname_requested")

            # 构造更新响应数据
            update_response = {
                "id": str(user.id),
                "nickname": f"用户_{user.id[:8]}",  # 返回默认昵称
                "updated_fields": updated_fields
            }

            return {
                "success": True,
                "data": update_response,
                "message": "更新成功"
            }

        except ValueError as e:
            self.logger.error(f"UUID格式验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": 400
            }

        except Exception as e:
            self.logger.error(f"更新用户资料失败: {e}")
            return {
                "success": False,
                "error": "更新用户资料失败",
                "code": 500
            }

    def claim_welcome_gift(self, user_id: UUID, points_service: PointsService,
                          welcome_gift_service: WelcomeGiftService) -> Dict[str, Any]:
        """
        领取欢迎礼包

        注意：Service层使用UUID参数，Repository层处理转换。

        Args:
            user_id (UUID): 用户ID
            points_service (PointsService): 积分服务
            welcome_gift_service (WelcomeGiftService): 欢迎礼包服务

        Returns:
            Dict[str, Any]: 领取结果

        Raises:
            ValueError: UUID格式无效
            Exception: 领取欢迎礼包失败
        """
        try:
            # UUID类型验证
            if not isinstance(user_id, UUID):
                raise ValueError(f"user_id必须是UUID对象，收到类型: {type(user_id)}")

            self.logger.info(f"领取欢迎礼包: {user_id}")

            # 验证用户存在
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "code": 404
                }

            # 转换UUID为字符串（Repository层处理，但欢迎礼包服务可能需要字符串）
            user_id_str = uuid_converter.to_db_format(user_id)

            # 领取欢迎礼包
            result = welcome_gift_service.claim_welcome_gift(user_id_str)

            # 构建响应数据
            rewards_granted = [
                {
                    "name": reward["name"],
                    "quantity": reward["quantity"],
                    "description": reward["description"]
                }
                for reward in result["rewards_granted"]
            ]

            return {
                "success": True,
                "data": {
                    "points_granted": result["points_granted"],
                    "rewards_granted": rewards_granted,
                    "transaction_group": result["transaction_group"],
                    "granted_at": result["granted_at"]
                },
                "message": "领取欢迎礼包成功"
            }

        except ValueError as e:
            self.logger.error(f"UUID格式验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": 400
            }

        except Exception as e:
            self.logger.error(f"领取欢迎礼包失败: {e}")
            return {
                "success": False,
                "error": "领取欢迎礼包失败",
                "code": 500
            }

    def get_welcome_gift_history(self, user_id: UUID, points_service: PointsService,
                                welcome_gift_service: WelcomeGiftService, limit: int = 10) -> Dict[str, Any]:
        """
        获取欢迎礼包历史

        注意：Service层使用UUID参数，Repository层处理转换。

        Args:
            user_id (UUID): 用户ID
            points_service (PointsService): 积分服务
            welcome_gift_service (WelcomeGiftService): 欢迎礼包服务
            limit (int): 返回记录数量限制

        Returns:
            Dict[str, Any]: 历史记录

        Raises:
            ValueError: UUID格式无效
            Exception: 获取历史失败
        """
        try:
            # UUID类型验证
            if not isinstance(user_id, UUID):
                raise ValueError(f"user_id必须是UUID对象，收到类型: {type(user_id)}")

            self.logger.info(f"获取欢迎礼包历史: {user_id}")

            # 验证用户存在
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "用户不存在",
                    "code": 404
                }

            # 转换UUID为字符串
            user_id_str = uuid_converter.to_db_format(user_id)

            # 获取历史记录
            history = welcome_gift_service.get_user_gift_history(user_id_str, limit)

            # 构建响应数据
            history_items = [
                {
                    "transaction_group": item["transaction_group"],
                    "granted_at": item["granted_at"],
                    "points_granted": item["points_granted"],
                    "rewards_count": item["rewards_count"],
                    "reward_items": item["reward_items"]
                }
                for item in history
            ]

            return {
                "success": True,
                "data": {
                    "history": history_items,
                    "total_count": len(history_items)
                },
                "message": "获取历史记录成功"
            }

        except ValueError as e:
            self.logger.error(f"UUID格式验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": 400
            }

        except Exception as e:
            self.logger.error(f"获取欢迎礼包历史失败: {e}")
            return {
                "success": False,
                "error": "获取历史记录失败",
                "code": 500
            }

    def create_guest_user(self) -> Dict[str, Any]:
        """
        创建游客用户

        Returns:
            Dict[str, Any]: 创建结果

        Raises:
            Exception: 创建用户失败
        """
        try:
            self.logger.info("创建游客用户")

            user = self.user_repo.create_guest_user()

            return {
                "success": True,
                "data": {
                    "id": str(user.id),
                    "is_guest": user.is_guest,
                    "created_at": user.created_at.isoformat()
                },
                "message": "创建游客用户成功"
            }

        except Exception as e:
            self.logger.error(f"创建游客用户失败: {e}")
            return {
                "success": False,
                "error": "创建游客用户失败",
                "code": 500
            }

    def user_exists(self, user_id: UUID) -> bool:
        """
        检查用户是否存在

        Args:
            user_id (UUID): 用户ID

        Returns:
            bool: 存在返回True，不存在返回False

        Raises:
            ValueError: UUID格式无效
            Exception: 检查失败
        """
        try:
            # UUID类型验证
            if not isinstance(user_id, UUID):
                raise ValueError(f"user_id必须是UUID对象，收到类型: {type(user_id)}")

            return self.user_repo.user_exists(user_id)

        except ValueError:
            raise  # 重新抛出验证错误
        except Exception as e:
            self.logger.error(f"检查用户存在性失败: {e}")
            raise Exception(f"检查用户存在性失败: {str(e)}")