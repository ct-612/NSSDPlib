"""
Unit tests for CDP reporting and synthetic data helpers.
"""
# 说明：CDP 报告与合成数据生成器的集成测试
# 覆盖：
# - PrivacyReport 与 UtilityReport 的构建与序列化
# - Marginal/Bayesian/Copula/GAN 生成器的拟合与采样
from __future__ import annotations

import pytest

from dplib.cdp.analytics.reporting.privacy_report import PrivacyReport
from dplib.cdp.analytics.reporting.utility_report import UtilityReport
from dplib.cdp.analytics.synthetic_data.bayesian import BayesianNetworkGenerator
from dplib.cdp.analytics.synthetic_data.copula import CopulaGenerator
from dplib.cdp.analytics.synthetic_data.gan import DPSyntheticGAN
from dplib.cdp.analytics.synthetic_data.marginal import MarginalGenerator
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.data import ContinuousDomain, Dataset, DiscreteDomain


def test_privacy_report_from_cdp_accountant() -> None:
    # 验证从会计器生成隐私报告并包含事件明细
    accountant = CDPPrivacyAccountant(total_epsilon=1.0, total_delta=1e-6)
    # 构造带标签的隐私事件用于报告
    accountant.add_composed_event(
        [{"epsilon": 0.3, "delta": 1e-6}],
        description="test",
        metadata={"event_id": "evt-1", "tags": {"stage": "integration"}},
    )

    # 生成报告并校验预算快照与元数据
    report = PrivacyReport.from_accountant(accountant)
    assert report.total_budget is not None
    assert report.spent.epsilon == pytest.approx(0.3)
    assert len(report.events) == 1
    assert report.events[0].event_id == "evt-1"
    assert report.events[0].tags["stage"] == "integration"
    assert len(report.timeline) == 1
    assert report.to_json()


def test_utility_report_from_samples() -> None:
    # 验证效用报告能基于样本生成摘要与曲线
    # 构造包含真值与噪声的样本集合
    samples = [
        {
            "query_id": "count",
            "mechanism": "laplace",
            "epsilon": 1.0,
            "delta": 0.0,
            "true_value": 10.0,
            "noisy_values": [9.5, 10.5, 10.1],
        },
        {
            "query_id": "sum",
            "mechanism": "laplace",
            "epsilon": 1.0,
            "delta": 0.0,
            "true_value": 20.0,
            "noisy_values": [19.0, 20.2, 20.8],
        },
    ]
    # 生成报告并校验摘要与曲线输出
    report = UtilityReport.from_samples(samples)
    assert report.global_summary is not None
    assert "count" in report.per_query_summary
    curves = report.get_error_vs_epsilon(metric="mse")
    assert curves
    assert report.to_json()


def test_marginal_generator_fit_and_sample() -> None:
    # 验证边缘生成器拟合与采样的端到端流程
    # 构造离散域与样本记录
    domain = {
        "color": DiscreteDomain(["red", "blue"]),
        "shape": DiscreteDomain(["square", "circle"]),
    }
    records = [
        {"color": "red", "shape": "square"},
        {"color": "blue", "shape": "circle"},
        {"color": "red", "shape": "circle"},
        {"color": "blue", "shape": "square"},
    ]
    # 使用固定种子拟合并采样
    generator = MarginalGenerator(domain=domain, epsilon=1.0, seed=123, marginals=[("color",), ("shape",)])
    generator.fit(records)
    sample = generator.sample(5)

    assert isinstance(sample, Dataset)
    assert len(sample) == 5
    assert set(sample.to_list()[0].keys()) == {"color", "shape"}


def test_bayesian_generator_fit_and_sample() -> None:
    # 验证贝叶斯网络生成器在固定结构下拟合采样
    # 构造离散域与结构先验
    domain = {
        "color": DiscreteDomain(["red", "blue"]),
        "shape": DiscreteDomain(["square", "circle"]),
    }
    records = [
        {"color": "red", "shape": "square"},
        {"color": "blue", "shape": "circle"},
        {"color": "red", "shape": "circle"},
        {"color": "blue", "shape": "square"},
    ]
    structure = [("shape", ("color",))]
    # 基于给定结构拟合并采样
    generator = BayesianNetworkGenerator(domain=domain, epsilon=1.0, seed=7, structure=structure)
    generator.fit(records)
    sample = generator.sample(4)

    assert isinstance(sample, Dataset)
    assert len(sample) == 4
    assert set(sample.to_list()[0].keys()) == {"color", "shape"}


def test_copula_generator_fit_and_sample() -> None:
    # 验证 Copula 生成器能拟合并采样连续与离散特征
    # 构造连续与离散混合域
    domain = {
        "height": ContinuousDomain(minimum=0.0, maximum=2.0),
        "weight": ContinuousDomain(minimum=0.0, maximum=100.0),
        "group": DiscreteDomain(["a", "b"]),
    }
    records = [
        {"height": 1.6, "weight": 60.0, "group": "a"},
        {"height": 1.7, "weight": 70.0, "group": "b"},
        {"height": 1.5, "weight": 55.0, "group": "a"},
        {"height": 1.8, "weight": 80.0, "group": "b"},
    ]
    # 使用固定种子拟合并采样
    generator = CopulaGenerator(domain=domain, epsilon=1.0, delta=1e-6, seed=21)
    generator.fit(records)
    sample = generator.sample(3)

    assert isinstance(sample, Dataset)
    assert len(sample) == 3
    assert set(sample.to_list()[0].keys()) == {"height", "weight", "group"}


def test_gan_generator_fit_and_sample() -> None:
    # 验证 GAN 生成器在 MVP 路径下完成拟合与采样
    # 构造连续域样本
    domain = {
        "x": ContinuousDomain(minimum=0.0, maximum=1.0),
        "y": ContinuousDomain(minimum=0.0, maximum=1.0),
    }
    records = [
        {"x": 0.1, "y": 0.2},
        {"x": 0.4, "y": 0.8},
        {"x": 0.9, "y": 0.3},
    ]
    # 使用固定种子运行拟合与采样
    generator = DPSyntheticGAN(domain=domain, epsilon=1.0, seed=11)
    generator.fit(records)
    sample = generator.sample(2)

    assert isinstance(sample, Dataset)
    assert len(sample) == 2
    assert set(sample.to_list()[0].keys()) == {"x", "y"}
