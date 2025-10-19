"""
服务层基类

该模块定义了服务层的基类，提供统一的服务接口和通用功能。
所有具体的服务类都应该继承自BaseService，确保服务层的一致性和可维护性。

设计原则：
1. 统一接口：提供一致的服务方法和行为
2. 错误处理：统一的异常处理和错误传播机制
3. 依赖注入：通过构造函数注入Repository依赖
4. 事务管理：通过Repository层管理数据库事务
5. 日志记录：统一的操作日志记录
6. 类型安全：使用类型提示确保代码安全性

核心功能：
- Repository依赖管理
- 异常处理和包装
- 操作日志记录
- 通用业务方法
- 参数验证
"""

from abc import ABC
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

from src.repositories.base import BaseRepository
from src.repositories.user import UserRepository
from src.repositories.task import TaskRepository
from src.repositories.focus import FocusRepository
from src.repositories.reward import RewardRepository
from .exceptions import BusinessException, wrap_repository_error


# 配置日志记录器
logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    服务层基类

    提供所有服务类的通用功能和接口。包括Repository管理、
    异常处理、日志记录等基础能力。

    Attributes:
        _user_repo (UserRepository): 用户数据访问对象
        _task_repo (TaskRepository): 任务数据访问对象
        _focus_repo (FocusRepository): 专注数据访问对象
        _reward_repo (RewardRepository): 奖励数据访问对象
        _logger (logging.Logger): 日志记录器
    """

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        focus_repo: Optional[FocusRepository] = None,
        reward_repo: Optional[RewardRepository] = None
    ):
        """
        初始化服务基类

        Args:
            user_repo: 用户数据访问对象，可选
            task_repo: 任务数据访问对象，可选
            focus_repo: 专注数据访问对象，可选
            reward_repo: 奖励数据访问对象，可选
        """
        self._user_repo = user_repo
        self._task_repo = task_repo
        self._focus_repo = focus_repo
        self._reward_repo = reward_repo
        self._logger = logger

        # 服务名称，用于日志记录
        self._service_name = self.__class__.__name__

        # 记录服务创建
        self._log_info("Service initialized", {
            "service": self._service_name,
            "repositories": {
                "user_repo": user_repo is not None,
                "task_repo": task_repo is not None,
                "focus_repo": focus_repo is not None,
                "reward_repo": reward_repo is not None
            }
        })

    # ==================== 日志记录方法 ====================

    def _log_info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录信息级别日志

        Args:
            message: 日志消息
            context: 上下文信息
        """
        log_data = {
            "service": self._service_name,
            "timestamp": datetime.now().isoformat(),
            **(context or {})
        }
        self._logger.info(f"{self._service_name}: {message}", extra=log_data)

    def _log_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录警告级别日志

        Args:
            message: 日志消息
            context: 上下文信息
        """
        log_data = {
            "service": self._service_name,
            "timestamp": datetime.now().isoformat(),
            **(context or {})
        }
        self._logger.warning(f"{self._service_name}: {message}", extra=log_data)

    def _log_error(self, message: str, error: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录错误级别日志

        Args:
            message: 日志消息
            error: 异常对象
            context: 上下文信息
        """
        log_data = {
            "service": self._service_name,
            "timestamp": datetime.now().isoformat(),
            **(context or {})
        }
        if error:
            log_data["error_type"] = error.__class__.__name__
            log_data["error_message"] = str(error)

        self._logger.error(f"{self._service_name}: {message}", extra=log_data, exc_info=error)

    # ==================== 异常处理方法 ====================

    def _handle_repository_error(self, error: Exception, operation: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        处理Repository层异常，转换为Service层异常并重新抛出

        Args:
            error: Repository层异常
            operation: 操作描述
            context: 操作上下文

        Raises:
            BusinessException: 转换后的业务异常
        """
        # 记录原始异常
        self._log_error(f"Repository error in {operation}", error, context)

        # 包装并抛出业务异常
        service_exception = wrap_repository_error(error, f"{self._service_name}.{operation}")

        # 添加服务上下文信息
        if context:
            service_exception.details.update(context)

        raise service_exception

    def _validate_required_params(self, params: Dict[str, Any], required_fields: List[str]) -> None:
        """
        验证必需参数

        Args:
            params: 参数字典
            required_fields: 必需字段列表

        Raises:
            ValidationException: 当缺少必需参数时
        """
        from .exceptions import ValidationException

        missing_fields = [field for field in required_fields if field not in params or params[field] is None]
        if missing_fields:
            raise ValidationException(
                message=f"Missing required parameters: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields, "provided_params": list(params.keys())}
            )

    # ==================== 通用业务方法 ====================

    def _check_resource_exists(self, repo: BaseRepository, resource_id: str, resource_type: str) -> Any:
        """
        检查资源是否存在

        Args:
            repo: Repository对象
            resource_id: 资源ID
            resource_type: 资源类型

        Returns:
            资源对象

        Raises:
            ResourceNotFoundException: 当资源不存在时
        """
        try:
            resource = repo.get_by_id(resource_id)
            if not resource:
                from .exceptions import ResourceNotFoundException
                raise ResourceNotFoundException(
                    resource_type=resource_type,
                    resource_id=resource_id
                )
            return resource
        except Exception as e:
            if isinstance(e, BusinessException):
                raise
            self._handle_repository_error(e, f"check_{resource_type.lower()}_exists", {"resource_id": resource_id})

    def _paginate_results(self, repo: BaseRepository, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """
        分页查询结果

        Args:
            repo: Repository对象
            page: 页码，从1开始
            per_page: 每页数量
            **filters: 过滤条件

        Returns:
            包含分页信息的字典
        """
        try:
            # 计算偏移量
            offset = (page - 1) * per_page

            # 查询总数
            total_count = repo.count(**filters)

            # 查询数据
            items = repo.find_many(limit=per_page, offset=offset, **filters)

            # 计算分页信息
            total_pages = (total_count + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "items": items,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
        except Exception as e:
            self._handle_repository_error(e, "paginate_results", {"page": page, "per_page": per_page, "filters": filters})

    # ==================== 事务管理方法 ====================

    def _execute_in_transaction(self, operation_func, *args, **kwargs):
        """
        在事务中执行操作

        注意：这里的事务管理通过Repository层实现，
        具体的实现方式取决于Repository层的设计。

        Args:
            operation_func: 要在事务中执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            操作结果

        Raises:
            BusinessException: 当操作失败时
        """
        try:
            self._log_info("Starting transaction", {"operation": operation_func.__name__})

            # 执行操作
            result = operation_func(*args, **kwargs)

            self._log_info("Transaction completed successfully", {"operation": operation_func.__name__})
            return result

        except Exception as e:
            self._log_error("Transaction failed", e, {"operation": operation_func.__name__})

            # 如果已经是业务异常，直接重新抛出
            if isinstance(e, BusinessException):
                raise

            # 否则包装为业务异常
            self._handle_repository_error(e, operation_func.__name__)

    # ==================== 数据转换方法 ====================

    def _to_dict(self, obj: Any, exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        将对象转换为字典

        Args:
            obj: 要转换的对象
            exclude_fields: 要排除的字段列表

        Returns:
            对象的字典表示
        """
        if obj is None:
            return {}

        # 如果对象已经有to_dict方法
        if hasattr(obj, 'to_dict'):
            result = obj.to_dict()
        else:
            # 使用对象的__dict__属性
            result = vars(obj).copy()

        # 排除指定字段
        if exclude_fields:
            for field in exclude_fields:
                result.pop(field, None)

        return result

    def _filter_sensitive_data(self, data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:
        """
        过滤敏感数据

        Args:
            data: 原始数据
            sensitive_fields: 敏感字段列表

        Returns:
            过滤后的数据
        """
        if sensitive_fields is None:
            sensitive_fields = ['password_hash', 'token', 'secret', 'key']

        filtered_data = data.copy()
        for field in sensitive_fields:
            if field in filtered_data:
                filtered_data[field] = "***"

        return filtered_data

    # ==================== 性能监控方法 ====================

    def _measure_execution_time(self, operation_name: str):
        """
        测量操作执行时间的上下文管理器

        Args:
            operation_name: 操作名称

        Returns:
            上下文管理器
        """
        from contextlib import contextmanager
        import time

        @contextmanager
        def timer():
            start_time = time.time()
            try:
                yield
            finally:
                execution_time = time.time() - start_time
                self._log_info(f"Operation completed", {
                    "operation": operation_name,
                    "execution_time_seconds": round(execution_time, 3)
                })

        return timer()

    # ==================== 依赖注入辅助方法 ====================

    def _ensure_repository(self, repo_name: str) -> BaseRepository:
        """
        确保Repository已注入

        Args:
            repo_name: Repository名称

        Returns:
            Repository实例

        Raises:
            BusinessException: 当Repository未注入时
        """
        repo = getattr(self, f"_{repo_name}", None)
        if repo is None:
            raise BusinessException(
                error_code="SERVICE_DEPENDENCY_MISSING",
                message=f"Repository '{repo_name}' is not injected",
                user_message="服务配置错误，请联系管理员",
                details={"service": self._service_name, "missing_repository": repo_name}
            )
        return repo

    def get_user_repository(self) -> UserRepository:
        """获取用户Repository"""
        return self._ensure_repository("user_repo")

    def get_task_repository(self) -> TaskRepository:
        """获取任务Repository"""
        return self._ensure_repository("task_repo")

    def get_focus_repository(self) -> FocusRepository:
        """获取专注Repository"""
        return self._ensure_repository("focus_repo")

    def get_reward_repository(self) -> RewardRepository:
        """获取奖励Repository"""
        return self._ensure_repository("reward_repo")


class ServiceFactory:
    """
    服务工厂类

    提供统一的Service实例创建方法，简化依赖注入过程。
    """

    @staticmethod
    def create_service(
        service_class: type,
        user_repo: Optional[UserRepository] = None,
        task_repo: Optional[TaskRepository] = None,
        focus_repo: Optional[FocusRepository] = None,
        reward_repo: Optional[RewardRepository] = None
    ) -> BaseService:
        """
        创建服务实例

        Args:
            service_class: 服务类
            user_repo: 用户Repository
            task_repo: 任务Repository
            focus_repo: 专注Repository
            reward_repo: 奖励Repository

        Returns:
            服务实例
        """
        return service_class(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo
        )

    @staticmethod
    def create_service_with_session(service_class: type, session) -> BaseService:
        """
        使用数据库会话创建服务实例

        Args:
            service_class: 服务类
            session: 数据库会话

        Returns:
            服务实例
        """
        return ServiceFactory.create_service(
            service_class=service_class,
            user_repo=UserRepository(session) if session else None,
            task_repo=TaskRepository(session) if session else None,
            focus_repo=FocusRepository(session) if session else None,
            reward_repo=RewardRepository(session) if session else None
        )