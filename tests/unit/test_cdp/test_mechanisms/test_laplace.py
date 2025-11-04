# tests\unit\test_cdp\test_mechanisms\test_laplace.py
import pytest
import numpy as np
from dplib.cdp.mechanisms.laplace import LaplaceMechanism, MechanismError

# -----------------------------
# Fixture 示例
# -----------------------------
@pytest.fixture
def laplace_mechanism():
    return LaplaceMechanism(epsilon=1.0, sensitivity=1.0)

@pytest.fixture(params=[0.1, 0.5, 1.0])
def epsilon(request):
    return request.param

@pytest.fixture(params=[0.1, 1.0, 5.0])
def sensitivity(request):
    return request.param

@pytest.fixture
def random_array():
    import numpy as np
    return lambda n: np.random.rand(n)

# -----------------------------
# 基本功能测试
# -----------------------------
def test_calibrate_and_randomise(laplace_mechanism):
    mech = laplace_mechanism
    mech.calibrate(2.0)
    val = 10.0
    noisy_val = mech.randomise(val)
    assert isinstance(noisy_val, float)
    assert noisy_val != val or noisy_val == val  # Laplace 随机性

def test_invalid_calibrate():
    mech = LaplaceMechanism(epsilon=1.0, sensitivity=1.0)
    with pytest.raises(MechanismError):
        mech.calibrate(-1)

def test_invalid_randomise_type(laplace_mechanism):
    with pytest.raises(MechanismError):
        laplace_mechanism.randomise("not_a_number")

# -----------------------------
# 统计特性测试
# -----------------------------
def test_laplace_statistics(laplace_mechanism):
    mech = laplace_mechanism
    mech.calibrate(1.0)
    samples = [mech.randomise(0.0) for _ in range(1000)]
    mean = np.mean(samples)
    var = np.var(samples)
    assert abs(mean) < 0.5
    assert var > 0

# -----------------------------
# 序列化/反序列化
# -----------------------------
def test_serialize_deserialize():
    mech = LaplaceMechanism(epsilon=0.5, sensitivity=2.0)
    data = mech.serialize()
    new_mech = LaplaceMechanism.deserialize(data)
    assert new_mech.epsilon == mech.epsilon
    assert new_mech.sensitivity == mech.sensitivity
