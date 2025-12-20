"""
Unit tests for the range queries LDP application.
"""
# 说明：range queries 端到端 LDP 应用的单元测试。
# 覆盖：
# - 客户端数值上报与基础元数据字段
# - 均值与分位数组合聚合器的构建分支
# - 参数校验与错误分支

from __future__ import annotations

import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.range_queries import (
    RangeQueriesApplication,
    RangeQueriesClientConfig,
    RangeQueriesServerConfig,
)


def test_range_queries_client_report_and_mean_aggregator() -> None:
    # 验证 range queries 客户端上报与默认均值聚合器
    client_config = RangeQueriesClientConfig(epsilon=1.0, clip_range=(0.0, 10.0))
    app = RangeQueriesApplication(client_config)
    client = app.build_client()
    report = client(4.5, "user-1")
    assert report.metadata.get("application") == "range_queries"
    assert report.metadata.get("noise_type") == "laplace"

    aggregator = app.build_aggregator()
    assert aggregator.get_metadata().get("type") == "mean"


def test_range_queries_quantile_aggregator_path() -> None:
    # 验证仅启用分位数时的聚合器选择
    client_config = RangeQueriesClientConfig(epsilon=1.0, clip_range=(0.0, 10.0))
    server_config = RangeQueriesServerConfig(estimate_mean=False, estimate_quantiles=[0.5])
    app = RangeQueriesApplication(client_config, server_config)
    aggregator = app.build_aggregator()
    assert aggregator.get_metadata().get("type") == "quantile"


def test_range_queries_combined_aggregator_path() -> None:
    # 验证同时启用均值与分位数时返回组合聚合器
    client_config = RangeQueriesClientConfig(epsilon=1.0, clip_range=(0.0, 10.0))
    server_config = RangeQueriesServerConfig(estimate_mean=True, estimate_quantiles=[0.5])
    app = RangeQueriesApplication(client_config, server_config)
    aggregator = app.build_aggregator()
    assert aggregator.get_metadata().get("type") == "range_queries"


def test_range_queries_config_validation() -> None:
    # 验证客户端与服务端参数校验逻辑
    with pytest.raises(ParamValidationError):
        RangeQueriesClientConfig(epsilon=1.0, clip_range=(1.0, 1.0))
    with pytest.raises(ParamValidationError):
        RangeQueriesServerConfig(estimate_mean=False, estimate_quantiles=None)
