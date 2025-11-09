"""
Unit tests covering behaviour of the GRR mechanism.

Covers:
    * calibration probabilities
    * randomisation for scalars, sequences, and numpy arrays
    * serialization integrity and domain validation errors
"""
# 说明：测试广义随机响应（GRR）机制在 LDP 场景下的行为。
# 覆盖：
# - 校准后概率 p/q 正确性
# - 标量/序列/NumPy 数组的逐元素随机化
# - 构造与输入校验；以及序列化往返一致性

import numpy as np
import pytest
from dplib.ldp.mechanisms.grr import GRRMechanism
from dplib.core.privacy.base_mechanism import MechanismError, ValidationError

@pytest.fixture
def grr_mechanism() -> GRRMechanism:
    """Provide a simple GRR mechanism with a 3-value domain."""
    # 夹具：提供一个包含 3 个取值的离散域，供后续复用
    return GRRMechanism(epsilon=1.0, domain=["A", "B", "C"])


@pytest.fixture
def calibrated_grr(grr_mechanism: GRRMechanism) -> GRRMechanism:
    """Return a calibrated GRR mechanism for reuse across tests."""
    # 对机制进行一次性校准，避免在各测试中重复调用
    return grr_mechanism.calibrate()


def test_calibrate_sets_probabilities(calibrated_grr: GRRMechanism) -> None:
    """Ensure calibration computes analytical truthful/non-truthful probabilities."""
    # 理论公式：p = e^ε / (e^ε + k - 1)，q = 1 / (e^ε + k - 1)，k 为域大小
    mech = calibrated_grr
    exp_eps = np.exp(mech.epsilon)
    denom = exp_eps + len(mech.domain) - 1
    assert mech.p == pytest.approx(exp_eps / denom)
    assert mech.q == pytest.approx(1.0 / denom)
    assert mech.probabilities["truthful"] == mech.p
    assert mech.probabilities["other"] == mech.q


def test_randomise_scalar_returns_domain_value(calibrated_grr: GRRMechanism) -> None:
    """Scalar randomisation should always stay inside the domain."""
    # 标量输入应始终随机化为域内值；固定种子降低测试偶然性
    mech = calibrated_grr
    mech.reseed(0)
    value = mech.randomise("A")
    assert value in mech.domain


def test_randomise_sequence_preserves_length(calibrated_grr: GRRMechanism) -> None:
    """Sequence inputs are processed element-wise and keep their length."""
    # 序列输入逐元素随机化，保持输出为 list 且长度不变
    mech = calibrated_grr
    mech.reseed(42)
    seq = ["A", "B", "C", "A"]
    result = mech.randomise(seq)
    assert isinstance(result, list)
    assert len(result) == len(seq)
    assert set(result).issubset(set(mech.domain))  # 所有输出仍属域内


def test_randomise_numpy_array(calibrated_grr: GRRMechanism) -> None:
    """Numpy arrays are noise-added while preserving shape and dtype=object."""
    # NumPy 数组输入应保持形状和数据类型不变；元素值仍限定在域内
    mech = calibrated_grr
    mech.reseed(7)
    arr = np.array([["A", "B"], ["C", "A"]], dtype=object)
    result = mech.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape
    assert result.dtype == object
    assert set(result.ravel()).issubset(set(mech.domain))


def test_randomise_unknown_value_raises(calibrated_grr: GRRMechanism) -> None:
    """Values outside the domain should fail fast."""
    # 域外值应立即报错，保证数据验证
    with pytest.raises(MechanismError):
        calibrated_grr.randomise("Z")


def test_invalid_domain_rejected() -> None:
    """Constructor must reject duplicate-only domains."""
    # 仅含重复值的域非法（类别数不足），应抛 ValidationError
    with pytest.raises(ValidationError):
        GRRMechanism(epsilon=1.0, domain=["only", "only"])


def test_probability_matches_formula(calibrated_grr: GRRMechanism) -> None:
    """Empirical truthful probability should match theory within tolerance."""
    # 经验概率检验：多次随机化输入“A”，其返回“A”的频率应接近理论 p
    mech = calibrated_grr
    mech.reseed(123)
    samples = [mech.randomise("A") for _ in range(5000)]
    prob = samples.count("A") / len(samples)
    assert prob == pytest.approx(mech.p, abs=0.02)  # 允许 2% 误差带


def test_serialization_roundtrip(calibrated_grr: GRRMechanism) -> None:
    """Serialisation should preserve parameters, metadata, and calibration flag."""
    # 序列化→反序列化往返一致性：域、p/q、_meta 以及校准标志必须一致
    mech = calibrated_grr
    mech._meta["origin"] = "unit-test"
    data = mech.serialize()
    restored = GRRMechanism.deserialize(data)
    assert restored.domain == mech.domain
    assert restored.p == mech.p
    assert restored.q == mech.q
    assert restored._meta == mech._meta
    assert restored._calibrated == mech._calibrated
