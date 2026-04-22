# knowlix
中文名：诺利克斯。智能知识归纳系统。

# 环境切换
 - 默认dev环境
 - `.env(需自行创建)`为公共配置文件，``.env.<环境>`(需自行创建)`环境专属配置文件,如：`.env.dev`、`.env.prod`
 - 在`.env`设置`ENV=dev`/`ENV=prod`，或者通过系统环境变量设置开启不同环境


# 数据库集成测试
 - 本机启动 PostgreSQL，`.env` / `.env.<环境>` 中配置 `PG_DATABASE_URL`（可用 `postgresql://...`，会自动改用 `postgresql+psycopg`）
 - 仅跑持久化烟测：`RUN_DB_TESTS=1 pytest tests/integration -q`

# 数据库迁移（Alembic）

## 步骤 5：模型基线（维护约定）

- **声明式基类**：`src/knowlix/infrastructure/persistence/orm.py` 的 `Base`。
- **ORM 模型包**：`src/knowlix/infrastructure/persistence/models/`，须在 `alembic/env.py` 中 `import knowlix.infrastructure.persistence.models`，以便 `target_metadata` 与 autogenerate 一致。
- **当前业务表**：`raw_questions`（`RawQuestionORM`），由迁移 `7c51c3f6fcd7` 建表、`c5430586d6e3` 增加审计列。

## 步骤 6：revision 链与干净库验证

- **迁移链**（按顺序）：`334f3a8e0b42` → `7c51c3f6fcd7`（`raw_questions`）→ `c5430586d6e3`（`created_by` / `updated_by`）。
- **日常升级**（项目根目录，已配置 `PG_DATABASE_URL`）：`alembic upgrade head`；`alembic current` 应显示 `c5430586d6e3`。

### 干净空库验收（推荐新环境或发版前）

1. 新建空库（示例）：`createdb -h localhost -U postgres knowlix_verify`（按你的账号修改）。
2. 本次终端指向该库（PowerShell）：`$env:PG_DATABASE_URL = "postgresql://postgres:密码@localhost:5432/knowlix_verify"`
3. 项目根执行：`alembic upgrade head`
4. 预期：`alembic_version.version_num = c5430586d6e3`，且存在表 `raw_questions`（含 `created_by`、`updated_by`）。
5. 可选：`alembic downgrade base` 后 `raw_questions` 应被删除。

**注意**：`id` 使用 `gen_random_uuid()`，需 **PostgreSQL 13+**。

## 其它

- `alembic.ini` 注释建议 **ASCII**，避免 Windows 读 ini 编码问题。
- 新建迁移：`alembic revision -m "描述"`；autogenerate：`alembic revision --autogenerate -m "描述"`。
- 已连库的 schema 校验：`RUN_DB_TESTS=1 pytest tests/integration/test_alembic_schema.py -q`（**新迁移发布后**请更新测试中 `expected_head`）。
