"""
Unified Random Number Generator (RNG) factory.
"""
from typing import Optional
import numpy as np

def make_rng(seed: Optional[int]) -> np.random.Generator:
    """
    Create a fresh numpy Generator from a seed.
    
    Args:
        seed: Integer seed or None.
    
    Returns:
        np.random.Generator
    """
    if seed is None:
        return np.random.default_rng()
    return np.random.default_rng(seed)
