"""
Unit tests for the Optimal Unary Encoding (OUE) mechanism.

Covers:
    * calibration probabilities derived from epsilon
    * randomisation for scalars, python sequences, and numpy arrays
    * empirical Bernoulli rates and serialization behaviour
"""
# 说明：对 OUE 机制的单元测试。
# 覆盖：
# - 由 ε 推导的伯努利参数 p/q 的校准正确性
# - 标量、Python 序列与 NumPy 数组的随机化形态与取值约束
# - 经验概率与理论值的一致性，以及序列化往返一致性

import numpy as np
import pytest
from dplib.ldp.mechanisms.oue import OUEMechanism
from dplib.core.privacy.base_mechanism import MechanismError, ValidationError


@pytest.fixture
def oue_mechanism() -> OUEMechanism:
    """Provide a default 4-category OUE instance for reuse."""
    # 夹具：提供一个包含 4 个取值的 OUE 实例，便于复用
    return OUEMechanism(epsilon=1.2, domain=["A", "B", "C", "D"])


@pytest.fixture
def calibrated_oue(oue_mechanism: OUEMechanism) -> OUEMechanism:
    """Return a calibrated OUE mechanism."""
    # 预校准实例，减少各测试的重复代码
    return oue_mechanism.calibrate()


def test_calibration_sets_expected_probabilities(calibrated_oue: OUEMechanism) -> None:
    """Analytical Bernoulli parameters should match OUE formula."""
    # 校验公式：p=0.5，q=1/(e^ε+1)
    mech = calibrated_oue
    exp_eps = np.exp(mech.epsilon)
    assert mech.p == pytest.approx(0.5)
    assert mech.q == pytest.approx(1.0 / (exp_eps + 1.0))
    assert mech.probabilities["true_bit_one"] == mech.p
    assert mech.probabilities["other_bit_one"] == mech.q


def test_randomise_scalar_outputs_binary_vector(calibrated_oue: OUEMechanism) -> None:
    """Scalar inputs should map to unary vectors with values in {0, 1}."""
    # 标量输入应输出长度为 |domain| 的 0/1 向量，dtype=int8
    mech = calibrated_oue
    mech.reseed(123)
    vec = mech.randomise("A")
    assert vec.shape == (len(mech.domain),)
    assert vec.dtype == np.int8
    assert set(np.unique(vec)).issubset({0, 1})


def test_randomise_sequence_returns_matrix(calibrated_oue: OUEMechanism) -> None:
    """Sequence inputs return stacked unary vectors."""
    # 序列输入应堆叠成矩阵，形状为 (len(seq), |domain|)，取值 ∈ {0,1}
    mech = calibrated_oue
    mech.reseed(7)
    seq = ["A", "B", "C"]
    result = mech.randomise(seq)
    assert isinstance(result, np.ndarray)
    assert result.shape == (len(seq), len(mech.domain))
    assert set(np.unique(result)).issubset({0, 1})


def test_randomise_numpy_array_expands_axis(calibrated_oue: OUEMechanism) -> None:
    """NumPy arrays gain a trailing unary axis."""
    # NumPy 数组应在末维扩展出一元编码轴，形状为 arr.shape + (|domain|,)
    mech = calibrated_oue
    mech.reseed(99)
    arr = np.array([["A", "B"], ["C", "A"]], dtype=object)
    result = mech.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape + (len(mech.domain),)
    assert result.dtype == np.int8
    assert set(np.unique(result)).issubset({0, 1})


def test_randomise_unknown_value_raises(calibrated_oue: OUEMechanism) -> None:
    """Values outside the configured domain must raise."""
    # 域外值应立即报错，抛出 MechanismError
    with pytest.raises(MechanismError):
        calibrated_oue.randomise("Z")


def test_invalid_domain_rejected() -> None:
    """Domain validation rejects duplicates and short domains."""
    # 域长度 < 2 和含重复值应被拒绝，抛 ValidationError
    with pytest.raises(ValidationError):
        OUEMechanism(epsilon=1.0, domain=["only"])
    with pytest.raises(ValidationError):
        OUEMechanism(epsilon=1.0, domain=["dup", "dup"])


def test_empirical_probabilities_match_formula(calibrated_oue: OUEMechanism) -> None:
    """Monte Carlo estimates of p/q should align with analytical values."""
    # 蒙特卡洛检验：多次编码 "A"，其真位与某一非真位的 1 比率应分别接近 p 和 q
    mech = calibrated_oue
    mech.reseed(2024)
    idx = mech.domain.index("A")
    other_idx = (idx + 1) % len(mech.domain)
    samples = np.stack([mech.randomise("A") for _ in range(6000)], axis=0)
    truth_rate = samples[:, idx].mean()
    other_rate = samples[:, other_idx].mean()
    assert truth_rate == pytest.approx(mech.p, abs=0.02)
    assert other_rate == pytest.approx(mech.q, abs=0.02)


def test_serialization_roundtrip(calibrated_oue: OUEMechanism) -> None:
    """Serialisation should persist calibration metadata."""
    # 序列化往返一致性：domain、p/q、_meta 以及校准标志应保持一致
    mech = calibrated_oue
    mech._meta["origin"] = "unit-test"
    data = mech.serialize()
    restored = OUEMechanism.deserialize(data)
    assert restored.domain == mech.domain
    assert restored.p == mech.p
    assert restored.q == mech.q
    assert restored._meta == mech._meta
    assert restored._calibrated == mech._calibrated
