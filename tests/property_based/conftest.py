"""
Shared Hypothesis strategies for property-based testing across NSSDPlib.
"""
# 说明：属性测试中共享的 Hypothesis 策略集。
# 职责：
# - 提供隐私参数（epsilon, delta）的复用生成策略
# - 为记账器与机制测试生成合法的 PrivacyBudget 实例
# - 生成具有受控形状与分布的多维 NumPy 数组
# - 暴露稳定的 RNG 种子生成策略以支持可复现性测试

import numpy as np
from hypothesis import strategies as st
from dplib.core.privacy.privacy_accountant import PrivacyBudget


# ------------------------------------------------------------------ Basic Types
@st.composite
def epsilons(draw):
    # 生成合法且正值的 epsilon 参数，避免数值下溢或极值导致计算异常
    return draw(
        st.floats(min_value=1e-10,
                  max_value=100.0,
                  allow_nan=False,
                  allow_infinity=False))


@st.composite
def deltas(draw):
    # 生成满足差分隐私定义的 [0, 1] 闭区间内的浮点数偏移量
    return draw(
        st.floats(min_value=0.0,
                  max_value=1.0,
                  allow_nan=False,
                  allow_infinity=False))


@st.composite
def privacy_budgets(draw):
    # 组合 epsilon 与 delta 生成符合 PrivacyBudget 构造要求的组合对象
    eps = draw(epsilons())
    delta = draw(deltas())
    return PrivacyBudget(epsilon=eps, delta=delta)


# ------------------------------------------------------------------ Arrays & Data
@st.composite
def ndarrays(draw, min_dims=0, max_dims=3, min_side=1, max_side=10):
    # 构建具有随机形状与数值的多维 NumPy 数组，模拟典型的机制输入数据结构
    # 随机采样每个维度的长度并构造形状元组
    shape = draw(
        st.lists(st.integers(min_side, max_side),
                 min_size=min_dims,
                 max_size=max_dims))
    return draw(
        st.arrays(dtype=np.float64,
                  shape=tuple(shape),
                  elements=st.floats(min_value=-1e6,
                                     max_value=1e6,
                                     allow_nan=False,
                                     allow_infinity=False)))


# ------------------------------------------------------------------ Helper objects
@st.composite
def seeds(draw):
    # 提供整数种子或空值，用于初始化随机数生成器以进行可复现性验证
    return draw(
        st.one_of(st.none(), st.integers(min_value=0, max_value=2**32 - 1)))
