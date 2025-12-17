"""Unified entry point for LDP encoders."""

from __future__ import annotations

from .base import BaseEncoder, FittedEncoder, StatelessEncoder
from .bloom_filter import BloomFilterEncoder
from .categorical import CategoricalEncoder
from .encoder_factory import (
    EncoderFactory,
    build_encoder_pipeline,
    create_encoder,
    get_encoder_class,
    register_encoder,
)
from .hashing import HashEncoder
from .numerical import NumericalBucketsEncoder
from .sketch import SketchEncoder
from .unary import BinaryEncoder, UnaryEncoder

__all__ = [
    "BaseEncoder",
    "StatelessEncoder",
    "FittedEncoder",
    "CategoricalEncoder",
    "NumericalBucketsEncoder",
    "UnaryEncoder",
    "BinaryEncoder",
    "HashEncoder",
    "BloomFilterEncoder",
    "SketchEncoder",
    "register_encoder",
    "get_encoder_class",
    "create_encoder",
    "build_encoder_pipeline",
    "EncoderFactory",
]
