
# NSSDPlib - Comprehensive Differential Privacy Library

**NSSDPlib** is a unified, comprehensive library for **Differential Privacy (DP)**, designed to provide rigorous privacy guarantees for data analysis and machine learning. It supports both **Central Differential Privacy (CDP)** and **Local Differential Privacy (LDP)** within a modular and extensible architecture.

## 🚀 Key Features

*   **Unified Architecture**: Integrates Core privacy primitives, CDP mechanisms, and LDP workflows.
*   **Central Differential Privacy (CDP)**:
    *   **Mechanisms**: Laplace, Gaussian, Geometric, Staircase, Vector, Exponential.
    *   **Analytics**: Query Engine (Count, Sum, Mean, Variance, Histogram, Range) with privacy/utility reports.
    *   **Accounting**: Robust `PrivacyAccountant` and `PrivacyBudget` management (Pure DP, Approximate DP).
    *   **Composition**: Basic/Advanced composition, Moments accountant, Budget scheduler, Composition theorems.
*   **Local Differential Privacy (LDP)**:
    *   **Mechanisms**: GRR, OUE, OLH, RAPPOR, Duchi, Piecewise, Local Laplace/Gaussian.
    *   **Encoders**: Unary, Binary, Hash, Bloom Filter, Sketch, Numerical Bucketing.
    *   **Aggregators**: Frequency, Mean/Variance, Quantile, User-level, Consistency.
    *   **Applications**: Frequency Estimation, Heavy Hitters, Marginals, Sequence Analysis.
*   **Production Ready**:
    *   **Verified**: Comprehensive property-based testing suite ensuring theoretical correctness and numerical stability.
    *   **Strict Typing**: Fully typed codebase for reliability.

## 📦 Installation

NSSDPlib uses optional dependencies to keep installations lightweight.

### 1. Core + CDP + LDP (Recommended)
For most users working with privacy statistics and local privacy applications:

```bash
pip install -e ".[core,cdp,ldp]"
```

### 2. Full Installation (Development & ML)
Includes Machine Learning components (if available) and development tools:

```bash
pip install -e ".[all]"
```

### 3. Minimal Installation
Only core abstractions and data utilities:

```bash
pip install -e ".[core]"
```

### 4. Local Development Setup

```bash
git clone https://github.com/ct-612/NSSDPlib.git

cd NSSDPlib

python -m venv .venv

.venv\Scripts\activate.ps1

pip install -e ".[dev,core,cdp,ldp]"

pytest -q
```

## ⚡ Quick Start

### Central Differential Privacy (CDP)

Applying noise to a single value using the Laplace mechanism:

```python
from dplib.cdp.mechanisms import LaplaceMechanism

# Initialize mechanism with epsilon=1.0
mech = LaplaceMechanism(epsilon=1.0)
mech.calibrate(sensitivity=1.0)

# Randomise a value
true_value = 10.0
noisy_value = mech.randomise(true_value)

print(f"True: {true_value}, Noisy: {noisy_value}")
```

### Privacy Accounting

Track cumulative privacy budget consumption:

```python
from dplib.core.privacy import PrivacyAccountant

accountant = PrivacyAccountant()

# Add an event: Epsilon=0.5, Delta=0
accountant.add_event(epsilon=0.5, delta=0.0, description="Query 1")

# Add another event
accountant.add_event(epsilon=0.5, delta=1e-5, description="Query 2")

print(f"Total Spent: {accountant.spent()}")
```

### Local Differential Privacy (LDP)

Running a Frequency Estimation simulation with Generalized Randomized Response (GRR):

```python
from dplib.ldp.applications import FrequencyEstimationApplication, FrequencyEstimationClientConfig

# Configuration
categories = ["A", "B", "C"]
config = FrequencyEstimationClientConfig(
    epsilon=2.0,
    categories=categories,
    mechanism="grr"
)

app = FrequencyEstimationApplication(client_config=config)

# 1. Client Side: Generate Report
client_fn = app.build_client()
report = client_fn(data="A", user_id="user_123")

# 2. Server Side: Aggregate
aggregator = app.build_aggregator()
estimate = aggregator.aggregate([report])

print("Estimated Frequencies:", estimate.point)
```

## 🛠️ Testing

NSSDPlib is rigorously tested using **property-based testing** (`hypothesis`) to ensure correctness across valid input ranges.

To run the full test suite:

```bash
pip install -e ".[dev]"
pytest
```

To run property-based verification:

```bash
pytest tests/property_based
```
