"""
Numerical utilities for basic dataset statistics.

Responsibilities:
    * Implemented with numerical stability in mind
    * Accept either scalar sequences or iterable mappings.
"""
# 说明：用于基础数据集统计的数值工具。
# 职责：
# - 提供基础统计数值工具：计数、求和（含 Kahan 补偿以提升数值稳定性）、均值、方差、直方图、以及在线统计（Welford）算法
# - 支持两类输入：纯数值序列，或“映射记录（Mapping）”序列（可通过 field 抽取某列）

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple


Number = float
# 简单别名：当前模块中将数值视为浮点


def _extract(values: Iterable[Any], *, field: Optional[str]) -> List[Number]:
    # 字段提取工具：将任意可迭代 values 规范化为 float 列表。
    # - 若 field 为 None：直接将各元素转为 float；
    # - 否则假设元素为 Mapping，从中取出指定字段并转为 float
    if field is None:
        return [float(value) for value in values]
    extracted = []
    for value in values:
        if isinstance(value, Mapping):
            extracted.append(float(value[field]))
        else:
            raise TypeError("field extraction requires mapping-based records")
    return extracted


def count(values: Iterable[Any]) -> int:
    """Return the number of items."""
    # 计数：迭代一次求长度（惰性可迭代也适用）
    return sum(1 for _ in values)


def summation(values: Iterable[Any], *, field: Optional[str] = None) -> float:
    """Return the sum of values with Kahan compensation."""
    # 求和（Kahan 补偿）：降低浮点累加误差
    extracted = _extract(values, field=field)
    total = 0.0
    compensation = 0.0
    for value in extracted:
        y = value - compensation
        t = total + y
        compensation = (t - total) - y
        total = t
    return total


def mean(values: Iterable[Any], *, field: Optional[str] = None) -> float:
    # 均值：对抽取后的数组求和/长度；空输入时报错
    extracted = _extract(values, field=field)
    if not extracted:
        raise ValueError("mean of empty input")
    return summation(extracted) / len(extracted)


def variance(values: Iterable[Any], *, field: Optional[str] = None, ddof: int = 1) -> float:
    # 方差：默认无偏估计（ddof=1 样本方差）。当样本数 ≤ ddof 时抛错。
    extracted = _extract(values, field=field)
    n = len(extracted)
    if n <= ddof:
        raise ValueError("not enough values to compute variance")
    mu = mean(extracted)
    accum = sum((x - mu) ** 2 for x in extracted)
    return accum / (n - ddof)


def histogram(values: Iterable[Any], *, bins: Sequence[float]) -> Tuple[List[int], Sequence[float]]:
    """Return histogram counts for numeric values and provided bin edges."""
    # 直方图计数：bins 为递增边界，返回各区间计数（左闭右开，最后一个区间右端点包含）
    if len(bins) < 2:
        raise ValueError("histogram requires at least two bin edges")
    counts = [0 for _ in range(len(bins) - 1)]
    for value in values:
        numeric = float(value)
        if numeric < bins[0] or numeric > bins[-1]:
            continue
        for idx in range(len(bins) - 1):
            left, right = bins[idx], bins[idx + 1]
            if left <= numeric < right or (idx == len(bins) - 2 and numeric == right):
                counts[idx] += 1
                break
    return counts, bins


@dataclass
class RunningStats:
    """Online algorithm for mean/variance using Welford's method."""
    # 在线均值/方差（Welford）：单次遍历、数值稳定、适合流式数据

    count: int = 0
    mean: float = 0.0
    _m2: float = 0.0  # 累积二阶矩（用于计算方差）

    def update(self, value: float) -> None:
        # 逐点更新：Welford 递推公式
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self._m2 += delta * delta2

    @property
    def variance(self) -> float:
        # 样本方差（ddof=1）；当样本不足 2 个返回 0.0
        if self.count < 2:
            return 0.0
        return self._m2 / (self.count - 1)

    @property
    def std(self) -> float:
        # 标准差：方差开平方
        return self.variance ** 0.5
