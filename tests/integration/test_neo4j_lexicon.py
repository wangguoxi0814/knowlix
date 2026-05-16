"""Neo4j 词汇图谱集成测试。

本机 Neo4j 已起且配置 NEO4J_URI 时：``RUN_NEO4J_TESTS=1 pytest tests/integration/test_neo4j_lexicon.py -q``
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from knowlix.domain.lexicon_graph import LexemeEdge, LexemeKind, LexemeNode, RelationType
from knowlix.infrastructure.graph.neo4j import Neo4jLexiconGraphRepository, close_neo4j_driver
from knowlix.infrastructure.graph.neo4j.driver import get_neo4j_driver
from knowlix.settings import settings

pytestmark = pytest.mark.skipif(
    settings.RUN_NEO4J_TESTS != 1 or not (settings.NEO4J_URI or "").strip(),
    reason="需 RUN_NEO4J_TESTS=1 且配置 NEO4J_URI",
)


@pytest.fixture
def graph_repo() -> Neo4jLexiconGraphRepository:
    repo = Neo4jLexiconGraphRepository(get_neo4j_driver())
    repo.ensure_schema()
    yield repo
    close_neo4j_driver()


def test_upsert_sample_and_induced_subgraph(graph_repo: Neo4jLexiconGraphRepository) -> None:
    suffix = uuid4().hex[:8]
    a_id = uuid4()
    b_id = uuid4()
    a = LexemeNode(id=a_id, kind=LexemeKind.WORD, canonical_text=f"neo4j_test_{suffix}_a")
    b = LexemeNode(id=b_id, kind=LexemeKind.WORD, canonical_text=f"neo4j_test_{suffix}_b")
    graph_repo.upsert_lexeme(a)
    graph_repo.upsert_lexeme(b)
    graph_repo.create_edge(
        LexemeEdge(
            id=uuid4(),
            src_id=a_id,
            dst_id=b_id,
            relation_type=RelationType.COLLOCATION,
        )
    )
    graph_repo.increment_occurrence(a_id, delta=2)

    loaded = graph_repo.get_lexeme(a_id)
    assert loaded is not None
    assert loaded.occurrence_count >= 3

    sampled = graph_repo.sample_lexemes(count=5, seed=42)
    assert len(sampled) >= 1

    sub = graph_repo.get_induced_subgraph([a_id, b_id])
    assert len(sub.nodes) == 2
    assert len(sub.edges) == 1
    assert sub.edges[0].relation_type == RelationType.COLLOCATION
