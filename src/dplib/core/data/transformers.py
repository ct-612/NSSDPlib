"""
Composable data transformers and lightweight pipeline utilities.

Included transformers:
    * ClippingTransformer: clamp numeric fields
    * NormalizationTransformer: scale to [0, 1] or z-score
    * DiscretizerTransformer: bucketize numeric values
    * OneHotEncoder: expand categorical columns
    * TransformerPipeline: orchestrate multi-step transformations
"""
# 说明：可组合的数据转换器与轻量级流水线工具。
# 职责：
# - 提供可组合的数据转换器与轻量流水线工具，支持裁剪、归一化、离散化、独热编码等常见预处理
# - 通过统一的 DataTransformer 接口实现可插拔、可复用、可顺序组合的处理流程

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

import math


Record = Mapping[str, Any]
MutableRecord = MutableMapping[str, Any]
# 记录类型别名：
# - Record 为不可变映射（输入）
# - MutableRecord 为可变映射（就地修改输出）


class TransformationError(RuntimeError):
    """Raised when a transformer cannot process input data."""
    # 转换器无法处理输入（如缺统计参数/越界/策略非法）时抛出的统一异常


class DataTransformer(ABC):
    """Abstract base class for stateless/stateful transformers."""
    # 转换器抽象基类：既可无状态（如裁剪），也可有状态（如需先 fit 的归一化）

    def __init__(self, *, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    def fit(self, data: Iterable[Record]) -> "DataTransformer":
        """Optional hook to collect statistics."""
        # 可选的拟合阶段：收集统计量（均值/方差/范围等），默认无操作
        return self

    @abstractmethod
    def transform_record(self, record: MutableRecord) -> MutableRecord:
        """Apply transformation in-place to a record."""
        # 就地修改单条记录的核心接口；子类必须实现

    def __call__(self, record: Record) -> MutableRecord:
        # 使实例可调用：复制输入记录为可变字典，再交由 transform_record 处理
        updated = dict(record)
        return self.transform_record(updated)


class ClippingTransformer(DataTransformer):
    """Clip numeric fields to a bounded interval."""
    # 裁剪转换器：将数值字段裁剪到给定 [min, max] 区间内

    def __init__(self, field: str, *, minimum: Optional[float] = None, maximum: Optional[float] = None):
        super().__init__(name=f"Clip[{field}]")
        if minimum is None and maximum is None:
            raise TransformationError("ClippingTransformer requires min/max bound")
        self.field = field
        self.minimum = minimum
        self.maximum = maximum

    def transform_record(self, record: MutableRecord) -> MutableRecord:
        value = record.get(self.field)
        if value is None:
            return record  # 缺失值不处理，直接返回
        numeric = float(value)
        if self.minimum is not None and numeric < self.minimum:
            numeric = self.minimum
        if self.maximum is not None and numeric > self.maximum:
            numeric = self.maximum
        record[self.field] = numeric
        return record


class NormalizationTransformer(DataTransformer):
    """Normalize numeric fields using min-max or z-score strategy."""
    # 归一化转换器：支持两种归一化策略
    # - "min-max 最小最大": 线性缩放到 [0,1]
    # - "z-score 标准分数": 减均值、除标准差（ z = (x − μ) ​/ σ ）

    def __init__(self, field: str, *, strategy: str = "minmax"):
        super().__init__(name=f"Normalize[{field}]")
        if strategy not in {"minmax", "zscore"}:
            raise TransformationError("strategy must be 'minmax' or 'zscore'")
        self.field = field
        self.strategy = strategy
        self._params: Optional[Dict[str, float]] = None  # 拟合后保存参数

    def fit(self, data: Iterable[Record]) -> "NormalizationTransformer":
        # 拟合阶段收集 min/max 或 mean/std
        values = [float(record[self.field]) for record in data if self.field in record and record[self.field] is not None]
        if not values:
            raise TransformationError(f"no values available to fit field '{self.field}'")
        if self.strategy == "minmax":
            self._params = {"min": min(values), "max": max(values)}
        else:
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)  # 样本方差（ddof=1）
            self._params = {"mean": mean, "std": math.sqrt(var) or 1.0}  # std 为 0 时回退为 1 以避免除零
        return self

    def transform_record(self, record: MutableRecord) -> MutableRecord:
        if not self._params:
            raise TransformationError("NormalizationTransformer must be fitted before use")
        value = record.get(self.field)
        if value is None:
            return record
        numeric = float(value)
        if self.strategy == "minmax":
            span = self._params["max"] - self._params["min"] or 1.0  # 避免 span 为 0
            numeric = (numeric - self._params["min"]) / span
        else:
            numeric = (numeric - self._params["mean"]) / self._params["std"]
        record[self.field] = numeric
        return record


class DiscretizerTransformer(DataTransformer):
    """Map numeric fields into bucket ids using provided edges."""
    # 离散化：将数值字段按边界切分到离散桶，输出桶索引（0..n-2）

    def __init__(self, field: str, edges: Sequence[float]):
        super().__init__(name=f"Discretize[{field}]")
        if len(edges) < 2:
            raise TransformationError("DiscretizerTransformer requires at least two edges")
        self.field = field
        self.edges = list(edges)

    def transform_record(self, record: MutableRecord) -> MutableRecord:
        value = record.get(self.field)
        if value is None:
            return record
        numeric = float(value)
        if numeric < self.edges[0] or numeric > self.edges[-1]:
            raise TransformationError(f"value {numeric} outside of discretizer range")
        # 选择最大满足 numeric >= edge 的下标作为桶编号（最后一个右端点包含）
        bucket = max(idx for idx, edge in enumerate(self.edges[:-1]) if numeric >= edge)
        record[self.field] = bucket
        return record


class OneHotEncoder(DataTransformer):
    """Expand a categorical field into multiple binary indicators."""
    # 独热编码器：将类别字段展开为多列 0/1 指示器，并移除原字段

    def __init__(self, field: str, categories: Sequence[Any]):
        super().__init__(name=f"OneHot[{field}]")
        if not categories:
            raise TransformationError("OneHotEncoder requires categories")
        self.field = field
        self.categories = list(dict.fromkeys(categories))  # 去重且保留顺序

    def transform_record(self, record: MutableRecord) -> MutableRecord:
        value = record.get(self.field)
        for category in self.categories:
            record[f"{self.field}__{category}"] = 1.0 if value == category else 0.0
        record.pop(self.field, None)  # 删除原始字段，避免重复
        return record


@dataclass
class TransformerPipeline:
    """Composable pipeline that executes transformers in sequence."""
    # 可组合流水线：用于顺序执行多个转换器，fit 阶段逐步流水化更新中间数据

    steps: List[DataTransformer]

    def fit(self, data: Iterable[Record]) -> "TransformerPipeline":
        # 逐步拟合 并 "就地"应用于工作数据，使后续转换器能使用前置转换后的特征统计
        working_data = list(data)
        for transformer in self.steps:
            transformer.fit(working_data)
            working_data = [transformer(record) for record in working_data]
        return self

    def transform(self, record: Record) -> MutableRecord:
        # 对单条记录按顺序应用所有步骤，返回转换后的可变字典
        current = dict(record)
        for transformer in self.steps:
            current = transformer(current)
        return current

    def map(self, data: Iterable[Record]) -> List[MutableRecord]:
        # 对批量数据进行转换并返回列表
        return [self.transform(record) for record in data]
