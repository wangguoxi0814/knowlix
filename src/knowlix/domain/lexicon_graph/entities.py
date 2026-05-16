"""词汇图谱聚合与值对象（与持久化技术无关）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class LexemeKind(str, Enum):
    WORD = "word"
    PHRASE = "phrase"


class RelationType(str, Enum):
    """可学习关系类型；与技术设计中的边语义对齐。"""

    COLLOCATION = "collocation"
    HYPERNYM = "hypernym"
    COOCCURRENCE = "cooccurrence"
    TRANSLATION = "translation"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class LexemeNode:
    id: UUID
    kind: LexemeKind
    canonical_text: str
    occurrence_count: int = 1
    phonetic: str | None = None
    gloss_short: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.canonical_text.strip():
            raise ValueError("canonical_text 不能为空")


@dataclass(frozen=True, slots=True)
class LexemeEdge:
    id: UUID
    src_id: UUID
    dst_id: UUID
    relation_type: RelationType
    weight: float = 1.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LearningSubgraph:
    """子图学习集 DTO。"""

    node_ids: tuple[UUID, ...]
    nodes: tuple[LexemeNode, ...]
    edges: tuple[LexemeEdge, ...]
    policy_version: str = "v1"
    rng_seed: int | None = None
