"""
Factory helpers to register and construct LDP applications by name.

Example:
    app = create_application(
        "heavy_hitters",
        client_config=HeavyHittersClientConfig(epsilon=1.0, categories=["a", "b"]),
        server_config=HeavyHittersServerConfig(top_k=5),
    )
    client = app.build_client()
    aggregator = app.build_aggregator()

Responsibilities:
    * maintain a registry of application identifiers
    * expose helpers to register, resolve, and instantiate applications
    * pre-register built-in applications for convenience
"""
# 说明：提供 LDP 应用的注册表与工厂入口。
# 职责：
# - 维护应用名称到实现类的注册映射
# - 支持按名称获取与实例化应用
# - 预注册内置应用便于配置驱动调用

from __future__ import annotations

from typing import Any, Dict, Type

from dplib.core.utils.param_validation import ParamValidationError
from .base import BaseLDPApplication
from .heavy_hitters import HeavyHittersApplication
from .frequency_estimation import FrequencyEstimationApplication
from .range_queries import RangeQueriesApplication
from .marginals import MarginalsApplication
from .key_value import KeyValueApplication
from .sequence_analysis import SequenceAnalysisApplication

_APPLICATION_REGISTRY: Dict[str, Type[BaseLDPApplication]] = {}


def register_application(name: str, cls: Type[BaseLDPApplication]) -> None:
    # 将应用类注册到全局注册表
    if not name:
        raise ParamValidationError("application name must be non-empty")
    key = str(name).lower()
    _APPLICATION_REGISTRY[key] = cls


def get_application_class(name: str) -> Type[BaseLDPApplication]:
    # 按名称获取应用类并在缺失时抛出 KeyError
    key = str(name).lower()
    if key not in _APPLICATION_REGISTRY:
        available = ", ".join(sorted(_APPLICATION_REGISTRY))
        raise ParamValidationError(f"application '{name}' not registered; available: {available}")
    return _APPLICATION_REGISTRY[key]


def create_application(name: str, **kwargs: Any) -> BaseLDPApplication:
    # 按名称实例化应用并透传构造参数
    cls = get_application_class(name)
    return cls(**kwargs)  # type: ignore[call-arg]


class ApplicationFactory:
    """Class-based facade around the application registry."""

    @staticmethod
    def register(name: str, cls: Type[BaseLDPApplication]) -> None:
        # 提供面向对象风格的应用注册入口
        register_application(name, cls)

    @staticmethod
    def get_class(name: str) -> Type[BaseLDPApplication]:
        # 提供面向对象风格的应用类获取入口
        return get_application_class(name)

    @staticmethod
    def create(name: str, **kwargs: Any) -> BaseLDPApplication:
        # 提供面向对象风格的应用实例化入口
        return create_application(name, **kwargs)


register_application("heavy_hitters", HeavyHittersApplication)
register_application("frequency_estimation", FrequencyEstimationApplication)
register_application("range_queries", RangeQueriesApplication)
register_application("marginals", MarginalsApplication)
register_application("key_value", KeyValueApplication)
register_application("sequence_analysis", SequenceAnalysisApplication)
