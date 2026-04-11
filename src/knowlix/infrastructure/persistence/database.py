"""SQLAlchemy 引擎（懒加载）。未配置 URL 时仅在首次连接时报错。"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from knowlix.settings import settings

_engine: Engine | None = None

def _database_url() -> str:
    return (settings.PG_DATABASE_URL or "").strip()

def require_database_url() -> str:
    url = _database_url()
    if not url:
        raise RuntimeError(
            "未配置 PG_DATABASE_URL。请在 .env 或 .env.<ENV> 中设置 PostgreSQL 连接串。"
        )
    return _normalize_postgres_driver(url)


def _normalize_postgres_driver(url: str) -> str:
    """使用已声明的 psycopg3 驱动（postgresql+psycopg）。"""
    if url.startswith("postgresql+") or url.startswith("postgres+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            require_database_url(),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
    return _engine


def reset_engine_cache() -> None:
    """释放连接池；在测试里热切换 PG_DATABASE_URL 后应调用。"""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
