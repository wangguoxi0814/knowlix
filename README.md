# knowlix
中文名：诺利克斯。智能知识归纳系统。

# 环境切换
 - 默认dev环境
 - `.env(需自行创建)`为公共配置文件，`.env.**(需自行创建)`环境专属配置文件,如：`.env.dev`、`.env.prod`
 - 在`.env`设置`ENV=dev`/`ENV=prod`，或者通过系统环境变量设置开启不同环境
 

# 数据库集成测试
 - 本机启动 PostgreSQL，`.env` / `.env.<环境>` 中配置 `PG_DATABASE_URL`（可用 `postgresql://...`，会自动改用 `postgresql+psycopg`）
 - 仅跑持久化烟测：`RUN_DB_TESTS=1 pytest tests/integration -q`