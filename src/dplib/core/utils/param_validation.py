"""
Reusable validation helpers and decorators.
"""
# 说明：参数验证相关的辅助函数与装饰器，用于在库内部统一进行轻量级参数检查与转换。
# 职责：
# - ParamValidationError：专门用于参数校验失败的异常类型
# - ensure：基于布尔条件触发参数校验错误的轻量断言工具
# - ensure_type：检查参数是否属于指定类型集合，并在失败时给出带 label 的错误提示
# - validate_arguments：根据 schema 为函数参数应用验证/转换逻辑的装饰器，统一处理位置参数与关键字参数

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Mapping, Tuple, Type


class ParamValidationError(ValueError):
    """Raised when parameter validation fails."""


def ensure(condition: bool, message: str, *, error: Type[Exception] = ParamValidationError) -> None:
    # 条件不满足时抛出指定的异常类型（默认使用 ParamValidationError）
    if not condition:
        raise error(message)


def ensure_type(value: Any, expected: Tuple[type, ...], *, label: str = "value") -> None:
    # 检查 value 是否为 expected 集合中的任意类型，否则抛出带字段标签的 ParamValidationError
    if not isinstance(value, expected):
        names = ", ".join(t.__name__ for t in expected)
        raise ParamValidationError(f"{label} must be instance of {names}")


def validate_arguments(schema: Mapping[str, Callable[[Any], Any]]) -> Callable:
    """
    Decorator validating arguments according to callables.

    Each validator receives the argument and should return the (possibly
    transformed) value or raise ParamValidationError.
    """
    # 装饰器根据给定的可调用对象对参数进行验证/转换
    # schema：以参数名为键、验证/转换函数为值的映射，用于在调用前统一处理入参

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 将位置参数复制为可变列表，便于按索引就地修改
            mutable = list(args)
            # 将关键字参数复制为普通字典，避免修改调用方实参对象
            kw: Dict[str, Any] = dict(kwargs)
            for name, validator in schema.items():
                # 若该参数以关键字形式传入，直接应用验证器进行校验/转换
                if name in kw:
                    kw[name] = validator(kw[name])
                    continue
                # 若参数名不在函数形参列表中(可能是多余 schema 条目)，跳过，忽略该 schema 项
                if name not in func.__code__.co_varnames:
                    continue
                # 若参数名在函数形参列表中，定位参数名在形参列表中的索引
                index = func.__code__.co_varnames.index(name)
                # 若 index 超出当前传入位置参数个数，说明未显式提供对应位置参数(使用默认值或未传)，跳过，不强制验证
                if index >= len(mutable):
                    continue
                # 对应位置参数存在，则应用验证器进行校验/转换
                mutable[index] = validator(mutable[index])
            return func(*tuple(mutable), **kw)

        return wrapper

    return decorator

