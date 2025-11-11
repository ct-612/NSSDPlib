"""
Privacy-preserving SUM query utilities.

Responsibilities:
    * enforce numeric bounds to guarantee global sensitivity
    * default to Laplace noise calibrated from epsilon and (upper-lower)
    * operate on scalars, Python iterables, or numpy arrays
"""
# 说明：差分隐私求和查询工具。
# 职责：
# - 通过对输入值进行区间裁剪 [lower, upper] 来保证全局敏感度（Δ = upper - lower）
# - 默认使用拉普拉斯机制，尺度由 ε 与 Δ 标定
# - 支持标量、Python 可迭代、NumPy 数组作为输入

from __future__ import annotations
from typing import Iterable, Optional, Sequence, Any, Tuple
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError
from dplib.cdp.mechanisms.laplace import LaplaceMechanism


class PrivateSumQuery:
    """Release DP protected sums for bounded numeric sequences."""
    # 对经过裁剪的数值序列计算和，并在输出端加拉普拉斯噪声。

    def __init__(
        self,
        epsilon: float,
        bounds: Tuple[float, float],
        *,
        mechanism: Optional[BaseMechanism] = None,
    ):
        # 初始化：校验并保存边界、ε；敏感度 Δ = upper - lower；准备或验证机制。
        self.lower, self.upper = self._validate_bounds(bounds)
        self._validate_epsilon(epsilon)
        self.epsilon = float(epsilon)
        self.sensitivity = self.upper - self.lower
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> None:
        # ε 必须为正
        if epsilon is None or float(epsilon) <= 0:
            raise ValidationError("epsilon must be a positive number for sum queries")

    @staticmethod
    def _validate_bounds(bounds: Tuple[float, float]) -> Tuple[float, float]:
        # 边界必须是二元组/列表，且 lower < upper
        if (
            not isinstance(bounds, (tuple, list))
            or len(bounds) != 2
        ):
            raise ValidationError("bounds must be a (lower, upper) pair")
        lower, upper = float(bounds[0]), float(bounds[1])
        if lower >= upper:
            raise ValidationError("sum query bounds must satisfy lower < upper")
        return lower, upper

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 准备噪声机制：
        # - 未提供时创建 LaplaceMechanism(ε, Δ) 并 calibrate()；
        # - 提供时要求继承 BaseMechanism 且已校准。
        if mechanism is None:
            mech = LaplaceMechanism(
                epsilon=self.epsilon,
                sensitivity=self.sensitivity,
            )
            mech.calibrate()
            return mech
        if not isinstance(mechanism, BaseMechanism):
            raise ValidationError("mechanism must inherit from BaseMechanism")
        if not mechanism.calibrated:
            raise ValidationError("provided mechanism must be calibrated before use")
        return mechanism

    @staticmethod
    def _to_numpy(values: Any) -> np.ndarray:
        # 将输入转换为 float 型 ndarray；拒绝字符串；通用可迭代通过 list(...) 再转 array
        if isinstance(values, (str, bytes)):
            raise ValidationError("sum query input must be numeric and non-string")
        if isinstance(values, np.ndarray):
            return values.astype(float)
        if isinstance(values, Sequence):
            return np.asarray(values, dtype=float)
        try:
            return np.asarray(list(values), dtype=float)
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValidationError("sum query input must be numeric iterable") from exc

    def _clip(self, arr: np.ndarray) -> np.ndarray:
        # 对数组进行区间裁剪并转为 float；空数组时仅保证 dtype
        if arr.size == 0:
            return arr.astype(float)
        return np.clip(arr, self.lower, self.upper).astype(float)

    def evaluate(self, values: Iterable[float]) -> float:
        """
        Execute the DP sum query.

        Args:
            values: Iterable numeric data.
        Returns:
            Noisy sum respecting the configured bounds.
        """
        # 流程：转换→裁剪→真实求和→通过机制加噪→返回浮点结果
        arr = self._clip(self._to_numpy(values))
        true_sum = float(arr.sum())
        return float(self.mechanism.randomise(true_sum))
