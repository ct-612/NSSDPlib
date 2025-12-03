"""
Tests for SensitivityAnalyzer dispatch and validation.
"""
# 说明：SensitivityAnalyzer 分发逻辑和输入参数校验行为的单元测试。
# 覆盖：
# - 常见查询在通过 SensitivityAnalyzer 调用时返回的 query 名称与敏感度数值
# - 通过 analyze 统一入口分发到各查询分析方法时返回的 query 名称与敏感度数值
# - analyze 接口在缺失必填参数或传入非法组合时抛出 ParamValidationError
# - 对未知查询名称的防御性校验分支

import pytest

from dplib.cdp.sensitivity import SensitivityAnalyzer
from dplib.core.data import ContinuousDomain
from dplib.core.utils.param_validation import ParamValidationError


def test_sensitivity_analyzer_reports_values() -> None:
    # 验证通过 SensitivityAnalyzer 调用 count 和 range_mean 时报告的 query 名称与敏感度是否符合预期
    analyzer = SensitivityAnalyzer()
    domain = ContinuousDomain(minimum=0.0, maximum=4.0)

    report = analyzer.count(max_contribution=2)
    assert report.query == "count"
    assert report.sensitivity == pytest.approx(2.0)

    report = analyzer.range(domain, window=2, max_contribution=1, metric="mean")
    assert report.query == "range_mean"
    assert report.sensitivity == pytest.approx(4.0)


def test_sensitivity_analyze_reports_values() -> None:
    # 验证通过统一入口根据查询名分派到对应分析方法时报告的 query 名称与敏感度是否符合预期
    analyzer = SensitivityAnalyzer()
    domain = ContinuousDomain(minimum=0.0, maximum=4.0)

    report = analyzer.analyze("count", max_contribution=2)
    assert report.query == "count"
    assert report.sensitivity == pytest.approx(2.0)

    report = analyzer.analyze("range", domain=domain, window=3, max_contribution=2, metric="mean")
    assert report.query == "range_mean"
    assert report.sensitivity == pytest.approx(8.0)


def test_sensitivity_analyzer_validate_inputs() -> None:
    # 检查 analyze 接口在缺失 domain/window 等必需参数或传入未知查询名时是否抛出 ParamValidationError
    analyzer = SensitivityAnalyzer()
    domain = ContinuousDomain(minimum=0.0, maximum=4.0)

    with pytest.raises(ParamValidationError):
        analyzer.analyze("sum")
    with pytest.raises(ParamValidationError):
        analyzer.analyze("range", domain=domain, window=None)  # type: ignore[arg-type]
    with pytest.raises(ParamValidationError):
        analyzer.analyze("unknown")
