"""
Abstract base class for LDP applications.

Responsibilities:
    * define client/aggregator builder contracts for LDP pipelines
    * provide name/config helpers for application introspection
"""
# 说明：LDP applications 的抽象基类定义，约束端到端 pipeline 构建入口。
# 职责：
# - 约定客户端侧 raw input -> LDPReport 的构建接口
# - 约定服务端侧 LDPReport -> Estimate 的聚合入口
# - 提供应用名称与配置的默认暴露方式

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Mapping, Sequence

from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.types import LDPReport


class BaseLDPApplication(ABC):
    """
    Abstract base class for LDP applications.

    build_client returns a client-side callable that perturbs raw input into LDPReport.
    build_aggregator returns a server-side aggregator that converts LDPReport batches into Estimate.
    get_config can be overridden to expose epsilon, encoder, and mechanism configuration.

    TODO:
        * decide whether to expose encoder fit helpers at the application API
        * decide whether to allow injecting pre-fitted encoders and define validation rules
    """

    @abstractmethod
    def build_client(self) -> Callable[[Any, str], LDPReport | Sequence[LDPReport]]:
        # 构建客户端侧的上报函数用于将原始输入扰动为 LDPReport
        raise NotImplementedError

    @abstractmethod
    def build_aggregator(self) -> BaseAggregator:
        # 构建服务端侧聚合器以消费 LDPReport 序列并输出统计估计
        raise NotImplementedError

    def get_name(self) -> str:
        # 返回应用名称便于日志记录与调试
        return self.__class__.__name__

    def get_config(self) -> Mapping[str, Any]:
        # 返回应用配置的可序列化字典以便上层追踪
        return {}
