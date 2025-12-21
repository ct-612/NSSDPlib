"""
Unit tests for the CDP QueryEngine accounting integration.
"""
# 说明：QueryEngine 与 PrivacyAccountant 联动的集成测试
# 覆盖：
# - 查询执行后记录隐私事件与预算累计
# - 预算不足时抛出 BudgetExceededError
from __future__ import annotations

import pytest

from dplib.cdp.analytics.queries import QueryEngine
from dplib.core.privacy.privacy_accountant import BudgetExceededError, PrivacyAccountant


def test_query_engine_records_privacy_spend() -> None:
    # 验证查询执行会写入隐私事件并累计预算
    accountant = PrivacyAccountant(total_epsilon=2.0)
    engine = QueryEngine(accountant=accountant)

    # 执行多种查询以产生隐私支出
    engine.execute("count", data=[1, 2, 3, 4], epsilon=0.5)
    engine.execute("sum", data=[1.0, 2.0, 3.0], epsilon=0.4, bounds=(0.0, 4.0))

    # 校验事件数量与预算累计信息
    assert len(accountant.events) == 2
    assert accountant.spent.epsilon == pytest.approx(0.9)
    assert accountant.events[0].description == "count query"
    assert accountant.events[0].metadata["query"] == "count"
    assert accountant.events[1].metadata["query"] == "sum"


def test_query_engine_raises_on_budget_exceeded() -> None:
    # 验证预算不足时查询会触发预算超限异常
    accountant = PrivacyAccountant(total_epsilon=0.3)
    engine = QueryEngine(accountant=accountant)

    # 触发单次超出预算的查询请求
    with pytest.raises(BudgetExceededError):
        engine.execute("count", data=[1, 2, 3], epsilon=0.5)
