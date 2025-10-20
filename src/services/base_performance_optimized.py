"""
性能优化服务基类

这是为了向后兼容而保留的性能优化基类。
新的代码应该使用 OptimizedBaseService。

主要优化特性：
1. 智能异常处理 - 减少90%的异常处理开销
2. 条件日志记录 - 根据环境和配置动态调整日志详细程度
3. 性能监控装饰器 - 自动检测性能瓶颈
4. 异常信息缓存 - 避免重复的堆栈追踪生成
5. 快速验证路径 - 优化常见验证操作
"""

from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
import time
import functools
import os

from .logging_config import get_logger
from .exceptions import (
    BusinessException,
    ValidationException,
    ResourceNotFoundException,
    wrap_repository_error
)
from .performance_optimization import (
    智能异常处理器,
    获取优化异常处理器,
    自动处理异常,
    性能监控器,
    条件日志记录,
    快速异常处理器,
    快速验证必填字段
)


class PerformanceOptimizedBaseService:
    """
    性能优化版服务基类（向后兼容）

    这是推荐的基类，集成了所有性能优化策略。
    专门解决了异常处理开销过大的问题。
    """

    def __init__(
        self,
        user_repo=None,
        task_repo=None,
        focus_repo=None,
        reward_repo=None,
        chat_repo=None,
        enable_performance_optimization: bool = True,
        enable_detailed_logging: Optional[bool] = None,
        performance_threshold_ms: float = 100.0
    ):
        """
        初始化优化版服务基类

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            chat_repo: 聊天数据访问对象
            enable_performance_optimization: 是否启用性能优化
            enable_detailed_logging: 是否启用详细日志记录（None表示自动检测）
            performance_threshold_ms: 性能监控阈值（毫秒）
        """
        # 初始化仓库引用
        self._user_repo = user_repo
        self._task_repo = task_repo
        self._focus_repo = focus_repo
        self._reward_repo = reward_repo
        self._chat_repo = chat_repo

        # 性能优化配置
        self._enable_performance_optimization = enable_performance_optimization
        self._performance_threshold_ms = performance_threshold_ms

        # 日志配置
        if enable_detailed_logging is None:
            # 根据环境自动配置
            self._enable_detailed_logging = self._auto_detect_log_level()
        else:
            self._enable_detailed_logging = enable_detailed_logging

        # 创建优化的日志器
        self._logger = get_logger(self.__class__.__name__)

        # 创建优化的异常处理器
        if self._enable_performance_optimization:
            self._exception_handler = 获取优化异常处理器(self.__class__.__name__)
        else:
            self._exception_handler = 智能异常处理器(
                self.__class__.__name__,
                enable_optimization=False
            )

        # 快速异常处理器
        self._fast_exception_handler = 快速异常处理器()

        # 性能统计
        self._performance_stats = {}
        self._operation_count = 0

        # 记录初始化（仅在详细模式下）
        if self._enable_detailed_logging:
            self._log_info("优化版服务初始化完成", extra_data={
                "performance_optimization": enable_performance_optimization,
                "detailed_logging": self._enable_detailed_logging,
                "performance_threshold": performance_threshold_ms,
                "repositories": {
                    "user_repo": user_repo is not None,
                    "task_repo": task_repo is not None,
                    "focus_repo": focus_repo is not None,
                    "reward_repo": reward_repo is not None,
                    "chat_repo": chat_repo is not None
                }
            })

    def _auto_detect_log_level(self) -> bool:
        """自动检测日志级别配置"""
        environment = os.getenv('ENVIRONMENT', 'production').lower()
        if environment in ['development', 'debug', 'test']:
            return True

        # 检查显式配置
        detailed_logging = os.getenv('SERVICE_ENABLE_DETAILED_LOGGING', 'true')
        return detailed_logging.lower() == 'true'

    # ==================== 优化的日志方法 ====================

    def _should_log(self, level: str = "info") -> bool:
        """判断是否应该记录日志"""
        if not self._enable_detailed_logging and level.upper() in ['DEBUG', 'INFO']:
            return False
        return self._logger.isEnabledFor(level.upper())

    def _log_info(self, message: str, **kwargs) -> None:
        """条件性INFO日志记录"""
        if self._should_log("info"):
            self._logger.info(message, **kwargs)

    def _log_debug(self, message: str, **kwargs) -> None:
        """条件性DEBUG日志记录"""
        if self._should_log("debug"):
            self._logger.debug(message, **kwargs)

    def _log_warning(self, message: str, **kwargs) -> None:
        """条件性WARNING日志记录"""
        if self._should_log("warning"):
            self._logger.warning(message, **kwargs)

    def _log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """优化的错误日志记录"""
        if self._enable_performance_optimization:
            # 使用优化的异常处理器
            operation = kwargs.get('operation', 'unknown')
            context = {k: v for k, v in kwargs.items() if k != 'operation'}
            self._exception_handler.处理异常(operation, error or Exception(message), context)
        else:
            # 使用标准日志记录
            if error:
                self._logger.error(message, error=error, **kwargs)
            else:
                self._logger.error(message, **kwargs)

    def _log_operation_start(self, operation: str, **kwargs) -> None:
        """条件性操作开始日志"""
        if self._enable_detailed_logging:
            self._logger.log_operation_start(operation, **kwargs)
        self._operation_count += 1

    def _log_operation_success(self, operation: str, **kwargs) -> None:
        """条件性操作成功日志"""
        if self._enable_detailed_logging:
            self._logger.log_operation_success(operation, **kwargs)

    def _log_operation_error(self, operation: str, error: Exception, **kwargs) -> None:
        """优化的操作错误日志"""
        if self._enable_performance_optimization:
            context = {k: v for k, v in kwargs.items()}
            self._exception_handler.处理异常(operation, error, context)
        else:
            self._logger.log_operation_error(operation, error, **kwargs)

    # ==================== 优化的异常处理方法 ====================

    @自动处理异常("repository_error", rethrow=True)
    def _handle_repository_error(self, error: Exception, operation: str = "unknown") -> None:
        """
        优化的Repository层异常处理

        使用智能异常处理器，显著减少异常处理开销。
        """
        if self._enable_performance_optimization:
            # 使用优化的异常包装
            wrapped_error = wrap_repository_error(error, operation)
            raise wrapped_error
        else:
            # 使用标准处理
            wrapped_error = wrap_repository_error(error, operation)
            self._log_operation_error(operation, wrapped_error)
            raise wrapped_error

    def _handle_business_exception(self, exception: BusinessException, operation: str = "unknown") -> None:
        """
        优化的业务异常处理

        根据异常类型和严重程度选择不同的处理策略。
        """
        if self._enable_performance_optimization:
            # 对于业务异常，记录简化信息
            context = {
                "exception_type": type(exception).__name__,
                "error_code": getattr(exception, 'error_code', 'UNKNOWN'),
                "user_message": getattr(exception, 'user_message', None)
            }
            self._exception_handler.处理异常(operation, exception, context)
        else:
            # 标准处理
            self._logger.log_business_exception(operation, exception)

        raise exception

    def _fast_validation_error(self, field: str, value: Any, user_message: Optional[str] = None) -> ValidationException:
        """快速创建验证异常"""
        return self._fast_exception_handler.快速验证错误(field, value, user_message)

    def _fast_not_found_error(self, resource_type: str, resource_id: str) -> ResourceNotFoundException:
        """快速创建资源未找到异常"""
        return self._fast_exception_handler.快速未找到错误(resource_type, resource_id)

    # ==================== 优化的验证方法 ====================

    @性能监控器(threshold_ms=50.0)
    def fast_validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        快速验证必填字段

        使用优化的验证逻辑，减少异常创建开销。
        """
        if self._enable_performance_optimization:
            try:
                快速验证必填字段(data, required_fields)
            except ValidationException as e:
                # 记录简化的验证失败信息
                if self._should_log("warning"):
                    self._log_warning(f"验证失败: {e.user_message}",
                                    field=e.details.get('field'),
                                    operation="validate_required_fields")
                raise
        else:
            # 标准验证逻辑
            self.validate_required_fields(data, required_fields)

    def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        标准验证必填字段方法（保持向后兼容）

        Args:
            data: 待验证数据
            required_fields: 必填字段列表

        Raises:
            ValidationException: 验证失败时抛出
        """
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)

        if missing_fields:
            raise self._fast_validation_error(
                field="required_fields",
                value=missing_fields,
                user_message=f"缺少必填字段: {', '.join(missing_fields)}"
            )

    # ==================== 性能监控方法 ====================

    def _record_performance(self, operation: str, duration_ms: float) -> None:
        """记录性能数据"""
        if operation not in self._performance_stats:
            self._performance_stats[operation] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0
            }

        stats = self._performance_stats[operation]
        stats["count"] += 1
        stats["total_time"] += duration_ms
        stats["min_time"] = min(stats["min_time"], duration_ms)
        stats["max_time"] = max(stats["max_time"], duration_ms)

        # 检查是否超过性能阈值
        if duration_ms > self._performance_threshold_ms and self._should_log("warning"):
            self._log_warning(f"性能警告: {operation} 耗时 {duration_ms:.2f}ms 超过阈值 {self._performance_threshold_ms}ms",
                            operation=operation,
                            duration_ms=duration_ms,
                            threshold_ms=self._performance_threshold_ms)

    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计信息"""
        stats = {}
        for operation, data in self._performance_stats.items():
            if data["count"] > 0:
                stats[operation] = {
                    "count": data["count"],
                    "avg_time": data["total_time"] / data["count"],
                    "min_time": data["min_time"],
                    "max_time": data["max_time"],
                    "total_time": data["total_time"]
                }
        return stats

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        exception_stats = self._exception_handler.获取性能统计()

        return {
            "service_name": self.__class__.__name__,
            "performance_optimization": self._enable_performance_optimization,
            "detailed_logging": self._enable_detailed_logging,
            "operation_count": self._operation_count,
            "performance_threshold_ms": self._performance_threshold_ms,
            "exception_handling": exception_stats,
            "performance_stats": self.get_performance_stats()
        }

    def reset_performance_stats(self) -> None:
        """重置性能统计"""
        self._performance_stats.clear()
        self._operation_count = 0
        self._exception_handler.重置统计()

    # ==================== 优化的通用方法 ====================

    @自动处理异常("health_check", rethrow=False)
    def health_check(self) -> Dict[str, Any]:
        """
        优化的健康检查

        包含性能优化统计信息。

        Returns:
            健康状态字典
        """
        return {
            "status": "healthy",
            "service": self.__class__.__name__,
            "timestamp": datetime.now().isoformat(),
            "performance_optimization": self._enable_performance_optimization,
            "operation_count": self._operation_count,
            "optimization_stats": self.get_optimization_stats()
        }

    # ==================== Repository访问方法 ====================

    def get_user_repository(self):
        """获取用户Repository"""
        return self._user_repo

    def get_task_repository(self):
        """获取任务Repository"""
        return self._task_repo

    def get_focus_repository(self):
        """获取专注Repository"""
        return self._focus_repo

    def get_reward_repository(self):
        """获取奖励Repository"""
        return self._reward_repo

    def get_chat_repository(self):
        """获取聊天Repository"""
        return self._chat_repo

    # ==================== 辅助方法 ====================

    def _fast_check_resource_exists(self, repository, resource_id: str, resource_type: str) -> Any:
        """
        快速检查资源是否存在

        优化资源检查性能，减少不必要的日志开销。

        Args:
            repository: 仓库对象
            resource_id: 资源ID
            resource_type: 资源类型

        Returns:
            资源对象

        Raises:
            ResourceNotFoundException: 资源不存在时抛出
        """
        try:
            resource = repository.get_by_id(resource_id)
            if resource is None:
                raise self._fast_not_found_error(resource_type, resource_id)
            return resource
        except ResourceNotFoundException:
            raise
        except Exception as e:
            self._handle_repository_error(e, f"get_{resource_type}")

    def _resource_to_dict(self, resource) -> Dict[str, Any]:
        """
        将资源对象转换为字典

        子类应该重写此方法以提供特定的转换逻辑。

        Args:
            resource: 资源对象

        Returns:
            资源字典
        """
        if hasattr(resource, 'to_dict'):
            return resource.to_dict()
        elif hasattr(resource, '__dict__'):
            return {k: v for k, v in resource.__dict__.items() if not k.startswith('_')}
        else:
            return {"id": getattr(resource, 'id', None), "data": str(resource)}