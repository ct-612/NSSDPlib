# NSSDPlib

统一差分隐私库。目标：
- 支持 CDP（服务端）与 LDP（客户端）模块化安装。
- 提供可扩展机制、隐私会计与测试框架。
- 支持 PyPI 分发与 CI/CD 集成。

快速开始
```bash
# 本地初始化
git clone <repo>
cd NSSDPlib
python -m venv .venv
source .venv/bin/activate   # 或 Windows: .venv\Scripts\activate
pip install -e ".[dev,cdp,ldp]"
pytest -q
```

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

