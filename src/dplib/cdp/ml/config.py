"""
Configuration objects for the CDP ML base layer.

Responsibilities
  - Define validated configuration containers for model, training, and DP settings.
  - Provide JSON-friendly serialization helpers for configuration payloads.
  - Centralize configuration validation rules for ML workflows.

Usage Context
  - Used by training engines, backends, and evaluation routines.

Limitations
  - Validation covers basic ranges and does not inspect model-specific parameters.
"""
# 说明：CDP ML 基础层配置对象，覆盖模型、训练、DP 与会计设置。
# 职责：
# - ModelConfig/TrainingConfig/DPConfig/AccountingConfig：分层管理 ML 配置项
# - MLConfig：统一聚合配置入口并提供验证与序列化能力
# - validate/to_dict/from_dict：规范配置校验与 JSON 友好转换流程

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError


@dataclass
class ModelConfig:
    """
    Model configuration describing the model type and backend.

    - Configuration
      - model_type: Model identifier used by factories.
      - backend: Optional backend identifier such as sklearn or torch.
      - params: Model-specific parameters.

    - Behavior
      - Validates presence and type of the model identifier.

    - Usage Notes
      - Use as the primary input for model factories.
    """
    # 模型配置对象，描述模型类型、后端与参数

    model_type: str
    backend: Optional[str] = None
    params: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> "ModelConfig":
        # 校验模型名称与参数类型，确保后续工厂逻辑可用
        ensure_type(self.model_type, (str,), label="model_type")
        ensure(self.model_type.strip() != "", "model_type must be non-empty")
        if self.backend is not None:
            ensure_type(self.backend, (str,), label="backend")
            ensure(self.backend.strip() != "", "backend must be non-empty")
        ensure_type(self.params, (Mapping,), label="params")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将模型配置导出为可序列化字典
        return {
            "model_type": self.model_type,
            "backend": self.backend,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelConfig":
        """Create ModelConfig from a dictionary payload."""
        # 从字典还原模型配置，缺失字段时抛出明确错误
        if "model_type" not in data:
            raise ParamValidationError("model_type is required")
        return cls(
            model_type=data["model_type"],
            backend=data.get("backend"),
            params=data.get("params", {}),
        )


@dataclass
class TrainingConfig:
    """
    Training configuration for ML workloads.

    - Configuration
      - epochs: Number of training epochs.
      - batch_size: Training batch size.
      - learning_rate: Optimizer learning rate.
      - shuffle: Whether to shuffle training data.
      - seed: Optional random seed.

    - Behavior
      - Validates numeric ranges and boolean flags.

    - Usage Notes
      - Use to configure training loops and data loaders.
    """
    # 训练配置对象，描述训练轮次、批大小、学习率与随机种子等信息

    epochs: int = 1
    batch_size: int = 32
    learning_rate: float = 1e-3
    shuffle: bool = True
    seed: Optional[int] = None

    def validate(self) -> "TrainingConfig":
        # 校验训练参数的基本范围，确保训练循环的基本假设成立
        ensure_type(self.epochs, (int,), label="epochs")
        ensure_type(self.batch_size, (int,), label="batch_size")
        ensure_type(self.learning_rate, (float, int), label="learning_rate")
        ensure_type(self.shuffle, (bool,), label="shuffle")
        ensure(self.epochs > 0, "epochs must be > 0")
        ensure(self.batch_size > 0, "batch_size must be > 0")
        ensure(self.learning_rate > 0, "learning_rate must be > 0")
        if self.seed is not None:
            ensure_type(self.seed, (int,), label="seed")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将训练配置导出为可序列化字典
        return {
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "shuffle": self.shuffle,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TrainingConfig":
        """Create TrainingConfig from a dictionary payload."""
        # 从字典还原训练配置，缺省字段使用默认值
        epochs_value = data.get("epochs")
        batch_value = data.get("batch_size")
        lr_value = data.get("learning_rate")
        shuffle_value = data.get("shuffle")
        return cls(
            epochs=int(epochs_value) if epochs_value is not None else cls.epochs,
            batch_size=int(batch_value) if batch_value is not None else cls.batch_size,
            learning_rate=float(lr_value) if lr_value is not None else cls.learning_rate,
            shuffle=shuffle_value if shuffle_value is not None else cls.shuffle,
            seed=data.get("seed"),
        )


@dataclass
class DPConfig:
    """
    Differential privacy configuration for training.

    - Configuration
      - enabled: Whether DP is enabled.
      - epsilon: Optional target epsilon.
      - delta: Optional target delta.
      - noise_multiplier: Noise multiplier for DP-SGD.
      - max_grad_norm: Gradient clipping norm.

    - Behavior
      - Validates ranges and required fields when enabled.

    - Usage Notes
      - Use to configure DP-SGD and privacy accounting.
    """
    # DP 训练配置，包含噪声尺度与裁剪阈值等关键参数

    enabled: bool = False
    epsilon: Optional[float] = None
    delta: Optional[float] = None
    noise_multiplier: Optional[float] = None
    max_grad_norm: Optional[float] = None

    def validate(self) -> "DPConfig":
        # 校验 DP 训练参数的范围，并在启用 DP 时要求关键字段存在
        ensure_type(self.enabled, (bool,), label="enabled")
        if self.epsilon is not None:
            ensure_type(self.epsilon, (float, int), label="epsilon")
            ensure(self.epsilon >= 0, "epsilon must be >= 0")
        if self.delta is not None:
            ensure_type(self.delta, (float, int), label="delta")
            ensure(0 < float(self.delta) < 1, "delta must be in (0,1)")
        if self.noise_multiplier is not None:
            ensure_type(self.noise_multiplier, (float, int), label="noise_multiplier")
            ensure(self.noise_multiplier >= 0, "noise_multiplier must be >= 0")
        if self.max_grad_norm is not None:
            ensure_type(self.max_grad_norm, (float, int), label="max_grad_norm")
            ensure(self.max_grad_norm > 0, "max_grad_norm must be > 0")
        if self.enabled:
            ensure(self.noise_multiplier is not None, "noise_multiplier required when dp is enabled")
            ensure(self.max_grad_norm is not None, "max_grad_norm required when dp is enabled")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将 DP 配置导出为可序列化字典
        return {
            "enabled": self.enabled,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "noise_multiplier": self.noise_multiplier,
            "max_grad_norm": self.max_grad_norm,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DPConfig":
        """Create DPConfig from a dictionary payload."""
        # 从字典还原 DP 配置，缺省字段使用默认值
        enabled_value = data.get("enabled")
        return cls(
            enabled=enabled_value if enabled_value is not None else cls.enabled,
            epsilon=data.get("epsilon"),
            delta=data.get("delta"),
            noise_multiplier=data.get("noise_multiplier"),
            max_grad_norm=data.get("max_grad_norm"),
        )


@dataclass
class AccountingConfig:
    """
    Privacy accounting configuration for ML training.

    - Configuration
      - method: Accounting method identifier.
      - sample_rate: Optional sample rate for accounting.
      - steps: Optional number of steps to account for.
      - target_epsilon: Optional target epsilon.
      - target_delta: Optional target delta.

    - Behavior
      - Validates numeric ranges and required value shapes.

    - Usage Notes
      - Use to drive privacy accounting and calibration.
    """
    # 会计配置对象，描述会计方法与采样率等参数

    method: str = "rdp"
    sample_rate: Optional[float] = None
    steps: Optional[int] = None
    target_epsilon: Optional[float] = None
    target_delta: Optional[float] = None

    def validate(self) -> "AccountingConfig":
        # 校验会计配置参数的基本范围，确保会计器可用
        ensure_type(self.method, (str,), label="method")
        ensure(self.method.strip() != "", "method must be non-empty")
        if self.sample_rate is not None:
            ensure_type(self.sample_rate, (float, int), label="sample_rate")
            ensure(0 < float(self.sample_rate) <= 1, "sample_rate must be in (0,1]")
        if self.steps is not None:
            ensure_type(self.steps, (int,), label="steps")
            ensure(self.steps > 0, "steps must be > 0")
        if self.target_epsilon is not None:
            ensure_type(self.target_epsilon, (float, int), label="target_epsilon")
            ensure(self.target_epsilon >= 0, "target_epsilon must be >= 0")
        if self.target_delta is not None:
            ensure_type(self.target_delta, (float, int), label="target_delta")
            ensure(0 < float(self.target_delta) < 1, "target_delta must be in (0,1)")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将会计配置导出为可序列化字典
        return {
            "method": self.method,
            "sample_rate": self.sample_rate,
            "steps": self.steps,
            "target_epsilon": self.target_epsilon,
            "target_delta": self.target_delta,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AccountingConfig":
        """Create AccountingConfig from a dictionary payload."""
        # 从字典还原会计配置，缺省字段使用默认值
        return cls(
            method=data.get("method", cls.method),
            sample_rate=data.get("sample_rate"),
            steps=data.get("steps"),
            target_epsilon=data.get("target_epsilon"),
            target_delta=data.get("target_delta"),
        )


@dataclass
class MLConfig:
    """
    Aggregated ML configuration for training workflows.

    - Configuration
      - model: ModelConfig describing the model type.
      - training: TrainingConfig with training loop settings.
      - dp: DPConfig with privacy settings.
      - accounting: AccountingConfig with accounting settings.
      - metadata: Additional metadata for auditing.

    - Behavior
      - Validates nested configuration objects.

    - Usage Notes
      - Use as the canonical configuration payload for ML APIs.
    """
    # ML 训练配置聚合入口，封装模型/训练/DP/会计等配置

    model: ModelConfig
    training: TrainingConfig = field(default_factory=TrainingConfig)
    dp: DPConfig = field(default_factory=DPConfig)
    accounting: AccountingConfig = field(default_factory=AccountingConfig)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> "MLConfig":
        # 统一调用子配置的校验逻辑，确保整体配置可用
        ensure_type(self.model, (ModelConfig,), label="model")
        ensure_type(self.training, (TrainingConfig,), label="training")
        ensure_type(self.dp, (DPConfig,), label="dp")
        ensure_type(self.accounting, (AccountingConfig,), label="accounting")
        ensure_type(self.metadata, (Mapping,), label="metadata")
        self.model.validate()
        self.training.validate()
        self.dp.validate()
        self.accounting.validate()
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将聚合配置导出为可序列化字典
        return {
            "model": self.model.to_dict(),
            "training": self.training.to_dict(),
            "dp": self.dp.to_dict(),
            "accounting": self.accounting.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MLConfig":
        """Create MLConfig from a dictionary payload."""
        # 从字典还原聚合配置，支持嵌套 dict 或对象实例
        if "model" not in data:
            raise ParamValidationError("model configuration is required")
        model_value = data["model"]
        if isinstance(model_value, ModelConfig):
            model = model_value
        elif isinstance(model_value, Mapping):
            model = ModelConfig.from_dict(model_value)
        else:
            raise ParamValidationError("model must be ModelConfig or mapping")

        training_value = data.get("training", {})
        if isinstance(training_value, TrainingConfig):
            training = training_value
        elif isinstance(training_value, Mapping):
            training = TrainingConfig.from_dict(training_value)
        else:
            raise ParamValidationError("training must be TrainingConfig or mapping")

        dp_value = data.get("dp", {})
        if isinstance(dp_value, DPConfig):
            dp = dp_value
        elif isinstance(dp_value, Mapping):
            dp = DPConfig.from_dict(dp_value)
        else:
            raise ParamValidationError("dp must be DPConfig or mapping")

        accounting_value = data.get("accounting", {})
        if isinstance(accounting_value, AccountingConfig):
            accounting = accounting_value
        elif isinstance(accounting_value, Mapping):
            accounting = AccountingConfig.from_dict(accounting_value)
        else:
            raise ParamValidationError("accounting must be AccountingConfig or mapping")

        return cls(
            model=model,
            training=training,
            dp=dp,
            accounting=accounting,
            metadata=data.get("metadata", {}),
        )
