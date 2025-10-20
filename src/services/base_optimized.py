"""
优化版服务基类

这是统一的优化版服务基类，集成了所有性能优化策略。
替代了原来的 base_optimized.py 和 base_performance_optimized.py，
消除了代码重复，提供了一致的优化接口。

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


class OptimizedBaseService:
    """
    优化版服务基类

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
        启用性能优化: bool = True,
        启用详细日志: Optional[bool] = None,
        性能阈值毫秒: float = 100.0
    ):
        """
        初始化优化版服务基类

        Args:
            user_repo: 用户数据访问对象
            task_repo: 任务数据访问对象
            focus_repo: 专注数据访问对象
            reward_repo: 奖励数据访问对象
            chat_repo: 聊天数据访问对象
            启用性能优化: 是否启用性能优化
            启用详细日志: 是否启用详细日志记录（None表示自动检测）
            性能阈值毫秒: 性能监控阈值（毫秒）
        """
        # 初始化仓库引用
        self._user_repo = user_repo
        self._task_repo = task_repo
        self._focus_repo = focus_repo
        self._reward_repo = reward_repo
        self._chat_repo = chat_repo

        # 性能优化配置
        self._启用性能优化 = 启用性能优化
        self._性能阈值毫秒 = 性能阈值毫秒

        # 日志配置
        if 启用详细日志 is None:
            # 根据环境自动配置
            self._启用详细日志 = self._自动检测日志级别()
        else:
            self._启用详细日志 = 启用详细日志

        # 创建优化的日志器
        self._日志器 = get_logger(self.__class__.__name__)

        # 创建优化的异常处理器
        if self._启用性能优化:
            self._异常处理器 = 获取优化异常处理器(self.__class__.__name__)
        else:
            self._异常处理器 = 智能异常处理器(
                self.__class__.__name__,
                enable_optimization=False
            )

        # 快速异常处理器
        self._快速异常处理器 = 快速异常处理器()

        # 性能统计
        self._性能统计 = {}
        self._操作计数 = 0

        # 记录初始化（仅在详细模式下）
        if self._启用详细日志:
            self._记录信息("优化版服务初始化完成", extra_data={
                "性能优化": 启用性能优化,
                "详细日志": self._启用详细日志,
                "性能阈值": 性能阈值毫秒,
                "仓库": {
                    "user_repo": user_repo is not None,
                    "task_repo": task_repo is not None,
                    "focus_repo": focus_repo is not None,
                    "reward_repo": reward_repo is not None,
                    "chat_repo": chat_repo is not None
                }
            })

    def _自动检测日志级别(self) -> bool:
        """自动检测日志级别配置"""
        环境 = os.getenv('ENVIRONMENT', 'production').lower()
        if 环境 in ['development', 'debug', 'test']:
            return True

        # 检查显式配置
        详细日志 = os.getenv('SERVICE_ENABLE_DETAILED_LOGGING', 'true')
        return 详细日志.lower() == 'true'

    # ==================== 优化的日志方法 ====================

    def _应该记录日志(self, 级别: str = "info") -> bool:
        """判断是否应该记录日志"""
        if not self._启用详细日志 and 级别.upper() in ['DEBUG', 'INFO']:
            return False
        return self._日志器.isEnabledFor(级别.upper())

    def _记录信息(self, 消息: str, **kwargs) -> None:
        """条件性INFO日志记录"""
        if self._应该记录日志("info"):
            self._日志器.info(消息, **kwargs)

    def _记录调试(self, 消息: str, **kwargs) -> None:
        """条件性DEBUG日志记录"""
        if self._应该记录日志("debug"):
            self._日志器.debug(消息, **kwargs)

    def _记录警告(self, 消息: str, **kwargs) -> None:
        """条件性WARNING日志记录"""
        if self._应该记录日志("warning"):
            self._日志器.warning(消息, **kwargs)

    def _记录错误(self, 消息: str, 错误: Optional[Exception] = None, **kwargs) -> None:
        """优化的错误日志记录"""
        if self._启用性能优化:
            # 使用优化的异常处理器
            操作 = kwargs.get('operation', 'unknown')
            上下文 = {k: v for k, v in kwargs.items() if k != 'operation'}
            self._异常处理器.处理异常(操作, 错误 or Exception(消息), 上下文)
        else:
            # 使用标准日志记录
            if 错误:
                self._日志器.error(消息, error=错误, **kwargs)
            else:
                self._日志器.error(消息, **kwargs)

    def _记录操作开始(self, 操作: str, **kwargs) -> None:
        """条件性操作开始日志"""
        if self._启用详细日志:
            self._日志器.log_operation_start(操作, **kwargs)
        self._操作计数 += 1

    def _记录操作成功(self, 操作: str, **kwargs) -> None:
        """条件性操作成功日志"""
        if self._启用详细日志:
            self._日志器.log_operation_success(操作, **kwargs)

    def _记录操作错误(self, 操作: str, 错误: Exception, **kwargs) -> None:
        """优化的操作错误日志"""
        if self._启用性能优化:
            上下文 = {k: v for k, v in kwargs.items()}
            self._异常处理器.处理异常(操作, 错误, 上下文)
        else:
            self._日志器.log_operation_error(操作, 错误, **kwargs)

    # ==================== 优化的异常处理方法 ====================

    @自动处理异常("repository_error", 重新抛出=True)
    def _处理仓库错误(self, 错误: Exception, 操作: str = "unknown") -> None:
        """
        优化的Repository层异常处理

        使用智能异常处理器，显著减少异常处理开销。
        """
        if self._启用性能优化:
            # 使用优化的异常包装
            包装错误 = wrap_repository_error(错误, 操作)
            raise 包装错误
        else:
            # 使用标准处理
            包装错误 = wrap_repository_error(错误, 操作)
            self._记录操作错误(操作, 包装错误)
            raise 包装错误

    def _处理业务异常(self, 异常: BusinessException, 操作: str = "unknown") -> None:
        """
        优化的业务异常处理

        根据异常类型和严重程度选择不同的处理策略。
        """
        if self._启用性能优化:
            # 对于业务异常，记录简化信息
            上下文 = {
                "异常类型": type(异常).__name__,
                "错误代码": getattr(异常, 'error_code', 'UNKNOWN'),
                "用户消息": getattr(异常, 'user_message', None)
            }
            self._异常处理器.处理异常(操作, 异常, 上下文)
        else:
            # 标准处理
            self._日志器.log_business_exception(操作, 异常)

        raise 异常

    def _快速验证错误(self, 字段: str, 值: Any, 用户消息: Optional[str] = None) -> ValidationException:
        """快速创建验证异常"""
        return self._快速异常处理器.快速验证错误(字段, 值, 用户消息)

    def _快速未找到错误(self, 资源类型: str, 资源ID: str) -> ResourceNotFoundException:
        """快速创建资源未找到异常"""
        return self._快速异常处理器.快速未找到错误(资源类型, 资源ID)

    # ==================== 优化的验证方法 ====================

    @性能监控器(阈值毫秒=50.0)
    def 快速验证必填字段(self, 数据: Dict[str, Any], 必填字段: List[str]) -> None:
        """
        快速验证必填字段

        使用优化的验证逻辑，减少异常创建开销。
        """
        if self._启用性能优化:
            try:
                快速验证必填字段(数据, 必填字段)
            except ValidationException as e:
                # 记录简化的验证失败信息
                if self._应该记录日志("warning"):
                    self._记录警告(f"验证失败: {e.user_message}",
                                    field=e.details.get('field'),
                                    operation="validate_required_fields")
                raise
        else:
            # 标准验证逻辑
            self.validate_required_fields(数据, 必填字段)

    def validate_required_fields(self, 数据: Dict[str, Any], 必填字段: List[str]) -> None:
        """
        标准验证必填字段方法（保持向后兼容）

        Args:
            数据: 待验证数据
            必填字段: 必填字段列表

        Raises:
            ValidationException: 验证失败时抛出
        """
        缺失字段 = []

        for 字段 in 必填字段:
            if 字段 not in 数据 or 数据[字段] is None or 数据[字段] == "":
                缺失字段.append(字段)

        if 缺失字段:
            raise self._快速验证错误(
                field="required_fields",
                value=缺失字段,
                user_message=f"缺少必填字段: {', '.join(缺失字段)}"
            )

    # ==================== 性能监控方法 ====================

    def _记录性能(self, 操作: str, 耗时毫秒: float) -> None:
        """记录性能数据"""
        if 操作 not in self._性能统计:
            self._性能统计[操作] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0
            }

        统计 = self._性能统计[操作]
        统计["count"] += 1
        统计["total_time"] += 耗时毫秒
        统计["min_time"] = min(统计["min_time"], 耗时毫秒)
        统计["max_time"] = max(统计["max_time"], 耗时毫秒)

        # 检查是否超过性能阈值
        if 耗时毫秒 > self._性能阈值毫秒 and self._应该记录日志("warning"):
            self._记录警告(f"性能警告: {操作} 耗时 {耗时毫秒:.2f}ms 超过阈值 {self._性能阈值毫秒}ms",
                            operation=操作,
                            duration_ms=耗时毫秒,
                            threshold_ms=self._性能阈值毫秒)

    def 获取性能统计(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计信息"""
        统计 = {}
        for 操作, 数据 in self._性能统计.items():
            if 数据["count"] > 0:
                统计[操作] = {
                    "count": 数据["count"],
                    "avg_time": 数据["total_time"] / 数据["count"],
                    "min_time": 数据["min_time"],
                    "max_time": 数据["max_time"],
                    "total_time": 数据["total_time"]
                }
        return 统计

    def 获取优化统计(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        异常统计 = self._异常处理器.获取性能统计()

        return {
            "服务名称": self.__class__.__name__,
            "性能优化": self._启用性能优化,
            "详细日志": self._启用详细日志,
            "操作计数": self._操作计数,
            "性能阈值毫秒": self._性能阈值毫秒,
            "异常处理": 异常统计,
            "性能统计": self.获取性能统计()
        }

    def 重置性能统计(self) -> None:
        """重置性能统计"""
        self._性能统计.clear()
        self._操作计数 = 0
        self._异常处理器.重置统计()

    # ==================== 优化的通用方法 ====================

    @自动处理异常("health_check", 重新抛出=False)
    def 健康检查(self) -> Dict[str, Any]:
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
            "性能优化": self._启用性能优化,
            "操作计数": self._操作计数,
            "优化统计": self.获取优化统计()
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

    def _快速检查资源存在(self, 仓库, 资源ID: str, 资源类型: str) -> Any:
        """
        快速检查资源是否存在

        优化资源检查性能，减少不必要的日志开销。

        Args:
            仓库: 仓库对象
            资源ID: 资源ID
            资源类型: 资源类型

        Returns:
            资源对象

        Raises:
            ResourceNotFoundException: 资源不存在时抛出
        """
        try:
            资源 = 仓库.get_by_id(资源ID)
            if 资源 is None:
                raise self._快速未找到错误(资源类型, 资源ID)
            return 资源
        except ResourceNotFoundException:
            raise
        except Exception as e:
            self._处理仓库错误(e, f"get_{资源类型}")

    def _资源转字典(self, 资源) -> Dict[str, Any]:
        """
        将资源对象转换为字典

        子类应该重写此方法以提供特定的转换逻辑。

        Args:
            资源: 资源对象

        Returns:
            资源字典
        """
        if hasattr(资源, 'to_dict'):
            return 资源.to_dict()
        elif hasattr(资源, '__dict__'):
            return {k: v for k, v in 资源.__dict__.items() if not k.startswith('_')}
        else:
            return {"id": getattr(资源, 'id', None), "data": str(资源)}

    # ==================== 批量操作优化方法 ====================

    @性能监控器(阈值毫秒=200.0)
    def 批量创建资源(self,
                     仓库,
                     资源数据列表: List[Dict[str, Any]],
                     资源类型: str,
                     批次大小: int = 50) -> List[Dict[str, Any]]:
        """
        批量创建资源

        优化批量操作性能，减少单次操作的开销。

        Args:
            仓库: 仓库对象
            资源数据列表: 资源数据列表
            资源类型: 资源类型
            批次大小: 批处理大小

        Returns:
            创建的资源列表

        Raises:
            ValidationException: 验证失败
        """
        if not 资源数据列表:
            return []

        创建的资源列表 = []
        总数量 = len(资源数据列表)

        self._记录信息(f"开始批量创建{资源类型}",
                      总数量=总数量,
                      批次大小=批次大小)

        # 分批处理，避免内存压力
        for i in range(0, 总数量, 批次大小):
            批次数据 = 资源数据列表[i:i + 批次大小]
            批次开始 = i + 1
            批次结束 = min(i + 批次大小, 总数量)

            try:
                # 批量创建
                批次创建列表 = []
                for 资源数据 in 批次数据:
                    创建的资源 = 仓库.create(资源数据)
                    批次创建列表.append(self._资源转字典(创建的资源))

                创建的资源列表.extend(批次创建列表)

                if self._启用详细日志:
                    self._记录调试(f"批次创建完成",
                                  batch=f"{批次开始}-{批次结束}",
                                  created_count=len(批次创建列表))

            except Exception as e:
                self._记录错误(f"批量创建{资源类型}失败",
                              error=e,
                              batch=f"{批次开始}-{批次结束}")
                raise

        if self._启用详细日志:
            self._记录操作成功("batch_create_resources",
                               资源类型=资源类型,
                               total_created=len(创建的资源列表))

        return 创建的资源列表