"""A-MEU-03：数据库连接与 UoW。

默认跳过：避免 CI / 本机未起 PostgreSQL 时长时间挂起或失败。
本机已起库且配置好 PG_DATABASE_URL 时：``RUN_DB_TESTS=1 pytest tests/integration -q``
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from knowlix.infrastructure.persistence import UnitOfWork
from knowlix.settings import settings

pytestmark = pytest.mark.skipif(
    settings.RUN_DB_TESTS != 1
    or not (settings.PG_DATABASE_URL or "").strip(),    
    reason="需设置 RUN_DB_TESTS=1 且配置 PG_DATABASE_URL，才运行数据库集成测试",
)


def test_unit_of_work_select_one() -> None:
    with UnitOfWork() as uow:
        assert uow.session.execute(text("SELECT 1")).scalar_one() == 1


def test_unit_of_work_inserts_then_rollbacks_on_error() -> None:
    with pytest.raises(RuntimeError, match="intentional"):
        with UnitOfWork() as uow:
            uow.session.execute(text("CREATE TEMP TABLE knowlix_meu03_smoke (x int)"))
            uow.session.execute(text("INSERT INTO knowlix_meu03_smoke VALUES (1)"))
            raise RuntimeError("intentional")

    with UnitOfWork() as uow:
        with pytest.raises(ProgrammingError):
            uow.session.execute(text("SELECT * FROM knowlix_meu03_smoke")).all()
