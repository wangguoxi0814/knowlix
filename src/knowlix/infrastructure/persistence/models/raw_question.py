"""原始问题表：与 REQUIREMENTS B-MEU-02 对齐的最小持久化模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import BigInteger, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from knowlix.infrastructure.persistence.orm import Base


class RawQuestionORM(Base):
    __tablename__ = "raw_questions"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    body: Mapped[str] = mapped_column(Text())
    context: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # pending | organized | discarded（领域校验后续在用例层加强）
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=sa.text("'pending'"),
    )
    # 创建人/更新人：无账号体系前可用占位 id（如 0）；后续可改 FK
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
