"""Neo4j 约束与索引（幂等）。"""

from __future__ import annotations

from neo4j import Driver

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    "CREATE CONSTRAINT lexeme_id IF NOT EXISTS FOR (n:Lexeme) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX lexeme_canonical IF NOT EXISTS FOR (n:Lexeme) ON (n.canonical_text)",
    "CREATE INDEX lexeme_kind IF NOT EXISTS FOR (n:Lexeme) ON (n.kind)",
)


def ensure_lexeme_schema(driver: Driver, *, database: str | None = None) -> None:
    with driver.session(database=database) as session:
        for stmt in _SCHEMA_STATEMENTS:
            session.run(stmt)
