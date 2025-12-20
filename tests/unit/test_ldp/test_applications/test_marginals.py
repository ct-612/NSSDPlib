"""
Unit tests for the marginals LDP application.
"""
# 说明：marginals 端到端 LDP 应用的单元测试。
# 覆盖：
# - 多维客户端上报的 report 数量与维度元数据
# - 服务端聚合输出的 marginals 结构
# - 缺失维度输入的参数校验

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.marginals import (
    MarginalSpec,
    MarginalsApplication,
    MarginalsClientConfig,
    MarginalsServerConfig,
)
from dplib.ldp.types import LDPReport


def _collect_reports(client, records: Sequence[Mapping[str, Any]], user_id: str) -> list[LDPReport]:
    # 使用客户端函数批量生成 LDPReport 列表
    reports: list[LDPReport] = []
    for record in records:
        reports.extend(client(record, user_id))
    return reports


def test_marginals_client_and_aggregator() -> None:
    # 验证多维 marginals 客户端上报与聚合结构
    specs = [
        MarginalSpec(name="color", type="categorical", categories=["red", "blue", "green"]),
        MarginalSpec(name="age_bucket", type="numerical", num_buckets=3, clip_range=(0.0, 3.0)),
    ]
    client_config = MarginalsClientConfig(epsilon_per_dimension=1.0, marginals=specs)
    server_config = MarginalsServerConfig(normalize=True)
    app = MarginalsApplication(client_config, server_config)
    client = app.build_client()

    reports = _collect_reports(
        client,
        [{"color": "red", "age_bucket": 1.0}, {"color": "blue", "age_bucket": 2.0}],
        "user-1",
    )
    assert len(reports) == 4
    assert {r.metadata.get("dimension") for r in reports} == {"color", "age_bucket"}

    aggregator = app.build_aggregator()
    estimate = aggregator.aggregate(reports)
    assert estimate.metric == "marginals"
    assert set(estimate.point.keys()) == {"color", "age_bucket"}


def test_marginals_missing_dimension_value() -> None:
    # 验证缺失维度输入时抛出 ParamValidationError
    specs = [MarginalSpec(name="color", type="categorical", categories=["red", "blue"])]
    client_config = MarginalsClientConfig(epsilon_per_dimension=1.0, marginals=specs)
    app = MarginalsApplication(client_config)
    client = app.build_client()
    with pytest.raises(ParamValidationError):
        client({"wrong_key": "red"}, "user-1")
