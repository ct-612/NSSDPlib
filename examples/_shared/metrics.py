"""
Simple metrics for validating example outputs.
"""
from typing import Any, Sequence, Union
import numpy as np

def _to_numpy(data: Any) -> np.ndarray:
    return np.asarray(data, dtype=float)

def l1_error(p: Union[Sequence, np.ndarray], q: Union[Sequence, np.ndarray]) -> float:
    """Calculate L1 distance (sum of absolute differences)."""
    p_arr = _to_numpy(p)
    q_arr = _to_numpy(q)
    return float(np.sum(np.abs(p_arr - q_arr)))

def max_abs_error(p: Union[Sequence, np.ndarray], q: Union[Sequence, np.ndarray]) -> float:
    """Calculate Maximum Absolute Error (L-infinity distance)."""
    p_arr = _to_numpy(p)
    q_arr = _to_numpy(q)
    return float(np.max(np.abs(p_arr - q_arr)))

def mean_squared_error(p: Union[Sequence, np.ndarray], q: Union[Sequence, np.ndarray]) -> float:
    """Calculate Mean Squared Error."""
    p_arr = _to_numpy(p)
    q_arr = _to_numpy(q)
    return float(np.mean((p_arr - q_arr) ** 2))
