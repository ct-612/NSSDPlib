"""Numerical discretisation encoder for LDP pipelines."""
# 说明：为连续/数值型输入提供离散化桶索引编码，输出整数桶索引，可与 GRR/unary/hashing 等机制配合使用。
# 职责：
# - 根据均匀或分位数策略将连续数值映射到离散桶索引
# - 管理数值剪裁边界与桶边缘的计算
# - 提供编码（值转索引）与解码（索引转代表值）功能

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Tuple

import numpy as np

from dplib.core.utils.param_validation import ParamValidationError
from .base import FittedEncoder
from dplib.ldp.types import EncodedValue


class NumericalBucketsEncoder(FittedEncoder):
    """
    Discretise numeric values into bucket indices using uniform or quantile-based bins.

    - strategy="uniform": equally spaced edges over [min, max] (or clip_range).
    - strategy="quantile": empirical quantile edges to balance counts; falls back
      to uniform if quantiles collapse into zero-width buckets.
    """

    def __init__(
        self,
        num_buckets: int,
        strategy: str = "uniform",
        clip_range: Optional[Tuple[float, float]] = None,
    ):
        # 初始化数值编码器配置，支持 均匀/分位数 分桶策略与可选的数值剪裁范围
        super().__init__()
        if num_buckets <= 0:
            raise ParamValidationError("num_buckets must be positive")
        self.num_buckets = int(num_buckets)
        self.strategy = strategy
        self.clip_range = clip_range
        self.edges: Optional[np.ndarray] = None

    def fit(self, data: Iterable[float]) -> "NumericalBucketsEncoder":
        # 基于输入数据分布或预设剪裁范围计算分桶边缘 edges
        """Compute bucket edges from data (or provided clip_range)."""
        values = list(data)
        if len(values) == 0:
            raise ParamValidationError("data must be non-empty to fit NumericalBucketsEncoder")

        # 确定数值范围的上下界，若未提供 clip_range 则由数据推导
        if self.clip_range is not None:
            a, b = self.clip_range
        else:
            a = min(values)
            b = max(values)

        # 根据指定策略生成分桶边缘
        if self.strategy == "uniform":
            edges = np.linspace(a, b, self.num_buckets + 1)
        elif self.strategy == "quantile":
            # 使用经验分位数构造更平衡的桶，必要时退回均匀桶以避免零宽度区间
            q_points = np.linspace(0.0, 1.0, self.num_buckets + 1)
            clipped_values = np.clip(values, a, b)
            edges = np.quantile(clipped_values, q_points)
            edges[0], edges[-1] = a, b
            # 如全部分位数坍缩为同一值，则退回均匀分桶；否则允许部分零宽度桶以保持分位信息
            if np.all(np.diff(edges) <= 0):
                edges = np.linspace(a, b, self.num_buckets + 1)
        else:
            raise ParamValidationError(f"unknown strategy '{self.strategy}'")

        self.edges = edges
        self._mark_fitted()
        return self

    def encode(self, value: float) -> EncodedValue:
        # 将浮点数值映射为对应的整数桶索引，包含越界剪裁处理
        """Map numeric value to its bucket index (int)."""
        self._ensure_fitted()
        if self.edges is None:
            raise ParamValidationError("encoder edges not initialised")

        # 将值剪裁到 [min_edge, max_edge] 区间内
        clipped = float(np.clip(value, self.edges[0], self.edges[-1]))
        # 使用二分查找确定值所在的桶区间索引，side="right" 配合 -1 实现左闭右开逻辑
        idx = int(np.searchsorted(self.edges, clipped, side="right") - 1)
        # 处理可能的上边界溢出情况，确保索引不超过 num_buckets - 1
        if idx >= self.num_buckets:
            idx = self.num_buckets - 1
        return idx

    def decode(self, encoded: EncodedValue) -> float:
        # 将桶索引逆向映射回该桶的代表值（通常为桶中心点）
        """Map bucket index back to representative (bucket centre) value."""
        self._ensure_fitted()
        if self.edges is None:
            raise ParamValidationError("encoder edges not initialised")
        if not isinstance(encoded, (int, np.integer)):
            raise ParamValidationError("encoded value for numerical decode must be an int")

        idx = int(encoded)
        if idx < 0 or idx >= self.num_buckets:
            raise ParamValidationError(f"encoded index {idx} out of range")

        # 计算桶的左右边缘并取平均值作为中心点
        return float((self.edges[idx] + self.edges[idx + 1]) / 2.0)

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回编码器的序列化元数据，包括类型、桶数量、策略及边缘数组
        """Return JSON-serializable metadata about the bucketisation."""
        return {
            "type": "numerical_buckets",
            "num_buckets": self.num_buckets,
            "strategy": self.strategy,
            "edges": None if self.edges is None else self.edges.tolist(),
        }
