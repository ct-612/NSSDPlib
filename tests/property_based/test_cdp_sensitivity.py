"""
Property-based tests for the CDP Noise Calibrator.
"""
# 说明：中心化差分隐私（CDP）噪声校准器（calibrate, calibrate_laplace, calibrate_gaussian）的属性测试。
# 覆盖：
# - 拉普拉斯机制噪声参数计算的数学一致性
# - 高斯机制校准分派器（dispatcher）的逻辑正确性
# - 对未知或未注册机制名称的参数校验拦截

import pytest
from hypothesis import given, strategies as st
from dplib.cdp.sensitivity.noise_calibrator import calibrate, calibrate_laplace, calibrate_gaussian
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- Noise Calibrator
@given(st.floats(min_value=0.1, max_value=10.0),
       st.floats(min_value=0.0, max_value=100.0))
def test_calibrate_laplace_consistency(epsilon, sensitivity):
    # 验证拉普拉斯校准结果是否符合 scale = sensitivity / epsilon 的数学定义
    scale = calibrate_laplace(epsilon, sensitivity=sensitivity)
    if sensitivity == 0:
        assert scale == 0.0
    else:
        assert scale == pytest.approx(sensitivity / epsilon)


@given(st.floats(min_value=0.1, max_value=10.0),
       st.floats(min_value=1e-5, max_value=0.01),
       st.floats(min_value=0.0, max_value=100.0))
def test_calibrate_gaussian_dispatcher(epsilon, delta, sensitivity):
    # 验证通用校准入口能够正确分派并调用高斯机制的参数计算逻辑
    param, val = calibrate("gaussian",
                           epsilon,
                           delta=delta,
                           sensitivity=sensitivity)
    assert param == "sigma"
    if sensitivity == 0:
        assert val == 0.0
    else:
        assert val > 0.0


@given(st.floats(min_value=0.1, max_value=10.0))
def test_calibrate_unknown_mechanism(epsilon):
    # 验证校准器在收到不受支持的机制名称时能正确抛出参数校验异常
    with pytest.raises(ParamValidationError):
        calibrate("unknown_mech", epsilon, sensitivity=1.0)
