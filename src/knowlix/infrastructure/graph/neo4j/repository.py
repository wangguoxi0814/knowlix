"""Neo4j 实现的 LexiconGraphPort。"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import UUID, uuid4

from neo4j import Driver

from knowlix.domain.lexicon_graph import (
    LexemeEdge,
    LexemeKind,
    LexemeNode,
    LearningSubgraph,
)
from knowlix.infrastructure.graph.neo4j import mapper
from knowlix.infrastructure.graph.neo4j.schema import ensure_lexeme_schema


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Neo4jLexiconGraphRepository:
    """词汇总图谱仓储：节点与边存于 Neo4j。"""

    def __init__(self, driver: Driver, *, database: str | None = None) -> None:
        self._driver = driver
        # None 表示使用 Neo4j 实例默认库（通常为 neo4j）
        self._database = database

    def _session(self):
        return self._driver.session(database=self._database)

    def ensure_schema(self) -> None:
        ensure_lexeme_schema(self._driver, database=self._database)

    def upsert_lexeme(self, node: LexemeNode) -> LexemeNode:
        now = _utc_now()
        created = node.created_at or now
        query = """
        MERGE (n:Lexeme {id: $id})
        ON CREATE SET
            n.kind = $kind,
            n.canonical_text = $canonical_text,
            n.occurrence_count = $occurrence_count,
            n.phonetic = $phonetic,
            n.gloss_short = $gloss_short,
            n.created_at = datetime($created_at),
            n.updated_at = datetime($updated_at)
        ON MATCH SET
            n.kind = $kind,
            n.canonical_text = $canonical_text,
            n.phonetic = $phonetic,
            n.gloss_short = $gloss_short,
            n.updated_at = datetime($updated_at)
        RETURN n
        """
        params = {
            "id": str(node.id),
            "kind": node.kind.value,
            "canonical_text": node.canonical_text,
            "occurrence_count": node.occurrence_count,
            "phonetic": node.phonetic,
            "gloss_short": node.gloss_short,
            "created_at": created.isoformat(),
            "updated_at": (node.updated_at or now).isoformat(),
        }
        with self._session() as session:
            record = session.run(query, params).single()
            if record is None:
                raise RuntimeError("upsert_lexeme 未返回节点")
            return mapper.lexeme_from_props(mapper.node_to_props(record["n"]))

    def get_lexeme(self, node_id: UUID) -> LexemeNode | None:
        query = "MATCH (n:Lexeme {id: $id}) RETURN n LIMIT 1"
        with self._session() as session:
            record = session.run(query, id=str(node_id)).single()
            if record is None:
                return None
            return mapper.lexeme_from_props(mapper.node_to_props(record["n"]))

    def find_by_canonical(self, canonical_text: str, kind: LexemeKind) -> LexemeNode | None:
        query = """
        MATCH (n:Lexeme {canonical_text: $text, kind: $kind})
        RETURN n LIMIT 1
        """
        with self._session() as session:
            record = session.run(query, text=canonical_text, kind=kind.value).single()
            if record is None:
                return None
            return mapper.lexeme_from_props(mapper.node_to_props(record["n"]))

    def increment_occurrence(self, node_id: UUID, delta: int = 1) -> int:
        query = """
        MATCH (n:Lexeme {id: $id})
        SET n.occurrence_count = coalesce(n.occurrence_count, 0) + $delta,
            n.updated_at = datetime($updated_at)
        RETURN n.occurrence_count AS count
        """
        with self._session() as session:
            record = session.run(
                query,
                id=str(node_id),
                delta=delta,
                updated_at=_utc_now().isoformat(),
            ).single()
            if record is None:
                raise LookupError(f"Lexeme 不存在: {node_id}")
            return int(record["count"])

    def create_edge(self, edge: LexemeEdge) -> LexemeEdge:
        query = """
        MATCH (a:Lexeme {id: $src_id}), (b:Lexeme {id: $dst_id})
        MERGE (a)-[r:RELATES {id: $edge_id}]->(b)
        SET r.relation_type = $relation_type,
            r.weight = $weight
        RETURN r, a.id AS src_id, b.id AS dst_id
        """
        params = {
            "edge_id": str(edge.id),
            "src_id": str(edge.src_id),
            "dst_id": str(edge.dst_id),
            "relation_type": edge.relation_type.value,
            "weight": edge.weight,
        }
        with self._session() as session:
            record = session.run(query, params).single()
            if record is None:
                raise RuntimeError("create_edge 失败：端点不存在或写入未返回")
            rel = dict(record["r"])
            return mapper.edge_from_record(
                str(edge.id),
                str(record["src_id"]),
                str(record["dst_id"]),
                rel,
            )

    def sample_lexemes(
        self,
        *,
        count: int,
        exclude_ids: frozenset[UUID] | None = None,
        kind: LexemeKind | None = None,
        seed: int | None = None,
    ) -> list[LexemeNode]:
        if count <= 0:
            return []
        excluded = [str(i) for i in (exclude_ids or frozenset())]
        kind_clause = "AND n.kind = $kind" if kind is not None else ""
        # Neo4j 5+ rand()；用较大 LIMIT 后在应用层 shuffle 以支持 seed
        fetch_limit = min(max(count * 5, count), 500)
        query = f"""
        MATCH (n:Lexeme)
        WHERE NOT n.id IN $exclude_ids {kind_clause}
        RETURN n
        LIMIT $fetch_limit
        """
        params: dict = {"exclude_ids": excluded, "fetch_limit": fetch_limit}
        if kind is not None:
            params["kind"] = kind.value
        with self._session() as session:
            records = list(session.run(query, params))
        nodes = [mapper.lexeme_from_props(mapper.node_to_props(r["n"])) for r in records]
        rng = random.Random(seed)
        rng.shuffle(nodes)
        return nodes[:count]

    def get_induced_subgraph(self, node_ids: list[UUID]) -> LearningSubgraph:
        if not node_ids:
            return LearningSubgraph(node_ids=(), nodes=(), edges=())
        ids = [str(i) for i in node_ids]
        node_query = "MATCH (n:Lexeme) WHERE n.id IN $ids RETURN n"
        edge_query = """
        MATCH (a:Lexeme)-[r:RELATES]->(b:Lexeme)
        WHERE a.id IN $ids AND b.id IN $ids
        RETURN r, a.id AS src_id, b.id AS dst_id
        """
        with self._session() as session:
            node_records = list(session.run(node_query, ids=ids))
            edge_records = list(session.run(edge_query, ids=ids))
        nodes = tuple(mapper.lexeme_from_props(mapper.node_to_props(r["n"])) for r in node_records)
        edges: list[LexemeEdge] = []
        for r in edge_records:
            rel = dict(r["r"])
            edge_id = rel.get("id") or str(uuid4())
            edges.append(
                mapper.edge_from_record(
                    str(edge_id),
                    str(r["src_id"]),
                    str(r["dst_id"]),
                    rel,
                )
            )
        return LearningSubgraph(
            node_ids=tuple(UUID(str(n.id)) for n in nodes),
            nodes=nodes,
            edges=tuple(edges),
        )

    def search_canonical_prefix(
        self, prefix: str, *, limit: int = 20, kind: LexemeKind | None = None
    ) -> list[LexemeNode]:
        if not prefix.strip():
            return []
        kind_clause = "AND n.kind = $kind" if kind is not None else ""
        query = f"""
        MATCH (n:Lexeme)
        WHERE n.canonical_text STARTS WITH $prefix {kind_clause}
        RETURN n
        ORDER BY n.occurrence_count DESC, n.canonical_text
        LIMIT $limit
        """
        params: dict = {"prefix": prefix, "limit": limit}
        if kind is not None:
            params["kind"] = kind.value
        with self._session() as session:
            records = list(session.run(query, params))
        return [mapper.lexeme_from_props(mapper.node_to_props(r["n"])) for r in records]
