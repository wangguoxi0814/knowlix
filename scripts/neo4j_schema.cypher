// 词汇图谱约束（与 ensure_schema() 一致，可手工在 Neo4j Browser 执行）
CREATE CONSTRAINT lexeme_id IF NOT EXISTS FOR (n:Lexeme) REQUIRE n.id IS UNIQUE;
CREATE INDEX lexeme_canonical IF NOT EXISTS FOR (n:Lexeme) ON (n.canonical_text);
CREATE INDEX lexeme_kind IF NOT EXISTS FOR (n:Lexeme) ON (n.kind);
