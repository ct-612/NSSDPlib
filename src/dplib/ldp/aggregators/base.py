"""Base abstractions for server-side LDP aggregators."""
# 说明：聚合器在服务端消费 LDPReport 列表并输出 Estimate，不负责解码原始值，仅基于encoded 值与机制参数做统计估计。
# 职责：
# - 定义服务端 LDP 聚合器的抽象接口与最小行为契约
# - 约定 aggregate/get_metadata/reset 方法签名，便于不同聚合算法统一接入
# - 提供 StatelessAggregator 基类以简化无状态聚合器的实现

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from dplib.ldp.types import Estimate, LDPReport


class BaseAggregator(ABC):
    """
    Abstract interface for server-side LDP aggregation.

    Aggregators take a batch of LDPReport objects and produce an Estimate. They
    may maintain internal state (e.g., running counters) and can be reset when
    reused across rounds.
    """

    @abstractmethod
    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 子类实现对一批 LDPReport 的聚合逻辑并返回对应的统计估计结果
        """Aggregate a batch of LDP reports into an Estimate."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> Mapping[str, Any]:
        # 子类返回描述聚合方案配置与行为的 JSON 友好元数据快照
        """Return JSON-serialisable metadata describing the aggregation scheme."""
        raise NotImplementedError

    def reset(self) -> None:
        # 默认实现不维护内部状态，子类如有累积计数器或缓存可重写以执行清理动作
        """Reset internal state if applicable (default no-op)."""
        return None


class StatelessAggregator(BaseAggregator):
    """Aggregator with no persistent state; reset is a no-op."""

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:  # pragma: no cover - abstract passthrough
        # 无状态聚合器的子类仍需实现具体聚合算法，仅不在实例上保留跨轮次状态
        raise NotImplementedError

    def get_metadata(self) -> Mapping[str, Any]:
        # 使用类名作为类型标识返回最小化的聚合器元数据
        return {"type": self.__class__.__name__}

    def reset(self) -> None:
        # 对无状态聚合器而言 reset 显式为空操作，便于在公共接口中安全调用
        return None
