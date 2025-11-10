# NSSDPlib API 接口协议

---

## 1. 总体设计原则
- 所有机制类统一继承 `BaseMechanism`，共享生命周期、序列化与异常模型，避免多套隐私预算语义。
- 严格参数校验 + 明确异常层次，确保 SDK 与服务端能够做精确错误兜底。
- 强制链式调用友好（`calibrate(...)->randomise(...)->serialize()`），便于在流水线/管道中组合。
- 序列化结果必须可 JSON 化，便于跨语言传输与持久化，同时允许通过 `meta` 字段携带定制信息。
- 默认实现无状态（除 RNG 与校准缓存），可通过 `reseed()` 与 `deserialize()` 保证可重现性。

---

## 2. 核心抽象：`BaseMechanism`

### 2.1 构造参数
| 参数 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `epsilon` | float | 是 | - | 隐私预算，必须为 `>0`。 |
| `delta` | float | 否 | `0.0` | 仅对近似 / CDP 机制生效，要求 `>=0`。 |
| `rng` | `np.random.Generator \| seed` | 否 | `None` | 内部噪声源，可传已有 `Generator` 或任意可播种对象。 |
| `name` | str | 否 | 类名 | 用于日志与序列化中的 `name` 字段。 |

### 2.2 生命周期
1. **实例化**：完成 ε/δ 校验，构建 RNG，`calibrated=False`。
2. **`calibrate()`**：由子类 `_calibrate_parameters()` 计算噪声参数（如 scale/sigma）。成功后 `_calibrated=True` 并返回 `self` 以支持链式写法。
3. **`randomise()` / `add_noise()`**：调用前必须处于已校准状态，否则抛出 `NotCalibratedError`。输入通过 `_coerce_numeric()` 规整，输出再由 `_restore_numeric_like()` 复原形状。
4. **`serialize()` / `to_json()`**：输出快照用于跨进程共享；`deserialize()` / `from_json()` 负责恢复实例，RNG 默认重新初始化以避免跨主机不一致。
5. **维护操作**：`reset_calibration()`、`reseed()`、`mechanism_id` 等辅助能力保持机制状态可控。

### 2.3 公共方法契约
| 方法 | 关键签名 | 行为约定 | 常见异常 |
| --- | --- | --- | --- |
| `calibrate()` | `calibrate(sensitivity: Optional[float] = None, **kwargs)` | 校准噪声参数，返回 `self`。未提供 sensitivity 时沿用构造参数。 | `ValidationError` (参数非法)、子类自定义异常 |
| `randomise()` | `randomise(value: Any) -> Any` | 对标量、序列或 `np.ndarray` 加噪，保持输入结构。 | `NotCalibratedError`、`ValidationError` |
| `add_noise()` | `add_noise(value)` | `randomise()` 的语义别名，便于更自然的 API（例如 `mechanism.add_noise(x)`）。 | 同上 |
| `reset_calibration()` | `reset_calibration()` | 仅清空 `_calibrated`，不改变子类缓存，常用于热重载。 | - |
| `require_calibrated()` | - | 运行期保护，在自定义流程中显式断言。 | `NotCalibratedError` |
| `serialize()/deserialize()` | - | JSON 兼容的 dict，字段见 2.4。子类可 `base.update({...})` 扩展。 | `ValidationError` |
| `to_json()/from_json()` | - | 方便直接持久化到文本 / 网络。 | `ValidationError` |
| `reseed()` | `reseed(seed)` | 用新的种子重建 RNG，便于 deterministic 测试。 | - |
| `mechanism_id` | property | 机制稳定 ID；默认为类名去掉 `Mechanism` 后缀并转小写。 | - |

### 2.4 序列化字段
```json
{
  "class": "dplib.cdp.mechanisms.laplace.LaplaceMechanism",
  "mechanism": "laplace",
  "name": "LaplaceMechanism",
  "epsilon": 1.0,
  "delta": 0.0,
  "calibrated": true,
  "meta": {}
}
```
- **必选字段**：`class`, `mechanism`, `epsilon`, `delta`, `calibrated`, `meta`。
- **子类扩展**：使用 `serialize()` 的 `dict.update()` 附加字段，例如 `{"sensitivity": 2.0, "scale": 0.5}`。
- **`meta` 约定**：自由键值，但需保持 JSON 兼容；推荐写入追踪信息（数据域、运行环境、调参标识）。

### 2.5 校验与异常
- 所有机制异常继承 `MechanismError`，并细分：
  - `ValidationError`：输入/参数非法（包含 ε、δ、值域、迭代器等）。
  - `CalibrationError`：噪声参数缺失或与当前 ε/δ 不一致。
  - `NotCalibratedError`：在未校准状态调用随机化相关方法。
- 业务层捕获 `MechanismError` 可统一转换成 HTTP/SDK 错误响应。

---

## 3. CDP 机制接口

### 3.1 `LaplaceMechanism`
- 纯 `(ε, 0)` 拉普拉斯噪声，`scale = sensitivity / epsilon`。
- 构造参数包含 `sensitivity`（默认 1），`calibrate()` 可覆盖新的敏感度。
- `randomise()` 支持 float、list/tuple、`np.ndarray`，内部会自动广播噪声。
- 序列化附加字段：
  ```json
  {
    "... base fields ...": "...",
    "sensitivity": 2.0,
    "scale": 2.0
  }
  ```
- 使用示例：
  ```python
  mech = LaplaceMechanism(epsilon=0.5, sensitivity=1.0).calibrate()
  private_result = mech.randomise(42.0)
  snapshot = mech.serialize()  # 可写入存储或通过 API 透出
  restored = LaplaceMechanism.deserialize(snapshot)
  restored.randomise(21.0)
  ```

### 3.2 `GaussianMechanism`
- 近似差分隐私 `(ε, δ)`，要求 `delta > 0`（构造、校准阶段二次校验）。
- 采用经典常数 `1.25`：`sigma = Δf * sqrt(2 * ln(1.25 / δ)) / ε`。
- `calibrate()` 支持同时覆盖 `sensitivity` 与 `delta`，并写入 `sigma`。
- 序列化扩展字段：`{"sensitivity": ..., "delta": ..., "sigma": ...}`。
- 建议在分析作业中显式传入业务使用的 δ 值，避免默认为 `1e-5`。

---

## 4. LDP 机制与编码器蓝图

### 4.1 `LDPMechanism`（规划)
- 继承 `BaseMechanism`，额外暴露 `encode()` / `decode()`（如需要）用于本地扰动前的数据准备。
- 推荐契约：
  ```python
  class LDPMechanism(BaseMechanism):
      encoder: "Encoder"

      def encode(self, value: Any) -> Any:
          return self.encoder.encode(value)

      def randomise(self, value: Any) -> Any:
          encoded = self.encode(value)
          ...  # 添加局部噪声
  ```
- `meta` 字段可保存编码器的结构信息（hash 函数、bucket 数等），以便服务端还原。

### 4.2 `Encoder`
- 抽象接口需至少实现 `encode(value) -> Any`，必要时可补充 `decode()` 或 `domain()`。
- 设计原则：纯函数、无状态、可序列化；通过组合实现 bit flipping、RAPPOR、Bloom filter 等编码策略。
- 在序列化时，将编码器参数嵌入机制 `meta` 下的 `encoder` 子字段：
  ```json
  "meta": {
    "encoder": {
      "class": "dplib.ldp.encoders.bloom.BloomEncoder",
      "config": {"k": 2, "m": 1024}
    }
  }
  ```

---

## 5. 典型 API 调用流程

### 5.1 CDP 工作流
```python
mech = LaplaceMechanism(epsilon=1.0, sensitivity=1.0).calibrate()
true_value = 10.0
noisy = mech.randomise(true_value)
store.write(mech.serialize())  # 可复用相同机制配置
```
- 步骤：构造 → `calibrate()` → `randomise()` → （可选）序列化。
- 若需重新调参：`mech.reset_calibration()` 后再次 `calibrate(new_sensitivity)`。

### 5.2 LDP 工作流（示例）
```python
encoder = SomeEncoder(domain=["A", "B", "C"])
mech = LDPMechanism(epsilon=0.8, encoder=encoder).calibrate()
encoded = mech.encode(user_value)
report = mech.randomise(encoded)
```
- 客户端只暴露已扰动的报告；服务端依靠 `meta.encoder` 信息聚合。

### 5.3 查询 API：`PrivateCountQuery`
- 位置：`dplib.cdp.analytics.queries.count.PrivateCountQuery`。
- 构造参数：`epsilon`（必填）、`mechanism`（可选，默认内部创建已校准的拉普拉斯机制）、`predicate`。
- 行为约定：
  1. `evaluate(data, predicate=None)`：强制数据可迭代，`predicate` 为空时直接计数。
  2. 若传入自定义 `mechanism`，调用者必须预先完成 `calibrate()`，否则抛出 `ValidationError`。
  3. 默认敏感度为 1，适用于标准计数查询；复杂场景可自建机制传入。
- 示例：
  ```python
  custom = GaussianMechanism(epsilon=1.0, delta=1e-5, sensitivity=1.0).calibrate()
  query = PrivateCountQuery(epsilon=1.0, mechanism=custom)
  result = query.evaluate(dataset, predicate=lambda x: x.is_valid())
  ```

---

## 6. 错误与异常协定
- **统一前缀**：所有机制 / 查询相关异常均继承 `MechanismError`，便于外层一次性捕获。
- **分类处理**：
  | 异常 | 触发场景 | 建议处理 |
  | --- | --- | --- |
  | `ValidationError` | ε/δ/敏感度非法、值非可迭代、传入机制未校准等 | 400/422 错误，提示调用者修正输入 |
  | `CalibrationError` | 噪声参数缺失、scale/sigma 未生成 | 重试或重新校准 |
  | `NotCalibratedError` | 直接 `randomise` 未先 `calibrate` | 指导调用者先调用 `calibrate()` |
  | 其他自定义 | 机制内部可扩展，如 `EncoderError` | 按需扩展 |

---

## 7. 返回值与序列化示例
- `randomise()`：与输入数据类型保持一致（标量 → float、list → list、ndarray → ndarray），以免破坏调用方的进一步计算。
- `serialize()` 示例（Laplace）：
  ```json
  {
    "class": "dplib.cdp.mechanisms.laplace.LaplaceMechanism",
    "mechanism": "laplace",
    "name": "LaplaceMechanism",
    "epsilon": 1.0,
    "delta": 0.0,
    "calibrated": true,
    "meta": {},
    "sensitivity": 2.0,
    "scale": 2.0
  }
  ```
- `serialize()` 示例（Gaussian）：
  ```json
  {
    "... base fields ...": "...",
    "sensitivity": 1.0,
    "delta": 1e-5,
    "sigma": 2.378
  }
  ```

---

## 8. 扩展与自定义 checklist
1. **继承** `BaseMechanism` 并实现 `_calibrate_parameters()` 与 `randomise()`。
2. **状态字段** 全部挂在实例属性上，便于 `serialize()` 收集；不要依赖全局变量。
3. **序列化**：在 `super().serialize()` 的基础上追加自定义字段；`deserialize()` 负责恢复它们。
4. **异常**：沿用现有异常层级；如需新异常，也应继承 `MechanismError`。
5. **测试**：至少覆盖
   - 参数校验（非法 ε/δ/敏感度）
   - `calibrate()` 多次调用行为
   - `randomise()` 对不同输入形态的一致性

---

## 9. API 版本管理
- 采用语义化版本号（`MAJOR.MINOR.PATCH`），重大 breaking 变更必须 bump MAJOR。
- 每次接口新增/修改需在本文档中更新对应小节并以 changelog 说明（可在 PR 描述同步）。
- 对外服务在响应头或 payload 中暴露 `api_version` 字段，便于客户端识别。

---
