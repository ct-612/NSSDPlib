"""
Unit tests for validation helpers and decorators.
"""
# 说明：参数与状态验证工具（ensure / ensure_type / validate_arguments）的单元测试。
# 覆盖：
# - ensure：在条件为真时静默通过，条件为假时抛出 ParamValidationError
# - ensure_type：检查值是否属于给定类型集合，否则抛出带 label 的 ParamValidationError
# - validate_arguments：按 schema 自动验证函数参数的装饰器行为（成功路径与错误路径）

import pytest

from dplib.core.utils import ParamValidationError, ensure, ensure_type, validate_arguments


def test_ensure_passes_and_fails() -> None:
    # 验证 ensure 在条件为 True 时不抛错，条件为 False 时抛 ParamValidationError
    ensure(True, "should not raise")
    with pytest.raises(ParamValidationError):
        ensure(False, "error")


def test_ensure_type_checks() -> None:
    # 验证 ensure_type 对正确类型通过，对错误类型抛 ParamValidationError
    ensure_type(5, (int,), label="value")
    with pytest.raises(ParamValidationError):
        ensure_type("text", (int,), label="value")


def test_validate_arguments_decorator() -> None:
    # 验证 validate_arguments 装饰器按 schema 调用验证器并在类型错误时抛 ParamValidationError
    def validator(value):
        # 简单验证器：要求 value 为 int，否则由 ensure_type 抛错
        ensure_type(value, (int,), label="x")
        return value

    @validate_arguments({"x": validator})
    def add_one(x: int) -> int:
        # 被装饰函数：对通过验证的参数执行 +1
        return x + 1

    assert add_one(4) == 5
    with pytest.raises(ParamValidationError):
        add_one("bad")  # type: ignore[arg-type]
