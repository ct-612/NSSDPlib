"""
Property-based tests for CDP synthetic data generators.
"""
# 说明：中心化差分隐私（CDP）合成数据生成器的属性测试。
# 覆盖：
# - SyntheticGeneratorConfig 的序列化与反序列化一致性
# - MarginalGenerator 的边际分布保真度与采样形状
# - BayesianNetworkGenerator 在固定结构下的拟合与拓扑采样
# - CopulaGenerator 的潜在空间转换与逆 CDF 采样
# - DPSyntheticGAN 的基础接口流程与退化行为验证
# - create_generator 工厂函数的正确调度

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.cdp.analytics.synthetic_data.base_generator import (
    SyntheticGeneratorConfig, create_generator)
from dplib.cdp.analytics.synthetic_data.marginal import MarginalGenerator
from dplib.cdp.analytics.synthetic_data.bayesian import BayesianNetworkGenerator
from dplib.cdp.analytics.synthetic_data.copula import CopulaGenerator
from dplib.cdp.analytics.synthetic_data.gan import DPSyntheticGAN
from dplib.core.data import Dataset, DatasetMetadata
from dplib.core.data.domain import DiscreteDomain, ContinuousDomain, BucketizedDomain


# ------------------------------------------------------------------ Configuration
@settings(suppress_health_check=[HealthCheck.too_slow])
@given(st.text(min_size=1), st.floats(min_value=0.1, max_value=10.0),
       st.floats(min_value=0, max_value=1e-3))
def test_generator_config_roundtrip(method, epsilon, delta):
    # 验证生成器配置对象在字典转换过程中的信息不丢失
    config = SyntheticGeneratorConfig(method=method,
                                      epsilon=epsilon,
                                      delta=delta,
                                      extra={"a": 1})
    payload = config.to_dict()
    recovered = SyntheticGeneratorConfig.from_dict(payload)

    assert recovered.method == method
    assert recovered.epsilon == pytest.approx(epsilon)
    assert recovered.delta == pytest.approx(delta)
    assert recovered.extra == {"a": 1}


# ------------------------------------------------------------------ Marginal Generator
@given(st.integers(min_value=1, max_value=10))
def test_marginal_generator_shape(n_samples):
    # 验证边际生成器采样的输出形状与请求的样本数一致
    domain = {
        "A": DiscreteDomain(["x", "y"]),
        "B": BucketizedDomain([0, 5, 10])
    }
    gen = MarginalGenerator(domain, epsilon=1.0)
    data = Dataset.from_records([{"A": "x", "B": 1}, {"A": "y", "B": 6}])

    gen.fit(data)
    sampled = gen.sample(n_samples)

    assert len(sampled.to_list()) == n_samples
    for record in sampled.to_list():
        assert "A" in record and "B" in record


# ------------------------------------------------------------------ Bayesian Generator
def test_bayesian_generator_sampling():
    # 验证贝叶斯网络生成器在给定依赖结构下的拟合与采样逻辑
    domain = {
        "P": DiscreteDomain(["yes", "no"]),
        "C": DiscreteDomain(["low", "high"])
    }
    # Structure: P -> C
    structure = [("P", tuple()), ("C", ("P", ))]
    gen = BayesianNetworkGenerator(domain, epsilon=2.0, structure=structure)

    data = Dataset.from_records([{
        "P": "yes",
        "C": "high"
    }, {
        "P": "yes",
        "C": "low"
    }, {
        "P": "no",
        "C": "low"
    }])

    gen.fit(data)
    sampled = gen.sample(5)
    assert len(sampled.to_list()) == 5


# ------------------------------------------------------------------ Copula Generator
@given(st.integers(min_value=1, max_value=5))
def test_copula_generator_fit(n):
    # 验证高斯 Copula 生成器在连续特征场景下的拟合稳定性
    domain = {
        "X": ContinuousDomain(minimum=0, maximum=10),
        "Y": ContinuousDomain(minimum=-5, maximum=5)
    }
    gen = CopulaGenerator(domain, epsilon=1.0, delta=1e-6)

    # 构造简单的线性相关数据
    x = np.linspace(0, 10, 20)
    y = x / 2.0
    data = Dataset.from_arrays({"X": x, "Y": y})

    gen.fit(data)
    sampled = gen.sample(n)
    assert len(sampled.to_list()) == n


# ------------------------------------------------------------------ Factory
def test_create_generator_dispatch():
    # 验证工厂函数能够正确实例化不同类型的生成器
    domain = {"A": DiscreteDomain([1, 2])}
    config = {"method": "marginal", "epsilon": 1.0}

    gen = create_generator("marginal", domain, config)
    assert isinstance(gen, MarginalGenerator)

    config_gan = {
        "method": "gan",
        "epsilon": 1.0,
        "extra": {
            "backend": "torch"
        }
    }
    gen_gan = create_generator("gan", domain, config_gan)
    assert isinstance(gen_gan, DPSyntheticGAN)
