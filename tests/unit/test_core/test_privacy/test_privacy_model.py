"""
Unit tests for the privacy model registry and conversions.
"""
# 说明：隐私模型枚举、机制注册表与模型间转换工具的单元测试。
# 覆盖：
# - PrivacyModel.from_str / MechanismType.from_str 字符串解析与非法输入错误分支
# - 机制默认模型映射、支持矩阵以及 ensure_supported_model 的一致性校验
# - zCDP ↔ CDP、zCDP → RDP、RDP → CDP 的转换公式与参数边界检查
# - GDP → zCDP / CDP、LDP → CDP 的转换逻辑与非法参数报错
# - ModelSpec 的 validate / to_tuple / as_cdp / to_parameters 行为与必填参数约束
# - registry_snapshot 返回的隐私模型/机制标识集合是否包含预期条目

import math

import pytest

from dplib.core.privacy.privacy_model import (
    MECHANISM_DEFAULT_MODEL,
    MECHANISM_SUPPORTED_MODELS,
    MechanismType,
    ModelSpec,
    PrivacyModel,
    ensure_supported_model,
    mechanism_default_model,
    mechanism_supports,
    registry_snapshot,
    zcdp_to_cdp,
    cdp_to_zcdp,
    zcdp_to_rdp,
    rdp_to_cdp,
    gdp_to_zcdp,
    gdp_to_cdp,
    ldp_to_cdp,
)
from dplib.core.utils.param_validation import ParamValidationError


def test_privacy_model_from_str_and_error():
    # PrivacyModel.from_str 应支持大小写不敏感解析，未知名称抛 ParamValidationError
    assert PrivacyModel.from_str("CDP") is PrivacyModel.CDP
    assert PrivacyModel.from_str("gdp") is PrivacyModel.GDP
    with pytest.raises(ParamValidationError):
        PrivacyModel.from_str("unknown-model")


def test_mechanism_type_from_str_and_alias():
    # MechanismType.from_str 应处理大小写和别名（如 "unary" → UNARY）
    assert MechanismType.from_str("Laplace") is MechanismType.LAPLACE
    assert MechanismType.from_str("unary") is MechanismType.UNARY
    with pytest.raises(ParamValidationError):
        MechanismType.from_str("bad-mech")


def test_mechanism_model_mappings():
    # 机制默认模型 / 支持模型集合与 ensure_supported_model 的一致性校验
    assert mechanism_default_model(MechanismType.GAUSSIAN) is PrivacyModel.CDP
    assert mechanism_supports(MechanismType.GRR, PrivacyModel.LDP)
    assert not mechanism_supports(MechanismType.GRR, PrivacyModel.CDP)
    with pytest.raises(ParamValidationError):
        ensure_supported_model(MechanismType.GRR, PrivacyModel.CDP)
    ensure_supported_model(MechanismType.GRR, PrivacyModel.LDP)  # no raise
    # 映射表中应至少包含高斯机制条目
    assert MechanismType.GAUSSIAN in MECHANISM_DEFAULT_MODEL
    assert MechanismType.GAUSSIAN in MECHANISM_SUPPORTED_MODELS


def test_conversion_zcdp_to_cdp_and_inverse_bounds():
    # zCDP → CDP 与 CDP → zCDP 的公式实现与参数边界检查
    eps = zcdp_to_cdp(1.0, 1e-5)
    assert eps == pytest.approx(1 + 2 * math.sqrt(math.log(1e5)))
    rho = cdp_to_zcdp(1.0, 1e-5)
    assert rho > 0
    with pytest.raises(ParamValidationError):
        zcdp_to_cdp(-1, 1e-5)
    with pytest.raises(ParamValidationError):
        cdp_to_zcdp(1, 1.5)


def test_conversion_zcdp_to_rdp_and_rdp_to_cdp():
    # zCDP → RDP / RDP → CDP 转换公式以及非法阶数的错误分支
    assert zcdp_to_rdp(0.5, 2) == pytest.approx(1.0)
    eps_cdp = rdp_to_cdp(order=2, rdp_epsilon=1.0, delta=1e-5)
    assert eps_cdp == pytest.approx(1.0 + math.log(1e5))
    with pytest.raises(ParamValidationError):
        zcdp_to_rdp(0.5, 1)
    with pytest.raises(ParamValidationError):
        rdp_to_cdp(order=1, rdp_epsilon=1.0, delta=1e-5)


def test_gdp_and_ldp_conversions():
    # GDP → zCDP / CDP 与 LDP → CDP 的转换，以及非法参数的报错行为
    assert gdp_to_zcdp(2.0) == pytest.approx(2.0)
    eps = gdp_to_cdp(2.0, 1e-5)
    assert eps > 0
    assert ldp_to_cdp(1.2) == (1.2, 0.0)
    with pytest.raises(ParamValidationError):
        gdp_to_zcdp(0)
    with pytest.raises(ParamValidationError):
        ldp_to_cdp(-0.1)


def test_model_spec_validation_and_to_tuple():
    # 不同模型下 ModelSpec 的校验与 to_tuple 输出格式，以及缺失/非法参数的校验
    assert ModelSpec(model=PrivacyModel.LDP, epsilon=1.0).validate().to_tuple() == ("ldp", 1.0)
    assert ModelSpec(model=PrivacyModel.PURE_DP, epsilon=2.0).validate().to_tuple() == ("pure_dp", 2.0)
    assert ModelSpec(model=PrivacyModel.CDP, epsilon=1.0, delta=1e-5).to_tuple() == ("cdp", 1.0, 1e-05)
    assert ModelSpec(model=PrivacyModel.ZCDP, rho=0.5).to_tuple() == ("zcdp", 0.5)
    assert ModelSpec(model=PrivacyModel.RDP, alpha=4.0, epsilon=0.3).to_tuple() == ("rdp", 4.0, 0.3)
    assert ModelSpec(model=PrivacyModel.GDP, mu=0.8).to_tuple() == ("gdp", 0.8)
    with pytest.raises(ParamValidationError):
        ModelSpec(model=PrivacyModel.CDP, epsilon=1.0).validate()
    with pytest.raises(ParamValidationError):
        ModelSpec(model=PrivacyModel.RDP, alpha=0.5, epsilon=0.3).validate()
    with pytest.raises(ParamValidationError):
        ModelSpec(model=PrivacyModel.GDP, mu=0.0).validate()


def test_model_spec_as_cdp_conversions():
    # as_cdp 应正确从 LDP/zCDP/RDP/GDP 折算为 CDP，并调用对应转换函数
    cdp_from_ldp = ModelSpec(model=PrivacyModel.LDP, epsilon=1.0).as_cdp()
    assert cdp_from_ldp.model is PrivacyModel.CDP
    assert cdp_from_ldp.epsilon == 1.0 and cdp_from_ldp.delta == 0.0

    cdp_from_zcdp = ModelSpec(model=PrivacyModel.ZCDP, rho=0.5).as_cdp(delta=1e-5)
    assert cdp_from_zcdp.model is PrivacyModel.CDP
    assert cdp_from_zcdp.delta == pytest.approx(1e-5)

    cdp_from_rdp = ModelSpec(model=PrivacyModel.RDP, alpha=4.0, epsilon=0.5).as_cdp(delta=1e-5)
    expected_eps = rdp_to_cdp(4.0, 0.5, 1e-5)
    assert cdp_from_rdp.epsilon == pytest.approx(expected_eps)
    assert cdp_from_rdp.delta == pytest.approx(1e-5)

    cdp_from_gdp = ModelSpec(model=PrivacyModel.GDP, mu=1.0).as_cdp(delta=1e-5)
    expected_eps_gdp = gdp_to_cdp(1.0, 1e-5)
    assert cdp_from_gdp.epsilon == pytest.approx(expected_eps_gdp)
    assert cdp_from_gdp.delta == pytest.approx(1e-5)


def test_model_spec_to_parameters_filters_none():
    # to_parameters 应过滤掉 None，仅保留实际存在的数值参数
    params = ModelSpec(model=PrivacyModel.RDP, alpha=5.0, epsilon=0.2).to_parameters()
    assert params == {"epsilon": 0.2, "alpha": 5.0}


def test_registry_snapshot_contains_expected_entries():
    # registry_snapshot 返回的隐私模型/机制列表应包含常用标识
    snap = registry_snapshot()
    assert "cdp" in snap["privacy_models"]
    assert "zcdp" in snap["privacy_models"]
    assert "gaussian" in snap["mechanisms"]
    assert "grr" in snap["mechanisms"]
