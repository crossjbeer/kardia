"""add hnsw index for chunk embeddings

Revision ID: 0004_chunk_fts
Revises: 0003_chunk_embedding_hnsw
Create Date: 2026-03-22 22:33:45.123456
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_chunk_fts"
down_revision = "0003_chunk_embedding_hnsw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column("chunks", sa.Column("search_vector", postgresql.TSVECTOR))

    op.execute("UPDATE chunks SET search_vector = to_tsvector('english', content)")

    op.execute("""
        CREATE INDEX chunks_search_vector_gin_idx
        ON chunks USING gin(search_vector)
    """)

    # trigger keeps search_vector in sync when content changes
    op.execute("""
        CREATE OR REPLACE FUNCTION chunks_search_vector_update() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector := to_tsvector('english', NEW.content);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER chunks_search_vector_trigger
        BEFORE INSERT OR UPDATE OF content ON chunks
        FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_update();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON chunks")
    op.execute("DROP FUNCTION IF EXISTS chunks_search_vector_update")
    op.execute("DROP INDEX IF EXISTS chunks_search_vector_gin_idx")
    op.drop_column("chunks", "search_vector")
