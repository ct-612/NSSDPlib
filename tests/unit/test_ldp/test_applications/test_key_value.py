"""
Unit tests for the key-value LDP application.
"""
# 说明：key-value 端到端 LDP 应用的单元测试。
# 覆盖：
# - 客户端 key 与 value 报告生成逻辑
# - 服务端聚合输出同时包含频率与均值估计
# - 配置参数的基本校验

from __future__ import annotations

import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.key_value import (
    KeyValueApplication,
    KeyValueClientConfig,
    KeyValueServerConfig,
)


def test_key_value_client_reports() -> None:
    # 验证 key-value 客户端生成 key 与 value 两类报告
    client_config = KeyValueClientConfig(
        epsilon_key=1.0,
        epsilon_value=0.5,
        categories=["k1", "k2"],
        value_clip_range=(0.0, 10.0),
    )
    app = KeyValueApplication(client_config)
    client = app.build_client()
    reports = client(("k1", 3.0), "user-1")
    assert len(reports) == 2
    metrics = {report.metadata.get("metric") for report in reports}
    assert metrics == {"key", "value"}


def test_key_value_aggregator_outputs_both_metrics() -> None:
    # 验证聚合输出包含 key 频率与 value 均值
    client_config = KeyValueClientConfig(
        epsilon_key=1.0,
        epsilon_value=0.5,
        categories=["k1", "k2"],
        value_clip_range=(0.0, 10.0),
    )
    server_config = KeyValueServerConfig(estimate_key_frequency=True, estimate_value_mean=True)
    app = KeyValueApplication(client_config, server_config)
    client = app.build_client()
    reports = []
    reports.extend(client(("k1", 2.0), "user-1"))
    reports.extend(client(("k2", 4.0), "user-2"))
    aggregator = app.build_aggregator()
    estimate = aggregator.aggregate(reports)
    assert estimate.metric == "key_value"
    assert "frequency" in estimate.point
    assert "value_mean" in estimate.point


def test_key_value_config_validation() -> None:
    # 验证 key-value 配置参数校验分支
    with pytest.raises(ParamValidationError):
        KeyValueApplication(
            KeyValueClientConfig(epsilon_key=1.0, categories=["k1"]),
            KeyValueServerConfig(estimate_key_frequency=True, estimate_value_mean=True),
        )
    with pytest.raises(ParamValidationError):
        KeyValueApplication(
            KeyValueClientConfig(epsilon_key=1.0, epsilon_value=0.5, categories=["k1"], value_clip_range=None),
            KeyValueServerConfig(estimate_value_mean=True),
        )
