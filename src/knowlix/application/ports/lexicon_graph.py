"""词汇知识图谱端口：由 Neo4j 等 infrastructure 实现。"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from knowlix.domain.lexicon_graph import (
    LexemeEdge,
    LexemeKind,
    LexemeNode,
    LearningSubgraph,
)


class LexiconGraphPort(Protocol):
    """总词汇图谱的读写与拓扑查询。"""

    def ensure_schema(self) -> None:
        """创建约束与索引（幂等）。"""

    def upsert_lexeme(self, node: LexemeNode) -> LexemeNode:
        ...

    def get_lexeme(self, node_id: UUID) -> LexemeNode | None:
        ...

    def find_by_canonical(self, canonical_text: str, kind: LexemeKind) -> LexemeNode | None:
        ...

    def increment_occurrence(self, node_id: UUID, delta: int = 1) -> int:
        ...

    def create_edge(self, edge: LexemeEdge) -> LexemeEdge:
        ...

    def sample_lexemes(
        self,
        *,
        count: int,
        exclude_ids: frozenset[UUID] | None = None,
        kind: LexemeKind | None = None,
        seed: int | None = None,
    ) -> list[LexemeNode]:
        """随机采样节点（子图种子）。"""

    def get_induced_subgraph(self, node_ids: list[UUID]) -> LearningSubgraph:
        """返回节点集合及其之间的诱导子边。"""

    def search_canonical_prefix(
        self, prefix: str, *, limit: int = 20, kind: LexemeKind | None = None
    ) -> list[LexemeNode]:
        """录入相似合并的前缀检索（规则层兜底）。"""
