"""A-MEU-04 步骤 6：在已执行 migrate 的库上校验 schema（需先有 alembic upgrade head）。

干净空库验收流程见 README「干净库验证」；本测试验证当前开发库是否已应用到最新迁移。
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from knowlix.infrastructure.persistence import UnitOfWork
from knowlix.settings import settings

pytestmark = pytest.mark.skipif(
    settings.RUN_DB_TESTS != 1
    or not (settings.PG_DATABASE_URL or "").strip(),
    reason="需 RUN_DB_TESTS=1 且 PG_DATABASE_URL",
)


def test_alembic_version_row_exists() -> None:
    with UnitOfWork() as uow:
        n = uow.session.execute(
            text("SELECT count(*) FROM alembic_version")
        ).scalar_one()
        assert int(n) >= 1


def test_raw_questions_table_exists() -> None:
    with UnitOfWork() as uow:
        found = uow.session.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'raw_questions'"
            )
        ).scalar_one_or_none()
        assert found == 1


def test_revision_at_known_head() -> None:
    """与当前迁移链末端一致；新增迁移后请同步更新此处 revision id。"""
    expected_head = "c5430586d6e3"
    with UnitOfWork() as uow:
        v = uow.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        assert v == expected_head
