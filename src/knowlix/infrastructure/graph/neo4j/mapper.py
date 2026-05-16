"""Neo4j 记录 ↔ 领域对象。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from knowlix.domain.lexicon_graph import LexemeEdge, LexemeKind, LexemeNode, RelationType

_LABEL = "Lexeme"
_REL = "RELATES"


def node_to_props(node: object) -> dict:
    """将 Neo4j Node 或映射转为普通 dict。"""
    if isinstance(node, dict):
        return node
    items = getattr(node, "items", None)
    if callable(items):
        return dict(items())
    return dict(node)  # type: ignore[arg-type]


def lexeme_from_props(props: dict) -> LexemeNode:
    return LexemeNode(
        id=UUID(str(props["id"])),
        kind=LexemeKind(str(props["kind"])),
        canonical_text=str(props["canonical_text"]),
        occurrence_count=int(props.get("occurrence_count") or 1),
        phonetic=props.get("phonetic"),
        gloss_short=props.get("gloss_short"),
        created_at=_parse_dt(props.get("created_at")),
        updated_at=_parse_dt(props.get("updated_at")),
    )


def edge_from_record(
    edge_id: str,
    src_id: str,
    dst_id: str,
    rel_props: dict,
) -> LexemeEdge:
    return LexemeEdge(
        id=UUID(edge_id),
        src_id=UUID(src_id),
        dst_id=UUID(dst_id),
        relation_type=RelationType(str(rel_props.get("relation_type", RelationType.OTHER.value))),
        weight=float(rel_props.get("weight") or 1.0),
        metadata={
            k: str(v)
            for k, v in rel_props.items()
            if k not in {"relation_type", "weight", "id"} and v is not None
        },
    )


def _parse_dt(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    to_native = getattr(value, "to_native", None)
    if callable(to_native):
        native = to_native()
        if isinstance(native, datetime):
            return native
    return datetime.fromisoformat(str(value))


def lexeme_label() -> str:
    return _LABEL


def relates_type() -> str:
    return _REL
