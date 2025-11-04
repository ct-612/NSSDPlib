# tests/conftest.py
import pytest
import numpy as np
import random
import os

# -----------------------------
# 全局随机数种子管理
# -----------------------------
@pytest.fixture(scope="session", autouse=True)
def set_global_seed():
    """
    为所有测试设置全局随机数种子，保证可复现性。
    """
    seed = int(os.environ.get("PYTEST_SEED", 42))
    np.random.seed(seed)
    random.seed(seed)
    yield seed  # 可以在测试中访问
    # 测试完成后无需清理

# -----------------------------
# 机制实例化 Fixture
# -----------------------------
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
# 如果后续添加 GaussianMechanism，可在这里 import

@pytest.fixture
def laplace_mechanism():
    """
    返回一个默认 epsilon=1.0 的 LaplaceMechanism 实例
    """
    return LaplaceMechanism(epsilon=1.0)

# 可扩展：提供 GaussianMechanism fixture
# from dplib.core.privacy.gaussian_mechanism import GaussianMechanism
# @pytest.fixture
# def gaussian_mechanism():
#     return GaussianMechanism(epsilon=1.0, delta=1e-5)

# -----------------------------
# 参数化示例 Fixture
# -----------------------------
@pytest.fixture(params=[0.1, 1.0, 10.0])
def epsilon(request):
    """
    为测试提供不同 epsilon 值
    """
    return request.param

@pytest.fixture(params=[1.0, 2.0, 5.0])
def sensitivity(request):
    """
    为测试提供不同敏感度
    """
    return request.param

# -----------------------------
# 简单工具函数
# -----------------------------
@pytest.fixture
def random_array():
    """
    返回一个随机浮点数组，默认长度 5
    """
    def _make_array(length=5):
        return np.random.rand(length)
    return _make_array
