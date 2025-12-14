"""
Lightweight registry mapping LDP mechanism identifiers to concrete classes.

Mirrors the CDP registry style: normalise identifiers, expose lookup helpers,
and validate privacy model compatibility.
"""
# 说明：为本地差分隐私（LDP）机制提供轻量级注册表与查找工具。
# 职责：
# - 维护 MechanismType 到具体 LDP 机制类的映射
# - 提供从字符串或枚举到 MechanismType 的规范化转换接口
# - 校验机制是否支持给定隐私模型并在不兼容时抛出统一异常
# - 为文档与调试导出当前已注册机制及类名的快照

from __future__ import annotations

from typing import Dict, Type

from dplib.core.privacy.privacy_model import (
    MechanismType,
    PrivacyModel,
    ensure_supported_model,
)
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.continuous import (
    DuchiMechanism,
    LocalGaussianMechanism,
    LocalLaplaceMechanism,
    PiecewiseMechanism,
)
from dplib.ldp.mechanisms.discrete import (
    GRRMechanism,
    OLHMechanism,
    OUEMechanism,
    RAPPORMechanism,
    UnaryRandomizer,
)

# 集中维护 MechanismType 到具体机制实现类的映射表
MECHANISM_REGISTRY: Dict[MechanismType, Type] = {
    MechanismType.GRR: GRRMechanism,
    MechanismType.OUE: OUEMechanism,
    MechanismType.OLH: OLHMechanism,
    MechanismType.RAPPOR: RAPPORMechanism,
    MechanismType.UNARY_RANDOMIZER: UnaryRandomizer,
    MechanismType.LOCAL_LAPLACE: LocalLaplaceMechanism,
    MechanismType.LOCAL_GAUSSIAN: LocalGaussianMechanism,
    MechanismType.DUCHI: DuchiMechanism,
    MechanismType.PIECEWISE: PiecewiseMechanism,
}


def normalize_mechanism(mechanism: str | MechanismType) -> MechanismType:
    """Coerce string or enum to MechanismType, raising on unknown identifiers."""
    # 将字符串或枚举形式的机制标识规范化为 MechanismType 枚举并在未知标识时抛出参数校验错误
    if isinstance(mechanism, MechanismType):
        return mechanism
    try:
        return MechanismType.from_str(str(mechanism))
    except Exception as exc:  # pragma: no cover - defensive
        raise ParamValidationError(f"unknown mechanism '{mechanism}'") from exc


def get_mechanism_class(mechanism: str | MechanismType) -> Type:
    """Return the concrete class registered for the mechanism identifier."""
    # 根据规范化后的机制标识从注册表中查找并返回对应的 LDP 机制类
    mech_type = normalize_mechanism(mechanism)
    if mech_type not in MECHANISM_REGISTRY:
        raise ParamValidationError(f"mechanism '{mech_type.value}' not registered")
    return MECHANISM_REGISTRY[mech_type]


def ensure_mechanism_supports_model(
    mechanism: str | MechanismType,
    model: PrivacyModel,
) -> None:
    """Raise if the mechanism does not support the requested privacy model."""
    # 校验指定机制是否支持给定隐私模型模型不兼容时通过 ensure_supported_model 抛出错误
    mech_type = normalize_mechanism(mechanism)
    ensure_supported_model(mech_type, model)


def registered_mechanisms_snapshot() -> Dict[str, str]:
    """Snapshot of registered mechanisms for tooling or docs."""
    # 为工具链或文档用途导出当前注册表中机制标识到类名的只读快照
    return {mech.value: cls.__name__ for mech, cls in MECHANISM_REGISTRY.items()}
