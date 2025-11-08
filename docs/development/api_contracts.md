# NSSDPlib API 接口协议

---

## 1. 总体设计原则
- 所有机制类均实现统一接口（BaseMechanism）
- 参数校验与错误处理标准化
- 支持链式调用与上下文管理
- 返回值结构清晰，便于前后端集成

---

## 2. 核心接口定义

### BaseMechanism
```python
class BaseMechanism(ABC):
    def __init__(self, epsilon: float, delta: float = 0.0, rng: Optional[Any] = None, name: Optional[str] = None): ...
    def calibrate(self, sensitivity: float, **kwargs) -> None: ...
    def randomise(self, value: Any) -> Any: ...
    def serialize(self) -> Dict[str, Any]: ...
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "BaseMechanism": ...
    """
    - 抽象基类接口，所有机制必须实现以下方法：
        - __init__：构造函数，接受隐私预算、随机数生成器等基础参数。
        - calibrate：计算噪声参数并进入已校准状态。
        - randomise：对输入数据加噪并返回。
        - serialize / deserialize：机制状态可序列化和恢复。
    """
```

#### 参数说明
- `epsilon` (float): 隐私预算，必须为正数
- `delta` (float): 隐私参数，CDP机制必需，LDP可选
- `sensitivity` (float): 查询敏感度，必须为正数
- `rng` (可选): 随机数生成器或种子
- `name` (可选): 机制名称

#### 返回值
- `randomise`: 返回加噪后的数据（float/int/array）
- `serialize`: 返回机制状态字典
- `deserialize`: 返回机制实例

#### 错误处理
- 参数不合法时抛出 `MechanismError` 或其子类
- 未校准机制调用 `randomise` 时抛出 `NotCalibratedError`

---

## 3. CDP 机制接口

### LaplaceMechanism
```python
class LaplaceMechanism(BaseMechanism):
    def calibrate(self, sensitivity: float): ...
    def randomise(self, value: float) -> float: ...
    """
    - 继承 BaseMechanism，实现拉普拉斯噪声机制。
    - 只需实现 calibrate 和 randomise。
    """
```

### GaussianMechanism
```python
class GaussianMechanism(BaseMechanism):
    def calibrate(self, sensitivity: float, delta: float = None): ...
    def randomise(self, value: float) -> float: ...
    """
    - 继承 BaseMechanism，实现高斯噪声机制。
    - calibrate 允许覆盖 delta。
    """
```

---

## 4. LDP 机制接口

### LDPMechanism
```python
class LDPMechanism(BaseMechanism):
    def encode(self, value: Any) -> Any: ...
    def randomise(self, value: Any) -> Any: ...
    """
    - 用于本地差分隐私（LDP）。
    - 支持数据编码 encode()，然后添加噪声。
    """
```

### Encoder
```python
class Encoder(ABC):
    def encode(self, value: Any) -> Any: ...
    """
    - 抽象编码器接口。
    - 可自定义编码方式（如hashing、bloom_filter）。
    """
```

---

## 5. 典型 API 调用流程

### CDP 机制
```python
mech = LaplaceMechanism(epsilon=1.0, sensitivity=1.0)
mech.calibrate(sensitivity=2.0)
noisy = mech.randomise(10.0)
"""
- CDP使用流程：创建机制 → 校准 → 添加噪声。
"""
```

### LDP 机制
```python
encoder = SomeEncoder(...)
mech = LDPMechanism(epsilon=1.0, encoder=encoder)
encoded = mech.encode(42)
noisy = mech.randomise(encoded)
"""
- LDP使用流程：创建编码器 → 创建机制 → 编码 → 添加噪声。
"""
```

---

## 6. 错误与异常协议
- 所有机制相关错误均继承自 `MechanismError`
- 常见异常：
  - `ValidationError`: 参数校验失败
  - `CalibrationError`: 校准失败
  - `NotCalibratedError`: 未校准机制调用

---

## 7. 返回值结构示例

### serialize()
```json
{
  "class": "dplib.cdp.mechanisms.laplace.LaplaceMechanism",
  "epsilon": 1.0,
  "delta": 0.0,
  "sensitivity": 2.0,
  "calibrated": true,
  "meta": {}
}
```

---

## 8. 扩展与自定义协议
- 新机制需继承 BaseMechanism 并实现 calibrate/randomise/serialize
- 可通过 meta 字段扩展序列化内容
- 支持自定义异常类型

---

## 9. API 版本管理
- 所有接口变更需在文档中注明版本
- 推荐使用语义化版本号（如 v1.2.0）

---
