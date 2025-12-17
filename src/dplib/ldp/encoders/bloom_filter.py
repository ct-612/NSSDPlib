"""Bloom Filter encoder for RAPPOR-style LDP mechanisms."""
# 说明：将输入值通过多路哈希映射到固定长度 Bloom Filter 的若干 bit 位，作为 RAPPOR 等机制的编码前置步骤，编码不可逆。
# 职责：
# - 维护 Bloom Filter 的位数、哈希函数个数与随机种子等静态配置
# - 使用哈希族将输入值编码为适合 RAPPOR 等 LDP 机制消费的位向量表示
# - 提供 Bloom Filter 维度与哈希配置的元数据视图以便调试与文档生成

from __future__ import annotations

from typing import Any, Mapping

from dplib.core.utils.param_validation import ParamValidationError
from .base import StatelessEncoder
from dplib.ldp.ldp_utils import make_bitarray, make_hash_family
from dplib.ldp.types import EncodedValue


class BloomFilterEncoder(StatelessEncoder):
    """Encode values into Bloom Filter bit vectors using multiple hashes."""

    def __init__(self, num_bits: int, num_hashes: int, seed: int = 0):
        # 初始化 Bloom Filter 编码器的位数、哈希函数数量以及随机种子并构造内部哈希函数族
        if num_bits <= 0:
            raise ParamValidationError("num_bits must be positive")
        if num_hashes <= 0:
            raise ParamValidationError("num_hashes must be positive")
        self.num_bits = int(num_bits)
        self.num_hashes = int(num_hashes)
        self.seed = int(seed)
        self.hash_functions = make_hash_family(self.num_hashes, self.num_bits, self.seed)

    def encode(self, value: Any) -> EncodedValue:
        """Return a bit vector with positions from hash functions set to 1."""
        # 将输入值转为字符串后经多路哈希映射为若干索引并在对应 bit 位置置 1
        value_str = str(value)
        indices = [fn(value_str) for fn in self.hash_functions]
        return make_bitarray(self.num_bits, indices)

    def decode(self, encoded: EncodedValue) -> Any:
        """Bloom Filter encoding is not reversible."""
        # 明确声明当前 Bloom Filter 编码不可逆避免误用为值恢复接口
        raise NotImplementedError("BloomFilterEncoder decode is not supported")

    def get_metadata(self) -> Mapping[str, Any]:
        """Metadata describing Bloom Filter dimensions and hash config."""
        # 返回 Bloom Filter 位宽、哈希次数与种子等配置的元数据快照
        return {
            "type": "bloom_filter",
            "num_bits": self.num_bits,
            "num_hashes": self.num_hashes,
            "seed": self.seed,
        }
