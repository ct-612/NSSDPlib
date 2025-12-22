"""
Property-based tests for Utility and Privacy Reporting components.
"""
# 说明：效用报告（UtilityReport）与隐私报告（PrivacyReport）组件的属性测试。
# 覆盖：
# - 误差指标（MSE, MAE, RMSE, Bias, Variance）计算的准确性与非负性
# - 从样本集合构建效用报告的自动化流程
# - 隐私报告中累计额度（Snapshot）与剩余额度（Remaining）的动态守恒逻辑
# - 针对报告对象向 JSON/Markdown 导出的序列化一致性验证

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.cdp.analytics.reporting.utility_report import UtilityReport, ErrorMetrics, QueryUtilityRecord
from dplib.cdp.analytics.reporting.privacy_report import PrivacyReport, PrivacyUsageRecord, PrivacyAnnotation
from dplib.core.privacy import PrivacyModel, PrivacyGuarantee


# ----------------------------------------------------------------- Utility Reporting
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    st.lists(st.floats(min_value=-1000, max_value=1000),
             min_size=1,
             max_size=50))
def test_error_metrics_calculation(vals):
    # 验证误差指标计算器的正确性，确保 MSE/MAE/RMSE 等统计项符合数学逻辑
    truth = np.asarray(vals)
    # 生成带随机偏差的噪声观测值
    noise = np.random.normal(0, 1, size=len(vals))
    noisy = truth + noise

    metrics = UtilityReport.compute_error_metrics(truth, noisy)

    # 基本非负性校验
    assert metrics.mse >= 0
    assert metrics.mae >= 0
    assert metrics.rmse >= 0
    assert metrics.variance >= 0
    assert metrics.n_samples == len(vals)

    # 验证 RMSE 是 MSE 的平方根关系
    assert metrics.rmse == pytest.approx(np.sqrt(metrics.mse))
    # 验证 MSE = Bias^2 + Variance 的误差分解关系
    assert metrics.mse == pytest.approx(metrics.bias**2 + metrics.variance)


@given(
    st.lists(st.fixed_dictionaries({
        "query_id":
        st.text(min_size=1, max_size=5),
        "true_value":
        st.floats(min_value=0, max_value=100),
        "noisy_values":
        st.lists(st.floats(min_value=0, max_value=100), min_size=2,
                 max_size=5),
        "mechanism":
        st.sampled_from(["laplace", "gaussian"]),
        "epsilon":
        st.floats(min_value=0.1, max_value=1.0)
    }),
             min_size=1,
             max_size=5))
def test_utility_report_from_samples(samples):
    # 验证从分散的样本记录集合一键生成结构化效用报告的完整流程
    report = UtilityReport.from_samples(samples)

    assert len(report.records) == len(samples)
    assert report.global_summary is not None
    # 校验分组聚合逻辑：报告中的每个唯一 ID 都应在 summary 中有对应项
    unique_ids = {s["query_id"] for s in samples}
    assert len(report.per_query_summary) == len(unique_ids)


# ----------------------------------------------------------------- Privacy Reporting
@given(
    st.lists(st.fixed_dictionaries({
        "epsilon":
        st.floats(min_value=0.01, max_value=1.0),
        "delta":
        st.floats(min_value=0, max_value=0.001)
    }),
             min_size=1,
             max_size=10),
    st.floats(min_value=10.0, max_value=20.0)  # Total budget epsilon
)
def test_privacy_report_snapshot_consistency(events_data, total_eps):
    # 验证隐私报告在处理事件序列时，时间线快照（Timeline Snapshot）的额度计算一致性
    total_spent = PrivacyGuarantee(model=PrivacyModel.CDP,
                                   epsilon=0.0,
                                   delta=0.0)
    # 构造剩余额度（如果存在总预算限制）
    total_limit = PrivacyGuarantee(model=PrivacyModel.CDP,
                                   epsilon=total_eps,
                                   delta=0.1)

    report = PrivacyReport(model=PrivacyModel.CDP,
                           total_budget=total_limit,
                           spent=total_spent,
                           remaining=total_limit)

    cumulative_eps = 0.0
    for i, data in enumerate(events_data):
        rec = PrivacyUsageRecord(event_id=f"e{i}",
                                 name=f"event_{i}",
                                 mechanism="laplace",
                                 privacy_model=PrivacyModel.CDP,
                                 epsilon=data["epsilon"],
                                 delta=data["delta"])
        report.events.append(rec)
        cumulative_eps += data["epsilon"]

    # 执行时间线重算逻辑
    # 核心测试点：确保 report.remaining 在初始总量基础上随事件序列正确递减
    report.remaining = PrivacyGuarantee(model=PrivacyModel.CDP,
                                        epsilon=total_eps,
                                        delta=0.1)
    report.compute_timeline()

    assert len(report.timeline) == len(events_data)
    # 验证最后一个快照的累计消耗量与手动计算结果一致
    last_snap = report.timeline[-1]
    assert last_snap.cumulative_epsilon == pytest.approx(cumulative_eps)
    # 验证剩余额度守恒：已消耗 + 剩余 = 总额度（允许微小浮点误差）
    if last_snap.remaining_epsilon is not None:
        assert last_snap.cumulative_epsilon + last_snap.remaining_epsilon == pytest.approx(
            total_eps)


# ----------------------------------------------------------------- Serialization
def test_report_serialization_formats():
    # 验证报告对象同时支持字典、JSON 以及 Markdown 导出，且数据内容结构一致
    metrics = ErrorMetrics(mse=0.1,
                           mae=0.2,
                           rmse=0.316,
                           bias=0.05,
                           variance=0.09,
                           max_error=0.4,
                           n_samples=10)
    record = QueryUtilityRecord(query_id="q1",
                                mechanism="laplace",
                                epsilon=1.0,
                                delta=0.0,
                                true_value=10.0,
                                noisy_values=[10.1, 9.9],
                                error_metrics=metrics)
    report = UtilityReport(records=[record])
    report.compute_global_summary()

    # 验证输出不为空且包含关键关键字
    json_out = report.to_json()
    assert "q1" in json_out
    assert "mse" in json_out

    md_out = report.to_markdown()
    assert "| q1 |" in md_out
    assert "0.1000" in md_out
