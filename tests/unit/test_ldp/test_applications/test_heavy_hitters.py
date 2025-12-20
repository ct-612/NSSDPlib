"""
Unit tests for the heavy hitters LDP application.
"""
# 说明：heavy hitters 端到端 LDP 应用的单元测试。
# 覆盖：
# - 客户端报告生成与元数据字段
# - 服务端聚合输出的频率估计结构
# - top-k 提取辅助函数的排序与过滤逻辑

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.heavy_hitters import (
    HeavyHittersApplication,
    HeavyHittersClientConfig,
    HeavyHittersServerConfig,
    extract_top_k,
)
from dplib.ldp.types import Estimate, LDPReport


def _collect_reports(client, values: Sequence[Any], user_id: str) -> list[LDPReport]:
    # 使用客户端函数批量生成 LDPReport 列表
    return [client(value, user_id) for value in values]


def test_heavy_hitters_client_report_metadata() -> None:
    # 验证 heavy hitters 客户端生成报告与核心元数据字段
    client_config = HeavyHittersClientConfig(epsilon=1.0, categories=["a", "b", "c"], top_k=2)
    app = HeavyHittersApplication(client_config, HeavyHittersServerConfig(top_k=2))
    client = app.build_client()
    report = client("a", "user-1")
    assert report.user_id == "user-1"
    assert report.metadata.get("application") == "heavy_hitters"
    assert report.metadata.get("domain_size") == 3
    assert "mechanism" in report.metadata


def test_heavy_hitters_aggregate_and_extract_top_k() -> None:
    # 验证聚合输出的频率估计结构与 top-k 辅助函数行为
    client_config = HeavyHittersClientConfig(epsilon=1.0, categories=["a", "b", "c"], top_k=2)
    app = HeavyHittersApplication(client_config)
    client = app.build_client()
    reports = _collect_reports(client, ["a", "b", "b", "c", "a"], "user-1")
    aggregator = app.build_aggregator()
    estimate = aggregator.aggregate(reports)
    values = np.asarray(estimate.point, dtype=float)
    assert estimate.metric == "frequency"
    assert values.shape[0] == 3
    assert values.sum() == pytest.approx(1.0)

    manual_est = Estimate(
        metric="frequency",
        point=np.asarray([0.1, 0.6, 0.3]),
        metadata={"categories": ["x", "y", "z"]},
    )
    top_k = extract_top_k(manual_est, top_k=2)
    assert top_k[0][0] == "y"
    assert top_k[1][0] == "z"


def test_heavy_hitters_config_validation() -> None:
    # 验证 heavy hitters 配置参数的基本校验
    with pytest.raises(ParamValidationError):
        HeavyHittersClientConfig(epsilon=1.0, categories=[], top_k=2)
    with pytest.raises(ParamValidationError):
        HeavyHittersClientConfig(epsilon=1.0, categories=["a", "b"], top_k=0)
