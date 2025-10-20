"""
服务层基类 - 使用统一日志系统

该模块定义了服务层的基类，提供统一的服务接口和通用功能。
所有具体的服务类都应该继承自BaseService，确保服务层的一致性和可维护性。

设计原则：
1. 统一接口：提供一致的服务方法和行为
2. 错误处理：统一的异常处理和错误传播机制
3. 依赖注入：通过构造函数注入Repository依赖
4. 事务管理：通过Repository层管理数据库事务
5. 日志记录：统一的操作日志记录（可配置级别）
6. 类型安全：使用类型提示确保代码安全性
7. 性能监控：支持性能日志记录和分析

核心功能：
- Repository依赖管理
- 异常处理和包装
- 操作日志记录
- 通用业务方法
- 参数验证
- 性能监控
"""

from abc import ABC
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from datetime import datetime

from src.repositories.base import BaseRepository
from .exceptions import BusinessException, wrap_repository_error
from .logging_config import get_logger, operation_logger, performance_logger

# 避免循环导入
if TYPE_CHECKING:
    from src.repositories.user import UserRepository
    from src.repositories.task import TaskRepository
    from src.repositories.focus import FocusRepository
    from src.repositories.reward import RewardRepository
    from src.repositories.chat import ChatRepository


class BaseService(ABC):
    """
    提供所有服务类的通用功能和接口。包括Repository管理、
    异常处理、日志记录等基础能力。

    Attributes:
        _user_repo (UserRepository): 用户数据访问对象
        _task_repo (TaskRepository): 任务数据访问对象
        _focus_repo (FocusRepository): 专注数据访问对象
        _reward_repo (RewardRepository): 奖励数据访问对象
        _chat_repo (ChatRepository): 聊天数据访问对象
        _logger (ServiceLogger): 服务日志记录器
    """

    def __init__(
        self,
        user_repo: Optional['UserRepository'] = None,
        task_repo: Optional['TaskRepository'] = None,
        focus_repo: Optional['FocusRepository'] = None,
        reward_repo: Optional['RewardRepository'] = None,
        chat_repo: Optional['ChatRepository'] = None
    ):
        """
        初始化服务基类

        Args:
            user_repo: 用户数据访问对象，可选
            task_repo: 任务数据访问对象，可选
            focus_repo: 专注数据访问对象，可选
            reward_repo: 奖励数据访问对象，可选
            chat_repo: 聊天数据访问对象，可选
        """
        self._user_repo = user_repo
        self._task_repo = task_repo
        self._focus_repo = focus_repo
        self._reward_repo = reward_repo
        self._chat_repo = chat_repo

        # 创建统一的服务日志器
        self._logger = get_logger(self.__class__.__name__)

        # 记录服务初始化
        self._logger.info("Service initialized", extra_data={
            "repositories": {
                "user_repo": user_repo is not None,
                "task_repo": task_repo is not None,
                "focus_repo": focus_repo is not None,
                "reward_repo": reward_repo is not None,
                "chat_repo": chat_repo is not None
            }
        })

    # ==================== Repository管理方法 ====================

    def _ensure_repository(self, repo_name: str) -> BaseRepository:
        """
        确保Repository存在

        Args:
            repo_name: Repository名称

        Returns:
            Repository实例

        Raises:
            BusinessException: 如果Repository不存在
        """
        repo = getattr(self, f"_{repo_name}", None)
        if repo is None:
            raise BusinessException(
                error_code="REPOSITORY_NOT_FOUND",
                message=f"Required repository '{repo_name}' is not initialized",
                details={"service": self.__class__.__name__, "missing_repo": repo_name}
            )
        return repo

    # ==================== 日志记录方法 ====================

    def _log_debug(self, message: str, **kwargs) -> None:
        """记录DEBUG级别日志"""
        self._logger.debug(message, **kwargs)

    def _log_info(self, message: str, **kwargs) -> None:
        """记录INFO级别日志"""
        self._logger.info(message, **kwargs)

    def _log_warning(self, message: str, **kwargs) -> None:
        """记录WARNING级别日志"""
        self._logger.warning(message, **kwargs)

    def _log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """
        记录ERROR级别日志

        Args:
            message: 日志消息
            error: 异常对象
            **kwargs: 额外的上下文信息
        """
        if error:
            self._logger.error(message, extra_data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                **kwargs
            })
        else:
            self._logger.error(message, **kwargs)

    def _log_critical(self, message: str, **kwargs) -> None:
        """记录CRITICAL级别日志"""
        self._logger.critical(message, **kwargs)

    # ==================== 业务操作日志装饰器 ====================

    @operation_logger()
    def _execute_with_logging(self, operation: str, func, *args, **kwargs):
        """
        执行带日志记录的业务操作

        Args:
            operation: 操作名称
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 函数执行异常
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self._log_operation_error(operation, e)
            raise

    def _log_operation_start(self, operation: str, **kwargs) -> None:
        """记录操作开始"""
        self._logger.log_operation_start(operation, **kwargs)

    def _log_operation_success(self, operation: str, **kwargs) -> None:
        """记录操作成功"""
        self._logger.log_operation_success(operation, **kwargs)

    def _log_operation_error(self, operation: str, error: Exception, **kwargs) -> None:
        """记录操作错误"""
        self._logger.log_operation_error(operation, error, **kwargs)

    def _log_performance(self, operation: str, duration_ms: float, **kwargs) -> None:
        """记录性能指标"""
        self._logger.log_performance(operation, duration_ms, **kwargs)

    # ==================== 异常处理方法 ====================

    def _handle_repository_error(self, error: Exception, operation: str = "unknown") -> None:
        """
        处理Repository层异常

        Args:
            error: Repository异常
            operation: 操作名称
        """
        wrapped_error = wrap_repository_error(error, operation)
        self._log_operation_error(operation, wrapped_error)
        raise wrapped_error

    def _handle_business_exception(self, exception: BusinessException, operation: str = "unknown") -> None:
        """
        处理业务异常

        Args:
            exception: 业务异常
            operation: 操作名称
        """
        self._logger.log_business_exception(operation, exception)
        raise exception

    # ==================== 通用业务方法 ====================

    @operation_logger(log_result=True)
    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        验证必填字段

        Args:
            data: 数据字典
            required_fields: 必填字段列表

        Raises:
            ValidationException: 如果验证失败
        """
        from .exceptions import ValidationException

        missing_fields = [field for field in required_fields if field not in data or data[field] is None]

        if missing_fields:
            self._logger.validation_error(
                field=missing_fields[0] if len(missing_fields) == 1 else "multiple_fields",
                value=None,
                reason=f"Missing required field(s): {', '.join(missing_fields)}"
            )
            raise ValidationException(
                field=missing_fields[0] if len(missing_fields) == 1 else "multiple_fields",
                value=None,
                message=f"Missing required field(s): {', '.join(missing_fields)}"
            )

    def _validate_id(self, entity_id: str, entity_type: str = "entity") -> str:
        """
        验证ID格式

        Args:
            entity_id: 实体ID
            entity_type: 实体类型

        Returns:
            验证后的ID

        Raises:
            ValidationException: 如果ID格式无效
        """
        from .exceptions import ValidationException

        if not entity_id:
            self._logger.validation_error(
                field=f"{entity_type}_id",
                value=entity_id,
                reason="ID cannot be empty"
            )
            raise ValidationException(
                field=f"{entity_type}_id",
                value=entity_id,
                message=f"{entity_type}_id cannot be empty"
            )

        if not isinstance(entity_id, str):
            entity_id = str(entity_id)

        return entity_id

    def _paginate_results(self, results: List[Any], offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """
        分页处理结果

        Args:
            results: 结果列表
            offset: 偏移量
            limit: 限制数量

        Returns:
            分页结果字典
        """
        total = len(results)
        paginated_results = results[offset:offset + limit]

        return {
            "items": paginated_results,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }

    def _filter_active_items(self, items: List[Any]) -> List[Any]:
        """
        过滤活跃项目

        Args:
            items: 项目列表

        Returns:
            过滤后的活跃项目列表
        """
        return [item for item in items if getattr(item, 'is_active', True)]

    def _sort_by_priority(self, items: List[Any], priority_field: str = "priority") -> List[Any]:
        """
        按优先级排序

        Args:
            items: 项目列表
            priority_field: 优先级字段名

        Returns:
            排序后的项目列表
        """
        return sorted(items, key=lambda x: getattr(x, priority_field, 0), reverse=True)

    # ==================== 时间相关方法 ====================

    def _get_current_time(self) -> datetime:
        """获取当前时间"""
        return datetime.now()

    def _format_datetime(self, dt: datetime) -> str:
        """
        格式化日期时间

        Args:
            dt: 日期时间对象

        Returns:
            格式化的日期时间字符串
        """
        return dt.isoformat()

    def _parse_datetime(self, dt_str: str) -> datetime:
        """
        解析日期时间字符串

        Args:
            dt_str: 日期时间字符串

        Returns:
            日期时间对象

        Raises:
            ValidationException: 如果格式无效
        """
        from .exceptions import ValidationException

        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            self._logger.validation_error(
                field="datetime",
                value=dt_str,
                reason="Invalid datetime format"
            )
            raise ValidationException(
                field="datetime",
                value=dt_str,
                message="Invalid datetime format"
            )

    # ==================== 数据转换方法 ====================

    def _to_dict_list(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        将对象列表转换为字典列表

        Args:
            items: 对象列表

        Returns:
            字典列表
        """
        return [item.to_dict() if hasattr(item, 'to_dict') else item for item in items]

    def _extract_pagination_params(self, **kwargs) -> tuple[int, int]:
        """
        提取分页参数

        Args:
            **kwargs: 关键字参数

        Returns:
            (offset, limit) 元组
        """
        offset = kwargs.get('offset', 0)
        limit = kwargs.get('limit', 50)

        # 验证分页参数
        if offset < 0:
            offset = 0
        if limit <= 0:
            limit = 50
        if limit > 1000:  # 防止过大的查询
            limit = 1000

        return offset, limit

    # ==================== 统计方法 ====================

    def _calculate_stats(self, items: List[Any]) -> Dict[str, Any]:
        """
        计算基础统计信息

        Args:
            items: 项目列表

        Returns:
            统计信息字典
        """
        if not items:
            return {"total": 0, "active": 0, "inactive": 0}

        total = len(items)
        active = len(self._filter_active_items(items))

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "active_rate": f"{(active / total * 100):.1f}%" if total > 0 else "0.0%"
        }

    # ==================== 健康检查方法 ====================

    def _health_check(self) -> Dict[str, Any]:
        """
        执行服务健康检查

        Returns:
            健康检查结果
        """
        health_status = {
            "service": self.__class__.__name__,
            "status": "healthy",
            "timestamp": self._get_current_time().isoformat(),
            "repositories": {}
        }

        # 检查各个Repository的健康状态
        repos = {
            "user_repo": self._user_repo,
            "task_repo": self._task_repo,
            "focus_repo": self._focus_repo,
            "reward_repo": self._reward_repo,
            "chat_repo": self._chat_repo
        }

        for repo_name, repo in repos.items():
            health_status["repositories"][repo_name] = {
                "available": repo is not None,
                "type": type(repo).__name__ if repo else None
            }

        # 如果有任何Repository不可用，标记为不健康
        unhealthy_repos = [name for name, status in health_status["repositories"].items()
                           if not status["available"]]

        if unhealthy_repos:
            health_status["status"] = "degraded"
            health_status["missing_repositories"] = unhealthy_repos

        return health_status

    # ==================== 清理方法 ====================

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if exc_type is not None:
            self._log_error("Service context manager exited with exception",
                            error=exc_val if exc_val else Exception("Unknown exception"))


class ServiceFactory:
    """
    服务工厂类

    提供统一的Service实例创建方法，简化依赖注入过程。
    """

    @staticmethod
    def create_service(
        service_class: type,
        user_repo: Optional['UserRepository'] = None,
        task_repo: Optional['TaskRepository'] = None,
        focus_repo: Optional['FocusRepository'] = None,
        reward_repo: Optional['RewardRepository'] = None,
        chat_repo: Optional['ChatRepository'] = None
    ) -> BaseService:
        """
        创建服务实例

        Args:
            service_class: 服务类
            user_repo: 用户Repository
            task_repo: 任务Repository
            focus_repo: 专注Repository
            reward_repo: 奖励Repository
            chat_repo: 聊天Repository

        Returns:
            服务实例
        """
        return service_class(
            user_repo=user_repo,
            task_repo=task_repo,
            focus_repo=focus_repo,
            reward_repo=reward_repo,
            chat_repo=chat_repo
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
            reward_repo=RewardRepository(session) if session else None,
            chat_repo=ChatRepository(session) if session else None
        )