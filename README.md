# **NSSDPlib**

### 🔹 统一差分隐私库。目标：
* **统一架构**：提供统一的核心框架（core）、CDP 模块、LDP 模块三层结构。
* **可复用组件**：实现机制工厂、隐私会计、敏感度分析、组合定理、聚合器等通用组件。
* **可验证隐私**：提供形式化隐私证明与测试工具。
* **可扩展生态**：开放接口支持第三方机制与模型插件。
* **高效运行**：兼顾数值稳定性与计算性能，支持大规模实验与基准测试。
---

### 🔹 快速开始
```bash
# 本地初始化

git clone https://github.com/ct-612/NSSDPlib.git

cd NSSDPlib

python -m venv .venv

.venv\Scripts\activate.ps1

pip install -e ".[dev,core,cdp,ldp]"

pytest -q
```
---

## 推荐安装组合（Recommended Install Profiles）

> 说明：本项目采用可选依赖（extras）进行模块化安装。
>
> * `cdp` 默认 **不包含** 机器学习训练依赖（以保持依赖轻量、安装更快、冲突更少）。
> * 需要 DP-SGD/训练/模型评估时，额外安装 `ml`：即 `.[cdp,ml]`。
> * 一键全量环境使用 `.[all]`。

### 1）最小可用：Core（基础抽象 + 数据/隐私/工具链）

适用于：只需要 `core/*` 能力（Domain/Dataset、会计器抽象、工具函数），或作为其他工程依赖。

```bash
pip install -e ".[core]"
```

包含能力（示例）：

* `dplib.core.data`：Domain / Dataset / Transformers / Validation / Statistics / Sensitivity
* `dplib.core.privacy`：BaseMechanism / PrivacyModel / PrivacyAccountant / BudgetTracker / Composition
* `dplib.core.utils`：param_validation / serialization / logging / performance / random 等

---

### 2）CDP（不含 ML）：服务端差分隐私统计分析与机制体系

适用于：做 DP 机制、组合、查询分析、敏感度与报告（如有），但**不做模型训练**。

```bash
pip install -e ".[cdp]"
```

包含能力（示例）：

* `dplib.cdp.mechanisms`：Laplace / Gaussian / Exponential / Geometric / Staircase / Vector
* `dplib.cdp.composition`：basic / advanced / moments accountant / scheduler / theorems
* `dplib.cdp.analytics.queries`：count / sum / mean / variance / histogram / range / query_engine
* `dplib.cdp.sensitivity`：analyzer / bounds / calibrator 等

---

### 3）CDP + ML：在 CDP 基础上启用 DP 训练与模型评估（可选扩展）

适用于：需要 DP-SGD、训练器、模型评估/隐私审计等能力。

```bash
pip install -e ".[cdp,ml]"
```

建议说明（写在 README 里，避免误解）：

* `ml` 是可选扩展，可能引入较重依赖（如 PyTorch / TensorFlow / scikit-learn 等）。
* 默认 `cdp` 不引入 ML 依赖，保持“统计分析 CDP”场景轻量且稳定。

---

### 4）LDP：客户端本地扰动 + 编码 + 服务端聚合 + 端到端应用

适用于：遥测/客户端上报等本地差分隐私工作流。

```bash
pip install -e ".[ldp]"
```

包含能力（示例）：

* `dplib.ldp.encoders`：categorical / numerical / unary / hashing / sketch / bloom_filter
* `dplib.ldp.mechanisms`：GRR / OUE / OLH / RAPPOR / continuous（以及 unary_randomizer）
* `dplib.ldp.aggregators`：frequency / mean / variance / quantile / user_level / consistency
* `dplib.ldp.applications`：heavy_hitters / range_queries / marginals / key_value / sequence_analysis

---

### 5）开发者环境（测试/格式化/类型检查/构建工具）

适用于：贡献代码、跑 CI 同款检查、本地调试。

```bash
pip install -e ".[dev]"
```

---

### 6）一键全量（推荐给 CI / Release 验收 / 完整功能体验）

适用于：一次性装齐 core + cdp + ldp + ml + docs + dev（用于 CI、发布前验证、完整功能验证）。

```bash
pip install -e ".[all]"
```

---

## 推荐组合速查

| 需求场景                    | 推荐命令                         |
| ----------------------- | ---------------------------- |
| 只用基础抽象/数据层/会计器          | `pip install -e ".[core]"`   |
| 做 CDP 机制/组合/查询分析（不训练）   | `pip install -e ".[cdp]"`    |
| 做 CDP + DP 训练（DP-SGD 等） | `pip install -e ".[cdp,ml]"` |
| 做 LDP 端到端（编码+扰动+聚合+应用）  | `pip install -e ".[ldp]"`    |
| 本地开发/跑测试/CI 同款工具        | `pip install -e ".[dev]"`    |
| 发布前/全功能/CI 验收           | `pip install -e ".[all]"`    |

---

## 快速自检（可选）

安装后可用以下方式快速验证环境就绪（示例）：

```bash
python -c "import dplib; print('dplib ok')"
python -c "from dplib.cdp.mechanisms import LaplaceMechanism; print('cdp ok')"
python -c "from dplib.ldp.mechanisms.discrete import GRRMechanism; print('ldp ok')"
# 若启用 ML
python -c "import dplib.cdp.ml; print('ml ok')"
```

---

