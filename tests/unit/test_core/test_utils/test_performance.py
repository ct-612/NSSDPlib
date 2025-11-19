"""
Unit tests for performance measurement helpers.
"""
# 说明：性能测量辅助工具（Timer / time_function / benchmark / memory_profile）的单元测试。
# 覆盖：
# - Timer：作为上下文管理器使用时是否正确记录 elapsed 时间
# - time_function(...)：是否返回单次调用的耗时（秒）
# - benchmark(...): 是否返回包含 min/max/mean/stdev 的统计摘要
# - memory_profile(...): 是否返回包含 current_bytes / peak_bytes 的内存使用概览

from time import sleep

from dplib.core.utils import Timer, benchmark, memory_profile, time_function


def dummy_work(delay: float = 0.001) -> None:
    # 模拟带可控延迟的轻量工作负载，用作性能测量目标函数
    sleep(delay)


def test_timer_context_manager() -> None:
    # 验证 Timer 作为上下文管理器使用时，是否会记录正的 elapsed 值
    with Timer() as timer:
        dummy_work(0.001)
    assert timer.elapsed > 0


def test_time_function_returns_elapsed() -> None:
    # 验证 time_function 返回的耗时为非负数
    elapsed = time_function(dummy_work, 0.0)
    assert elapsed >= 0


def test_benchmark_returns_summary() -> None:
    # 验证 benchmark 返回结果至少包含 min/max/mean/stdev 这几个摘要指标
    stats = benchmark(dummy_work, repeat=2, warmup=0, delay=0.0)
    assert {"min", "max", "mean", "stdev"} <= stats.keys()


def test_memory_profile_returns_usage() -> None:
    # 验证 memory_profile 返回的字典中包含当前与峰值内存占用字段
    profile = memory_profile(dummy_work, 0.0)
    assert "current_bytes" in profile and "peak_bytes" in profile
