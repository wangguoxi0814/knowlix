# Knowlix 需求说明

> 版本：0.1  
> 关联文档：[TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md)  
> 约定：**最小可执行单元**（下文简称 **MEU**）须满足：可单独规划工期、可验收（含明确完成标准）、尽量可独立测试或演示。

---

## 0. 全局约定

| 项 | 说明 |
|----|------|
| **优先级** | **P0** 核心归纳链路必备；**P1** 增强体验；**P2** 扩展（费曼/评分等）。 |
| **编号** | `[模块缩写]-MEU-序号`，如 `ING-MEU-01`。 |
| **验收** | 每条 MEU 下列「完成标准」；未列数据字段以技术设计中的实体为准。 |
| **持久化** | 关系数据 **仅 PostgreSQL**（与 TECHNICAL_DESIGN 一致）。 |

---

## 模块 A — 工程与基础设施底座

支撑所有业务 MEU 的最小落地条件。

### A-MEU-01 项目结构与可安装包

- **内容**：`src/knowlix/` 分层目录、`pyproject.toml` 可 `pip install -e .`，测试目录可运行 `pytest`。
- **完成标准**：空测试通过；包可被 import；README 或 docs 中能写清启动开发环境的一条命令（可与 A-MEU-02 合并文档）。

### A-MEU-02 配置与安全加载

- **内容**：数据库 URL、可选 LLM Key 等经环境变量 / `pydantic-settings` 注入应用组装根；示例 `.env.example`（不含真实密钥）。
- **完成标准**：未设置 DB 时启动应明确报错或跳过 DB（二选一应文档说明）；密钥不得出现在仓库或领域层。

### A-MEU-03 PostgreSQL 连接与会话边界

- **内容**：`infrastructure` 中实现引擎/连接池；`UnitOfWork`（或等价）界定事务与仓储生命周期。
- **完成标准**：单测或集成测试能插入并回滚一条占位记录；Streamlit/CLI 仅通过应用层入口访问，不裸连 SQL。

### A-MEU-04 Alembic 迁移基线

- **内容**：Alembic 与 SQLAlchemy 模型对齐；首批迁移可空表或最小表集。
- **完成标准**：`alembic upgrade head` 可在干净库成功执行；CI 或文档要求迁移与模型同步。

### A-MEU-05 组装根（依赖注入）

- **内容**：单一入口（如 `bootstrap()`）构造仓储、用例；`interfaces/streamlit` 不直接 import `infrastructure` 持久化细节（符合技术设计）。
- **完成标准**：替换 Fake 端口后 UI 行为可控；代码审查可按 import 规则检查。

---

## 模块 B — 问题摄入（Ingestion）

### B-MEU-01 原始问题领域模型

- **内容**：`RawQuestion`（或 `Capture`）实体/值对象：`id`、正文、可选上下文、状态机 `pending → organized | discarded`、时间戳。
- **完成标准**：领域单测覆盖状态非法迁移被拒绝（若已定义规则）；无 Streamlit 依赖。

### B-MEU-02 原始问题持久化

- **内容**：PostgreSQL 表 + 仓储接口实现；按 id 查询、列表（分页参数可先简化为 limit）。
- **完成标准**：集成测试：`save → load` 一致；删除/废弃行为与技术设计一致（若采用软删需写明）。

### B-MEU-03 用例：收录问题（CaptureProblem）

- **内容**：应用层用例：校验输入 → 持久化 `pending` 记录 → 返回 id。
- **完成标准**：Fake 端口下单元测试通过；非法输入返回可区分错误（不崩溃）。

### B-MEU-04 用例：废弃原始记录

- **内容**：将指定 `RawQuestion` 标为 `discarded`（或等价），不参与后续归纳/合并候选。
- **完成标准**：已废弃记录出现在「已归档/已废弃」列表语义正确；归纳流水线不处理该状态。

---

## 模块 C — AI 辅助问答（可选输入源，P1）

### C-MEU-01 端口：QuestionAnswerPort

- **内容**：定义 `Protocol`：入参（问题文本、可选上下文）→ 出参（答案正文、可选引用结构）；提供 `Fake` 实现。
- **完成标准**：应用层用例仅依赖端口类型；无具体厂商 SDK 在 `domain`/`application` 内。

### C-MEU-02 用例：生成草稿答案并关联原始问题

- **内容**：对某条 `RawQuestion` 调用端口，将结果持久化为「草稿答案」关联该 id（独立表或 JSON 字段，二选一并文档化）。
- **完成标准**：重复调用策略明确（覆盖/版本号/历史）；失败时原始问题仍存在且可重试。

### C-MEU-03 基础设施适配器：真实 LLM

- **内容**：实现 `QuestionAnswerPort`（超时、重试、日志脱敏可后补）；配置切换 Fake/真实。
- **完成标准**：密钥仅在 infrastructure；归纳用例在未配置 LLM 时仍可跑通（降级路径）。

---

## 模块 D — 知识归纳（Organization，★ P0 核心）

### D-MEU-01 知识点领域模型

- **内容**：`KnowledgeItem`：`canonical_title`、`summary_bullets`（列表）、`evidence_refs`（关联 `RawQuestion` id 列表）、版本或更新时间。
- **完成标准**：不变量文档化（例如至少一条 evidence）；非法空标题被领域或应用层拒绝。

### D-MEU-02 知识点持久化

- **内容**：表结构 + 仓储；与 `RawQuestion` 外键或关联表清晰。
- **完成标准**：创建、读取、更新要点列表；证据链可追溯。

### D-MEU-03 端口：SummarizerPort

- **内容**：输入：一组 raw 文本/或已有草稿；输出：标题 + 要点列表（结构化）；`Fake` 固定输出。
- **完成标准**：`OrganizeIntoKnowledge` 单测不连网可通过。

### D-MEU-04 用例：归纳生成知识点（OrganizeIntoKnowledge）

- **内容**：从一条或多条 `pending` raw 生成/更新 `KnowledgeItem`；写 `evidence_refs`；将相关 raw 标为 `organized`。
- **完成标准**：幂等策略写明（同一 raw 重跑不重复挂载）；事务失败时 raw 状态不回滚到错误中间态（或采用 Outbox/重试标记，择一文档化）。

### D-MEU-05 适配器：真实 Summarizer

- **内容**：对接选定 LLM，结构化输出经 Pydantic 校验后写入领域 DTO。
- **完成标准**：解析失败时进入 `failed`/重试队列，不损坏已有 `KnowledgeItem`（行为可测）。

---

## 模块 E — 分类体系（Taxonomy）

### E-MEU-01 分类树领域与持久化

- **内容**：`TaxonomyNode`（树或限定 DAG）；表 + 仓储；禁止删除仍有知识挂载的节点（或强制迁移规则）。
- **完成标准**：可增删改查节点；环检测（若为树）。

### E-MEU-02 知识点挂载分类（人工）

- **内容**：`KnowledgeItem` 关联 `taxonomy_node_id`（或多对多，与技术设计最终拍板一致）；用例：人工指定分类。
- **完成标准**：列表可按分类过滤；取消挂载后数据一致。

### E-MEU-03 端口：TaxonomySuggestPort + Fake

- **内容**：输入知识点摘要/标题 → 输出候选路径 + 置信度。
- **完成标准**：`AssignOrSuggestTaxonomy` 可先只跑 Fake 打通流程。

### E-MEU-04 用例：建议 + 确认分类（AssignOrSuggestTaxonomy）

- **内容**：拉取建议 → 写入「待审核」或直接落地（产品择一）；人工覆盖以最后一次为准。
- **完成标准**：审计字段（谁、何时改的）可选 P1，P0 至少要能区分「系统建议 vs 人工最终值」若产品需要。

---

## 模块 F — 同质合并（Deduplication）

### F-MEU-01 合并候选与决策模型

- **内容**：`MergeCandidate`/`MergeDecision`：涉及实体 id、相似度、算法版本、状态（ proposed / accepted / rejected ）。
- **完成标准**：同一对待重复 propose 有明确策略（更新分数或忽略）。

### F-MEU-02 端口：EmbeddingPort / VectorStorePort（或 pgvector 封装）

- **内容**：向量化文本、Nearest 查询；提供内存 Fake 或固定向量 Fake。
- **完成标准**：`ProposeMerges` 单测可不启真实向量库。

### F-MEU-03 用例：生成合并候选（ProposeMerges）

- **内容**：批处理：对 `KnowledgeItem` 或 `RawQuestion` 集合算相似度，超过阈值写入候选表。
- **完成标准**：阈值与 Top-K 可配置；大数据量时可分页/分批（可先文档写明限制）。

### F-MEU-04 端口：MergeJudgePort（可选，P1）

- **内容**：LLM/规则判定是否同质；与向量分数组合策略可配置。
- **完成标准**：关闭 Judge 时仅向量路径仍可用。

### F-MEU-05 用例：接受合并（AcceptMerge）

- **内容**：合并知识点或问题簇：证据链合并、taxonomy 冲突规则（主从/人工选）；更新 `merge_group_id` 等。
- **完成标准**：合并后旧实体不可达或重定向逻辑一致；可追溯合并前 id。

### F-MEU-06 用例：拒绝合并（RejectMerge）

- **内容**：标记拒绝；可选冷却期不再自动推荐同一对。
- **完成标准**：拒绝记录可出现在复盘统计中（若复盘需要）。

---

## 模块 G — 每日复盘（Daily Review）

### G-MEU-01 复盘快照模型与持久化

- **内容**：`DailyReviewSnapshot`：日期、统计字段、关键事件列表（新增知识点、分类变更、合并结果、待办队列摘要）。
- **完成标准**：同一日重复生成策略（覆盖 vs 版本递增）文档化。

### G-MEU-02 用例：生成当日复盘（BuildDailyReview）

- **内容**：聚合指定日 UTC/本地时区（**须固定一种并文档**）的变更；写入快照。
- **完成标准**：无变更日返回空快照而非错误。

### G-MEU-03 导出：Markdown

- **内容**：模板渲染（Jinja2 等）输出 `.md` 文件或下载流。
- **完成标准**：编码 UTF-8；与用户可见时区说明一致。

### G-MEU-04 导出：JSON（P1）

- **内容**：与 Markdown 信息等价或为其子集 machine-readable。
- **完成标准**：schema 版本号字段便于今后兼容。

---

## 模块 H — Streamlit 界面（按页拆 MEU）

界面只做呈现与调用用例，逻辑在应用层。

### H-MEU-01 应用壳与导航

- **内容**：多页 Streamlit 或侧边栏路由；全局错误提示区。
- **完成标准**：各子页面可切换不丢必选配置（如 DB 已连接）。

### H-MEU-02 页：收录问题

- **内容**：表单提交 → `CaptureProblem`；展示最近 N 条 pending。
- **完成标准**：用户可见成功/失败信息；与技术设计 import 边界一致。

### H-MEU-03 页：知识点列表与详情

- **内容**：列表、筛选（至少按状态或分类若已有）；详情展示 evidence、草稿答案（若有）。
- **完成标准**：从 raw 跳转知识点链路可点通。

### H-MEU-04 页：触发归纳与状态

- **内容**：选择 raw 或批量 → 触发 `OrganizeIntoKnowledge`；`st.status` 或队列状态展示。
- **完成标准**：长任务不阻塞整个进程可采用线程/队列（与 A 底座一致）。

### H-MEU-05 页：分类管理（最小）

- **内容**：树形编辑或简单 CRUD + 知识点挂载。
- **完成标准**：与 E 模块用例打通。

### H-MEU-06 页：合并候选队列

- **内容**：列表展示候选；Accept/Reject 按钮。
- **完成标准**：与 F 模块用例打通；操作后列表刷新正确。

### H-MEU-07 页：每日复盘

- **内容**：选择日期 → 生成/展示快照；下载 Markdown（及 JSON 若有）。
- **完成标准**：与 G 模块一致。

---

## 模块 I — 费曼与辅导（扩展，P2）

### I-MEU-01 可见性：隐藏标准要点

- **内容**：`KnowledgeItem` 或展示 DTO 上增加「对费曼练习隐藏要点/答案」开关；Streamlit 隐藏区块。
- **完成标准**：开关切换后页面不出现泄漏（含浏览器「查看源码」仅 Markdown 层面的合理范围外不存储于前端敏感区）。

### I-MEU-02 用例：提交阐述（SubmitFeynmanNarration）

- **内容**：用户文本（可选后续音频经 `TranscriptionPort`）；关联知识点 id；持久化。
- **完成标准**：多次提交是追加还是覆盖需产品句句话定义并实现。

### I-MEU-03 端口：评分与建议（ScoreNarration）

- **内容**：对比标准要点或 RAG 证据，输出分数维度和短建议；`Fake` 实现。
- **完成标准**：**不修改** `KnowledgeItem` 核心归纳字段，仅写辅导子域表或附属记录。

### I-MEU-04 页：费曼练习

- **内容**：隐藏答案 → 输入阐述 → 展示评分与建议（调用 I-MEU-03）。
- **完成标准**：LLM 关闭时 Fake 或友好提示。

---

## 模块 J — 未来 Web/API（占位，P2）

与技术设计「interfaces/api」对齐，每条可在核心稳定后独立立项。

### J-MEU-01 FastAPI 骨架与健康检查

- **内容**：`/health`、`/ready`（可检查 DB）；与组装根共用用例。
- **完成标准**：与 Streamlit 并行部署文档说明端口。

### J-MEU-02 资源路由：Capture / Knowledge / Review

- **内容**：REST 或最小 RPC 映射到现有用例；Pydantic 请求响应模型。
- **完成标准**：OpenAPI 可生成；与 Streamlit 行为一致（集成测试抽样）。

### J-MEU-03 认证预留

- **内容**：中间件占位（API Key 或 JWT 二选一占位）；不强行实现完整账号体系除非产品要求。
- **完成标准**：无认证时仅开发环境可访问（文档警示）。

---

## 附录：建议交付顺序（依赖粗排）

1. **A** 全系 → **B** → **D**（到 D-MEU-04 Fake 通路）→ **H-MEU-01～03**  
2. **E** 人工分类 → **H-MEU-05**  
3. **F** Fake 向量 → **H-MEU-06** → 换真实 **pgvector**  
4. **G** + **H-MEU-07**  
5. **C**（可选）、**D-MEU-05**、**E-MEU-04** 真实模型  
6. **I**、**J** 按需插入  

---

## 文档维护

- 新增 MEU 时：补充编号、优先级、完成标准，并反向检查 [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md) 是否需同步（模型名、端口名、存储策略）。
