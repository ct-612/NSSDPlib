# NSSDPlib 全流程开发作业指引（步骤级）

本指引基于 `docs/development/project_plan.md`、`requirements.md`、`architecture.md`、`tech_stack.md` 以及当前代码仓库结构（`src/dplib/*`, `tests/*`, `docs/*`）整理，旨在帮助项目负责人快速了解从立项到发布的每一个执行步骤、交付物、责任人以及现状。

## 状态图例

- **已完成**：交付物存在且达成阶段验收目标。
- **进行中**：基础工作或部分交付已存在，尚需补齐验收条件。
- **待启动**：前置条件尚未达成或工作尚未开启。

## 阶段状态概览

| 阶段 | 目标概述 | 当前状态 | 佐证 |
| ---- | -------- | -------- | ---- |
| 0 项目准备与架构设计 | 冻结需求/架构/CI 策略 | 🟡 进行中 | 需求/架构/技术栈文档已落地，但 README/贡献规范缺失 |
| 1 核心框架开发（core/） | 建立 BaseMechanism/Accountant/Data/Utils | 🟡 进行中 | `src/dplib/core/privacy/*`、`core/data/*` 已实现，`core/utils/*` 缺失 |
| 2 CDP 模块实现 | 服务端机制/组合/ML/analytics | 🟡 进行中 | 仅 `src/dplib/cdp/mechanisms/{laplace,gaussian}.py` 与 `composition/{basic,advanced}.py` 可用 |
| 3 LDP 模块实现 | 客户端机制/编码/聚合/应用 | 🟡 进行中 | 仅 `src/dplib/ldp/mechanisms/{grr,oue}.py` 存在，其他模块为空 |
| 4 模块化安装与包管理 | 拆分 core/cdp/ldp 安装与 extras | 🟡 进行中 | `pyproject.toml` 已声明 extras，但缺少构建脚本与验证 |
| 5 测试与验证 | 单元/集成/属性/性能/回归体系 | 🟡 进行中 | 仅 `tests/unit/test_core/*`、`test_cdp/*` 有实现，其余目录为空 |
| 6 文档、示例与教程 | 完整 Sphinx 文档与示例矩阵 | ⚪ 待启动 | `docs/` 仅有空的 `index.rst`/`conf.py`，无 API/示例内容 |
| 7 发布与运维 | PyPI 分发、监控、版本治理 | ⚪ 待启动 | 缺少 release pipeline、运行手册与支持策略 |

---

## 阶段 0 · 项目准备与架构设计（状态：✅ 已完成）

**阶段目标**：明确范围、架构、模块边界、技术/CI 策略与协作规范。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 0.1 | 收集业务与技术需求、建立优先级 | 访谈记录、竞品调研 | `docs/development/requirements.md` | PM/架构 | ✅ 已完成（`requirements.md` 已列出 core/CDP/LDP MVP 范围、性能阈值与非功能约束，并同步至 `project_plan.md`） |
| 0.2 | 绘制总体架构、数据流、部署拓扑 | 需求基线 | `docs/development/architecture.md` | 架构 | ✅ 已完成（`architecture.md` 已生成 core/cdp/ldp 分层及部署 Mermaid 图，覆盖数据流/依赖） |
| 0.3 | 定义技术栈、依赖矩阵、CI/CD 策略 | 架构草案 | `docs/development/tech_stack.md` | Dev Lead | ✅ 已完成（`tech_stack.md` 明确 Python 3.9~3.13、构建链路、CI 运行 `pytest/black/isort/mypy` 等） |
| 0.4 | 输出阶段性计划与流程 | 0.1~0.3 | `docs/development/project_plan.md` | PM | ✅ 已完成（`project_plan.md` 现包含 0~7 阶段里程碑、交付物与验收要点，并与本文件双向引用） |
| 0.5 | 建立协作规范（代码风格、分支、评审） | 团队约定 | README/CONTRIBUTING（待补充） | 所有人 | ⚪ 待启动（需在 README 新增贡献/分支策略段，并创建 `docs/development/contributing.rst` 统筹流程） |

**出口检查**：需求/架构/技术栈文档齐全且通过评审；后续阶段以此为输入。当前仅贡献指南待补充，可在 Stage 6 同步。

### 文件级拆解（Stage 0 · 文档资产）

- `0-D01 docs/development/requirements.md`（Owner：PM/架构｜状态：✅ 已完成）：当前版本已对 core/cdp/ldp 功能范围、性能指标（ε≤2.0、δ≤1e-5、DP-SGD ≥ OpenDP 0.9×）、平台支持和 MVP 边界逐条列出，并含追踪矩阵。
- `0-D02 docs/development/architecture.md`（Owner：架构｜状态：✅ 已完成）：包括分层架构、数据流、部署拓扑三张 Mermaid 图及文字说明，且与 `src/dplib/*` 现有模块命名保持同步。
- `0-D03 docs/development/tech_stack.md`（Owner：Dev Lead｜状态：✅ 已完成）：罗列 Python 版本矩阵、依赖管理方式（`pip install -e .[dev]`）、CI 工具链（pytest/flake8/mypy/black/isort/safety）及发布目标。
- `0-D04 docs/development/project_plan.md`（Owner：PM｜状态：✅ 已完成）：对七个阶段的交付物、责任人、验收标准做了展开，并链接 README/目录文档作为交叉验证。
- `0-D05 docs/development/directory_layout.md`（Owner：PM + Dev Lead｜状态：✅ 已完成）：除了目录树，也新增“目录状态追踪”表，记录 core/cdp/ldp/tests/docs 等目录已交付内容与待办。
- `0-D06 docs/development/api_contracts.md`（Owner：Core Team｜状态：✅ 已完成）：详细约束 BaseMechanism 接口、序列化协议、异常模型，并引用 `privacy_accountant`、data layer 的类型说明。
- `0-P01 README.md`（Owner：所有人｜状态：🟡 进行中）：已包含项目概述、核心目标与 `pip install -e .` 示例，仍需补上贡献流程、分支策略、Stage 6 教程链接及多包安装指南。
- `0-P02 docs/development/contributing.rst`（Owner：所有人｜状态：⚪ 待启动）：文件尚未创建，需整理代码风格、评审流程、Issue/PR 模板，作为 README 的延伸。

---

## 阶段 1 · 核心框架开发（core/）（状态：🟡 进行中）

**阶段目标**：实现所有模块共用的基础抽象与工具，并具备基本测试覆盖。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 1.1 | 实现 `BaseMechanism`/`PrivacyAccountant`/`Composition` 抽象及异常体系 | `api_contracts.md` | `src/dplib/core/privacy/*` | Core Team | ✅ 已完成（`base_mechanism.py`/`privacy_accountant.py`/`composition.py`/`budget_tracker.py` 已落地） |
| 1.2 | 实现数据域/敏感度抽象与验证工具 | Step 1.1 | `src/dplib/core/data/*` | Core Team | ✅ 已完成（对照 `directory_layout.md`，`domain.py`/`dataset.py`/`transformers.py`/`validation.py`/`statistics.py`/`sensitivity.py` 均已补齐并写入类型注释） |
| 1.3 | 完成 `core/utils`（math/random/config/logging/perf） | Step 1.1 | `src/dplib/core/utils/*` | Core Team | ⚪ 待启动（目录仅有空的 `__init__.py`） |
| 1.4 | 建立机制工厂与注册表 | 1.1~1.3 | `src/dplib/core/__init__.py`、工厂模块 | Core Team | ⚪ 待启动（`core/__init__.py` 为空，未导出工厂） |
| 1.5 | 覆盖核心单元测试 + 类型/格式化检查 | 代码实现 | `tests/unit/test_core/*`, CI 配置 | QA/Dev | 🟡 进行中（新增 `tests/unit/test_core/test_data_layer.py`，覆盖 Domain/Dataset/Transformers/Validation/Sensitivity，但 `core/utils/*` 仍缺 UT） |
| 1.6 | 生成核心 API 文档草稿 | 1.1~1.4 | `docs/api/core.rst`（待补充） | Tech Writer | ⚪ 待启动（`docs/api/core.rst` 未创建） |

**出口检查**：`core/` UT 覆盖 ≥80%，wheel <5MB，API 契约一致。当前需补齐数据/工具文档与覆盖率报告。

### 文件级拆解（Stage 1 · core/）

**privacy 子模块**

- `1P-01 src/dplib/core/privacy/__init__.py`（Owner：Core Team｜状态：🟡 进行中）：仅导出部分类，仍需补充 `privacy_model`/`privacy_guarantee` 等符号并完善文档。
- `1P-02 src/dplib/core/privacy/base_mechanism.py`（Owner：Core Team｜状态：✅ 已完成）：定义 `BaseMechanism.run/release` 流程、异常类型与上下文校验，保证实现遵循 `api_contracts.md`。
- `1P-03 src/dplib/core/privacy/privacy_accountant.py`（Owner：Core Team｜状态：✅ 已完成）：提供通用会计器抽象、可插拔预算模型以及与 `composition.py` 的集成钩子。
- `1P-04 src/dplib/core/privacy/composition.py`（Owner：Core Team｜状态：✅ 已完成）：实现顺序/高级组合规则与验证逻辑，暴露给 CDP/LDP 模块复用。
- `1P-05 src/dplib/core/privacy/privacy_model.py`（Owner：Core Team｜状态：⚪ 待启动）：文件尚未创建，需定义 CDP/LDP/自定义模型的枚举与语义描述。
- `1P-06 src/dplib/core/privacy/budget_tracker.py`（Owner：Core Team｜状态：✅ 已完成）：实现预算账本持久化、线程安全扣减与 Stage 7 运行期度量输出。
- `1P-07 src/dplib/core/privacy/privacy_guarantee.py`（Owner：Core Team｜状态：⚪ 待启动）：文件尚未创建，需定义差分隐私保证结构与报告格式。

**data 子模块**

- `1D-01 src/dplib/core/data/__init__.py`（Owner：Core Team｜状态：✅ 已完成）：已按照 `directory_layout.md` 导出 Domain/Dataset/Transformers/Validation/Statistics/Sensitivity 全部入口，并补充 `__all__`。
- `1D-02 src/dplib/core/data/domain.py`（Owner：Core Team｜状态：✅ 已完成）：实现离散/连续/桶化 Domain 抽象与描述器，支撑 schema 校验与 LDP 编码需求。
- `1D-03 src/dplib/core/data/dataset.py`（Owner：Core Team｜状态：✅ 已完成）：支持数据加载、缓存、批处理、列裁剪与切分策略，并在 `tests/unit/test_core/test_data_layer.py` 进行覆盖。
- `1D-04 src/dplib/core/data/transformers.py`（Owner：Core Team｜状态：✅ 已完成）：提供裁剪、归一化、离散化（`DiscretizerTransformer`）、独热编码与流水线执行。
- `1D-05 src/dplib/core/data/validation.py`（Owner：Core Team｜状态：✅ 已完成）：提供 Schema/Field/Validator 及缺失检测工具，后续与 `core/utils/validation.py` 集成即可复用。
- `1D-06 src/dplib/core/data/statistics.py`（Owner：Core Team｜状态：✅ 已完成）：实现 count/sum/mean/variance/histogram 与 `RunningStats`，满足 Stage 2/3 校准需求。
- `1D-07 src/dplib/core/data/sensitivity.py`（Owner：Core Team｜状态：✅ 已完成）：提供 count/sum/mean 的全局/局部/平滑敏感度计算与 `SmoothSensitivityEstimate`。

**utils 子模块**

- `1U-01 src/dplib/core/utils/__init__.py`（Owner：Core Team｜状态：⚪ 待启动）：当前仅有空壳，尚未导出任何工具函数。
- `1U-02 src/dplib/core/utils/math_utils.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要实现 softmax/logsumexp 等函数及测试。
- `1U-03 src/dplib/core/utils/random.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要统一 `numpy.random.Generator` 管理。
- `1U-04 src/dplib/core/utils/config.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要提供配置解析/覆盖机制。
- `1U-05 src/dplib/core/utils/serialization.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要实现 JSON/MsgPack/Protobuf helper。
- `1U-06 src/dplib/core/utils/logging.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要建立统一日志格式。
- `1U-07 src/dplib/core/utils/validation.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要沉淀通用参数断言。
- `1U-08 src/dplib/core/utils/performance.py`（Owner：Core Team｜状态：⚪ 待启动）：文件未创建，需要封装性能/内存度量工具。

**核心聚合/导出**

- `1C-01 src/dplib/core/__init__.py`（Owner：Core Team｜状态：⚪ 待启动）：文件当前为空，需要注册机制工厂、Accountant 实现与默认配置供 `dplib` 顶层使用。

**核心单元测试**

- `1T-01 tests/unit/test_core/__init__.py`（Owner：QA｜状态：🟡 进行中）：仅作为占位符，尚未沉淀共享 fixture。
- `1T-02 tests/unit/test_core/test_base_mechanism.py`（Owner：QA｜状态：✅ 已完成）：覆盖参数验证、随机性、release 输出。
- `1T-03 tests/unit/test_core/test_privacy_accountant.py`（Owner：QA｜状态：✅ 已完成）：验证预算扣减、组合与多模型兼容。
- `1T-04 tests/unit/test_core/test_composition.py`（Owner：QA｜状态：✅ 已完成）：覆盖顺序/高级组合公式及异常路径。
- `1T-05 tests/unit/test_core/test_budget_tracker.py`（Owner：QA｜状态：✅ 已完成）：验证 `BudgetTracker`/`TrackedScope` 生命周期、告警阈值与序列化，补充 `privacy_accountant` 以外的预算场景。
- `1T-06 tests/unit/test_core/test_domain.py`（Owner：QA｜状态：✅ 已完成）：覆盖 `DiscreteDomain/ContinuousDomain/BucketizedDomain` 的 encode/decode、clamp 与越界异常，取代旧 `test_data_layer.py` 中的混合断言。
- `1T-07 tests/unit/test_core/test_dataset.py`（Owner：QA｜状态：✅ 已完成）：验证 Dataset 的加载、批处理、map/select/split 及列式构造，补齐惰性加载与长度检查。
- `1T-08 tests/unit/test_core/test_transformers.py`（Owner：QA｜状态：✅ 已完成）：单测 Clipping/Normalization/DiscretizerTransformer/OneHot/Pipeline 的 fit-transform 顺序与异常处理。
- `1T-09 tests/unit/test_core/test_validation.py`（Owner：QA｜状态：✅ 已完成）：针对 SchemaValidator 的 RAISE/DROP/IMPUTE 策略与 `detect_missing` 统计提供覆盖。
- `1T-10 tests/unit/test_core/test_statistics.py`（Owner：QA｜状态：✅ 已完成）：验证 count/summation/mean/variance/histogram/RunningStats 的数值稳定性。
- `1T-11 tests/unit/test_core/test_sensitivity.py`（Owner：QA｜状态：✅ 已完成）：覆盖 count/sum/mean 全局/局部/平滑敏感度的主要场景与异常路径。

**核心 API 文档**

- `1A-01 docs/api/core.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：为 BaseMechanism/Data/Utils 输出 API 参考、示例代码，并链接 `directory_layout.md` 的对应文件。

---

## 阶段 2 · CDP 模块实现（服务器端）（状态：🟡 进行中）

**阶段目标**：完成服务端差分隐私机制、组合、敏感度、ML 支持及分析工具。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 2.1 | 实现拉普拉斯/高斯/指数/几何/阶梯/向量机制及注册 | Stage 1 | `src/dplib/cdp/mechanisms/*` | CDP Team | 🟡 进行中（仅 Laplace/Gaussian 上线，其余机制/工厂缺失） |
| 2.2 | 实现基本/高级组合与 Moments Accountant | Stage 1 | `src/dplib/cdp/composition/*` | CDP Team | 🟡 进行中（`basic.py`/`advanced.py` 已完成，Accountant/调度仍缺） |
| 2.3 | 敏感度分析与噪声校准工具 | Stage 1 | `src/dplib/cdp/sensitivity/*` | CDP Team | ⚪ 待启动（目录仅空壳） |
| 2.4 | DP-SGD 等 ML 管线与示例 | Stage 1 | `src/dplib/cdp/ml/*`, `examples/cdp/*` | ML Subteam | ⚪ 待启动（`ml/` 仅留空 `__init__.py`，示例缺失） |
| 2.5 | CDP Analytics：查询 API、报告、基准脚本 | 2.1~2.4 | `src/dplib/cdp/analytics/*`, `benchmarks/performance/*` | Analytics | 🟡 进行中（仅 `queries/{count,mean,sum}.py`，其余模块缺失） |
| 2.6 | 单元/集成/性能测试与文档 | 2.1~2.5 | `tests/unit/test_cdp/*`, `docs/api/cdp.rst` | QA/Tech Writer | 🟡 进行中（仅 Laplace/Gaussian 有 UT，API 文档缺失） |

**出口检查**：噪声 <1ms、DP-SGD ≥OpenDP 0.9×、测试覆盖 ≥85%。当前 analytics/benchmarks/文档仍在补齐，性能验证未记录。

### 文件级拆解（Stage 2 · cdp/）

**mechanisms**

- `2M-01 src/dplib/cdp/mechanisms/__init__.py`（Owner：CDP Team｜状态：🟡 进行中）：当前仅导出 Laplace/Gaussian，后续需补齐其余机制并接入工厂。
- `2M-02 src/dplib/cdp/mechanisms/laplace.py`（Owner：CDP Team｜状态：✅ 已完成）：实现拉普拉斯噪声生成、尺度校准与文档示例。
- `2M-03 src/dplib/cdp/mechanisms/gaussian.py`（Owner：CDP Team｜状态：✅ 已完成）：实现高斯机制、δ-approx 支持以及 `privacy_guarantee` 输出。
- `2M-04 src/dplib/cdp/mechanisms/exponential.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需实现评分函数/归一化逻辑。
- `2M-05 src/dplib/cdp/mechanisms/geometric.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需提供整数域噪声实现。
- `2M-06 src/dplib/cdp/mechanisms/staircase.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需实现阶梯化机制。
- `2M-07 src/dplib/cdp/mechanisms/vector_mechanism.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需支持向量化噪声。
- `2M-08 src/dplib/cdp/mechanisms/mechanism_factory.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需提供名称到类的构建工厂。
- `2M-09 src/dplib/cdp/mechanisms/mechanism_registry.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需维护注册表与版本信息。

**composition**

- `2C-01 src/dplib/cdp/composition/__init__.py`（Owner：CDP Team｜状态：🟡 进行中）：聚合基本/高级组合入口，仅导出已实现的模块。
- `2C-02 src/dplib/cdp/composition/basic.py`（Owner：CDP Team｜状态：✅ 已完成）：实现基本组合定理、误差上界计算。
- `2C-03 src/dplib/cdp/composition/advanced.py`（Owner：CDP Team｜状态：✅ 已完成）：实现高级组合/Moments Accountant 核心逻辑。
- `2C-04 src/dplib/cdp/composition/privacy_accountant.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需封装 CDP 会计器实现。
- `2C-05 src/dplib/cdp/composition/budget_scheduler.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需提供多查询预算分配策略。
- `2C-06 src/dplib/cdp/composition/composition_theorems.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需沉淀组合定理证明/测试向量。

**sensitivity**

- `2S-01 src/dplib/cdp/sensitivity/__init__.py`（Owner：CDP Team｜状态：⚪ 待启动）：当前为空壳，尚未导出任何敏感度接口。
- `2S-02 src/dplib/cdp/sensitivity/analyzer.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需生成局部/全局敏感度报告。
- `2S-03 src/dplib/cdp/sensitivity/calibrator.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需实现噪声标定逻辑。
- `2S-04 src/dplib/cdp/sensitivity/bounds.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需维护敏感度上下界 helper。
- `2S-05 src/dplib/cdp/sensitivity/global_sensitivity.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建，需提供全局敏感度预计算。

**ml/models、training、evaluation**

- `2L-01 src/dplib/cdp/ml/models/__init__.py`（Owner：ML Subteam｜状态：⚪ 待启动）：当前为空壳，未导出任何模型。
- `2L-02 src/dplib/cdp/ml/models/linear.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需实现 DP 线性模型。
- `2L-03 src/dplib/cdp/ml/models/neural_network.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需提供 DP NN 噪声策略。
- `2L-04 src/dplib/cdp/ml/models/tree_model.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需实现 DP-GBDT/随机森林。
- `2L-05 src/dplib/cdp/ml/models/clustering.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需实现 DP-KMeans。
- `2L-06 src/dplib/cdp/ml/models/model_factory.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需注册模型类型。
- `2T-01 src/dplib/cdp/ml/training/__init__.py`（Owner：ML Subteam｜状态：⚪ 待启动）：仅空文件，未导出训练算法。
- `2T-02 src/dplib/cdp/ml/training/dp_sgd.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建，需实现 DP-SGD 主循环。
- `2T-03 src/dplib/cdp/ml/training/objective_perturbation.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2T-04 src/dplib/cdp/ml/training/output_perturbation.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2T-05 src/dplib/cdp/ml/training/trainer.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2T-06 src/dplib/cdp/ml/training/gradient_clipping.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2E-01 src/dplib/cdp/ml/evaluation/__init__.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2E-02 src/dplib/cdp/ml/evaluation/metrics.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2E-03 src/dplib/cdp/ml/evaluation/validator.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2E-04 src/dplib/cdp/ml/evaluation/privacy_audit.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。

**analytics**

- `2A-01 src/dplib/cdp/analytics/__init__.py`（Owner：Analytics｜状态：🟡 进行中）：导出 queries 子模块，synthetic/reporting 仍缺。
- `2A-02 src/dplib/cdp/analytics/queries/__init__.py`（Owner：Analytics｜状态：🟡 进行中）：注册已完成的查询 API。
- `2A-03 src/dplib/cdp/analytics/queries/count.py`（Owner：Analytics｜状态：✅ 已完成）：实现计数查询与噪声注入。
- `2A-04 src/dplib/cdp/analytics/queries/sum.py`（Owner：Analytics｜状态：✅ 已完成）：实现求和查询。
- `2A-05 src/dplib/cdp/analytics/queries/mean.py`（Owner：Analytics｜状态：✅ 已完成）：实现均值查询。
- `2A-06 src/dplib/cdp/analytics/queries/variance.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2A-07 src/dplib/cdp/analytics/queries/histogram.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2A-08 src/dplib/cdp/analytics/queries/range_query.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2A-09 src/dplib/cdp/analytics/queries/query_engine.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2A-10 src/dplib/cdp/analytics/synthetic_data/__init__.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-11 src/dplib/cdp/analytics/synthetic_data/generator.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-12 src/dplib/cdp/analytics/synthetic_data/methods/__init__.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-13 src/dplib/cdp/analytics/synthetic_data/methods/marginal.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-14 src/dplib/cdp/analytics/synthetic_data/methods/bayesian.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-15 src/dplib/cdp/analytics/synthetic_data/methods/gan.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-16 src/dplib/cdp/analytics/synthetic_data/methods/copula.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-17 src/dplib/cdp/analytics/reporting/__init__.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-18 src/dplib/cdp/analytics/reporting/privacy_report.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。
- `2A-19 src/dplib/cdp/analytics/reporting/utility_report.py`（Owner：Analytics｜状态：⚪ 待启动）：目录尚未创建。

**模块入口与示例**

- `2I-01 src/dplib/cdp/__init__.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件为空，尚未导出已实现模块。
- `2X-01 examples/cdp_examples/__init__.py`（Owner：CDP Team｜状态：⚪ 待启动）：目录尚未创建，需提供示例入口。
- `2X-02 examples/cdp_examples/cdp_mechanisms.py`（Owner：CDP Team｜状态：⚪ 待启动）：文件未创建。
- `2X-03 examples/cdp_examples/cdp_ml_training.py`（Owner：ML Subteam｜状态：⚪ 待启动）：文件未创建。
- `2X-04 examples/cdp_examples/cdp_data_analysis.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2X-05 examples/cdp_examples/cdp_synthetic_data.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2D-01 docs/api/cdp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建，需补充模块/API 说明。

**性能基准**

- `2B-01 benchmarks/performance/__init__.py`（Owner：Analytics｜状态：🟡 进行中）：仅有空占位，待补充共享配置。
- `2B-02 benchmarks/performance/benchmark_mechanisms.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2B-03 benchmarks/performance/benchmark_composition.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。
- `2B-04 benchmarks/performance/benchmark_ml.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建。

> 注：`tests/unit/test_cdp/*` 的文件级拆解详见 Stage 5，以保证测试体系集中管理。

---

## 阶段 3 · LDP 模块实现（客户端）（状态：🟡 进行中）

**阶段目标**：为客户端提供轻量机制、编码、聚合与示例，保证包体积和性能。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 3.1 | 实现 GRR/OUE/OLH/RAPPOR/连续值机制 | Stage 1 | `src/dplib/ldp/mechanisms/*` | LDP Team | 🟡 进行中（仅 GRR/OUE 实现，其余机制缺失） |
| 3.2 | 编码器（分类/数值/哈希/Sketch/BF）及元数据输出 | 3.1 | `src/dplib/ldp/encoders/*` | LDP Team | ⚪ 待启动（目录仅空 `__init__.py`） |
| 3.3 | 聚合器（频率/均值/方差/分位数） | 3.1 | `src/dplib/ldp/aggregators/*` | LDP Team | ⚪ 待启动（无实现文件） |
| 3.4 | 典型应用（heavy hitters、range query 等） | 3.2~3.3 | `src/dplib/ldp/applications/*`, `examples/ldp/*` | LDP Team | ⚪ 待启动（应用与示例目录为空） |
| 3.5 | 轻量序列化/网络接口（JSON/Protobuf） | 3.1~3.4 | 序列化模块（待建） | LDP Team | ⚪ 待启动 |
| 3.6 | 客户端基准与准确性评估 | 3.1~3.4 | `benchmarks/performance/ldp_*` | QA | ⚪ 待启动（无基准脚本） |
| 3.7 | 文档与教程（客户端视角） | 3.1~3.5 | `docs/api/ldp.rst`, `notebooks/tutorials/*` | Tech Writer | ⚪ 待启动（文件未创建） |

**出口检查**：`dplib-ldp` <10MB，1000 用户聚合 <2s，端到端示例可跑通。当前缺乏序列化层、基准测试与教程验证。

### 文件级拆解（Stage 3 · ldp/）

**mechanisms**

- `3M-01 src/dplib/ldp/mechanisms/__init__.py`（Owner：LDP Team｜状态：🟡 进行中）：仅导出 GRR/OUE，其他机制尚未挂载。
- `3M-02 src/dplib/ldp/mechanisms/grr.py`（Owner：LDP Team｜状态：✅ 已完成）：实现广义随机响应（GRR）。
- `3M-03 src/dplib/ldp/mechanisms/oue.py`（Owner：LDP Team｜状态：✅ 已完成）：实现优雅一次编码（OUE）。
- `3M-04 src/dplib/ldp/mechanisms/olh.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3M-05 src/dplib/ldp/mechanisms/rappor.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3M-06 src/dplib/ldp/mechanisms/unary_encoding.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3M-07 src/dplib/ldp/mechanisms/direct_encoding.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3M-08 src/dplib/ldp/mechanisms/continuous/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录尚未创建。
- `3M-09 src/dplib/ldp/mechanisms/continuous/laplace.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录尚未创建。
- `3M-10 src/dplib/ldp/mechanisms/continuous/gaussian.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录尚未创建。
- `3M-11 src/dplib/ldp/mechanisms/continuous/piecewise.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录尚未创建。
- `3M-12 src/dplib/ldp/mechanisms/continuous/duchi.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录尚未创建。
- `3M-13 src/dplib/ldp/mechanisms/mechanism_factory.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3M-14 src/dplib/ldp/mechanisms/mechanism_registry.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。

**encoders**

- `3E-01 src/dplib/ldp/encoders/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：仅有空文件，尚未导出接口。
- `3E-02 src/dplib/ldp/encoders/base.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-03 src/dplib/ldp/encoders/categorical.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-04 src/dplib/ldp/encoders/numerical.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-05 src/dplib/ldp/encoders/hashing.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-06 src/dplib/ldp/encoders/sketch.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-07 src/dplib/ldp/encoders/bloom_filter.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3E-08 src/dplib/ldp/encoders/encoder_factory.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。

**aggregators**

- `3A-01 src/dplib/ldp/aggregators/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：仅空文件，尚未导出接口。
- `3A-02 src/dplib/ldp/aggregators/frequency.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-03 src/dplib/ldp/aggregators/mean.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-04 src/dplib/ldp/aggregators/variance.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-05 src/dplib/ldp/aggregators/quantile.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-06 src/dplib/ldp/aggregators/user_aggregate.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-07 src/dplib/ldp/aggregators/consistency.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3A-08 src/dplib/ldp/aggregators/aggregator_factory.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。

**composition**

- `3C-01 src/dplib/ldp/composition/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：仅空文件，尚未导出接口。
- `3C-02 src/dplib/ldp/composition/basic.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3C-03 src/dplib/ldp/composition/sequential.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3C-04 src/dplib/ldp/composition/parallel.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3C-05 src/dplib/ldp/composition/privacy_accountant.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。

**applications**

- `3P-01 src/dplib/ldp/applications/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：仅空文件，尚未导出接口。
- `3P-02 src/dplib/ldp/applications/heavy_hitters.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3P-03 src/dplib/ldp/applications/range_queries.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3P-04 src/dplib/ldp/applications/marginals.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3P-05 src/dplib/ldp/applications/key_value.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3P-06 src/dplib/ldp/applications/sequence_analysis.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3P-07 src/dplib/ldp/applications/application_factory.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。

**模块入口与示例**

- `3I-01 src/dplib/ldp/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件为空，未导出任何组件。
- `3X-01 examples/ldp_examples/__init__.py`（Owner：LDP Team｜状态：⚪ 待启动）：目录未创建。
- `3X-02 examples/ldp_examples/ldp_frequency_estimation.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3X-03 examples/ldp_examples/ldp_mean_estimation.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3X-04 examples/ldp_examples/ldp_heavy_hitters.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3X-05 examples/ldp_examples/ldp_applications.py`（Owner：LDP Team｜状态：⚪ 待启动）：文件未创建。
- `3D-01 docs/api/ldp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建。

**性能基准**

- `3B-01 benchmarks/performance/benchmark_ldp.py`（Owner：Analytics｜状态：⚪ 待启动）：文件未创建，需实现 LDP 端性能基准脚本。

> 注：`tests/unit/test_ldp/*` 的文件级拆解详见 Stage 5。

---

## 阶段 4 · 模块化安装与包管理（状态：🟡 进行中）

**阶段目标**：拆分 `dplib-core`/`dplib-cdp`/`dplib-ldp`，提供 extras/executable 构建与安装指南。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 4.1 | 设计包拆分方案与依赖拓扑 | Stage 0~3 | 包拆分 RFC | Dev Lead | 🟡 进行中（extras 结构已体现在 `pyproject.toml`/`setup.cfg`） |
| 4.2 | 更新 `pyproject.toml`/`setup.cfg`（多 wheel + extras） | 4.1 | 配置文件/构建脚本 | Build Engineer | 🟡 进行中（核心依赖已配置，仍缺构建/验证脚本） |
| 4.3 | 配置 `python -m build` 与 `twine` 流程 | 4.2 | `build/` 脚本、CI job | Build Engineer | ⚪ 待启动 |
| 4.4 | 安装矩阵验证（core-only、cdp、ldp、dev/docs） | 4.2 | 测试矩阵报告 | QA | ⚪ 待启动 |
| 4.5 | 更新安装文档/FAQ | 4.2~4.4 | `docs/installation.rst`, README | Tech Writer | ⚪ 待启动 |

**出口检查**：多 wheel 构建通过、依赖拓扑清晰、安装文档落地。需等 Stage 3 基础稳定后启动。

### 文件级拆解（Stage 4 · packaging）

- `4B-01 pyproject.toml`（Owner：Build Engineer｜状态：🟡 进行中）：已声明 `dplib-core/cdp/ldp/all` extras 与构建后端，需补充版本管理与自动化校验。
- `4B-02 setup.cfg`（Owner：Build Engineer｜状态：🟡 进行中）：已包含 metadata、extras、pytest 配置，仍需完善 entry points/发布信息。
- `4B-03 MANIFEST.in`（Owner：Build Engineer｜状态：🟡 进行中）：已覆盖 README/LICENSE/docs/examples/notebooks/tests，后续需压测体积并接入 CI。
- `4B-04 LICENSE`（Owner：Dev Lead｜状态：✅ 已完成）：MIT 许可文件存在并随包分发。
- `4B-05 src/dplib/__init__.py`（Owner：Dev Lead｜状态：🟡 进行中）：仅导出 `__all__`，尚未包含版本号与便捷导出。
- `4B-06 README.md`（Owner：Dev Lead｜状态：🟡 进行中）：在封装阶段补充安装矩阵、extras 示例，匹配 PyPI 展示。
- `4B-07 docs/installation.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：提供 pip/conda/源码安装指引，并覆盖 extras 组合。
- `4B-08 docs/quickstart.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：更新 quickstart，区分 core/CDP/LDP 独立安装与验证。
- `4B-09 Makefile`（Owner：Build Engineer｜状态：⚪ 待启动）：新增 `make wheel`, `make release` 等目标，串联 Stage 4/7 pipeline。
- `4B-10 requirements-docs.txt`（Owner：Tech Writer｜状态：⚪ 待启动）：定义文档构建依赖，供 Stage 6/4 联合验证。

---

## 阶段 5 · 测试与验证（状态：🟡 进行中）

**阶段目标**：建立完整的 UT/集成/属性/性能/回归体系并集成 CI。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 5.1 | 规划测试层级与目录 | Stage 0~3 | `tests/unit`, `tests/integration`, `tests/property_based`, `tests/performance`, `tests/accuracy`, `tests/regression`, `tests/fixtures` | QA | ✅ 已完成（tests/unit/test_core/*、test_cdp/*、test_ldp/* 等目录及 `conftest.py` 已建成，可直接落地后续用例） |
| 5.2 | 实现 core/cdp/ldp 单元测试并收集覆盖率 | Stage 1~3 | `tests/unit/*`, 覆盖率报告 | QA | 🟡 进行中（core & Laplace/Gaussian/GRR/OUE 有 UT，其余缺失） |
| 5.3 | 构建 LDP→CDP 端到端集成测试 | Stage 2~3 | `tests/integration/*` | QA | ⚪ 待启动（目录为空） |
| 5.4 | 属性测试（ε/δ 边界）与 `hypothesis` 库整合 | Stage 1~3 | `tests/property_based/*` | QA | ⚪ 待启动（无实现） |
| 5.5 | 性能 & 基准测试流水线（nightly） | Stage 2~3 | `tests/performance/*`, `benchmarks/*` | QA/DevOps | ⚪ 待启动（无脚本） |
| 5.6 | 回归测试与基线数据维护 | 2~3 | `tests/regression/*`, 基线工件 | QA | ⚪ 待启动（目录未落地） |
| 5.7 | CI 集成（GitHub Actions matrix + 报告上传） | 5.2~5.6 | `.github/workflows/*` | DevOps | 🟡 进行中（`ci.yml` 存在，缺覆盖率/benchmark 上传） |

**出口检查**：语句覆盖率 ≥90%，核心模块 ≥95%，属性/性能测试达标并自动化执行。尚需补齐覆盖率统计与性能流水线。

### 文件级拆解（Stage 5 · 测试与验证）

**单元测试 / core（Owner：QA｜状态：🟡 进行中）**

- `5U-01 tests/unit/test_core/__init__.py`（Owner：QA｜状态：🟡 进行中）：当前仅注册路径，需补充 `pytest` fixture（如 mock rng、domain 样例）供其余测试共享。
- `5U-02 tests/unit/test_core/test_base_mechanism.py`（Owner：QA｜状态：✅ 已完成）：覆盖 epsilon/delta/sensitivity 校验、`calibrate/require_calibrated` 生命周期以及 `_coerce_numeric`，确保所有机制可复用统一基类。
- `5U-03 tests/unit/test_core/test_privacy_accountant.py`（Owner：QA｜状态：✅ 已完成）：验证预算核减、剩余额度计算、`BudgetExceededError` 抛出及快照序列化。
- `5U-04 tests/unit/test_core/test_budget_tracker.py`（Owner：QA｜状态：✅ 已完成）：聚焦 `BudgetTracker`/`TrackedScope` 的阈值告警、嵌套范围与持久化行为，与 Accountant 测试互补。
- `5U-05 tests/unit/test_core/test_composition.py`（Owner：QA｜状态：✅ 已完成）：验证顺序/高级组合的 epsilon/delta 聚合以及异常路径，保证结果与 `PrivacyEvent` 规范一致。
- `5U-06 tests/unit/test_core/test_domain.py`（Owner：QA｜状态：✅ 已完成）：已拆出独立文件验证离散/连续/桶化域的 encode-decode、clamp 与非法输入。
- `5U-07 tests/unit/test_core/test_dataset.py`（Owner：QA｜状态：✅ 已完成）：覆盖 Dataset 的批处理、map/select、split 以及 from_records/from_arrays 异常路径。
- `5U-08 tests/unit/test_core/test_transformers.py`（Owner：QA｜状态：✅ 已完成）：验证 Clipping、Normalization、DiscretizerTransformer、OneHotEncoder 及流水线顺序执行。
- `5U-09 tests/unit/test_core/test_validation.py`（Owner：QA｜状态：✅ 已完成）：对 SchemaValidator 的 RAISE/DROP/IMPUTE、imputer hook 与 `detect_missing` 进行断言。
- `5U-10 tests/unit/test_core/test_statistics.py`（Owner：QA｜状态：✅ 已完成）：新增 count/summation/mean/variance/histogram 与 RunningStats 的数值正确性测试。
- `5U-11 tests/unit/test_core/test_sensitivity.py`（Owner：QA｜状态：✅ 已完成）：新增 count/sum/mean 全局/局部/平滑敏感度以及异常处理的单测。

**单元测试 / cdp（Owner：QA｜状态：🟡 进行中）**

- `5C-01 tests/unit/test_cdp/__init__.py`（Owner：QA｜状态：🟡 进行中）：仅注册包路径，需补充公共 fixture 与 helper，避免在单个文件重复构造机制。
- `5C-02 tests/unit/test_cdp/test_mechanisms/__init__.py`（Owner：QA｜状态：🟡 进行中）：仅导出 Laplace/Gaussian，用于收拢 `pytest` markers；待新增其余机制的共享工厂。
- `5C-03 tests/unit/test_cdp/test_mechanisms/test_laplace.py`（Owner：QA｜状态：✅ 已完成）：验证噪声尺度 `sensitivity/epsilon`、标量与向量输入、`release` 序列化，覆盖 calibrate→randomise 全链路。
- `5C-04 tests/unit/test_cdp/test_mechanisms/test_gaussian.py`（Owner：QA｜状态：✅ 已完成）：校验 δ>0 场景、`privacy_guarantee` 输出、形状保持与异常抛出。
- `5C-05 tests/unit/test_cdp/test_mechanisms/test_exponential.py`（Owner：QA｜状态：⚪ 待启动）：待实现评分函数 mock、归一化常数验证与 argmax 稳定性测试。
- `5C-06 tests/unit/test_cdp/test_mechanisms/test_geometric.py`（Owner：QA｜状态：⚪ 待启动）：需补整数域噪声的正负采样、PMF 正规化与 0-敏感度边界用例。
- `5C-07 tests/unit/test_cdp/test_composition/__init__.py`（Owner：QA｜状态：⚪ 待启动）：计划封装 PrivacyEvent fixture 及通用断言，避免 basic/advanced 重复。
- `5C-08 tests/unit/test_cdp/test_composition/test_basic.py`（Owner：QA｜状态：✅ 已完成）：验证顺序/并行组合的 epsilon/delta 聚合、输入归一化与异常信息。
- `5C-09 tests/unit/test_cdp/test_composition/test_advanced.py`（Owner：QA｜状态：✅ 已完成）：覆盖高阶组合（Moments Accountant）与容差 slack，确保与 `PrivacyAccountant` 输出一致。
- `5C-10 tests/unit/test_cdp/test_composition/test_moment_accounting.py`（Owner：QA｜状态：⚪ 待启动）：需要针对 moment accountant/预算调度实现专项用例，一旦 `composition/privacy_accountant` 扩展完成即补测。
- `5C-11 tests/unit/test_cdp/test_ml/__init__.py`（Owner：QA｜状态：⚪ 待启动）：待随 DP-SGD 管线一同创建，收敛判定逻辑需预留。
- `5C-12 tests/unit/test_cdp/test_ml/test_dp_sgd.py`（Owner：QA｜状态：⚪ 待启动）：DP-SGD 尚未落地，需构造 toy dataset、RNG 固定与梯度裁剪断言。
- `5C-13 tests/unit/test_cdp/test_ml/test_linear_models.py`（Owner：QA｜状态：⚪ 待启动）：随线性模型实现补测，验证带噪梯度与指标记录。
- `5C-14 tests/unit/test_cdp/test_ml/test_neural_networks.py`（Owner：QA｜状态：⚪ 待启动）：需针对 MLP/Conv 简化模型验证 DP 训练流程。
- `5C-15 tests/unit/test_cdp/test_ml/test_model_evaluation.py`（Owner：QA｜状态：⚪ 待启动）：计划落地 DP 模型评估、隐私审计报告的测试。
- `5C-16 tests/unit/test_cdp/test_analytics/__init__.py`（Owner：QA｜状态：⚪ 待启动）：需在 analytics query 扩展后提供公共夹具。
- `5C-17 tests/unit/test_cdp/test_analytics/test_queries.py`（Owner：QA｜状态：✅ 已完成）：验证 `PrivateSumQuery`/`PrivateCountQuery`/`PrivateMeanQuery` 的裁剪、预算拆分、最小计数阈值以及异常信息。
- `5C-18 tests/unit/test_cdp/test_analytics/test_synthetic_data.py`（Owner：QA｜状态：⚪ 待启动）：等待 synthetic data 生成器落地，需覆盖采样稳定性与预算消费记录。
- `5C-19 tests/unit/test_cdp/test_analytics/test_reporting.py`（Owner：QA｜状态：⚪ 待启动）：计划在报告模块上线后验证指标拼装与展示。

**单元测试 / ldp（Owner：QA｜状态：🟡 进行中）**

- `5L-01 tests/unit/test_ldp/__init__.py`（Owner：QA｜状态：🟡 进行中）：目前仅注册包路径，后续需补充客户端侧的公共 fixture（如伪造遥测数据）。
- `5L-02 tests/unit/test_ldp/test_mechanisms/__init__.py`（Owner：QA｜状态：🟡 进行中）：仅导入现有机制，待 OLH/RAPPOR/连续机制补全后扩展导出。
- `5L-03 tests/unit/test_ldp/test_mechanisms/test_grr.py`（Owner：QA｜状态：✅ 已完成）：验证 GRR 在不同类别数量、ε 下的概率归一化、KL 约束与 `to_dict` 序列化。
- `5L-04 tests/unit/test_ldp/test_mechanisms/test_oue.py`（Owner：QA｜状态：✅ 已完成）：覆盖 OUE 参数校验、采样 bit-vector 的期望概率、以及批量输入的稳定性。
- `5L-05 tests/unit/test_ldp/test_mechanisms/test_olh.py`（Owner：QA｜状态：⚪ 待启动）：需在 OLH 实现后补充哈希族选择、稀疏向量合成与容错测试。
- `5L-06 tests/unit/test_ldp/test_mechanisms/test_rappor.py`（Owner：QA｜状态：⚪ 待启动）：待实现 Bloom 与噪声注入逻辑后，补足编码/解码用例。
- `5L-07 tests/unit/test_ldp/test_mechanisms/test_continuous.py`（Owner：QA｜状态：⚪ 待启动）：连续值机制实现后需覆盖裁剪、pdf/采样验证。
- `5L-08 tests/unit/test_ldp/test_encoders/__init__.py`（Owner：QA｜状态：⚪ 待启动）：将来封装 categorical/numerical 编码器的公共 fixture。
- `5L-09 tests/unit/test_ldp/test_encoders/test_categorical.py`（Owner：QA｜状态：⚪ 待启动）：实现后需验证 one-hot / bucket encoder 的精度与错误分支。
- `5L-10 tests/unit/test_ldp/test_encoders/test_numerical.py`（Owner：QA｜状态：⚪ 待启动）：规划针对数值离散化策略的覆盖率。
- `5L-11 tests/unit/test_ldp/test_encoders/test_hashing.py`（Owner：QA｜状态：⚪ 待启动）：待实现 hashing encoder 后补充 hash family/碰撞测试。
- `5L-12 tests/unit/test_ldp/test_encoders/test_sketch.py`（Owner：QA｜状态：⚪ 待启动）：需继承 sketch/bloom 工程后验证稀疏恢复能力。
- `5L-13 tests/unit/test_ldp/test_aggregators/__init__.py`（Owner：QA｜状态：⚪ 待启动）：聚合器实现后建公共 fixture。
- `5L-14 tests/unit/test_ldp/test_aggregators/test_frequency.py`（Owner：QA｜状态：⚪ 待启动）：聚合器上线后验证频率估计的偏差/方差。
- `5L-15 tests/unit/test_ldp/test_aggregators/test_mean.py`（Owner：QA｜状态：⚪ 待启动）：需覆盖均值聚合器对噪声输入的鲁棒性。
- `5L-16 tests/unit/test_ldp/test_aggregators/test_variance.py`（Owner：QA｜状态：⚪ 待启动）：计划验证二阶矩估计与误差分析。
- `5L-17 tests/unit/test_ldp/test_aggregators/test_quantile.py`（Owner：QA｜状态：⚪ 待启动）：待实现 quantile 聚合算法后补充顺序统计测试。
- `5L-18 tests/unit/test_ldp/test_applications/__init__.py`（Owner：QA｜状态：⚪ 待启动）：应用示例落地后汇总 fixture。
- `5L-19 tests/unit/test_ldp/test_applications/test_heavy_hitters.py`（Owner：QA｜状态：⚪ 待启动）：需构建 1k 用户样本，验证 heavy hitter 管道与聚合精度。
- `5L-20 tests/unit/test_ldp/test_applications/test_range_queries.py`（Owner：QA｜状态：⚪ 待启动）：实现 LDP range query 后新增端到端测试。
- `5L-21 tests/unit/test_ldp/test_applications/test_marginals.py`（Owner：QA｜状态：⚪ 待启动）：待上线 marginals 应用后，验证不同维度组合的结果。

**单元测试 / utils（Owner：QA｜状态：⚪ 待启动）**

- `5U-09 tests/unit/test_utils/__init__.py`（Owner：QA｜状态：⚪ 待启动）：待 core/utils/* 模块落地后，需在此注册公共 fixture（如随机种子、基准配置）。
- `5U-10 tests/unit/test_utils/test_math_utils.py`（Owner：QA｜状态：⚪ 待启动）：计划覆盖 softmax/logsumexp/stable_log 的数值稳定性，一旦 `math_utils.py` 创建即补测。
- `5U-11 tests/unit/test_utils/test_random.py`（Owner：QA｜状态：⚪ 待启动）：需验证 RNG 包装器是否复用 `numpy.random.Generator` 且支持播种/序列化。
- `5U-12 tests/unit/test_utils/test_validation.py`（Owner：QA｜状态：⚪ 待启动）：待共享参数断言工具上线后，补齐边界/异常信息测试。
- `5U-13 tests/unit/test_utils/test_performance.py`（Owner：QA｜状态：⚪ 待启动）：需对性能计时/内存度量 helper 做稳定性与线程安全断言。

**集成测试（Owner：QA｜状态：⚪ 待启动）**

- `5I-01 tests/integration/__init__.py`（Owner：QA｜状态：⚪ 待启动）：需定义共享数据集/预算 fixture，方便流水线用例共用。
- `5I-02 tests/integration/test_cdp_pipeline.py`（Owner：QA｜状态：⚪ 待启动）：规划覆盖 “数据域→Dataset→机制→Accountant” 的端到端流程，并校验预算累计。
- `5I-03 tests/integration/test_ldp_pipeline.py`（Owner：QA｜状态：⚪ 待启动）：待 LDP encoders/aggregators 可用后，验证客户端采样→上传→服务端聚合。
- `5I-04 tests/integration/test_cross_module.py`（Owner：QA｜状态：⚪ 待启动）：用于验证 core+cdp/ldp 组合调用链、配置共享与限流策略。

**属性测试（Owner：QA｜状态：⚪ 待启动）**

- `5P-01 tests/property_based/__init__.py`（Owner：QA｜状态：⚪ 待启动）：待引入 Hypothesis 设置，共享随机种子与策略。
- `5P-02 tests/property_based/test_dp_properties.py`（Owner：QA｜状态：⚪ 待启动）：将使用 Hypothesis 生成 ε/δ/敏感度组合，断言机制的隐私损失不超过理论上界。
- `5P-03 tests/property_based/test_composition_properties.py`（Owner：QA｜状态：⚪ 待启动）：需要对随机 PrivacyEvent 序列进行组合，验证基本/高级公式是否保持单调性。
- `5P-04 tests/property_based/test_mechanism_properties.py`（Owner：QA｜状态：⚪ 待启动）：计划针对噪声分布（Laplace/Gaussian/...）检验对称性、零均值、尺度关系。
- `5P-05 tests/property_based/test_accuracy_properties.py`（Owner：QA｜状态：⚪ 待启动）：需用随机数据集评估噪声前后误差分布，构建效用曲线。

**性能/准确性测试（Owner：QA｜状态：⚪ 待启动）**

- `5F-01 tests/performance/__init__.py`（Owner：QA｜状态：⚪ 待启动）：待性能基准脚本上线后在此注册 PyTest markers。
- `5F-02 tests/performance/test_mechanism_performance.py`（Owner：QA｜状态：⚪ 待启动）：将评估 Laplace/Gaussian 噪声的吞吐（单值 <1ms、向量 <500ms）。
- `5F-03 tests/performance/test_composition_performance.py`（Owner：QA｜状态：⚪ 待启动）：需压测 composition/moment accountant 的批量组合开销。
- `5F-04 tests/performance/test_ml_performance.py`（Owner：QA｜状态：⚪ 待启动）：DP-SGD 等训练脚本落地后，对梯度裁剪/噪声开销作性能评估。
- `5F-05 tests/performance/test_ldp_performance.py`（Owner：QA｜状态：⚪ 待启动）：需构建 1000 用户样本，验证客户端上传与聚合端延迟 <2s。
- `5F-06 tests/performance/benchmark_utils.py`（Owner：QA｜状态：⚪ 待启动）：计划抽象计时/统计 helper，供 benchmark/test 双方复用。
- `5A-01 tests/accuracy/__init__.py`（Owner：QA｜状态：⚪ 待启动）：待准确性基准脚本上线后统一注册。
- `5A-02 tests/accuracy/test_mechanism_accuracy.py`（Owner：QA｜状态：⚪ 待启动）：将对不同噪声机制测量真实误差 vs 理论 bound。
- `5A-03 tests/accuracy/test_bias_variance.py`（Owner：QA｜状态：⚪ 待启动）：构建多批数据评估偏差/方差与 epsilon 的关系。
- `5A-04 tests/accuracy/test_utility_analysis.py`（Owner：QA｜状态：⚪ 待启动）：计划输出隐私-效用曲线及临界点。
- `5A-05 tests/accuracy/accuracy_utils.py`（Owner：QA｜状态：⚪ 待启动）：需要沉淀准确度指标工具，供准确性测试及 notebook 复用。

**测试基线与夹具（Owner：QA｜状态：⚪ 待启动）**

- `5X-01 tests/fixtures/__init__.py`（Owner：QA｜状态：⚪ 待启动）：需作为统一入口暴露模拟数据/隐私配置。
- `5X-02 tests/fixtures/test_data.py`（Owner：QA｜状态：⚪ 待启动）：计划提供小型 DataFrame/直方图样本供 UT/IT 复用。
- `5X-03 tests/fixtures/mock_objects.py`（Owner：QA｜状态：⚪ 待启动）：需定义伪机制/会计器对象，便于测试注入。
- `5X-04 tests/fixtures/privacy_configs.py`（Owner：QA｜状态：⚪ 待启动）：承担 ε/δ 配置与预算切分参数的集中管理。
- `5X-05 tests/fixtures/mechanism_fixtures.py`（Owner：QA｜状态：⚪ 待启动）：将输出常见机制实例（Laplace/Gaussian/GRR/OUE）供参数化测试使用。
- `5R-01 tests/regression/__init__.py`（Owner：QA｜状态：⚪ 待启动，当前仅存在 `tests/regressionmkdir/` 占位）：需重命名目录，并注册回归基线。
- `5R-02 tests/regression/test_regression_cdp.py`（Owner：QA｜状态：⚪ 待启动）：计划记录关键 bugfix 用例，随 release 回归。
- `5R-03 tests/regression/test_regression_ldp.py`（Owner：QA｜状态：⚪ 待启动）：同上，覆盖客户端链路。
- `5R-04 tests/regression/test_bug_fixes.py`（Owner：QA｜状态：⚪ 待启动）：收集历史缺陷并固化测试。
- `5C-20 tests/conftest.py`（Owner：QA｜状态：🟡 进行中）：目前包含基础 pytest fixture（RNG、DummyDomain），需扩展支持数据集/Accountant/机制工厂。

**CI/基准流水线（Owner：DevOps + Analytics｜状态：🟡 进行中）**

- `5B-01 benchmarks/performance/__init__.py`（Owner：Analytics｜状态：🟡 进行中）：当前仅暴露占位符，待注册机制/组合/ML/ldp 子基准。
- `5B-02 benchmarks/performance/benchmark_mechanisms.py`（Owner：Analytics｜状态：⚪ 待启动）：需针对 Laplace/Gaussian 等噪声机制测量吞吐，并输出 CSV/JSON 供 CI 上传。
- `5B-03 benchmarks/performance/benchmark_composition.py`（Owner：Analytics｜状态：⚪ 待启动）：计划压测 basic/advanced 组合在不同事件数量下的耗时与内存。
- `5B-04 benchmarks/performance/benchmark_ml.py`（Owner：Analytics｜状态：⚪ 待启动）：DP-SGD/线性模型实现后，需记录每轮训练耗时与精度。
- `5B-05 benchmarks/performance/benchmark_ldp.py`（Owner：Analytics｜状态：⚪ 待启动）：构建模拟 1k+ 客户端吞吐基准，量化编码/上传/聚合成本。
- `5B-06 benchmarks/accuracy/__init__.py`（Owner：Analytics｜状态：⚪ 待启动）：待准确性基准脚本上线后注册子模块。
- `5B-07 benchmarks/accuracy/accuracy_mechanisms.py`（Owner：Analytics｜状态：⚪ 待启动）：需输出噪声机制的误差 vs ε 曲线。
- `5B-08 benchmarks/accuracy/accuracy_composition.py`（Owner：Analytics｜状态：⚪ 待启动）：计划验证组合误差累积情况，与理论 bound 对比。
- `5B-09 benchmarks/accuracy/accuracy_ml.py`（Owner：Analytics｜状态：⚪ 待启动）：记录 DP-SGD 模型的 test accuracy 与 baseline 差距。
- `5B-10 benchmarks/accuracy/accuracy_ldp.py`（Owner：Analytics｜状态：⚪ 待启动）：构建 LDP 聚合精度基准，报告 Hellinger/Bias。
- `5B-11 benchmarks/scalability/__init__.py`（Owner：Analytics｜状态：⚪ 待启动）：待扩展 submodule。
- `5B-12 benchmarks/scalability/scalability_mechanisms.py`（Owner：Analytics｜状态：⚪ 待启动）：测量机制在维度/批量增长下的延迟。
- `5B-13 benchmarks/scalability/scalability_ml.py`（Owner：Analytics｜状态：⚪ 待启动）：记录 DP-SGD 在不同样本量（1e4~1e6）下的扩展性。
- `5B-14 benchmarks/scalability/scalability_ldp.py`（Owner：Analytics｜状态：⚪ 待启动）：评估 LDP 客户端数量扩展与聚合性能。
- `5B-15 benchmarks/run_benchmarks.py`（Owner：Analytics｜状态：⚪ 待启动）：负责统一入口、解析 CLI 参数并上传结果。
- `5W-01 .github/workflows/ci.yml`（Owner：DevOps｜状态：🟡 进行中）：现已运行 lint+pytest，需补 coverage/benchmark artifact 上传与多 Python 版本矩阵。

---

## 阶段 6 · 文档、示例与教程（状态：🟡 进行中）

**阶段目标**：提供可构建的 Sphinx 文档、示例与教程，覆盖客户端/服务端全链路。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 6.1 | 维护 Sphinx 目录结构（overview/installation/api/theory/development） | Stage 0~3 | `docs/*.rst`, `docs/development/*.md` | Tech Writer | 🟡 进行中（仅 `index.rst`/`conf.py` 空壳） |
| 6.2 | 同步 API 文档与最新接口（core/cdp/ldp） | Stage 1~3 | `docs/api/*.rst` | Tech Writer | ⚪ 待启动 |
| 6.3 | 编写安装/快速开始/FAQ | Stage 4 | `docs/installation.rst`, `docs/quickstart.rst` | Tech Writer | ⚪ 待启动（文件未创建） |
| 6.4 | 丰富示例与 notebooks（CDP & LDP 端到端） | Stage 2~3 | `examples/*`, `notebooks/tutorials/*` | Dev + TW | ⚪ 待启动（目录为空） |
| 6.5 | 配置文档构建/校验（`sphinx-build`, `nbval`, `pytest --examples`） | Stage 6.2~6.4 | CI job &报告 | DevOps | ⚪ 待启动 |
| 6.6 | 输出隐私预算/性能评估可视化教程 | Stage 2~5 | Notebooks、图表 | Analytics | ⚪ 待启动 |

**出口检查**：Sphinx 构建 0 warning，示例可自动验证，教程覆盖安装+隐私预算+性能分析。当前文档结构齐全，但 API/示例/验证仍在更新。

### 文件级拆解（Stage 6 · 文档/示例/教程）

**Sphinx 主站**

- `6D-01 docs/index.rst`（Owner：Tech Writer｜状态：🟡 进行中）：仅含空骨架，需补充章节导航。
- `6D-02 docs/conf.py`（Owner：Tech Writer｜状态：🟡 进行中）：仅初始化主题配置，待补扩展/版本信息。
- `6D-03 docs/overview.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建。
- `6D-04 docs/installation.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建。
- `6D-05 docs/quickstart.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建。
- `6D-06 docs/tutorials.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建。

**API/Examples/Theory 栏目**

- `6A-01 docs/api/index.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：尚未搭建 API 索引骨架以串联 core/cdp/ldp 页面。
- `6A-02 docs/api/core.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：core API 文档尚未撰写。
- `6A-03 docs/api/cdp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：CDP API 文档尚未撰写。
- `6A-04 docs/api/ldp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：LDP API 文档尚未撰写。
- `6E-01 docs/examples/index.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：示例索引页缺失。
- `6E-02 docs/examples/basic.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：基础示例文档缺失。
- `6E-03 docs/examples/cdp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：CDP 示例文档缺失。
- `6E-04 docs/examples/ldp.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：LDP 示例文档缺失。
- `6T-01 docs/theory/index.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：理论篇索引未搭建。
- `6T-02 docs/theory/dp_basics.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：DP 基础章节缺失。
- `6T-03 docs/theory/mechanisms.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：DP 机制章节缺失。
- `6Dev-01 docs/development/index.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：开发者文档入口页缺失。
- `6Dev-02 docs/development/contributing.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：开发贡献指南尚未沉淀。
- `6Dev-03 docs/development/testing.rst`（Owner：Tech Writer｜状态：⚪ 待启动）：测试规范文档未编写。
- `6S-01 docs/_static/custom.css`（Owner：Tech Writer｜状态：⚪ 待启动）：自定义样式文件未准备。
- `6S-02 docs/_static/logo.png`（Owner：Tech Writer｜状态：⚪ 待启动）：品牌 Logo 资源未提供。

**Python 示例**

- `6X-01 examples/basic/__init__.py`（Owner：Dev + TW｜状态：⚪ 待启动）：基础示例包的入口文件缺失。
- `6X-02 examples/basic/basic_queries.py`（Owner：Dev + TW｜状态：⚪ 待启动）：基本查询示例脚本未编写。
- `6X-03 examples/basic/mechanism_demo.py`（Owner：Dev + TW｜状态：⚪ 待启动）：机制演示脚本缺失。
- `6X-04 examples/basic/composition_demo.py`（Owner：Dev + TW｜状态：⚪ 待启动）：组合示例脚本缺失。
- `6X-05 examples/basic/privacy_accounting_demo.py`（Owner：Dev + TW｜状态：⚪ 待启动）：隐私会计示例脚本缺失。
- `6X-06 examples/cdp_examples/__init__.py`（Owner：Dev + TW｜状态：⚪ 待启动）：CDP 示例包入口缺失。
- `6X-07 examples/cdp_examples/cdp_mechanisms.py`（Owner：Dev + TW｜状态：⚪ 待启动）：CDP 机制示例脚本缺失。
- `6X-08 examples/cdp_examples/cdp_ml_training.py`（Owner：Dev + TW｜状态：⚪ 待启动）：CDP ML 训练示例缺失。
- `6X-09 examples/cdp_examples/cdp_data_analysis.py`（Owner：Dev + TW｜状态：⚪ 待启动）：CDP 数据分析示例缺失。
- `6X-10 examples/cdp_examples/cdp_synthetic_data.py`（Owner：Dev + TW｜状态：⚪ 待启动）：CDP 合成数据示例缺失。
- `6X-11 examples/ldp_examples/__init__.py`（Owner：Dev + TW｜状态：⚪ 待启动）：LDP 示例包入口缺失。
- `6X-12 examples/ldp_examples/ldp_frequency_estimation.py`（Owner：Dev + TW｜状态：⚪ 待启动）：LDP 频率估计示例缺失。
- `6X-13 examples/ldp_examples/ldp_mean_estimation.py`（Owner：Dev + TW｜状态：⚪ 待启动）：LDP 均值估计示例缺失。
- `6X-14 examples/ldp_examples/ldp_heavy_hitters.py`（Owner：Dev + TW｜状态：⚪ 待启动）：LDP 频繁项示例缺失。
- `6X-15 examples/ldp_examples/ldp_applications.py`（Owner：Dev + TW｜状态：⚪ 待启动）：LDP 综合应用示例缺失。
- `6X-16 examples/advanced/__init__.py`（Owner：Dev + TW｜状态：⚪ 待启动）：高级示例包入口缺失。
- `6X-17 examples/advanced/custom_mechanisms.py`（Owner：Dev + TW｜状态：⚪ 待启动）：自定义机制示例缺失。
- `6X-18 examples/advanced/performance_tuning.py`（Owner：Dev + TW｜状态：⚪ 待启动）：性能调优示例缺失。
- `6X-19 examples/advanced/real_world_scenarios.py`（Owner：Dev + TW｜状态：⚪ 待启动）：真实场景示例缺失。

**Notebooks**

- `6N-01 notebooks/tutorials/01_getting_started.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：入门教程 Notebook 缺失。
- `6N-02 notebooks/tutorials/02_cdp_mechanisms.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：CDP 机制教程 Notebook 缺失。
- `6N-03 notebooks/tutorials/03_ldp_mechanisms.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：LDP 机制教程 Notebook 缺失。
- `6N-04 notebooks/tutorials/04_privacy_accounting.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：隐私会计教程 Notebook 缺失。
- `6N-05 notebooks/tutorials/05_dp_machine_learning.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：DP 机器学习教程 Notebook 缺失。
- `6N-06 notebooks/tutorials/06_advanced_topics.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：高级主题 Notebook 缺失。
- `6N-07 notebooks/demonstrations/real_world_examples.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：真实案例演示 Notebook 缺失。
- `6N-08 notebooks/demonstrations/privacy_utility_tradeoff.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：隐私-效用权衡 Notebook 缺失。
- `6N-09 notebooks/demonstrations/performance_comparison.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：性能对比 Notebook 缺失。
- `6N-10 notebooks/research/algorithm_comparison.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：研究向算法对比 Notebook 缺失。
- `6N-11 notebooks/research/novel_mechanisms.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：新型机制 Notebook 缺失。
- `6N-12 notebooks/research/privacy_analysis.ipynb`（Owner：Analytics｜状态：⚪ 待启动）：隐私分析 Notebook 缺失。

**构建 & 验证**

- `6B-01 docs/Makefile`（Owner：DevOps｜状态：⚪ 待启动）：文件未创建，需封装 `sphinx-build`/`linkcheck`/`html`。
- `6B-02 docs/requirements-docs.txt`（Owner：DevOps｜状态：⚪ 待启动）：文件未创建，需锁定构建依赖。
- `6CI-01 .github/workflows/docs.yml`（Owner：DevOps｜状态：⚪ 待启动）：未创建，需负责文档构建、`nbval` 与示例测试。

---

## 阶段 7 · 发布与运维（状态：⚪ 待启动）

**阶段目标**：建立发布流程、版本策略、监控与运维手册，完成 PyPI/私有仓库发布。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 7.1 | 制定发布策略与版本节奏（SemVer + LTS） | Stage 0~4 | Release Policy 文档 | PM/Dev Lead | ⚪ 待启动 |
| 7.2 | 搭建 release pipeline（版本号、build、签名、上传） | Stage 4 | `.github/workflows/release.yml` 或脚本 | DevOps | ⚪ 待启动 |
| 7.3 | 发布前验证：隐私/性能/回归 Gate | Stage 5 | Release checklist | QA | ⚪ 待启动 |
| 7.4 | 运维与监控（性能、预算、错误率） | Stage 2~3 | Runbook、监控面板 | DevOps | ⚪ 待启动 |
| 7.5 | 缺陷响应与版本支持流程 | 7.1 | Issue/Support Playbook | PM | ⚪ 待启动 |
| 7.6 | 首次公开版本（v0.1.0）发布与回顾 | 7.1~7.5 | Release Note、复盘纪要 | 全员 | ⚪ 待启动 |

**出口检查**：PyPI/私有仓库发布完成，运维 runbook 生效，反馈闭环建立。当前尚未启动，需等待 Stage 4~6 输入。

### 文件级拆解（Stage 7 · 发布与运维）

- `7R-01 docs/development/project_plan.md`（Owner：PM｜状态：🟡 进行中）：文档已存在，但尚未覆盖发布节奏/回归窗口。
- `7R-02 docs/development/tech_stack.md`（Owner：Dev Lead｜状态：🟡 进行中）：记录了当前依赖，需追加签名策略与 Release 支撑。
- `7R-03 docs/development/release_policy.md`（Owner：PM｜状态：⚪ 待启动）：文件未创建，需要定义 SemVer/LTS、回滚流程。
- `7R-04 docs/development/runbook.md`（Owner：DevOps｜状态：⚪ 待启动）：文件未创建，需沉淀部署/监控/报警流程。
- `7R-05 docs/development/support_playbook.md`（Owner：PM｜状态：⚪ 待启动）：文件未创建，需记录问题分级/SLA。
- `7R-06 docs/releases/v0.1.0.md`（Owner：Tech Writer｜状态：⚪ 待启动）：文件未创建，需编写 Release Notes。
- `7P-01 .github/workflows/release.yml`（Owner：DevOps｜状态：⚪ 待启动）：workflow 未存在。
- `7P-02 scripts/release.py`（Owner：DevOps｜状态：⚪ 待启动）：脚本未存在。
- `7P-03 pyproject.toml / setup.cfg`（Owner：Build Engineer｜状态：🟡 进行中）：基础 metadata 已有，仍需补 `project.urls`、分类器等发布信息。
- `7P-04 README.md`（Owner：Dev Lead｜状态：🟡 进行中）：需在发布前补充安装/徽章/兼容性内容。
- `7O-01 benchmarks/performance/*` + `benchmarks/run_benchmarks.py`（Owner：Analytics｜状态：⚪ 待启动）：Benchmark 脚本尚未实现。
- `7O-02 docs/api/*` 与 `docs/examples/*`（Owner：Tech Writer｜状态：⚪ 待启动）：API/示例文档尚未生成。
- `7O-03 notebooks/*`（Owner：Analytics｜状态：⚪ 待启动）：Notebook 尚未编写。
- `7O-04 README.md` + `docs/overview.rst`（Owner：Dev Lead｜状态：⚪ 待启动）：发布说明/概览章节尚未完善。

---

## 使用方式

1. 以表格中的 Step ID 为粒度创建任务或提示词（例如 “执行 Step 2.5：完善 `src/dplib/cdp/analytics` 并补基准脚本”）。
2. 通过“状态”列快速识别已完成与待补项，避免重复投入。
3. 若需要新增工作流，先在 `docs/development/project_plan.md` 中补充宏观规划，再回填到本文件。
