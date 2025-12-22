"""
Property-based tests for the Central Differential Privacy (CDP) mechanisms.
"""
# 说明：中心化差分隐私（CDP）机制（Laplace, Gaussian, Geometric, Staircase, Vector, Exponential）的属性测试。
# 覆盖：
# - 连续型机制（拉普拉斯、高斯）在确定性种子下的输出可复现性
# - 离散型机制（几何机制）的整数保持特性与校准单调性
# - 阶梯机制在合法 gamma 参数下的配置拦截
# - 向量机制的形状保持与多范数下的噪声缩放
# - 指数机制的候选项选出合法性与效用单调性

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.cdp.mechanisms.gaussian import GaussianMechanism
from dplib.cdp.mechanisms.geometric import GeometricMechanism
from dplib.cdp.mechanisms.staircase import StaircaseMechanism
from dplib.cdp.mechanisms.vector import VectorMechanism
from dplib.cdp.mechanisms.exponential import ExponentialMechanism
from dplib.core.privacy.base_mechanism import ValidationError


# ---------------------------------------------------------------- Reproducibility
@given(st.integers(0, 1000), st.floats(min_value=-100, max_value=100))
def test_laplace_reproducibility(seed, val):
    # 验证拉普拉斯机制在相同种子下产生完全一致的加噪结果，保证结果可复现
    m1 = LaplaceMechanism(epsilon=1.0, rng=seed)
    m1.calibrate()
    res1 = m1.randomise(val)

    m2 = LaplaceMechanism(epsilon=1.0, rng=seed)
    m2.calibrate()
    res2 = m2.randomise(val)

    assert res1 == res2


@given(st.integers(0, 1000), st.floats(min_value=-100, max_value=100))
def test_gaussian_reproducibility(seed, val):
    # 验证高斯机制在固定种子下能生成稳定确定的噪声值，支持审计与测试
    m1 = GaussianMechanism(epsilon=1.0, delta=1e-5, rng=seed)
    m1.calibrate()
    res1 = m1.randomise(val)

    m2 = GaussianMechanism(epsilon=1.0, delta=1e-5, rng=seed)
    m2.calibrate()
    res2 = m2.randomise(val)

    assert res1 == res2


# ---------------------------------------------------------------- Output Properties
@given(
    st.lists(st.floats(min_value=-100, max_value=100), min_size=1,
             max_size=10))
def test_laplace_output_shape(vals):
    # 验证批量拉普拉斯扰动后，输出列表的元素个数与容器类型保持不变
    m = LaplaceMechanism(epsilon=1.0)
    m.calibrate()
    res = m.randomise(vals)
    assert len(res) == len(vals)
    assert isinstance(res, list)


@given(
    st.lists(st.floats(min_value=-100, max_value=100), min_size=1,
             max_size=10))
def test_gaussian_output_shape(vals):
    # 验证高斯机制对列表输入进行加噪后，输出的维度结构与输入完全对齐
    m = GaussianMechanism(epsilon=1.0, delta=1e-5)
    m.calibrate()
    res = m.randomise(vals)
    assert len(res) == len(vals)
    assert isinstance(res, list)


def test_laplace_scalar_output():
    # 确保对 Python 原生标量值加噪后返回的仍是非 numpy 封装的 float 类型
    m = LaplaceMechanism(epsilon=1.0)
    m.calibrate()
    res = m.randomise(1.0)
    assert isinstance(res, float)


# ---------------------------------------------------------------- Geometric Mechanism
@given(st.integers(min_value=-100, max_value=100))
def test_geometric_integer_preservation(val):
    # 验证几何机制在对整数输入加噪后其结果严格保持整数类型而不退化为浮点数
    m = GeometricMechanism(epsilon=1.0)
    m.calibrate()
    res = m.randomise(val)
    assert isinstance(res, int)
    # 对于 numpy 整数输入，输出也应保持 numpy 整数类型
    res_np = m.randomise(np.int64(val))
    assert np.issubdtype(np.array(res_np).dtype, np.integer)


@given(st.floats(min_value=0.1, max_value=10.0))
def test_geometric_calibration_monotonicity(epsilon):
    # 验证几何机制的衰减因子随 epsilon 增大而具有单调性，符合理论噪声衰减规律
    m1 = GeometricMechanism(epsilon=epsilon)
    m1.calibrate()

    m2 = GeometricMechanism(epsilon=epsilon * 2)
    m2.calibrate()

    # epsilon 越大 -> rate = eps/sens 越大 -> decay = exp(-rate) 越小
    assert m2.decay < m1.decay
    # 成功概率 success_prob = 1 - decay，故 epsilon 越大成功概率越大
    assert m2.success_prob > m1.success_prob


# ---------------------------------------------------------------- Staircase Mechanism
@given(st.floats(min_value=-1.0, max_value=2.0))
def test_staircase_gamma_constraint(gamma):
    # 验证阶梯机制构造函数对 gamma 值的合法范围 [0, 1] 做出的强制性参数校验
    if 0.0 <= gamma <= 1.0:
        StaircaseMechanism(gamma=gamma)
    else:
        with pytest.raises(ValidationError):
            StaircaseMechanism(gamma=gamma)


@given(st.floats(min_value=0.0, max_value=100.0))
def test_staircase_non_negativity_distribution(val):
    # 验证阶梯机制对浮点输入执行加噪后的输出类型与基本运行状态
    # 这里主要测试机制运行无报错且输出是浮点数
    m = StaircaseMechanism(epsilon=10.0)  # High epsilon -> Low noise
    m.calibrate()
    res = m.randomise(val)
    assert isinstance(res, float)


# ---------------------------------------------------------------- Vector Mechanism
@given(st.lists(st.floats(), min_size=1, max_size=10),
       st.integers(min_value=1, max_value=3))
def test_vector_shape_preservation(prefix, dims):
    # 验证多维向量机制在处理矩阵或张量输入时能精准保持 NumPy 数组的形状
    # 构造一个 shape 为 (len(prefix), dims) 的 2D 数组
    arr = np.array([prefix] * dims).T
    m = VectorMechanism(epsilon=1.0)
    m.calibrate()
    res = m.randomise(arr)
    assert res.shape == arr.shape
    assert isinstance(res, np.ndarray)


@given(st.floats(min_value=0.1, max_value=10.0))
def test_vector_norm_scaling(eps):
    # 验证向量机制在不同范数约束下的噪声规模推导是否符合预期的数学定义
    m_l1 = VectorMechanism(epsilon=eps, norm="l1", distribution="laplace")
    m_l1.calibrate(sensitivity=1.0)

    m_l2 = VectorMechanism(epsilon=eps, norm="l2", distribution="laplace")
    m_l2.calibrate(sensitivity=1.0)

    # Laplace 机制下，scale = sensitivity / epsilon
    # 两者 scale 应相等，这里验证机制正确设置了 norm 元数据且参数计算符合预期
    assert m_l1.scale == pytest.approx(m_l2.scale)
    assert m_l1._meta["norm"] == "l1"
    assert m_l2._meta["norm"] == "l2"


# ---------------------------------------------------------------- Exponential Mechanism
@given(
    st.lists(st.integers(), min_size=2, max_size=10, unique=True).map(tuple))
def test_exponential_selection_validity(candidates):
    # 验证指数机制的索引选出结果必须严格存在于初始预定义的候选集中
    # 使用简单的效用函数：score(x) = x
    def utility(x, c):
        return float(c)

    m = ExponentialMechanism(epsilon=1.0,
                             candidates=candidates,
                             utility_fn=utility)
    m.calibrate()

    # 因为 utility_fn 需要 value 参数，即使它可能不被使用
    res = m.randomise(None)
    assert res in candidates


@given(st.floats(min_value=1.0, max_value=10.0))  # Epsilon
def test_exponential_utility_monotonicity(epsilon):
    # 验证指数机制的概率分布随效用分数增大而具有单调上升特性，确保采样倾向性
    # 场景：两个候选 A (score=0), B (score=10)
    candidates = ("A", "B")
    scores = (0.0, 10.0)

    m = ExponentialMechanism(epsilon=epsilon, candidates=candidates)
    m.calibrate()

    # 运行一次 randomise 并通过访问内部 _last_probabilities 验证高分候选项概率更大
    m.randomise(None, scores=scores)

    probs = m._last_probabilities
    assert probs is not None
    # 候选 B (index 1) 的分数远高于 A (index 0)，所以 probs[1] 应该大于 probs[0]
    assert probs[1] > probs[0]
    # 并且 probs 之和应为 1
    assert np.sum(probs) == pytest.approx(1.0)
