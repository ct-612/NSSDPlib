"""
Property-based tests for the LDP to CDP Privacy Mapping.
"""
# 说明：本地化差分隐私（LDP）到中心化差分隐私（CDP）隐私参数映射逻辑的属性测试。
# 覆盖：
# - 默认映射器对 epsilon 参数的提取与元数据的完整传递验证
# - 映射过程中对 delta 缺省值的安全填充逻辑
# - 结构化隐私事件标准化流程及其对 LDP 上下文（用户 ID, 轮次, 源）的自动注入

import pytest
from hypothesis import given, strategies as st
from dplib.ldp.composition.ldp_cdp_mapping import default_ldp_to_cdp_mapper, normalize_cdp_event, LDPToCDPEvent
from dplib.ldp.types import LocalPrivacyUsage


# ---------------------------------------------------------------- LDP-to-CDP Mapping
@given(st.floats(min_value=0.1, max_value=10.0),
       st.dictionaries(keys=st.text(), values=st.text()))
def test_default_mapper_params(epsilon, meta):
    # 验证基础映射函数能将本地隐私使用量对象转换为对应的 CDP 视图隐私事件
    usage = LocalPrivacyUsage(epsilon=epsilon, user_id="u1", metadata=meta)
    event = default_ldp_to_cdp_mapper(usage)

    assert event.epsilon == epsilon
    assert event.metadata == meta
    # 如果元数据中未显式包含 delta，则默认应映射为纯差分隐私（delta=0.0）
    if "delta" not in meta:
        assert event.delta == 0.0


@given(st.floats(min_value=0.1, max_value=10.0))
def test_normalize_cdp_event_context(epsilon):
    # 验证标准化函数能自动向隐私事件注入必要的本地隐私上下文信息以供记账审计
    usage = LocalPrivacyUsage(epsilon=epsilon, user_id="user_123", round_id=5)
    raw_event = LDPToCDPEvent(epsilon=epsilon, delta=0.0, description="desc")

    norm_event = normalize_cdp_event(usage, raw_event)

    # 校验注入的 ldp_context 字段结构
    context = norm_event.metadata["ldp_context"]
    assert context["user_id"] == "user_123"
    assert context["round_id"] == 5
    assert context["source"] == "ldp"
