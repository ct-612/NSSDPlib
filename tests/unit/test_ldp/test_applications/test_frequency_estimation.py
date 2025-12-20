"""
Unit tests for the frequency estimation LDP application.
"""
# 说明：frequency estimation 端到端 LDP 应用的单元测试。
# 覆盖：
# - 客户端报告生成与归一化聚合路径
# - normalize 关闭时的聚合器选择
# - 配置参数的基础校验

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.frequency_estimation import (
    FrequencyEstimationApplication,
    FrequencyEstimationClientConfig,
    FrequencyEstimationServerConfig,
)
from dplib.ldp.types import LDPReport


def _collect_reports(client, values: Sequence[Any], user_id: str) -> list[LDPReport]:
    # 使用客户端函数批量生成 LDPReport 列表
    return [client(value, user_id) for value in values]


def test_frequency_estimation_client_and_normalized_aggregator() -> None:
    # 验证频率估计客户端与默认一致性后处理聚合器
    client_config = FrequencyEstimationClientConfig(epsilon=1.0, categories=["a", "b", "c"])
    app = FrequencyEstimationApplication(client_config)
    client = app.build_client()
    reports = _collect_reports(client, ["a", "b", "b", "c"], "user-1")
    aggregator = app.build_aggregator()
    assert aggregator.get_metadata().get("type") == "consistency"
    estimate = aggregator.aggregate(reports)
    values = np.asarray(estimate.point, dtype=float)
    assert estimate.metric == "frequency"
    assert values.sum() == pytest.approx(1.0)


def test_frequency_estimation_without_normalize() -> None:
    # 验证 normalize 关闭时返回基础频率聚合器
    client_config = FrequencyEstimationClientConfig(epsilon=1.0, categories=["a", "b", "c"])
    server_config = FrequencyEstimationServerConfig(normalize=False)
    app = FrequencyEstimationApplication(client_config, server_config)
    aggregator = app.build_aggregator()
    assert aggregator.get_metadata().get("type") == "frequency"


def test_frequency_estimation_config_validation() -> None:
    # 验证频率估计配置参数的校验逻辑
    with pytest.raises(ParamValidationError):
        FrequencyEstimationClientConfig(epsilon=1.0, categories=[], mechanism="grr")
    with pytest.raises(ParamValidationError):
        FrequencyEstimationClientConfig(epsilon=1.0, categories=["a"], mechanism="oue")
