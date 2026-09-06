"""Laptop RAG uses EmbeddingGemma 768-dimensional vectors."""
revision='0003'; down_revision='0002'
def upgrade():
 from alembic import op
 op.execute('DROP INDEX IF EXISTS idx_document_chunks_embedding')
 op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)')
 op.execute('CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops)')
def downgrade():
 from alembic import op
 op.execute('DROP INDEX IF EXISTS idx_document_chunks_embedding')
 op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)')
