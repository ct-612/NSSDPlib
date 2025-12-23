"""
Integration tests for LDP interoperability pipelines.
"""
# 说明：LDP 编码 机制 聚合组件互操作测试
# 覆盖：
# - GRR 与 OUE 管线端到端频率估计
# - LocalLaplace 与均值聚合器的一致性检查
# - 向量长度不一致时的错误路径
from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.encoders import CategoricalEncoder, UnaryEncoder
from dplib.ldp.mechanisms.continuous import LocalLaplaceMechanism
from dplib.ldp.mechanisms.discrete import GRRMechanism, OUEMechanism
from dplib.ldp.types import LDPReport


def test_grr_categorical_frequency_pipeline() -> None:
    # 验证 GRR 与分类编码的频率估计管线
    categories = ["a", "b", "c"]
    encoder = CategoricalEncoder(categories=categories)
    mechanism = GRRMechanism(
        epsilon=4.0,
        domain_size=len(categories),
        rng=np.random.default_rng(123),
    )
    data = ["a"] * 800 + ["b"] * 150 + ["c"] * 50
    # 预置机制元数据以支持去偏估计
    base_metadata = {
        "domain_size": len(categories),
        "prob_true": mechanism.prob_true,
        "prob_false": mechanism.prob_false,
        "mechanism": mechanism.mechanism_id,
    }

    # 生成报告并聚合输出
    reports = [
        mechanism.generate_report(
            encoder.encode(value),
            user_id=str(idx),
            metadata=dict(base_metadata),
        )
        for idx, value in enumerate(data)
    ]

    aggregator = FrequencyAggregator(num_categories=None, mechanism="grr")
    estimate = aggregator.aggregate(reports)
    point = np.asarray(estimate.point, dtype=float)

    # 校验分布形状与主类占比
    assert point.shape == (len(categories),)
    assert float(point.sum()) == pytest.approx(1.0, abs=1e-6)
    assert int(np.argmax(point)) == 0
    assert point[0] > 0.5
    assert estimate.metadata["n_reports"] == len(data)


def test_oue_unary_frequency_pipeline() -> None:
    # 验证 OUE 与 unary 编码的频率估计管线
    length = 5
    encoder = UnaryEncoder(length=length)
    mechanism = OUEMechanism(
        epsilon=4.0,
        rng=np.random.default_rng(77),
    )
    data = [2] * 600 + [1] * 200 + [0] * 120 + [3] * 60 + [4] * 20
    # 预置 OUE 的 p q 参数用于去偏估计
    base_metadata = {"p": mechanism.p, "q": mechanism.q, "mechanism": mechanism.mechanism_id}

    # 生成报告并聚合输出
    reports = [
        mechanism.generate_report(
            encoder.encode(value),
            user_id=str(idx),
            metadata=dict(base_metadata),
        )
        for idx, value in enumerate(data)
    ]

    aggregator = FrequencyAggregator(num_categories=length, mechanism="oue")
    estimate = aggregator.aggregate(reports)
    point = np.asarray(estimate.point, dtype=float)

    # 校验分布形状与主类索引
    assert point.shape == (length,)
    assert float(point.sum()) == pytest.approx(1.0, abs=1e-6)
    assert int(np.argmax(point)) == 2
    assert point[2] > 0.4


def test_local_laplace_mean_pipeline() -> None:
    # 验证本地 Laplace 与均值聚合器的协同
    clip_range = (0.0, 10.0)
    epsilon = 5.0
    mechanism = LocalLaplaceMechanism(
        epsilon=epsilon,
        clip_range=clip_range,
        rng=np.random.default_rng(11),
    )
    data = np.linspace(0.0, 10.0, 101)
    # 生成扰动报告用于均值估计
    reports = [
        mechanism.generate_report(float(value), user_id=str(idx), metadata={"clip_range": clip_range})
        for idx, value in enumerate(data)
    ]

    # 计算噪声方差并聚合均值
    scale = (clip_range[1] - clip_range[0]) / epsilon
    noise_variance = 2.0 * scale * scale
    aggregator = MeanAggregator(clip_range=clip_range, noise_variance=noise_variance)
    estimate = aggregator.aggregate(reports)

    # 校验均值误差与报告元数据
    assert abs(estimate.point - float(np.mean(data))) < 1.0
    assert estimate.metadata["n_reports"] == len(data)


def test_frequency_aggregator_rejects_mismatched_vectors() -> None:
    # 验证向量长度不一致会触发参数校验异常
    reports = [
        LDPReport(user_id="u1", mechanism_id="oue", encoded=[1, 0], epsilon=1.0),
        LDPReport(user_id="u2", mechanism_id="oue", encoded=[1, 0, 0], epsilon=1.0),
    ]
    aggregator = FrequencyAggregator()
    # 校验聚合时抛出异常
    with pytest.raises(ParamValidationError):
        aggregator.aggregate(reports)
