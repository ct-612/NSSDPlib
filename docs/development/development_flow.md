# NSSDPlib 全流程开发作业指引（步骤级）

本指引基于 `docs/development/project_plan.md`、`requirements.md`、`architecture.md`、`tech_stack.md` 以及当前代码仓库结构（`src/dplib/*`, `tests/*`, `docs/*`）整理，旨在帮助项目负责人快速了解从立项到发布的每一个执行步骤、交付物、责任人以及现状。

## 状态图例

- **已完成**：交付物存在且达成阶段验收目标。
- **进行中**：基础工作或部分交付已存在，尚需补齐验收条件。
- **待启动**：前置条件尚未达成或工作尚未开启。

## 阶段状态概览

| 阶段 | 目标概述 | 当前状态 | 佐证 |
| ---- | -------- | -------- | ---- |
| 0 项目准备与架构设计 | 冻结需求/架构/CI 策略 | 已完成 | `docs/development/requirements.md`, `architecture.md`, `tech_stack.md`, `project_plan.md` |
| 1 核心框架开发（core/） | 建立 BaseMechanism/Accountant/Data/Utils | 进行中 | `src/dplib/core/*`, `tests/unit/test_core` |
| 2 CDP 模块实现 | 服务端机制/组合/ML/analytics | 进行中 | `src/dplib/cdp/*`, `docs/development/project_plan.md` 更新 |
| 3 LDP 模块实现 | 客户端机制/编码/聚合/应用 | 进行中 | `src/dplib/ldp/*` |
| 4 模块化安装与包管理 | 拆分 core/cdp/ldp 安装与 extras | 待启动 | `pyproject.toml` 仍为单包 |
| 5 测试与验证 | 单元/集成/属性/性能/回归体系 | 进行中 | `tests/(unit|integration|property_based|performance)` |
| 6 文档、示例与教程 | 完整 Sphinx 文档与示例矩阵 | 进行中 | `docs/*`, `examples/*`, `notebooks/*` |
| 7 发布与运维 | PyPI 分发、监控、版本治理 | 待启动 | 缺少 release pipeline 与运维文档 |

---

## 阶段 0 · 项目准备与架构设计（状态：已完成）

**阶段目标**：明确范围、架构、模块边界、技术/CI 策略与协作规范。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 0.1 | 收集业务与技术需求、建立优先级 | 访谈记录、竞品调研 | `docs/development/requirements.md` | PM/架构 | 已完成 |
| 0.2 | 绘制总体架构、数据流、部署拓扑 | 需求基线 | `docs/development/architecture.md` | 架构 | 已完成 |
| 0.3 | 定义技术栈、依赖矩阵、CI/CD 策略 | 架构草案 | `docs/development/tech_stack.md` | Dev Lead | 已完成 |
| 0.4 | 输出阶段性计划与流程 | 0.1~0.3 | `docs/development/project_plan.md` | PM | 已完成 |
| 0.5 | 建立协作规范（代码风格、分支、评审） | 团队约定 | README/CONTRIBUTING（待补充） | 所有人 | 进行中（需沉淀贡献指引） |

**出口检查**：需求/架构/技术栈文档齐全且通过评审；后续阶段以此为输入。当前仅贡献指南待补充，可在 Stage 6 同步。

---

## 阶段 1 · 核心框架开发（core/）（状态：进行中）

**阶段目标**：实现所有模块共用的基础抽象与工具，并具备基本测试覆盖。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 1.1 | 实现 `BaseMechanism`/`PrivacyAccountant`/`Composition` 抽象及异常体系 | `api_contracts.md` | `src/dplib/core/privacy/*` | Core Team | 已完成（代码存在，需验证接口一致性） |
| 1.2 | 实现数据域/敏感度抽象与验证工具 | Step 1.1 | `src/dplib/core/data/*` | Core Team | 进行中（API 需对齐 LDP 需求） |
| 1.3 | 完成 `core/utils`（math/random/config/logging/perf） | Step 1.1 | `src/dplib/core/utils/*` | Core Team | 进行中（性能监控与配置文档缺失） |
| 1.4 | 建立机制工厂与注册表 | 1.1~1.3 | `src/dplib/core/__init__.py`、工厂模块 | Core Team | 进行中 |
| 1.5 | 覆盖核心单元测试 + 类型/格式化检查 | 代码实现 | `tests/unit/test_core/*`, CI 配置 | QA/Dev | 进行中（测试框架存在，覆盖率尚未验证） |
| 1.6 | 生成核心 API 文档草稿 | 1.1~1.4 | `docs/api/core.rst`（待补充） | Tech Writer | 待启动 |

**出口检查**：`core/` UT 覆盖 ≥80%，wheel <5MB，API 契约一致。当前需补齐数据/工具文档与覆盖率报告。

---

## 阶段 2 · CDP 模块实现（服务器端）（状态：进行中）

**阶段目标**：完成服务端差分隐私机制、组合、敏感度、ML 支持及分析工具。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 2.1 | 实现拉普拉斯/高斯/指数/几何/阶梯/向量机制及注册 | Stage 1 | `src/dplib/cdp/mechanisms/*` | CDP Team | 已完成（实现存在，需补文档） |
| 2.2 | 实现基本/高级组合与 Moments Accountant | Stage 1 | `src/dplib/cdp/composition/*` | CDP Team | 进行中（Moments Accountant 待验证） |
| 2.3 | 敏感度分析与噪声校准工具 | Stage 1 | `src/dplib/cdp/sensitivity/*` | CDP Team | 进行中 |
| 2.4 | DP-SGD 等 ML 管线与示例 | Stage 1 | `src/dplib/cdp/ml/*`, `examples/cdp/*` | ML Subteam | 进行中（示例缺少） |
| 2.5 | CDP Analytics：查询 API、报告、基准脚本 | 2.1~2.4 | `src/dplib/cdp/analytics/*`, `benchmarks/performance/*` | Analytics | 进行中（新目录正在开发） |
| 2.6 | 单元/集成/性能测试与文档 | 2.1~2.5 | `tests/unit/test_cdp/*`, `docs/api/cdp.rst` | QA/Tech Writer | 进行中 |

**出口检查**：噪声 <1ms、DP-SGD ≥OpenDP 0.9×、测试覆盖 ≥85%。当前 analytics/benchmarks/文档仍在补齐，性能验证未记录。

---

## 阶段 3 · LDP 模块实现（客户端）（状态：进行中）

**阶段目标**：为客户端提供轻量机制、编码、聚合与示例，保证包体积和性能。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 3.1 | 实现 GRR/OUE/OLH/RAPPOR/连续值机制 | Stage 1 | `src/dplib/ldp/mechanisms/*` | LDP Team | 已完成（实现存在） |
| 3.2 | 编码器（分类/数值/哈希/Sketch/BF）及元数据输出 | 3.1 | `src/dplib/ldp/encoders/*` | LDP Team | 进行中（元数据/Schema 待完善） |
| 3.3 | 聚合器（频率/均值/方差/分位数） | 3.1 | `src/dplib/ldp/aggregators/*` | LDP Team | 进行中 |
| 3.4 | 典型应用（heavy hitters、range query 等） | 3.2~3.3 | `src/dplib/ldp/applications/*`, `examples/ldp/*` | LDP Team | 进行中（示例待补） |
| 3.5 | 轻量序列化/网络接口（JSON/Protobuf） | 3.1~3.4 | 序列化模块（待建） | LDP Team | 待启动 |
| 3.6 | 客户端基准与准确性评估 | 3.1~3.4 | `benchmarks/performance/ldp_*` | QA | 待启动 |
| 3.7 | 文档与教程（客户端视角） | 3.1~3.5 | `docs/api/ldp.rst`, `notebooks/tutorials/*` | Tech Writer | 进行中 |

**出口检查**：`dplib-ldp` <10MB，1000 用户聚合 <2s，端到端示例可跑通。当前缺乏序列化层、基准测试与教程验证。

---

## 阶段 4 · 模块化安装与包管理（状态：待启动）

**阶段目标**：拆分 `dplib-core`/`dplib-cdp`/`dplib-ldp`，提供 extras/executable 构建与安装指南。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 4.1 | 设计包拆分方案与依赖拓扑 | Stage 0~3 | 包拆分 RFC | Dev Lead | 待启动 |
| 4.2 | 更新 `pyproject.toml`/`setup.cfg`（多 wheel + extras） | 4.1 | 配置文件/构建脚本 | Build Engineer | 待启动（当前仍单包） |
| 4.3 | 配置 `python -m build` 与 `twine` 流程 | 4.2 | `build/` 脚本、CI job | Build Engineer | 待启动 |
| 4.4 | 安装矩阵验证（core-only、cdp、ldp、dev/docs） | 4.2 | 测试矩阵报告 | QA | 待启动 |
| 4.5 | 更新安装文档/FAQ | 4.2~4.4 | `docs/installation.rst`, README | Tech Writer | 待启动 |

**出口检查**：多 wheel 构建通过、依赖拓扑清晰、安装文档落地。需等 Stage 3 基础稳定后启动。

---

## 阶段 5 · 测试与验证（状态：进行中）

**阶段目标**：建立完整的 UT/集成/属性/性能/回归体系并集成 CI。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 5.1 | 规划测试层级与目录 | Stage 0~3 | `tests/unit`, `tests/integration`, `tests/property_based`, `tests/performance`, `tests/accuracy`, `tests/regression`, `tests/fixtures` | QA | 已完成（目录已建） |
| 5.2 | 实现 core/cdp/ldp 单元测试并收集覆盖率 | Stage 1~3 | `tests/unit/*`, 覆盖率报告 | QA | 进行中（覆盖率未统计） |
| 5.3 | 构建 LDP→CDP 端到端集成测试 | Stage 2~3 | `tests/integration/*` | QA | 进行中 |
| 5.4 | 属性测试（ε/δ 边界）与 `hypothesis` 库整合 | Stage 1~3 | `tests/property_based/*` | QA | 进行中（框架存在需补案例） |
| 5.5 | 性能 & 基准测试流水线（nightly） | Stage 2~3 | `tests/performance/*`, `benchmarks/*` | QA/DevOps | 待启动 |
| 5.6 | 回归测试与基线数据维护 | 2~3 | `tests/regression/*`, 基线工件 | QA | 待启动 |
| 5.7 | CI 集成（GitHub Actions matrix + 报告上传） | 5.2~5.6 | `.github/workflows/*` | DevOps | 进行中（需接入覆盖率/基准上传） |

**出口检查**：语句覆盖率 ≥90%，核心模块 ≥95%，属性/性能测试达标并自动化执行。尚需补齐覆盖率统计与性能流水线。

---

## 阶段 6 · 文档、示例与教程（状态：进行中）

**阶段目标**：提供可构建的 Sphinx 文档、示例与教程，覆盖客户端/服务端全链路。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 6.1 | 维护 Sphinx 目录结构（overview/installation/api/theory/development） | Stage 0~3 | `docs/*.rst`, `docs/development/*.md` | Tech Writer | 已完成（结构存在） |
| 6.2 | 同步 API 文档与最新接口（core/cdp/ldp） | Stage 1~3 | `docs/api/*.rst` | Tech Writer | 进行中 |
| 6.3 | 编写安装/快速开始/FAQ | Stage 4 | `docs/installation.rst`, `docs/quickstart.rst` | Tech Writer | 待启动（依赖 Stage 4 输出） |
| 6.4 | 丰富示例与 notebooks（CDP & LDP 端到端） | Stage 2~3 | `examples/*`, `notebooks/tutorials/*` | Dev + TW | 进行中 |
| 6.5 | 配置文档构建/校验（`sphinx-build`, `nbval`, `pytest --examples`） | Stage 6.2~6.4 | CI job &报告 | DevOps | 进行中（需消除 warning） |
| 6.6 | 输出隐私预算/性能评估可视化教程 | Stage 2~5 | Notebooks、图表 | Analytics | 待启动 |

**出口检查**：Sphinx 构建 0 warning，示例可自动验证，教程覆盖安装+隐私预算+性能分析。当前文档结构齐全，但 API/示例/验证仍在更新。

---

## 阶段 7 · 发布与运维（状态：待启动）

**阶段目标**：建立发布流程、版本策略、监控与运维手册，完成 PyPI/私有仓库发布。

| Step | 具体工作 | 输入/依赖 | 产出 | Owner | 状态 |
| ---- | -------- | -------- | ---- | ----- | ---- |
| 7.1 | 制定发布策略与版本节奏（SemVer + LTS） | Stage 0~4 | Release Policy 文档 | PM/Dev Lead | 待启动 |
| 7.2 | 搭建 release pipeline（版本号、build、签名、上传） | Stage 4 | `.github/workflows/release.yml` or 等效脚本 | DevOps | 待启动 |
| 7.3 | 发布前验证：隐私/性能/回归 Gate | Stage 5 | Release checklist | QA | 待启动 |
| 7.4 | 运维与监控（性能、预算、错误率） | Stage 2~3 | Runbook、监控面板 | DevOps | 待启动 |
| 7.5 | 缺陷响应与版本支持流程 | 7.1 | Issue/Support Playbook | PM | 待启动 |
| 7.6 | 首次公开版本（v0.1.0）发布与回顾 | 7.1~7.5 | Release Note、复盘纪要 | 全员 | 待启动 |

**出口检查**：PyPI/私有仓库发布完成，运维 runbook 生效，反馈闭环建立。当前尚未启动，需等待 Stage 4~6 输入。

---

## 使用方式

1. 以表格中的 Step ID 为粒度创建任务或提示词（例如 “执行 Step 2.5：完善 `src/dplib/cdp/analytics` 并补基准脚本”）。
2. 通过“状态”列快速识别已完成与待补项，避免重复投入。
3. 若需要新增工作流，先在 `docs/development/project_plan.md` 中补充宏观规划，再回填到本文件。
