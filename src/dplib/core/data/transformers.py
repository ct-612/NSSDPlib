"""
Composable data transformers and lightweight pipeline utilities for record-like data.
The module provides record-level transformations and a sequential pipeline
for simple preprocessing steps.

Responsibilities
  - Define a base interface for record transformers with optional fitting.
  - Provide common transformations for numeric and categorical fields.
  - Offer a simple sequential pipeline for multi-step preprocessing.

Usage Context
  - Use for lightweight preprocessing of mapping-based records before downstream analysis or modeling.
  - Designed for record-wise transformation where fields are accessed by name.

Limitations
  - Does not perform schema validation, missing-value imputation, or global type harmonization.
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
    """
    Exception raised when a transformer cannot process input data or configuration.

    - Configuration
      - No additional fields beyond the standard exception message.
    
    - Behavior
      - Signals invalid configuration, missing fit state, or inputs outside allowed bounds.
    
    - Usage Notes
      - Raise to indicate that a transformation step cannot proceed.
    """
    # 转换器无法处理输入（如缺统计参数/越界/策略非法）时抛出的统一异常


class DataTransformer(ABC):
    """
    Base interface for record-level transformations that may require fitting.

    - Configuration
      - name: Optional identifier used for display; defaults to the class name.
    
    - Behavior
      - fit may collect statistics from records and returns self.
      - transform_record updates a mutable record in-place and returns it.
      - Calling the instance applies the transformation to a copied record.
    
    - Usage Notes
      - Subclasses implement transform_record; override fit only when statistics are needed.
    """
    # 转换器抽象基类：既可无状态（如裁剪），也可有状态（如需先 fit 的归一化）

    def __init__(self, *, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    def fit(self, data: Iterable[Record]) -> "DataTransformer":
        """Optional hook to collect statistics from records; default implementation is a no-op that returns self."""
        # 可选的拟合阶段：收集统计量（均值/方差/范围等），默认无操作
        return self

    @abstractmethod
    def transform_record(self, record: MutableRecord) -> MutableRecord:
        """Apply the transformation in-place to a mutable record and return the updated record."""
        # 就地修改单条记录的核心接口；子类必须实现

    def __call__(self, record: Record) -> MutableRecord:
        # 使实例可调用：复制输入记录为可变字典，再交由 transform_record 处理
        updated = dict(record)
        return self.transform_record(updated)


class ClippingTransformer(DataTransformer):
    """
    Clamp a numeric field to a bounded interval if limits are provided.

    - Configuration
      - field: Name of the numeric field to clip.
      - minimum: Optional lower bound.
      - maximum: Optional upper bound.
    
    - Behavior
      - Leaves records unchanged when the field is missing or None.
      - Casts the value to float and enforces provided bounds.
    
    - Usage Notes
      - Use to constrain outliers before downstream processing.
    """
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
    """
    Normalize a numeric field using min-max scaling or z-score standardization.

    - Configuration
      - field: Name of the numeric field to normalize.
      - strategy: "minmax" for [0, 1] scaling or "zscore" for standardization.
    
    - Behavior
      - fit computes statistics from available non-None values for the field.
      - transform_record requires prior fit and leaves missing values unchanged.
      - If the fitted scale is zero, a unit scale is used to avoid division by zero.
    
    - Usage Notes
      - Apply when a consistent numeric scale is required across records.
    """
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
    """
    Discretize a numeric field into bucket indices defined by provided edges.

    - Configuration
      - field: Name of the numeric field to bucketize.
      - edges: Sequence of bucket boundaries; the first and last define the allowed range.
    
    - Behavior
      - Requires input values to fall within the inclusive range of the edge endpoints.
      - Maps each value to an integer bucket index based on where it falls between edges.
    
    - Usage Notes
      - Use when converting continuous values into categorical bins.
    """
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
    """
    Expand a categorical field into binary indicator fields.

    - Configuration
      - field: Name of the categorical field to encode.
      - categories: Sequence of categories; duplicates are removed while preserving order.
    
    - Behavior
      - Adds one indicator field per category using the "{field}__{category}" naming pattern.
      - Each indicator is 1.0 when the record value matches the category, otherwise 0.0.
      - Removes the original field from the output record.
    
    - Usage Notes
      - Use to convert categorical values into numeric features.
    """
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
    """
    Sequential pipeline for fitting and applying multiple transformers.

    - Configuration
      - steps: List of DataTransformer instances executed in order.
    
    - Behavior
      - fit runs each step on the current working data so later steps see prior transformations.
      - transform applies all steps in order to a single record and returns the transformed copy.
      - map transforms an iterable of records and returns a list of results.
    
    - Usage Notes
      - Use to compose preprocessing steps into a reusable pipeline.
    """
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
