"""
Utility helpers for the CDP ML base layer.

Responsibilities
  - Provide lightweight ML-specific helpers for seeding and device selection.
  - Normalize checkpoint path conventions and JSON IO helpers.
  - Reuse core logging, RNG, and serialization utilities.

Usage Context
  - Used by ML training and evaluation modules for shared utilities.

Limitations
  - Device resolution relies on optional backends and only returns cpu/cuda.
"""
# 说明：CDP ML 子模块的轻量工具集合，聚焦训练相关的设备、种子与序列化。
# 职责：
# - seed_everything：统一 numpy 与可选框架的随机种子设置
# - resolve_device：解析训练设备（cpu/cuda）并处理后端缺失
# - checkpoint_path：规范化模型检查点路径生成
# - json_read/json_write：复用 core.serialization 的 JSON 读写流程

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Sequence, Union

import numpy as np

from dplib.core.utils.logging import get_logger
from dplib.core.utils.param_validation import ensure, ensure_type
from dplib.core.utils.random import create_rng
from dplib.core.utils.serialization import deserialize_from_json, serialize_to_json

from .exceptions import BackendNotAvailable

logger = get_logger(__name__)


def seed_everything(seed: Optional[int]) -> np.random.Generator:
    """
    Seed numpy and optional ML backends, returning a numpy Generator.
    """
    # 设置 numpy 与可选后端的随机种子，返回可复现的 numpy RNG
    ensure_type(seed, (int, type(None)), label="seed")
    rng = create_rng(seed)
    np.random.seed(seed)
    if seed is None:
        return rng

    def _seed_torch(value: int) -> None:
        # torch 为可选依赖，缺失时直接忽略
        try:
            import torch  # type: ignore
        except Exception:
            return
        torch.manual_seed(value)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(value)

    def _seed_tensorflow(value: int) -> None:
        # tensorflow 为可选依赖，缺失时直接忽略
        try:
            import tensorflow as tf  # type: ignore
        except Exception:
            return
        tf.random.set_seed(value)

    _seed_torch(int(seed))
    _seed_tensorflow(int(seed))
    return rng


def resolve_device(prefer: Optional[str] = None) -> str:
    """
    Resolve training device string from optional preference.
    """
    # 根据偏好解析 cpu/cuda 设备，缺失后端时给出明确错误提示
    if prefer is None:
        torch = _try_import_torch()
        if torch is not None and torch.cuda.is_available():
            logger.debug("Resolved device to cuda based on torch availability.")
            return "cuda"
        logger.debug("Resolved device to cpu (no CUDA backend detected).")
        return "cpu"

    ensure_type(prefer, (str,), label="prefer")
    prefer_value = prefer.strip().lower()
    ensure(prefer_value in {"cpu", "cuda"}, "prefer must be 'cpu' or 'cuda'")
    if prefer_value == "cpu":
        return "cpu"

    torch = _try_import_torch()
    if torch is None:
        raise BackendNotAvailable(
            "torch",
            extras="ml-torch",
            message="torch is required to resolve CUDA devices",
        )
    if not torch.cuda.is_available():
        raise BackendNotAvailable(
            "cuda",
            extras="ml-torch",
            message="CUDA is not available in the installed torch build",
        )
    return "cuda"


def checkpoint_path(base_dir: Union[os.PathLike, str], name: str, step: Optional[int] = None) -> str:
    """
    Build a standardized checkpoint path under the base directory.
    """
    # 统一生成检查点文件路径，便于训练过程中的命名规范化
    ensure_type(base_dir, (str, os.PathLike), label="base_dir")
    ensure_type(name, (str,), label="name")
    ensure(name.strip() != "", "name must be non-empty")
    if step is not None:
        ensure_type(step, (int,), label="step")
        ensure(step >= 0, "step must be >= 0")
        filename = f"{name}_step_{step}"
    else:
        filename = name
    path = Path(base_dir) / f"{filename}.ckpt"
    return str(path)


def json_read(path: Union[os.PathLike, str]) -> Any:
    """
    Read a JSON file using core serialization helpers.
    """
    # 读取 JSON 文件并使用 core.serialization 进行反序列化
    ensure_type(path, (str, os.PathLike), label="path")
    text = Path(path).read_text(encoding="utf-8")
    logger.debug("Loaded JSON payload from %s.", path)
    return deserialize_from_json(text)


def json_write(
    path: Union[os.PathLike, str],
    payload: Any,
    *,
    sensitive_fields: Optional[Sequence[str]] = None,
    version: Optional[str] = None,
) -> None:
    """
    Write a JSON file using core serialization helpers.
    """
    # 将对象序列化为 JSON 并写入指定路径
    ensure_type(path, (str, os.PathLike), label="path")
    text = serialize_to_json(payload, sensitive_fields=sensitive_fields, version=version)
    Path(path).write_text(text, encoding="utf-8")
    logger.debug("Wrote JSON payload to %s.", path)


def _try_import_torch() -> Optional[Any]:
    # 尝试懒加载 torch，缺失时返回 None
    try:
        import torch  # type: ignore
    except Exception:
        return None
    return torch
