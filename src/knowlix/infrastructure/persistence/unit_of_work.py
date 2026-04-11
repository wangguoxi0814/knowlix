"""事务边界：进入时打开 Session，退出时 commit 或 rollback。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker


class UnitOfWork:
    """与 A-MEU-03 对齐的最小 UoW；仓储后续通过 session 注册到此对象上。"""

    def __init__(self) -> None:
        from knowlix.infrastructure.persistence.database import get_engine

        self._factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
        self._session: Session | None = None

    def __enter__(self) -> UnitOfWork:
        self._session = self._factory()
        return self

    def __exit__(self, exc_type: type | None, exc: BaseException | None, tb: Any) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            self._session.rollback()
        else:
            self._session.commit()
        self._session.close()
        self._session = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork 须在 with 块内使用")
        return self._session
