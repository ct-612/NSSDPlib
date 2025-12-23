"""
Privacy-preserving range query utilities built on noisy prefix sums.

Responsibilities
  - Build DP prefix sums for bounded numeric arrays.
  - Answer arbitrary index ranges using a single noisy prefix table.
  - Support sum/count/mean via metric selection.

Usage Context
  - Use to answer multiple range queries with one noisy prefix table.
  - Designed for bounded numeric inputs with contribution limits.

Limitations
  - Requires valid range indices using Python slicing semantics.
  - Mean results are stabilized by a minimum noisy count.
"""
# 说明：基于带噪前缀和实现差分隐私区间查询的工具模块。
# 职责：
# - 构建有界数值序列的差分隐私前缀和查询接口
# - 通过单次前缀表构建支持任意索引区间的重复查询
# - 通过 metric 参数统一支持 sum/count/mean 等多种区间统计

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError
from dplib.core.utils.param_validation import ensure, ensure_type
from dplib.cdp.mechanisms.vector import VectorMechanism

from .sum import PrivateSumQuery

Range = Tuple[int, int]


class PrivateRangeQuery:
    """
    Release DP protected range queries (sum/count/mean) via noisy prefixes.

    - Configuration
      - epsilon: Privacy budget used for calibrating the prefix mechanism.
      - bounds: Lower and upper bounds applied to inputs.
      - mechanism: Optional calibrated mechanism override.
      - max_contribution: Per-entity contribution bound for sensitivity.
      - metric: Default metric for queries ("sum", "count", or "mean").
      - min_count: Lower bound for stabilizing noisy mean denominators.

    - Behavior
      - Builds noisy prefix sums and answers ranges by subtraction.
      - Supports mean by combining noisy sum and noisy count prefixes.

    - Usage Notes
      - Provide a calibrated mechanism to override default construction.
    """

    def __init__(
        self,
        epsilon: float,
        bounds: Tuple[float, float],
        *,
        mechanism: Optional[BaseMechanism] = None,
        max_contribution: int = 1,
        metric: str = "sum",
        min_count: float = 1e-6,
    ):
        # 初始化区间查询对象并完成 epsilon、边界、贡献次数、度量类型和机制的参数校验与设置
        self.lower, self.upper = PrivateSumQuery._validate_bounds(bounds)
        self.epsilon = self._validate_epsilon(epsilon)
        self.max_contribution = self._validate_contribution(max_contribution)
        self.metric = self._validate_metric(metric)
        self.min_count = float(max(min_count, 1e-12))
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 校验并强制转换 epsilon 为正实数值，非法输入时抛出 ValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("epsilon must be a positive number for range queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for range queries", error=ValidationError)
        return numeric

    @staticmethod
    def _validate_contribution(max_contribution: int) -> int:
        # 校验单个用户对整个前缀序列的最大贡献次数必须为正并返回标准化整数值
        ensure(max_contribution > 0, "max_contribution must be positive", error=ValidationError)
        return int(max_contribution)

    @staticmethod
    def _validate_metric(metric: str) -> str:
        # 校验度量类型只允许 sum/count/mean 并返回标准化的小写字符串
        allowed = {"sum", "count", "mean"}
        lowered = metric.lower()
        if lowered not in allowed:
            raise ValidationError(f"metric must be one of {allowed}")
        return lowered

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 如果未显式提供机制则构造默认 Laplace 向量机制，否则校验并返回给定机制实例
        if mechanism is None:
            mech = VectorMechanism(
                epsilon=self.epsilon,
                sensitivity=1.0,
                distribution="laplace",
                norm="l1",
            )
            return mech
        ensure_type(mechanism, (BaseMechanism,), label="mechanism")
        return mechanism

    def _sensitivity(self, prefix_length: int, metric: str) -> float:
        # 根据前缀长度和度量类型计算对应前缀表的全局敏感度
        width = max(prefix_length - 1, 1)
        if metric == "count":
            return float(self.max_contribution * width)
        span = self.upper - self.lower
        return float(span * self.max_contribution * width)

    def _calibrate(self, prefix_length: int, metric: str) -> BaseMechanism:
        # 按当前前缀长度和度量类型为底层机制重新标定敏感度参数
        sensitivity = self._sensitivity(prefix_length, metric)
        mech = self.mechanism
        mech.calibrate(sensitivity=sensitivity)
        return mech

    @staticmethod
    def _materialize_numeric(values: Any) -> List[float]:
        # 复用 PrivateSumQuery 的数值化逻辑将输入转为浮点列表
        numeric = PrivateSumQuery._materialize_numeric(values)
        return list(numeric)

    def _build_prefix(self, base_values: np.ndarray) -> List[float]:
        # 基于基础数值数组构造包含初始 0 的前缀和序列
        prefix = [0.0]
        running = 0.0
        for value in base_values:
            running += float(value)
            prefix.append(running)
        return prefix

    def _noisy_prefix(self, metric: str, clipped: np.ndarray) -> np.ndarray:
        # 按度量类型选择基础数组并构建前缀和，然后用标定机制对整个前缀表加噪
        if metric == "count":
            base = np.ones_like(clipped, dtype=float)
        else:
            base = clipped
        prefix = self._build_prefix(base)
        mech = self._calibrate(len(prefix), metric)
        noisy = mech.randomise(np.asarray(prefix, dtype=float))
        return np.asarray(noisy, dtype=float)

    def prefix_sums(self, values: Iterable[float]) -> List[float]:
        """Backward compatible noisy prefix sums for sum metric."""
        # 提供向后兼容的 sum 度量前缀和接口，对输入剪裁后返回带噪前缀和列表
        materialized = self._materialize_numeric(values)
        clipped = np.clip(np.asarray(materialized, dtype=float), self.lower, self.upper)
        return self._noisy_prefix("sum", clipped).tolist()

    @staticmethod
    def _validate_ranges(ranges: Sequence[Range], length: int) -> Tuple[Range, ...]:
        # 校验每个区间的起止下标非负、end 不小于 start 且不超过整体长度并返回规范化区间元组
        validated: List[Range] = []
        for start, end in ranges:
            ensure(start >= 0, "range start must be non-negative", error=ValidationError)
            ensure(end >= start, "range end must be >= start", error=ValidationError)
            ensure(end <= length, "range end out of bounds", error=ValidationError)
            validated.append((int(start), int(end)))
        return tuple(validated)

    def evaluate(
        self,
        values: Iterable[float],
        ranges: Sequence[Range],
        *,
        metric: Optional[str] = None,
    ) -> List[float]:
        # 按指定或默认度量类型执行差分隐私区间查询并通过带噪前缀和差分得到各区间结果
        """
        Execute the DP range query over provided ranges.

        Args:
            values: Iterable numeric data.
            ranges: Sequence of (start, end) index pairs using Python slicing semantics [start, end).
            metric: Query type ('sum', 'count', 'mean'); defaults to constructor metric.
        Returns:
            Noisy results for each requested range.
        """
        effective_metric = self._validate_metric(metric or self.metric)
        materialized = self._materialize_numeric(values)
        clipped = np.clip(np.asarray(materialized, dtype=float), self.lower, self.upper)
        validated = self._validate_ranges(ranges, len(materialized))

        if effective_metric == "mean":
            # 对均值查询分别构造 sum 和 count 的带噪前缀和并用稳定计数避免除零或极端比值
            noisy_sum = self._noisy_prefix("sum", clipped)
            noisy_count = self._noisy_prefix("count", clipped)
            results: List[float] = []
            for start, end in validated:
                dp_sum = float(noisy_sum[end] - noisy_sum[start])
                dp_count = float(noisy_count[end] - noisy_count[start])
                stable_count = max(dp_count, self.min_count)
                mean_estimate = dp_sum / stable_count
                # 将估计均值裁剪回原始值域以保持数值稳定和语义合理
                results.append(float(np.clip(mean_estimate, self.lower, self.upper)))
            return results

        noisy_prefix = self._noisy_prefix(effective_metric, clipped)
        results = []
        for start, end in validated:
            results.append(float(noisy_prefix[end] - noisy_prefix[start]))
        return results
