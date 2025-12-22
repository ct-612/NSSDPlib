
# NSSDPlib - Comprehensive Differential Privacy Library

**NSSDPlib** 是一个统一且全面的**差分隐私 (Differential Privacy, DP)** 综合库，旨在为数据分析和机器学习提供严格的隐私保证。它采用模块化且可扩展的架构，同时支持**中心化差分隐私 (CDP)** 与**本地化差分隐私 (LDP)**。

## 🚀 核心特性

*   **统一架构**：无缝集成核心隐私原语、CDP 机制与 LDP 工作流。
*   **中心化差分隐私 (CDP)**：
    *   **机制 (Mechanisms)**：Laplace, Gaussian, Geometric, Staircase, Vector, Exponential。
    *   **统计分析 (Analytics)**：查询引擎 (Count, Sum, Mean, Variance, Histogram, Range) 及隐私/效用报告。
    *   **隐私会计 (Accounting)**：强大的 `PrivacyAccountant` 与 `PrivacyBudget` 管理 (支持纯 DP 、近似 DP)。
    *   **组合 (Composition)**：基础/高级组合、矩会计、预算调度、组合定理。
*   **本地化差分隐私 (LDP)**：
    *   **机制 (Mechanisms)**：GRR, OUE, OLH, RAPPOR, Duchi, Piecewise, Local Laplace/Gaussian。
    *   **编码器 (Encoders)**：Unary, Binary, Hash, Bloom Filter, Sketch, Numerical Bucketing。
    *   **聚合器 (Aggregators)**：Frequency, Mean/Variance, Quantile, User-level, Consistency。
    *   **应用 (Applications)**：频率估计 (Frequency Estimation), 频繁项挖掘 (Heavy Hitters), 边缘分布 (Marginals), 序列分析 (Sequence Analysis)。
*   **生产级质量**：
    *   **验证**：拥有全面的基于属性的测试套件 (Property-based Testing)，确保理论正确性与数值稳定性。
    *   **类型安全**：全代码库采用静态类型标注，提升可靠性与开发体验。

## 📦 安装指南

NSSDPlib 采用可选依赖管理，以保持安装轻量化。

### 1. Core + CDP + LDP (推荐)
适用于大多数需要隐私统计分析与本地隐私应用的开发者：

```bash
pip install -e ".[core,cdp,ldp]"
```

### 2. 全量安装 (开发与机器学习)
包含机器学习 (ML) 组件及开发测试工具：

```bash
pip install -e ".[all]"
```

### 3. 最小化安装
仅包含核心抽象与数据工具：

```bash
pip install -e ".[core]"
```

### 4. 本地初始化

```bash
git clone https://github.com/ct-612/NSSDPlib.git

cd NSSDPlib

python -m venv .venv

.venv\Scripts\activate.ps1

pip install -e ".[dev,core,cdp,ldp]"

pytest -q
```

## ⚡ 快速开始

### 中心化差分隐私 (CDP)

使用拉普拉斯机制 (Laplace Mechanism) 对单个数值进行扰动：

```python
from dplib.cdp.mechanisms import LaplaceMechanism

# 初始化机制，设置隐私预算 epsilon=1.0
mech = LaplaceMechanism(epsilon=1.0)
mech.calibrate(sensitivity=1.0)

# 随机化数值
true_value = 10.0
noisy_value = mech.randomise(true_value)

print(f"真实值: {true_value}, 加噪值: {noisy_value}")
```

### 隐私会计 (Privacy Accounting)

追踪累积的隐私预算消耗：

```python
from dplib.core.privacy import PrivacyAccountant

accountant = PrivacyAccountant()

# 添加一个隐私事件: Epsilon=0.5, Delta=0
accountant.add_event(epsilon=0.5, delta=0.0, description="查询 1")

# 添加另一个事件
accountant.add_event(epsilon=0.5, delta=1e-5, description="查询 2")

print(f"总消耗: {accountant.spent()}")
```

### 本地化差分隐私 (LDP)

使用广义随机响应 (GRR) 进行频率估计的模拟示例：

```python
from dplib.ldp.applications import FrequencyEstimationApplication, FrequencyEstimationClientConfig

# 配置
categories = ["A", "B", "C"]
config = FrequencyEstimationClientConfig(
    epsilon=2.0,
    categories=categories,
    mechanism="grr"
)

app = FrequencyEstimationApplication(client_config=config)

# 1. 客户端：生成隐私报告 (Report)
client_fn = app.build_client()
report = client_fn(data="A", user_id="user_123")

# 2. 服务端：聚合统计 (Aggregate)
aggregator = app.build_aggregator()
estimate = aggregator.aggregate([report])

print("频率估计结果:", estimate.point)
```

## 🛠️ 测试与验证

NSSDPlib 使用 **基于属性的测试 (Property-based Testing)** 工具 (`hypothesis`) 进行了严格验证，确保在各种输入范围内的正确性。

运行完整测试套件：

```bash
pip install -e ".[dev]"
pytest
```

运行属性验证测试：

```bash
pytest tests/property_based
```
