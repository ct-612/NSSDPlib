"""LDP-focused utility helpers for hash families, bit operations, and parameter validation."""
# 说明：为 LDP 子系统提供哈希族构造、比特向量操作与参数校验等通用工具函数。
# 职责：
# - 封装基于 xxhash 或 mmh3 的哈希落桶逻辑并支持构造独立哈希函数族
# - 提供基于 bitarray 或普通列表的比特向量创建与统计操作
# - 校验概率与 epsilon 等关键 DP 参数范围并实现 sigmoid/logit 等数值工具

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Union

import numpy as np
from dplib.core.utils.param_validation import ParamValidationError

try:
    import xxhash
except Exception:  # pragma: no cover - optional dependency
    # 可选依赖 xxhash 缺失时不计入覆盖率并在后续逻辑中回退到其他实现
    xxhash = None  # type: ignore

try:
    import mmh3
except Exception:  # pragma: no cover - optional dependency
    # 可选依赖 mmh3 缺失时不计入覆盖率并在后续逻辑中视为不可用
    mmh3 = None  # type: ignore

try:
    from bitarray import bitarray as _BitArrayRuntime
except Exception:  # pragma: no cover - optional dependency
    # 可选依赖 bitarray 缺失时退化为 None，相关功能使用纯 Python 列表替代
    _BitArrayRuntime = None  # type: ignore

if TYPE_CHECKING:
    from bitarray import bitarray as BitArrayType
else:
    BitArrayType = Any

BitVector = Union["BitArrayType", List[int]]
# 表示基于 bitarray 或普通 int 列表的比特向量类型别名


def hash_to_range(value: Union[str, bytes], seed: int, num_buckets: int) -> int:
    """
    Hash value into [0, num_buckets) using xxhash (preferred) or mmh3 as fallback.

    Raises:
        ValueError: if num_buckets <= 0.
        ImportError: if neither xxhash nor mmh3 is available.
    """
    # 使用可用的哈希库将输入 value 映射到 [0, num_buckets) 区间，并根据 seed 控制哈希族
    if num_buckets <= 0:
        raise ParamValidationError("num_buckets must be positive")

    if xxhash is not None:
        payload = value.encode("utf-8") if isinstance(value, str) else value
        if not isinstance(payload, (bytes, bytearray)):
            raise ParamValidationError("value must be str or bytes")
        digest = xxhash.xxh64(payload, seed=seed).intdigest()
    elif mmh3 is not None:
        if isinstance(value, bytes):
            payload_str = value.decode("utf-8", errors="ignore")
        elif isinstance(value, str):
            payload_str = value
        else:
            raise ParamValidationError("value must be str or bytes")
        digest = mmh3.hash(payload_str, seed=seed, signed=False)
    else:
        raise ImportError("xxhash or mmh3 is required for hashing")

    return int(digest % num_buckets)


def make_hash_family(num_hashes: int, num_buckets: int, seed: int) -> List[Callable[[str], int]]:
    """
    Create a family of independent hash functions mapping strings into [0, num_buckets).
    """
    # 构造一组相互独立的哈希函数，将字符串映射到固定桶数的索引空间
    if num_hashes <= 0:
        raise ParamValidationError("num_hashes must be positive")
    if num_buckets <= 0:
        raise ParamValidationError("num_buckets must be positive")

    hash_functions: List[Callable[[str], int]] = []
    for i in range(num_hashes):
        sub_seed = seed + i * 0x9E3779B1  # ensure varied seeds
        # 使用不同的子 seed 保证每个哈希函数的随机性差异

        def _fn(value: str, _seed=sub_seed) -> int:
            return hash_to_range(value, seed=_seed, num_buckets=num_buckets)

        hash_functions.append(_fn)
    return hash_functions


def make_bitarray(length: int, indices: Iterable[int] = ()) -> BitVector:
    """
    Create a bit vector of given length and set positions in indices to 1.
    """
    # 创建指定长度的比特向量并将给定 indices 位置置为 1，优先使用 bitarray 实现
    if length < 0:
        raise ParamValidationError("length must be non-negative")

    if _BitArrayRuntime is not None:
        bits = _BitArrayRuntime(length)
        bits.setall(False)
        for idx in indices:
            if 0 <= idx < length:
                bits[idx] = True
        return bits

    bits_list = [0] * length
    for idx in indices:
        if 0 <= idx < length:
            bits_list[idx] = 1
    return bits_list


def bitarray_to_indices(bits: BitVector) -> List[int]:
    """Return indices where the bit vector has value 1."""
    # 将比特向量中为 1 的位置提取为索引列表返回
    return [i for i, bit in enumerate(bits) if bool(bit)]


def count_ones(bits: BitVector) -> int:
    """Count the number of set bits."""
    # 统计比特向量中被置为 1 的比特个数
    if _BitArrayRuntime is not None and isinstance(bits, _BitArrayRuntime):
        return bits.count()
    return int(sum(1 for b in bits if b))


def ensure_probability(p: float, name: str = "p") -> None:
    """Ensure p is within [0, 1]; otherwise raise ParamValidationError."""
    # 校验给定概率参数是否落在 [0, 1] 区间内，非法时抛出 ParamValidationError
    if not (0.0 <= p <= 1.0):
        raise ParamValidationError(f"{name} must be within [0, 1]")


def ensure_epsilon(epsilon: float) -> None:
    """Ensure epsilon is positive; otherwise raise ParamValidationError."""
    # 校验隐私预算 epsilon 是否为正数，非法时抛出 ParamValidationError
    if epsilon <= 0:
        raise ParamValidationError("epsilon must be positive")


def sigmoid(x: float) -> float:
    """Compute sigmoid using numpy for stability."""
    # 使用 numpy 实现数值稳定的 sigmoid 函数转换
    return float(1.0 / (1.0 + np.exp(-x)))


def logit(p: float) -> float:
    """Compute logit(p) where p in (0, 1); raises ParamValidationError otherwise."""
    # 在 p ∈ (0, 1) 条件下计算 logit 变换，边界值时抛出异常
    ensure_probability(p, name="p")
    if p in (0.0, 1.0):
        raise ParamValidationError("p must be in (0, 1) for logit")
    return float(np.log(p / (1.0 - p)))
