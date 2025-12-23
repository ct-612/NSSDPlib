"""
Noise calibrator utilities based on sensitivity and privacy budget.

Provides common calibration formulas for Laplace and Gaussian mechanisms,
plus a thin dispatcher for mechanism-aware calibration.

Responsibilities
  - Provide calibration formulas for common CDP mechanisms.
  - Validate epsilon, delta, and sensitivity inputs.
  - Dispatch calibration by mechanism name and return parameter values.

Usage Context
  - Use to compute noise parameters before mechanism calibration.
  - Intended for lightweight integration in CDP pipelines.

Limitations
  - Uses the standard 1.25 constant for Gaussian calibration.
  - Supports only a predefined set of mechanism identifiers.
"""
# 说明：基于查询敏感度与隐私预算为常见 CDP 机制计算噪声参数的校准工具。
# 职责：
# - 为 Laplace 与 Gaussian 机制提供可复用的噪声尺度/方差校准公式
# - 对输入 epsilon/delta/sensitivity 做类型与取值区间的标准化校验
# - 提供统一的 calibrate 入口按机制名称分派到对应校准函数并返回参数名与数值

from __future__ import annotations

import math
from typing import Optional, Tuple

from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type


def calibrate_laplace(epsilon: float, *, sensitivity: float) -> float:
    # 按 Laplace 机制噪声校准公式计算尺度参数 b 并处理零敏感度退化场景
    # b = sensitivity / epsilon
    """Return Laplace scale (b) for given epsilon and sensitivity."""
    ensure_type(epsilon, (int, float), label="epsilon")
    ensure_type(sensitivity, (int, float), label="sensitivity")
    ensure(epsilon > 0, "epsilon must be positive")
    ensure(sensitivity >= 0, "sensitivity must be non-negative")
    if sensitivity == 0:
        return 0.0
    return float(sensitivity) / float(epsilon)


def calibrate_gaussian(epsilon: float, delta: float, *, sensitivity: float) -> float:
    # 使用常见 (ε, δ)-DP 高斯机制 1.25 上界公式计算噪声标准差 σ 并校验参数有效性
    # σ = sensitivity * sqrt(2 * ln(1.25 / δ)) / epsilon
    """Return Gaussian sigma for (epsilon, delta)-DP using common 1.25 bound."""
    ensure_type(epsilon, (int, float), label="epsilon")
    ensure_type(delta, (int, float), label="delta")
    ensure_type(sensitivity, (int, float), label="sensitivity")
    ensure(epsilon > 0, "epsilon must be positive")
    ensure(0 < delta < 1, "delta must be in (0,1)")
    ensure(sensitivity >= 0, "sensitivity must be non-negative")
    if sensitivity == 0:
        return 0.0
    return float(sensitivity) * math.sqrt(2.0 * math.log(1.25 / float(delta))) / float(epsilon)


def calibrate(
    mechanism: str,
    epsilon: float,
    *,
    sensitivity: float,
    delta: Optional[float] = None,
    distribution: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Calibrate noise parameter for a mechanism.

    Returns (param_name, value) where param_name is "scale" (Laplace) or "sigma" (Gaussian).
    """
    # 统一入口根据机制名称分派到具体校准函数并返回对应噪声参数名与数值
    name = mechanism.lower()
    if name in {"laplace"}:
        return "scale", calibrate_laplace(epsilon, sensitivity=sensitivity)
    if name in {"gaussian"}:
        if delta is None:
            raise ParamValidationError("delta is required for gaussian calibration")
        return "sigma", calibrate_gaussian(epsilon, delta, sensitivity=sensitivity)
    if name in {"geometric", "staircase"}:
        # 采用与拉普拉斯同幅度的离散尺度
        return "scale", calibrate_laplace(epsilon, sensitivity=sensitivity)
    if name in {"exponential"}:
        ensure(sensitivity > 0, "sensitivity must be positive for exponential mechanism")
        return "utility_multiplier", float(epsilon) / (2.0 * float(sensitivity))
    if name in {"vector"}:
        dist = (distribution or "laplace").lower()
        if dist == "gaussian":
            if delta is None:
                raise ParamValidationError("delta is required for gaussian vector calibration")
            return "sigma", calibrate_gaussian(epsilon, delta, sensitivity=sensitivity)
        # 默认使用拉普拉斯向量噪声
        return "scale", calibrate_laplace(epsilon, sensitivity=sensitivity)
    raise ParamValidationError(f"unsupported mechanism '{mechanism}'")
