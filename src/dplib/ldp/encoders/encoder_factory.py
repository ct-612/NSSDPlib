"""Factory and registry helpers for LDP encoders."""
# 说明：提供编码器的注册与按名称实例化能力，可根据配置构建编码 pipeline。
# 职责：
# - 维护从字符串名称到编码器类的注册表用于集中管理
# - 提供按名称创建单个编码器实例的工厂函数与类封装入口
# - 支持根据配置字典批量构建顺序编码器 pipeline 以适配不同 LDP 场景

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Type

from dplib.core.utils.param_validation import ParamValidationError
from .base import BaseEncoder
from .bloom_filter import BloomFilterEncoder
from .categorical import CategoricalEncoder
from .hashing import HashEncoder
from .numerical import NumericalBucketsEncoder
from .sketch import SketchEncoder
from .unary import BinaryEncoder, UnaryEncoder

_ENCODER_REGISTRY: Dict[str, Type[BaseEncoder]] = {}


def register_encoder(name: str, cls: Type[BaseEncoder]) -> None:
    """Register an encoder class under the given name."""
    # 将编码器类以给定名称注册到全局字典中用于后续按名查找
    if not name:
        raise ParamValidationError("encoder name must be non-empty")
    _ENCODER_REGISTRY[str(name)] = cls


def get_encoder_class(name: str) -> Type[BaseEncoder]:
    """Retrieve encoder class by name; raises KeyError if missing."""
    # 根据名称从注册表中获取编码器类不存在时抛出 KeyError
    key = str(name)
    if key not in _ENCODER_REGISTRY:
        raise ParamValidationError(f"encoder '{name}' not registered")
    return _ENCODER_REGISTRY[key]


def create_encoder(name: str, **kwargs: Any) -> BaseEncoder:
    """Instantiate an encoder by registry name with provided kwargs."""
    # 通过名称查表并使用传入参数实例化对应编码器
    cls = get_encoder_class(name)
    return cls(**kwargs)  # type: ignore[call-arg]


def build_encoder_pipeline(config: Mapping[str, Any]) -> List[BaseEncoder]:
    """
    Build a list of encoder instances from a config mapping.

    Expected shape:
        {"encoders": [{"type": "categorical", "categories": [...]}, {"type": "unary", "length": 3}]}
    """
    # 从配置字典中解析 encoders 列表依次构建编码器实例 pipeline
    encoders_cfg = config.get("encoders")
    if encoders_cfg is None:
        raise ParamValidationError("config must contain 'encoders' list")

    pipeline: List[BaseEncoder] = []
    for item in encoders_cfg:
        # 每个配置项必须包含 type 字段，其余字段作为实例化参数透传
        if "type" not in item:
            raise ParamValidationError("each encoder config must include 'type'")
        params = {k: v for k, v in item.items() if k != "type"}
        pipeline.append(create_encoder(item["type"], **params))
    return pipeline


class EncoderFactory:
    """Convenience wrapper mirroring the function-based factory helpers."""
    # 提供面向对象封装的编码器工厂接口，便于在应用层以类方法形式调用

    @staticmethod
    def register(name: str, cls: Type[BaseEncoder]) -> None:
        # 通过工厂类方法注册新的编码器类型
        register_encoder(name, cls)

    @staticmethod
    def get_class(name: str) -> Type[BaseEncoder]:
        # 按名称获取已注册的编码器类
        return get_encoder_class(name)

    @staticmethod
    def create(name: str, **kwargs: Any) -> BaseEncoder:
        # 按名称和参数创建编码器实例
        return create_encoder(name, **kwargs)

    @staticmethod
    def build_pipeline(config: Mapping[str, Any]) -> List[BaseEncoder]:
        # 从配置构建编码器 pipeline
        return build_encoder_pipeline(config)


# Pre-register common encoders
register_encoder("categorical", CategoricalEncoder)
register_encoder("numerical_buckets", NumericalBucketsEncoder)
register_encoder("unary", UnaryEncoder)
register_encoder("binary", BinaryEncoder)
register_encoder("hash", HashEncoder)
register_encoder("bloom_filter", BloomFilterEncoder)
register_encoder("sketch", SketchEncoder)
