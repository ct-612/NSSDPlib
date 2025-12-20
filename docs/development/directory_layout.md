## **🏗️ 目录结构**

```
NSSDPlib/                              # 统一差分隐私库
├── 📁 docs/                           # 精简文档模块
│   ├── 📄 index.rst                   # 文档首页
│   ├── 📄 conf.py                     # Sphinx配置
│   ├── 📄 overview.rst                # 库概述
│   ├── 📄 installation.rst            # 安装指南
│   ├── 📄 quickstart.rst              # 快速开始
│   ├── 📄 tutorials.rst               # 教程集合
│   ├── 📁 api/                        # API参考
│   │   ├── 📄 index.rst
│   │   ├── 📄 core.rst
│   │   ├── 📄 cdp.rst
│   │   └── 📄 ldp.rst
│   ├── 📁 examples/                   # 示例文档
│   │   ├── 📄 index.rst
│   │   ├── 📄 basic.rst
│   │   ├── 📄 cdp.rst
│   │   └── 📄 ldp.rst
│   ├── 📁 theory/                     # 理论背景
│   │   ├── 📄 index.rst
│   │   ├── 📄 dp_basics.rst
│   │   └── 📄 mechanisms.rst
│   ├── 📁 development/                # 开发文档
│   │   ├── 📄 index.rst
│   │   ├── 📄 contributing.rst
│   │   ├── 📄 testing.rst
│   │   ├── 📄 api_contracts.md
│   │   ├── 📄 architecture.md
│   │   ├── 📄 development_flow.md
│   │   ├── 📄 directory_layout.md
│   │   ├── 📄 project_plan.md
│   │   ├── 📄 requirements.md
│   │   └── 📄 tech_stack.md
│   ├── 📁 _static/                    # 静态文件
│   │   ├── 📄 custom.css
│   │   └── 📄 logo.png
│   ├── 📄 Makefile                    # 构建命令
│   └── 📄 requirements-docs.txt       # 文档构建依赖
├── 📁 src/                            # 源码根目录
│   └── 📁 dplib/
│       ├── 📁 core/                   # 核心框架（必需）
│       │   ├── 📁 privacy/            # 隐私抽象层
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 base_mechanism.py       # 机制抽象基类
│       │   │   ├── 📄 privacy_accountant.py   # 统一隐私会计器
│       │   │   ├── 📄 composition.py          # 组合定理抽象
│       │   │   ├── 📄 privacy_model.py        # 隐私模型枚举(CDP/LDP)
│       │   │   ├── 📄 budget_tracker.py       # 预算跟踪器
│       │   │   └── 📄 privacy_guarantee.py    # 隐私保证证明
│       │   ├── 📁 data/                       # 数据抽象层
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 domain.py               # 数据域抽象基类
│       │   │   ├── 📄 dataset.py              # 数据集抽象
│       │   │   ├── 📄 transformers.py         # 数据转换流水线
│       │   │   ├── 📄 data_validation.py      # 数据验证工具
│       │   │   ├── 📄 statistics.py           # 数据统计工具
│       │   │   └── 📄 sensitivity.py          # 敏感度计算工具
│       │   ├── 📁 utils/                      # 共享工具库
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 math_utils.py           # 数学工具(softmax, logsumexp等)
│       │   │   ├── 📄 random.py               # 随机数生成器
│       │   │   ├── 📄 config.py               # 统一配置管理
│       │   │   ├── 📄 serialization.py        # 序列化工具
│       │   │   ├── 📄 logging.py              # 日志系统
│       │   │   ├── 📄 param_validation.py     # 参数验证装饰器
│       │   │   └── 📄 performance.py          # 性能监控工具
│       │   └── 📄 __init__.py
│       ├── 📁 cdp/                            # 中心化差分隐私模块
│       │   ├── 📁 mechanisms/                 # CDP机制实现
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 laplace.py              # 拉普拉斯机制
│       │   │   ├── 📄 gaussian.py             # 高斯机制
│       │   │   ├── 📄 exponential.py          # 指数机制
│       │   │   ├── 📄 geometric.py            # 几何机制
│       │   │   ├── 📄 staircase.py            # 阶梯机制
│       │   │   ├── 📄 vector.py               # 向量值机制
│       │   │   ├── 📄 mechanism_factory.py    # CDP机制工厂
│       │   │   └── 📄 mechanism_registry.py   # 机制注册表
│       │   ├── 📁 composition/                # CDP组合定理
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 basic.py                # 基本组合
│       │   │   ├── 📄 advanced.py             # 高级组合(矩会计)
│       │   │   ├── 📄 privacy_accountant.py   # CDP隐私会计
│       │   │   ├── 📄 budget_scheduler.py     # 预算调度器
│       │   │   ├── 📄 moment_accountant.py
│       │   │   └── 📄 composition_theorems.py # 组合定理实现
│       │   ├── 📁 sensitivity/                # 敏感度分析
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 sensitivity_analyzer.py # 敏感度分析器
│       │   │   ├── 📄 noise_calibrator.py     # 噪声校准器
│       │   │   ├── 📄 sensitivity_bounds.py   # 敏感度边界计算
│       │   │   └── 📄 global_sensitivity.py   # 全局敏感度
│       │   ├── 📁 ml/                         # CDP机器学习
│       │   │   ├── 📁 models/                 # 差分隐私模型
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 linear.py           # 线性模型(LR, SVM)
│       │   │   │   ├── 📄 neural_network.py   # 神经网络
│       │   │   │   ├── 📄 tree_model.py       # 树模型(DP-GBDT)
│       │   │   │   ├── 📄 clustering.py       # 聚类模型(DP-KMeans)
│       │   │   │   └── 📄 model_factory.py    # 模型工厂
│       │   │   ├── 📁 training/               # 训练算法
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 dp_sgd.py           # DP-SGD实现
│       │   │   │   ├── 📄 objective_perturbation.py # 目标扰动
│       │   │   │   ├── 📄 output_perturbation.py    # 输出扰动
│       │   │   │   ├── 📄 trainer.py          # 训练器基类
│       │   │   │   └── 📄 gradient_clipping.py # 梯度裁剪
│       │   │   ├── 📁 evaluation/             # 模型评估
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 metrics.py          # 隐私保护评估指标
│       │   │   │   ├── 📄 validator.py        # 模型验证器
│       │   │   │   └── 📄 privacy_audit.py    # 隐私审计
│       │   │   └── 📄 __init__.py
│       │   ├── 📁 analytics/                  # CDP分析工具
│       │   │   ├── 📁 queries/                # 隐私保护查询
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 count.py            # 计数查询
│       │   │   │   ├── 📄 sum.py              # 求和查询
│       │   │   │   ├── 📄 mean.py             # 均值查询
│       │   │   │   ├── 📄 variance.py         # 方差查询
│       │   │   │   ├── 📄 histogram.py        # 直方图查询
│       │   │   │   ├── 📄 range_query.py      # 范围查询
│       │   │   │   └── 📄 query_engine.py     # 查询引擎
│       │   │   ├── 📁 synthetic_data/         # 合成数据生成
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 base_generator.py   # 生成器基类
│       │   │   │   ├── 📄 marginal.py         # 边际方法
│       │   │   │   ├── 📄 bayesian.py         # 贝叶斯网络
│       │   │   │   ├── 📄 gan.py              # 生成对抗网络
│       │   │   │   └── 📄 copula.py           # Copula方法
│       │   │   ├── 📁 reporting/              # 报告生成
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 privacy_report.py   # 隐私报告
│       │   │   │   └── 📄 utility_report.py   # 效用报告
│       │   │   └── 📄 __init__.py
│       │   └── 📄 __init__.py
│       ├── 📁 ldp/                            # 本地差分隐私模块
│       │   ├── 📄 types.py                    # LDPReport / EncodedValue / Estimate 等跨模块共享类型定义
│       │   ├── 📄 ldp_utils.py                    # LDP 专用工具：hash family、bit 操作、通用校验/数学 helper
│       │   ├── 📁 mechanisms/                 # 本地扰动机制（严格 client-side 语义）
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 base.py                 # BaseLDPMechanism：继承 core.BaseMechanism，固定 privacy_model=LDP
│       │   │   ├── 📁 discrete/               # 离散 LDP 机制（分类/有限域）
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 grr.py              # 广义随机响应
│       │   │   │   ├── 📄 oue.py              # 优化一元编码
│       │   │   │   ├── 📄 olh.py              # 优化局部哈希
│       │   │   │   ├── 📄 rappor.py           # RAPPOR机制
│       │   │   │   └── 📄 unary_randomizer.py # 对 unary 编码后的 bit 向量做随机化（和 encoders.unary 配合）
│       │   │   ├── 📁 continuous/             # 连续值LDP机制
│       │   │   │   ├── 📄 __init__.py
│       │   │   │   ├── 📄 laplace_local.py    # 本地 Laplace 噪声（区间裁剪后加噪）
│       │   │   │   ├── 📄 gaussian_local.py   # 本地 Gaussian 噪声（区间裁剪后加噪）
│       │   │   │   ├── 📄 piecewise.py        # Piecewise 机制（Kairouz 型等）
│       │   │   │   └── 📄 duchi.py            # Duchi机制
│       │   │   ├── 📄 mechanism_factory.py    # LDP机制工厂
│       │   │   └── 📄 mechanism_registry.py   # LDP机制注册表
│       │   ├── 📁 encoders/                   # 编码层（deterministic，client/server 共享）
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 base.py                 # BaseEncoder 协议：fit/encode/decode/metadata
│       │   │   ├── 📄 categorical.py          # 类别编码：label / one-hot 等
│       │   │   ├── 📄 numerical.py            # 数值离散化编码：等宽/等频 bucket
│       │   │   ├── 📄 unary.py                # Unary / Binary 编码（仅编码，不加噪）
│       │   │   ├── 📄 hashing.py              # 通用 hash-based 编码（OLH / sketch 等的基础）
│       │   │   ├── 📄 sketch.py               # Count-Sketch / Count-Min 等结构的编码支持
│       │   │   ├── 📄 bloom_filter.py         # Bloom Filter 编码（RAPPOR 用）
│       │   │   └── 📄 encoder_factory.py      # 编码器工厂
│       │   ├── 📁 aggregators/                # 聚合层（strict server-side 语义）
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 base.py                 # BaseAggregator：aggregate(reports) -> Estimate
│       │   │   ├── 📄 frequency.py            # 频率估计聚合器（适配 GRR/UE/OLH/RAPPOR）
│       │   │   ├── 📄 mean.py                 # 均值估计（需要 continuous LDP 机制输出）
│       │   │   ├── 📄 variance.py             # 方差 / 二阶矩估计
│       │   │   ├── 📄 quantile.py             # 分位数估计（可用分桶+秩近似）
│       │   │   ├── 📄 user_level.py           # 用户级聚合逻辑：按 user_id 合并多轮报告（原 user_aggregate.py）
│       │   │   ├── 📄 consistency.py          # 一致性约束工具（一致性后处理：非负、归一化等）
│       │   │   └── 📄 aggregator_factory.py   # 聚合器工厂
│       │   ├── 📁 composition/                # LDP 视角的隐私组合 & 会计（per-user ε）
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 compose.py
│       │   │   ├── 📄 ldp_cdp_mapping.py
│       │   │   └── 📄 privacy_accountant.py   # LDP 会计器，可选地挂接 core 的 CDP Accountant
│       │   ├── 📁 applications/               # 端到端 LDP 应用（pipeline），封装 encoder+mechanism+aggregator
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 base.py                 # BaseLDPApplication 抽象基类
│       │   │   ├── 📄 heavy_hitters.py        # Heavy hitters（频繁项）检测
│       │   │   ├── 📄 frequency_estimation.py # 泛频率估计（可作为 heavy_hitters 的基础）
│       │   │   ├── 📄 range_queries.py        # 区间查询（数值型 LDP）
│       │   │   ├── 📄 marginals.py            # 多维边际估计（配合 encoders + aggregators）
│       │   │   ├── 📄 key_value.py            # key-value 遥测（典型 telemetry 场景）
│       │   │   ├── 📄 sequence_analysis.py    # 序列/事件流分析（如点击序列）
│       │   │   └── 📄 application_factory.py  # 应用工厂:根据配置组装 pipeline（client/report/server）
│       │   └── 📄 __init__.py
│       └── 📄 __init__.py
├── 📁 tests/                          # 综合测试模块
│   ├── 📁 unit/                       # 单元测试
│   │   ├── 📁 test_core/              # 核心模块测试
│   │   │   ├── 📁 test_privacy/             # 隐私抽象测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_base_mechanism.py
│   │   │   │   ├── 📄 test_privacy_accountant.py
│   │   │   │   ├── 📄 test_budget_tracker.py
│   │   │   │   ├── 📄 test_composition.py
│   │   │   │   ├── 📄 test_privacy_guarantee.py
│   │   │   │   └── 📄 test_privacy_model.py
│   │   │   ├── 📁 test_data/             # 数据抽象测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_domain.py
│   │   │   │   ├── 📄 test_dataset.py
│   │   │   │   ├── 📄 test_sensitivity.py
│   │   │   │   ├── 📄 test_statistics.py
│   │   │   │   ├── 📄 test_transformers.py
│   │   │   │   └── 📄 test_data_validation.py
│   │   │   ├── 📁 test_utils/             # 工具函数测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_math_utils.py
│   │   │   │   ├── 📄 test_random.py
│   │   │   │   ├── 📄 test_config.py
│   │   │   │   ├── 📄 test_logging.py
│   │   │   │   ├── 📄 test_serialization.py
│   │   │   │   ├── 📄 test_param_validation.py
│   │   │   │   └── 📄 test_performance.py
│   │   │   └── 📄 __init__.py
│   │   ├── 📁 test_cdp/               # CDP模块测试
│   │   │   ├── 📁 test_mechanisms/    # CDP机制测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_laplace.py
│   │   │   │   ├── 📄 test_gaussian.py
│   │   │   │   ├── 📄 test_exponential.py
│   │   │   │   ├── 📄 test_staircase.py
│   │   │   │   ├── 📄 test_vector.py
│   │   │   │   ├── 📄 test_geometric.py
│   │   │   │   └── 📄 test_mechanism_factory_registry.py
│   │   │   ├── 📁 test_composition/   # CDP组合测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_basic.py
│   │   │   │   ├── 📄 test_advanced.py
│   │   │   │   └── 📄 test_moment_accounting.py
│   │   │   ├── 📁 test_ml/            # CDP机器学习测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_dp_sgd.py
│   │   │   │   ├── 📄 test_linear_models.py
│   │   │   │   ├── 📄 test_neural_networks.py
│   │   │   │   └── 📄 test_model_evaluation.py
│   │   │   ├── 📁 test_analytics/     # CDP分析测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_queries.py
│   │   │   │   ├── 📄 test_query_engine.py
│   │   │   │   ├── 📄 test_base_generator.py
│   │   │   │   ├── 📄 test_synthetic_methods.py
│   │   │   │   └── 📄 test_reporting.py
│   │   │   └── 📄 __init__.py
│   │   ├── 📁 test_ldp/               # LDP模块测试
│   │   │   ├── 📄 test_types.py       # LDPReport / Estimate 等 dataclass 的基本行为
│   │   │   ├── 📁 test_mechanisms/    # LDP机制测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_grr.py
│   │   │   │   ├── 📄 test_oue.py
│   │   │   │   ├── 📄 test_olh.py
│   │   │   │   ├── 📄 test_rappor.py
│   │   │   │   ├── 📄 test_unary_randomizer.py
│   │   │   │   └── 📄 test_continuous_mechanisms.py    # 聚合 continuous 下的 duchi/piecewise/laplace_local/gaussian_local 的基础性质测试
│   │   │   ├── 📁 test_encoders/      # LDP编码器测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_categorical_encoder.py
│   │   │   │   ├── 📄 test_numerical_encoder.py
│   │   │   │   ├── 📄 test_unary_encoder.py 
│   │   │   │   ├── 📄 test_bloom_filter_encoder.py 
│   │   │   │   ├── 📄 test_hashing_encoder.py
│   │   │   │   └── 📄 test_sketch_encoder.py
│   │   │   ├── 📁 test_aggregators/   # LDP聚合器测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_frequency_aggregator.py
│   │   │   │   ├── 📄 test_mean_aggregator.py
│   │   │   │   ├── 📄 test_variance_aggregator.py
│   │   │   │   ├── 📄 test_quantile_aggregator.py
│   │   │   │   ├── 📄 test_user_level_aggregator.py   # user_level 的逻辑：按 user_id 合并多轮报告
│   │   │   │   └── 📄 test_consistency_aggregator.py
│   │   │   ├── 📁 test_composition/
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_compose.py
│   │   │   │   └── 📄 test_privacy_accountant.py
│   │   │   ├── 📁 test_applications/  # LDP应用测试
│   │   │   │   ├── 📄 __init__.py
│   │   │   │   ├── 📄 test_heavy_hitters.py
│   │   │   │   ├── 📄 test_frequency_estimation.py
│   │   │   │   ├── 📄 test_range_queries.py
│   │   │   │   ├── 📄 test_marginals.py
│   │   │   │   ├── 📄 test_key_value.py
│   │   │   │   └── 📄 test_sequence_analysis.py
│   │   │   └── 📄 __init__.py
│   │   └── 📄 __init__.py
│   ├── 📁 integration/                # 集成测试
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_cdp_pipeline.py    # CDP流水线测试
│   │   ├── 📄 test_ldp_pipeline.py    # LDP流水线测试
│   │   ├── 📄 test_cross_module.py    # 跨模块集成测试
│   │   ├── 📄 test_data_flow.py       # 数据流测试
│   │   └── 📄 test_privacy_accounting.py # 隐私会计集成测试
│   ├── 📁 property_based/             # 属性测试
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_dp_properties.py   # 差分隐私属性测试
│   │   ├── 📄 test_composition_properties.py # 组合属性测试
│   │   ├── 📄 test_mechanism_properties.py # 机制属性测试
│   │   └── 📄 test_accuracy_properties.py # 准确性属性测试
│   ├── 📁 performance/                # 性能测试
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_mechanism_performance.py # 机制性能测试
│   │   ├── 📄 test_composition_performance.py # 组合性能测试
│   │   ├── 📄 test_ml_performance.py  # 机器学习性能测试
│   │   ├── 📄 test_ldp_performance.py # LDP性能测试
│   │   └── 📄 benchmark_utils.py      # 性能测试工具
│   ├── 📁 accuracy/                   # 准确性测试
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_mechanism_accuracy.py # 机制准确性测试
│   │   ├── 📄 test_bias_variance.py   # 偏差方差测试
│   │   ├── 📄 test_utility_analysis.py # 效用分析测试
│   │   └── 📄 accuracy_utils.py       # 准确性测试工具
│   ├── 📁 fixtures/                   # 测试夹具
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_data.py            # 测试数据生成
│   │   ├── 📄 mock_objects.py         # 模拟对象
│   │   ├── 📄 privacy_configs.py      # 隐私配置夹具
│   │   └── 📄 mechanism_fixtures.py   # 机制夹具
│   ├── 📁 regression/                 # 回归测试
│   │   ├── 📄 __init__.py
│   │   ├── 📄 test_regression_cdp.py  # CDP回归测试
│   │   ├── 📄 test_regression_ldp.py  # LDP回归测试
│   │   └── 📄 test_bug_fixes.py       # Bug修复测试
│   └── 📄 conftest.py                 # pytest配置
├── 📁 examples/                       # 使用示例
│   ├── 📁 basic/                      # 基础示例
│   │   ├── 📄 __init__.py
│   │   ├── 📄 basic_queries.py        # 基础查询示例
│   │   ├── 📄 mechanism_demo.py       # 机制演示
│   │   ├── 📄 composition_demo.py     # 组合演示
│   │   └── 📄 privacy_accounting_demo.py # 隐私会计演示
│   ├── 📁 cdp_examples/               # CDP示例
│   │   ├── 📄 __init__.py
│   │   ├── 📄 cdp_mechanisms.py       # CDP机制使用
│   │   ├── 📄 cdp_ml_training.py      # CDP机器学习
│   │   ├── 📄 cdp_data_analysis.py    # CDP数据分析
│   │   └── 📄 cdp_synthetic_data.py   # CDP合成数据
│   ├── 📁 ldp_examples/               # LDP示例
│   │   ├── 📄 __init__.py
│   │   ├── 📄 ldp_frequency_estimation.py # LDP频率估计
│   │   ├── 📄 ldp_mean_estimation.py  # LDP均值估计
│   │   ├── 📄 ldp_heavy_hitters.py    # LDP频繁项发现
│   │   └── 📄 ldp_applications.py     # LDP应用场景
│   └── 📁 advanced/                   # 高级示例
│       ├── 📄 __init__.py
│       ├── 📄 custom_mechanisms.py    # 自定义机制
│       ├── 📄 performance_tuning.py   # 性能调优
│       └── 📄 real_world_scenarios.py # 真实世界场景
├── 📁 benchmarks/                     # 基准测试
│   ├── 📁 performance/                # 性能基准
│   │   ├── 📄 __init__.py
│   │   ├── 📄 benchmark_mechanisms.py # 机制性能基准
│   │   ├── 📄 benchmark_composition.py # 组合性能基准
│   │   ├── 📄 benchmark_ml.py         # 机器学习基准
│   │   ├── 📄 benchmark_ldp.py        # LDP性能基准
│   │   └── 📄 benchmark_utils.py      # 基准测试工具
│   ├── 📁 accuracy/                   # 准确性基准
│   │   ├── 📄 __init__.py
│   │   ├── 📄 accuracy_mechanisms.py  # 机制准确性基准
│   │   ├── 📄 accuracy_composition.py # 组合准确性基准
│   │   ├── 📄 accuracy_ml.py          # 机器学习准确性基准
│   │   └── 📄 accuracy_ldp.py         # LDP准确性基准
│   ├── 📁 scalability/                # 可扩展性基准
│   │   ├── 📄 __init__.py
│   │   ├── 📄 scalability_mechanisms.py # 机制可扩展性
│   │   ├── 📄 scalability_ml.py       # 机器学习可扩展性
│   │   └── 📄 scalability_ldp.py      # LDP可扩展性
│   └── 📄 run_benchmarks.py           # 运行基准测试
├── 📁 notebooks/                      # Jupyter笔记本
│   ├── 📁 tutorials/                  # 教程笔记本
│   │   ├── 📄 01_getting_started.ipynb           # 入门指南
│   │   ├── 📄 02_cdp_mechanisms.ipynb            # CDP机制
│   │   ├── 📄 03_ldp_mechanisms.ipynb            # LDP机制
│   │   ├── 📄 04_privacy_accounting.ipynb        # 隐私会计
│   │   ├── 📄 05_dp_machine_learning.ipynb       # 差分隐私机器学习
│   │   └── 📄 06_advanced_topics.ipynb           # 高级主题
│   ├── 📁 demonstrations/             # 演示笔记本
│   │   ├── 📄 real_world_examples.ipynb          # 真实世界示例
│   │   ├── 📄 privacy_utility_tradeoff.ipynb     # 隐私效用权衡
│   │   └── 📄 performance_comparison.ipynb       # 性能比较
│   └── 📁 research/                   # 研究笔记本
│       ├── 📄 algorithm_comparison.ipynb         # 算法比较
│       ├── 📄 novel_mechanisms.ipynb             # 新机制研究
│       └── 📄 privacy_analysis.ipynb             # 隐私分析
├── 📄 .gitignore
├── 📄 LICENSE
├── 📄 MANIFEST.in
├── 📄 pyproject.toml
├── 📄 README.md
└── 📄 setup.cfg
```
---
## **目录状态追踪（与 `project_plan.md`、`development_flow.md` 对齐）**

下表仅覆盖需要立即关注的目录/文件。对于 **✅ 已完成** 的条目，记录了已经交付的能力；对于 **🟡 进行中** 与 **⚪ 待启动** 的条目，则列出了仍需落地的具体操作，方便在 code review 或项目例会上快速定位责任人与动作。

### Stage 1 · `core/`

| 目录/文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/dplib/core/privacy/` | ✅ 已完成 | 已实现：`base_mechanism.py`、`privacy_accountant.py`、`budget_tracker.py`、`composition.py`、`privacy_model.py`、`privacy_guarantee.py`，并在 `__init__.py` 中统一导出；测试覆盖 `tests/unit/test_core/test_privacy/test_{base_mechanism,privacy_accountant,budget_tracker,composition,privacy_model,privacy_guarantee}.py`。 |
| `src/dplib/core/data/` | ✅ 已完成 | 已实现：`domain.py`/`dataset.py`/`transformers.py`/`data_validation.py`/`statistics.py`/`sensitivity.py` 及 `__init__.py`，提供域定义、数据集封装、裁剪流水线、Schema 校验与敏感度估计；测试拆分到 `tests/unit/test_core/test_data/test_{domain,dataset,transformers,data_validation,statistics,sensitivity}.py`。 |
| `src/dplib/core/utils/` | ✅ 已完成 | 已实现：`math_utils.py`、`random.py`、`config.py`、`serialization.py`、`logging.py`、`param_validation.py`、`performance.py` 并在 `__init__.py` 中导出；对应单测位于 `tests/unit/test_core/test_utils/test_{math_utils,random,config,serialization,logging,param_validation,performance}.py`。 |

### Stage 2 · `cdp/`

| 目录/文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/dplib/cdp/mechanisms/` | ✅ 已完成 | 已实现：`laplace.py`、`gaussian.py`、`exponential.py`、`geometric.py`、`staircase.py`、`vector.py` 以及 `mechanism_{factory,registry}.py`，均复用 `BaseMechanism` 校准生命周期；测试覆盖 `tests/unit/test_cdp/test_mechanisms/test_{laplace,gaussian,exponential,geometric,staircase,vector}.py` 及 factory/registry UT。 |
| `src/dplib/cdp/composition/` | ✅ 已完成 | `basic.py`、`advanced.py` 提供顺序/高级组合实现并输出 `CompositionResult`，配套 `tests/unit/test_cdp/test_composition/test_{basic,advanced}.py` 已验证在多事件输入上与 `PrivacyAccountant` 的互操作。 |
| `src/dplib/cdp/analytics/queries/` | ✅ 已完成 | 已实现：`count.py`、`sum.py`、`mean.py`、`variance.py`、`histogram.py`、`range.py`、`query_engine.py`，覆盖计数/求和/均值/方差/直方图/区间（sum/count/mean）查询与统一入口；测试覆盖 `tests/unit/test_cdp/test_analytics/test_queries.py`、`test_query_engine.py`。 |
| `src/dplib/cdp/analytics/synthetic_data/` | ✅ 已完成 | 实现生成器抽象及方法：`base_generator.py`、`marginal.py`、`bayesian.py`、`gan.py`、`copula.py`，支持可配置 fit/sample 与工厂构造；测试覆盖 `tests/unit/test_cdp/test_analytics/test_base_generator.py`、`test_synthetic_methods.py`。 |
| `src/dplib/cdp/analytics/reporting/` | ✅ 已完成 | 实现隐私/效用报告：`__init__.py`、`privacy_report.py`、`utility_report.py`，提供事件聚合、时间线/曲线生成与序列化；测试覆盖 `tests/unit/test_cdp/test_analytics/test_reporting.py`。 |
| `src/dplib/cdp/ml/` | ⚪ 待启动 | 仅有 `__init__.py`。需实现 DP-SGD 训练器、线性/神经网络示例、模型评估与高阶 API，确保可被 Stage 5 集成测试复用。 |
| `src/dplib/cdp/sensitivity/` | ✅ 已完成 | 已实现：`global_sensitivity.py`（sum/mean/variance/histogram/range）、`sensitivity_bounds.py`（上下界/metric 支持）、`sensitivity_analyzer.py`（分析分发）、`noise_calibrator.py` 及 `__init__.py` 导出；测试覆盖 `tests/unit/test_cdp/test_sensitivity/test_{global_sensitivity,noise_calibrator,sensitivity_bounds,sensitivity_analyzer}.py`。 |

### Stage 3 · `ldp/`

| 目录/文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/dplib/ldp/mechanisms/` | 🟡 进行中 | 已实现离散/连续机制全量（`grr`/`oue`/`olh`/`rappor`/`unary_randomizer` + `laplace_local`/`gaussian_local`/`piecewise`/`duchi`）及 registry/factory，配套 UT `tests/unit/test_ldp/test_mechanisms/test_{grr,oue,olh,rappor,unary_randomizer,continuous_mechanisms}.py`。 |
| `src/dplib/ldp/encoders/` | ✅ 已完成 | 已实现 base/categorical/numerical（均匀分桶，分位数留 TODO）/unary+binary/hashing/bloom_filter/sketch（简化占位）与 encoder_factory；UT 位于 `tests/unit/test_ldp/test_encoders/test_{categorical,numerical,hashing,sketch,bloom_filter,unary}_encoder.py`。 |
| `src/dplib/ldp/aggregators/` | ✅ 已完成 | 已实现 frequency/mean/variance/quantile/user_level/consistency 与 aggregator_factory；frequency 支持 GRR 去偏与 bit 向量均值/去偏（p/q 可用时），consistency 覆盖非负裁剪/归一化/单调约束/simplex 投影，variance 支持噪声方差扣除，quantile 提供 Laplace/Gaussian 校正的可选分支；UT 位于 `tests/unit/test_ldp/test_aggregators/test_{frequency,mean,variance,quantile,user_level,consistency}_aggregator.py`。 |
| `src/dplib/ldp/applications/` | ✅ 已完成 | 已实现 BaseLDPApplication、heavy_hitters/frequency_estimation/range_queries/marginals/key_value/sequence_analysis 与 application_factory，并补齐对应单元测试 `tests/unit/test_ldp/test_applications/test_*.py`。 |
| `src/dplib/ldp/composition/` | ✅ 已完成 | 已落地 compose、ldp_cdp_mapping、privacy_accountant，提供 per-user 组合入口与 LDP→CDP 映射策略。 |

### Stage 5 · `tests/`

| 目录/文件 | 状态 | 说明 |
| --- | --- | --- |
| `tests/unit/test_core/` | 🟡 进行中 | 已实现：`test_privacy/test_{base_mechanism,privacy_accountant,budget_tracker,composition,privacy_model,privacy_guarantee}.py`、`test_data/test_{domain,dataset,transformers,data_validation,statistics,sensitivity}.py`、`test_utils/test_{math_utils,random,config,serialization,logging,performance,param_validation}.py` 覆盖核心机制、预算器、数据层与工具链。待补：统一 fixture 及类型格式化检查。 |
| `tests/unit/test_cdp/` | 🟡 进行中 | 已实现机制/组合/analytics/sensitivity UT：`test_mechanisms/test_{laplace,gaussian,exponential,geometric,staircase,vector}.py`、`test_mechanism_factory_registry.py`、`test_composition/test_{basic,advanced,budget_scheduler,privacy_accountant,moment_accountant}.py`、`test_analytics/test_{queries,query_engine,base_generator,synthetic_methods,reporting}.py`、`test_sensitivity/test_{global_sensitivity,noise_calibrator,sensitivity_bounds,sensitivity_analyzer}.py`；待补 ML 与高维数据集案例。 |
| `tests/unit/test_ldp/` | 🟡 进行中 | 已覆盖 types/机制（离散+连续）/编码器/聚合器/组合/应用 UT，见 `tests/unit/test_ldp/test_{types,composition/*,applications/*,mechanisms/*,encoders/*,aggregators/*}.py`；集成/性能仍待补。 |
| `tests/integration/` | ⚪ 待启动 | 仅有空目录。需实现 `test_{cdp,ldp}_pipeline.py`、`test_cross_module.py`、`test_data_flow.py`、`test_privacy_accounting.py`，覆盖从数据→机制→记账的全链路。 |
| `tests/property_based/` | ⚪ 待启动 | 仅有空目录。需按规划创建 `test_dp_properties.py`、`test_composition_properties.py` 等 Hypothesis 用例，校验极端参数组合。 |
| `tests/performance/` | ⚪ 待启动 | 仅有空目录。需补充 `test_mechanism_performance.py`、`test_composition_performance.py`、`test_ml_performance.py`、`test_ldp_performance.py` 及 `benchmark_utils.py`。 |
| `tests/accuracy/` | ⚪ 待启动 | 仅有空目录。需补 `test_mechanism_accuracy.py`、`test_bias_variance.py`、`test_utility_analysis.py` 等，用于跟踪实际误差。 |
| `tests/fixtures/` | ⚪ 待启动 | 仅有 `__init__.py`。需沉淀 `test_data.py`、`mock_objects.py`、`privacy_configs.py`、`mechanism_fixtures.py` 以支持其他测试目录。 |
| `tests/regression/` | ⚪ 待启动 | 名称与规划的 `tests/regression/` 不一致且仅有 `__init__.py`。需重命名目录并补充 `test_regression_{cdp,ldp}.py`、`test_bug_fixes.py` 防回归。 |

### Stage 6 · 文档、示例与资产

| 目录/文件 | 状态 | 说明 |
| --- | --- | --- |
| `docs/development/*.md` | ✅ 已完成 | `requirements.md`、`architecture.md`、`tech_stack.md`、`project_plan.md`、`development_flow.md` 与当前文件均已同步最新架构/流程约束，可直接作为评审依据。 |
| `docs/development/contributing.rst` & `docs/development/testing.rst` | ⚪ 待启动 | 文件尚未创建；需将 README 中的贡献规范、代码风格、CI 要求迁移为 Sphinx 章节以便发布到 ReadTheDocs。 |
| `docs/index.rst` & `docs/conf.py` | 🟡 进行中 | 文件存在但为空。需补充 toctree、项目 metadata、主题/扩展配置，以及 `myst_parser`/`autodoc` 设置以纳入 Markdown 与 API 文档。 |
| `docs/api/` | ⚪ 待启动 | 目录为空。应新建 `core.rst`、`cdp.rst`、`ldp.rst` 与 `index.rst`，并配置 `autosummary`/`autodoc`。 |
| `docs/examples/` & `docs/theory/` | ⚪ 待启动 | 两个目录均无文件。需根据目录树创建 `basic.rst`、`cdp.rst`、`ldp.rst`、`dp_basics.rst`、`mechanisms.rst` 等内容。 |
| `docs/_static/` | ⚪ 待启动 | 目录为空；需补 `custom.css` 与 `logo.png`，并在 `conf.py` 中引用。 |
| `docs/Makefile` & `docs/requirements-docs.txt` | ⚪ 待启动 | 文件未创建；需提供 `make html`/`make linkcheck` 入口与文档构建依赖说明。 |
| `README.md` | 🟡 进行中 | 已包含项目概述与安装指引，但缺少贡献流程、分支策略与链接到 `docs/development` 资料；需按 Stage 0 要求补全。 |
| `examples/` | ⚪ 待启动 | 目录为空。需实现 `basic/`、`cdp_examples/`、`ldp_examples/`、`advanced/` 下的脚本，并同步到文档示例章节。 |
| `benchmarks/` | ⚪ 待启动 | 仅存在空 `__init__.py`。需落地 `performance/`、`accuracy/`、`scalability/` 下的 benchmark_* 模块与 `run_benchmarks.py`。 |
| `notebooks/` | ⚪ 待启动 | 目录为空；需创建教程、演示与研究类 Jupyter Notebook（01~06 + demonstrations + research）并在 README/文档中挂载。 |
