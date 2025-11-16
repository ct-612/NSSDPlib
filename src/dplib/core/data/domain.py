"""
Domain abstractions used throughout the data layer.

Responsibilities:
    * describe legal value ranges and canonical dtypes
    * validate incoming values and provide optional mappings/encoders
    * support discrete, continuous, and bucketised domains out of the box
"""
# 说明：数据层通用“域（Domain）”抽象。
# 职责：
# - 统一描述字段的取值空间与规范化 dtype（如 category/float/bucket）
# - 为上层组件（Schema/Validator/Transformers）提供一致的校验与编码接口
# - 内置三类常用域：离散（类别）、连续（数值区间）、分桶（区间边界）

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


class DomainError(ValueError):
    """Raised when values fall outside of the declared domain."""
    # 域相关错误：用于表示输入值不属于声明的域（取值范围）


@dataclass(frozen=True)
class DomainInfo:
    """Lightweight descriptor used for logging and schema inspection."""
    # 轻量级域描述：便于日志与模式（schema）检查展示

    name: str
    dtype: str
    cardinality: Optional[int] = None
    bounds: Optional[Tuple[Optional[float], Optional[float]]] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BaseDomain(ABC):
    """Abstract base class for all domains."""
    # 所有域类型的抽象基类：统一名称、dtype、元数据与校验/编码接口

    def __init__(self, name: Optional[str] = None, dtype: Optional[str] = None, metadata: Optional[Mapping[str, Any]] = None):
        self._name = name or self.__class__.__name__
        self._dtype = dtype or "object"
        self._metadata = dict(metadata or {})

    @property
    def name(self) -> str:
        return self._name  # 域名：用于可读性与日志

    @property
    def dtype(self) -> str:
        return self._dtype  # 规范化 dtype：如 "category"、"float64"、"bucket" 等

    @property
    def metadata(self) -> Mapping[str, Any]:
        return dict(self._metadata)  # 返回副本，避免外部修改内部状态

    @abstractmethod
    def contains(self, value: Any) -> bool:
        """Return True when the provided value belongs to the domain."""
        # 成员关系判定：子类必须实现

    def clamp(self, value: Any) -> Any:
        """Clamp the value to the domain if supported; otherwise, raise."""
        # 默认实现：不支持自动裁剪，若不在域内则抛错（连续域会覆盖）
        if not self.contains(value):
            raise DomainError(f"value {value!r} outside of domain {self.name}")
        return value

    def encode(self, value: Any) -> Any:
        """Map the raw value onto a canonical representation."""
        # 规范化映射：默认恒等；离散域会映射到索引
        return value

    def decode(self, value: Any) -> Any:
        """Inverse of `encode`; defaults to an identity map."""
        # 反向映射：默认恒等；离散域从索引映射回标签
        return value

    def validate(self, value: Any) -> Any:
        """Check membership and return encoded value."""
        # 组合操作：先 contains，再 encode；作为通用入口
        if not self.contains(value):
            raise DomainError(f"value {value!r} outside of domain {self.name}")
        return self.encode(value)

    def describe(self) -> DomainInfo:
        """Return a human readable summary."""
        # 对外可读摘要：供调试/文档/可视化使用
        return DomainInfo(name=self.name, dtype=self.dtype, metadata=self.metadata)


class DiscreteDomain(BaseDomain):
    """Domain backed by a finite set of categories."""
    # 离散域：由有限类别集合支撑；提供类别<->索引的可逆编码

    def __init__(
        self,
        categories: Sequence[Any],
        *,
        ordered: bool = False,
        name: Optional[str] = None,
        dtype: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        if not categories:
            raise DomainError("DiscreteDomain requires at least one category")
        super().__init__(name=name or "DiscreteDomain", dtype=dtype or "category", metadata=metadata)
        deduped = list(dict.fromkeys(categories))  # 去重且保持顺序
        self._categories: List[Any] = deduped
        self._set = set(deduped)  # 快速成员测试
        self._ordered = ordered   # 是否有序（用于下游可选逻辑）
        self._index = {cat: idx for idx, cat in enumerate(deduped)}  # 类别->索引

    @property
    def categories(self) -> Tuple[Any, ...]:
        return tuple(self._categories)

    def contains(self, value: Any) -> bool:
        return value in self._set

    def encode(self, value: Any) -> int:
        # 将类别值编码为稳定索引
        if value not in self._index:
            raise DomainError(f"value {value!r} outside of domain {self.name}")
        return self._index[value]

    def decode(self, value: Any) -> Any:
        # 将索引解码回类别值；索引越界即抛错
        if isinstance(value, int) and 0 <= value < len(self._categories):
            return self._categories[value]
        raise DomainError(f"encoded value {value!r} outside of domain {self.name}")

    def describe(self) -> DomainInfo:
        # 描述信息包括基数与有序标记
        return DomainInfo(
            name=self.name,
            dtype=self.dtype,
            cardinality=len(self._categories),
            metadata={"ordered": self._ordered, **self.metadata},
        )


class ContinuousDomain(BaseDomain):
    """Numeric domain defined by lower/upper bounds."""
    # 连续数值域：由上/下界与开闭区间标记定义，支持裁剪（clamp）

    def __init__(
        self,
        *,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        inclusive: Tuple[bool, bool] = (True, True),
        name: Optional[str] = None,
        dtype: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        if minimum is not None and maximum is not None and minimum > maximum:
            raise DomainError("minimum must be <= maximum")
        super().__init__(name=name or "ContinuousDomain", dtype=dtype or "float64", metadata=metadata)
        self.minimum = minimum
        self.maximum = maximum
        self.inclusive = inclusive  # (左闭?, 右闭?)

    def contains(self, value: Any) -> bool:
        # 将输入转为 float；若越界或类型不正确则返回 False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        if self.minimum is not None:
            if self.inclusive[0]:
                if numeric < self.minimum:
                    return False
            else:
                if numeric <= self.minimum:
                    return False
        if self.maximum is not None:
            if self.inclusive[1]:
                if numeric > self.maximum:
                    return False
            else:
                if numeric >= self.maximum:
                    return False
        return True

    def clamp(self, value: Any) -> float:
        # 支持裁剪到边界范围内；返回浮点数
        numeric = float(value)
        if self.minimum is not None and numeric < self.minimum:
            numeric = self.minimum
        if self.maximum is not None and numeric > self.maximum:
            numeric = self.maximum
        return numeric

    def describe(self) -> DomainInfo:
        # 描述信息包括边界与开闭标记
        return DomainInfo(
            name=self.name,
            dtype=self.dtype,
            bounds=(self.minimum, self.maximum),
            metadata={"inclusive": self.inclusive, **self.metadata},
        )


class BucketizedDomain(BaseDomain):
    """Domain that maps numeric values into discrete buckets using edges."""
    # 分桶域：通过边界序列将数值映射为离散桶索引；支持二分查找编码与区间解码

    def __init__(
        self,
        edges: Sequence[float],
        *,
        right_inclusive: bool = True,
        name: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        if len(edges) < 2:
            raise DomainError("BucketizedDomain requires at least two edges")
        if sorted(edges) != list(edges):
            raise DomainError("edges must be sorted ascending")
        super().__init__(name=name or "BucketizedDomain", dtype="bucket", metadata=metadata)
        self.edges = tuple(edges)               # 单调递增边界序列
        self.right_inclusive = right_inclusive  # 右端点是否包含

    def contains(self, value: Any) -> bool:
        # 值需在整体边界 [min(edge), max(edge)] 内
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        return self.edges[0] <= numeric <= self.edges[-1]

    def encode(self, value: Any) -> int:
        # 数值 -> 桶索引：二分定位左闭（或右开）区间
        numeric = float(value)
        if not self.contains(numeric):
            raise DomainError(f"value {value!r} outside of bucket range {self.edges}")
        left = 0
        right = len(self.edges) - 1
        # 循环结束时，left 指向所属桶的左边界索引
        while left < right - 1:
            mid = (left + right) // 2
            if numeric < self.edges[mid] or (numeric == self.edges[mid] and not self.right_inclusive):
                right = mid
            else:
                left = mid
        return left

    def decode(self, value: Any) -> Tuple[float, float]:
        # 桶索引 -> 区间 [edge[i], edge[i+1]]
        if isinstance(value, int) and 0 <= value < len(self.edges) - 1:
            return self.edges[value], self.edges[value + 1]
        raise DomainError(f"bucket index {value!r} outside of range")

    def describe(self) -> DomainInfo:
        # 描述信息包括区间总体范围、桶数量与右闭标记
        return DomainInfo(
            name=self.name,
            dtype=self.dtype,
            bounds=(self.edges[0], self.edges[-1]),
            cardinality=len(self.edges) - 1,
            metadata={"right_inclusive": self.right_inclusive, **self.metadata},
        )
