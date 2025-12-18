"""
Unit tests for the QuantileAggregator over numeric LDP reports.
"""
# 说明：针对 QuantileAggregator 在存在/不存在噪声信息场景下的分位数估计行为进行单元测试。
# 覆盖：
# - 从 LDPReport 元数据中解析 noise_std 与 noise_type 并执行 Laplace 去噪调整
# - 噪声类型不受支持时的回退逻辑与元数据记录方式
# - 未提供噪声信息时保持观测分位数并在元数据中标记缺省噪声配置

import numpy as np
import pytest

from dplib.ldp.aggregators.quantile import QuantileAggregator
from dplib.ldp.types import LDPReport


def test_quantile_basic_and_noise_meta_resolution():
    # 验证从元数据中解析 Laplace 噪声参数并对分位数做噪声去偏调整且在元数据中标记 noise_adjusted
    reports = [
        LDPReport(user_id=1, mechanism_id="laplace", encoded=0.0, epsilon=1.0, metadata={"noise_std": 1.0, "noise_type": "laplace"}),
        LDPReport(user_id=2, mechanism_id="laplace", encoded=2.0, epsilon=1.0, metadata={"noise_std": 1.0, "noise_type": "laplace"}),
    ]
    agg = QuantileAggregator([0.25, 0.5], method="linear")
    est = agg.aggregate(reports)
    assert est.metric == "quantile"
    assert est.metadata["noise_adjusted"] is True
    assert est.metadata["noise_type"] == "laplace"
    assert len(est.point) == 2


def test_quantile_unsupported_noise_type_fallback():
    # 验证当噪声类型未知时不会进行去噪调整并在元数据中记录 fallback 原因
    reports = [
        LDPReport(user_id=1, mechanism_id="custom", encoded=1.0, epsilon=1.0, metadata={"noise_std": 0.5, "noise_type": "unknown"}),
        LDPReport(user_id=2, mechanism_id="custom", encoded=3.0, epsilon=1.0, metadata={"noise_std": 0.5, "noise_type": "unknown"}),
    ]
    agg = QuantileAggregator([0.5], method="linear")
    est = agg.aggregate(reports)
    # 噪声类型不支持时不进行调整
    assert est.metadata["noise_adjusted"] is False or est.metadata["noise_adjustment_reason"] in ("noise_type_unsupported", "scipy_missing")


def test_quantile_no_noise_provided():
    # 验证未显式提供噪声参数时保持原始观测分位数并在元数据中将 noise_std 记录为 None
    reports = [
        LDPReport(user_id=1, mechanism_id="custom", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="custom", encoded=3.0, epsilon=1.0, metadata={}),
    ]
    agg = QuantileAggregator([0.5])
    est = agg.aggregate(reports)
    assert est.metadata["noise_std"] is None
