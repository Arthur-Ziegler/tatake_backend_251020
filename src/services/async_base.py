"""
异步基础服务类

提供统一的异步服务层抽象，实现业务逻辑处理的通用功能。
支持依赖注入、日志记录、异常处理等基础功能。

功能特性：
1. 异步依赖注入和Repository管理
2. 异步日志记录和性能监控
3. 异步异常处理和错误报告
4. 异步事务管理
5. 可扩展设计，支持具体服务类扩展

设计原则：
1. 单一责任：只负责业务逻辑处理
2. 开闭原则：对扩展开放，对修改封闭
3. 依赖倒置：依赖抽象而非具体实现
4. 接口隔离：提供简洁明确的接口
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.services.logging_config import get_logger


class AsyncBaseService:
    """
    异步基础服务类

    提供异步服务层的通用功能，所有具体服务类都应该继承自这个基类。

    Attributes:
        _logger: 异步服务日志器
        _repositories: 异步Repository字典
    """

    def __init__(self, **kwargs):
        """
        初始化异步基础服务

        Args:
            **kwargs: 各种Repository实例
        """
        # 获取服务名称
        self.service_name = self.__class__.__name__.replace('Service', '').lower()

        # 初始化日志器
        self._logger = get_logger(self.service_name)

        # 存储Repository实例
        self._repositories = {}
        for key, value in kwargs.items():
            if key.endswith('_repo') and value is not None:
                self._repositories[key] = value
                setattr(self, key, value)

    # ==================== 日志记录方法 ====================

    def _log_info(self, message: str, **kwargs):
        """记录信息日志"""
        self._logger.info(message, **kwargs)

    def _log_warning(self, message: str, **kwargs):
        """记录警告日志"""
        self._logger.warning(message, **kwargs)

    def _log_error(self, message: str, **kwargs):
        """记录错误日志"""
        self._logger.error(message, **kwargs)

    def _log_debug(self, message: str, **kwargs):
        """记录调试日志"""
        self._logger.debug(message, **kwargs)

    def _log_operation_start(self, operation: str, **kwargs):
        """记录操作开始"""
        self._logger.log_operation_start(operation, **kwargs)

    def _log_operation_success(self, operation: str, duration_ms: Optional[float] = None, **kwargs):
        """记录操作成功"""
        self._logger.log_operation_success(operation, duration_ms, **kwargs)

    def _log_operation_error(self, operation: str, error: Exception, **kwargs):
        """记录操作错误"""
        self._logger.log_operation_error(operation, error, **kwargs)

    def _log_business_exception(self, operation: str, exception: Exception, **kwargs):
        """记录业务异常"""
        self._logger.log_business_exception(operation, exception, **kwargs)

    def _log_validation_error(self, field: str, value: Any, reason: str, **kwargs):
        """记录验证错误"""
        self._logger.log_validation_error(field, value, reason, **kwargs)

    def _log_performance(self, operation: str, duration_ms: float, **kwargs):
        """记录性能日志"""
        self._logger.log_performance(operation, duration_ms, **kwargs)

    # ==================== 验证方法 ====================

    def _validate_required(self, value: Any, field_name: str):
        """验证必填字段"""
        if value is None or (isinstance(value, str) and not value.strip()):
            from .exceptions import ValidationException
            raise ValidationException(f"{field_name}不能为空")

    def _validate_email(self, email: str):
        """验证邮箱格式"""
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            from .exceptions import ValidationException
            raise ValidationException("邮箱格式不正确")

    def _validate_phone(self, phone: str):
        """验证手机号格式"""
        import re
        if not re.match(r'^1[3-9]\d{9}$', phone):
            from .exceptions import ValidationException
            raise ValidationException("手机号格式不正确")

    def _validate_length(self, value: str, field_name: str, min_length: int = 0, max_length: int = None):
        """验证字符串长度"""
        if len(value) < min_length:
            from .exceptions import ValidationException
            raise ValidationException(f"{field_name}长度不能少于{min_length}个字符")

        if max_length and len(value) > max_length:
            from .exceptions import ValidationException
            raise ValidationException(f"{field_name}长度不能超过{max_length}个字符")

    # ==================== Repository访问方法 ====================

    def get_repository(self, repo_name: str):
        """
        获取Repository实例

        Args:
            repo_name: Repository名称

        Returns:
            Repository实例或None
        """
        full_name = f"{repo_name}_repo"
        return self._repositories.get(full_name)

    def has_repository(self, repo_name: str) -> bool:
        """
        检查是否存在指定的Repository

        Args:
            repo_name: Repository名称

        Returns:
            bool: 存在返回True，否则返回False
        """
        full_name = f"{repo_name}_repo"
        return full_name in self._repositories

    # ==================== 工具方法 ====================

    def _generate_uuid(self) -> str:
        """生成UUID字符串"""
        import uuid
        return str(uuid.uuid4())

    def _current_time(self) -> datetime:
        """获取当前UTC时间"""
        return datetime.now(timezone.utc)

    def _format_timestamp(self, dt: datetime) -> str:
        """格式化时间戳为ISO字符串"""
        return dt.isoformat()

    def _dict_to_snake_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """将字典的键转换为蛇形命名"""
        import re
        result = {}
        for key, value in data.items():
            # 将驼峰命名转换为蛇形命名
            snake_key = re.sub('([A-Z])', r'_\1', key).lower()
            result[snake_key] = value
        return result

    def _dict_to_camel_case(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """将字典的键转换为驼峰命名"""
        def to_camel_case(snake_str):
            components = snake_str.split('_')
            return components[0] + ''.join(x.capitalize() for x in components[1:])

        result = {}
        for key, value in data.items():
            camel_key = to_camel_case(key)
            result[camel_key] = value
        return result

    def __repr__(self) -> str:
        """
        返回服务的字符串表示

        Returns:
            str: 服务的描述信息
        """
        return f"{self.__class__.__name__}(service={self.service_name})"


# 导出AsyncBaseService类
__all__ = ["AsyncBaseService"]