"""
Repository模块

提供数据访问层的抽象和实现，包括：
- BaseRepository：基础Repository类，提供CRUD操作
- UserRepository：用户Repository，封装用户相关业务查询

设计原则：
1. 统一的数据访问接口
2. 业务逻辑封装
3. 异常处理机制
4. 类型安全
"""

# 导入基础Repository类
from src.repositories.base import (
    BaseRepository,
    RepositoryError,
    RepositoryValidationError,
    RepositoryNotFoundError,
    RepositoryIntegrityError
)

# 导入具体Repository类
from src.repositories.user import UserRepository
from src.repositories.task import TaskRepository
from src.repositories.focus import FocusRepository
from src.repositories.reward import RewardRepository

# 导出所有Repository类
__all__ = [
    # 基础Repository
    "BaseRepository",
    "RepositoryError",
    "RepositoryValidationError",
    "RepositoryNotFoundError",
    "RepositoryIntegrityError",

    # 具体Repository
    "UserRepository",
    "TaskRepository",
    "FocusRepository",
    "RewardRepository"
]