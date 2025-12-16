"""
Unit tests for LDP continuous mechanisms.
"""
# 说明：连续数值型本地差分隐私机制的行为校验单元测试，包括 Laplace/Gaussian/Duchi 与近似实现的 Piecewise（剪裁+均匀噪声）。
# 覆盖：
# - 验证连续型机制在标量与数组输入下的输出类型与形状一致性
# - 验证机制对输入裁剪区间的尊重程度（带噪声时通过分位数近似检查）
# - 验证局部噪声在多个样本上的均值是否围绕原始输入值居中
# - 验证本地高斯机制中 sigma 是否被正确校准
# - 验证 Duchi 机制输出恒为 ±1 的编码形式
# - 验证 Duchi 机制的输出分布是否符合其理论概率

from __future__ import annotations

import numpy as np
import pytest

from dplib.ldp.mechanisms.continuous.duchi import DuchiMechanism
from dplib.ldp.mechanisms.continuous.gaussian_local import LocalGaussianMechanism
from dplib.ldp.mechanisms.continuous.laplace_local import LocalLaplaceMechanism
from dplib.ldp.mechanisms.continuous.piecewise import PiecewiseMechanism


@pytest.mark.parametrize(
    "mech_cls, kwargs, x",
    [
        (LocalLaplaceMechanism, {"epsilon": 1.0, "clip_range": (0.0, 1.0)}, 0.5),
        (LocalGaussianMechanism, {"epsilon": 1.0, "delta": 1e-5, "clip_range": (0.0, 1.0)}, 0.5),
        (PiecewiseMechanism, {"epsilon": 1.0}, 0.5),
        (DuchiMechanism, {"epsilon": 1.0}, 0.1),
    ],
)
def test_continuous_mechanism_output_type_and_shape(mech_cls, kwargs, x) -> None:
    # 验证连续型 LDP 机制在标量与数组输入时输出为浮点并保持与输入相同形状
    mech = mech_cls(**kwargs)
    out_scalar = mech.randomise(x)
    assert isinstance(out_scalar, (float, np.floating))

    arr = np.array([x, x])
    out_arr = mech.randomise(arr)
    out_arr = np.asarray(out_arr)
    assert out_arr.shape == arr.shape


@pytest.mark.parametrize(
    "mech_cls, kwargs, clip_range, margin",
    [
        (LocalLaplaceMechanism, {"epsilon": 1.0, "clip_range": (0.0, 1.0)}, (0.0, 1.0), 6.0),
        (LocalGaussianMechanism, {"epsilon": 1.0, "delta": 1e-5, "clip_range": (0.0, 1.0)}, (0.0, 1.0), 15.0),
        (PiecewiseMechanism, {"epsilon": 1.0}, (-10.0, 10.0), 0.0),
        (DuchiMechanism, {"epsilon": 1.0}, (-1.0, 1.0), 0.0),
    ],
)
def test_continuous_mechanism_respects_clipping(mech_cls, kwargs, clip_range, margin) -> None:
    # 通过大量采样与分位数检查连续型机制是否遵守指定裁剪区间或在可接受边界内波动
    mech = mech_cls(**kwargs)
    lower, upper = clip_range
    samples = []
    for v in [-10.0, 0.0, 10.0]:
        outs = mech.randomise(np.array([v] * 200))
        samples.extend(np.asarray(outs, dtype=float).tolist())
    samples_arr = np.array(samples)
    if margin == 0.0:
        assert np.all(samples_arr >= lower) and np.all(samples_arr <= upper)
    else:
        lo_pct = np.percentile(samples_arr, 1)
        hi_pct = np.percentile(samples_arr, 99)
        assert lo_pct >= lower - margin
        assert hi_pct <= upper + margin


@pytest.mark.parametrize(
    "mech_cls, kwargs, x0",
    [
        (LocalLaplaceMechanism, {"epsilon": 2.0, "clip_range": (-1.0, 1.0)}, 0.2),
        (LocalGaussianMechanism, {"epsilon": 2.0, "delta": 1e-5, "clip_range": (-1.0, 1.0)}, -0.3),
        (PiecewiseMechanism, {"epsilon": 1.0}, 0.7),
    ],
)
def test_continuous_mechanism_noise_centered(mech_cls, kwargs, x0) -> None:
    # 检查在固定输入重复采样下输出均值是否接近原始值以验证噪声是否近似零均值
    mech = mech_cls(**kwargs)
    n = 8000
    outs = mech.randomise(np.array([x0] * n))
    mean_out = float(np.asarray(outs).mean())
    assert mean_out == pytest.approx(x0, abs=0.2)


def test_local_gaussian_sigma_calibration() -> None:
    # 验证本地高斯机制中 sigma 是否根据 (epsilon, delta) 和敏感度被正确校准
    epsilon, delta = 1.0, 1e-5
    clip_range = (-2.0, 2.0)
    sensitivity = clip_range[1] - clip_range[0]
    mech = LocalGaussianMechanism(epsilon=epsilon, delta=delta, clip_range=clip_range)
    # 预期 sigma = (sensitivity * sqrt(2 * log(1.25 / delta))) / epsilon
    expected_sigma = (sensitivity * np.sqrt(2 * np.log(1.25 / delta))) / epsilon
    assert mech.sigma == pytest.approx(expected_sigma)


def test_duchi_outputs_pm_one() -> None:
    # 验证 Duchi 机制在合法输入范围内的每次输出都严格落在 {-1.0, 1.0}
    mech = DuchiMechanism(epsilon=1.0)
    outs = [mech.randomise(x) for x in np.linspace(-1, 1, 11)]
    for o in outs:
        assert o in (-1.0, 1.0)


@pytest.mark.parametrize("x", [-1.0, 0, 0.5, 1.0])
def test_duchi_output_distribution(x: float) -> None:
    # 验证 Duchi 机制的输出分布是否符合其理论概率
    epsilon = 1.0
    mech = DuchiMechanism(epsilon=epsilon)
    n_trials = 10000
    # 多次调用 randomise 并收集结果
    outputs = np.array([mech.randomise(x) for _ in range(n_trials)])
    # 计算 +1 结果的比例
    empirical_prob_positive = np.sum(outputs == 1.0) / n_trials
    # 从机制中获取理论概率
    theoretical_prob_positive = mech._p_positive(x)
    assert empirical_prob_positive == pytest.approx(theoretical_prob_positive, abs=0.02)
