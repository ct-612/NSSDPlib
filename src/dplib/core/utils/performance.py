"""
Performance measurement helpers.

Responsibilities
  - Provide timing utilities for code blocks and callables.
  - Offer basic benchmarking statistics for repeated runs.
  - Expose lightweight memory profiling via tracemalloc.

Usage Context
  - Use for quick local profiling or regression checks.
  - Intended for lightweight, in-process measurements.

Limitations
  - Not a substitute for full profiling suites.
  - Results depend on system load and Python runtime variability.
"""
# 说明：性能测量与基准测试工具集合，用于在库内部统一评估执行耗时与内存占用。
# 职责：
# - Timer：基于上下文管理器与 ContextDecorator 的计时工具，可用于 with 或函数装饰
# - time_function(...)：测量单次函数调用耗时（秒）
# - benchmark(...)：多次重复调用并给出最小值 / 最大值 / 平均值 / 标准差等统计
# - memory_profile(...)：利用 tracemalloc 统计当前与峰值内存使用量（字节）

from __future__ import annotations

import statistics
import time
import tracemalloc
from contextlib import ContextDecorator
from typing import Any, Callable, Dict, Iterable, List


class Timer(ContextDecorator):
    """
    Context manager for timing code blocks.

    - Configuration
      - No explicit configuration; timing starts on entry.

    - Behavior
      - Records start and end timestamps using a high-resolution clock.
      - Exposes elapsed time after exiting the context.

    - Usage Notes
      - Use as a context manager or decorator via ContextDecorator.
    """
    # 计时上下文管理器：进入时记录起始时间，退出时计算耗时（秒）

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        self.end = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start


def time_function(func: Callable[..., Any], *args: Any, **kwargs: Any) -> float:
    """Time a callable and return elapsed seconds."""
    # 使用 Timer 包装单次函数调用，返回运行耗时（秒）
    with Timer() as timer:
        func(*args, **kwargs)
    return timer.elapsed


def benchmark(func: Callable[..., Any], *, repeat: int = 5, warmup: int = 1, **kwargs: Any) -> Dict[str, float]:
    """Run a benchmark and return summary stats."""
    # 先执行若干次 warmup 预热，再重复调用以得到耗时样本并计算统计指标
    for _ in range(warmup):
        func(**kwargs)
    timings: List[float] = [time_function(func, **kwargs) for _ in range(repeat)]
    return {
        "min": min(timings),
        "max": max(timings),
        "mean": statistics.mean(timings),
        "stdev": statistics.pstdev(timings),
    }


def memory_profile(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Dict[str, int]:
    """Profile peak memory usage using tracemalloc."""
    # 启用 tracemalloc 跟踪内存分配，执行函数后返回当前与峰值内存占用
    tracemalloc.start()
    func(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"current_bytes": current, "peak_bytes": peak}

