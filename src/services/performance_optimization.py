"""
服务层性能优化工具

提供统一的性能优化功能，包括：
1. 智能异常处理
2. 性能监控装饰器
3. 条件日志记录
4. 快速验证工具
5. 异常信息缓存

合并了原有的 optimized_exception_handler.py 和 performance_optimization.py 的功能
"""

import os
import sys
import traceback
import time
import hashlib
import functools
from typing import Any, Dict, Optional, Union, Callable
from functools import lru_cache

from .logging_config import get_logger


class 智能异常处理器:
    """
    智能异常处理器

    专门针对异常处理开销过大的问题进行优化。
    通过智能日志记录、异常信息缓存和分级处理策略，
    显著降低异常处理的性能开销。
    """

    def __init__(self, 服务名称: str, 启用优化: bool = True):
        """
        初始化智能异常处理器

        Args:
            服务名称: 服务名称
            启用优化: 是否启用优化策略
        """
        self.服务名称 = 服务名称
        self.启用优化 = 启用优化
        self.日志器 = get_logger(f"{服务名称}.异常处理器")

        # 配置选项
        self._详细异常记录 = self._获取详细异常设置()
        self._调试模式 = self._获取调试模式()
        self._缓存异常信息 = self._获取缓存设置()

        # 异常信息缓存
        self._异常缓存 = {} if self._缓存异常信息 else None
        self._缓存最大大小 = 100

        # 性能统计
        self._已处理异常数 = 0
        self._缓存命中数 = 0

    def _获取详细异常设置(self) -> bool:
        """获取是否记录详细异常信息的设置"""
        return os.getenv('SERVICE_LOG_DETAILED_EXCEPTIONS', 'true').lower() == 'true'

    def _获取调试模式(self) -> bool:
        """获取是否为调试模式"""
        return os.getenv('ENVIRONMENT', 'production').lower() in ['development', 'debug']

    def _获取缓存设置(self) -> bool:
        """获取是否启用异常缓存"""
        return os.getenv('SERVICE_CACHE_EXCEPTION_INFO', 'true').lower() == 'true'

    def 处理异常(self,
                操作: str,
                异常: Exception,
                上下文: Optional[Dict[str, Any]] = None,
                日志级别: str = "ERROR") -> None:
        """
        优化的异常处理方法

        根据环境和配置选择最优的异常处理策略。

        Args:
            操作: 操作名称
            异常: 异常对象
            上下文: 额外上下文信息
            日志级别: 日志级别
        """
        self._已处理异常数 += 1

        if self.启用优化:
            self._优化异常处理(操作, 异常, 上下文, 日志级别)
        else:
            self._标准异常处理(操作, 异常, 上下文, 日志级别)

    def _优化异常处理(self,
                      操作: str,
                      异常: Exception,
                      上下文: Optional[Dict[str, Any]],
                      日志级别: str) -> None:
        """
        优化的异常处理实现

        使用多种优化策略减少异常处理开销。
        """
        # 快速路径：对于常见异常类型使用简化处理
        if self._是常见异常(异常):
            self._处理常见异常(操作, 异常, 上下文)
            return

        # 缓存路径：使用缓存的异常信息
        if self._缓存异常信息:
            缓存信息 = self._获取缓存异常信息(异常)
            if 缓存信息:
                self._记录缓存异常(操作, 缓存信息, 上下文)
                self._缓存命中数 += 1
                return

        # 生成异常信息（开销最大的部分）
        异常信息 = self._生成最小异常信息(异常)

        # 缓存异常信息
        if self._缓存异常信息 and self._异常缓存 is not None:
            self._缓存异常信息(异常, 异常信息)

        # 记录日志
        self._记录异常信息(操作, 异常信息, 上下文, 日志级别)

    def _标准异常处理(self,
                       操作: str,
                       异常: Exception,
                       上下文: Optional[Dict[str, Any]],
                       日志级别: str) -> None:
        """
        标准的异常处理实现（保持向后兼容）
        """
        # 生成完整的异常信息
        异常信息 = self._生成完整异常信息(异常)

        # 记录完整的日志
        self.日志器.error(
            f"Exception in {操作}",
            error=异常,
            operation=操作,
            exception_type=type(异常).__name__,
            exception_message=str(异常),
            **(上下文 or {})
        )

    def _是常见异常(self, 异常: Exception) -> bool:
        """判断是否为常见异常类型"""
        常见类型 = (
            ValueError, TypeError, KeyError, AttributeError,
            IndexError, FileNotFoundError, PermissionError
        )
        return isinstance(异常, 常见类型)

    def _处理常见异常(self,
                      操作: str,
                      异常: Exception,
                      上下文: Optional[Dict[str, Any]]) -> None:
        """
        处理常见异常类型的快速路径

        避免昂贵的堆栈追踪生成，只记录关键信息。
        """
        异常信息 = {
            "type": type(异常).__name__,
            "message": str(异常)[:200],  # 限制消息长度
            "operation": 操作
        }

        # 添加常见异常的特定信息
        if isinstance(异常, (KeyError, IndexError)):
            异常信息["missing_key"] = str(异常).strip("'\"")
        elif isinstance(异常, FileNotFoundError):
            异常信息["missing_file"] = str(异常)

        # 快速日志记录（不包含完整异常对象）
        self.日志器.error(
            f"Common exception in {操作}: {异常信息['type']}: {异常信息['message']}",
            **异常信息,
            **(上下文 or {})
        )

    def _获取缓存异常信息(self, 异常: Exception) -> Optional[Dict[str, Any]]:
        """从缓存获取异常信息"""
        if not self._异常缓存:
            return None

        缓存键 = self._生成异常缓存键(异常)
        return self._异常缓存.get(缓存键)

    def _缓存异常信息(self, 异常: Exception, 信息: Dict[str, Any]) -> None:
        """缓存异常信息"""
        if not self._异常缓存:
            return

        # 防止缓存过大
        if len(self._异常缓存) >= self._缓存最大大小:
            # 简单的LRU：删除最旧的条目
            最旧键 = next(iter(self._异常缓存))
            del self._异常缓存[最旧键]

        缓存键 = self._生成异常缓存键(异常)
        self._异常缓存[缓存键] = 信息

    def _生成异常缓存键(self, 异常: Exception) -> str:
        """生成异常信息的缓存键"""
        # 使用异常类型、消息和堆栈的哈希作为缓存键
        键数据 = f"{type(异常).__name__}:{str(异常)}:{id(异常)}"
        return hashlib.md5(键数据.encode()).hexdigest()

    def _生成最小异常信息(self, 异常: Exception) -> Dict[str, Any]:
        """
        生成最小化的异常信息

        只包含必要的信息，避免昂贵的操作。
        """
        信息 = {
            "type": type(异常).__name__,
            "message": str(异常)[:500],  # 限制消息长度
            "timestamp": time.time()
        }

        # 只在调试模式或详细异常模式下添加堆栈信息
        if self._调试模式 or self._详细异常记录:
            信息["traceback"] = self._获取紧凑堆栈信息(异常)

        return 信息

    def _生成完整异常信息(self, 异常: Exception) -> Dict[str, Any]:
        """
        生成完整的异常信息

        包含所有可能的调试信息。
        """
        信息 = {
            "type": type(异常).__name__,
            "message": str(异常),
            "module": getattr(异常, '__module__', 'unknown'),
            "timestamp": time.time(),
            "traceback": traceback.format_exc()
        }

        # 添加异常属性
        if hasattr(异常, '__dict__'):
            for 键, 值 in 异常.__dict__.items():
                if not 键.startswith('_'):
                    try:
                        信息[键] = str(值)[:200]
                    except Exception:
                        信息[键] = "<unable to serialize>"

        return 信息

    def _获取紧凑堆栈信息(self, 异常: Exception) -> str:
        """
        获取紧凑的堆栈追踪信息

        只包含关键帧，减少字符串长度。
        """
        try:
            堆栈信息 = traceback.format_exc()
            # 只保留前5行和后3行
            行列表 = 堆栈信息.split('\n')
            if len(行列表) > 8:
                紧凑行列表 = 行列表[:5] + ['...'] + 行列表[-3:]
                return '\n'.join(紧凑行列表)
            return 堆栈信息
        except Exception:
            return "<traceback unavailable>"

    def _记录缓存异常(self,
                      操作: str,
                      缓存信息: Dict[str, Any],
                      上下文: Optional[Dict[str, Any]]) -> None:
        """记录缓存的异常信息"""
        self.日志器.error(
            f"Cached exception in {操作}",
            operation=操作,
            cached=True,
            **缓存信息,
            **(上下文 or {})
        )

    def _记录异常信息(self,
                       操作: str,
                       异常信息: Dict[str, Any],
                       上下文: Optional[Dict[str, Any]],
                       日志级别: str) -> None:
        """记录异常信息"""
        # 根据日志级别选择记录方法
        日志消息 = f"Exception in {操作}: {异常信息['type']}: {异常信息['message']}"

        if 日志级别.upper() == "CRITICAL":
            self.日志器.critical(日志消息, operation=操作, **异常信息, **(上下文 or {}))
        elif 日志级别.upper() == "WARNING":
            self.日志器.warning(日志消息, operation=操作, **异常信息, **(上下文 or {}))
        else:
            self.日志器.error(日志消息, operation=操作, **异常信息, **(上下文 or {}))

    def 获取性能统计(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        缓存命中率 = (self._缓存命中数 / max(self._已处理异常数, 1)) * 100

        return {
            "handled_exceptions": self._已处理异常数,
            "cache_hits": self._缓存命中数,
            "cache_hit_rate": f"{缓存命中率:.1f}%",
            "cache_size": len(self._异常缓存) if self._异常缓存 else 0,
            "optimization_enabled": self.启用优化,
            "detailed_exceptions": self._详细异常记录,
            "debug_mode": self._调试模式
        }

    def 清空缓存(self) -> None:
        """清空异常缓存"""
        if self._异常缓存:
            self._异常缓存.clear()

    def 重置统计(self) -> None:
        """重置性能统计"""
        self._已处理异常数 = 0
        self._缓存命中数 = 0


# 全局异常处理器实例缓存
_异常处理器缓存: Dict[str, 智能异常处理器] = {}


def 获取优化异常处理器(服务名称: str) -> 智能异常处理器:
    """
    获取服务的优化异常处理器

    使用单例模式，每个服务只创建一个处理器实例。

    Args:
        服务名称: 服务名称

    Returns:
        优化异常处理器实例
    """
    if 服务名称 not in _异常处理器缓存:
        _异常处理器缓存[服务名称] = 智能异常处理器(服务名称)
    return _异常处理器缓存[服务名称]


# 装饰器：自动处理异常
def 自动处理异常(操作名称: Optional[str] = None,
                   日志级别: str = "ERROR",
                   重新抛出: bool = True):
    """
    异常处理装饰器

    自动处理函数中的异常，使用优化的异常处理器。

    Args:
        操作名称: 操作名称，如果为None则使用函数名
        日志级别: 日志级别
        重新抛出: 是否重新抛出异常
    """
    def 装饰器(函数):
        @functools.wraps(函数)
        def 包装器(self, *args, **kwargs):
            操作名 = 操作名称 or 函数.__name__

            # 获取异常处理器
            处理器 = getattr(self, '_异常处理器', None)
            if not 处理器:
                处理器 = 获取优化异常处理器(self.__class__.__name__)
                self._异常处理器 = 处理器

            try:
                return 函数(self, *args, **kwargs)
            except Exception as e:
                # 记录异常
                上下文 = {
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())[:5],  # 限制记录的参数数量
                    "method": 函数.__name__
                }

                处理器.处理异常(操作名, e, 上下文, 日志级别)

                if 重新抛出:
                    raise
                else:
                    return None

        return 包装器
    return 装饰器


def 性能监控器(阈值毫秒: float = 100.0):
    """
    性能监控装饰器

    只在超过阈值时记录日志，减少日志开销。

    Args:
        阈值毫秒: 性能阈值（毫秒）
    """
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*args, **kwargs):
            开始时间 = time.perf_counter()

            try:
                结果 = 函数(*args, **kwargs)
                return 结果
            finally:
                # 只在执行时间超过阈值时记录
                耗时毫秒 = (time.perf_counter() - 开始时间) * 1000
                if 耗时毫秒 > 阈值毫秒:
                    # 获取logger并记录警告
                    if hasattr(args[0], '_日志器'):
                        args[0]._日志器.warning(
                            f"性能警告: {函数.__name__} 执行时间 {耗时毫秒:.2f}ms 超过阈值 {阈值毫秒}ms"
                        )

        return 包装器
    return 装饰器


def 条件日志记录(条件函数: Callable[[], bool]):
    """
    条件日志装饰器

    根据条件函数决定是否记录日志，减少不必要的日志开销。

    Args:
        条件函数: 返回布尔值的条件函数
    """
    def 装饰器(函数: Callable) -> Callable:
        @functools.wraps(函数)
        def 包装器(*args, **kwargs):
            应该记录 = 条件函数()

            if 应该记录 and hasattr(args[0], '_记录操作开始'):
                args[0]._记录操作开始(函数.__name__)

            try:
                结果 = 函数(*args, **kwargs)

                if 应该记录 and hasattr(args[0], '_记录操作成功'):
                    args[0]._记录操作成功(函数.__name__)

                return 结果
            except Exception as e:
                if 应该记录 and hasattr(args[0], '_记录操作错误'):
                    args[0]._记录操作错误(函数.__name__, e)
                raise

        return 包装器
    return 装饰器


class 快速异常处理器:
    """
    快速异常处理器

    优化异常处理性能，减少不必要的开销。
    使用预编译的错误消息和简化的异常创建流程。
    """

    # 预定义常用错误消息，避免重复字符串格式化
    常见错误 = {
        "resource_not_found": "资源未找到",
        "validation_failed": "数据验证失败",
        "duplicate_resource": "资源已存在",
        "insufficient_balance": "余额不足",
        "auth_failed": "认证失败",
        "permission_denied": "权限不足"
    }

    @classmethod
    def 快速验证错误(cls, 字段: str, 值: Any, 用户消息: Optional[str] = None) -> 'ValidationException':
        """
        快速创建验证异常

        Args:
            字段: 字段名
            值: 字段值
            用户消息: 用户消息

        Returns:
            验证异常实例
        """
        from .异常处理 import ValidationException

        if 用户消息 is None:
            用户消息 = f"{字段}字段值无效"

        # 使用简化的异常创建，减少开销
        异常 = ValidationException(
            field=字段,
            value=值,
            message=f"Validation failed for field '{字段}'"
        )
        异常.user_message = 用户消息
        return 异常

    @classmethod
    def 快速未找到错误(cls, 资源类型: str, 资源ID: str) -> 'ResourceNotFoundException':
        """
        快速创建资源未找到异常

        Args:
            资源类型: 资源类型
            资源ID: 资源ID

        Returns:
            资源未找到异常实例
        """
        from .异常处理 import ResourceNotFoundException

        异常 = ResourceNotFoundException(
            resource_type=资源类型,
            resource_id=资源ID,
            message=f"{资源类型} with id '{资源ID}' not found"
        )
        异常.user_message = f"{资源类型}不存在"
        return 异常


def 快速验证必填字段(数据: Dict[str, Any], 必填字段: list) -> None:
    """
    快速验证必填字段

    优化性能的字段验证，减少异常创建开销。

    Args:
        数据: 待验证数据
        必填字段: 必填字段列表

    Raises:
        ValidationException: 验证失败时抛出
    """
    缺失字段 = []

    # 批量检查缺失字段，避免多次异常创建
    for 字段 in 必填字段:
        if 字段 not in 数据 or 数据[字段] is None or 数据[字段] == "":
            缺失字段.append(字段)

    if 缺失字段:
        处理器 = 快速异常处理器()
        raise 处理器.快速验证错误(
            field="required_fields",
            value=缺失字段,
            user_message=f"缺少必填字段: {', '.join(缺失字段)}"
        )


# ==================== 英文别名（向后兼容） ====================

# 类名别名
SmartExceptionHandler = 智能异常处理器
FastExceptionHandler = 快速异常处理器
PerformanceMonitor = 性能监控器
ConditionalLogging = 条件日志记录

# 函数别名
get_optimized_exception_handler = 获取优化异常处理器
handle_exception_automatically = 自动处理异常
fast_validate_required_fields = 快速验证必填字段
fast_validate_required = 快速验证必填字段
conditional_log = 条件日志记录
performance_monitor = 性能监控器

# 装饰器别名
auto_handle_exception = 自动处理异常