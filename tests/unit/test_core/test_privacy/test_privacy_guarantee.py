"""
Unit tests for the PrivacyGuarantee helper.
"""
# 说明：PrivacyGuarantee（隐私保证表示容器）的单元测试。
# 覆盖：
# - from_model_spec 的构造路径：LDP/RDP 等模型到容器的组装与 to_dict/to_report 导出
# - 机制与隐私模型不兼容时的 ParamValidationError 校验
# - validate 对必需参数缺失（如 CDP 中缺少 delta）的错误检测
# - as_cdp_view 从 zCDP/RDP/GDP 等模型折算到 CDP 时与 zcdp_to_cdp/rdp_to_cdp/gdp_to_cdp 一致性
# - to_model_spec 往返转换保持模型类型与数值参数不变

import pytest

from dplib.core.privacy.privacy_guarantee import PrivacyGuarantee
from dplib.core.privacy.privacy_model import MechanismType, ModelSpec, PrivacyModel, rdp_to_cdp, zcdp_to_cdp, gdp_to_cdp
from dplib.core.utils.param_validation import ParamValidationError


def test_from_model_spec_ldp_and_dict():
    # LDP 模型通过 from_model_spec 构造 Guarantee，验证 to_dict() 导出的结构和参数
    spec = ModelSpec(model=PrivacyModel.LDP, epsilon=0.8)
    guarantee = PrivacyGuarantee.from_model_spec(spec, mechanism=MechanismType.GRR, description="ldp event")
    data = guarantee.to_dict()
    assert data["model"] == "ldp"
    assert data["mechanism"] == "grr"
    assert data["parameters"]["epsilon"] == 0.8
    assert data["description"] == "ldp event"


def test_from_model_spec_rdp_and_report():
    # RDP 模型通过 from_model_spec 构造 Guarantee，验证 to_report() 中参数与摘要内容
    spec = ModelSpec(model=PrivacyModel.RDP, alpha=5.0, epsilon=0.3)
    guarantee = PrivacyGuarantee.from_model_spec(spec, mechanism=MechanismType.GAUSSIAN)
    report = guarantee.to_report()
    assert report["model"] == "rdp"
    assert "alpha" in report["parameters"]
    assert "epsilon=0.3" in report["summary"]


def test_invalid_mechanism_for_model_raises():
    # 为 CDP 模型选择不支持的 LDP 机制（GRR）应触发 ParamValidationError
    spec = ModelSpec(model=PrivacyModel.CDP, epsilon=1.0, delta=1e-5)
    with pytest.raises(ParamValidationError):
        PrivacyGuarantee.from_model_spec(spec, mechanism=MechanismType.GRR)


def test_validate_requires_parameters():
    # 对 CDP 模型缺少 delta 时，validate() 应抛出 ParamValidationError
    bad = PrivacyGuarantee(model=PrivacyModel.CDP, epsilon=1.0)  # missing delta
    with pytest.raises(ParamValidationError):
        bad.validate()


def test_as_cdp_from_zcdp_rdp_gdp():
    # as_cdp_view 应分别使用 zcdp_to_cdp / rdp_to_cdp / gdp_to_cdp 进行折算，结果与辅助函数一致
    z_spec = ModelSpec(model=PrivacyModel.ZCDP, rho=1.0)
    z_guar = PrivacyGuarantee.from_model_spec(z_spec, mechanism=MechanismType.GAUSSIAN)
    z_cdp = z_guar.as_cdp_view(delta=1e-5)
    assert z_cdp.model is PrivacyModel.CDP
    assert z_cdp.delta == pytest.approx(1e-5)
    assert z_cdp.epsilon == pytest.approx(zcdp_to_cdp(1.0, 1e-5))

    r_spec = ModelSpec(model=PrivacyModel.RDP, alpha=3.0, epsilon=0.5)
    r_guar = PrivacyGuarantee.from_model_spec(r_spec, mechanism=MechanismType.GAUSSIAN)
    r_cdp = r_guar.as_cdp_view(delta=1e-5)
    expected_rdp = rdp_to_cdp(3.0, 0.5, 1e-5)
    assert r_cdp.epsilon == pytest.approx(expected_rdp)
    assert r_cdp.delta == pytest.approx(1e-5)

    g_spec = ModelSpec(model=PrivacyModel.GDP, mu=1.2)
    g_guar = PrivacyGuarantee.from_model_spec(g_spec, mechanism=MechanismType.GAUSSIAN)
    g_cdp = g_guar.as_cdp_view(delta=1e-5)
    assert g_cdp.epsilon == pytest.approx(gdp_to_cdp(1.2, 1e-5))
    assert g_cdp.delta == pytest.approx(1e-5)


def test_to_model_spec_roundtrip():
    # from_model_spec → to_model_spec 往返应保持隐私模型及其参数不变
    spec = ModelSpec(model=PrivacyModel.CDP, epsilon=1.0, delta=1e-6)
    guar = PrivacyGuarantee.from_model_spec(spec, mechanism=MechanismType.GAUSSIAN, description="cdp")
    roundtrip = guar.to_model_spec()
    assert roundtrip.model is PrivacyModel.CDP
    assert roundtrip.epsilon == 1.0
    assert roundtrip.delta == pytest.approx(1e-6)
