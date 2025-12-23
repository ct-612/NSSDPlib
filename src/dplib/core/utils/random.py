"""
Random number generation helpers.

Responsibilities
  - Centralize RNG creation and seeding.
  - Provide reproducible splits for parallel workloads.
  - Offer noise sampling helpers used by mechanisms and tests.

Usage Context
  - Use when a consistent RNG interface is needed across modules.
  - Supports parallel-safe sampling via RNG splitting or pooling.

Limitations
  - Relies on numpy Generator behavior for reproducibility.
  - Distribution support is limited to the implemented options.
"""
# 说明：随机数生成与噪声采样辅助工具，用于在库中统一管理 RNG 的创建、复用与分配。
# 职责：
# - create_rng / reseed_rng：集中封装 numpy Generator 的创建与重置逻辑，支持显式种子与已有生成器
# - split_rng：从单一 RNG 派生出多个独立生成器，便于并行或多通道采样
# - sample_noise：按分布名称统一调度到拉普拉斯 / 高斯 / 均匀噪声采样接口，便于机制与测试代码使用
# - RNGPool：维护一组可复用的 Generator 池，通过索引获取，支持整体重置，保证并行环境下采样可复现

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

import numpy as np


def create_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Create a numpy Generator from a seed, SeedSequence, or existing generator."""
    # 将输入规范化为 numpy.random.Generator；若已是 Generator 则直接返回
    if isinstance(seed, np.random.Generator):
        return seed
    return np.random.default_rng(seed)


def reseed_rng(rng: np.random.Generator, seed: Optional[int]) -> np.random.Generator:
    """Replace RNG state with a new seed; returns the generator for chaining."""
    # 用新的种子生成状态并替换给定 rng 的内部状态，保持对象标识不变，方便链式调用
    new_state = create_rng(seed).bit_generator.state
    rng.bit_generator.state = new_state
    return rng


def split_rng(rng: np.random.Generator, num: int) -> List[np.random.Generator]:
    """Split an RNG into `num` independent generators."""
    # 基于底层 SeedSequence.spawn 从单一 RNG 派生出 num 个彼此独立的生成器
    if num <= 0:
        raise ValueError("num must be positive")
    seeds = rng.bit_generator._seed_seq.spawn(num)  # type: ignore[attr-defined]
    return [np.random.default_rng(seed) for seed in seeds]


def sample_noise(
    rng: np.random.Generator,
    distribution: str,
    size: Optional[Sequence[int]] = None,
    **kwargs,
) -> np.ndarray:
    """Sample noise for a given distribution with named parameters."""
    # 统一按 distribution 名称分派到不同分布的噪声采样接口，并支持 loc/scale 等命名参数
    distribution = distribution.lower()
    if distribution == "laplace":
        return rng.laplace(kwargs.get("loc", 0.0), kwargs["scale"], size=size)
    if distribution == "gaussian" or distribution == "normal":
        return rng.normal(kwargs.get("loc", 0.0), kwargs["scale"], size=size)
    if distribution == "uniform":
        return rng.uniform(kwargs.get("low", 0.0), kwargs.get("high", 1.0), size=size)
    raise ValueError(f"unsupported distribution '{distribution}'")


@dataclass
class RNGPool:
    """
    Manage a pool of RNGs for parallel-safe sampling.

    - Configuration
      - base_seed: Optional seed used to initialize the pool.
      - pool_size: Number of generators maintained in the pool.

    - Behavior
      - Splits a base RNG into independent generators.
      - Provides indexed access and full reseeding.

    - Usage Notes
      - Use when parallel tasks need independent RNG streams.
    """

    base_seed: Optional[int] = None
    pool_size: int = 4
    _pool: List[np.random.Generator] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        # 基于 base_seed 创建基础 RNG，并通过 split_rng 初始化固定大小的生成器池
        base = create_rng(self.base_seed)
        self._pool = split_rng(base, self.pool_size)

    def get(self, index: int) -> np.random.Generator:
        # 通过索引循环获取池中的某个 RNG，避免索引越界
        return self._pool[index % self.pool_size]

    def reseed(self, seed: Optional[int]) -> None:
        # 使用新的基础种子重建整个生成器池，以获得一组新的独立 RNG
        base = create_rng(seed)
        self._pool = split_rng(base, self.pool_size)

