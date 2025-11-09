"""
Laplace mechanism for pure differential privacy.

Responsibilities:
    * calibrate Laplace scale from epsilon and sensitivity
    * add Laplace noise to scalars, sequences, and arrays
    * persist calibration metadata for reproducibility
"""
# 说明：实现纯 (ε, 0)-DP 的拉普拉斯机制。
# 主要职责：
# 1) 由 epsilon 与全局敏感度 sensitivity 计算拉普拉斯噪声尺度 scale = sensitivity / epsilon
# 2) 对标量、序列、NumPy 数组逐元素加噪
# 3) 持久化校准元数据以确保可复现性

from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, CalibrationError


class LaplaceMechanism(BaseMechanism):
    """Pure (epsilon, 0)-DP Laplace mechanism."""

    def __init__(
        self,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)  
        self.sensitivity = float(sensitivity)    
        self.scale: Optional[float] = None       

    def _calibrate_parameters(self, *, sensitivity: Optional[float], **kwargs: Any) -> None:
        """Refresh the global sensitivity (if provided) and compute the Laplace scale."""
        # 受控校准流程（由基类 calibrate() 调用）：
        # - 若传入新的 sensitivity，则刷新内部敏感度
        # - 计算尺度参数 scale = sensitivity / epsilon
        del kwargs
        if sensitivity is not None:
            self.sensitivity = float(sensitivity)
        self.scale = self.sensitivity / self.epsilon  

    def randomise(self, value: Any) -> Any:
        """Add Laplace noise element-wise to numeric inputs."""
        # 加噪主入口：
        # 1) 确保已完成校准（scale 已就绪），否则抛出 CalibrationError
        # 2) 将输入统一为 ndarray，并记录是否为标量以便后续还原类型
        # 3) 依据输入形状采样拉普拉斯噪声并逐元素相加
        self.require_calibrated()
        if self.scale is None:
            raise CalibrationError("Laplace mechanism missing scale; call calibrate()")
        arr, was_scalar = self._coerce_numeric(value)       # arr: ndarray；was_scalar: 是否原始为标量
        # size=None -> 标量采样；否则与输入形状一致逐元素采样
        size = None if was_scalar else arr.shape
        noise = self._rng.laplace(0.0, self.scale, size=size)  # 采样中心为0、尺度为scale的拉普拉斯噪声
        result = arr + noise
        return self._restore_numeric_like(value, result, was_scalar)  # 按原始类型恢复（标量/数组）

    def serialize(self) -> Dict[str, Any]:
        """Persist sensitivity and scale alongside the base metadata."""
        # 序列化：在基类元数据基础上，额外保存敏感度与当前尺度参数
        base = super().serialize()
        base.update({"sensitivity": self.sensitivity, "scale": self.scale})
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "LaplaceMechanism":
        """Restore a Laplace mechanism, including custom metadata/scale."""
        # 反序列化：
        # - 使用保存的 epsilon 与 sensitivity 重新构造实例
        # - 恢复元信息 meta、校准状态 calibrated 以及 scale
        # - 注意：rng 不从数据中恢复，默认置为 None，避免在不同运行环境中绑定到不可用的随机源
        inst = cls(
            epsilon=data.get("epsilon"),
            sensitivity=data.get("sensitivity"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))                 
        inst._calibrated = bool(data.get("calibrated", False))  
        inst.scale = data.get("scale")                           
        return inst
