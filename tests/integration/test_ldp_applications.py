"""
Integration tests for LDP application pipelines.
"""
# 说明：LDP 应用端到端流程的集成测试
# 覆盖：
# - 频率 重频 区间 边缘 序列 键值应用管线
# - 应用配置错误路径与参数校验
from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.frequency_estimation import (
    FrequencyEstimationApplication,
    FrequencyEstimationClientConfig,
)
from dplib.ldp.applications.heavy_hitters import (
    HeavyHittersApplication,
    HeavyHittersClientConfig,
    HeavyHittersServerConfig,
    extract_top_k,
)
from dplib.ldp.applications.key_value import (
    KeyValueApplication,
    KeyValueClientConfig,
    KeyValueServerConfig,
)
from dplib.ldp.applications.marginals import MarginalSpec, MarginalsApplication, MarginalsClientConfig
from dplib.ldp.applications.range_queries import (
    RangeQueriesApplication,
    RangeQueriesClientConfig,
    RangeQueriesServerConfig,
)
from dplib.ldp.applications.sequence_analysis import (
    SequenceAnalysisApplication,
    SequenceAnalysisClientConfig,
    SequenceAnalysisServerConfig,
)


def test_frequency_estimation_application_end_to_end() -> None:
    # 验证频率估计应用的端到端流程
    categories = ["a", "b", "c"]
    # 构造应用配置并生成客户端与聚合器
    app = FrequencyEstimationApplication(
        FrequencyEstimationClientConfig(epsilon=4.0, categories=categories)
    )
    client = app.build_client()
    aggregator = app.build_aggregator()
    data = ["a"] * 300 + ["b"] * 120 + ["c"] * 80

    # 生成报告并聚合得到频率估计
    reports = [client(value, user_id=str(idx)) for idx, value in enumerate(data)]
    estimate = aggregator.aggregate(reports)
    point = np.asarray(estimate.point, dtype=float)

    # 校验输出分布形状与归一化约束
    assert point.shape == (len(categories),)
    assert float(point.sum()) == pytest.approx(1.0, abs=1e-6)
    assert np.all(point >= 0.0)


def test_heavy_hitters_application_end_to_end() -> None:
    # 验证重频应用的端到端流程与 top-k 输出
    categories = ["a", "b", "c"]
    # 构造应用配置并生成客户端
    app = HeavyHittersApplication(
        HeavyHittersClientConfig(epsilon=6.0, categories=categories, top_k=2),
        HeavyHittersServerConfig(top_k=2, min_support=0.0),
    )
    client = app.build_client()
    # 固定随机种子以降低随机性影响
    if app._mechanism is not None:
        app._mechanism.reseed(0)
    aggregator = app.build_aggregator()
    data = ["a"] * 400 + ["b"] * 80 + ["c"] * 20

    # 生成报告并聚合后提取 top-k
    reports = [client(value, user_id=str(idx)) for idx, value in enumerate(data)]
    estimate = aggregator.aggregate(reports)
    top = extract_top_k(estimate, top_k=2)

    # 校验 top-k 结果包含主类
    assert top
    assert top[0][0] == "a"


def test_range_queries_application_end_to_end() -> None:
    # 验证区间查询应用可输出均值与分位数
    # 构造客户端与服务端配置
    client_cfg = RangeQueriesClientConfig(epsilon=4.0, clip_range=(0.0, 10.0))
    server_cfg = RangeQueriesServerConfig(estimate_mean=True, estimate_quantiles=[0.25, 0.5, 0.75])
    app = RangeQueriesApplication(client_cfg, server_cfg)
    client = app.build_client()
    aggregator = app.build_aggregator()
    data = list(range(10)) * 10

    # 生成报告并聚合区间统计
    reports = [client(float(value), user_id=str(idx)) for idx, value in enumerate(data)]
    estimate = aggregator.aggregate(reports)

    # 校验输出包含均值与分位数
    assert estimate.metric == "range_queries"
    assert "mean" in estimate.point
    assert "quantiles" in estimate.point
    assert len(estimate.point["quantiles"]) == 3


def test_marginals_application_end_to_end() -> None:
    # 验证多维边缘应用的端到端聚合
    # 构造类别与数值维度配置
    specs = [
        MarginalSpec(name="color", type="categorical", categories=["red", "blue"]),
        MarginalSpec(name="age", type="numerical", num_buckets=4, clip_range=(0.0, 4.0)),
    ]
    app = MarginalsApplication(MarginalsClientConfig(epsilon_per_dimension=4.0, marginals=specs))
    client = app.build_client()
    aggregator = app.build_aggregator()
    records = [
        {"color": "red", "age": 1.0},
        {"color": "blue", "age": 2.2},
        {"color": "red", "age": 3.5},
        {"color": "blue", "age": 0.1},
    ]

    # 收集各维度报告后聚合
    reports = []
    for idx, record in enumerate(records):
        reports.extend(client(record, user_id=str(idx)))

    estimate = aggregator.aggregate(reports)
    color_point = np.asarray(estimate.point["color"], dtype=float)
    age_point = np.asarray(estimate.point["age"], dtype=float)

    # 校验各维度输出形状
    assert color_point.shape == (2,)
    assert age_point.shape == (4,)


def test_sequence_analysis_application_end_to_end() -> None:
    # 验证序列分析应用按位置输出频率估计
    categories = ["x", "y", "z"]
    # 构造应用配置与序列样本
    app = SequenceAnalysisApplication(
        SequenceAnalysisClientConfig(epsilon_per_event=4.0, max_length=3, categories=categories),
        SequenceAnalysisServerConfig(estimate_unigram=True),
    )
    client = app.build_client()
    aggregator = app.build_aggregator()
    sequences = [
        ["x", "y", "z"],
        ["x", "x", "y"],
        ["z", "y", "x"],
    ]

    # 生成多位置报告并聚合
    reports = []
    for idx, seq in enumerate(sequences):
        reports.extend(client(seq, user_id=str(idx)))

    estimate = aggregator.aggregate(reports)
    # 校验每个位置的分布形状
    assert estimate.metric == "sequence_unigram"
    for position in range(3):
        point = np.asarray(estimate.point[position], dtype=float)
        assert point.shape == (len(categories),)


def test_key_value_application_end_to_end() -> None:
    # 验证键值应用能同时估计频率与均值
    # 构造 key 与 value 配置
    client_cfg = KeyValueClientConfig(
        epsilon_key=4.0,
        epsilon_value=3.0,
        categories=["k1", "k2", "k3"],
        value_clip_range=(0.0, 10.0),
    )
    server_cfg = KeyValueServerConfig(estimate_key_frequency=True, estimate_value_mean=True)
    app = KeyValueApplication(client_cfg, server_cfg)
    client = app.build_client()
    aggregator = app.build_aggregator()
    pairs = [("k1", 2.0), ("k2", 5.0), ("k1", 3.0), ("k3", 7.5)]

    # 生成键值报告并聚合
    reports = []
    for idx, pair in enumerate(pairs):
        reports.extend(client(pair, user_id=str(idx)))

    estimate = aggregator.aggregate(reports)
    # 校验输出包含频率与均值
    assert estimate.metric == "key_value"
    assert "frequency" in estimate.point
    assert "value_mean" in estimate.point
    assert np.asarray(estimate.point["frequency"]).shape == (3,)


def test_sequence_analysis_bigram_not_supported() -> None:
    # 验证启用 bigram 配置会触发未实现错误
    app = SequenceAnalysisApplication(
        SequenceAnalysisClientConfig(epsilon_per_event=1.0, max_length=2, categories=["a", "b"]),
        SequenceAnalysisServerConfig(estimate_unigram=True, estimate_bigram=True),
    )
    # 校验构建客户端时抛出异常
    with pytest.raises(ParamValidationError):
        app.build_client()


def test_marginals_application_missing_dimension_raises() -> None:
    # 验证缺失维度输入会触发参数校验异常
    specs = [MarginalSpec(name="color", type="categorical", categories=["red", "blue"])]
    app = MarginalsApplication(MarginalsClientConfig(epsilon_per_dimension=1.0, marginals=specs))
    client = app.build_client()
    # 校验缺失字段时报错
    with pytest.raises(ParamValidationError):
        client({"age": 2.0}, user_id="u1")


def test_key_value_requires_value_epsilon_when_mean_enabled() -> None:
    # 验证启用均值估计时必须提供 value 的 epsilon
    client_cfg = KeyValueClientConfig(epsilon_key=1.0, epsilon_value=None, categories=["k1", "k2"])
    server_cfg = KeyValueServerConfig(estimate_key_frequency=False, estimate_value_mean=True)
    # 校验初始化阶段的参数检查
    with pytest.raises(ParamValidationError):
        KeyValueApplication(client_cfg, server_cfg)
