"""
Light-weight registry mapping MechanismType to concrete implementations.

Responsibilities
  - Provide a single source of truth for mechanism lookups.
  - Expose helpers to normalise identifiers and validate model support.

Usage Context
  - Use when resolving mechanism identifiers to concrete classes.
  - Intended to back factory helpers and model validation.

Limitations
  - Only includes mechanisms registered in MECHANISM_REGISTRY.
  - Assumes MechanismType values align with available implementations.
"""
# 说明：维护差分隐私 MechanismType 与具体机制实现类映射关系的轻量级注册表模块。
# 职责：
# - 作为机制查找与工厂创建的单一事实来源
# - 提供机制标识符的归一化与未注册机制的错误报告
# - 校验机制对不同 PrivacyModel 的支持情况并暴露注册表快照查询

from __future__ import annotations

from typing import Dict, Type

from dplib.core.privacy.privacy_model import (
    MechanismType,
    PrivacyModel,
    ensure_supported_model,
)
from dplib.core.utils.param_validation import ParamValidationError

from .exponential import ExponentialMechanism
from .gaussian import GaussianMechanism
from .geometric import GeometricMechanism
from .laplace import LaplaceMechanism
from .staircase import StaircaseMechanism
from .vector import VectorMechanism

# 集中维护 MechanismType 到具体机制实现类的映射表
MECHANISM_REGISTRY: Dict[MechanismType, Type] = {
    MechanismType.LAPLACE: LaplaceMechanism,
    MechanismType.GAUSSIAN: GaussianMechanism,
    MechanismType.EXPONENTIAL: ExponentialMechanism,
    MechanismType.GEOMETRIC: GeometricMechanism,
    MechanismType.STAIRCASE: StaircaseMechanism,
    MechanismType.VECTOR: VectorMechanism,
}


def normalize_mechanism(mechanism: str | MechanismType) -> MechanismType:
    # 将字符串或枚举形式的机制标识符规一化为 MechanismType 并对未知值抛出校验错误
    """Coerce string or enum to MechanismType, raising on unknown identifiers."""
    if isinstance(mechanism, MechanismType):
        return mechanism
    try:
        return MechanismType.from_str(str(mechanism))
    except Exception as exc:  # pragma: no cover - defensive
        raise ParamValidationError(f"unknown mechanism '{mechanism}'") from exc


def get_mechanism_class(mechanism: str | MechanismType) -> Type:
    # 根据归一化后的机制标识符从注册表中查找并返回对应的实现类
    """Return the concrete class registered for the mechanism identifier."""
    mech_type = normalize_mechanism(mechanism)
    if mech_type not in MECHANISM_REGISTRY:
        raise ParamValidationError(f"mechanism '{mech_type.value}' not registered")
    return MECHANISM_REGISTRY[mech_type]


def ensure_mechanism_supports_model(
    mechanism: str | MechanismType,
    model: PrivacyModel,
) -> None:
    # 校验给定机制在注册表中是否声明支持指定的隐私模型
    """Raise if the mechanism does not support the requested privacy model."""
    mech_type = normalize_mechanism(mechanism)
    ensure_supported_model(mech_type, model)


def registered_mechanisms_snapshot() -> Dict[str, str]:
    # 返回已注册机制标识符与类名的快照供工具或文档生成使用
    """Snapshot of registered mechanisms for tooling or docs."""
    return {mech.value: cls.__name__ for mech, cls in MECHANISM_REGISTRY.items()}
