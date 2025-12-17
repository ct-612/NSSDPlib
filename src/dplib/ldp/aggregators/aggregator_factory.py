"""Factory and registry utilities for LDP aggregators."""
# 说明：提供聚合器的注册与按名称创建能力，便于通过配置选择聚合策略。
# 职责：
# - 维护从字符串标识到聚合器实现类的注册表，支持运行时扩展
# - 提供按名称查找与实例化聚合器的统一工厂入口
# - 通过 AggregatorFactory 封装类方便在配置驱动或依赖注入场景中使用

from __future__ import annotations

from typing import Any, Dict, Type

from dplib.core.utils.param_validation import ParamValidationError
from .base import BaseAggregator
from .consistency import ConsistencyPostProcessor
from .frequency import FrequencyAggregator
from .mean import MeanAggregator
from .quantile import QuantileAggregator
from .user_level import UserLevelAggregator
from .variance import VarianceAggregator

_AGGREGATOR_REGISTRY: Dict[str, Type[BaseAggregator]] = {}


def register_aggregator(name: str, cls: Type[BaseAggregator]) -> None:
    """Register an aggregator class under a string identifier."""
    # 将聚合器类以给定名称写入全局注册表，供后续查找和构造使用
    if not name:
        raise ParamValidationError("aggregator name must be non-empty")
    _AGGREGATOR_REGISTRY[str(name)] = cls


def get_aggregator_class(name: str) -> Type[BaseAggregator]:
    """Retrieve aggregator class by name."""
    # 从注册表中按名称查找聚合器类型，不存在时抛出异常
    key = str(name)
    if key not in _AGGREGATOR_REGISTRY:
        raise ParamValidationError(f"aggregator '{name}' not registered")
    return _AGGREGATOR_REGISTRY[key]


def create_aggregator(name: str, **kwargs: Any) -> BaseAggregator:
    """Instantiate an aggregator from the registry."""
    # 根据名称获取聚合器类并以 kwargs 初始化实例，便于配置化创建
    cls = get_aggregator_class(name)
    return cls(**kwargs)  # type: ignore[call-arg]


class AggregatorFactory:
    """Convenience wrapper mirroring the function-based factory helpers."""

    @staticmethod
    def register(name: str, cls: Type[BaseAggregator]) -> None:
        # 提供面向对象形式的注册入口，复用 register_aggregator 的逻辑
        register_aggregator(name, cls)

    @staticmethod
    def get_class(name: str) -> Type[BaseAggregator]:
        # 包装 get_aggregator_class，便于在工厂上下文中获取聚合器类型
        return get_aggregator_class(name)

    @staticmethod
    def create(name: str, **kwargs: Any) -> BaseAggregator:
        # 工厂方法封装 create_aggregator，按名称和参数创建聚合器实例
        return create_aggregator(name, **kwargs)


# Pre-register common aggregators
register_aggregator("frequency", FrequencyAggregator)
register_aggregator("mean", MeanAggregator)
register_aggregator("variance", VarianceAggregator)
register_aggregator("quantile", QuantileAggregator)
register_aggregator("user_level", UserLevelAggregator)
register_aggregator("consistency", ConsistencyPostProcessor)
