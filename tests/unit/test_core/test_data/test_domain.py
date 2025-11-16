"""
Unit tests for domain abstractions.
"""
# 说明：离散/连续/分桶 Domain 抽象类型的编码、解码与约束行为单元测试。
# 覆盖：
# - DiscreteDomain：符号到索引的 encode/decode 往返一致性与非法值异常
# - ContinuousDomain：数值范围 contains(...) 与 clamp(...) 边界截断行为
# - BucketizedDomain：按分桶边界将实数映射到桶索引，并从索引恢复区间

import pytest

from dplib.core.data import (
    BucketizedDomain,
    ContinuousDomain,
    DiscreteDomain,
    DomainError,
)


def test_discrete_domain_encode_decode_roundtrip() -> None:
    # 使用离散符号集合构造离散域，底层通常维护值→索引的映射
    domain = DiscreteDomain(["A", "B", "C"])
    # encode 应将 "B" 映射到对应的整数索引 1
    encoded = domain.encode("B")
    assert encoded == 1
    # decode 应能从索引恢复原始符号（往返一致性）
    assert domain.decode(encoded) == "B"


def test_discrete_domain_invalid_value_raises() -> None:
    domain = DiscreteDomain(["yes", "no"])
    # 对于不在域中的取值，encode 应抛出 DomainError
    with pytest.raises(DomainError):
        domain.encode("maybe")


def test_continuous_domain_contains_and_clamp() -> None:
    # 定义连续数值域 [minimum, maximum] 闭区间
    domain = ContinuousDomain(minimum=0.0, maximum=10.0)
    # contains 检查给定值是否落在域内
    assert domain.contains(5.0)
    assert not domain.contains(11.0)
    # clamp 将超出范围的值裁剪到最近的边界
    assert domain.clamp(-5.0) == 0.0
    assert domain.clamp(12.0) == 10.0


def test_bucketized_domain_encode_decode() -> None:
    # BucketizedDomain：使用一组有序边界定义分桶
    # 这里边界为 [0, 1, 2, 3]，通常表示区间 [0,1)、[1,2)、[2,3]
    domain = BucketizedDomain([0.0, 1.0, 2.0, 3.0])
    # encode 将实数映射为桶索引：0.5 落在 [0,1) → 桶 0
    assert domain.encode(0.5) == 0
    # 2.4 落在 [2,3] 中，对应桶索引 2
    assert domain.encode(2.4) == 2
    # decode 从桶索引恢复对应的区间边界
    assert domain.decode(1) == (1.0, 2.0)
