"""Base abstractions for deterministic LDP encoders."""
# 说明：定义 LDP 编码层的基础接口，负责原始值与 EncodedValue 之间的确定性映射，不引入任何随机性，供编码器与聚合器复用。
# 职责：
# - 为本地差分隐私流水线中的编码器定义统一的抽象基类
# - 区分无状态编码器与需预先拟合状态的编码器两大类
# - 约定 fit/encode/decode/get_metadata 等最小方法集合以便编码与聚合组件复用

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping

from dplib.ldp.types import EncodedValue


class BaseEncoder(ABC):
    """
    Minimal deterministic encoding/decoding interface for LDP pipelines.

    Encoders should transform raw values into EncodedValue without adding noise,
    and, when possible, support decoding back to the original representation.
    """

    @abstractmethod
    def fit(self, data: Iterable[Any]) -> "BaseEncoder":
        """Optional pre-processing step; returns self for chaining."""
        # 可选预处理或拟合步骤，通常用于收集统计量并返回自身以支持链式调用
        raise NotImplementedError

    @abstractmethod
    def encode(self, value: Any) -> EncodedValue:
        """Encode a raw value into an EncodedValue consumable by LDP mechanisms."""
        # 将原始值编码为 EncodedValue 表示以供后续 LDP 机制使用
        raise NotImplementedError

    @abstractmethod
    def decode(self, encoded: EncodedValue) -> Any:
        """Decode an EncodedValue back to the raw representation when feasible."""
        # 在可行情况下将 EncodedValue 解码回接近原始语义的表示
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> Mapping[str, Any]:
        """Return JSON-serializable metadata describing the encoding scheme."""
        # 返回描述编码方案配置与形态的 JSON 可序列化元数据
        raise NotImplementedError


class StatelessEncoder(BaseEncoder):
    """
    Base class for encoders that require no fitting state.

    Provides a no-op fit and a minimal metadata payload; encode/decode remain
    abstract to be implemented by subclasses.
    """

    def fit(self, data: Iterable[Any]) -> "StatelessEncoder":
        """No-op fit for stateless encoders; returns self."""
        # 无状态编码器忽略输入数据直接返回自身以兼容统一接口
        del data
        return self

    def get_metadata(self) -> Mapping[str, Any]:
        """Return minimal metadata capturing encoder type."""
        # 返回仅包含编码器类型名称的精简元数据
        return {"type": self.__class__.__name__}

    @abstractmethod
    def encode(self, value: Any) -> EncodedValue:
        # 子类实现实际的编码逻辑不依赖任何拟合状态
        raise NotImplementedError

    @abstractmethod
    def decode(self, encoded: EncodedValue) -> Any:
        # 子类实现解码逻辑，如不支持解码通常可显式抛出异常
        raise NotImplementedError


class FittedEncoder(BaseEncoder):
    """
    Base class for encoders that must be fitted before use.

    Subclasses should populate necessary statistics during fit(), then set
    is_fitted to True. encode/decode implementations should call _ensure_fitted()
    to guard against use prior to fitting.
    """

    def __init__(self) -> None:
        # 初始化需拟合编码器并标记当前未完成拟合状态
        self.is_fitted: bool = False

    def _ensure_fitted(self) -> None:
        # 在 encode 或 decode 前检查是否已完成拟合，未拟合则抛出运行时错误
        if not self.is_fitted:
            raise RuntimeError("encoder must be fitted before encode/decode")

    def _mark_fitted(self) -> None:
        # 在 fit 完成必要统计学习后调用，以标记编码器已就绪
        self.is_fitted = True

    @abstractmethod
    def fit(self, data: Iterable[Any]) -> "FittedEncoder":
        # 子类在此实现基于数据的拟合过程并在结束时调用 _mark_fitted
        raise NotImplementedError

    @abstractmethod
    def encode(self, value: Any) -> EncodedValue:
        # 依赖已拟合状态将原始值编码为 EncodedValue 表示
        raise NotImplementedError

    @abstractmethod
    def decode(self, encoded: EncodedValue) -> Any:
        # 依赖已拟合状态将 EncodedValue 解码回原始或等价表示
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> Mapping[str, Any]:
        # 返回包含拟合状态或相关统计信息的编码配置元数据
        raise NotImplementedError
