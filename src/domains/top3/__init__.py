"""Top3领域包 - 微服务代理模式

TaKeKe项目的Top3功能已迁移到微服务架构。
本模块提供代理层，将Top3管理请求转发到Task微服务(localhost:20252)。

功能特性：
1. 微服务代理：HTTP调用转发到Task微服务
2. 响应格式转换：统一微服务和本地API格式
3. 积分扣除：设置Top3前扣除300积分
4. 事务支持：积分扣除失败时自动回滚

架构设计：
- 代理模式：保持API路径完全不变
- HTTP客户端：与Task微服务通信
- 格式转换：微服务格式 ↔ 本地格式
- 错误映射：HTTP状态码 → 业务错误码

API端点（代理）：
- POST /tasks/special/top3 - 积分扣除+代理设置
- GET /tasks/special/top3/{date} - 代理获取Top3

作者：TaKeKe团队
版本：2.0.0（微服务代理）
"""

from .schemas import (
    SetTop3Request,
    Top3Response,
    GetTop3Response
)
from .exceptions import Top3Exception

# 为了向后兼容，定义一个空的TaskTop3类
class TaskTop3:
    """占位TaskTop3类，保持向后兼容性"""
    pass

__all__ = [
    # 占位类（保持兼容性）
    "TaskTop3",

    # Schemas
    "SetTop3Request",
    "Top3Response",
    "GetTop3Response",

    # Exceptions
    "Top3Exception"
]
