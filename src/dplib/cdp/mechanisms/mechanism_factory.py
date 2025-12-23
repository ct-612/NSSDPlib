"""
Factory helpers to instantiate and calibrate mechanisms from registry identifiers.

Responsibilities
  - Normalise identifiers (string/enum) via the registry.
  - Construct mechanisms with supported init arguments.
  - Calibrate with provided sensitivity/delta and mechanism-specific kwargs.

Usage Context
  - Use when creating mechanisms by name or registry identifier.
  - Supports passing an existing mechanism instance for calibration.

Limitations
  - Relies on registry metadata for model support.
  - Filters kwargs to supported constructor/calibration signatures.
"""
# 说明：根据注册表标识符创建并校准差分隐私机制实例的工厂辅助函数。
# 职责：
# - 规范化字符串或枚举形式的机制标识符并解析为具体 MechanismType 与机制类
# - 根据机制构造函数与校准函数的签名筛选支持的参数并安全传递
# - 支持直接接收已有机制实例并在需要时进行隐私模型校验与一次性校准

from __future__ import annotations

import inspect
from typing import Any, Mapping, Optional

from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.privacy.privacy_model import MechanismType, PrivacyModel
from dplib.core.utils.param_validation import ParamValidationError

from .mechanism_registry import ensure_mechanism_supports_model, get_mechanism_class, normalize_mechanism


def _filter_kwargs(signature_obj: inspect.Signature, values: Mapping[str, Any]) -> dict[str, Any]:
    # 根据目标可调用对象的签名过滤出其能够接受的关键字参数
    """Keep only kwargs that the callable accepts."""
    return {k: v for k, v in values.items() if k in signature_obj.parameters}


def create_mechanism(
    mechanism: str | MechanismType | BaseMechanism,
    *,
    epsilon: float,
    delta: Optional[float] = None,
    sensitivity: Optional[float] = None,
    rng: Optional[Any] = None,
    name: Optional[str] = None,
    model: Optional[PrivacyModel] = None,
    calibrate: bool = True,
    **kwargs: Any,
) -> BaseMechanism:
    # 根据机制标识符或现有机制实例创建机制对象并在需要时进行一次性校准
    """
    Create and (optionally) calibrate a mechanism by identifier.

    Args:
        mechanism: MechanismType or string identifier, or an existing BaseMechanism.
        epsilon: Privacy budget ε passed to the constructor.
        delta: Optional δ (used when the target mechanism supports it).
        sensitivity: Optional global sensitivity used in calibration.
        rng: Optional RNG forwarded when supported.
        name: Optional human readable name.
        model: Optional PrivacyModel; validated against registry support.
        calibrate: Whether to call calibrate() before returning.
        **kwargs: Extra parameters forwarded to constructor/calibration when accepted.
    """
    if isinstance(mechanism, BaseMechanism):
        # 处理调用方已构造好机制实例的场景，仅做模型兼容性校验与按需校准
        mech_instance = mechanism
        if model is not None:
            # 若指定隐私模型则确认该机制在注册表中声明支持该模型
            ensure_mechanism_supports_model(mechanism.mechanism_id, model)
        if calibrate and not mech_instance.calibrated:
            # 基于机制私有的 _calibrate_parameters 签名动态构造可用的校准参数
            cal_sig = inspect.signature(mech_instance._calibrate_parameters)  # type: ignore[attr-defined]
            cal_kwargs = {}
            if "sensitivity" in cal_sig.parameters and sensitivity is not None:
                # 当校准需要敏感度且调用方显式提供时进行透传
                cal_kwargs["sensitivity"] = sensitivity
            if "delta" in cal_sig.parameters and delta is not None:
                # 当校准需要 delta 且调用方显式提供时进行透传
                cal_kwargs["delta"] = delta
            cal_kwargs.update(_filter_kwargs(cal_sig, kwargs))
            mech_instance.calibrate(**cal_kwargs)
        return mech_instance

    # 对字符串或枚举形式的机制标识符进行归一化并获取对应机制类
    mech_type = normalize_mechanism(mechanism)
    mech_cls = get_mechanism_class(mech_type)
    if model is not None:
        # 在实例化前校验机制与目标隐私模型的支持关系
        ensure_mechanism_supports_model(mech_type, model)

    init_sig = inspect.signature(mech_cls.__init__)
    # 依据构造函数签名筛选出机制支持的初始化参数集合
    init_kwargs = {
        "epsilon": epsilon,
        **_filter_kwargs(init_sig, {"delta": delta, "sensitivity": sensitivity, "rng": rng, "name": name, **kwargs}),
    }
    mech_instance: BaseMechanism = mech_cls(**{k: v for k, v in init_kwargs.items() if v is not None})

    if calibrate:
        # 若要求自动校准则根据机制定义的校准接口签名构造参数并触发一次校准
        cal_sig = inspect.signature(mech_instance._calibrate_parameters)  # type: ignore[attr-defined]
        cal_kwargs = {}
        if "sensitivity" in cal_sig.parameters and sensitivity is not None:
            cal_kwargs["sensitivity"] = sensitivity
        if "delta" in cal_sig.parameters and delta is not None:
            cal_kwargs["delta"] = delta
        cal_kwargs.update(_filter_kwargs(cal_sig, kwargs))
        mech_instance.calibrate(**cal_kwargs)

    return mech_instance
