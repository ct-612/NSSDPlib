"""
Privacy-preserving histogram utilities.

Responsibilities:
    * compute histogram counts for provided bin edges
    * apply vectorised DP noise calibrated to contribution limits
    * preserve original bin edges for downstream consumers
"""
# 说明：基于向量化噪声机制对直方图计数进行差分隐私保护的查询工具。
# 职责：
# - 校验 epsilon、bins 与 max_contribution 等参数并固化直方图分箱边界
# - 使用 VectorMechanism 按最大贡献约束对计数向量进行一次性噪声注入
# - 返回非负的噪声计数及原始分箱边界便于下游绘图或进一步统计分析

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from dplib.core.data.statistics import histogram
from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError
from dplib.core.utils.param_validation import ensure, ensure_type
from dplib.cdp.mechanisms.vector import VectorMechanism


class PrivateHistogramQuery:
    """Release DP protected histogram counts."""

    def __init__(
        self,
        epsilon: float,
        bins: Sequence[float],
        *,
        mechanism: Optional[BaseMechanism] = None,
        max_contribution: int = 1,
    ):
        # 初始化直方图查询参数并构造或验证用于加噪的向量机制
        self.epsilon = self._validate_epsilon(epsilon)
        self.bins = self._validate_bins(bins)
        self.max_contribution = self._validate_contribution(max_contribution)
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将传入的 epsilon 转为浮点并要求其为正数否则抛出 ValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("epsilon must be a positive number for histogram queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for histogram queries", error=ValidationError)
        return numeric

    @staticmethod
    def _validate_bins(bins: Sequence[float]) -> Tuple[float, ...]:
        # 确保 bins 为有序数值序列且至少包含两个边界点
        ensure_type(bins, (list, tuple), label="bins")
        ensure(len(bins) >= 2, "bins must include at least two edges", error=ValidationError)
        try:
            numeric_bins = tuple(float(edge) for edge in bins)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("bins must be numeric") from exc
        ensure(
            list(numeric_bins) == sorted(numeric_bins),
            "bins must be sorted ascending",
            error=ValidationError,
        )
        return numeric_bins

    @staticmethod
    def _validate_contribution(max_contribution: int) -> int:
        # 校验单个主体在直方图中的最大贡献次数用于设置敏感度
        ensure(max_contribution > 0, "max_contribution must be positive", error=ValidationError)
        return int(max_contribution)

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 若未提供外部机制则按 max_contribution 构造并校准 Laplace 向量机制，否则验证外部机制状态
        if mechanism is None:
            mech = VectorMechanism(
                epsilon=self.epsilon,
                sensitivity=float(self.max_contribution),
                distribution="laplace",
                norm="l1",
            )
            mech.calibrate()
            return mech
        ensure_type(mechanism, (BaseMechanism,), label="mechanism")
        ensure(mechanism.calibrated, "provided mechanism must be calibrated before use", error=ValidationError)
        return mechanism

    def evaluate(self, values: Iterable[float]) -> Tuple[List[float], Tuple[float, ...]]:
        """
        Execute the DP histogram query.

        Args:
            values: Iterable numeric data.
        Returns:
            (noisy_counts, bins)
        """
        # 先用确定性直方图统计计数，再对计数向量整体加噪并截断为非负值
        try:
            counts, bin_edges = histogram(values, bins=self.bins)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValidationError(str(exc)) from exc

        noisy = np.asarray(self.mechanism.randomise(np.asarray(counts, dtype=float)), dtype=float)
        clipped = np.maximum(noisy, 0.0)
        return clipped.tolist(), bin_edges
