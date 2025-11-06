# **技术选型与最小环境（决策清单）**

用于定义项目的核心技术栈、依赖、CI/CD 策略与仓库结构，确保开发环境一致性与可维护性。

---

## 一、Python 版本
- **最低版本**：3.9  
- **目标兼容版本**：3.9、3.10、3.11、3.12、3.13  

  - 覆盖主流长期支持版本；
  - 兼容多数科学计算与差分隐私库（如 NumPy、SciPy、OpenDP）。

---

## 二、核心依赖库

| 库            | 最低版本    | 说明                   |
| ------------ | ------- | -------------------- |
| numpy        | ≥ 1.24  | 数值计算核心               |
| scipy        | ≥ 1.10  | 概率分布与统计函数            |
| pandas       | ≥ 2.0   | 数据处理与结构化接口           |
| tqdm         | ≥ 4.65  | 进度条与批处理日志            |
| scikit-learn | ≥ 1.2   | 模型评估与基准算法            |
| matplotlib   | ≥ 3.7   | 可视化与报告输出             |
| bitarray     | ≥ 2.5   | 位级数据表示（如 LDP 编码）     |
| xxhash       | ≥ 3.2   | 高速哈希（机制与聚合器）         |
| datasketch   | ≥ 1.5.2 | LDP/聚合近似算法支持         |
| mmh3         | ≥ 3.0.0 | MurmurHash 实现，用于哈希机制 |

---

## 三、打包与发布方案

- **构建工具**：`setuptools` + `pyproject.toml`  
- **打包格式**：`wheel (.whl)`  
- **发布平台**：`PyPI`  
- **命令示例**：
  ```bash
  python -m build
  twine upload dist/*
  ```

* **版本管理**：

  * 遵循 [Semantic Versioning 2.0.0](https://semver.org/)
  * 主分支自动更新 `__version__`

---

## 四、CI 平台与代码质量工具

| 工具                 | 功能    | 说明                      |
| ------------------ | ----- | ----------------------- |
| `GitHub Actions` | 持续集成  | 运行测试矩阵（Python 3.9~3.13） |
| `pytest-cov`       | 测试覆盖率 | 目标 ≥ 90%                |
| `flake8`           | 代码规范  | 统一编码风格                  |
| `black`            | 自动格式化 | CI 检查一致性                |
| `mypy`             | 类型安全  | 静态检查类型错误                |
| `safety`           | 安全扫描  | 检查依赖安全漏洞                |

---

## 五、仓库结构

```
NSSDPlib/                              # 统一差分隐私库
├── 📁 docs/                           # 文档模块
├── 📁 src/                            # 源码根目录
│   └── 📁 dplib/
│       ├── 📁 core/                   # 核心框架
│       │   ├── 📁 privacy/            # 隐私抽象层
│       │   ├── 📁 data/               # 数据抽象层
│       │   └── 📁 utils/              # 共享工具库
│       ├── 📁 cdp/                    # 中心化差分隐私模块
│       │   ├── 📁 mechanisms/         # CDP机制实现
│       │   ├── 📁 composition/        # CDP组合定理
│       │   ├── 📁 sensitivity/        # 敏感度分析
│       │   ├── 📁 ml/                 # 机器学习
│       │   └── 📁 analytics/          # 分析工具
│       └── 📁 ldp/                    # 本地差分隐私模块
│           ├── 📁 mechanisms/         # LDP机制实现
│           ├── 📁 encoders/           # 数据编码器
│           ├── 📁 aggregators/        # 数据聚合器
│           ├── 📁 composition/        # LDP组合定理
│           └── 📁 applications/       # LDP应用场景
├── 📁 tests/                          # 综合测试模块
├── 📁 examples/                       # 使用示例
├── 📁 benchmarks/                     # 基准测试
└── 📁 notebooks/                      # Jupyter笔记本
```

---

## 六、开发与运行环境

| 环境     | 工具                        |
| ------ | ------------------------- |
| 开发 IDE | `VS Code` / `PyCharm`        |
| 虚拟环境   | `venv` / `conda`          |
| 文档构建   | `Sphinx` + `furo`         |
| 操作系统   |  `Windows 11` |

安装开发依赖：

```bash
pip install -e .[dev]
```

---

## 七、后续扩展计划

* 集成 `ruff` 替代 `flake8`；
* 增加 `pre-commit` 钩子；
* 支持 `tox` 多版本测试；
* `Docker` 化构建环境。

---