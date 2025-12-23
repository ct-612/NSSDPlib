"""
Per-user LDP privacy accountant with optional CDP bridging.

Responsibilities
  - Track per-user epsilon usage for local DP workflows.
  - Enforce optional per-user and global epsilon limits.
  - Provide summary snapshots for monitoring and reporting.
  - Forward usage to a CDP accountant via a configurable mapping strategy.

Usage Context
  - Use for per-user LDP accounting with optional CDP bridging.
  - Intended for server-side tracking of LocalPrivacyUsage records.

Limitations
  - Bridging relies on the configured mapper and metadata.
  - Composition is linear and does not apply advanced bounds.
"""
# 说明：面向 per-user epsilon 视角的 LDP 隐私会计器，支持可配置的 CDP 桥接。
# 职责：
# - 跟踪每个用户的 epsilon 使用量并执行预算上限检查
# - 提供总量与 per-user 统计摘要便于监控与报告
# - 通过可配置映射将本地 usage 透传到 CDP 会计器以便混合审计

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from .compose import ANONYMOUS_USER_KEY, summarize_budget

from dplib.ldp.types import LDPBudgetSummary, LocalPrivacyUsage

from dplib.core.utils.param_validation import ParamValidationError
from .ldp_cdp_mapping import LDPToCDPMapper, default_ldp_to_cdp_mapper, normalize_cdp_event

try:
    from dplib.core.privacy.privacy_accountant import BudgetExceededError
except Exception:
    class BudgetExceededError(RuntimeError):
        # 作为兜底异常类型用于预算超限场景
        pass

if TYPE_CHECKING:
    from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
else:
    CDPPrivacyAccountant = Any

class LDPPrivacyAccountant:
    """
    Per-user LDP privacy accountant.

    - Configuration
      - per_user_epsilon_limit: Optional per-user epsilon budget cap.
      - global_epsilon_limit: Optional global epsilon budget cap.
      - cdp_accountant: Optional CDP accountant for bridging events.
      - ldp_to_cdp_mapper: Optional mapper from local usage to CDP events.

    - Behavior
      - Tracks per-user and total epsilon usage with budget checks.
      - Forwards mapped events to a CDP accountant when configured.

    - Usage Notes
      - Mapping behavior depends on metadata and the configured mapper.
    """

    def __init__(
        self,
        per_user_epsilon_limit: Optional[float] = None,
        global_epsilon_limit: Optional[float] = None,
        cdp_accountant: Optional[CDPPrivacyAccountant] = None,
        ldp_to_cdp_mapper: Optional[LDPToCDPMapper] = None,
    ) -> None:
        # 配置 per-user 与全局 epsilon 上限并注入 LDP 到 CDP 的映射策略
        if per_user_epsilon_limit is not None and per_user_epsilon_limit < 0:
            raise ParamValidationError("per_user_epsilon_limit must be non-negative")
        if global_epsilon_limit is not None and global_epsilon_limit < 0:
            raise ParamValidationError("global_epsilon_limit must be non-negative")
        self.per_user_epsilon_limit = per_user_epsilon_limit
        self.global_epsilon_limit = global_epsilon_limit
        self._cdp_accountant = cdp_accountant
        self._ldp_to_cdp_mapper = ldp_to_cdp_mapper or default_ldp_to_cdp_mapper
        self._usages: List[LocalPrivacyUsage] = []
        self._per_user_spent: Dict[str, float] = {}
        self._total_spent = 0.0

    def _forward_usage_to_cdp(self, usage: LocalPrivacyUsage) -> None:
        # 使用映射策略生成 CDP 事件并透传到会计器
        if self._cdp_accountant is None:
            return
        mapped = self._ldp_to_cdp_mapper(usage)
        event = normalize_cdp_event(usage, mapped)
        if event.epsilon < 0 or event.delta < 0:
            raise ParamValidationError("epsilon and delta must be non-negative")
        if hasattr(self._cdp_accountant, "add_event"):
            self._cdp_accountant.add_event(
                epsilon=event.epsilon,
                delta=event.delta,
                description=event.description,
                metadata=dict(event.metadata),
            )
            return
        if hasattr(self._cdp_accountant, "add_composed_event"):
            payload = {
                "epsilon": event.epsilon,
                "delta": event.delta,
                "description": event.description,
                "metadata": dict(event.metadata),
            }
            self._cdp_accountant.add_composed_event(
                [payload],
                description=event.description,
                metadata=dict(event.metadata),
            )
            return
        # TODO: 适配 MomentAccountant 的 RDP 累积接口以支持非 add_event 的记账流程
        # TODO: 适配 BudgetTracker 等按 scope 记账入口并明确 scope 选择策略

    def add_usage(self, usage: LocalPrivacyUsage) -> None:
        # 记录单条 usage 并在超预算时抛出异常
        epsilon = float(usage.epsilon)
        if epsilon < 0:
            raise ParamValidationError("epsilon must be non-negative")

        user_key = ANONYMOUS_USER_KEY if usage.user_id is None else str(usage.user_id)
        next_user_spent = self._per_user_spent.get(user_key, 0.0) + epsilon
        next_total_spent = self._total_spent + epsilon

        # 预算检查在更新内部状态前执行以避免部分写入
        if self.per_user_epsilon_limit is not None and next_user_spent > self.per_user_epsilon_limit:
            raise BudgetExceededError(f"user {user_key} exceeds per-user epsilon limit")
        if self.global_epsilon_limit is not None and next_total_spent > self.global_epsilon_limit:
            raise BudgetExceededError("global epsilon limit exceeded")

        self._usages.append(usage)
        self._per_user_spent[user_key] = next_user_spent
        self._total_spent = next_total_spent

        # 将本地 usage 信息同步到 CDP 会计器用于混合审计
        self._forward_usage_to_cdp(usage)

    def add_usages(self, usages: Sequence[LocalPrivacyUsage]) -> None:
        # 批量添加 usage 并复用单条记录的校验与超限逻辑
        for usage in usages:
            self.add_usage(usage)

    def get_user_spent(self, user_id: str) -> float:
        # 查询指定 user_id 的累计 epsilon 支出
        return float(self._per_user_spent.get(str(user_id), 0.0))

    def get_total_spent(self) -> float:
        # 返回当前累计的总 epsilon 支出
        return float(self._total_spent)

    def summarize(self) -> LDPBudgetSummary:
        # 基于已记录的 usages 输出汇总视图
        return summarize_budget(self._usages)

    def reset(self) -> None:
        # 清空内部 usage 与累计状态但保留注入的 cdp_accountant
        self._usages.clear()
        self._per_user_spent.clear()
        self._total_spent = 0.0
