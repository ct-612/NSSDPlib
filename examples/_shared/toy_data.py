"""
Toy data generation helpers for examples.
"""
from typing import List, Optional, Tuple, Any
import numpy as np

def build_categorical_dataset(
    n_users: int,
    categories: List[Any],
    weights: Optional[List[float]] = None,
    rng: Optional[np.random.Generator] = None
) -> List[Any]:
    """
    Generate a list of categorical values.
    
    Args:
        n_users: Number of samples.
        categories: List of possible categories.
        weights: Probability weights for each category (sums to 1).
        rng: Random number generator.
        
    Returns:
        List of values.
    """
    if rng is None:
        rng = np.random.default_rng()
        
    return list(rng.choice(categories, size=n_users, p=weights))

def build_numerical_dataset(
    n_users: int,
    low: float,
    high: float,
    rng: Optional[np.random.Generator] = None,
    dtype: type = float
) -> np.ndarray:
    """
    Generate a numpy array of numerical values.
    
    Args:
        n_users: Number of samples.
        low: Lower bound.
        high: Upper bound.
        rng: Random number generator.
        dtype: Output data type (float or int).
        
    Returns:
        Numpy array.
    """
    if rng is None:
        rng = np.random.default_rng()
        
    if dtype is int:
        return rng.integers(low, high, size=n_users)
    return rng.uniform(low, high, size=n_users)
