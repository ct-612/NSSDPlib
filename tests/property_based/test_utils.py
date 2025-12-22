"""
Property-based tests for common numerical and validation utilities.
"""
# 说明：公共数值计算（logsumexp, softmax, stable_mean）与参数校验工具的属性测试。
# 覆盖：
# - 校验桩函数 ensure 与 ensure_type 对参数契约的强制性拦截
# - logsumexp 与 softmax 在极限数值输入下的稳定性与分布特性
# - stable_mean 在大数值动态范围下的聚合精度
# - clamp_probabilities 对极小值平滑处理及概率总和守恒的验证

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError
from dplib.core.utils.math_utils import logsumexp, softmax, stable_mean, clamp_probabilities


# ------------------------------------------------------------------ Param Validation
def test_ensure():
    # 验证 ensure 工具在断言失败时能正确分发预定义的参数验证报错消息
    ensure(True, "msg")
    with pytest.raises(ParamValidationError):
        ensure(False, "error message")


def test_ensure_type():
    # 验证类型校验工具能够识别并将不符合白名单类型的入参进行强拦截
    ensure_type(1, (int, ))
    ensure_type(1.0, (int, float))
    with pytest.raises(ParamValidationError):
        ensure_type("1", (int, ))


# ------------------------------------------------------------------ Math Utils
@given(
    st.lists(st.floats(min_value=-100, max_value=100), min_size=1,
             max_size=10))
def test_logsumexp_stability(values):
    # 验证稳健的 log-sum-exp 实现在处理对数级联加法时的数值稳定性
    res = logsumexp(values)
    # 对于单元素序列，其对数和应近似等于元素原始值
    if len(values) == 1:
        assert res == pytest.approx(values[0])
    # 结果应在数值上不小于输入项中的最大值
    assert res >= np.max(values) - 1e-12


@given(
    st.lists(st.floats(min_value=-10, max_value=10), min_size=1, max_size=10))
def test_softmax_properties(values):
    # 验证 softmax 输出的各种概率分量非负且总和保持为标准归一化状态
    probs = softmax(values)
    assert np.all(probs >= 0)
    assert np.sum(probs) == pytest.approx(1.0)


@given(
    st.lists(st.floats(min_value=-1e5, max_value=1e5), min_size=1,
             max_size=10))
def test_stable_mean(values):
    # 验证基于 Welford 思想的在线均值算法在大范围浮点输入下的计算精确性
    res = stable_mean(values)
    assert res == pytest.approx(np.mean(values))


@given(st.lists(st.floats(min_value=0, max_value=1), min_size=1, max_size=10))
def test_clamp_probabilities(probs):
    # 验证概率裁剪工具能在纠偏极小分量的同时精准维持概率分布的总和归一性
    arr = np.asarray(probs, dtype=float)
    clamped = clamp_probabilities(probs)
    # 验证裁剪后所有分量均受到预设下限的保护且分布再平衡有效
    assert np.all(clamped >= 1e-12 / np.sum(np.clip(arr, 1e-12, 1 - 1e-12)))
    assert np.sum(clamped) == pytest.approx(1.0)
