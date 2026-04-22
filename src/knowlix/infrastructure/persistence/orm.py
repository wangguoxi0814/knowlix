"""SQLAlchemy 2声明式基类；ORM 模型继承此类，metadata 供 Alembic 使用。"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """聚合所有表定义的 MetaData。"""
