"""
Global sensitivity helpers for common CDP queries (wrapping core data layer).
"""
# 说明：封装常见中心差分隐私查询的全局敏感度计算便捷接口。
# 职责：
# - 基于核心数据层的全局敏感度函数提供 count/sum/mean 的轻量包装
# - 暴露统一的函数签名与类型别名以便上层 CDP 机制或 API 直接调用
# - 提供 PRESETS 映射方便在配置或元数据中引用底层敏感度实现名称

from __future__ import annotations

from typing import Dict

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    count_global_sensitivity,
    mean_global_sensitivity,
    sum_global_sensitivity,
)


def count(max_contribution: int = 1) -> float:
    # 返回计数查询在给定每用户最大贡献次数约束下的全局 L1 敏感度
    return count_global_sensitivity(max_contribution=max_contribution)


def sum(domain: ContinuousDomain, *, max_contribution: int = 1) -> float:
    # 返回在指定数值域与每用户最大贡献次数约束下求和查询的全局敏感度
    return sum_global_sensitivity(domain, max_contribution=max_contribution)


def mean(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> float:
    # 返回在给定样本量与贡献上界下均值查询的全局敏感度，用于 CDP 噪声校准
    return mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)


# 为常见查询类型提供名称到底层敏感度实现函数名的映射，方便配置驱动调用
PRESETS: Dict[str, str] = {
    "count": "count_global_sensitivity",
    "sum": "sum_global_sensitivity",
    "mean": "mean_global_sensitivity",
}
