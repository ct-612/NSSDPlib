"""
Privacy-preserving SUM query utilities.

Responsibilities
  - Enforce numeric bounds to guarantee global sensitivity.
  - Default to Laplace noise calibrated from epsilon and bounds span.
  - Operate on scalars, Python iterables, or numpy arrays.

Usage Context
  - Use to release a noisy sum for bounded numeric data.
  - Supports simple privacy accounting through calibrated mechanisms.

Limitations
  - Requires finite numeric bounds with lower < upper.
  - Returns a float even when inputs are integer-like.
"""
# 说明：在有界数值范围内对求和结果添加噪声以满足差分隐私需求的查询工具。
# 职责：
# - 校验并固定输入数据的数值边界以确保全局敏感度有限
# - 默认使用基于 epsilon 与区间跨度校准的 Laplace 机制进行噪声注入
# - 支持标量、Python 可迭代对象与 numpy 数组等多种输入形式的统一处理

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from dplib.core.data.statistics import summation
from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError
from dplib.core.utils.param_validation import ensure, ensure_type
from dplib.cdp.mechanisms.laplace import LaplaceMechanism


class PrivateSumQuery:
    """
    Release DP protected sums for bounded numeric sequences.

    - Configuration
      - epsilon: Privacy budget for the default Laplace mechanism.
      - bounds: Lower and upper bounds used for clipping and sensitivity.
      - mechanism: Optional calibrated mechanism override.

    - Behavior
      - Clips inputs to bounds and computes a noisy sum.
      - Uses a calibrated mechanism to add noise to the true sum.

    - Usage Notes
      - Provide a calibrated mechanism to override defaults.
    """

    def __init__(
        self,
        epsilon: float,
        bounds: Tuple[float, float],
        *,
        mechanism: Optional[BaseMechanism] = None,
    ):
        # 初始化带界求和查询并根据敏感度配置默认或自定义的噪声机制
        # 校验并保存边界与 ε；敏感度 Δ = upper - lower；准备或验证噪声机制
        self.lower, self.upper = self._validate_bounds(bounds)
        self.epsilon = self._validate_epsilon(epsilon)
        self.sensitivity = self.upper - self.lower
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将传入的 epsilon 转为浮点并要求其为正数否则抛出 ValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("epsilon must be a positive number for sum queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for sum queries", error=ValidationError)
        return numeric

    @staticmethod
    def _validate_bounds(bounds: Tuple[float, float]) -> Tuple[float, float]:
        # 校验 bounds 结构与数值类型并确保 lower < upper
        ensure_type(bounds, (tuple, list), label="bounds")
        ensure(len(bounds) == 2, "bounds must be a (lower, upper) pair", error=ValidationError)
        try:
            lower, upper = float(bounds[0]), float(bounds[1])
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("bounds must be numeric") from exc
        ensure(lower < upper, "sum query bounds must satisfy lower < upper", error=ValidationError)
        return lower, upper

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 若未提供机制则按当前 ε 与敏感度构造并校准 Laplace 机制，否则校验外部机制类型与已校准状态
        if mechanism is None:
            mech = LaplaceMechanism(
                epsilon=self.epsilon,
                sensitivity=self.sensitivity,
            )
            mech.calibrate()
            return mech
        ensure_type(mechanism, (BaseMechanism,), label="mechanism")
        ensure(mechanism.calibrated, "provided mechanism must be calibrated before use", error=ValidationError)
        return mechanism

    @staticmethod
    def _materialize_numeric(values: Any) -> List[float]:
        # 将多种输入形式统一转换为浮点列表并显式拒绝字符串类型
        if isinstance(values, (str, bytes)):
            raise ValidationError("sum query input must be numeric and non-string")
        try:
            iterable = values if isinstance(values, Sequence) or isinstance(values, np.ndarray) else list(values)  # type: ignore[arg-type]
        except TypeError:
            iterable = [values]

        numeric: List[float] = []
        for value in iterable:
            try:
                numeric.append(float(value))
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValidationError("sum query input must be numeric iterable") from exc
        return numeric

    def _clip_values(self, values: List[float]) -> List[float]:
        # 将输入数值裁剪到配置的 [lower, upper] 区间以匹配敏感度假设
        if not values:
            return []
        clipped = np.clip(np.asarray(values, dtype=float), self.lower, self.upper)
        return clipped.tolist()

    def evaluate(self, values: Iterable[float]) -> float:
        """
        Execute the DP sum query.

        Args:
            values: Iterable numeric data.
        Returns:
            Noisy sum respecting the configured bounds.
        """
        # 统一输入类型与裁剪后计算真实和并通过机制注入噪声
        clipped = self._clip_values(self._materialize_numeric(values))
        true_sum = float(summation(clipped))
        return float(self.mechanism.randomise(true_sum))
