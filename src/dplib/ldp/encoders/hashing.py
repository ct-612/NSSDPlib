"""
Hash-based encoder for LDP mechanisms such as OLH, sketches, and Bloom filters.

Responsibilities
  - Map values to hash bucket indices using a hash family.
  - Support single or multiple hash outputs per value.
  - Provide metadata for hash configuration.

Usage Context
  - Use when categorical values must be mapped to a smaller hash domain.
  - Intended for mechanisms that operate on hashed indices.

Limitations
  - Hash encoding is not reversible.
  - Collisions are possible by design.
"""
# 说明：通过哈希函数族将类别或键映射到较小的哈希域，常用于 OLH / sketch / Bloom filter等机制，编码不可逆。
# 职责：
# - 校验并保存哈希域大小、哈希函数个数等核心配置
# - 基于 hash family 将输入值稳定映射为单个或多个桶索引
# - 提供元数据导出接口以支持配置记录与复现

from __future__ import annotations

from typing import Any, List, Mapping

from dplib.core.utils.param_validation import ParamValidationError
from .base import StatelessEncoder
from dplib.ldp.ldp_utils import make_hash_family
from dplib.ldp.types import EncodedValue


class HashEncoder(StatelessEncoder):
    """
    Encode arbitrary values into one or multiple hash bucket indices.

    - Configuration
      - num_buckets: Size of the hash domain.
      - num_hashes: Number of hash functions to apply.
      - seed: Seed used to derive hash functions.

    - Behavior
      - Applies one or more hash functions to the input value.
      - Returns a single index or a list of indices.

    - Usage Notes
      - Use with mechanisms that accept hashed indices.
    """

    def __init__(self, num_buckets: int, num_hashes: int = 1, seed: int = 0):
        # 初始化哈希编码器的桶数量、哈希函数个数与随机种子并构造哈希函数族
        if num_buckets <= 0:
            raise ParamValidationError("num_buckets must be positive")
        if num_hashes <= 0:
            raise ParamValidationError("num_hashes must be positive")
        self.num_buckets = int(num_buckets)
        self.num_hashes = int(num_hashes)
        self.seed = int(seed)
        self.hash_functions = make_hash_family(self.num_hashes, self.num_buckets, self.seed)

    def encode(self, value: Any) -> EncodedValue:
        """Return hash bucket(s) for the given value."""
        # 将输入值转为字符串后经多路哈希映射到桶索引，支持单桶或多桶返回形式
        value_str = str(value)
        hashes: List[int] = [fn(value_str) for fn in self.hash_functions]
        if self.num_hashes == 1:
            return int(hashes[0])
        return hashes

    def decode(self, encoded: EncodedValue) -> Any:
        """Hash encoding is not reversible."""
        # 明确声明哈希编码不可逆防止误用解码接口
        raise NotImplementedError("HashEncoder is not reversible")

    def get_metadata(self) -> Mapping[str, Any]:
        """Metadata describing hash parameters."""
        # 返回当前哈希编码器的结构化配置用于日志记录或序列化
        return {
            "type": "hash",
            "num_buckets": self.num_buckets,
            "num_hashes": self.num_hashes,
            "seed": self.seed,
        }
