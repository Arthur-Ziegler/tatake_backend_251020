"""
服务层统一日志配置

提供统一、清晰、可调节的日志系统，支持：
1. 不同日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
2. 可配置的日志详细程度
3. 统一的日志格式
4. 结构化日志输出
5. 性能友好的日志记录
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json
from functools import wraps
import time
import traceback
from pathlib import Path


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServiceLoggerConfig:
    """服务日志配置类"""

    def __init__(self):
        # 从环境变量读取配置
        self.log_level = os.getenv("SERVICE_LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("SERVICE_LOG_FORMAT", "structured")
        self.enable_console = os.getenv("SERVICE_LOG_CONSOLE", "true").lower() == "true"
        self.enable_file = os.getenv("SERVICE_LOG_FILE", "true").lower() == "true"
        self.log_file_path = os.getenv("SERVICE_LOG_FILE_PATH", "logs/services.log")
        self.enable_performance = os.getenv("SERVICE_LOG_PERFORMANCE", "false").lower() == "true"
        self.max_log_size = int(os.getenv("SERVICE_LOG_MAX_SIZE", "10")) * 1024 * 1024  # 10MB
        self.backup_count = int(os.getenv("SERVICE_LOG_BACKUP_COUNT", "5"))

        # 创建日志目录
        if self.enable_file:
            log_dir = Path(self.log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record):
        # 创建基础日志结构
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加服务特定信息
        if hasattr(record, 'service_name'):
            log_entry["service"] = record.service_name
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, 'extra_data'):
            log_entry["extra_data"] = record.extra_data

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info else None
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class SimpleFormatter(logging.Formatter):
    """简单日志格式化器"""

    def __init__(self):
        super().__init__()
        self.format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)-20s | "
            "%(funcName)-15s:%(lineno)-4d | %(message)s"
        )

    def format(self, record):
        # 添加服务信息到简单格式
        if hasattr(record, 'service_name'):
            record.name = f"{record.name}[{record.service_name}]"

        return super().format(record)


class ServiceLogger:
    """服务日志器基类"""

    def __init__(self, service_name: str, config: Optional[ServiceLoggerConfig] = None):
        self.service_name = service_name
        self.config = config or ServiceLoggerConfig()
        self.logger = self._create_logger()

    def _create_logger(self) -> logging.Logger:
        """创建日志器"""
        logger = logging.getLogger(f"services.{self.service_name}")
        logger.setLevel(getattr(logging, self.config.log_level))

        # 清除现有处理器
        logger.handlers.clear()

        # 创建格式化器
        if self.config.log_format == "structured":
            formatter = StructuredFormatter()
        else:
            formatter = SimpleFormatter()

        # 控制台处理器
        if self.config.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, self.config.log_level))
            logger.addHandler(console_handler)

        # 文件处理器
        if self.config.enable_file:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                self.config.log_file_path,
                maxBytes=self.config.max_log_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, self.config.log_level))
            logger.addHandler(file_handler)

        return logger

    def _log(self, level: LogLevel, message: str, **kwargs):
        """内部日志方法"""
        extra = {
            'service_name': self.service_name,
            **kwargs
        }

        log_method = getattr(self.logger, level.value.lower())
        log_method(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """DEBUG级别日志"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """INFO级别日志"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """WARNING级别日志"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """ERROR级别日志"""
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """CRITICAL级别日志"""
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def log_operation_start(self, operation: str, **kwargs):
        """记录操作开始"""
        self.info(f"开始执行: {operation}", operation=operation, **kwargs)

    def log_operation_success(self, operation: str, duration_ms: Optional[float] = None, **kwargs):
        """记录操作成功"""
        message = f"操作成功: {operation}"
        log_kwargs = {"operation": operation, **kwargs}

        if duration_ms is not None:
            message += f" (耗时: {duration_ms:.2f}ms)"
            log_kwargs["duration_ms"] = duration_ms

        self.info(message, **log_kwargs)

    def log_operation_error(self, operation: str, error: Exception, **kwargs):
        """记录操作错误"""
        self.error(
            f"操作失败: {operation} - {str(error)}",
            operation=operation,
            extra_data={"error_type": type(error).__name__, "error_message": str(error)},
            **kwargs
        )

    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """记录性能日志"""
        if self.config.enable_performance:
            self.info(
                f"性能指标: {operation} 耗时 {duration_ms:.2f}ms",
                operation=operation,
                duration_ms=duration_ms,
                extra_data={"performance_type": "timing"},
                **kwargs
            )

    def log_validation_error(self, field: str, value: Any, reason: str, **kwargs):
        """记录验证错误"""
        self.warning(
            f"验证失败 - 字段: {field}, 值: {value}, 原因: {reason}",
            operation="validation",
            extra_data={
                "validation_field": field,
                "validation_value": str(value),
                "validation_reason": reason
            },
            **kwargs
        )

    def log_business_exception(self, operation: str, exception: Exception, **kwargs):
        """记录业务异常"""
        self.error(
            f"业务异常: {operation} - {exception.error_code if hasattr(exception, 'error_code') else 'UNKNOWN'}: {str(exception)}",
            operation=operation,
            extra_data={
                "exception_code": getattr(exception, 'error_code', None),
                "user_message": getattr(exception, 'user_message', None),
                "exception_type": type(exception).__name__
            },
            exc_info=False,  # 不记录完整堆栈，避免日志过多
            **kwargs
        )


def performance_logger(operation_name: str = None):
    """性能日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, '_logger') or not self._logger.config.enable_performance:
                return func(self, *args, **kwargs)

            start_time = time.time()
            op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"

            try:
                result = func(self, *args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                self._logger.log_performance(op_name, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self._logger.log_operation_error(op_name, e, duration_ms=duration_ms)
                raise

        return wrapper
    return decorator


def operation_logger(operation_name: str = None, log_args: bool = False, log_result: bool = False):
    """操作日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, '_logger'):
                return func(self, *args, **kwargs)

            op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"

            # 记录操作开始
            log_data = {}
            if log_args:
                # 记录参数（去除敏感信息）
                safe_kwargs = {k: v for k, v in kwargs.items()
                             if not any(sensitive in str(k).lower()
                                       for sensitive in ['password', 'token', 'secret', 'key'])}
                log_data.update(safe_kwargs)

            self._logger.log_operation_start(op_name, extra_data=log_data if log_data else None)

            try:
                result = func(self, *args, **kwargs)

                # 记录操作成功
                success_data = {}
                if log_result and hasattr(result, 'to_dict'):
                    # 对于有to_dict方法的对象，记录结果摘要
                    result_dict = result.to_dict()
                    success_data = {k: v for k, v in result_dict.items()
                                  if not any(sensitive in str(k).lower()
                                            for sensitive in ['password', 'token', 'secret', 'key'])}

                self._logger.log_operation_success(op_name, extra_data=success_data if success_data else None)
                return result

            except Exception as e:
                self._logger.log_operation_error(op_name, e)
                raise

        return wrapper
    return decorator


# 全局日志器实例
_global_config = ServiceLoggerConfig()
_global_logger = ServiceLogger("global", _global_config)


def get_logger(service_name: str) -> ServiceLogger:
    """获取服务日志器实例"""
    return ServiceLogger(service_name)


def configure_global_logging(config: Optional[ServiceLoggerConfig] = None):
    """配置全局日志设置"""
    global _global_config, _global_logger
    _global_config = config or ServiceLoggerConfig()
    _global_logger = ServiceLogger("global", _global_config)