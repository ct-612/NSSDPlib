"""
Unit tests for mechanism registry and factory.
"""
# 说明：差分隐私机制注册表与工厂方法的单元测试。
# 覆盖：
# - 机制枚举与注册表中预期条目的存在性
# - 字符串与枚举到 MechanismType 的归一化行为与错误分支
# - 机制类查找、隐私模型支持校验以及工厂创建与校准逻辑

import pytest

from dplib.cdp.mechanisms import (
    MECHANISM_REGISTRY,
    GaussianMechanism,
    LaplaceMechanism,
    create_mechanism,
    ensure_mechanism_supports_model,
    get_mechanism_class,
    normalize_mechanism,
)
from dplib.core.privacy.privacy_model import MechanismType, PrivacyModel
from dplib.core.utils.param_validation import ParamValidationError


def test_registry_contains_expected_mechanisms() -> None:
    # 验证机制注册表中包含预期的 Laplace/Gaussian 枚举映射关系
    assert MechanismType.LAPLACE in MECHANISM_REGISTRY
    assert MechanismType.GAUSSIAN in MECHANISM_REGISTRY
    assert MECHANISM_REGISTRY[MechanismType.LAPLACE] is LaplaceMechanism


def test_normalize_mechanism_accepts_string_and_enum() -> None:
    # 验证机制名称归一化支持字符串与枚举输入并对未知名称抛出校验错误
    assert normalize_mechanism("laplace") == MechanismType.LAPLACE
    assert normalize_mechanism(MechanismType.GAUSSIAN) == MechanismType.GAUSSIAN
    with pytest.raises(ParamValidationError):
        normalize_mechanism("unknown")


def test_get_mechanism_class_lookup() -> None:
    # 验证通过名称查找机制类的功能以及缺失机制时的错误行为
    assert get_mechanism_class("gaussian") is GaussianMechanism
    with pytest.raises(ParamValidationError):
        get_mechanism_class("missing")


def test_ensure_supports_model_rejects_unsupported() -> None:
    # 验证机制与隐私模型不兼容时会触发参数校验异常
    with pytest.raises(ParamValidationError):
        ensure_mechanism_supports_model(MechanismType.LAPLACE, PrivacyModel.LDP)


def test_factory_creates_and_calibrates_laplace() -> None:
    # 验证工厂可以创建并自动校准 Laplace 机制且缩放参数符合 ε 与敏感度关系
    mech = create_mechanism("laplace", epsilon=1.5, sensitivity=2.0)
    assert isinstance(mech, LaplaceMechanism)
    assert mech.calibrated is True
    assert mech.scale == pytest.approx(2.0 / 1.5)


def test_factory_respects_delta_for_gaussian() -> None:
    # 验证工厂创建 Gaussian 机制时会保留传入的 δ 并完成校准
    mech = create_mechanism(MechanismType.GAUSSIAN, epsilon=1.0, delta=1e-4, sensitivity=1.0)
    assert isinstance(mech, GaussianMechanism)
    assert mech.calibrated is True
    assert mech.delta == pytest.approx(1e-4)
