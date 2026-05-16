# Knowlix 项目技术设计文档

> 版本：0.6（核心域：**词汇/词组知识图谱 + 子图学习集 + 检验闭环 + 录入相似合并**）  
> 目标：以 **Python** 实现「总知识图谱维护 → 为单次学习随机抽取规模可控子图（约 10～20 节点）→ 双模式检验更新掌握状态 → 录入时高相似项合并并累计频次以区分重点」；**唯一核心**是图谱与学习检验域；语音、出题模板、具体图算法与 UI 形态通过 **端口与适配器** 隔离，保证 **领域层不因 ASR/前端/模型厂商变化而大面积改动**。  
> 持久化：**双存储** — **Neo4j** 承载词汇总图谱（节点/边/频次）；**PostgreSQL** 承载掌握状态、会话快照、合并审计、向量与既有关系表（Alembic 迁移）。

---

## 1. 产品范围与优先级

### 1.1 核心能力（必须做对、可扩展）

| 能力 | 说明 |
|------|------|
| **总知识图谱** | 全库 **单词、词组** 为节点；边表示可学习关系（搭配、上下位、共现、翻译对等，类型可配置）；作为权威数据源演进。 |
| **子知识图谱（最小学习集）** | 从总图中按策略采样 **10～20** 个节点（可配置上下界）及其诱导子边（或扩展一跳邻居的策略二选一并文档化），解决「词量过大、全图不可学」问题。 |
| **检验模式一：用户造句** | 键盘与/或 **语音** 输入句子；系统判定是否覆盖目标词/词组；通过后更新 **掌握**，并从当前待练集合中移除（语义上「从库里移除已掌握」优先用 **状态过滤** 实现，避免物理删除丢失审计）。 |
| **检验模式二：系统出题** | 基于 **当前子图** 定制题目（选择/填空/连线等至少一种 MVP）；作答后更新掌握；已掌握项在 UI **划掉** 且后续出题降权或排除。 |
| **录入与相似合并** | 新录入与已有节点 **相似度高则合并** 到规范节点；维护 **出现/合并次数** 供排序、子图采样加权与「重点」展示。 |

### 1.2 扩展能力（非核心、插件化）

- **SRS / 间隔复习**、多端同步、开放 API、图谱可视化高级布局。  
- **人工拆分误合并**、批量导入、多租户。  

以上通过 **独立用例或应用服务** 接入，**不侵入**「图谱不变量、子图生成契约、掌握状态机」的核心聚合规则。

---

## 2. 架构原则

1. **有界上下文**：`LexiconGraph`（总图）、`LearningSession`（子图 + 会话）、`Verification`（检验与掌握）、`Ingestion`（录入与合并）职责清晰；跨上下文通过 **应用服务编排** 或 **领域事件**。  
2. **依赖倒置**：`domain/` **不依赖** Streamlit、HTTP、具体 ASR、具体 LLM SDK；只依赖 **`application/ports/` 中的 Protocol**。  
3. **用例驱动**：`application/use_cases/` 一用例一用户旅程（如 `BuildLearningSubgraph`、`SubmitUserSentence`、`GenerateSubgraphQuiz`）。  
4. **可替换基础设施**：`infrastructure/` 实现仓储、嵌入、ASR、出题 LLM；换 Web/API 只增 `interfaces/`。  
5. **子图与出题可版本化**：子图生成策略版本、出题模板版本写入元数据，便于回放与 A/B。

---

## 3. 有界上下文划分

```
┌─────────────────────────────────────────────────────────────────┐
│  LexiconGraph（总词汇知识图谱）                                    │
│  - LexemeNode（单词/词组）、LexemeEdge、规范形、别名               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Ingestion & Dedup（录入与合并）                                  │
│  - 归一化 → 相似检索 → 合并或新建 → occurrence_count 递增         │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  LearningSession（学习会话 / 子图）★ 与采样强相关                  │
│  - BuildLearningSubgraph：随机/加权/连通子图；节点数 10～20        │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌─────────────────┐   ┌──────────────────────┐
│ Verification  │   │ QuizGeneration  │   │ MasteryProjection   │
│ 造句判定        │   │ 子图驱动出题      │   │ 掌握状态与用户视图    │
└───────────────┘   └─────────────────┘   └──────────────────────┘
```

**边界规则**：  
- **总图** 拥有 `LexemeNode` / `LexemeEdge` 的生命周期与引用完整性。  
- **掌握状态** 建议建模为 **用户 × 规范节点** 的投影（或独立聚合），检验上下文 **可写** 掌握，读模型供子图采样「排除已掌握」。  
- **子图** 是会话级或快照级 DTO，不反向污染总图结构（除非显式「写回」用例，如用户编辑边）。

---

## 4. 推荐 Python 包结构（单体仓库、清晰分层）

```
knowlix/
├── pyproject.toml
├── src/
│   └── knowlix/
│       ├── domain/
│       │   ├── lexicon_graph/         # LexemeNode, LexemeEdge, 不变量
│       │   ├── learning_session/      # LearningSubgraph 值对象/实体
│       │   ├── verification/          # 掌握枚举、造句判定规则（纯逻辑部分）
│       │   └── ingestion/             # 合并决策值对象（若与图紧耦合可放 graph）
│       ├── application/
│       │   ├── ports/
│       │   └── use_cases/
│       ├── infrastructure/
│       │   ├── persistence/           # PostgreSQL：掌握、审计、向量等
│       │   ├── graph/
│       │   │   └── neo4j/             # LexiconGraphPort 实现
│       │   ├── ai/                    # 嵌入、LLM 出题、造句裁判
│       │   └── speech/                # ASR 适配器
│       └── interfaces/
│           └── streamlit/
├── tests/
└── docs/
    ├── TECHNICAL_DESIGN.md
    └── REQUIREMENTS.md
```

**规则**：`interfaces/streamlit/` **禁止** 直接 `import infrastructure`；经 **facade 用例** 或组装根注入。

---

## 5. 核心领域模型（草案）

### 5.1 聚合与实体

- **`LexemeNode`**：`id`、`kind`（word | phrase）、`canonical_text`、可选 `phonetic`/`gloss_short`、`occurrence_count`（合并与重复命中累计）、`created_at`/`updated_at`。  
- **`LexemeAlias`**（可选）：合并前的 surface form → 指向规范 `node_id`，支持检索与审计。  
- **`LexemeEdge`**：`src_id`、`dst_id`、`relation_type`、权重、元数据；删除节点时级联策略在仓储层与域规则中统一。  
- **`UserMastery`**（或 `MasteryRecord`）：`user_id`、`lexeme_node_id`、`state`（unknown | learning | mastered）、`last_verified_at`、`last_mode`（sentence | quiz）。  
- **`LearningSubgraphSnapshot`**（可选持久化）：`snapshot_id`、`node_ids[]`、`edge_ids[]`、`policy_version`、`rng_seed`、生成时间。  
- **`MergeAudit`**：候选对、相似度、算法版本、人工确认（P1）。

### 5.2 关键领域服务（无状态、可单测）

- **`CanonicalNormalizer`**：大小写、空白、全半角、可选词形归一（与产品规则一致）。  
- **`SentenceCoverageChecker`**：判定句子是否覆盖目标词/词组（**精确子串** / **分词后匹配** / **经端口 LLM 裁判** 三选一或组合；**默认 MVP**：归一化后子串 + 简单词边界规则，复杂形态走端口）。  
- **`SubgraphSampler`**：输入总图视图 + 约束（节点数上下界、排除已掌握、加权 key=`occurrence_count`），输出节点集与边集；**随机性** 通过注入 `RngPort` 或显式 seed 便于测试。

---

## 6. 端口（Ports）设计

| 端口 | 职责 |
|------|------|
| `EmbeddingPort` / `LexemeSimilarityPort` | 录入时 Top-K 相似节点分数；可 Fake 为编辑距离 + 哈希。 |
| `MergeJudgePort`（可选） | 高于阈值时 LLM/规则二次确认是否合并。 |
| `TranscriptionPort` | 语音 → 文本；领域只接收「转写文本 + 置信度 + 语言」。 |
| `SentenceJudgePort`（可选） | 造句是否合格、是否覆盖目标、语法轻量提示（**不**替代覆盖检查的硬规则时可关）。 |
| `QuizGeneratorPort` | 输入子图 DTO，输出结构化题目列表（类型、题干、选项、标答、关联 `lexeme_id`）。 |
| **`LexiconGraphPort`** | 词汇总图 CRUD、随机采样、诱导子图、前缀检索（**Neo4j 实现**）。 |
| `MasteryRepositoryPort` / `UnitOfWorkPort` | 掌握状态与关系型事务（**PostgreSQL**）。 |

**新增 Web/API**：复用相同端口，核心域零改或仅增加 `UserContext` 值对象。

---

## 7. 核心用例（应用层）

1. **`IngestLexeme`**：归一化 → 相似检索 → 合并递增 `occurrence_count` 或新建节点（可选边建议）。  
2. **`BuildLearningSubgraph`**：生成 10～20 节点的子图 DTO。  
3. **`SubmitUserSentence`**：绑定当前子图目标集合；转写（若语音）→ 覆盖检查 → 更新掌握与待练列表。  
4. **`GenerateSubgraphQuiz` / `SubmitQuizAnswers`**：出题 → 判分 → 更新掌握。  
5. **`RunLearningSession`**（编排）：生成子图 → 循环检验 → 可选刷新子图。  
6. **`ListOrSearchLexicon`**、`**MaintainEdges**`：维护总图（P0 可简化 UI）。

---

## 8. 界面层角色（Streamlit / 未来 Web）

- **薄适配器**：表单、子图列表/简图、造句框、语音按钮（调用 `TranscriptionPort`）、出题与划掉展示。  
- **不做**：相似度算法细节、SQL、直接调用第三方 SDK。  
- **会话状态**：当前 `LearningSubgraph` 与待练节点列表放在 `st.session_state` 或后端会话存储（未来 API）。

---

## 9. 技术选型与可替换方案

选型原则：**具体厂商与算法实现仅落在 `infrastructure` 与 `interfaces`**；`domain` / `application` 保持与实现无关。

### 9.1 语言、运行时与工程化

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| Python | **3.10+** | |
| 依赖管理 | **uv** 或 **Poetry** | `pip-tools` |
| 布局 | **`src/`** + `pyproject.toml` | |
| 代码质量 | **Ruff** + **mypy**（严格模式分阶段） | BasedPyright |
| 测试 | **pytest** + **pytest-cov** | **Hypothesis** 测采样与状态机 |

### 9.2 界面层

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 本地/内网 Demo UI | **Streamlit** | **Gradio** 极简原型；复杂交互 **NiceGUI** / 纯 **FastAPI + HTMX** |
| 配置 | **pydantic-settings** + 环境变量 | 密钥不入库不入域 |
| 图可视化（子图） | **Pyvis**（导出 HTML）或 **streamlit-agraph** | 大规模仅服务端生成静态图；前端重交互迁 SPA + **Cytoscape.js** / **D3** |
| 未来 Web | **FastAPI** + React/Vue | BFF 按需 |

### 9.3 持久化：双存储（Neo4j + PostgreSQL）

| 数据域 | 存储 | 说明 |
|--------|------|------|
| **词汇节点、边、occurrence_count** | **Neo4j** | 总知识图谱权威源；Cypher 做采样、诱导子图、k-hop 扩展 |
| **用户掌握、子图快照、合并审计、嵌入向量** | **PostgreSQL** | 关系型事务、Alembic 迁移、pgvector |
| **录入规则相似（前缀/编辑距离）** | Neo4j 前缀索引 + 应用层 **RapidFuzz** | 语义相似仍走 pgvector + `EmbeddingPort` |

| 类别 | 推荐 | 替代 / 备注 |
|------|------|-------------|
| 图数据库 | **Neo4j 5 Community** + 官方 **`neo4j` Python Driver** | **Memgraph**、**Neptune** 需另写 `LexiconGraphPort` 适配器 |
| 图模型 | 标签 **`Lexeme`**；关系 **`RELATES`**（属性 `relation_type`、`weight`） | 关系类型增多时可拆为多 rel type |
| Schema | 启动时 **`ensure_schema()`** 幂等约束（`id` UNIQUE、canonical 索引） | 可选 `scripts/neo4j_schema.cypher` 手工执行 |
| 连接配置 | `NEO4J_URI`（`bolt://`）、`NEO4J_USER`、`NEO4J_PASSWORD` | 本地 **`docker compose up neo4j`**；默认库无需配置 |
| 关系库 | **PostgreSQL** + **SQLAlchemy 2.0** | |
| 关系库迁移 | **Alembic** | 不含 Neo4j 图结构（图结构由 Neo4j 约束管理） |
| 模糊查重（PG 侧） | **pg_trgm** | 与 Neo4j 前缀检索互补 |
| JSON 元数据 | **JSONB**（PG） | 题目快照、子图策略参数 |

**结论（图存储）**：**Neo4j 为词汇图谱主库**；`LexiconGraphPort` 由 `Neo4jLexiconGraphRepository` 实现；子图采样优先 **Cypher + 应用层加权/随机种子**，不再以 NetworkX 全量拉取为主路径。掌握状态与子图会话元数据 **不写入 Neo4j 节点**（避免图库承担用户维度膨胀），经 PG 关联 `lexeme_id`。

### 9.4 向量、相似合并与重点权重

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 向量存 | **pgvector**（与业务同事务） | **Qdrant** / **Milvus** 独立扩缩 |
| 索引 | 数据量小 **暴力检索**；上万 **HNSW** | |
| 嵌入模型 | 云 API 经 `EmbeddingPort` | 离线 **sentence-transformers**；多语言 **BGE-M3** 等 |
| 纯规则兜底 | **RapidFuzz** / **python-Levenshtein** | 无向量时仍可合并极高相似短词 |

### 9.5 大模型与结构化出题 / 裁判

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 云 API | 官方 SDK 薄封装 | **LiteLLM** 多路由 |
| 结构化输出 | **Pydantic** + **Instructor** 或 JSON Schema tool | 出题与裁判共用模式 |
| 本地 | **Ollama** / **vLLM** | 与云端同一端口多实现 |
| 提示 | 仓库内版本化模板 + `prompt_version` 字段 | |

**注意**：`QuizGeneratorPort` 的默认实现可为 **模板化非 LLM 题目**（如从边生成连线题），LLM 为增强项，避免 MVP 强依赖模型可用性。

### 9.6 语音输入（造句模式）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 浏览器录音 | Streamlit **自定义组件** 或 **先文件上传 wav/mp3**（实现成本最低） | |
| 转写 | **OpenAI Whisper API** 或本地 **faster-whisper** | 国内云：**阿里云/讯飞** 等经 `TranscriptionPort` |
| 格式 | **ffmpeg** CLI 或 **pydub** | 统一采样率再送 ASR |

### 9.7 异步任务与调度

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 后台 | **线程池** + `queue` 或 **APScheduler** | 批量重算嵌入 |
| 扩展 | **Celery + Redis** | **Arq**（async） |

### 9.8 可观测性、安全

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 日志 | **structlog**（JSON） | 敏感字段脱敏在 infrastructure |
| 密钥 | **pydantic-settings** | |
| 依赖审计 | **pip-audit** / **uv audit** | CI |

### 9.9 容器与部署（可选）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 编排 | **docker compose**：**PostgreSQL** + **Neo4j** + App | 可选 **Qdrant** |
| 反向代理 | **Caddy** / **Nginx** | TLS 终止 |

### 9.10 依赖注入与组装根

| 类别 | 推荐 | 备注 |
|------|------|------|
| MVP | `interfaces/streamlit/app.py` 手工组装 | 显式、易调试 |
| 规模化 | **dependency-injector** / **lagom** | 核心不依赖容器 API |

### 9.11 序列化与导出

| 类别 | 推荐 | 备注 |
|------|------|------|
| JSON | **orjson**（高性能） | 可选 |
| 学习报告 | **Jinja2** → Markdown/HTML | |

### 9.12 与其它运行时边界

| 场景 | 做法 |
|------|------|
| 重 CPU 嵌入批处理 | 独立 worker 进程，队列消费 |
| 移动端 | API + 原生/Flutter；核心保持 Python 库 |

**选型小结**：MVP = **Streamlit + Neo4j（词汇图）+ PostgreSQL（掌握/审计/向量）+ Alembic + 端口化 ASR/LLM**；换图库仅替换 `infrastructure/graph/` 适配器。

---

## 10. 数据与持久化要点

### 10.1 Neo4j（词汇总图）

- **节点** `(:Lexeme)` 属性：`id`（UUID 字符串）、`kind`、`canonical_text`、`occurrence_count`、`phonetic`、`gloss_short`、`created_at`、`updated_at`（`datetime`）。  
- **边** `(a)-[:RELATES {id, relation_type, weight}]->(b)`；端点必须已存在。  
- **约束**：`lexeme_id` UNIQUE；`canonical_text`、`kind` 索引。  
- **查询模式**：`sample_lexemes` → `get_induced_subgraph` 支撑最小学习集；复杂 k-hop 可在仓储层扩展 Cypher。

### 10.2 PostgreSQL（关系与掌握）

- **用户掌握表**、**合并审计表**、**子图快照**（JSONB：节点 id 列表 + policy_version）、**嵌入向量**（pgvector）。  
- 外键逻辑以 **`lexeme_id`（UUID）** 关联 Neo4j 节点，**不做跨库 FK**；一致性由用例层保证。  
- **题目与作答日志**（可选）：便于分析错题与模型效果。

---

## 11. AI 集成策略

- 嵌入、合并裁判、造句裁判、LLM 出题均走 **端口**；失败时 **降级**（如无 LLM 则仅用规则出题 / 子串覆盖）。  
- 结构化输出一律 **Pydantic 校验** 后写入域。  
- `prompt_version` / `model_name` 写入审计或快照元数据。

---

## 12. 后续 Web / App 接入

| 交付形态 | 做法 |
|----------|------|
| HTTP API | `interfaces/api`（FastAPI）映射到与 Streamlit **相同用例** |
| 多租户 | `TenantId` / `UserId` 从接口注入用例；查询统一带作用域 |

---

## 13. 非功能需求（摘要）

- **可测试性**：采样、掌握状态机、覆盖检查可纯单测；集成测对 Fake 端口。  
- **性能**：子图构建在万级边内应 **秒级**；全图扫描加索引（节点标签、掌握状态）。  
- **隐私**：语音文件存储周期与脱敏策略在运维层定义；域内仅存转写文本与引用 id。

---

## 14. 实施里程碑（建议）

1. **M0**：Neo4j `LexiconGraphPort` + PG 掌握表迁移 + `IngestLexeme`（无向量可先 RapidFuzz）+ Streamlit 录入页。  
2. **M1**：`BuildLearningSubgraph`（Neo4j 采样 + 诱导子图）+ 子图展示 + 掌握表。  
3. **M2**：`GenerateSubgraphQuiz` / `SubmitQuizAnswers` + 划掉 UI。  
4. **M3**：`SubmitUserSentence` + 可选 `TranscriptionPort`。  
5. **M4**：pgvector 嵌入合并 + 人工拆分误合并（P1）+ API。

---

## 15. 小结

- **核心**锚定在 **词汇知识图谱 + 子图学习集 + 双模式检验 + 录入合并与频次**。  
- **技术选型** 以第 9 章为准：词汇图 **Neo4j**；掌握与向量 **PostgreSQL**；语音与出题 **端口化**；避免把 Neo4j Driver 渗入 `domain`。  
- 本文档与 [REQUIREMENTS.md](./REQUIREMENTS.md) 同步迭代版本号与术语表。
