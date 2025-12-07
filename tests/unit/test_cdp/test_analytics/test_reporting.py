"""
Unit tests for privacy and utility reporting helpers.
"""
# 说明：隐私预算报告与效用报告相关辅助工具的单元测试。
# 覆盖：
# - 从 CDPPrivacyAccountant 构建 PrivacyReport 并生成时间线与注释
# - PrivacyReport 手动追加事件后时间线与 event_id 映射行为
# - UtilityReport 误差指标加权聚合与(误差-ε)、(偏差/方差-ε) 曲线接口

from __future__ import annotations

import json

import numpy as np
import pytest

from dplib.cdp.analytics.reporting.privacy_report import (
    PrivacyReport,
    PrivacyUsageRecord,
)
from dplib.cdp.analytics.reporting.utility_report import UtilityReport
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.privacy import PrivacyModel


def test_privacy_report_from_accountant_and_annotations() -> None:
    # 验证基于 CDPPrivacyAccountant 构建 PrivacyReport 的时间线与注释生成逻辑
    accountant = CDPPrivacyAccountant(total_epsilon=1.0, total_delta=1e-5)
    accountant._accountant.add_event(0.2, 1e-6, description="q1", metadata={"tags": {"step": "1"}})
    accountant._accountant.add_event(0.6, 2e-6, description="q2")

    report = PrivacyReport.from_accountant(accountant, metadata={"run": "unit"})

    assert report.model == PrivacyModel.CDP
    assert pytest.approx(report.spent.epsilon) == 0.8
    assert len(report.events) == 2
    assert len(report.timeline) == 2
    # 剩余 epsilon 应等于总预算减去已花费的部分
    assert report.remaining is not None
    assert pytest.approx(report.remaining.epsilon) == 0.2
    # 注释应在花费达到 80% 阈值时产生 warning 级别标记
    assert any(ann.level == "warning" for ann in report.annotations)
    curve = report.get_epsilon_curve()
    assert curve["x"] == [1, 2]
    assert curve["y"][-1] == pytest.approx(0.8)
    # JSON 序列化往返应保持关键隐私预算数值一致
    payload = json.loads(report.to_json())
    assert payload["spent"]["epsilon"] == pytest.approx(0.8)


def test_privacy_report_manual_append_and_timeline() -> None:
    # 验证手动追加 PrivacyUsageRecord 后 compute_timeline 的累计 epsilon 与事件关联是否正确
    report = PrivacyReport(
        model=PrivacyModel.CDP,
        total_budget=None,
        spent=PrivacyReport.from_accountant(CDPPrivacyAccountant()).spent,
        remaining=None,
    )
    report.add_event(
        PrivacyUsageRecord(
            event_id="evt-custom",
            name="manual",
            mechanism="laplace",
            privacy_model=PrivacyModel.CDP,
            epsilon=0.1,
            delta=0.0,
        )
    )
    report.compute_timeline()
    assert report.timeline[0].cumulative_epsilon == pytest.approx(0.1)
    assert report.timeline[0].event_id == "evt-custom"


def test_utility_report_metrics_and_curves() -> None:
    # 验证 UtilityReport 的误差指标计算、全局加权聚合与(误差-ε)曲线、(偏差/方差-ε)权衡曲线生成行为
    samples = [
        {
            "query_id": "q1",
            "mechanism": "gaussian",
            "epsilon": 1.0,
            "delta": 1e-5,
            "true_value": np.array([10.0, 10.0, 10.0]),
            "noisy_values": np.array([11.0, 9.0, 10.5]),
        },
        {
            "query_id": "q1",
            "mechanism": "gaussian",
            "epsilon": 0.5,
            "delta": 1e-5,
            "true_value": np.array([5.0, 5.0]),
            "noisy_values": np.array([4.5, 5.5]),
        },
    ]

    report = UtilityReport.from_samples(samples)

    assert len(report.records) == 2
    assert report.global_summary is not None
    assert report.per_query_summary["q1"].n_samples == 5
    # 全局 MSE 应为两条记录按样本数加权后的平均值
    assert report.global_summary.mse == pytest.approx(0.55, rel=1e-2)
    curves = report.get_error_vs_epsilon(metric="mse", query_id="q1")
    assert len(curves) == 1
    assert curves[0].x == sorted([0.5, 1.0])
    tradeoff = report.get_bias_variance_tradeoff(query_id="q1")
    assert len(tradeoff) == 2
    assert tradeoff[0].y_label == "bias"
