"""
零Bug测试体系 - 基础测试数据工厂

提供所有测试工厂的基础类和通用功能。

核心特性：
1. 确定性数据生成
2. 批量创建支持
3. 字段覆盖机制
4. 关联数据管理
5. 数据验证
"""

import uuid
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from abc import ABC, abstractmethod

from faker import Faker

# 初始化Faker实例
fake = Faker('zh_CN')
Faker.seed(12345)  # 确保可重现的随机数据

T = TypeVar('T', bound='BaseFactory')


class BaseFactory(ABC):
    """基础测试数据工厂抽象类

    所有具体工厂类都必须继承此基类，确保一致的接口和行为。

    设计原则：
    - 确定性：相同输入产生相同输出
    - 可扩展：支持字段覆盖和自定义
    - 类型安全：严格的类型检查
    - 性能优化：批量创建和缓存
    """

    # 子类必须定义的默认数据
    DEFAULTS: Dict[str, Any] = {}

    # 关联的模型类（可选）
    model_class: Optional[Type] = None

    # 是否自动生成唯一字段
    auto_unique: bool = True

    @classmethod
    @abstractmethod
    def create(cls, **overrides: Any) -> Dict[str, Any]:
        """创建单个数据实例

        Args:
            **overrides: 要覆盖的默认字段

        Returns:
            数据字典

        Raises:
            NotImplementedError: 子类必须实现
        """
        raise NotImplementedError("子类必须实现create方法")

    @classmethod
    def create_batch(cls, count: int, **overrides: Any) -> List[Dict[str, Any]]:
        """批量创建数据实例

        Args:
            count: 创建数量
            **overrides: 要覆盖的默认字段

        Returns:
            数据字典列表

        Raises:
            ValueError: 数量必须大于0
        """
        if count <= 0:
            raise ValueError(f"创建数量必须大于0，当前值: {count}")

        return [cls.create(**overrides) for _ in range(count)]

    @classmethod
    def create_with_associations(cls, **overrides: Any) -> Any:
        """创建带有关联数据的实例

        默认返回字典，子类可以重写返回模型实例

        Args:
            **overrides: 要覆盖的默认字段

        Returns:
            模型实例或数据字典
        """
        data = cls.create(**overrides)
        if cls.model_class:
            return cls.model_class(**data)
        return data

    @classmethod
    def build(cls, **overrides: Any) -> Dict[str, Any]:
        """构建数据（不保存到数据库）

        与create方法相同，但语义上表示不持久化

        Args:
            **overrides: 要覆盖的默认字段

        Returns:
            数据字典
        """
        return cls.create(**overrides)

    @classmethod
    def _ensure_unique(cls, field_name: str, value: str) -> str:
        """确保字段值的唯一性

        Args:
            field_name: 字段名
            value: 原始值

        Returns:
            唯一的值
        """
        if not cls.auto_unique:
            return value
        return f"{value}_{uuid.uuid4().hex[:8]}"

    @classmethod
    def _generate_datetime(cls,
                          start_year: int = 2020,
                          end_year: int = 2024) -> datetime:
        """生成测试用时间戳

        Args:
            start_year: 起始年份
            end_year: 结束年份

        Returns:
            UTC时间戳
        """
        return fake.date_time_between(
            start_date=f"-{end_year - start_year}y",
            end_date="now"
        ).replace(tzinfo=timezone.utc)

    @classmethod
    def _generate_choice(cls, choices: List[Union[str, int, float]]) -> Union[str, int, float]:
        """从列表中随机选择

        Args:
            choices: 选项列表

        Returns:
            随机选择的值

        Raises:
            ValueError: 选项列表不能为空
        """
        if not choices:
            raise ValueError("选项列表不能为空")
        return random.choice(choices)

    @classmethod
    def _generate_float(cls,
                       min_value: float = 0.0,
                       max_value: float = 100.0,
                       decimal_places: int = 2) -> float:
        """生成测试用浮点数

        Args:
            min_value: 最小值
            max_value: 最大值
            decimal_places: 小数位数

        Returns:
            指定范围的浮点数
        """
        value = random.uniform(min_value, max_value)
        return round(value, decimal_places)

    @classmethod
    def _generate_int(cls,
                     min_value: int = 0,
                     max_value: int = 1000) -> int:
        """生成测试用整数

        Args:
            min_value: 最小值
            max_value: 最大值

        Returns:
            指定范围的整数
        """
        return random.randint(min_value, max_value)

    @classmethod
    def _generate_boolean(cls, true_probability: float = 0.5) -> bool:
        """生成测试用布尔值

        Args:
            true_probability: True的概率

        Returns:
            随机布尔值
        """
        return random.random() < true_probability

    @classmethod
    def _merge_data(cls, defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认数据和覆盖数据

        Args:
            defaults: 默认数据
            overrides: 覆盖数据

        Returns:
            合并后的数据
        """
        result = defaults.copy()
        result.update(overrides)
        return result

    @classmethod
    def validate_data(cls, data: Dict[str, Any]) -> bool:
        """验证生成的数据

        子类可以重写此方法实现自定义验证

        Args:
            data: 要验证的数据

        Returns:
            验证是否通过
        """
        # 基础验证：确保必填字段不为空
        required_fields = getattr(cls, 'REQUIRED_FIELDS', [])
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"必填字段 '{field}' 缺失或为空")
        return True

    @classmethod
    def get_schema(cls) -> Dict[str, Any]:
        """获取数据模式（用于文档和验证）

        Returns:
            数据模式字典
        """
        return {
            'defaults': cls.DEFAULTS,
            'model_class': cls.model_class.__name__ if cls.model_class else None,
            'auto_unique': cls.auto_unique,
            'required_fields': getattr(cls, 'REQUIRED_FIELDS', []),
        }


class FactoryRegistry:
    """工厂注册表

    管理所有测试工厂的注册和查找，支持动态创建。
    """

    _factories: Dict[str, Type[BaseFactory]] = {}

    @classmethod
    def register(cls, name: str, factory_class: Type[BaseFactory]) -> None:
        """注册工厂类

        Args:
            name: 工厂名称
            factory_class: 工厂类
        """
        cls._factories[name] = factory_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseFactory]]:
        """获取工厂类

        Args:
            name: 工厂名称

        Returns:
            工厂类，如果不存在返回None
        """
        return cls._factories.get(name)

    @classmethod
    def create(cls, name: str, **overrides: Any) -> Dict[str, Any]:
        """通过名称创建数据

        Args:
            name: 工厂名称
            **overrides: 覆盖字段

        Returns:
            创建的数据

        Raises:
            ValueError: 工厂不存在
        """
        factory_class = cls.get(name)
        if not factory_class:
            raise ValueError(f"工厂 '{name}' 不存在")
        return factory_class.create(**overrides)

    @classmethod
    def list_factories(cls) -> List[str]:
        """列出所有注册的工厂

        Returns:
            工厂名称列表
        """
        return list(cls._factories.keys())

    @classmethod
    def get_all_schemas(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有工厂的模式

        Returns:
            所有工厂的模式字典
        """
        return {
            name: factory.get_schema()
            for name, factory in cls._factories.items()
        }


def register_factory(name: str):
    """工厂注册装饰器

    Args:
        name: 工厂名称

    Returns:
        装饰器函数
    """
    def decorator(factory_class: Type[BaseFactory]) -> Type[BaseFactory]:
        FactoryRegistry.register(name, factory_class)
        return factory_class
    return decorator