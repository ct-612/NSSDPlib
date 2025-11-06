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

### 🔹 安装方式

* 只安装核心模块：

```bash
pip install .[core]
```

* 安装 CDP 模块：

```bash
pip install .[cdp]
```

* 安装 LDP 模块：

```bash
pip install .[ldp]
```

* 安装全部模块：

```bash
pip install .[all]
```

---

