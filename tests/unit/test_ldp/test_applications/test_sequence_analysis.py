"""
Unit tests for the sequence analysis LDP application.
"""
# 说明：sequence analysis 端到端 LDP 应用的单元测试。
# 覆盖：
# - 客户端序列上报的长度裁剪与位置元数据
# - 服务端按位置聚合的输出结构
# - bigram 未实现路径的错误分支

from __future__ import annotations

import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.sequence_analysis import (
    SequenceAnalysisApplication,
    SequenceAnalysisClientConfig,
    SequenceAnalysisServerConfig,
)


def test_sequence_analysis_client_and_aggregator() -> None:
    # 验证序列分析客户端上报与按位置聚合输出
    client_config = SequenceAnalysisClientConfig(
        epsilon_per_event=1.0,
        max_length=3,
        categories=["a", "b", "c"],
    )
    app = SequenceAnalysisApplication(client_config)
    client = app.build_client()
    reports = client(["a", "b", "c", "a"], "user-1")
    assert len(reports) == 3
    assert [r.metadata.get("position") for r in reports] == [0, 1, 2]

    aggregator = app.build_aggregator()
    estimate = aggregator.aggregate(reports)
    assert estimate.metric == "sequence_unigram"
    assert set(estimate.point.keys()) == {0, 1, 2}


def test_sequence_analysis_bigram_not_supported() -> None:
    # 验证 bigram 开关启用时抛出 ParamValidationError
    client_config = SequenceAnalysisClientConfig(
        epsilon_per_event=1.0,
        max_length=3,
        categories=["a", "b", "c"],
    )
    server_config = SequenceAnalysisServerConfig(estimate_unigram=True, estimate_bigram=True)
    app = SequenceAnalysisApplication(client_config, server_config)
    with pytest.raises(ParamValidationError):
        app.build_client()
