"""Neo4j 驱动生命周期。"""

from __future__ import annotations

from functools import lru_cache

from neo4j import Driver, GraphDatabase

from knowlix.settings import settings

_driver: Driver | None = None


def neo4j_uri() -> str:
    uri = (settings.NEO4J_URI or "").strip()
    if not uri:
        raise RuntimeError(
            "未配置 NEO4J_URI。请在 .env 或 .env.<ENV> 中设置，例如 bolt://localhost:7687"
        )
    return uri


def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is not None:
        return _driver
    user = (settings.NEO4J_USER or "").strip()
    password = settings.NEO4J_PASSWORD or ""
    auth = (user, password) if user else None
    _driver = GraphDatabase.driver(neo4j_uri(), auth=auth)
    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def reset_neo4j_driver_cache() -> None:
    close_neo4j_driver()
