"""
Unit tests for synthetic data generators based on marginals, Bayesian networks, copulas, and DP-GAN.
"""
# 说明：合成数据生成器（边际法、贝叶斯网、Copula 与 DP-GAN）端到端行为的单元测试。
# 覆盖：
# - 不同类型生成器的 fit 与 sample 全流程行为
# - get_privacy_spent 对已用隐私预算的聚合查询结果
# - 不同 epsilon 配置下隐私花费是否与预期一致

from __future__ import annotations

from dplib.cdp.analytics.synthetic_data.bayesian import BayesianNetworkGenerator
from dplib.cdp.analytics.synthetic_data.copula import CopulaGenerator
from dplib.cdp.analytics.synthetic_data.gan import DPSyntheticGAN
from dplib.cdp.analytics.synthetic_data.marginal import MarginalGenerator
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.data import Dataset
from dplib.core.data.domain import ContinuousDomain, DiscreteDomain
from dplib.core.privacy import PrivacyGuarantee


def _simple_accountant() -> CDPPrivacyAccountant:
    # 构造一个具有固定全局预算的 CDPPrivacyAccountant 供各生成器测试复用
    return CDPPrivacyAccountant(total_epsilon=10.0, total_delta=1e-3)


def test_marginal_generator_fit_and_sample() -> None:
    # 验证边际直方图生成器的拟合与采样流程以及隐私花费查询是否符合预期
    domain = {"color": DiscreteDomain(["red", "blue"])}
    records = [{"color": "red"}, {"color": "blue"}, {"color": "red"}]
    accountant = _simple_accountant()
    gen = MarginalGenerator(domain=domain, epsilon=1.0, accountant=accountant, seed=0)

    gen.fit(Dataset.from_records(records))
    sampled = gen.sample(4, as_dataset=True)

    assert len(sampled) == 4
    assert set(sampled[0].keys()) == {"color"}
    spent = gen.get_privacy_spent()
    assert isinstance(spent, PrivacyGuarantee)
    assert spent.epsilon == 1.0


def test_bayesian_generator_fit_and_sample() -> None:
    # 验证贝叶斯网络生成器在给定结构下能生成包含所有节点的记录并正确消耗 epsilon
    domain = {
        "x": DiscreteDomain([0, 1]),
        "y": DiscreteDomain([0, 1]),
    }
    structure = [("y", ("x",))]
    records = [
        {"x": 0, "y": 0},
        {"x": 0, "y": 1},
        {"x": 1, "y": 1},
    ]
    accountant = _simple_accountant()
    gen = BayesianNetworkGenerator(
        domain=domain,
        epsilon=0.8,
        structure=structure,
        accountant=accountant,
        seed=1,
    )

    gen.fit(Dataset.from_records(records))
    sampled = gen.sample(3, as_dataset=True)

    assert len(sampled) == 3
    assert set(sampled[0].keys()) == {"x", "y"}
    spent = gen.get_privacy_spent()
    assert isinstance(spent, PrivacyGuarantee)
    assert spent.epsilon == 0.8


def test_dp_gan_stub_fit_and_sample() -> None:
    # 验证 DP-GAN 占位实现可完成基本拟合与采样并将 epsilon 记入隐私会计
    domain = {"f1": DiscreteDomain([0, 1]), "f2": DiscreteDomain([0, 1])}
    records = [{"f1": 0, "f2": 1}, {"f1": 1, "f2": 0}]
    accountant = _simple_accountant()
    gen = DPSyntheticGAN(domain=domain, epsilon=1.2, accountant=accountant, seed=2)

    gen.fit(Dataset.from_records(records))
    sampled = gen.sample(5, as_dataset=True)

    assert len(sampled) == 5
    assert set(sampled[0].keys()) == {"f1", "f2"}
    spent = gen.get_privacy_spent()
    assert isinstance(spent, PrivacyGuarantee)
    assert spent.epsilon == 1.2


def test_copula_generator_fit_and_sample() -> None:
    # 验证 Copula 生成器对连续特征拟合边缘与协方差后能按域字段返回合成记录
    domain = {"v": ContinuousDomain(minimum=0.0, maximum=10.0)}
    records = [{"v": 1.0}, {"v": 2.5}, {"v": 3.5}, {"v": 4.0}]
    accountant = _simple_accountant()
    gen = CopulaGenerator(domain=domain, epsilon=0.5, accountant=accountant, seed=3)

    gen.fit(Dataset.from_records(records))
    sampled = gen.sample(6, as_dataset=True)

    assert len(sampled) == 6
    assert set(sampled[0].keys()) == {"v"}
    spent = gen.get_privacy_spent()
    assert isinstance(spent, PrivacyGuarantee)
    assert spent.epsilon == 0.5
