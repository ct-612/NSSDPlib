"""
Unary and fixed-length binary encoders for LDP bit-vector mechanisms.

Responsibilities
  - Encode integer indices into unary or fixed-length binary vectors.
  - Decode unary and binary vectors back to integer indices.
  - Provide metadata describing encoding configuration.

Usage Context
  - Use with bit-vector LDP mechanisms such as OUE or unary randomizers.
  - Intended for deterministic encoding before perturbation.

Limitations
  - Unary decoding requires exactly one active bit.
  - Binary encoding is limited by the configured bit width.
"""
# 说明：为 OUE / UnaryRandomizer / RAPPOR 等机制提供基础的 bit 向量编码，对整数索引进行 unary 或定长二进制表示的确定性映射。
# 职责：
# - 校验 unary 与二进制编码的长度参数并保证索引范围合法
# - 提供整数值到 bit 向量的一一映射以及可逆的 decode 接口
# - 暴露编码元数据以便在配置、日志或模型复现中使用

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from dplib.core.utils.param_validation import ParamValidationError
from .base import StatelessEncoder
from dplib.ldp.ldp_utils import bitarray_to_indices, count_ones, make_bitarray
from dplib.ldp.types import EncodedValue


class UnaryEncoder(StatelessEncoder):
    """
    Encode integer indices into unary 0/1 vectors and decode back.

    - Configuration
      - length: Length of the unary vector.

    - Behavior
      - Encodes a single active bit at the given index.
      - Decodes only when exactly one bit is active.

    - Usage Notes
      - Input values must be in the range [0, length).
    """
    # 提供整数类别索引到 unary 向量的编码与解码能力，用于 UnaryRandomizer/OUE/RAPPOR 等 LDP 机制

    def __init__(self, length: int):
        # 校验并记录 unary 向量长度参数，后续用于索引范围检查
        if length <= 0:
            raise ParamValidationError("length must be positive for UnaryEncoder")
        self.length = int(length)

    def encode(self, value: int) -> EncodedValue:
        """Return a unary vector with a single 1 at the given index."""
        # 将合法索引位置置为 1 其余为 0 生成对应的 unary bit 向量
        if not isinstance(value, int) or value < 0 or value >= self.length:
            raise ParamValidationError(f"value must be int in [0, {self.length})")
        return make_bitarray(self.length, [value])

    def decode(self, encoded: EncodedValue) -> int:
        """Recover index from unary vector; require exactly one active bit."""
        # 要求 unary 向量中恰好存在一个激活位，否则视为无效编码
        indices = bitarray_to_indices(encoded)  # type: ignore[arg-type]
        if len(indices) != 1 or count_ones(encoded) != 1:
            raise ParamValidationError("unary vector must contain exactly one active bit")
        return int(indices[0])

    def get_metadata(self) -> Mapping[str, Any]:
        """Metadata describing unary vector length."""
        # 返回 unary 编码长度等元数据便于序列化与调试
        return {"type": "unary", "length": self.length}


class BinaryEncoder(StatelessEncoder):
    """
    Encode integer values into fixed-length binary vectors (MSB-first).

    - Configuration
      - num_bits: Bit width of the encoded representation.

    - Behavior
      - Encodes non-negative integers into big-endian bit vectors.
      - Decodes bit vectors back to integer values.

    - Usage Notes
      - Values must fit within the configured bit width.
    """
    # 支持将非负整数编码为固定长度的大端二进制向量并提供可逆解码

    def __init__(self, num_bits: int):
        # 校验并记录二进制编码位宽，用于后续范围与形状检查
        if num_bits <= 0:
            raise ParamValidationError("num_bits must be positive for BinaryEncoder")
        self.num_bits = int(num_bits)

    def encode(self, value: int) -> EncodedValue:
        """Encode integer into a big-endian binary vector of length num_bits."""
        # 非负整数按大端顺序展开为固定长度 bit 向量，超出表示范围则抛出异常
        if not isinstance(value, int) or value < 0:
            raise ParamValidationError("value must be a non-negative int")
        max_value = 1 << self.num_bits
        if value >= max_value:
            raise ParamValidationError(f"value {value} does not fit in {self.num_bits} bits")

        bits = np.zeros(self.num_bits, dtype=int)
        for i in range(self.num_bits):
            # MSB-first: 从最高位到最低位依次写入对应比特值
            shift = self.num_bits - 1 - i
            bits[i] = (value >> shift) & 1
        return bits

    def decode(self, encoded: EncodedValue) -> int:
        """Decode big-endian binary vector back to integer."""
        # 将固定长度大端 bit 向量按位累积还原为整数值
        if not hasattr(encoded, "__iter__"):
            raise ParamValidationError("encoded value must be an iterable of bits")

        bits = list(int(b) for b in encoded)  # type: ignore[arg-type]
        if len(bits) != self.num_bits:
            raise ParamValidationError(f"binary vector must have length {self.num_bits}")

        value = 0
        for bit in bits:
            value = (value << 1) | (1 if bit else 0)
        return int(value)

    def get_metadata(self) -> Mapping[str, Any]:
        """Metadata describing binary encoding width."""
        # 返回二进制编码位宽等元数据供上层配置与文档使用
        return {"type": "binary", "num_bits": self.num_bits}
