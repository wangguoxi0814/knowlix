"""图数据库适配器。"""

from knowlix.infrastructure.graph.neo4j import Neo4jLexiconGraphRepository, close_neo4j_driver

__all__ = ["Neo4jLexiconGraphRepository", "close_neo4j_driver"]
