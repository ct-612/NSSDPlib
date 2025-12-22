"""
Property-based tests for the Local Differential Privacy (LDP) mechanisms.
"""
# 说明：本地差分隐私（LDP）机制（GRR, OUE, OLH, Rappor, Duchi, Piecewise, Local Laplace/Gaussian）的属性测试。
# 覆盖：
# - 离散机制（GRR, OLH）的定义域约束、概率守恒与索引逆映射
# - 位向量机制（OUE, Rappor）的输出比特结构、长度一致性与参数推排
# - 连续机制（Local Laplace/Gaussian）的输出截断与类型保持
# - 有界机制（Duchi, Piecewise）的输出离散性与取值范围约束
# - 异常输入与非法邻域参数的自动校验

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.ldp.mechanisms.discrete.grr import GRRMechanism
from dplib.ldp.mechanisms.discrete.oue import OUEMechanism
from dplib.ldp.mechanisms.discrete.olh import OLHMechanism
from dplib.ldp.mechanisms.continuous.laplace_local import LocalLaplaceMechanism
from dplib.ldp.mechanisms.continuous.gaussian_local import LocalGaussianMechanism
from dplib.ldp.mechanisms.continuous.duchi import DuchiMechanism
from dplib.ldp.mechanisms.continuous.piecewise import PiecewiseMechanism
from dplib.ldp.mechanisms.discrete.rappor import RAPPORMechanism
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- GRR Mechanism
@given(
    st.lists(st.integers(), min_size=2, max_size=10, unique=True).map(tuple))
def test_grr_domain_constraint(categories):
    # 验证 GRR 机制的随机化输出结果 must belong to the predefined discrete set
    epsilon = 1.0
    m = GRRMechanism(epsilon=epsilon, categories=categories)

    # 选择合法 input 并验证输出成员身份
    val = categories[0]
    res = m.randomise(val)

    assert res in categories


@given(st.integers(min_value=2, max_value=100),
       st.floats(min_value=0.1, max_value=5.0))
def test_grr_probability_conservation(domain_size, epsilon):
    # 验证 GRR 机制内部计算的真实值采样概率与噪声值采样概率之和满足归一化守恒
    m = GRRMechanism(epsilon=epsilon, domain_size=domain_size)

    total_prob = m.prob_true + (domain_size - 1) * m.prob_false
    assert total_prob == pytest.approx(1.0)


@given(
    st.lists(st.integers(), min_size=2, max_size=10, unique=True).map(tuple))
def test_grr_mapping_invertibility(categories):
    # 验证 GRR 机制内部实现的类别到索引映射逻辑具备双向可逆性
    m = GRRMechanism(epsilon=1.0, categories=categories)

    for val in categories:
        idx = m._to_index(val)
        recovered = m._from_index(idx)
        assert recovered == val


@given(st.integers(min_value=2, max_value=10))
def test_grr_invalid_input(domain_size):
    # 验证 GRR 机制能正确识别并拒绝对离散定义域之外的非法索引执行加噪请求
    m = GRRMechanism(epsilon=1.0, domain_size=domain_size)

    with pytest.raises(ParamValidationError):
        m.randomise(domain_size)  # 索引越界

    with pytest.raises(ParamValidationError):
        m.randomise(-1)


# ---------------------------------------------------------------- OUE Mechanism
@given(st.lists(st.integers(min_value=0, max_value=1), min_size=1,
                max_size=20))
def test_oue_bit_structure(bits):
    # 验证 OUE 机制生成的后置隐私响应是一个仅包含 0/1 数值的位序列容器
    m = OUEMechanism(epsilon=1.0)
    # 传入符合要求的位列表
    res = m.randomise(bits)

    assert isinstance(res, list)
    assert all(x in (0, 1) for x in res)
    assert len(res) == len(bits)


@given(st.integers(min_value=1, max_value=20))
def test_oue_dimension_consistency(length):
    # 验证 OUE 机制在执行翻转变换后不会改变输入向量的原始维度大小
    m = OUEMechanism(epsilon=1.0)
    bits = [0] * length
    res = m.randomise(bits)
    assert len(res) == length


@given(st.floats(min_value=0.1, max_value=5.0))
def test_oue_parameter_derivation(epsilon):
    # 验证 OUE 机制在仅通过预算参数初始化时，能正确根据算法定义导出 p 与 q 翻转概率
    # p 理论值为 0.5, q = 1 / (exp(eps) + 1)
    m = OUEMechanism(epsilon=epsilon)
    assert m.p == 0.5
    expected_q = 1.0 / (np.exp(epsilon) + 1.0)
    assert m.q == pytest.approx(expected_q)


# ---------------------------------------------------------------- OLH Mechanism
@given(st.integers(min_value=0, max_value=99),
       st.integers(min_value=2, max_value=20))
def test_olh_hash_range_constraint(val, hash_range):
    # 验证 OLH 机制生成的哈希索引输出严格被限制在指定的哈希桶取值范围内
    m = OLHMechanism(epsilon=1.0, domain_size=val + 10, hash_range=hash_range)
    res = m.randomise(val)

    assert isinstance(res, (int, np.integer))
    assert 0 <= res < hash_range


@given(st.floats(min_value=0.1, max_value=5.0),
       st.integers(min_value=2, max_value=10))
def test_olh_parameter_consistency(epsilon, hash_range):
    # 验证 OLH 机制的 p 和 q 属性符合基于 epsilon 与桶数量定义的概率比值规律
    m = OLHMechanism(epsilon=epsilon, domain_size=10, hash_range=hash_range)

    # 验证比率 p / q = exp(epsilon)
    ratio = m.p / m.q
    assert ratio == pytest.approx(np.exp(epsilon))

    # 验证总概率守恒 p + (g-1)q = 1
    total_prob = m.p + (hash_range - 1) * m.q
    assert total_prob == pytest.approx(1.0)


# ---------------------------------------------------------------- Continuous LDP Mechanisms
@given(st.floats(min_value=-100, max_value=100),
       st.floats(min_value=-10, max_value=0),
       st.floats(min_value=0.1, max_value=10))
def test_laplace_local_clipping(val, min_val, range_width):
    # 验证本地拉普拉斯机制能够返回浮点型加噪结果并隐式执行输入裁剪
    max_val = min_val + range_width
    m = LocalLaplaceMechanism(epsilon=1.0, clip_range=(min_val, max_val))

    res = m.randomise(val)
    assert isinstance(res, float)


@given(st.floats(min_value=-100, max_value=100),
       st.floats(min_value=-10, max_value=0),
       st.floats(min_value=0.1, max_value=10))
def test_gaussian_local_type_preservation(val, min_val, range_width):
    # 验证本地高斯机制在任意输入下均能稳定返回 Python 原生浮点数类型的结果
    max_val = min_val + range_width
    m = LocalGaussianMechanism(epsilon=1.0,
                               delta=1e-5,
                               clip_range=(min_val, max_val))

    res = m.randomise(val)
    assert isinstance(res, float)


@given(st.floats(min_value=-1.0, max_value=1.0))
def test_duchi_domain_constraint(val):
    # 验证 Duchi 机制的输出取值集合被严格限制在 {-1.0, +1.0} 这两个离散点上
    m = DuchiMechanism(epsilon=1.0)
    res = m.randomise(val)
    assert res == 1.0 or res == -1.0


@given(st.floats(min_value=-10.0, max_value=10.0))
def test_piecewise_domain_constraint(val):
    # 验证分段隐私机制（Piecewise）的随机化输出始终保持在标准差分隐私定义域 [-1, 1] 内
    m = PiecewiseMechanism(epsilon=1.0)
    res = m.randomise(val)
    assert -1.0 <= res <= 1.0


# ---------------------------------------------------------------- RAPPOR Mechanism
@given(
    st.lists(st.integers(min_value=0, max_value=1), min_size=8, max_size=32),
    st.floats(min_value=0.1, max_value=5.0))
def test_rappor_structure(bits, epsilon):
    # 验证 RAPPOR 机制在执行翻转后其输出位向量的长度与数值有效性均符合规范
    m = RAPPORMechanism(epsilon=epsilon)
    res = m.randomise(bits)
    assert isinstance(res, list)
    assert len(res) == len(bits)
    assert all(x in (0, 1) for x in res)


@given(st.integers(min_value=8, max_value=64))
def test_rappor_bloom_simulation(length):
    # 验证 RAPPOR 机制能正确处理包括全零或全一在内的各种极值位向量输入而不产生异常
    m = RAPPORMechanism(epsilon=1.0)
    zeros = [0] * length
    ones = [1] * length

    res_z = m.randomise(zeros)
    res_o = m.randomise(ones)

    assert len(res_z) == length
    assert len(res_o) == length
