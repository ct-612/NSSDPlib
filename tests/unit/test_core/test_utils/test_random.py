"""
Unit tests for random number generation helpers.
"""
# 说明：随机数生成工具与 RNG 池（RNGPool）的单元测试。
# 覆盖：
# - create_rng / reseed_rng：基于种子的 RNG 创建与重置是否可复现
# - split_rng：从单一 RNG 派生多个子生成器，并验证子生成器样本相互独立
# - sample_noise：按分布名称采样拉普拉斯 / 高斯噪声，以及对未知分布抛出错误
# - RNGPool：基于 base_seed 初始化与 reseed 后的采样可重复性

import numpy as np
import pytest

from dplib.core.utils import RNGPool, create_rng, reseed_rng, sample_noise, split_rng


def test_create_rng_and_reseed() -> None:
    # 验证使用同一 seed 创建并重置 RNG 后，生成的随机数序列具有可复现性
    rng = create_rng(42)
    first = rng.normal()
    reseed_rng(rng, 42)
    assert rng.normal() == pytest.approx(first)


def test_split_rng_produces_independent_generators() -> None:
    # 验证 split_rng 产生的多个子生成器数量正确，且各自样本值不同（相互独立）
    rng = create_rng(123)
    children = split_rng(rng, 3)
    assert len(children) == 3
    samples = [child.normal() for child in children]
    assert len(set(samples)) == len(samples)


def test_sample_noise_distributions() -> None:
    # 验证 sample_noise 针对不同分布名称返回预期形状的样本，并对未知分布抛出异常
    rng = create_rng(0)
    laplace = sample_noise(rng, "laplace", scale=1.0, size=10)
    assert laplace.shape == (10,)
    gaussian = sample_noise(rng, "gaussian", scale=1.0, size=5)
    assert gaussian.shape == (5,)
    with pytest.raises(ValueError):
        sample_noise(rng, "unknown", scale=1.0)


def test_rng_pool_reseed() -> None:
    # 验证 RNGPool 在相同 base_seed 下 reseed 后，采样结果与初始行为保持一致
    pool = RNGPool(base_seed=1, pool_size=2)
    a_sample_before = pool.get(0).normal()
    pool.reseed(1)
    a_sample_after = pool.get(0).normal()
    assert pytest.approx(a_sample_before) == a_sample_after
