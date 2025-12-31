"""Entry point for the CDP ML backends."""

from __future__ import annotations

from .registry import BackendCapabilities, BackendSpec, detect_available_backends, get_backend

__all__ = [
    "BackendCapabilities",
    "BackendSpec",
    "detect_available_backends",
    "get_backend",
]
