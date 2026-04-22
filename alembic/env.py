from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# 从仓库根执行 alembic 时，包在 src/knowlix 下
_root = Path(__file__).resolve().parent.parent
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from knowlix.infrastructure.persistence.database import require_database_url
from knowlix.infrastructure.persistence.orm import Base

# 导入 ORM 子模块，将表注册进 Base.metadata
import knowlix.infrastructure.persistence.models  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """与 runtime 一致：PG_DATABASE_URL + psycopg3 驱动规范化。"""
    return require_database_url()


def run_migrations_offline() -> None:
    """Offline：只生成 SQL，不连库。"""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online：连库执行迁移。"""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
