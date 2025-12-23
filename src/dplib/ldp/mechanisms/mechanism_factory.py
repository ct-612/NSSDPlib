"""
Factory helpers to instantiate LDP mechanisms from registry identifiers.

Responsibilities
  - Normalize identifiers and resolve mechanism classes via the registry.
  - Filter constructor and calibration arguments by callable signatures.
  - Optionally calibrate mechanisms after instantiation.

Usage Context
  - Use to build mechanisms from configuration without direct class references.
  - Intended for application-level plumbing that selects mechanisms by name.

Limitations
  - Only parameters accepted by constructors or calibration hooks are passed.
  - Does not override mechanism-specific validation logic.
"""
# 说明：根据注册表标识构造本地差分隐私机制实例的工厂工具。
# 职责：
# - 统一规范机制标识字符串或枚举并通过注册表解析到具体类
# - 过滤并组装构造函数与校准函数支持的参数集合
# - 在创建实例前后校验与目标隐私模型的兼容性并按需调用 calibrate

from __future__ import annotations

import inspect
from typing import Any, Mapping, Optional

from dplib.core.privacy.privacy_model import MechanismType, PrivacyModel
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.base import BaseLDPMechanism

from .mechanism_registry import (
    ensure_mechanism_supports_model,
    get_mechanism_class,
    normalize_mechanism,
)


def _filter_kwargs(signature_obj: inspect.Signature, values: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only kwargs that the callable accepts."""
    # 根据目标可调用对象的签名筛选出其实际支持的关键字参数子集
    return {k: v for k, v in values.items() if k in signature_obj.parameters}


def create_mechanism(
    mechanism: str | MechanismType | BaseLDPMechanism,
    *,
    epsilon: Optional[float] = None,
    delta: Optional[float] = None,
    rng: Optional[Any] = None,
    name: Optional[str] = None,
    model: PrivacyModel = PrivacyModel.LDP,
    calibrate: bool = True,
    **kwargs: Any,
) -> BaseLDPMechanism:
    """
    Create and (optionally) calibrate an LDP mechanism by identifier.

    Args:
        mechanism: MechanismType or string identifier, or an existing BaseLDPMechanism.
        epsilon: Privacy budget Îµ passed to the constructor (if required).
        delta: Optional Î´ (rarely used in LDP, passed when supported).
        rng: Optional RNG forwarded when supported.
        name: Optional human readable name.
        model: Target PrivacyModel for compatibility validation (default LDP).
        calibrate: Whether to call calibrate() before returning.
        **kwargs: Extra parameters forwarded to constructor/calibration when accepted.
    """
    # 通过标识符或现有机制实例创建 LDP 机制对象并在需要时调用 calibrate 完成参数校准
    # 同时确保机制与指定隐私模型兼容并只传递构造器和校准函数实际接受的关键字参数
    if isinstance(mechanism, BaseLDPMechanism):
        mech_instance = mechanism
        if model is not None:
            ensure_mechanism_supports_model(mechanism.mechanism_id, model)
        if calibrate and not mech_instance.calibrated:
            cal_sig = inspect.signature(mech_instance._calibrate_parameters)  # type: ignore[attr-defined]
            cal_kwargs = _filter_kwargs(cal_sig, kwargs)
            if "delta" in cal_sig.parameters and delta is not None:
                cal_kwargs.setdefault("delta", delta)
            mech_instance.calibrate(**cal_kwargs)
        return mech_instance

    mech_type = normalize_mechanism(mechanism)
    mech_cls = get_mechanism_class(mech_type)
    if model is not None:
        ensure_mechanism_supports_model(mech_type, model)

    init_sig = inspect.signature(mech_cls.__init__)
    init_kwargs = _filter_kwargs(
        init_sig,
        {"epsilon": epsilon, "delta": delta, "rng": rng, "name": name, **kwargs},
    )
    if "epsilon" in init_sig.parameters and "epsilon" not in init_kwargs:
        raise ParamValidationError("epsilon is required to construct this mechanism")
    mech_instance: BaseLDPMechanism = mech_cls(**init_kwargs)  # type: ignore[arg-type]

    if calibrate:
        cal_sig = inspect.signature(mech_instance._calibrate_parameters)  # type: ignore[attr-defined]
        cal_kwargs = _filter_kwargs(cal_sig, kwargs)
        if "delta" in cal_sig.parameters and delta is not None:
            cal_kwargs.setdefault("delta", delta)
        mech_instance.calibrate(**cal_kwargs)

    return mech_instance


def create_default_grr(epsilon: float, categories: Any) -> BaseLDPMechanism:
    """Convenience helper to construct a GRR mechanism with categories."""
    # 便捷构造使用给定类别列表的 GRR 机制并复用通用工厂逻辑
    return create_mechanism("grr", epsilon=epsilon, categories=categories)


def create_default_oue(epsilon: float) -> BaseLDPMechanism:
    """Convenience helper to construct a default OUE mechanism."""
    # 便捷构造使用默认参数配置的 OUE 机制并复用通用工厂逻辑
    return create_mechanism("oue", epsilon=epsilon)
