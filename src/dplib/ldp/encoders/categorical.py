"""
Categorical encoder for deterministic LDP pipelines.

Responsibilities
  - Maintain a stable category-to-index vocabulary.
  - Encode categories as integer indices or one-hot vectors.
  - Decode indices or one-hot vectors back to categories.

Usage Context
  - Use before local mechanisms that operate on categorical indices.
  - Intended for deterministic encoding in LDP pipelines.

Limitations
  - Unknown values require an explicit unknown_value in the vocabulary.
  - One-hot decoding uses argmax and assumes a valid one-hot vector.
"""
# 说明：为 LDP pipeline 提供最基础的类别编码，负责类别与整数索引/one-hot 之间的确定性映射，典型用于 GRR / OLH 等以整数索引为输入的机制。
# 职责：
# - 维护类别到整数索引以及索引到类别的双向映射
# - 支持基于数据拟合得到稳定词表并处理未知值回退
# - 提供整数索引与 one-hot 表示之间的编码解码能力

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from dplib.core.utils.param_validation import ParamValidationError
from .base import FittedEncoder
from dplib.ldp.types import EncodedValue


class CategoricalEncoder(FittedEncoder):
    """
    Map categorical values to stable integer indices (and back).

    Can be initialised with an explicit category list or learn it via fit().

    - Configuration
      - categories: Optional category list used to build the vocabulary.
      - unknown_value: Placeholder for unseen categories if included.

    - Behavior
      - Encodes categories to integer indices and decodes them back.
      - Supports one-hot encoding and decoding.

    - Usage Notes
      - Call fit when categories are not supplied at construction.
    """

    def __init__(self, categories: Optional[Sequence[Any]] = None, unknown_value: str = "<UNK>"):
        # 初始化类别编码器，可选使用预设类别列表并配置未知值占位符
        super().__init__()
        self.unknown_value = unknown_value
        self.value_to_index: Dict[Any, int] = {}
        self.index_to_value: List[Any] = []

        if categories is not None:
            self._build_vocab(categories)
            self._mark_fitted()

    def _build_vocab(self, categories: Sequence[Any]) -> None:
        """Construct vocabulary mappings preserving order."""
        # 根据给定类别序列构建去重且顺序稳定的词表映射
        self.value_to_index.clear()
        self.index_to_value.clear()
        for value in categories:
            if value in self.value_to_index:
                continue
            idx = len(self.index_to_value)
            self.value_to_index[value] = idx
            self.index_to_value.append(value)

    def fit(self, data: Iterable[Any]) -> "CategoricalEncoder":
        """Collect distinct values from data in order of appearance."""
        # 从数据中按出现顺序收集唯一类别并构建词表然后标记编码器已拟合
        self._build_vocab(list(dict.fromkeys(data)))  # preserve order while deduplicating
        # 保持原始出现顺序同时去重以构造稳定词表
        self._mark_fitted()
        return self

    def encode(self, value: Any) -> EncodedValue:
        """Encode category to integer index; falls back to unknown_value when present."""
        # 将类别值编码为整数索引，不存在时尝试回退到 unknown_value 对应索引
        self._ensure_fitted()
        if value in self.value_to_index:
            return int(self.value_to_index[value])
        if self.unknown_value in self.value_to_index:
            return int(self.value_to_index[self.unknown_value])
        raise ParamValidationError(
            f"value '{value}' not in vocabulary and unknown_value not configured"
        )

    def decode(self, encoded: EncodedValue) -> Any:
        """Map integer index back to the original category."""
        # 将整数索引解码回原始类别并对类型和索引越界进行校验
        self._ensure_fitted()
        if not isinstance(encoded, (int, np.integer)):
            raise ParamValidationError("encoded value for categorical decode must be an int")
        idx = int(encoded)
        if idx < 0 or idx >= len(self.index_to_value):
            raise ParamValidationError(f"encoded index {idx} out of range")
        return self.index_to_value[idx]

    def encode_one_hot(self, value: Any) -> np.ndarray:
        """Encode category into a one-hot numpy vector of length = num_classes."""
        # 将单个类别编码为长度等于类别数的 one-hot 向量供后续数值机制或模型使用
        self._ensure_fitted()
        idx = int(self.encode(value))
        vec = np.zeros(len(self.index_to_value), dtype=int)
        vec[idx] = 1
        return vec

    def decode_one_hot(self, vec: np.ndarray) -> Any:
        """Decode one-hot vector back to category via argmax."""
        # 通过 argmax 从 one-hot 向量恢复类别并检查向量维度与词表大小一致
        self._ensure_fitted()
        if vec.ndim != 1 or len(vec) != len(self.index_to_value):
            raise ParamValidationError("one-hot vector has incompatible shape")
        idx = int(np.argmax(vec))
        return self.decode(idx)

    def get_metadata(self) -> Mapping[str, Any]:
        """Return metadata describing category vocabulary and unknown handling."""
        # 返回包含类别列表与未知值占位符配置的元数据便于持久化与调试
        return {
            "type": "categorical",
            "categories": list(self.index_to_value),
            "unknown_value": self.unknown_value,
        }
