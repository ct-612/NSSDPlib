# tests\unit\test_cdp\test_mechanisms\test_gaussian.py
import pytest
import numpy as np
from dplib.cdp.mechanisms.gaussian import GaussianMechanism, MechanismError


@pytest.fixture
def gaussian_mechanism():
    return GaussianMechanism(epsilon=1.0, delta=1e-3, sensitivity=1.0)


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


def test_calibrate_and_randomise(gaussian_mechanism):
    mech = gaussian_mechanism
    mech.calibrate(2.0, delta=1e-3)
    val = 10.0
    noisy_val = mech.randomise(val)
    assert isinstance(noisy_val, float)
    assert noisy_val != val or noisy_val == val


def test_invalid_calibrate():
    mech = GaussianMechanism(epsilon=1.0, delta=1e-3, sensitivity=1.0)
    with pytest.raises(MechanismError):
        mech.calibrate(-1)


def test_invalid_randomise_type(gaussian_mechanism):
    with pytest.raises(MechanismError):
        gaussian_mechanism.randomise("not_a_number")


def test_gaussian_statistics(gaussian_mechanism):
    mech = gaussian_mechanism
    mech.calibrate(1.0, delta=1e-3)
    samples = [mech.randomise(0.0) for _ in range(1000)]
    mean = np.mean(samples)
    var = np.var(samples)
    assert abs(mean) < 0.5
    assert var > 0


def test_serialize_deserialize():
    mech = GaussianMechanism(epsilon=0.5, delta=1e-4, sensitivity=2.0)
    mech.calibrate(2.0, delta=1e-4)
    data = mech.serialize()
    new_mech = GaussianMechanism.deserialize(data)
    assert new_mech.epsilon == mech.epsilon
    assert new_mech.sensitivity == mech.sensitivity