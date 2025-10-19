"""
用户Repository实现

提供用户相关的数据访问层操作，封装用户业务逻辑查询。
继承自BaseRepository，专注于用户特有的业务场景。

功能特性：
1. 用户认证查询（邮箱、手机号、微信OpenID查找）
2. 用户状态管理（注册用户、游客用户、活跃用户）
3. 用户创建和升级（游客转注册用户）
4. 存在性检查（邮箱、手机号唯一性验证）
5. 业务统计和分析（用户活跃度、注册趋势等）

设计原则：
1. 单一责任：专注于用户相关的数据访问
2. 查询封装：复杂业务查询封装在Repository方法中
3. 异常统一：使用统一的异常处理机制
4. 类型安全：强类型参数和返回值
5. 性能优化：合理使用数据库索引和查询优化

使用示例：
    >>> # 创建用户Repository
    >>> user_repo = UserRepository(session)
    >>>
    >>> # 按邮箱查找用户
    >>> user = user_repo.find_by_email("user@example.com")
    >>>
    >>> # 检查邮箱是否已存在
    >>> exists = user_repo.email_exists("new@example.com")
    >>>
    >>> # 创建游客用户
    >>> guest_user = user_repo.create_guest_user("测试游客")
    >>>
    >>> # 升级游客为注册用户
    >>> registered_user = user_repo.upgrade_guest_to_registered(
    ...     guest_user.id, "registered@example.com", nickname="正式用户"
    ... )
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

# 导入基础Repository和异常类
from src.repositories.base import BaseRepository, RepositoryError, RepositoryValidationError, RepositoryNotFoundError
from src.models.user import User


class UserRepository(BaseRepository[User]):
    """
    用户Repository类

    提供用户相关的数据库操作，封装用户业务逻辑查询。
    继承自BaseRepository，专注于用户特有的业务场景。

    Attributes:
        session: SQLAlchemy会话对象
        model: User模型类
    """

    def __init__(self, session: Session):
        """
        初始化UserRepository

        Args:
            session: SQLAlchemy会话对象
        """
        super().__init__(session, User)

    def find_by_email(self, email: str) -> User:
        """
        根据邮箱查找用户

        Args:
            email: 用户邮箱地址

        Returns:
            User: 找到的用户实例

        Raises:
            RepositoryValidationError: 邮箱参数无效时
            RepositoryNotFoundError: 用户不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> user = user_repo.find_by_email("user@example.com")
            >>> print(user.nickname)
            "张三"
        """
        try:
            # 参数验证
            if not email or not isinstance(email, str):
                raise RepositoryValidationError("邮箱参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(User).where(User.email == email)

            # 执行查询
            user = self.session.exec(statement).first()

            if user is None:
                raise RepositoryNotFoundError(f"未找到邮箱为 {email} 的用户")

            return user

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据邮箱查找用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据邮箱查找用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_phone(self, phone: str) -> User:
        """
        根据手机号查找用户

        Args:
            phone: 用户手机号码

        Returns:
            User: 找到的用户实例

        Raises:
            RepositoryValidationError: 手机号参数无效时
            RepositoryNotFoundError: 用户不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> user = user_repo.find_by_phone("13800138000")
            >>> print(user.nickname)
            "张三"
        """
        try:
            # 参数验证
            if not phone or not isinstance(phone, str):
                raise RepositoryValidationError("手机号参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(User).where(User.phone == phone)

            # 执行查询
            user = self.session.exec(statement).first()

            if user is None:
                raise RepositoryNotFoundError(f"未找到手机号为 {phone} 的用户")

            return user

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据手机号查找用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据手机号查找用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_by_wechat_openid(self, wechat_openid: str) -> User:
        """
        根据微信OpenID查找用户

        Args:
            wechat_openid: 微信OpenID

        Returns:
            User: 找到的用户实例

        Raises:
            RepositoryValidationError: 微信OpenID参数无效时
            RepositoryNotFoundError: 用户不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> user = user_repo.find_by_wechat_openid("wx123456789")
            >>> print(user.nickname)
            "张三"
        """
        try:
            # 参数验证
            if not wechat_openid or not isinstance(wechat_openid, str):
                raise RepositoryValidationError("微信OpenID参数不能为空且必须是字符串类型")

            # 构建查询
            statement = select(User).where(User.wechat_openid == wechat_openid)

            # 执行查询
            user = self.session.exec(statement).first()

            if user is None:
                raise RepositoryNotFoundError(f"未找到微信OpenID为 {wechat_openid} 的用户")

            return user

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"根据微信OpenID查找用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"根据微信OpenID查找用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_registered_users(self) -> List[User]:
        """
        查找所有注册用户（非游客）

        Returns:
            List[User]: 注册用户列表

        Raises:
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> users = user_repo.find_registered_users()
            >>> print(f"共有 {len(users)} 个注册用户")
            "共有 100 个注册用户"
        """
        try:
            # 构建查询：查找非游客用户
            statement = select(User).where(User.is_guest == False).order_by(User.created_at.desc())

            # 执行查询
            users = self.session.exec(statement).all()

            return list(users)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找注册用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找注册用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_guest_users(self) -> List[User]:
        """
        查找所有游客用户

        Returns:
            List[User]: 游客用户列表

        Raises:
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> users = user_repo.find_guest_users()
            >>> print(f"共有 {len(users)} 个游客用户")
            "共有 50 个游客用户"
        """
        try:
            # 构建查询：查找游客用户
            statement = select(User).where(User.is_guest == True).order_by(User.created_at.desc())

            # 执行查询
            users = self.session.exec(statement).all()

            return list(users)

        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找游客用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找游客用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def find_active_users(self, days: int = 30) -> List[User]:
        """
        查找最近活跃用户

        Args:
            days: 活跃天数阈值，默认30天

        Returns:
            List[User]: 活跃用户列表

        Raises:
            RepositoryValidationError: 天数参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> users = user_repo.find_active_users(30)
            >>> print(f"最近30天有 {len(users)} 个活跃用户")
            "最近30天有 80 个活跃用户"
        """
        try:
            # 参数验证
            if not isinstance(days, int) or days <= 0:
                raise RepositoryValidationError("天数参数必须是正整数")

            # 计算活跃时间阈值
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 构建查询：查找最近登录时间在阈值内的用户
            statement = select(User).where(
                and_(
                    User.last_login_at >= threshold_date,
                    User.last_login_at.isnot(None)
                )
            ).order_by(User.last_login_at.desc())

            # 执行查询
            users = self.session.exec(statement).all()

            return list(users)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"查找活跃用户失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise RepositoryError(
                f"查找活跃用户时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def email_exists(self, email: str) -> bool:
        """
        检查邮箱是否已存在

        Args:
            email: 邮箱地址

        Returns:
            bool: 邮箱存在返回True，否则返回False

        Raises:
            RepositoryValidationError: 邮箱参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> exists = user_repo.email_exists("new@example.com")
            >>> if not exists:
            ...     print("邮箱可以使用")
            "邮箱可以使用"
        """
        try:
            # 参数验证
            if not email or not isinstance(email, str):
                raise RepositoryValidationError("邮箱参数不能为空且必须是字符串类型")

            # 使用基类的exists方法
            return self.exists(email=email)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"检查邮箱存在性时发生错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def phone_exists(self, phone: str) -> bool:
        """
        检查手机号是否已存在

        Args:
            phone: 手机号码

        Returns:
            bool: 手机号存在返回True，否则返回False

        Raises:
            RepositoryValidationError: 手机号参数无效时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> exists = user_repo.phone_exists("13800138000")
            >>> if not exists:
            ...     print("手机号可以使用")
            "手机号可以使用"
        """
        try:
            # 参数验证
            if not phone or not isinstance(phone, str):
                raise RepositoryValidationError("手机号参数不能为空且必须是字符串类型")

            # 使用基类的exists方法
            return self.exists(phone=phone)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"检查手机号存在性时发生错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def create_guest_user(self, nickname: str = None) -> User:
        """
        创建游客用户

        Args:
            nickname: 用户昵称，可选

        Returns:
            User: 创建的游客用户

        Raises:
            RepositoryValidationError: 数据验证失败时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> guest_user = user_repo.create_guest_user("测试游客")
            >>> print(f"创建游客用户: {guest_user.id}")
            "创建游客用户: 123e4567-e89b-12d3-a456-426614174000"
        """
        try:
            # 参数验证
            if nickname is not None and not isinstance(nickname, str):
                raise RepositoryValidationError("昵称参数必须是字符串类型")

            # 生成默认昵称（如果未提供）
            if not nickname:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                nickname = f"游客_{timestamp}"

            # 创建游客用户数据
            user_data = {
                "nickname": nickname,
                "is_guest": True
            }

            # 使用基类的create方法
            return self.create(user_data)

        except RepositoryValidationError:
            # 重新抛出验证异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"创建游客用户失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    def upgrade_guest_to_registered(self, user_id: str, email: str, **kwargs) -> User:
        """
        将游客用户升级为注册用户

        Args:
            user_id: 用户ID
            email: 用户邮箱
            **kwargs: 其他用户信息（如昵称、手机号、微信OpenID等）

        Returns:
            User: 升级后的用户

        Raises:
            RepositoryValidationError: 数据验证失败时
            RepositoryNotFoundError: 用户不存在时
            RepositoryError: 数据库操作错误时

        Example:
            >>> user_repo = UserRepository(session)
            >>> upgraded_user = user_repo.upgrade_guest_to_registered(
            ...     guest_user.id,
            ...     "registered@example.com",
            ...     nickname="正式用户",
            ...     phone="13800138000"
            ... )
            >>> print(f"用户已升级: {upgraded_user.is_guest}")
            "用户已升级: False"
        """
        try:
            # 参数验证
            if not user_id or not isinstance(user_id, str):
                raise RepositoryValidationError("用户ID参数不能为空且必须是字符串类型")

            if not email or not isinstance(email, str):
                raise RepositoryValidationError("邮箱参数不能为空且必须是字符串类型")

            # 查找用户
            user = self.get_by_id(user_id)
            if user is None:
                raise RepositoryNotFoundError(f"未找到ID为 {user_id} 的用户")

            # 检查是否为游客用户
            if not user.is_guest:
                raise RepositoryValidationError(f"用户 {user_id} 已经是注册用户，无需升级")

            # 检查邮箱是否已被其他用户使用
            if self.email_exists(email):
                raise RepositoryValidationError(f"邮箱 {email} 已被其他用户使用")

            # 构建更新数据
            update_data = {
                "email": email,
                "is_guest": False,
                **kwargs
            }

            # 移除不允许更新的字段
            update_data.pop("id", None)
            update_data.pop("created_at", None)
            update_data.pop("updated_at", None)

            # 更新用户
            return self.update(user_id, update_data)

        except (RepositoryValidationError, RepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except Exception as e:
            raise RepositoryError(
                f"升级游客用户失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )


# 导出UserRepository类
__all__ = ["UserRepository"]