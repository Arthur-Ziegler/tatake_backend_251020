"""
异步基础Repository类

提供统一的异步数据访问层抽象，实现Repository模式的核心功能。
支持泛型操作，确保类型安全和代码复用。

功能特性：
1. 异步基础CRUD操作（创建、读取、更新、删除）
2. 异步查询方法（获取所有、存在性检查、计数）
3. 参数验证和异常处理
4. 泛型类型支持，确保类型安全
5. 可扩展设计，支持具体Repository类扩展

设计原则：
1. 单一责任：只负责数据访问操作
2. 开闭原则：对扩展开放，对修改封闭
3. 依赖倒置：依赖抽象而非具体实现
4. 接口隔离：提供简洁明确的接口

使用示例：
    >>> # 创建异步Repository实例
    >>> user_repo = AsyncBaseRepository(async_session, User)
    >>>
    >>> # 创建用户
    >>> user_data = {"nickname": "张三", "email": "zhangsan@example.com"}
    >>> user = await user_repo.create(user_data)
    >>>
    >>> # 查询用户
    >>> found_user = await user_repo.get_by_id(user.id)
    >>> all_users = await user_repo.get_all()
    >>>
    >>> # 更新用户
    >>> updated_user = await user_repo.update(user.id, {"nickname": "李四"})
    >>>
    >>> # 检查存在性和计数
    >>> exists = await user_repo.exists(email="zhangsan@example.com")
    >>> count = await user_repo.count()
"""

from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

# 导入基础模型
from src.models.base_model import BaseSQLModel

# 泛型类型变量，约束为BaseSQLModel的子类
T = TypeVar('T', bound=BaseSQLModel)


class AsyncRepositoryError(Exception):
    """异步Repository操作异常基类"""

    def __init__(self, message: str, operation: str = None, model_name: str = None):
        """
        初始化异步Repository异常

        Args:
            message: 异常消息
            operation: 操作类型（create, read, update, delete等）
            model_name: 模型名称
        """
        super().__init__(message)
        self.operation = operation
        self.model_name = model_name


class AsyncRepositoryValidationError(AsyncRepositoryError):
    """异步数据验证异常"""

    def __init__(self, message: str, field_errors: Dict[str, List[str]] = None):
        """
        初始化异步验证异常

        Args:
            message: 异常消息
            field_errors: 字段级别的错误信息
        """
        super().__init__(message, "validation")
        self.field_errors = field_errors or {}


class AsyncRepositoryNotFoundError(AsyncRepositoryError):
    """异步资源未找到异常"""

    def __init__(self, message: str, resource_id: str = None):
        """
        初始化异步未找到异常

        Args:
            message: 异常消息
            resource_id: 资源ID
        """
        super().__init__(message, "read")
        self.resource_id = resource_id


class AsyncRepositoryIntegrityError(AsyncRepositoryError):
    """异步数据完整性异常"""

    def __init__(self, message: str, constraint: str = None):
        """
        初始化异步完整性异常

        Args:
            message: 异常消息
            constraint: 约束名称
        """
        super().__init__(message, "integrity")
        self.constraint = constraint


class AsyncBaseRepository(Generic[T]):
    """
    异步基础Repository类

    提供统一的异步数据访问接口，支持泛型操作和类型安全。
    所有具体异步Repository类都应该继承自这个基类。

    Attributes:
        session: SQLAlchemy异步会话对象
        model: Repository管理的模型类
        model_name: 模型名称，用于错误消息
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        初始化异步Repository

        Args:
            session: SQLAlchemy异步会话对象
            model: 要管理的模型类，必须继承自BaseSQLModel

        Raises:
            TypeError: 当session或model参数类型不正确时
        """
        # 参数验证 - 检查session是否有基本的异步会话方法
        if not hasattr(session, 'execute') or not hasattr(session, 'commit') or not hasattr(session, 'close'):
            raise TypeError(f"session参数必须是有效的异步数据库会话对象，实际类型: {type(session).__name__}")

        if not (isinstance(model, type) and issubclass(model, BaseSQLModel)):
            raise TypeError(f"model参数必须是BaseSQLModel的子类，实际类型: {type(model).__name__}")

        self.session = session
        self.model = model
        self.model_name = model.__name__

    async def create(self, obj_data: Dict[str, Any]) -> T:
        """
        异步创建新对象

        Args:
            obj_data: 包含对象数据的字典

        Returns:
            T: 创建的对象实例

        Raises:
            AsyncRepositoryValidationError: 数据验证失败时
            AsyncRepositoryIntegrityError: 数据完整性约束冲突时
            AsyncRepositoryError: 其他数据库操作错误时
        """
        try:
            # 参数验证
            if not isinstance(obj_data, dict):
                raise AsyncRepositoryValidationError(
                    f"obj_data参数必须是字典类型，实际类型: {type(obj_data).__name__}"
                )

            # 创建模型实例
            db_obj = self.model(**obj_data)

            # 添加到会话并提交
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)

            return db_obj

        except ValidationError as e:
            # Pydantic验证错误
            await self.session.rollback()
            raise AsyncRepositoryValidationError(
                f"数据验证失败: {str(e)}",
                field_errors=e.errors() if hasattr(e, 'errors') else None
            )
        except IntegrityError as e:
            # 数据完整性错误
            await self.session.rollback()
            raise AsyncRepositoryIntegrityError(
                f"数据完整性约束冲突: {str(e)}",
                constraint=getattr(e, 'orig', None)
            )
        except SQLAlchemyError as e:
            # 其他SQLAlchemy错误
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"创建{self.model_name}失败: {str(e)}",
                operation="create",
                model_name=self.model_name
            )
        except Exception as e:
            # 其他未预期错误
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"创建{self.model_name}时发生未知错误: {str(e)}",
                operation="create",
                model_name=self.model_name
            )

    async def get_by_id(self, obj_id: Union[str, UUID]) -> Optional[T]:
        """
        异步根据ID获取对象

        Args:
            obj_id: 对象ID，支持字符串和UUID类型

        Returns:
            Optional[T]: 找到的对象实例，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: ID参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if obj_id is None:
                raise AsyncRepositoryValidationError("obj_id参数不能为None")

            if not isinstance(obj_id, (str, UUID)):
                raise AsyncRepositoryValidationError(
                    f"obj_id参数必须是字符串或UUID类型，实际类型: {type(obj_id).__name__}"
                )

            # 构建查询
            statement = select(self.model).where(self.model.id == str(obj_id))

            # 执行查询
            result = await self.session.execute(statement)
            db_obj = result.scalar_one_or_none()

            return db_obj

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询{self.model_name}失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询{self.model_name}时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def get_all(self, **filters) -> List[T]:
        """
        异步获取所有对象，支持过滤条件

        Args:
            **filters: 过滤条件，关键字参数

        Returns:
            List[T]: 对象列表

        Raises:
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 构建基础查询
            statement = select(self.model)

            # 应用过滤条件
            for key, value in filters.items():
                if hasattr(self.model, key):
                    if isinstance(value, (list, tuple)):
                        # 支持IN查询
                        statement = statement.where(getattr(self.model, key).in_(value))
                    else:
                        # 精确匹配查询
                        statement = statement.where(getattr(self.model, key) == value)

            # 执行查询并返回结果
            result = await self.session.execute(statement)
            db_objects = result.scalars().all()

            return list(db_objects)

        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"查询{self.model_name}列表失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"查询{self.model_name}列表时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def update(self, obj_id: Union[str, UUID], update_data: Dict[str, Any]) -> Optional[T]:
        """
        异步更新对象

        Args:
            obj_id: 对象ID
            update_data: 要更新的数据字典

        Returns:
            Optional[T]: 更新后的对象，未找到时返回None

        Raises:
            AsyncRepositoryValidationError: 数据验证失败时
            AsyncRepositoryNotFoundError: 对象不存在时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if obj_id is None:
                raise AsyncRepositoryValidationError("obj_id参数不能为None")

            if not isinstance(obj_id, (str, UUID)):
                raise AsyncRepositoryValidationError(
                    f"obj_id参数必须是字符串或UUID类型，实际类型: {type(obj_id).__name__}"
                )

            if not isinstance(update_data, dict):
                raise AsyncRepositoryValidationError(
                    f"update_data参数必须是字典类型，实际类型: {type(update_data).__name__}"
                )

            if not update_data:
                raise AsyncRepositoryValidationError("update_data参数不能为空字典")

            # 查找现有对象
            db_obj = await self.get_by_id(obj_id)
            if db_obj is None:
                raise AsyncRepositoryNotFoundError(
                    f"未找到ID为{obj_id}的{self.model_name}",
                    resource_id=str(obj_id)
                )

            # 更新字段
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # 提交更改并刷新对象
            await self.session.commit()
            await self.session.refresh(db_obj)

            return db_obj

        except (AsyncRepositoryValidationError, AsyncRepositoryNotFoundError):
            # 重新抛出已知异常
            raise
        except IntegrityError as e:
            await self.session.rollback()
            raise AsyncRepositoryIntegrityError(
                f"更新{self.model_name}时完整性约束冲突: {str(e)}",
                constraint=getattr(e, 'orig', None)
            )
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"更新{self.model_name}失败: {str(e)}",
                operation="update",
                model_name=self.model_name
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"更新{self.model_name}时发生未知错误: {str(e)}",
                operation="update",
                model_name=self.model_name
            )

    async def delete(self, obj_id: Union[str, UUID]) -> bool:
        """
        异步删除对象

        Args:
            obj_id: 对象ID

        Returns:
            bool: 删除成功返回True，对象不存在返回False

        Raises:
            AsyncRepositoryValidationError: ID参数无效时
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 参数验证
            if obj_id is None:
                raise AsyncRepositoryValidationError("obj_id参数不能为None")

            if not isinstance(obj_id, (str, UUID)):
                raise AsyncRepositoryValidationError(
                    f"obj_id参数必须是字符串或UUID类型，实际类型: {type(obj_id).__name__}"
                )

            # 查找对象
            db_obj = await self.get_by_id(obj_id)
            if db_obj is None:
                return False

            # 删除对象
            await self.session.delete(db_obj)
            await self.session.commit()

            return True

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"删除{self.model_name}失败: {str(e)}",
                operation="delete",
                model_name=self.model_name
            )
        except Exception as e:
            await self.session.rollback()
            raise AsyncRepositoryError(
                f"删除{self.model_name}时发生未知错误: {str(e)}",
                operation="delete",
                model_name=self.model_name
            )

    async def exists(self, **filters) -> bool:
        """
        异步检查对象是否存在

        Args:
            **filters: 过滤条件，关键字参数

        Returns:
            bool: 对象存在返回True，否则返回False

        Raises:
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            if not filters:
                raise AsyncRepositoryValidationError("至少需要提供一个过滤条件")

            # 构建查询
            statement = select(func.count()).select_from(self.model)

            # 应用过滤条件
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)

            if not conditions:
                raise AsyncRepositoryValidationError("提供的过滤条件中没有有效的字段")

            statement = statement.where(and_(*conditions))

            # 执行查询并检查结果
            result = await self.session.execute(statement)
            count = result.scalar()

            return count > 0

        except AsyncRepositoryValidationError:
            # 重新抛出验证异常
            raise
        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"检查{self.model_name}存在性失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"检查{self.model_name}存在性时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    async def count(self, **filters) -> int:
        """
        异步统计对象数量

        Args:
            **filters: 过滤条件，关键字参数

        Returns:
            int: 对象数量

        Raises:
            AsyncRepositoryError: 数据库操作错误时
        """
        try:
            # 构建计数查询
            statement = select(func.count()).select_from(self.model)

            # 应用过滤条件（如果有）
            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        if isinstance(value, (list, tuple)):
                            conditions.append(getattr(self.model, key).in_(value))
                        else:
                            conditions.append(getattr(self.model, key) == value)

                if conditions:
                    statement = statement.where(and_(*conditions))

            # 执行查询并返回计数
            result = await self.session.execute(statement)
            count = result.scalar()

            return count or 0

        except SQLAlchemyError as e:
            raise AsyncRepositoryError(
                f"统计{self.model_name}数量失败: {str(e)}",
                operation="read",
                model_name=self.model_name
            )
        except Exception as e:
            raise AsyncRepositoryError(
                f"统计{self.model_name}数量时发生未知错误: {str(e)}",
                operation="read",
                model_name=self.model_name
            )

    def __repr__(self) -> str:
        """
        返回异步Repository的字符串表示

        Returns:
            str: Repository的描述信息
        """
        return f"{self.__class__.__name__}(model={self.model_name})"


# 导出所有相关类
__all__ = [
    "AsyncBaseRepository",
    "AsyncRepositoryError",
    "AsyncRepositoryValidationError",
    "AsyncRepositoryNotFoundError",
    "AsyncRepositoryIntegrityError"
]