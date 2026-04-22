"""ORM 表模型；导入 side-effect 会注册到 Base.metadata（供 Alembic使用）。"""

from knowlix.infrastructure.persistence.models.raw_question import RawQuestionORM

__all__ = ["RawQuestionORM"]
