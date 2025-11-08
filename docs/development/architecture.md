# **NSSDPlib结构设计**
---
## **🎯 总体分层架构图**
```mermaid
graph TD

%% ─────────────── 根目录 ───────────────
A["dplib/<br>统一差分隐私库"]

%% ─────────────── 一级模块 ───────────────
A --> D1["docs/<br>文档模块"]
A --> C1["core/<br>核心框架"]
A --> C2["cdp/<br>中心化差分隐私模块"]
A --> C3["ldp/<br>本地差分隐私模块"]
A --> T1["tests/<br>测试模块"]
A --> E1["examples/<br>使用示例"]
A --> B1["benchmarks/<br>基准测试"]
A --> N1["notebooks/<br>Jupyter笔记本"]

%% ─────────────── docs（二级） ───────────────
D1 --> D1_1["api/<br>API参考"]
D1 --> D1_2["examples/<br>示例文档"]
D1 --> D1_3["theory/<br>理论背景"]
D1 --> D1_4["development/<br>开发文档"]
D1 --> D1_5["_static/<br>静态资源"]

%% ─────────────── core（二级） ───────────────
C1 --> C1_1["privacy/<br>隐私抽象层"]
C1 --> C1_2["data/<br>数据抽象层"]
C1 --> C1_3["utils/<br>共享工具库"]

%% ─────────────── cdp（二级） ───────────────
C2 --> C2_1["mechanisms/<br>机制实现"]
C2 --> C2_2["composition/<br>组合定理"]
C2 --> C2_3["sensitivity/<br>敏感度分析"]
C2 --> C2_4["ml/<br>机器学习"]
C2 --> C2_5["analytics/<br>分析工具"]

%% ─────────────── ldp（二级） ───────────────
C3 --> C3_1["mechanisms/<br>LDP机制"]
C3 --> C3_2["encoders/<br>编码器"]
C3 --> C3_3["aggregators/<br>聚合器"]
C3 --> C3_4["composition/<br>组合机制"]
C3 --> C3_5["applications/<br>应用场景"]

%% ─────────────── tests（二级） ───────────────
T1 --> T1_1["unit/<br>单元测试"]
T1 --> T1_2["integration/<br>集成测试"]
T1 --> T1_3["property_based/<br>属性测试"]
T1 --> T1_4["performance/<br>性能测试"]
T1 --> T1_5["accuracy/<br>准确性测试"]
T1 --> T1_6["fixtures/<br>测试夹具"]
T1 --> T1_7["regression/<br>回归测试"]

%% ─────────────── examples（二级） ───────────────
E1 --> E1_1["basic/<br>基础示例"]
E1 --> E1_2["cdp_examples/<br>CDP示例"]
E1 --> E1_3["ldp_examples/<br>LDP示例"]
E1 --> E1_4["advanced/<br>高级示例"]

%% ─────────────── benchmarks（二级） ───────────────
B1 --> B1_1["performance/<br>性能基准"]
B1 --> B1_2["accuracy/<br>准确性基准"]
B1 --> B1_3["scalability/<br>可扩展性基准"]

%% ─────────────── notebooks（二级） ───────────────
N1 --> N1_1["tutorials/<br>教程笔记本"]
N1 --> N1_2["demonstrations/<br>演示笔记本"]
N1 --> N1_3["research/<br>研究笔记本"]

%% ─────────────── 样式定义 ───────────────
style A fill:#2E86C1,stroke:#1B4F72,color:#fff

%% docs
style D1 fill:#5DADE2,stroke:#2E86C1
style D1_1 fill:#5DADE2,stroke:#2E86C1
style D1_2 fill:#5DADE2,stroke:#2E86C1
style D1_3 fill:#5DADE2,stroke:#2E86C1
style D1_4 fill:#5DADE2,stroke:#2E86C1
style D1_5 fill:#5DADE2,stroke:#2E86C1

%% core
style C1 fill:#58D68D,stroke:#1E8449
style C1_1 fill:#58D68D,stroke:#1E8449
style C1_2 fill:#58D68D,stroke:#1E8449
style C1_3 fill:#58D68D,stroke:#1E8449

%% cdp
style C2 fill:#F5B041,stroke:#B9770E
style C2_1 fill:#F5B041,stroke:#B9770E
style C2_2 fill:#F5B041,stroke:#B9770E
style C2_3 fill:#F5B041,stroke:#B9770E
style C2_4 fill:#F5B041,stroke:#B9770E
style C2_5 fill:#F5B041,stroke:#B9770E

%% ldp
style C3 fill:#F1948A,stroke:#922B21
style C3_1 fill:#F1948A,stroke:#922B21
style C3_2 fill:#F1948A,stroke:#922B21
style C3_3 fill:#F1948A,stroke:#922B21
style C3_4 fill:#F1948A,stroke:#922B21
style C3_5 fill:#F1948A,stroke:#922B21

%% tests
style T1 fill:#BB8FCE,stroke:#633974
style T1_1 fill:#BB8FCE,stroke:#633974
style T1_2 fill:#BB8FCE,stroke:#633974
style T1_3 fill:#BB8FCE,stroke:#633974
style T1_4 fill:#BB8FCE,stroke:#633974
style T1_5 fill:#BB8FCE,stroke:#633974
style T1_6 fill:#BB8FCE,stroke:#633974
style T1_7 fill:#BB8FCE,stroke:#633974

%% examples
style E1 fill:#F7DC6F,stroke:#B7950B
style E1_1 fill:#F7DC6F,stroke:#B7950B
style E1_2 fill:#F7DC6F,stroke:#B7950B
style E1_3 fill:#F7DC6F,stroke:#B7950B
style E1_4 fill:#F7DC6F,stroke:#B7950B

%% benchmarks
style B1 fill:#85C1E9,stroke:#2874A6
style B1_1 fill:#85C1E9,stroke:#2874A6
style B1_2 fill:#85C1E9,stroke:#2874A6
style B1_3 fill:#85C1E9,stroke:#2874A6

%% notebooks
style N1 fill:#7FB3D5,stroke:#1F618D
style N1_1 fill:#7FB3D5,stroke:#1F618D
style N1_2 fill:#7FB3D5,stroke:#1F618D
style N1_3 fill:#7FB3D5,stroke:#1F618D
```

---

## **🧭 模块概览**

| **🧩模块/**             | **核心职责**                     |
| :---------------- | :------------------------------ |
| **`📘docs/`**       | 提供完整的项目文档、API参考、理论说明与开发指南。      |
| **`⚙️core/`**       | 定义通用抽象层与工具函数，是 CDP 与 LDP 的共同基础。 |
| **`🔵cdp/`**        | 实现中心化差分隐私算法与机制，用于可信服务器端的数据保护。   |
| **`🟢ldp/`**        | 实现本地差分隐私算法与应用，使用户数据在上传前即被保护。    |
| **`🧪tests/`**      | 提供全面的单元、集成与性能测试，保障库的稳定与正确性。     |
| **`💡examples/`**   | 包含从入门到高级的使用示例，展示典型差分隐私应用。       |
| **`📊benchmarks/`** | 评估不同机制在性能、准确性和可扩展性方面的表现。        |
| **`📓notebooks/`**  | 提供交互式 Jupyter 笔记本，用于实验、教学与算法演示。 |
| **`🧬hybrid/`**     | 混合模式（待扩展）                |

---

## **🔄 模块边界与依赖关系**

```mermaid
graph TD
    %% 定义子图和节点
    subgraph core[core 核心层]
        direction TB
        privacy["privacy<br/>差分隐私基础"]
        data["data<br/>数据处理"]
        utils["utils<br/>通用工具"]
        
        %% core 内部依赖
        privacy --> utils
        data --> utils
    end

    subgraph cdp[cdp 中心化差分隐私]
        direction TB
        cdp_mech["mechanisms<br/>隐私机制"]
        cdp_comp["composition<br/>组合规则"]
        cdp_sens["sensitivity<br/>敏感度分析"]
        cdp_ml["ml<br/>机器学习"]
        cdp_ana["analytics<br/>分析工具"]

        %% cdp 内部依赖
        cdp_mech --> cdp_comp
        cdp_ml --> cdp_mech
        cdp_ml --> cdp_ana
        cdp_ana --> cdp_mech
        cdp_sens --> cdp_mech
    end

    subgraph ldp[ldp 本地差分隐私]
        direction TB
        ldp_mech["mechanisms<br/>隐私机制"]
        ldp_enc["encoders<br/>编码器"]
        ldp_agg["aggregators<br/>聚合器"]
        ldp_app["applications<br/>应用场景"]
        ldp_comp["composition<br/>组合规则"]

        %% ldp 内部依赖
        ldp_mech --> ldp_comp
        ldp_app --> ldp_mech
        ldp_app --> ldp_enc
        ldp_agg --> ldp_mech
        ldp_agg --> ldp_enc
    end

    %% 跨模块依赖关系
    cdp_mech --> privacy
    cdp_ml --> data
    cdp_ana --> data
    
    ldp_mech --> privacy
    ldp_app --> data
    ldp_agg --> data

    %% 样式设置
    classDef coreStyle fill:#58D68D,stroke:#1E8449,color:#333
    classDef cdpStyle fill:#F5B041,stroke:#B9770E,color:#333
    classDef ldpStyle fill:#F1948A,stroke:#922B21,color:#333
    
    class privacy,data,utils coreStyle
    class cdp_mech,cdp_comp,cdp_sens,cdp_ml,cdp_ana cdpStyle
    class ldp_mech,ldp_enc,ldp_agg,ldp_app,ldp_comp ldpStyle
```

### **📝 依赖规则说明**

1. **层次依赖原则**
   - core 层为基础设施，不依赖其他模块
   - cdp 和 ldp 可依赖 core 层组件
   - cdp 和 ldp 之间禁止直接依赖

2. **模块内部规则**
   - mechanisms 为基础组件，其他组件可以依赖它
   - composition 被 mechanisms 使用，处理隐私预算
   - analytics/ml 可以使用 mechanisms 实现分析功能
   - applications 可以使用本模块内的所有组件

3. **数据流原则**
   - 所有数据处理优先通过 core.data 提供的接口
   - 避免在 cdp/ldp 中重复实现数据处理逻辑
   - 确保数据转换的一致性和可追踪性

4. **工具使用原则**
   - 通用工具函数统一放在 core.utils
   - 特定领域工具放在对应模块中
   - 避免跨模块调用工具函数

### **🔭 设计目标**

1. **可扩展性**
   - 新机制通过继承 BaseMechanism 轻松添加
   - 新的分析方法可在各自模块中独立开发
   - 支持在不修改核心代码的情况下扩展功能

2. **模块化**
   - 每个子模块职责单一明确
   - 依赖关系清晰，避免循环依赖
   - 便于单元测试和集成测试

3. **可维护性**
   - 清晰的层次结构
   - 最小化跨模块依赖
   - 统一的接口设计
---

## **🔄 数据流与API调用序列**

### **1. CDP模式数据流**

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant Server as 服务端(CDP)
    participant DB as 数据库
    
    %% 初始化阶段
    Note over Server: 初始化CDP机制
    Server->>Server: 配置 ε, δ
    Server->>Server: 初始化LaplaceMechanism/GaussianMechanism
    
    %% 数据收集与处理
    Client->>Server: 发送原始数据
    activate Server
    Server->>DB: 存储原始数据
    Server->>Server: 计算查询敏感度
    Server->>Server: 校准隐私机制
    deactivate Server
    
    %% 查询处理
    Client->>+Server: 发送分析查询请求
    Server->>DB: 执行原始查询
    DB-->>Server: 返回查询结果
    Server->>Server: 添加差分隐私噪声
    Server-->>-Client: 返回隐私保护结果
    
    %% 隐私预算跟踪
    Server->>Server: 更新隐私预算支出
    
    Note over Client,Server: 重复查询直到预算耗尽
```

### **2. LDP模式数据流**

```mermaid
sequenceDiagram
    participant Client as 客户端(LDP)
    participant Server as 聚合服务器
    participant DB as 数据库
    
    %% 初始化阶段
    Note over Client: 初始化LDP机制
    Client->>Client: 配置 ε
    Client->>Client: 初始化编码器与隐私机制
    
    %% 本地数据处理
    Client->>Client: 准备原始数据
    Client->>Client: 编码数据
    Client->>Client: 添加LDP噪声
    
    %% 数据上传
    Client->>+Server: 发送隐私处理后的数据
    Server->>DB: 存储加噪数据
    DB-->>Server: 确认存储
    Server-->>-Client: 确认接收
    
    %% 聚合分析
    Note over Server: 聚合阶段
    Server->>DB: 获取多用户数据
    DB-->>Server: 返回加噪数据
    Server->>Server: 执行无偏估计
    Server->>Server: 计算聚合统计
    
    %% 结果获取
    Client->>+Server: 请求分析结果
    Server-->>-Client: 返回聚合结果
```

### **3. API调用流程**

```mermaid
sequenceDiagram
    participant App as 应用层
    participant Core as Core模块
    participant CDP as CDP模块
    participant LDP as LDP模块
    participant Utils as 工具模块
    
    %% 初始化
    App->>Core: 创建隐私上下文
    Core->>Core: 验证参数
    
    %% CDP路径
    alt CDP模式
        App->>CDP: 创建CDP机制实例
        CDP->>Core: 继承基础机制
        CDP->>CDP: 配置隐私参数
        App->>CDP: 调用randomise()
        CDP->>Utils: 使用工具函数
        CDP-->>App: 返回加噪结果
    
    %% LDP路径
    else LDP模式
        App->>LDP: 创建LDP机制实例
        LDP->>Core: 继承基础机制
        LDP->>LDP: 设置编码器
        App->>LDP: 调用encode()
        LDP->>LDP: 编码数据
        App->>LDP: 调用randomise()
        LDP->>Utils: 使用工具函数
        LDP-->>App: 返回本地处理结果
    end
    
    %% 资源释放
    App->>Core: 清理资源
```

### **📝 关键交互说明**

1. **CDP模式特点**
   - 原始数据集中存储在服务端
   - 查询时进行差分隐私保护
   - 集中跟踪隐私预算消耗
   - 支持复杂查询和机器学习任务

2. **LDP模式特点**
   - 数据在本地完成隐私处理
   - 服务端只接收隐私保护后的数据
   - 分布式隐私预算管理
   - 适合大规模数据收集场景

3. **API设计原则**
   - 统一的机制接口
   - 灵活的配置选项
   - 清晰的错误处理
   - 链式调用支持

---