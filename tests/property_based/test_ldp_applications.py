"""
Property-based tests for the LDP Applications.
"""
# 说明：本地化差分隐私（LDP）上层应用（HeavyHitters, FrequencyEstimation, Marginals, SequenceAnalysis）的属性测试。
# 覆盖：
# - HeavyHitters Top-K 提取逻辑的降序排列与子集约束验证
# - 端到端应用结构的初始化及其生成的客户端报告元数据一致性
# - 边缘分布应用的多维度报告生成逻辑
# - 序列分析应用在指定最大长度下的报告限制
# - 错误参数与不支持度量类型的拦截校验

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.ldp.applications.heavy_hitters import extract_top_k, HeavyHittersApplication, HeavyHittersClientConfig, HeavyHittersServerConfig
from dplib.ldp.applications.frequency_estimation import FrequencyEstimationApplication, FrequencyEstimationClientConfig
from dplib.ldp.applications.marginals import MarginalsApplication, MarginalsClientConfig, MarginalSpec
from dplib.ldp.applications.sequence_analysis import SequenceAnalysisApplication, SequenceAnalysisClientConfig
from dplib.ldp.types import Estimate
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- Heavy Hitters Logic
@given(
    st.lists(st.tuples(st.integers(), st.floats(min_value=0.0, max_value=1.0)),
             min_size=1,
             max_size=20), st.integers(min_value=1, max_value=10))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_extract_top_k_ordering(pairs, top_k):
    # 验证 Top-K 提取器能输出按频率严格降序排列的结果，且元素均来自原始类别集
    categories = [p[0] for p in pairs]
    frequencies = [p[1] for p in pairs]

    metadata = {"categories": categories}
    est = Estimate(metric="frequency",
                   point=frequencies,
                   variance=None,
                   confidence_interval=None,
                   metadata=metadata)

    res = extract_top_k(est, top_k)

    # 检查返回数量限制
    assert len(res) <= top_k
    assert len(res) <= len(pairs)

    # 检查降序排列特性
    freqs = [r[1] for r in res]
    assert freqs == sorted(freqs, reverse=True)

    # 验证元素成员身份合法性
    res_cats = {r[0] for r in res}
    assert res_cats.issubset(set(categories))


@given(
    st.lists(st.text(min_size=1), min_size=2, max_size=5,
             unique=True).map(tuple), st.floats(min_value=0.1, max_value=5.0))
def test_heavy_hitters_e2e_structure(categories, epsilon):
    # 验证频繁项应用能正确构建客户端函数并生成携带正确应用标识的 LDP 报告
    client_config = HeavyHittersClientConfig(epsilon=epsilon,
                                             categories=categories,
                                             mechanism="grr")
    app = HeavyHittersApplication(client_config)

    client_fn = app.build_client()

    # 模拟生成的客户端隐私报告
    val = categories[0]
    report = client_fn(val, user_id="u001")

    assert report.metadata["application"] == "heavy_hitters"
    assert report.metadata["mechanism"] == "grr"
    # 验证离散域大小配置是否正确透传
    assert report.metadata["domain_size"] == len(categories)


@given(st.integers(min_value=1, max_value=10))
def test_extract_top_k_invalid_inputs(top_k):
    # 验证 Top-K 逻辑对非频率度量类型的估计结果执行了正确的参数校验拦截
    est = Estimate(metric="mean",
                   point=[0.5],
                   variance=None,
                   confidence_interval=None,
                   metadata={})
    with pytest.raises(ParamValidationError):
        extract_top_k(est, top_k)


# ---------------------------------------------------------------- Frequency Estimation Application
@given(
    st.lists(st.text(min_size=1), min_size=2, max_size=5,
             unique=True).map(tuple), st.floats(min_value=0.1, max_value=5.0))
def test_freq_estimation_e2e(categories, epsilon):
    # 验证频率估计端到端组件能正确初始化并通过 GRR 机制生成具有特定应用标识的报告
    client_config = FrequencyEstimationClientConfig(epsilon=epsilon,
                                                    categories=categories,
                                                    mechanism="grr")
    app = FrequencyEstimationApplication(client_config)
    client_fn = app.build_client()

    val = categories[0]
    report = client_fn(val, user_id="u1")
    assert report.metadata["application"] == "frequency_estimation"


# ---------------------------------------------------------------- Marginals Application
@given(
    st.lists(st.text(min_size=1), min_size=2, max_size=3,
             unique=True).map(tuple), st.floats(min_value=0.1, max_value=5.0))
def test_marginals_e2e_config(cols, epsilon):
    # 验证边缘分布应用能够为输入的字典行数据按维度生成对应的 LDP 分量报告
    # 为每列随机生成分类配置
    specs = [MarginalSpec(name=c, categories=["a", "b"]) for c in cols]

    client_config = MarginalsClientConfig(epsilon_per_dimension=epsilon,
                                          marginals=specs)
    app = MarginalsApplication(client_config)

    client_fn = app.build_client()
    # 客户端输入通常是多特征构成的行字典
    row = {c: "a" for c in cols}
    reports = client_fn(row, user_id="u2")

    assert isinstance(reports, list)
    assert len(reports) == len(cols)
    assert reports[0].metadata["application"] == "marginals"


# ---------------------------------------------------------------- Sequence Analysis Application
@given(st.floats(min_value=0.1, max_value=5.0),
       st.integers(min_value=2, max_value=5))
def test_sequence_analysis_e2e_structure(epsilon, max_len):
    # 验证序列分析组件针对变长列表输入生成的报告数量不会超过预设的最大长度限制
    client_config = SequenceAnalysisClientConfig(epsilon_per_event=epsilon,
                                                 max_length=max_len,
                                                 categories=["A", "B"])
    app = SequenceAnalysisApplication(client_config)
    client_fn = app.build_client()

    seq = ["A", "B"]
    reports = client_fn(seq, user_id="u3")
    assert isinstance(reports, list)
    assert len(reports) <= max_len
    assert reports[0].metadata["application"] == "sequence_analysis"
