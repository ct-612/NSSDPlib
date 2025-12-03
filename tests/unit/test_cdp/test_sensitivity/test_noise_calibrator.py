"""
Tests for noise calibrator utilities.
"""
# 说明：噪声校准工具函数的单元测试。
# 覆盖：
# - Laplace 与 Gaussian 噪声校准参数的基本数值正确性
# - 通用 calibrate 分发接口在不同机制类型下返回的参数名与数值
# - 缺失 delta、非法机制组合和未知机制类型时抛出 ParamValidationError

import math

import pytest

from dplib.cdp.sensitivity.noise_calibrator import (
    calibrate,
    calibrate_gaussian,
    calibrate_laplace,
)
from dplib.core.utils.param_validation import ParamValidationError


def test_calibrate_laplace_and_gaussian() -> None:
    # 验证 Laplace 和 Gaussian 校准接口在给定 epsilon 与敏感度时返回的噪声参数是否符合解析公式
    assert calibrate_laplace(1.0, sensitivity=2.0) == pytest.approx(2.0)
    sigma = calibrate_gaussian(1.0, 1e-5, sensitivity=1.5)
    assert sigma == pytest.approx(1.5 * math.sqrt(2 * math.log(1.25 / 1e-5)))


def test_calibrate_dispatch_and_errors() -> None:
    # 检查通用 calibrate 分发逻辑的参数名选择以及错误配置时的异常抛出行为
    param, value = calibrate("laplace", 1.0, sensitivity=3.0)
    assert param == "scale" and value == pytest.approx(3.0)
    param, value = calibrate("gaussian", 1.0, sensitivity=2.0, delta=1e-5)
    assert param == "sigma" and value == pytest.approx(calibrate_gaussian(1.0, 1e-5, sensitivity=2.0))

    with pytest.raises(ParamValidationError):
        calibrate("gaussian", 1.0, sensitivity=1.0)
    with pytest.raises(ParamValidationError):
        calibrate("vector", 1.0, sensitivity=1.0, distribution="gaussian")
    with pytest.raises(ParamValidationError):
        calibrate("unknown", 1.0, sensitivity=1.0)
