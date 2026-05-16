import pytest
from uuid import uuid4

from knowlix.domain.lexicon_graph import LexemeKind, LexemeNode


def test_lexeme_node_rejects_empty_canonical() -> None:
    with pytest.raises(ValueError, match="canonical_text"):
        LexemeNode(id=uuid4(), kind=LexemeKind.WORD, canonical_text="   ")
