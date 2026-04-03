# Knowlix 项目技术设计文档

> 版本：0.4（持久化固定为 PostgreSQL）  
> 目标：以 **Python** 实现「知识 AI 问答 → 自动归纳整理 → 分类与同质合并 → 每日复盘」；**唯一核心**是知识归纳与分类能力；扩展能力（费曼自检、AI 纠错/打分等）与 UI（Streamlit / 未来 Web/App）通过边界与端口隔离，确保 **核心域代码不因前端形态变化而改动**。

---

## 1. 产品范围与优先级

### 1.1 核心能力（必须做对、可扩展）

| 能力 | 说明 |
|------|------|
| **问题捕获** | 用户当下遇到的问题以结构化形式进入系统（原文、上下文、标签草稿等）。 |
| **AI 辅助问答** | 可选：生成初版解答或要点，作为归纳输入（解答可持久化，但产品上可「弱化」为辅助）。 |
| **自动归纳** | 将散点记录整理为「知识点」实体（标题、摘要、要点、引用来源问题）。 |
| **分类体系** | 支持多级分类 / 主题；可由规则、LLM、或混合策略打标；**分类逻辑在应用层可替换**。 |
| **同质问题合并** | 相似问合并到同一知识点或同一「问题簇」；支持人工确认与撤销。 |
| **每日复盘** | 按日汇总：新增知识点、分类变动、合并记录、待处理队列；可导出 Markdown/JSON。 |

### 1.2 扩展能力（非核心、插件化）

- 知识点下 **隐藏标准答案**，用户用费曼法自述，系统录音/文本提交。  
- **AI 纠错、相似度打分、优化建议**（对比「标准要点」或 RAG 证据）。  

以上扩展通过 **独立的应用服务 + 端口** 接入，**不侵入**「归纳、分类、合并、复盘」的领域不变量。

---

## 2. 架构原则

1. **有界上下文（Bounded Context）**：每个上下文有明确语言与职责，跨上下文通过 **应用服务编排** 或 **领域事件** 通信，避免「一个大类搞定一切」。  
2. **依赖倒置**：核心域 **不依赖** Streamlit、HTTP、具体 LLM SDK、具体数据库驱动；只依赖 **端口（Protocol / ABC）**。  
3. **用例驱动**：`application/use_cases/` 中每个用例对应一条用户旅程（如「收录问题 → 触发归纳」），领域逻辑在 `domain/`。  
4. **可替换基础设施**：`infrastructure/` 实现仓储，AI 客户端，向量库等；换 Web/API 只新增 `interfaces/` 下的适配器。  
5. **事件与异步（可选演进）**：归类、合并、日报生成可发域事件，便于未来 Worker、移动端推送订阅同一流水线。

---

## 3. 有界上下文划分

```
┌─────────────────────────────────────────────────────────────────┐
│  Knowledge Ingestion & Q&A（摄入与问答）                          │
│  - 原始问题、会话、可选 AI 草稿答案                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Knowledge Organization（知识归纳）★ 核心                         │
│  - RawRecord → KnowledgeItem；聚类；与分类、合并策略协作           │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌─────────────────┐   ┌──────────────────────┐
│ Taxonomy      │   │ Deduplication   │   │ Daily Review          │
│ 分类与打标     │   │ 同质合并         │   │ 日终汇总与报告         │
└───────────────┘   └─────────────────┘   └──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Feynman & Tutor（费曼 / 辅导）— 扩展上下文                         │
│  - 隐答案、用户阐述、AI 评分与建议 — 只依赖 KnowledgeItem 的只读视图   │
└─────────────────────────────────────────────────────────────────┘
```

**边界规则**：  
- 「归纳」上下文 **拥有** `KnowledgeItem` 的生命周期与不变量。  
- 「分类」「合并」「复盘」可协作与订阅事件，但 **不反向修改** 彼此内部聚合根（通过明确命令/用例更新）。  
- 「费曼」仅消费 **稳定的查询 DTO**（如 `KnowledgeItemSummary`），避免与归纳聚合写模型耦合。

---

## 4. 推荐 Python 包结构（单体仓库、清晰分层）

```
knowlix/
├── pyproject.toml
├── src/
│   └── knowlix/
│       ├── domain/                    # 纯领域：实体、值对象、领域服务、不变量
│       │   ├── organization/          # 核心：KnowledgeItem, MergeCandidate, ...
│       │   ├── taxonomy/
│       │   ├── ingestion/
│       │   ├── review/
│       │   └── feynman/               # 扩展域（可选包，或后续独立模块）
│       ├── application/               # 用例、事务边界、编排
│       │   ├── ports/                 # Protocol：LLM, VectorSearch, Clock, IdGenerator
│       │   └── use_cases/
│       ├── infrastructure/            # 适配器实现
│       │   ├── persistence/           # PostgreSQL + Repository
│       │   ├── ai/                      # OpenAI/本地模型等
│       │   └── jobs/                  # 定时日报、批处理
│       └── interfaces/                # 交付形态（薄层）
│           └── streamlit/             # 页面仅调用 application
│           # 未来: interfaces/api/ (FastAPI)、interfaces/mobile_gateway/
├── tests/
│   ├── domain/
│   ├── application/
│   └── integration/
└── docs/
    └── TECHNICAL_DESIGN.md
```

**规则**：`interfaces/streamlit/` **禁止** 直接 import `infrastructure`；一律通过 **facade 用例** 或 **DI 容器** 注入 `application` 服务。

---

## 5. 核心领域模型（草案）

### 5.1 聚合与实体

- **`RawQuestion`（或 `Capture`）**：用户原始输入；状态：`pending` → `organized` / `discarded`。  
- **`KnowledgeItem`（核心聚合根）**：归纳后的知识点；含 `canonical_title`、`summary_bullets`、`evidence_refs`（指向原始问题 ID）、`taxonomy_node_id`、`merge_group_id`、`visibility_flags`（如是否对扩展模块展示标准答案）。  
- **`TaxonomyNode`**：树或 DAG；`KnowledgeItem` 可挂载多个 tag（值对象）或由节点拥有（二选一并写清不变量）。  
- **`MergeDecision`**：候选对、相似度分数、来源算法版本、人工确认记录。  
- **`DailyReviewSnapshot`**：某日的不可变快照（便于审计与回放）。

### 5.2 关键领域服务（无状态、可单测）

- **`OrganizationService`**：Raw → KnowledgeItem 的转换规则（可调用 **端口** `SummarizerPort`，实现不在域内）。  
- **`SimilarityClusteringPolicy`**：抽象接口 + 多种实现（向量、LLM 判同、规则）；**同质合并**策略可插拔。  
- **`ClassificationPolicy`**：打标管道（多级分类、置信度、待人工审核队列）。

---

## 6. 端口（Ports）设计 — 保证核心可扩展

在 `application/ports/` 中定义 **Protocol**，示例：

| 端口 | 职责 |
|------|------|
| `SummarizerPort` | 将多条 Raw 或对话历史压缩为知识点草案。 |
| `QuestionAnswerPort` | 可选：独立问答，输出带引用结构的答案。 |
| `EmbeddingPort` / `VectorStorePort` | 语义检索与聚类。 |
| `TaxonomySuggestPort` | 建议分类路径（返回候选 + 分数）。 |
| `MergeJudgePort` | LLM/规则判定是否同质（返回结构化结果）。 |
| `UnitOfWorkPort` | 事务与仓储网关（领域不直接写 SQL）。 |

**新增 Web/API**：实现相同端口或复用 `infrastructure` 实现，**零改动** `domain` 与用例签名（最多增加「鉴权上下文」值对象传入用例）。

---

## 7. 核心用例（应用层）

1. **`CaptureProblem`**：保存原始问题，可选触发异步归纳。  
2. **`OrganizeIntoKnowledge`**：生成/更新 `KnowledgeItem`，写入证据链。  
3. **`AssignOrSuggestTaxonomy`**：自动+人工校正分类。  
4. **`ProposeMerges` / `AcceptMerge` / `RejectMerge`**：同质候选与同态合并。  
5. **`BuildDailyReview`**：生成当日 `DailyReviewSnapshot` 与可读报告。  

**扩展用例（独立模块）**：  
6. **`SubmitFeynmanNarration` / `ScoreNarration`**：读 `KnowledgeItem`，写辅导子域聚合。

---

## 8. Streamlit 前端角色

- **仅做**：表单、列表、可视化时间线、复盘页展示；会话状态与 `st.cache_resource` 包装的 **应用服务入口**。  
- **不做**：分类算法、合并判定、数据库 SQL、直接调用第三方 LLM。  
- **分页与后台任务**：长耗时归纳/聚类可 `st.status` + 线程/队列，或后台 `jobs`（后续与 Web 共用）。

---

## 9. 技术选型与可替换方案

本节给出 **MVP 默认推荐** 与 **可替换项**，选型原则：**仅落入 `infrastructure` 与 `interfaces`**，`domain` / `application` 保持与具体厂商无关。

### 9.1 语言、运行时与工程化

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| Python | **3.10.6**（类型提示与性能） |  |
| 依赖与虚拟环境 | **uv**（锁文件 + 极速安装）或 **Poetry** | `pip-tools` + `requirements.in` 亦够轻量 |
| 打包布局 | **`src/` 布局** + `pyproject.toml` | 避免隐式 `PYTHONPATH` 污染 |
| 代码质量 | **Ruff**（lint + format）+ **mypy**（严格模式分阶段打开） | BasedPyright 可作类型检查备选 |
| 测试 | **pytest** + **pytest-cov**；契约用 **schemathesis**（将来 API） | **Hypothesis** 用于分类/合并策略属性测试 |

### 9.2 界面层（当前优先 Streamlit）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 桌面/本地 Web UI | **Streamlit** | **Gradio** 适合极简 Demo；复杂交互可迁 **NiceGUI** |
| 会话与配置 | `st.session_state` + **Pydantic Settings** 读环境变量 | 敏感键不落仓库；`.env` 仅本地 |
| 组件增强 | **streamlit-extras**、原生 `st.data_editor` | 图表 **Plotly** / **Altair** 二选一即可 |
| 未来纯 Web | **FastAPI** + 任意 SPA（React / Vue）仅作 `interfaces` | **HTMX + Jinja2** 可作轻量后台管理 |

### 9.3 将来 API 与认证（核心外）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| HTTP API | **FastAPI** | Starlette 裸用；体量极大时再拆 BFF |
| 模式与校验 | **Pydantic v2** | OpenAPI 由 FastAPI 自动生成 |
| 认证/会话 | 视产品：**JWT**（`python-jose` / Authlib）或 **Session + HTTP-only Cookie** | 商业 ID：**Clerk**、**Auth0** 仅挂在 API 适配器 |
| 文件上传（费曼音频） | **python-multipart** + 对象存储适配器 | 本地 MVP：限制大小 + 防路径穿越 |

### 9.4 持久化与迁移

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 关系库 | **PostgreSQL**（唯一选项；开发与生产同一引擎，避免方言差异） | 本地/MVP 用 **Docker Compose** 或单容器 Postgres 即可 |
| ORM | **SQLAlchemy 2.0**（Core + ORM 分明） | 喜模型合一：**SQLModel**（仍基于 SQLAlchemy） |
| 迁移 | **Alembic**（自首批表起纳入工作流） | 与 CI 对齐：`upgrade heads` 作为部署前置检查 |
| 全文检索（可选） | **pg_trgm** + GIN（模糊/相似）；或 **tsvector**（分词需按语言调参） | 检索极重时再评估 **Elastic/OpenSearch** |
| JSON 字段 | **JSONB**（PostgreSQL）+ SQLAlchemy 映射 | 大块 blob 单独表或大对象存储，避免聚合根行过宽 |

### 9.5 向量与语义合并 / 检索

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 向量存储 | **pgvector**（与业务库同 Postgres，事务与备份策略一致） | 规模大或要独立扩缩：**Qdrant**、**Milvus**；本地轻量实验可 **Chroma**（不走主库） |
| 向量索引 | 候选对少时可 **暴力余弦**；上万条再上 **HNSW**（由向量库提供） | **FAISS** 适合纯本地离线索引 |
| Embedding 模型 | 云端 API（OpenAI 等）经 `EmbeddingPort` | 离线：**sentence-transformers**；多语言看 **BGE-M3** 等 |

### 9.6 大模型接入与结构化输出

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 云 API | 官方 SDK（**openai**、**anthropic**）经统一 **薄封装** | **LiteLLM**：多供应商路由、fallback、计费统计 |
| 结构化 JSON | **Pydantic + Instructor** 或 **OpenAI JSON Schema / tool** | 避免把 **LangChain** 链塞进 `domain`；若用，仅限 `infrastructure` 流水线胶水 |
| 本地 / 私有部署 | **Ollama**、**vLLM**、**llama.cpp** | 与云端同一 `QuestionAnswerPort` 多实现 |
| 提示管理 | 仓库内 **版本化模板**（Jinja2 或纯字符串）+ 元数据表记 `prompt_version` | 远程拉取：后期接配置中心 |

### 9.7 异步任务、调度与消息

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| MVP 后台 | **线程池** + 队列（`queue.Queue`）或 Streamlit 外挂 **APScheduler** | 足够支撑单机日报与批归纳 |
| 可扩展队列 | **Celery + Redis** | 轻量：**RQ**、**Arq**（async） |
| 事件总线（后期） | 进程内 **事件列表** 或 **Redis Pub/Sub** | 多服务：**Kafka**（通常过重） |

### 9.8 可观测性、日志与安全

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 日志 | **structlog**（JSON 友好）或标准 `logging` + 格式化 | 敏感字段脱敏在 infrastructure |
| 指标（后期） | **OpenTelemetry** + Prometheus exporter | MVP 可先打点时间戳 |
| 配置密钥 | **pydantic-settings**；密钥来自环境变量或密钥管理 | 禁止把 API Key 写进领域层 |

### 9.9 文档导出与模板

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 每日复盘 Markdown | **Jinja2** 模板 + `BuildDailyReview` DTO | **markupsafe** 防注入；PDF 后期 **WeasyPrint** / pandoc |

### 9.10 容器与部署（可选）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 容器 | **Docker** 单阶段 + 多阶段构建减镜像 | **docker compose** 编排 Streamlit + **PostgreSQL**（必选；镜像或启动脚本启用 **pgvector**）+ 可选 **Qdrant**（专用向量库扩缩） |
| 逆向代理 | **Caddy** 或 **Nginx** 终止 TLS | Streamlit 内置不适合直接公网暴露 |

### 9.11 依赖注入与组装根（Composition Root）

| 类别 | MVP/DIY 推荐 | 替代 / 备注 |
|------|-------------|-------------|
| 组装方式 | **`interfaces/streamlit/app.py`（或 `main.py`）手工 `new` 仓储 + 注入用例** | 简单、显式、易调试 |
| DI 容器 | 体量变大再引入 **dependency-injector** 或 **lagom** | 避免核心层依赖任何容器 API |
| 生命周期 | Streamlit：`@st.cache_resource` 包住「进程级单例」（DB 引擎、LLM 客户端） | 与 Web Worker 模型不同，拆环境时重写 interfaces 即可 |

### 9.12 序列化、API 交换格式与缓存

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| JSON（高性能） | **orjson** 或 **msgspec**（将来 FastAPI 响应模型仍可 Pydantic，序列化层切换） | 标准库 `json` 够用则不必提前引入 |
| 导出/备份 | **JSON Lines**（`.jsonl`）流式写出日报或批量导出 | 大块附件用文件路径引用，不嵌 base64 |
| 缓存（可选） | **diskcache** / **Redis**（多实例时再） | 仅限 infrastructure；缓存键含 `prompt_version`、模型名 |

### 9.13 扩展：费曼口述与音频（仅基础设施）

| 类别 | 可选方案 | 备注 |
|------|-----------|------|
| 语音转写 | **Whisper**（本地）、**Azure Speech**、**阿里云/讯飞** 等经 `TranscriptionPort` | 核心域只收「转写文本 + 元数据」 |
| 音频处理 | **pydub**（格式转换）、浏览器端 **Web Audio**（可选） | 存储走对象存储适配器或限大小本地目录 |
| 文本差分/高亮（UI） | **diff-match-patch**；展示仅在 interfaces | 与 `ScoreNarration` 输出无关 |

### 9.14 RAG 与长文档切块（可选，不绑架核心）

| 类别 | 推荐策略 | 替代 / 备注 |
|------|-----------|-------------|
| 定位 | **检索增强**只实现于 `infrastructure`，对领域暴露 `EvidenceRetrieverPort` 或扩展现有 `QuestionAnswerPort` | 核心仍是「归纳/分类/合并」，RAG 是答案质量插件 |
| 切块 | 自研 **固定窗口 + 重叠** 或 **语义切块**（小库） | **LlamaIndex** 仅作 adapter 胶水；避免业务规则进 Index |
| 重排序 | **cross-encoder**（cpu 小模型）作二阶段排序 | 经端口注入，便于单测 Fake |

### 9.15 安全、隐私与合规（工程技术项）

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 静态敏感数据 | 字段级 **Fernet**（`cryptography`）或 DB 透明加密（部署层） | 密钥.rotation 策略放在运维文档，不在域内 |
| 清洗与审计 | 导出日志 **脱敏**；删除请求走用例 `ForgetSubject`（若产品需要） | |
| 依赖漏洞 | **pip-audit** / **uv audit** 进 CI | |

### 9.16 CLI、脚本与开发者体验

| 类别 | MVP 推荐 | 替代 / 备注 |
|------|-----------|-------------|
| 运维/批处理 CLI | **Typer** + `knowlix.cli`（如重建索引、补跑日报） | **Click** 亦可 |
| Git 钩子 | **pre-commit**（Ruff、mypy、检测大文件） | |
| 任务启动 | **Makefile** 或 **just**（`justfile`）统一 `test`、`lint`、`run` | |

### 9.17 与其它语言/运行时的边界（可选远期）

| 场景 | 做法 | 原因 |
|------|------|------|
| 高性能向量检索服务 | 独立 **Qdrant/Milvus** 进程，HTTP/gRPC | Python 核心不变 |
| 重 CPU 预处理 | 侧车 **Rust/Go** 微服务，经 HTTP 调用 | 仅当 profiling 证明瓶颈 |
| 移动端 | **不**在核心引入 Kivy；App 走 **API + 原生/Flutter** | 保持核心纯 Python 库即可 |

**选型结论**：MVP 以 **Streamlit + PostgreSQL + Alembic + 统一 LLM 端口** 闭环；语义向量优先 **pgvector**（同库），必要时再外挂专用向量库；任务队列仅在「后台任务与并发」触线时引入，**不改变核心用例与领域模型**。上表各「替代」列可在不触碰 `domain` 的前提下替换实现。

---

## 10. 数据与持久化

- **唯一关系库**：**PostgreSQL**；ORM 采用 **SQLAlchemy 2.0** 或 **SQLModel**；仓储与连接池在 `infrastructure/persistence/`，连接串由环境变量注入。  
- **向量**：默认落在 **pgvector** 扩展（与业务数据同事务或明确读写顺序）；若单机资源或检索规模不适用，再通过 **`VectorStorePort`** 换用 Qdrant 等，**迁移与双写策略仅在 infrastructure 层**。  
- **日报**：快照落库（PostgreSQL）+ 模板渲染（Jinja2 / 纯 Python 字符串），导出与 Streamlit/Web 共用同一 `BuildDailyReview` 输出 DTO。

---

## 11. AI 集成策略（与核心解耦）

- **提示词与 schema**：集中在 `infrastructure/ai/prompts/`，版本号写入 `MergeDecision` / `KnowledgeItem` 元数据，便于回放与 A/B。  
- **结构化输出**：分类、合并、归纳一律优先 **JSON schema / tool calling**，应用层校验后写入域。  
- **降级**：LLM 不可用时，摄取仍成功，队列标记 `retry`，不破坏归纳流水线状态机。

---

## 12. 后续 Web / App 接入方式

| 交付形态 | 建议 | 与核心的关系 |
|----------|------|----------------|
| **Web** | 新增 `interfaces/api`（如 FastAPI），路由处理器调用 **相同用例**；JWT/OAuth 在接口层。 | 核心包无变更。 |
| **移动端** | App → API → 用例；或 GraphQL BFF；离线缓存由客户端处理。 | 核心包无变更。 |
| **多租户（若需要）** | `TenantId` 作为值对象从接口层注入用例；仓储查询统一带租户。 | 领域规则可逐用例加强。 |

---

## 13. 非功能需求（摘要）

- **可测试性**：领域单测不连网；集成测对 Fake 端口。  
- **可观测性**：用例级结构化日志（`correlation_id`）、关键指标（归纳延迟、合并准确率人工反馈）。  
- **隐私**：原始问题与阐述可加密字段或按环境配置脱敏；密钥仅在 infrastructure。  
- **合规**：扩展「费曼录音」时注意本地存储与权限模型，与核心归纳表分离。

---

## 14. 实施里程碑（建议）

1. **M0**：包结构 + `KnowledgeItem` / `RawQuestion` + **PostgreSQL** 仓储 + Alembic 基线 + `CaptureProblem`。  
2. **M1**：`OrganizeIntoKnowledge` + `SummarizerPort` Fake/真实实现 + Streamlit 最小流程。  
3. **M2**：`Taxonomy` + `ProposeMerges` + 人工审核 UI。  
4. **M3**：`BuildDailyReview` + 导出。  
5. **M4（扩展）**：`interfaces/api` + Feynman 子域 + 评分端口。

---

## 15. 小结

- **核心**锚定在 **Knowledge Organization** 有界上下文：归纳、分类、同质合并、每日复盘。  
- **Streamlit** 是 **薄适配器**；**Web/App** 通过 **相同的应用用例与端口** 接入，无需修改核心领域与用例实现。  
- **同质合并与分类** 以 **策略 + 端口** 注入，保证算法与模型迭代时上层流程稳定。  
- **技术选型** 以第 9 章为清单：新增栈时优先对照「落入哪一层」，避免泄漏进核心域。  
- **关系型与事务型持久化** 仅 **PostgreSQL**（开发/生产同一引擎）；向量检索以 **pgvector** 为默认，必要时经端口切换外挂库，不改变领域模型。

本文档作为后续 `README`、API 契约与数据库迁移的父文档，随实现迭代版本号与「上下文地图」。
